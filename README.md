# 🎬 YouTube Clipper

Sistema inteligente integrado ao **Hermes Agent** para busca, detecção de highlights e corte automático de vídeos do YouTube.

## ✨ Funcionalidades

- 🔍 **Busca inteligente** — Encontre vídeos no YouTube por tema/palavra-chave
- 🧠 **Detecção de highlights** — IA analisa a transcrição e identifica os melhores momentos
- ✂️ **Corte preciso** — FFmpeg corta os trechos selecionados com qualidade
- 📬 **Entrega via Telegram** — Clipes enviados diretamente no chat

## 🏗️ Arquitetura

```
┌──────────────────────────────────────┐
│       Hermes Skill (SKILL.md)         │  ← Orquestração
├──────────────────────────────────────┤
│  search.py  │  download.py            │  ← Módulos
│  transcribe │  highlights.py          │
│  clip.py    │  pipeline.py            │
└──────────────────────────────────────┘
```

## 🚀 Uso via Hermes Agent

```
"Jarvis, busque vídeos sobre [tema] e faça cortes"
```

O Hermes irá:
1. Buscar os top 5 vídeos sobre o tema
2. Pedir que você escolha quais cortar
3. Baixar, transcrever e detectar highlights automaticamente
4. Cortar e enviar os clipes via Telegram

## 📋 Pré-requisitos

- Python 3.11+
- FFmpeg
- API Keys: YouTube Data API v3, OpenAI

## 🔧 Instalação

```bash
git clone https://github.com/rafaelramosdf/youtube-clipper.git
cd youtube-clipper
uv sync
```

## ⚙️ Configuração

1. Copie `.env.example` para `.env`
2. Preencha suas API keys
3. Instale a skill no Hermes

## 📄 Licença

MIT