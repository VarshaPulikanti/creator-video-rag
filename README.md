# Creator Video RAG

Full-stack RAG chatbot that ingests **one YouTube video (A)** and **one Instagram Reel (B)**, pulls transcripts + metadata, computes engagement rates, embeds chunks into **ChromaDB**, and answers creator questions via **LangChain** with **streaming**, **source citations**, and **multi-turn memory**.

Optimized for **cost vs quality at ~1,000 creators/day** — UI is functional, not fancy.

---

## What it does

1. Accepts YouTube + Instagram Reel URLs
2. Fetches metadata (views, likes, comments, creator, followers, hashtags, date, duration) via **yt-dlp**
3. Fetches transcripts:
   - **YouTube:** `youtube-transcript-api` → description → optional Whisper
   - **Instagram:** yt-dlp subs → caption → optional Whisper (`ENABLE_WHISPER=true`, `pip install faster-whisper`)
4. Computes **engagement rate** = `(likes + comments) / views × 100`
5. Chunks + embeds (OpenAI `text-embedding-3-small`) into **ChromaDB**, every chunk tagged with `video_id` (`A` or `B`)
6. RAG chat (LangChain retrieval chain + history-aware retriever) with:
   - SSE **streaming**
   - **Citations** (video + chunk index + excerpt)
   - **Session memory** (JSON file, sliding window)

---

## Stack

| Layer | Choice | Why |
|-------|--------|-----|
| Frontend | Next.js 15 + React 19 | Fast dev, SSR-ready if we add auth later |
| Backend | FastAPI | Async SSE, clean OpenAPI, Python = LangChain native |
| Orchestration | LangChain | Required; history-aware retriever + retrieval chain |
| Embeddings | OpenAI `text-embedding-3-small` | Best $/quality for short-form text at scale |
| Vector DB | Chroma (local persist) | Zero cost for demo; swap to pgvector/Pinecone in prod |
| LLM | `gpt-4o-mini` | ~20× cheaper than GPT-4o, strong enough for analytics Q&A |
| Transcripts | youtube-transcript-api + yt-dlp (+ Whisper optional) | Covers all three paths from the brief |

---

## Cost & scale (1,000 creators / day)

**Assumptions per creator:** 2 videos, ~3k transcript tokens, ~8 chat turns, 6 chunks retrieved per turn.

| Item | Est. daily @ 1k creators | Notes |
|------|--------------------------|-------|
| Embeddings (ingest once) | ~$2–4 | 3-small is $0.02/1M tokens; cache by URL hash |
| Chat (gpt-4o-mini) | ~$15–40 | Depends on turn length; cap `max_tokens` in prod |
| Vector DB | $0–50 | Chroma self-hosted = $0; Pinecone serverless ~$50 at this scale |
| yt-dlp fetch | infra | Run in queue workers; rate-limit per platform |

**Why this is the sweet spot:** Paid transcript APIs (AssemblyAI) add ~$0.15–0.30 per minute — fine for edge cases, too expensive as the default path for 2k videos/day. Whisper on CPU is cheap but slow; batch GPU workers help at 10k+/day.

**What breaks at 10k users:** Single-process Chroma + disk sessions. Mitigations:

- Move vectors to **pgvector** (one Postgres, transactional, backup-friendly)
- **Redis** for session + chat history
- **SQS/BullMQ** ingest queue so yt-dlp + embed don’t block API
- **Idempotent ingest** keyed by `hash(platform + video_id)` to skip re-embed

**Better alternative if budget is unlimited:** Gemini 1.5 Flash + Vertex vector search — slightly lower quality on nuanced hook copy, lower latency, better $ at huge token volume. I’d still keep metadata in structured SQL for exact engagement math (don’t ask the LLM to divide).

---

## Chunking trade-offs

- **500 chars, 80 overlap:** balances citation granularity vs embed API calls
- **Dedicated hook chunk (0–5s):** improves “compare hooks” without oversized retrieval noise
- **Metadata as its own document (`chunk_index: -1`):** factual Qs (followers, engagement) don’t rely on transcript similarity

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** and npm
- **yt-dlp** on PATH (`pip install yt-dlp` or `winget install yt-dlp`)
- **OpenAI API key**

---

## Setup

```bash
# 1. Clone and env
cp .env.example .env
# Edit .env — set OPENAI_API_KEY

# 2. Backend
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open **http://localhost:3000**, paste a real YouTube URL and Instagram Reel URL, click **Ingest & build index**, then use the suggested prompts or ask your own.

**Windows shortcuts:** `.\scripts\start-backend.ps1` and `.\scripts\start-frontend.ps1`

---

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness + OpenAI key configured |
| POST | `/api/ingest` | Body: `{ youtube_url, instagram_url }` |
| POST | `/api/chat/stream` | SSE: `token`, `sources`, `done`, `error` |

---

## Project layout

```
backend/app/
  main.py                 # FastAPI routes
  services/
    video_fetcher.py      # yt-dlp + youtube-transcript-api
    embeddings_store.py   # chunk, embed, Chroma
    rag_chain.py          # LangChain RAG + SSE stream
    session_store.py      # chat memory
frontend/
  app/page.tsx            # 3-column UI
  components/             # VideoCard, ChatPanel
```

---

## Submit (email reply)

1. **Project URL** — `http://localhost:3000` (or your deploy URL)  
2. **Project Description** — one paragraph: RAG chatbot comparing YouTube (A) vs Instagram Reel (B); LangChain, ChromaDB, FastAPI, Next.js; dynamic ingest, streaming chat with citations.  
3. **Loom URL** — your recording (fresh run, two real URLs, all 5 prompts + follow-up for memory)  
4. **Github repo** — `https://github.com/YOUR_USERNAME/creator-video-rag`

**Git history:** from project root run `.\scripts\make-git-history.ps1` then push.

---

## License

MIT
