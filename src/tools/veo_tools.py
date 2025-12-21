"""Tools para geracao de video usando Veo 3.1 via Fal.ai."""

import asyncio
import time
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal, Optional, Union

import fal_client
import httpx

from config.settings import get_settings

settings = get_settings()


@dataclass
class VeoJob:
    """Job de geracao Veo."""

    request_id: str
    prompt: str
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class VeoResult:
    """Resultado de geracao de video."""

    video_path: Path
    prompt: str
    duration_seconds: float
    resolution: str
    cost_usd: float
    generation_time_seconds: float


@dataclass
class VeoClipsResult:
    """Resultado de geracao de multiplos clips."""

    clips: list[VeoResult]
    total_cost_usd: float
    total_generation_time_seconds: float
    failed_prompts: list[str]


class VeoTools:
    """Gerenciador de geracao de video usando Veo 3.1 via Fal.ai."""

    # Modelo Veo no Fal.ai
    MODEL_ID = "fal-ai/veo2"  # ou "fal-ai/veo3" quando disponivel

    def __init__(self):
        """Inicializa Veo tools."""
        if not settings.fal_key:
            raise RuntimeError("FAL_KEY nao configurado")
        # Fal client usa variavel de ambiente FAL_KEY automaticamente
        import os
        os.environ["FAL_KEY"] = settings.fal_key

    async def generate_video(
        self,
        prompt: str,
        output_path: Union[str, Path],
        duration: int = 5,
        aspect_ratio: str = "9:16",
        mode: Optional[Literal["test", "production"]] = None,
    ) -> VeoResult:
        """Gera video usando Veo.

        Args:
            prompt: Prompt descritivo do video
            output_path: Caminho de saida
            duration: Duracao em segundos (5-10)
            aspect_ratio: Proporcao (9:16 para vertical, 16:9 para horizontal)
            mode: Modo de geracao (test=rapido/baixa qualidade, production=lento/alta)

        Returns:
            VeoResult com informacoes do video gerado
        """
        mode = mode or settings.veo_mode
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        start_time = time.time()

        # Configura parametros baseado no modo
        if mode == "test":
            # Modo teste: mais rapido, menor qualidade
            model_params = {
                "prompt": prompt,
                "duration": min(duration, 5),
                "aspect_ratio": aspect_ratio,
            }
        else:
            # Modo producao: mais lento, maior qualidade
            model_params = {
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "num_inference_steps": 50,  # Mais steps = maior qualidade
            }

        try:
            # Submete job
            result = await asyncio.to_thread(
                fal_client.subscribe,
                self.MODEL_ID,
                arguments=model_params,
                with_logs=True,
            )

            # Extrai URL do video
            video_url = result.get("video", {}).get("url")
            if not video_url:
                raise RuntimeError("Fal.ai nao retornou URL do video")

            # Download do video
            await self._download_video(video_url, output_path)

            generation_time = time.time() - start_time
            cost = self._calculate_cost(mode)

            return VeoResult(
                video_path=output_path,
                prompt=prompt,
                duration_seconds=float(duration),
                resolution="1080x1920" if aspect_ratio == "9:16" else "1920x1080",
                cost_usd=cost,
                generation_time_seconds=generation_time,
            )

        except Exception as e:
            raise RuntimeError(f"Erro na geracao Veo: {e}")

    async def generate_clips(
        self,
        prompts: list[str],
        output_dir: Union[str, Path],
        duration: int = 5,
        aspect_ratio: str = "9:16",
        mode: Optional[Literal["test", "production"]] = None,
        max_concurrent: int = 2,
    ) -> VeoClipsResult:
        """Gera multiplos clips de video em paralelo.

        Args:
            prompts: Lista de prompts para cada clip
            output_dir: Diretorio de saida
            duration: Duracao de cada clip
            aspect_ratio: Proporcao
            mode: Modo de geracao
            max_concurrent: Maximo de geracoes simultaneas

        Returns:
            VeoClipsResult com todos os clips gerados
        """
        mode = mode or settings.veo_mode
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        clips = []
        failed_prompts = []

        # Processa em batches para limitar concorrencia
        semaphore = asyncio.Semaphore(max_concurrent)

        async def generate_with_semaphore(idx: int, prompt: str) -> Optional[VeoResult]:
            async with semaphore:
                try:
                    output_path = output_dir / f"clip_{idx:03d}.mp4"
                    return await self.generate_video(
                        prompt=prompt,
                        output_path=output_path,
                        duration=duration,
                        aspect_ratio=aspect_ratio,
                        mode=mode,
                    )
                except Exception as e:
                    print(f"[Veo] Erro no clip {idx}: {e}")
                    failed_prompts.append(prompt)
                    return None

        # Gera todos os clips
        tasks = [
            generate_with_semaphore(idx, prompt)
            for idx, prompt in enumerate(prompts)
        ]
        results = await asyncio.gather(*tasks)

        # Filtra resultados validos
        clips = [r for r in results if r is not None]

        total_time = time.time() - start_time
        total_cost = sum(c.cost_usd for c in clips)

        return VeoClipsResult(
            clips=clips,
            total_cost_usd=total_cost,
            total_generation_time_seconds=total_time,
            failed_prompts=failed_prompts,
        )

    async def _download_video(self, url: str, output_path: Path) -> None:
        """Download de video gerado."""
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.get(url)
            response.raise_for_status()

            with open(output_path, "wb") as f:
                f.write(response.content)

    def _calculate_cost(self, mode: str) -> float:
        """Calcula custo da geracao."""
        if mode == "test":
            return float(settings.cost_veo_test)
        return float(settings.cost_veo_production)

    def estimate_cost(
        self,
        num_clips: int,
        mode: Optional[Literal["test", "production"]] = None,
    ) -> float:
        """Estima custo de geracao de clips.

        Args:
            num_clips: Numero de clips a gerar
            mode: Modo de geracao

        Returns:
            Custo estimado em USD
        """
        mode = mode or settings.veo_mode
        cost_per_clip = self._calculate_cost(mode)
        return cost_per_clip * num_clips

    @staticmethod
    def optimize_prompt(prompt: str) -> str:
        """Otimiza prompt para melhores resultados.

        Args:
            prompt: Prompt original

        Returns:
            Prompt otimizado
        """
        # Adiciona modificadores para melhor qualidade
        enhancements = [
            "cinematic lighting",
            "high quality",
            "4K",
            "smooth motion",
        ]

        # Verifica se ja tem alguns desses termos
        prompt_lower = prompt.lower()
        additions = [e for e in enhancements if e.lower() not in prompt_lower]

        if additions:
            prompt = f"{prompt}, {', '.join(additions[:2])}"

        return prompt

    @staticmethod
    def create_scene_prompts(
        hook_description: str,
        development_scenes: list[str],
        cta_description: str,
    ) -> list[str]:
        """Cria lista de prompts para cenas de um video viral.

        Args:
            hook_description: Descricao visual do hook (0-3s)
            development_scenes: Lista de descricoes do desenvolvimento
            cta_description: Descricao visual do CTA

        Returns:
            Lista de prompts otimizados
        """
        prompts = []

        # Hook - precisa ser impactante
        hook_prompt = VeoTools.optimize_prompt(
            f"{hook_description}, dramatic opening shot, attention-grabbing"
        )
        prompts.append(hook_prompt)

        # Development scenes
        for scene in development_scenes:
            scene_prompt = VeoTools.optimize_prompt(scene)
            prompts.append(scene_prompt)

        # CTA - call to action visual
        cta_prompt = VeoTools.optimize_prompt(
            f"{cta_description}, engaging ending, call to action"
        )
        prompts.append(cta_prompt)

        return prompts


# Singleton para uso global
veo_tools = VeoTools()


# Funcao auxiliar sincrona
def generate_video_sync(
    prompt: str,
    output_path: Union[str, Path],
    **kwargs,
) -> VeoResult:
    """Versao sincrona do generate_video."""
    return asyncio.run(veo_tools.generate_video(prompt, output_path, **kwargs))
