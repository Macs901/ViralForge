#!/usr/bin/env python3
"""ViralForge CLI - Sistema Autonomo de Videos Virais."""

import sys
from typing import Optional

import click

from config.settings import get_settings

settings = get_settings()


@click.group()
@click.version_option(version="2.0.0", prog_name="ViralForge")
def cli():
    """ViralForge - Sistema Autonomo de Videos Virais.

    Use os comandos abaixo para gerenciar o pipeline de producao de videos virais.
    """
    pass


# === Comandos de Scraping ===


@cli.command()
@click.option("--profile", "-p", help="Username do perfil (sem @)")
@click.option("--profile-id", "-i", type=int, help="ID do perfil no banco")
@click.option("--max-videos", "-m", default=50, help="Maximo de videos a coletar")
def scrape(profile: Optional[str], profile_id: Optional[int], max_videos: int):
    """Executa scraping de videos de um perfil."""
    from src.agents import watcher_agent

    if not profile and not profile_id:
        click.echo("Erro: Informe --profile ou --profile-id")
        sys.exit(1)

    try:
        result = watcher_agent.run(
            profile_id=profile_id,
            username=profile,
            max_videos=max_videos,
        )
        click.echo(f"✅ Scraping concluido!")
        click.echo(f"   Perfil: @{result.profile_username}")
        click.echo(f"   Videos coletados: {result.videos_collected}")
        click.echo(f"   Pre-filtrados: {result.videos_prefiltered}")
        click.echo(f"   Custo: ${result.cost_usd:.4f}")
    except Exception as e:
        click.echo(f"❌ Erro: {e}")
        sys.exit(1)


@cli.command()
@click.option("--max-videos", "-m", default=30, help="Maximo de videos por perfil")
def scrape_all(max_videos: int):
    """Executa scraping de todos os perfis ativos."""
    from src.agents import watcher_agent

    click.echo("🔍 Iniciando scraping de todos os perfis...")
    results = watcher_agent.run_all_active_profiles(max_videos)

    total_collected = sum(r.videos_collected for r in results)
    total_prefiltered = sum(r.videos_prefiltered for r in results)
    total_cost = sum(r.cost_usd for r in results)

    click.echo(f"✅ Scraping concluido!")
    click.echo(f"   Perfis processados: {len(results)}")
    click.echo(f"   Total coletados: {total_collected}")
    click.echo(f"   Total pre-filtrados: {total_prefiltered}")
    click.echo(f"   Custo total: ${total_cost:.4f}")


@cli.command()
@click.argument("username")
@click.argument("niche")
@click.option("--priority", "-p", default=1, help="Prioridade (1-5)")
def add_profile(username: str, niche: str, priority: int):
    """Adiciona novo perfil para monitoramento.

    USERNAME: Nome de usuario do Instagram (sem @)
    NICHE: Categoria/nicho do perfil
    """
    from src.agents import watcher_agent

    try:
        profile = watcher_agent.add_profile(
            username=username,
            niche=niche,
            priority=priority,
        )
        click.echo(f"✅ Perfil @{profile.username} adicionado!")
        click.echo(f"   ID: {profile.id}")
        click.echo(f"   Nicho: {profile.niche}")
    except Exception as e:
        click.echo(f"❌ Erro: {e}")
        sys.exit(1)


# === Comandos de Analise ===


@cli.command()
@click.argument("video_id", type=int)
@click.option("--force", "-f", is_flag=True, help="Reanalisar mesmo se ja analisado")
@click.option("--provider", "-p", type=click.Choice(["gemini", "claude"]), help="Provider de analise")
def analyze(video_id: int, force: bool, provider: Optional[str]):
    """Analisa um video especifico."""
    from src.agents import get_analyst_agent

    try:
        agent = get_analyst_agent(provider=provider)
        result = agent.analyze(video_id, force=force)
        click.echo(f"✅ Analise concluida! (provider: {agent.provider})")
        click.echo(f"   Virality Score: {result.virality_score:.2f}")
        click.echo(f"   Replicability Score: {result.replicability_score:.2f}")
        click.echo(f"   Valido: {'Sim' if result.is_valid else 'Nao'}")
        click.echo(f"   Custo: ${result.cost_usd:.4f}")
    except Exception as e:
        click.echo(f"❌ Erro: {e}")
        sys.exit(1)


@cli.command()
@click.option("--limit", "-l", default=10, help="Maximo de videos a analisar")
@click.option("--provider", "-p", type=click.Choice(["gemini", "claude"]), help="Provider de analise")
def analyze_pending(limit: int, provider: Optional[str]):
    """Analisa videos pendentes que passaram no pre-filtro."""
    from src.agents import get_analyst_agent

    agent = get_analyst_agent(provider=provider)
    click.echo(f"🧠 Analisando videos pendentes com {agent.provider}...")
    results = agent.analyze_pending(limit=limit)

    valid = sum(1 for r in results if r.is_valid)
    total_cost = sum(r.cost_usd for r in results)

    click.echo(f"✅ Analise concluida!")
    click.echo(f"   Videos analisados: {len(results)}")
    click.echo(f"   Analises validas: {valid}")
    click.echo(f"   Custo total: ${total_cost:.4f}")


# === Comandos de Estrategia ===


@cli.command()
@click.argument("video_id", type=int)
@click.option("--niche", "-n", help="Nicho alvo")
def strategy(video_id: int, niche: Optional[str]):
    """Gera estrategia a partir de um video analisado."""
    from src.agents import strategist_agent

    try:
        result = strategist_agent.generate(video_id, niche=niche)
        click.echo(f"✅ Estrategia gerada!")
        click.echo(f"   ID: {result.strategy_id}")
        click.echo(f"   Titulo: {result.title}")
        click.echo(f"   Cenas: {result.num_scenes}")
        click.echo(f"   Custo estimado: ${result.estimated_cost_usd:.2f}")
    except Exception as e:
        click.echo(f"❌ Erro: {e}")
        sys.exit(1)


@cli.command()
@click.argument("niche")
@click.option("--limit", "-l", default=3, help="Numero de estrategias")
def strategy_batch(niche: str, limit: int):
    """Gera estrategias a partir dos melhores videos de um nicho."""
    from src.agents import strategist_agent

    click.echo(f"📝 Gerando {limit} estrategias para nicho '{niche}'...")
    results = strategist_agent.generate_from_best_videos(niche=niche, limit=limit)

    total_cost = sum(r.cost_usd for r in results)

    click.echo(f"✅ Estrategias geradas!")
    for r in results:
        click.echo(f"   - [{r.strategy_id}] {r.title}")
    click.echo(f"   Custo total: ${total_cost:.4f}")


# === Comandos de Producao ===


@cli.command()
@click.argument("strategy_id", type=int)
@click.option("--mode", "-m", type=click.Choice(["test", "production"]), default="test")
@click.option("--music", help="Nome do arquivo de musica")
def produce(strategy_id: int, mode: str, music: Optional[str]):
    """Produz video a partir de uma estrategia."""
    from src.agents import producer_agent

    click.echo(f"🎬 Iniciando producao (modo: {mode})...")

    try:
        result = producer_agent.produce_sync(
            strategy_id=strategy_id,
            mode=mode,
            music_track=music,
        )
        click.echo(f"✅ Video produzido!")
        click.echo(f"   Production ID: {result.production_id}")
        click.echo(f"   Duracao: {result.duration_seconds}s")
        click.echo(f"   Custo: ${result.total_cost_usd:.2f}")
        click.echo(f"   Tempo: {result.production_time_seconds:.1f}s")
        click.echo(f"   Path: {result.final_video_path}")
    except Exception as e:
        click.echo(f"❌ Erro: {e}")
        sys.exit(1)


@cli.command()
@click.argument("strategy_id", type=int)
def approve(strategy_id: int):
    """Aprova estrategia para producao."""
    from src.agents import producer_agent

    try:
        strategy = producer_agent.approve_strategy(strategy_id)
        click.echo(f"✅ Estrategia aprovada!")
        click.echo(f"   Titulo: {strategy.title}")
        click.echo(f"   Status: {strategy.status}")
    except Exception as e:
        click.echo(f"❌ Erro: {e}")
        sys.exit(1)


# === Comandos de Status ===


@cli.command()
def status():
    """Mostra status geral do sistema."""
    from src.tools import budget_tools

    status = budget_tools.get_daily_status()

    click.echo("📊 Status do ViralForge")
    click.echo("=" * 40)
    click.echo(f"📅 Data: {status['date']}")
    click.echo()
    click.echo("💰 Orcamento:")
    budget = status["budget"]
    click.echo(f"   Limite: ${budget['limit_usd']:.2f}")
    click.echo(f"   Gasto: ${budget['spent_usd']:.2f}")
    click.echo(f"   Restante: ${budget['remaining_usd']:.2f}")
    click.echo(f"   Uso: {budget['usage_percent']:.1f}%")
    if budget["exceeded"]:
        click.echo("   ⚠️  BUDGET EXCEDIDO!")
    click.echo()
    click.echo("📈 Contadores:")
    counters = status["counters"]
    click.echo(f"   Scraping runs: {counters['scraping_runs']}")
    click.echo(f"   Videos coletados: {counters['videos_collected']}")
    click.echo(f"   Videos analisados: {counters['videos_analyzed']}")
    click.echo(f"   Estrategias geradas: {counters['strategies_generated']}")
    click.echo(f"   Videos produzidos: {counters['videos_produced']}")
    click.echo()
    click.echo("💵 Custos por servico:")
    costs = status["costs_by_service"]
    click.echo(f"   Apify: ${costs['apify']:.4f}")
    click.echo(f"   Gemini: ${costs['gemini']:.4f}")
    click.echo(f"   OpenAI: ${costs['openai']:.4f}")
    click.echo(f"   Veo: ${costs['veo']:.4f}")
    click.echo(f"   ElevenLabs: ${costs['elevenlabs']:.4f}")


@cli.command()
def init_db():
    """Inicializa o banco de dados."""
    from src.core.database import init_db

    click.echo("🗄️  Inicializando banco de dados...")
    init_db()
    click.echo("✅ Banco de dados inicializado!")


@cli.command()
def list_profiles():
    """Lista todos os perfis monitorados."""
    from sqlalchemy import select
    from src.core.database import get_sync_db
    from src.db.models import MonitoredProfile

    db = get_sync_db()
    try:
        profiles = db.execute(select(MonitoredProfile)).scalars().all()

        if not profiles:
            click.echo("Nenhum perfil cadastrado.")
            return

        click.echo("📋 Perfis Monitorados:")
        click.echo("-" * 60)
        for p in profiles:
            status = "🟢" if p.is_active else "🔴"
            click.echo(f"{status} [{p.id}] @{p.username} | {p.niche} | P{p.priority}")
            click.echo(f"   Videos: {p.total_videos_collected} | Ultimo: {p.last_scraped_at or 'Nunca'}")
    finally:
        db.close()


@cli.command()
@click.option("--status", "-s", type=click.Choice(["pending", "analyzed", "all"]), default="all")
@click.option("--limit", "-l", default=20, help="Numero de videos a listar")
def list_videos(status: str, limit: int):
    """Lista videos coletados."""
    from sqlalchemy import select
    from src.core.database import get_sync_db
    from src.db.models import ViralVideo

    db = get_sync_db()
    try:
        stmt = select(ViralVideo)

        if status == "pending":
            stmt = stmt.where(
                ViralVideo.passes_prefilter == True,
                ViralVideo.is_analyzed == False,
            )
        elif status == "analyzed":
            stmt = stmt.where(ViralVideo.is_analyzed == True)

        stmt = stmt.order_by(ViralVideo.statistical_viral_score.desc()).limit(limit)
        videos = db.execute(stmt).scalars().all()

        if not videos:
            click.echo("Nenhum video encontrado.")
            return

        click.echo(f"🎥 Videos ({status}):")
        click.echo("-" * 80)
        for v in videos:
            prefilter = "✅" if v.passes_prefilter else "❌"
            analyzed = "📊" if v.is_analyzed else "⏳"
            click.echo(
                f"[{v.id}] {prefilter}{analyzed} Score: {float(v.statistical_viral_score or 0):.2f} | "
                f"👀 {v.views_count:,} | ❤️ {v.likes_count:,}"
            )
    finally:
        db.close()


@cli.command()
@click.option("--status", "-s", type=click.Choice(["draft", "approved", "produced", "all"]), default="all")
@click.option("--limit", "-l", default=20, help="Numero de estrategias a listar")
def list_strategies(status: str, limit: int):
    """Lista estrategias geradas."""
    from sqlalchemy import select
    from src.core.database import get_sync_db
    from src.db.models import GeneratedStrategy

    db = get_sync_db()
    try:
        stmt = select(GeneratedStrategy)

        if status != "all":
            stmt = stmt.where(GeneratedStrategy.status == status)

        stmt = stmt.order_by(GeneratedStrategy.created_at.desc()).limit(limit)
        strategies = db.execute(stmt).scalars().all()

        if not strategies:
            click.echo("Nenhuma estrategia encontrada.")
            return

        click.echo(f"📝 Estrategias ({status}):")
        click.echo("-" * 80)
        for s in strategies:
            icon = {"draft": "📝", "approved": "✅", "in_production": "🎬", "produced": "🎥"}.get(s.status, "❓")
            click.echo(f"[{s.id}] {icon} {s.title[:50]}")
            click.echo(f"   Cenas: {s.scene_count} | Custo est.: ${float(s.estimated_production_cost_usd or 0):.2f}")
    finally:
        db.close()


@cli.command()
def help_commands():
    """Mostra ajuda detalhada dos comandos."""
    click.echo("""
ViralForge v2.0 - Comandos Disponiveis

SCRAPING:
  scrape          Scraping de um perfil especifico
  scrape-all      Scraping de todos os perfis ativos
  add-profile     Adicionar novo perfil para monitorar

ANALISE:
  analyze         Analisar um video especifico
  analyze-pending Analisar videos pendentes

ESTRATEGIA:
  strategy        Gerar estrategia para um video
  strategy-batch  Gerar estrategias em lote

PRODUCAO:
  produce         Produzir video de uma estrategia
  approve         Aprovar estrategia para producao

STATUS:
  status          Status geral do sistema
  list-profiles   Listar perfis monitorados
  list-videos     Listar videos coletados
  list-strategies Listar estrategias geradas

SISTEMA:
  init-db         Inicializar banco de dados
  help-commands   Esta ajuda

Use 'python main.py COMANDO --help' para detalhes de cada comando.
    """)


if __name__ == "__main__":
    cli()
