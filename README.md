# 🎬 YouTube Clipper

[![Tests](https://img.shields.io/badge/tests-47%2F47%20passed-brightgreen)](https://github.com/rafaelramosdf/youtube-clipper/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![Hermes](https://img.shields.io/badge/hermes-agent-skill-purple)](https://hermes-agent.nousresearch.com)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Sistema inteligente integrado ao **Hermes Agent** para busca, detecção de highlights com IA e corte automático de vídeos do YouTube.

```
"Jarvis, busque vídeos sobre [tema] e faça cortes para o canal"
```

## ✨ Funcionalidades

| Módulo | Tech | Descrição |
|--------|------|-----------|
| 🔍 **search** | YouTube Data API v3 | Busca vídeos por tema (top 5) |
| ⬇️ **download** | yt-dlp | Download MP4 até 1080p |
| 🎙️ **transcribe** | OpenAI Whisper API | Transcrição com timestamps |
| 🧠 **highlights** | GPT-4o-mini | IA detecta melhores momentos |
| ✂️ **clip** | FFmpeg | Corte preciso (copy + re-encode fallback) |
| 🔄 **pipeline** | Python | Orquestração completa do fluxo |

## 🏗️ Arquitetura

```
┌──────────────────────────────────────────┐
│          Hermes Skill (SKILL.md)           │  ← "Jarvis, busque..."
├──────────────────────────────────────────┤
│  search.py  ──→  download.py              │
│       ↓              ↓                    │
│  (usuário    transcribe.py                │
│   escolhe)        ↓                       │
│              highlights.py ──→ clip.py    │
│                                    ↓      │
│                            Telegram 📬    │
└──────────────────────────────────────────┘
```

## 🚀 Uso

### Via Hermes Agent (recomendado)

```
"Jarvis, busque vídeos sobre melhores momentos NBA e faça cortes"
```

O Hermes irá:
1. Buscar top 5 vídeos sobre o tema
2. Mostrar resultados para você escolher
3. Baixar → Transcrever → Detectar highlights → Cortar
4. Enviar clipes via Telegram

### Via CLI

```bash
# Pipeline completo com URLs diretas
uv run python3 -c "
from youtube_clipper.pipeline import run_pipeline
result = run_pipeline(
    query='',
    video_urls=['https://youtube.com/watch?v=VIDEO_ID'],
    max_clips_per_video=3,
    max_clip_duration=60,
)
for c in result.clips:
    print(f'✅ {c.highlight.title} → {c.output_path}')
"
```

### Módulos individuais

```python
# Buscar
from youtube_clipper.search import search_youtube
results = search_youtube("gols do Corinthians", max_results=5)

# Baixar
from youtube_clipper.download import download_video
meta = download_video("https://youtube.com/watch?v=...")

# Transcrever
from youtube_clipper.transcribe import transcribe_video
segments = transcribe_video(meta, language="pt")

# Detectar highlights
from youtube_clipper.highlights import detect_highlights
highlights = detect_highlights(segments, video_duration=300, max_clips=3)

# Cortar
from youtube_clipper.clip import clip_video
clips = clip_video(meta.file_path, highlights)
```

## 📋 Pré-requisitos

- **Python 3.11+**
- **FFmpeg** (já incluso na maioria das distros)
- **API Keys:**
  - [YouTube Data API v3](https://console.cloud.google.com/apis/credentials) — para busca
  - [OpenAI API](https://platform.openai.com/api-keys) — para transcrição + highlights

## 🔧 Instalação

```bash
git clone https://github.com/rafaelramosdf/youtube-clipper.git
cd youtube-clipper
uv sync
```

## ⚙️ Configuração

Crie um arquivo `.env`:

```bash
YOUTUBE_API_KEY=sua_key_youtube
OPENAI_API_KEY=sua_key_openai
```

Ou configure no Hermes:

Ou configure no Hermes:

```bash
hermes config set youtube_clipper.youtube_api_key "sua_key"
hermes config set youtube_clipper.openai_api_key "sua_key"
```

## ✅ Testes

```bash
uv run pytest tests/ -v
# 47 passed ✓
```

| Módulo | Testes | Tipo |
|--------|--------|------|
| download | 7 | Mock |
| transcribe | 9 | Mock + FFmpeg real |
| highlights | 10 | Mock |
| clip | 7 | FFmpeg real |
| search | 9 | Mock |
| pipeline | 5 | Mock |

## 📁 Estrutura

```
youtube-clipper/
├── src/youtube_clipper/
│   ├── search.py          # YouTube search
│   ├── download.py        # Video download
│   ├── transcribe.py      # Audio transcription
│   ├── highlights.py      # AI highlight detection
│   ├── clip.py            # FFmpeg clipping
│   └── pipeline.py        # Orchestrator
├── tests/                 # Test suite (47 tests)
├── skills/youtube-clipper/
│   └── SKILL.md           # Hermes skill definition
├── pyproject.toml
└── README.md
```

## 🗺️ Roadmap

- [x] MVP: busca + download + transcrição + highlights + corte + Telegram
- [ ] Upload automático no YouTube (YouTube Data API v3 insert)
- [ ] Suporte a Shorts vertical (9:16)
- [ ] Watermark/marca d'água personalizada
- [ ] Google Drive upload (fallback)
- [ ] Agendamento via cron jobs do Hermes

## 📄 Licença

MIT © Rafael Ramos