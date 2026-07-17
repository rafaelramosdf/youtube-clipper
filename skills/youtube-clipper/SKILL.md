---
name: youtube-clipper
description: "Busca vídeos no YouTube, detecta highlights com IA e faz cortes automáticos — integrado ao Hermes Agent"
version: 1.0.0
author: Rafael Ramos
platforms: [linux]
metadata:
  hermes:
    tags: [youtube, video, clipping, shorts, highlights, ai]
    required_toolsets: [terminal, file, send_message]
    env_vars:
      - YOUTUBE_API_KEY
      - OPENAI_API_KEY
---

# 🎬 YouTube Clipper

Sistema inteligente de busca, detecção de highlights e corte de vídeos do YouTube.

## Fluxo de Uso (via Hermes)

O usuário faz um pedido como:

> "Jarvis, busque vídeos sobre [tema] e faça cortes"

Ou mais específico:

> "Jarvis, quero novos cortes para o canal. Busque vídeos sobre [tema] no YouTube e me mostre os top 5."

### Etapas

1. **Busca**: Execute `search.py` com o tema solicitado
2. **Apresentação**: Mostre os resultados formatados (título, canal, duração, thumbnail)
3. **Seleção**: Pergunte ao usuário quais vídeos cortar (ex: "1, 3, 5")
4. **Processamento**: Para cada vídeo selecionado:
   - Download → Transcrição → Detecção de highlights → Corte
5. **Entrega**: Envie os clipes via Telegram usando `send_message` com `MEDIA:`

## Comandos

### Buscar vídeos

```bash
cd /opt/data/youtube-clipper && uv run python3 -c "
from youtube_clipper.search import search_youtube
results = search_youtube('QUERY_AQUI', max_results=5)
for i, r in enumerate(results, 1):
    print(f'{i}. {r.title} | {r.channel} | {r.duration} | {r.url}')
"
```

### Baixar vídeo

```bash
cd /opt/data/youtube-clipper && uv run python3 -c "
from youtube_clipper.download import download_video
meta = download_video('URL_DO_VIDEO')
print(f'Baixado: {meta.title} → {meta.file_path}')
"
```

### Transcrever vídeo

```bash
cd /opt/data/youtube-clipper && uv run python3 -c "
from youtube_clipper.download import VideoMetadata
from youtube_clipper.transcribe import transcribe_video
meta = VideoMetadata('ID', 'Titulo', 'Canal', 300, 'CAMINHO/VIDEO.mp4')
segs = transcribe_video(meta, language='pt')
print(f'Segmentos: {len(segs)}')
"
```

### Detectar highlights

```bash
cd /opt/data/youtube-clipper && uv run python3 -c "
from youtube_clipper.highlights import detect_highlights
# segments = resultado da transcrição
# highlights = detect_highlights(segments, video_duration=300, video_title='Título', max_clips=3)
"
```

### Cortar vídeo

```bash
cd /opt/data/youtube-clipper && uv run python3 -c "
from youtube_clipper.clip import clip_video
from youtube_clipper.highlights import Highlight
# results = clip_video('VIDEO.mp4', highlights, output_dir='/tmp/clips')
"
```

### Pipeline completo (um vídeo)

```bash
cd /opt/data/youtube-clipper && uv run python3 -c "
from youtube_clipper.pipeline import run_pipeline
result = run_pipeline(
    query='tema',
    video_urls=['https://youtube.com/watch?v=ID'],
    max_clips_per_video=3,
    max_clip_duration=60,
)
for clip in result.clips:
    if clip.success:
        print(f'✅ {clip.highlight.title} → {clip.output_path}')
    else:
        print(f'❌ {clip.highlight.title}: {clip.error}')
"
```

## Tratamento de Erros

| Erro | Causa | Solução |
|------|-------|---------|
| `YouTube API key not configured` | YOUTUBE_API_KEY não está definida | Configure a env var ou aguarde o usuário fornecer |
| `Transcription failed` | OPENAI_API_KEY inválida ou sem créditos | Verifique a key no .env |
| `Download failed` | Vídeo indisponível/privado | Avise o usuário e pule o vídeo |
| `No highlights found` | Transcrição vazia ou vídeo monótono | Avise que nenhum corte foi gerado |

## Envio via Telegram

Após gerar os clipes, envie cada um usando:

```
send_message com MEDIA:/caminho/do/clipe.mp4
```

Formate a mensagem com:
- Título do clipe
- Fonte (canal original)
- Duração

## Configuração

As API keys devem estar em `.env`:

```bash
YOUTUBE_API_KEY=sua_key_youtube
OPENAI_API_KEY=sua_key_openai
```

Ou configuradas no ambiente Hermes via `hermes config set`.

## Limitações

- Requer FFmpeg instalado (já disponível)
- Requer yt-dlp (instalado via uv sync)
- YouTube API quota: 10.000 unidades/dia (≈100 buscas)
- Whisper API: cobrado por minuto de áudio
- Sem GPU: transcrição via API (rápida, mas paga)