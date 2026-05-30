# Run checklist (technical screening)

## Install once

- Python 3.11+
- Node.js 20+ and npm
- Git
- yt-dlp: `pip install yt-dlp`

## Configure

```powershell
cd c:\Users\P. Balakistanna\Downloads\project
copy .env.example .env
```

Edit `.env` — set `OPENAI_API_KEY`.

## Terminal 1 — backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## Terminal 2 — frontend

```powershell
cd frontend
copy .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## Demo (Loom)

1. Paste public YouTube URL (Video A) + Instagram Reel URL (Video B)
2. Ingest
3. Ask all 5 suggested prompts + one follow-up question
4. Show streaming + Sources (Video A/B, chunk)
5. Explain cost/scale (see README)

## GitHub

```powershell
cd c:\Users\P. Balakistanna\Downloads\project
git remote add origin https://github.com/YOUR_USERNAME/creator-video-rag.git
git branch -M main
git push -u origin main
```

## Email reply

1. Project URL: http://localhost:3000  
2. Project Description: (see README opening paragraph)  
3. Loom URL: your link  
4. Github repo: your link  
