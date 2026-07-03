# PLANO MESTRE IA — ViralForge

> Gerado em 2026-07-03 a partir de auditoria da VPS + leitura do repositório (README.md, STATUS-V3.md, PRD-VIRALFORGE-V3.md, pyproject.toml, estrutura de src/).

## 1. Nome do projeto

**ViralForge** — Sistema autônomo de análise, estratégia e produção de vídeos virais (Instagram Reels, TikTok, YouTube Shorts), com MCP server para operação via Claude.

## 2. Caminho na VPS

- **Source (git):** `/home/marcocardoso/projects/ViralForge/`
- **Cópia duplicada (PROBLEMA):** `/home/marcocardoso/projects/SparkAgency/services/viralforge/` — cópia byte-idêntica dentro do repo SparkAgency, com `.env` próprio divergente
- **Deploy produção:** `/srv/apps/viralforge/`
- **Containers (8):** `viral_api`, `viral_worker`, `viral_scheduler`, `viral_postgres` (postgres:15), `viral_redis`, `viral_minio`, `viralforge-mcp-prd`, `viralforge-rest-prd`
- **Domínio:** `viralforge-mcp.macspark.dev`

## 3. Objetivo

Automatizar o pipeline completo de vídeos virais: **coleta** (Apify: Instagram/TikTok/YouTube/Twitter) → **análise semântica** (Gemini/Claude, transcrição Whisper/Groq) → **estratégia de replicação** (GPT-4) → **produção** (Veo 3.1 via fal.ai + TTS edge-tts/ElevenLabs + mixagem FFmpeg) → **publicação/agendamento** → **tracking de performance e inteligência competitiva**. Tudo operável via MCP server (80+ tools) pelo Claude, servindo à operação de conteúdo da SparkAgency/Sabrina.

## 4. Stack

| Camada | Tecnologia |
|---|---|
| Linguagem | Python ≥3.11 (migração pip → **uv** em andamento, não commitada) |
| API | FastAPI + Uvicorn (`src/api/`) |
| Filas | Celery (concurrency=2) + Redis |
| Banco | PostgreSQL 15 + SQLAlchemy 2 + Alembic (38 models em `src/db/models/`) |
| Storage | MinIO |
| IA | Gemini, Claude (anthropic), GPT-4 (openai), Groq Whisper, openai-whisper local, fal-client (Veo 3.1) |
| Áudio/Vídeo | FFmpeg, pydub, edge-tts (grátis) + ElevenLabs (fallback) |
| Scraping | Apify (Instagram, TikTok, YouTube, Twitter/X) |
| Integração | MCP server (`src/mcp/server.py`, 80+ tools) + REST API |
| Infra | Docker Compose, Traefik, rede `proxy` |

## 5. Estado atual

- **v3.0 COMPLETA** segundo `STATUS-V3.md`: 9 agentes (Watcher, Analyst, Strategist, Producer, Trend Hunter, Scheduler, Style Cloner, Performance Tracker, Competitor Intel), 80+ MCP tools, publishers, scrapers de 4 plataformas.
- **Em produção**: 8 containers rodando de `/srv/apps/viralforge`.
- **Último commit:** 2026-03-15 (`9fea822 refactor: atualiza agents e configurações do ViralForge`) — repo parado há ~3,5 meses.
- **Não commitado:** `pyproject.toml` + `uv.lock` (migração pip→uv), `src/core/telemetry.py`, `renovate.json`, além de `data/`, `frames/` e um MP4 de teste. Backup em `/opt/backups/uncommitted-20260703/ViralForge-uncommitted.tar.gz`.
- **PROBLEMA CENTRAL:** duplicação byte-idêntica do projeto dentro de `SparkAgency/services/viralforge/` (mesmo `main.py` integral), com `.env` divergente — duas "verdades" do mesmo sistema.

## 6. O que já está pronto

- Pipeline completo v3: coleta → análise semântica (cores, enquadramento, expressões, áudio, performance) → roteiro sugerido → estratégia → produção com TTS + mixagem → publicação.
- **MCP server** com 80+ tools (scraping 4 plataformas, análise, estratégia, produção, trend hunting, agendamento, style cloning, performance, competitor intel, publishing) — exposto em `viralforge-mcp.macspark.dev`.
- REST API (`src/api/` + `viralforge-rest-prd`).
- Controle de custos: pré-filtro estatístico de viral score antes de gastar tokens, budget awareness com abort automático, tracking de custos por run.
- Transcrição dupla: Groq Whisper (rápido/grátis via API) ou whisper `medium` local (CPU).
- Banco com 38 models, migrations Alembic, Google Sheets integration, CI/CD básico.
- Suíte de testes em `tests/` (agents, agents_v3, api, models, publishers, scrapers) com pytest.
- Segurança parcial: portas de DB já restritas a localhost (commit `bdeb3c8`).

## 7. O que está faltando

1. **Consolidar a duplicação com SparkAgency** (decisão do Marco pendente — recomendação da auditoria: ViralForge standalone como fonte única; SparkAgency consome via REST API/MCP e remove `services/viralforge/`).
2. **Commitar a migração pip→uv** (`pyproject.toml`, `uv.lock`) + `src/core/telemetry.py` + `renovate.json`; alinhar Dockerfile ao uv e aposentar `requirements.txt`.
3. Remover do versionamento o **MP4 de teste** (`video_autoconfianca_test.mp4` — peso no repo) e garantir `data/`, `frames/`, `*.mp4` no `.gitignore`.
4. **Rotacionar credenciais default** no `.env` de produção (ex.: `minioadmin` no MinIO).
5. Sincronizar produção com o repo após os commits (rebuild das imagens em `/srv/apps/viralforge`).
6. Documentar qual `.env` é canônico e eliminar o divergente do lado SparkAgency.

## 8. Problemas encontrados

- **Duplicação byte-idêntica**: `SparkAgency/services/viralforge/main.py` é cópia integral deste projeto; correções feitas em um lado não chegam ao outro; `.env` divergentes podem fazer os dois lados apontarem para recursos diferentes sem ninguém perceber.
- **Working tree sujo desde março**: migração uv e telemetria existem só no disco (backup feito em 2026-07-03, mas não é versionamento).
- **MP4 de teste versionado/presente no repo** — infla clone e imagem de build.
- **Possíveis credenciais default** (`minioadmin`) no `.env` de produção.
- Incerteza sobre qual código as imagens em produção contêm (repo parado há 3,5 meses, containers rodando há mais tempo que o último commit).
- Dependência dupla de gestão de pacotes durante a transição (requirements.txt no git vs. pyproject/uv fora do git).

## 9. Riscos técnicos

- **Drift irreversível entre as duas cópias**: quanto mais tempo a duplicação viver, mais caro fica consolidar (hoje ainda é byte-idêntica — janela ideal para resolver AGORA).
- **Custos de API descontrolados** se budget tools falharem: Apify, GPT-4, Gemini, Claude, fal.ai (Veo 3.1 é caro por segundo de vídeo), ElevenLabs.
- **Fragilidade de scrapers**: Apify actors e APIs de plataformas mudam sem aviso; scraping de Instagram/TikTok pode quebrar silenciosamente.
- **Recursos da VPS**: Whisper local + FFmpeg + Celery em 4 vCores/15GB compartilhados com todo o ecossistema — OOM é o motivo de concurrency=2; aumentar paralelismo pode derrubar outros projetos.
- Migração pip→uv não testada em build Docker de produção.
- Publicação automática em contas reais: bug no scheduler pode postar conteúdo errado.

## 10. Riscos de segurança

- **Credenciais default** (`minioadmin`) no `.env` de `/srv/apps/viralforge` — rotacionar e reiniciar stack.
- **Duas cópias de `.env` com API keys caras** (OpenAI, Anthropic, Google, Apify, ElevenLabs, fal.ai) em dois repos distintos — dobra a superfície de vazamento; consolidar para um único local em `/srv/`.
- Tokens de publicação (Instagram/TikTok/YouTube) dão controle de contas reais — tratar como segredo crítico.
- `data/` e `frames/` untracked podem conter vídeos/dados de terceiros — nunca commitar.
- Manter portas de postgres/redis/minio fechadas (já restritas a localhost — não regredir).

## 11. Dependências

- **APIs externas pagas:** Apify (scraping), OpenAI GPT-4, Google Gemini, Anthropic Claude, fal.ai (Veo 3.1), ElevenLabs (fallback TTS), Groq (grátis).
- **Infra da VPS:** Traefik + rede `proxy`, Docker Compose; postgres/redis/minio **próprios** (viral_*), não os compartilhados da infra core.
- **Consumidores:** SparkAgency (hoje via cópia duplicada — deve passar a consumir via REST/MCP), Claude Desktop/Code via MCP (`viralforge-mcp.macspark.dev`), Google Sheets.
- **Sistema:** FFmpeg no container do worker; CPU para Whisper local.

## 12. Como rodar (local/VPS)

**Local:**
```bash
cd /home/marcocardoso/projects/ViralForge
cp .env.example .env   # preencher API keys
uv sync                # (pós-migração; hoje: pip install -r requirements.txt)
docker compose up -d   # postgres, redis, minio, worker, api
docker compose exec worker python main.py status
docker compose exec worker python main.py scrape
```

**MCP local (Claude Desktop/Code):**
```bash
python -m src.mcp.server   # cwd=/home/marcocardoso/projects/ViralForge, PYTHONPATH idem
```

**VPS (produção):**
```bash
cd /srv/apps/viralforge
docker compose ps          # 8 containers viral_* e viralforge-*-prd
docker compose logs -f viral_worker
```

## 13. Como testar

```bash
cd /home/marcocardoso/projects/ViralForge
pytest                      # config em pytest.ini; testes em tests/
pytest tests/test_agents_v3.py -v      # agentes v3
pytest tests/test_scrapers.py -v       # scrapers (podem exigir keys/mocks)
```
Smoke test de produção: `curl` no health da REST API via Traefik e uma tool barata do MCP (`get_budget_status`, `list_videos`). Testes que chamam APIs pagas devem rodar com mocks ou budget cap.

## 14. Como fazer deploy

Procedimento padrão da VPS (ver `~/projects/ViralForge/DEPLOY.md` e `08-DOCKER-DEPLOY.md`):
1. Alterações no source em `~/projects/ViralForge` → commit → push (**push exclusivo do @devops**).
2. `cd /srv/apps/viralforge`
3. `docker compose build`
4. `docker compose up -d`
5. `docker compose logs -f` — verificar worker, scheduler e MCP.
6. Nunca expor portas de postgres/redis/minio.

## 15. Plano de finalização em etapas

1. **Etapa 1 — Versionar o que existe (imediato, ~1h):** adicionar `data/`, `frames/`, `*.mp4` ao `.gitignore`; commitar `pyproject.toml` + `uv.lock` + `src/core/telemetry.py` + `renovate.json` (backup já em `/opt/backups/uncommitted-20260703/ViralForge-uncommitted.tar.gz`); remover `video_autoconfianca_test.mp4` do repo.
2. **Etapa 2 — Segurança (mesmo dia):** rotacionar `minioadmin` e demais defaults no `.env` de `/srv/apps/viralforge`; revisar todas as API keys; restart da stack.
3. **Etapa 3 — Consolidação (após decisão do Marco, ~2-3 dias):** eleger `~/projects/ViralForge` como fonte única; em SparkAgency, substituir `services/viralforge/` por cliente REST/MCP; deletar a cópia e o `.env` divergente; documentar o contrato de integração.
4. **Etapa 4 — Alinhar produção (~1 dia):** migrar Dockerfile para uv; rebuild + redeploy em `/srv/apps/viralforge`; smoke test do pipeline ponta a ponta com budget cap baixo.
5. **Etapa 5 — Operação (contínuo):** monitorar custos por run, agendar publicações, revisar Renovate, acompanhar quebras de scrapers.

## 16. Tarefas pendentes por prioridade

**P0 (agora):**
- [ ] Commitar migração uv + telemetry + renovate (não commitados desde março)
- [ ] Rotacionar credenciais default do `.env` de produção (minioadmin)
- [ ] Decisão do Marco sobre a consolidação da duplicação com SparkAgency

**P1 (esta semana):**
- [ ] Executar a consolidação (remover cópia em SparkAgency, integrar via API/MCP)
- [ ] Remover MP4 de teste do repo e ampliar `.gitignore` (data/, frames/, *.mp4)
- [ ] Verificar paridade código ↔ containers em produção e rebuildar

**P2 (este mês):**
- [ ] Migrar Dockerfile/CI para uv e aposentar `requirements.txt`
- [ ] Rodar suíte pytest completa com mocks e corrigir quebras
- [ ] Auditar custos acumulados por API e ajustar budget caps

## 17. Próximos prompts recomendados para continuar com IA

1. "No ViralForge, revise os arquivos não commitados (pyproject.toml, uv.lock, src/core/telemetry.py, renovate.json), confirme que o build ainda funciona com uv e proponha commits atômicos. Não faça push."
2. "Compare byte a byte ~/projects/ViralForge com ~/projects/SparkAgency/services/viralforge (incluindo os .env, sem imprimir segredos) e produza o plano de consolidação: o que deletar, o que a SparkAgency passa a consumir via REST/MCP."
3. "Rotacione as credenciais do .env de /srv/apps/viralforge (MinIO minioadmin e afins), liste os containers a reiniciar e valide o pipeline com get_budget_status."
4. "Migre o Dockerfile do ViralForge de pip/requirements.txt para uv (uv sync --frozen), rebuilde localmente e rode pytest antes de propor deploy."
5. "Gere um relatório de custos do ViralForge: leia o tracking de custos por run no banco e me diga quanto cada API (Apify, GPT-4, Gemini, fal.ai) consumiu no último mês."

## 18. Decisões que Marco precisa tomar

1. **A decisão central — consolidação:** ViralForge standalone como fonte única (recomendação da auditoria) com SparkAgency consumindo via API/MCP, OU mover tudo para dentro do SparkAgency? Cada dia de espera aumenta o risco de drift entre as cópias.
2. **Qual `.env` é o canônico** hoje (o do ViralForge ou o da cópia SparkAgency) — as configs divergem e é preciso saber qual reflete a produção.
3. **Orçamento mensal de APIs** (Veo 3.1/fal.ai é o item caro): definir teto para os budget caps automáticos.
4. **Publicação automática:** manter publish autônomo (scheduler posta sozinho) ou exigir aprovação humana antes de cada post?
5. **Versão do projeto:** `pyproject.toml` declara 2.0.0 mas STATUS descreve v3.0 completa — alinhar versionamento e tags.

## 19. O que NÃO mexer sem cuidado

- **A cópia em `SparkAgency/services/viralforge/`**: não editar nem deletar antes da decisão de consolidação — mudanças unilaterais criam drift; hoje a igualdade byte-idêntica é o que torna a consolidação barata.
- **`.env` de produção** em `/srv/apps/viralforge`: contém todas as API keys pagas e tokens de contas reais; nunca commitar, nunca logar.
- **Budget tools / pré-filtro estatístico**: são o freio de custos; desativar "para testar" pode gerar fatura alta em horas.
- **`viral_postgres`**: 38 models + histórico de análises e custos; migrations Alembic só com backup prévio.
- **Concurrency do Celery (=2)**: calibrada para não dar OOM na VPS compartilhada; não aumentar sem medir RAM.
- **Publishers com tokens reais**: testes de publicação devem usar contas de teste, nunca as contas oficiais.

## 20. Conexão com o ecossistema do agente secretário/segundo cérebro

- ViralForge é o **motor de conteúdo** do ecossistema Macspark: SparkAgency (agência) e o projeto Sabrina (sabrina.macspark.dev / sabelle.com.br) são os consumidores naturais das estratégias e vídeos produzidos.
- O **MCP server em `viralforge-mcp.macspark.dev`** é a interface preferencial do segundo cérebro: o agente secretário (SparkOne/macs-ecosystem) e o Claude podem orquestrar todo o pipeline via as 80+ tools sem tocar no código — este é exatamente o padrão que a consolidação recomendada oficializa (SparkAgency consumindo via MCP/REST em vez de copiar código).
- Integrações existentes que conectam ao segundo cérebro: Google Sheets (relatórios), tracking de performance (insumo para decisões de conteúdo do agente), e potencial de alertas via Evolution API/WhatsApp da infra core (hoje parada).
- Após a consolidação, registrar no memory do ecossistema (`project_ecosystem.md`) que a fonte única é `~/projects/ViralForge` e que qualquer automação do secretário deve usar o MCP, nunca a cópia do SparkAgency.
