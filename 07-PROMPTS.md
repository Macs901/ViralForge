# 07 - Prompts Otimizados v2.0

## 7.1 Arquivo: `config/prompts.py`

```python
"""
Prompts otimizados para os agentes v2.0.
Todos os prompts exigem output JSON estrito e validável.
"""

# ============================================
# ANALYSIS PROMPT (Gemini Vision)
# ============================================

ANALYSIS_PROMPT = """
Você é um especialista em engenharia reversa de conteúdo viral.
Analise este vídeo do Instagram/TikTok e extraia insights estruturados.

## CONTEXTO DO VÍDEO:
- Transcrição: {transcription}
- Legenda: {caption}
- Hashtags: {hashtags}
- Views: {views}
- Likes: {likes}
- Comentários: {comments}

## SUA TAREFA:
Analise o vídeo frame a frame e retorne um JSON com a estrutura EXATA abaixo.

## OUTPUT OBRIGATÓRIO (JSON ESTRITO):

{{
  "hook": {{
    "duration_seconds": <float 0-10>,
    "technique": "<curiosity_gap|pattern_interrupt|bold_claim|question|shocking_stat|controversy|transformation|other>",
    "text_transcription": "<texto falado nos primeiros 3 segundos ou null>",
    "visual_description": "<descrição visual do hook>",
    "effectiveness_score": <float 0-1>
  }},
  "development": {{
    "narrative_style": "<tutorial|story|demonstration|comparison|transformation|behind_scenes|listicle|other>",
    "key_points": ["<ponto 1>", "<ponto 2>", ...],
    "pacing": "<fast|medium|slow>",
    "retention_techniques": ["<técnica 1>", "<técnica 2>", ...]
  }},
  "cta": {{
    "type": "<comment|like|share|follow|link|save|other>",
    "text": "<texto do CTA ou null>",
    "placement": "<start|middle|end>",
    "effectiveness": <float 0-1>
  }},
  "visual_analysis": {{
    "lighting": "<descrição da iluminação>",
    "color_palette": ["<cor 1>", "<cor 2>", ...],
    "camera_movements": ["<movimento 1>", ...],
    "text_overlays": <true|false>,
    "transitions": ["<tipo 1>", ...],
    "thumbnail_hook": "<elemento que chama atenção na thumbnail ou null>"
  }},
  "audio_analysis": {{
    "music_type": "<trending|original|none>",
    "voice_tone": "<energetic|calm|serious|humorous|inspirational>",
    "sound_effects": <true|false>,
    "music_bpm": <int 60-200 ou null>
  }},
  "viral_factors": {{
    "trend_alignment": "<descrição do alinhamento com tendências>",
    "emotional_trigger": "<emoção principal evocada>",
    "shareability_reason": "<motivo pelo qual pessoas compartilhariam>",
    "target_audience": "<público-alvo identificado>"
  }},
  "scores": {{
    "virality_potential": <float 0-1>,
    "replicability": <float 0-1>,
    "production_quality": <float 0-1>
  }}
}}

## REGRAS:
1. Retorne APENAS o JSON, sem texto antes ou depois
2. Não use blocos de código markdown (```)
3. Todos os campos são obrigatórios
4. Use exatamente os valores permitidos nos campos enum
5. Scores devem ser realistas (0.7+ indica viral genuíno)
"""


# ============================================
# STRATEGY PROMPT (GPT-4o)
# ============================================

STRATEGY_PROMPT = """
Você é um copywriter especialista em viralização de conteúdo para Instagram Reels.

## VÍDEO VIRAL DE REFERÊNCIA:
- Transcrição: {transcription}
- Legenda: {caption}
- Métricas: {views} views, {likes} likes, {comments} comentários

## ANÁLISE DO VÍDEO:
- Hook: {hook_analysis}
- Desenvolvimento: {development}
- CTA: {cta_analysis}
- Fatores virais: {viral_factors}
- Elementos visuais: {visual_elements}
- Score de viralidade: {virality_score}

## NICHO ALVO: {target_niche}

## SUA TAREFA:
Crie uma NOVA estratégia de conteúdo inspirada no padrão viral identificado.
O conteúdo deve ser ORIGINAL, não uma cópia.

## OUTPUT OBRIGATÓRIO (JSON ESTRITO):

{{
  "titulo": "<título do vídeo (max 100 chars)>",
  "conceito_central": "<conceito único que diferencia este conteúdo>",
  "roteiro": {{
    "hook": {{
      "duracao": "0-3s",
      "texto_falado": "<texto que será narrado no hook - IMPACTANTE>",
      "acao_visual": "<descrição da ação visual>"
    }},
    "desenvolvimento": {{
      "duracao": "3-25s",
      "texto_falado": "<texto da parte principal - INFORMATIVO e ENGAJANTE>",
      "acao_visual": "<descrição das ações visuais>"
    }},
    "cta": {{
      "duracao": "25-30s",
      "texto_falado": "<texto do call-to-action - URGENTE>",
      "acao_visual": "<descrição da ação visual>"
    }}
  }},
  "veo_prompts": [
    {{
      "scene": 1,
      "duration": "<4s|5s|6s|7s|8s>",
      "prompt": "<prompt detalhado para Veo 3.1 - MÍNIMO 50 palavras>",
      "camera": "<static shot|slow pan|tracking shot|drone shot|handheld|zoom in|zoom out>",
      "lighting": "<natural|studio|dramatic|soft|backlit|golden hour>"
    }},
    {{
      "scene": 2,
      "duration": "...",
      "prompt": "...",
      "camera": "...",
      "lighting": "..."
    }}
  ],
  "publicacao": {{
    "caption": "<legenda completa com emojis e call-to-action>",
    "hashtags": ["<hashtag1>", "<hashtag2>", ...],
    "melhor_horario": "<horário sugerido ex: 18h-20h>",
    "primeira_frase_hook": "<primeira frase que aparece no feed>"
  }}
}}

## DICAS PARA PROMPTS VEO 3.1:
1. Sempre inclua: "4k, cinematic lighting, photorealistic, high quality"
2. Especifique ambiente, sujeito, ação e emoção
3. Movimentos de câmera: "slow pan left", "tracking shot following subject"
4. Máximo 8 segundos por cena
5. Seja MUITO específico - quanto mais detalhes, melhor o resultado

## REGRAS:
1. Retorne APENAS o JSON, sem texto antes ou depois
2. Não use blocos de código markdown (```)
3. O roteiro deve ter EXATAMENTE 3 seções: hook, desenvolvimento, cta
4. Mínimo 3 cenas no veo_prompts, máximo 8
5. Duração total: 25-35 segundos
6. Texto falado deve ser natural para TTS (sem emojis, sem caps lock)
"""


# ============================================
# PRODUCER INSTRUCTIONS (Enhancer de Prompts Veo)
# ============================================

VEO_PROMPT_ENHANCER = """
Você otimiza prompts para o Google Veo 3.1.

## PROMPT ORIGINAL:
{original_prompt}

## DURAÇÃO: {duration}

## REGRAS DE OTIMIZAÇÃO:

1. **Adicione qualificadores técnicos:**
   - "4k resolution, cinematic lighting, photorealistic rendering"
   - "professional cinematography, high production value"

2. **Especifique movimento de câmera:**
   - Se estático: "static shot, locked camera, steady frame"
   - Se movimento: "smooth tracking shot", "slow dolly in", "gentle pan right"

3. **Defina iluminação:**
   - "natural daylight", "golden hour sunlight", "soft studio lighting"
   - "dramatic shadows", "backlit silhouette", "neon glow"

4. **Ambiente e atmosfera:**
   - Cores dominantes
   - Textura do ambiente
   - Profundidade de campo

5. **Ação clara:**
   - Sujeito fazendo ação específica
   - Expressão facial/corporal
   - Interação com ambiente

## OUTPUT:
Retorne APENAS o prompt otimizado, sem explicações.
Máximo 200 palavras.
"""


# ============================================
# TTS SCRIPT OPTIMIZER
# ============================================

TTS_SCRIPT_OPTIMIZER = """
Você otimiza textos para narração TTS (Text-to-Speech).

## TEXTO ORIGINAL:
{original_text}

## REGRAS:
1. Remova emojis e caracteres especiais
2. Converta números para extenso quando natural ("3" → "três")
3. Adicione pontuação para pausas naturais
4. Use "..." para pausas dramáticas
5. Evite siglas - escreva por extenso
6. Mantenha frases curtas (máximo 15 palavras)
7. Use linguagem conversacional

## OUTPUT:
Retorne APENAS o texto otimizado para TTS, sem explicações.
"""


# ============================================
# PROMPT VERSIONS (para o banco de dados)
# ============================================

PROMPT_VERSIONS = {
    'analysis': {
        'v1.0': ANALYSIS_PROMPT,
    },
    'strategy': {
        'v1.0': STRATEGY_PROMPT,
    },
    'veo_enhancer': {
        'v1.0': VEO_PROMPT_ENHANCER,
    },
    'tts_optimizer': {
        'v1.0': TTS_SCRIPT_OPTIMIZER,
    }
}


def get_prompt(prompt_type: str, version: str = 'v1.0') -> str:
    """Retorna um prompt específico por tipo e versão."""
    return PROMPT_VERSIONS.get(prompt_type, {}).get(version, '')


def list_prompt_versions() -> dict:
    """Lista todas as versões de prompts disponíveis."""
    return {
        prompt_type: list(versions.keys())
        for prompt_type, versions in PROMPT_VERSIONS.items()
    }
```

---

## 7.2 Exemplos de Outputs Esperados

### Exemplo de Output do Gemini (Análise)

```json
{
  "hook": {
    "duration_seconds": 2.5,
    "technique": "curiosity_gap",
    "text_transcription": "Você não vai acreditar no que descobri sobre produtividade",
    "visual_description": "Close-up do rosto com expressão de surpresa, fundo desfocado",
    "effectiveness_score": 0.85
  },
  "development": {
    "narrative_style": "tutorial",
    "key_points": [
      "Técnica Pomodoro modificada",
      "Bloqueio de distrações",
      "Revisão semanal"
    ],
    "pacing": "fast",
    "retention_techniques": ["text overlays", "jump cuts", "sound effects"]
  },
  "cta": {
    "type": "follow",
    "text": "Segue pra mais dicas de produtividade",
    "placement": "end",
    "effectiveness": 0.75
  },
  "visual_analysis": {
    "lighting": "Iluminação natural de janela, suave e difusa",
    "color_palette": ["branco", "azul", "bege"],
    "camera_movements": ["static", "zoom in lento no final"],
    "text_overlays": true,
    "transitions": ["jump cut", "fade"],
    "thumbnail_hook": "Expressão de surpresa com texto 'PRODUTIVIDADE'"
  },
  "audio_analysis": {
    "music_type": "trending",
    "voice_tone": "energetic",
    "sound_effects": true,
    "music_bpm": 120
  },
  "viral_factors": {
    "trend_alignment": "Produtividade é tema evergreen com picos em janeiro e setembro",
    "emotional_trigger": "Frustração com falta de foco, desejo de melhoria",
    "shareability_reason": "Dicas práticas e aplicáveis imediatamente",
    "target_audience": "Profissionais 25-35, estudantes universitários"
  },
  "scores": {
    "virality_potential": 0.78,
    "replicability": 0.85,
    "production_quality": 0.72
  }
}
```

### Exemplo de Output do GPT-4o (Estratégia)

```json
{
  "titulo": "A técnica de 2 minutos que mudou minha produtividade",
  "conceito_central": "Regra dos 2 minutos aplicada ao trabalho remoto com twist de gamificação",
  "roteiro": {
    "hook": {
      "duracao": "0-3s",
      "texto_falado": "Eu perdia 3 horas por dia até descobrir essa técnica simples.",
      "acao_visual": "Close no rosto com expressão de revelação importante"
    },
    "desenvolvimento": {
      "duracao": "3-25s",
      "texto_falado": "A regra é simples. Se algo leva menos de dois minutos, faça agora. Mas aqui está o segredo que ninguém conta. Transforme isso em um jogo. Cada tarefa completada vale um ponto. Dez pontos e você ganha uma pausa de cinco minutos. Em uma semana, minha produtividade triplicou.",
      "acao_visual": "Demonstração visual de tarefas sendo completadas, contador de pontos, celebração"
    },
    "cta": {
      "duracao": "25-30s",
      "texto_falado": "Salva esse vídeo e comenta quantos pontos você fez hoje.",
      "acao_visual": "Gesto de salvar, texto animado com call-to-action"
    }
  },
  "veo_prompts": [
    {
      "scene": 1,
      "duration": "4s",
      "prompt": "Professional young adult in modern home office, close-up shot of face showing moment of realization, natural window lighting creating soft shadows, warm color grading, 4k cinematic quality, photorealistic, shallow depth of field with blurred background showing desk setup",
      "camera": "static shot",
      "lighting": "natural"
    },
    {
      "scene": 2,
      "duration": "6s",
      "prompt": "Hands typing on laptop keyboard in modern minimalist workspace, sticky notes being checked off one by one, satisfying visual of task completion, overhead shot transitioning to side angle, soft studio lighting, 4k resolution, professional cinematography",
      "camera": "slow pan",
      "lighting": "studio"
    },
    {
      "scene": 3,
      "duration": "5s",
      "prompt": "Digital counter incrementing from 0 to 10 with celebration particles, gamification UI elements floating in 3D space, vibrant colors against clean white background, motion graphics style, 4k quality, modern tech aesthetic",
      "camera": "zoom in",
      "lighting": "soft"
    },
    {
      "scene": 4,
      "duration": "4s",
      "prompt": "Same professional from scene 1, now smiling confidently at camera, making save gesture with hand, animated text appearing beside them, warm inviting atmosphere, golden hour lighting through window, 4k cinematic, photorealistic rendering",
      "camera": "static shot",
      "lighting": "golden hour"
    }
  ],
  "publicacao": {
    "caption": "A técnica que me fez parar de procrastinar 🎯\n\nEu testei por 30 dias e os resultados foram surreais.\n\nSalva pra não esquecer e comenta quantos pontos você fez! 👇\n\n#produtividade #dicasdeestudo #trabalhoremoto #focototal #organizacao",
    "hashtags": [
      "produtividade",
      "dicasdeestudo",
      "trabalhoremoto",
      "focototal",
      "organizacao",
      "homeoffice",
      "crescimentopessoal"
    ],
    "melhor_horario": "18h-20h",
    "primeira_frase_hook": "A técnica que me fez parar de procrastinar 🎯"
  }
}
```
