"""Producer Agent - Responsavel por produzir videos completos."""

import asyncio
import tempfile
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional
from uuid import uuid4

from sqlalchemy import select

from config.settings import get_settings
from src.core.database import get_sync_db
from src.db.models import (
    GeneratedStrategy,
    ProducedVideo,
    ProductionStatus,
    RunMetrics,
    StrategyStatus,
)
from src.tools import budget_tools, ffmpeg_tools, storage_tools, tts_tools, veo_tools

settings = get_settings()


@dataclass
class ProducerResult:
    """Resultado de producao de video."""

    run_id: str
    production_id: int
    strategy_id: int
    final_video_path: str
    duration_seconds: float
    total_cost_usd: float
    production_time_seconds: float
    error: Optional[str] = None


class ProducerAgent:
    """Agent responsavel por produzir videos completos.

    Pipeline:
    1. Geracao de TTS (narracao)
    2. Geracao de clips Veo
    3. Concatenacao dos clips
    4. Mixagem final (video + narracao + musica)
    5. Upload para MinIO
    """

    def __init__(self):
        """Inicializa Producer Agent."""
        self.tts = tts_tools
        self.veo = veo_tools
        self.ffmpeg = ffmpeg_tools
        self.storage = storage_tools
        self.budget = budget_tools

    async def produce(
        self,
        strategy_id: int,
        mode: Optional[str] = None,
        music_track: Optional[str] = None,
    ) -> ProducerResult:
        """Produz video completo a partir de uma estrategia.

        Args:
            strategy_id: ID da estrategia
            mode: Modo Veo (test/production)
            music_track: Nome do arquivo de musica (opcional)

        Returns:
            ProducerResult com resultado da producao
        """
        run_id = str(uuid4())
        start_time = datetime.now()
        mode = mode or settings.veo_mode

        db = get_sync_db()
        try:
            # Busca estrategia
            strategy = db.get(GeneratedStrategy, strategy_id)
            if not strategy:
                raise ValueError(f"Estrategia {strategy_id} nao encontrada")

            if strategy.status not in [StrategyStatus.DRAFT.value, StrategyStatus.APPROVED.value]:
                raise ValueError(f"Estrategia nao esta pronta para producao (status: {strategy.status})")

            # Verifica budget
            can_produce, msg = self.budget.can_produce_video(
                num_scenes=strategy.scene_count,
                script_chars=strategy.total_script_length,
                veo_mode=mode,
            )
            if not can_produce:
                raise RuntimeError(msg)

            # Cria registro de producao
            production = ProducedVideo(
                strategy_id=strategy_id,
                status=ProductionStatus.PENDING.value,
            )
            db.add(production)

            # Cria metrica de run
            run_metric = RunMetrics(
                run_id=run_id,
                task_name="producer_production",
                agent_name="producer",
            )
            db.add(run_metric)

            # Atualiza status da estrategia
            strategy.status = StrategyStatus.IN_PRODUCTION.value
            db.commit()
            db.refresh(production)

            print(f"[Producer] Iniciando producao #{production.id} para estrategia '{strategy.title}'")

            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)

                # 1. Gera TTS
                print("[Producer] Gerando narracao TTS...")
                production.status = ProductionStatus.GENERATING_TTS.value
                db.commit()

                tts_result = await self._generate_tts(strategy, tmp_path)
                production.tts_file_path = str(tts_result.file_path)
                production.tts_provider = tts_result.provider
                production.narration_duration_seconds = Decimal(str(tts_result.duration_seconds))
                production.tts_cost_usd = Decimal(str(tts_result.cost_usd))

                # 2. Gera clips Veo
                print(f"[Producer] Gerando {strategy.scene_count} clips Veo ({mode})...")
                production.status = ProductionStatus.GENERATING_VIDEO.value
                db.commit()

                clips_result = await self._generate_clips(strategy, tmp_path, mode)
                production.clips_paths = [str(c.video_path) for c in clips_result.clips]
                production.veo_cost_usd = Decimal(str(clips_result.total_cost_usd))
                production.veo_jobs = [
                    {"prompt": c.prompt, "path": str(c.video_path)}
                    for c in clips_result.clips
                ]

                if clips_result.failed_prompts:
                    print(f"[Producer] Aviso: {len(clips_result.failed_prompts)} clips falharam")

                # 3. Concatena clips
                print("[Producer] Concatenando clips...")
                production.status = ProductionStatus.MIXING.value
                db.commit()

                concatenated_path = tmp_path / "concatenated.mp4"
                clip_paths = [c.video_path for c in clips_result.clips]
                self.ffmpeg.concatenate_videos(clip_paths, concatenated_path)

                # 4. Mixa audio
                print("[Producer] Mixando audio...")
                final_path = tmp_path / "final.mp4"

                music_path = None
                if music_track:
                    music_full_path = settings.music_path / music_track
                    if music_full_path.exists():
                        music_path = music_full_path
                        production.music_track_used = music_track
                        production.music_volume_used = strategy.music_volume

                mix_result = self.ffmpeg.mix_audio_with_video(
                    video_path=concatenated_path,
                    narration_path=tts_result.file_path,
                    output_path=final_path,
                    music_path=music_path,
                    music_volume=float(strategy.music_volume),
                )

                # 5. Upload para MinIO
                print("[Producer] Fazendo upload para storage...")
                final_remote_path = self.storage.upload_production(
                    final_path,
                    production.id,
                    "final",
                )
                production.final_video_path = final_remote_path

                # Metadados do video final
                video_info = self.ffmpeg.get_video_info(final_path)
                production.final_duration_seconds = int(video_info.duration_seconds)
                production.final_resolution = f"{video_info.width}x{video_info.height}"
                production.final_file_size_mb = Decimal(
                    str(final_path.stat().st_size / (1024 * 1024))
                )

            # Calcula custo total
            production.calculate_total_cost()
            production.status = ProductionStatus.COMPLETED.value

            # Atualiza estrategia
            strategy.status = StrategyStatus.PRODUCED.value

            # Registra custos
            if production.tts_cost_usd > 0:
                self.budget.register_cost("elevenlabs", production.tts_cost_usd, 1, db)
            self.budget.register_cost("veo", production.veo_cost_usd, strategy.scene_count, db)
            self.budget.increment_counter("videos_produced", 1, db)
            self.budget.increment_counter("veo_generations", strategy.scene_count, db)

            # Finaliza metrica
            run_metric.items_processed = 1
            run_metric.actual_cost_usd = production.total_production_cost_usd
            run_metric.complete(success=True)

            db.commit()

            production_time = (datetime.now() - start_time).total_seconds()

            print(f"[Producer] Producao #{production.id} concluida! "
                  f"Custo: ${production.total_production_cost_usd}")

            return ProducerResult(
                run_id=run_id,
                production_id=production.id,
                strategy_id=strategy_id,
                final_video_path=production.final_video_path,
                duration_seconds=float(production.final_duration_seconds or 0),
                total_cost_usd=float(production.total_production_cost_usd or 0),
                production_time_seconds=production_time,
            )

        except Exception as e:
            # Registra falha
            if "production" in locals():
                production.status = ProductionStatus.FAILED.value
                production.error_message = str(e)
            if "strategy" in locals():
                strategy.status = StrategyStatus.DRAFT.value
            if "run_metric" in locals():
                run_metric.complete(success=False, error=str(e))
            db.commit()
            raise
        finally:
            db.close()

    async def _generate_tts(
        self,
        strategy: GeneratedStrategy,
        output_dir: Path,
    ):
        """Gera narracao TTS."""
        # Combina scripts
        full_script = strategy.full_script or (
            f"{strategy.hook_script or ''} "
            f"{strategy.development_script or ''} "
            f"{strategy.cta_script or ''}"
        )

        output_path = output_dir / "narration.mp3"

        return await self.tts.generate_tts(
            text=full_script.strip(),
            output_path=output_path,
            voice=strategy.tts_config.get("voice") if strategy.tts_config else None,
        )

    async def _generate_clips(
        self,
        strategy: GeneratedStrategy,
        output_dir: Path,
        mode: str,
    ):
        """Gera clips de video com Veo."""
        if not strategy.veo_prompts:
            raise ValueError("Estrategia sem prompts Veo definidos")

        # Extrai prompts visuais
        prompts = [
            self.veo.optimize_prompt(p.get("visual_description", ""))
            for p in strategy.veo_prompts
        ]

        return await self.veo.generate_clips(
            prompts=prompts,
            output_dir=output_dir / "clips",
            duration=5,  # 5 segundos por clip
            aspect_ratio="9:16",  # Vertical
            mode=mode,
        )

    def produce_sync(
        self,
        strategy_id: int,
        mode: Optional[str] = None,
        music_track: Optional[str] = None,
    ) -> ProducerResult:
        """Versao sincrona do produce."""
        return asyncio.run(self.produce(strategy_id, mode, music_track))

    def produce_next_approved(self, mode: Optional[str] = None) -> Optional[ProducerResult]:
        """Produz proxima estrategia aprovada.

        Args:
            mode: Modo Veo

        Returns:
            ProducerResult ou None se nao houver estrategia
        """
        db = get_sync_db()
        try:
            # Busca estrategia aprovada
            stmt = (
                select(GeneratedStrategy)
                .where(GeneratedStrategy.status == StrategyStatus.APPROVED.value)
                .order_by(GeneratedStrategy.created_at)
                .limit(1)
            )
            strategy = db.execute(stmt).scalar_one_or_none()

            if not strategy:
                print("[Producer] Nenhuma estrategia aprovada encontrada")
                return None

            return self.produce_sync(strategy.id, mode)
        finally:
            db.close()

    def approve_strategy(self, strategy_id: int) -> GeneratedStrategy:
        """Aprova estrategia para producao.

        Args:
            strategy_id: ID da estrategia

        Returns:
            GeneratedStrategy atualizada
        """
        db = get_sync_db()
        try:
            strategy = db.get(GeneratedStrategy, strategy_id)
            if not strategy:
                raise ValueError(f"Estrategia {strategy_id} nao encontrada")

            strategy.status = StrategyStatus.APPROVED.value
            db.commit()
            db.refresh(strategy)

            print(f"[Producer] Estrategia '{strategy.title}' aprovada para producao!")
            return strategy
        finally:
            db.close()


# Singleton para uso global
producer_agent = ProducerAgent()
