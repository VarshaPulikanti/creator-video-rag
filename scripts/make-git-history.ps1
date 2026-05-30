# Run from project root after installing Git.
# Creates a linear commit history for the repo.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Install Git first: https://git-scm.com/download/win"
    exit 1
}

if (-not (Test-Path .git)) { git init }

git add .gitignore .env.example README.md
git commit -m "chore: initial repo, env template, readme" 2>$null

git add backend/requirements.txt backend/app/config.py backend/app/models/ backend/app/__init__.py
git commit -m "feat(backend): fastapi models and settings" 2>$null

git add backend/app/services/video_fetcher.py
git commit -m "feat: youtube and instagram ingest with yt-dlp" 2>$null

git add backend/app/services/embeddings_store.py backend/app/services/session_store.py
git commit -m "feat: chroma embeddings with video_id tags" 2>$null

git add backend/app/services/rag_chain.py backend/app/main.py
git commit -m "feat: langchain rag, sse stream, citations, memory" 2>$null

git add frontend/
git commit -m "feat: next.js ui with video cards and chat" 2>$null

git add scripts/
git commit -m "chore: dev startup and git helper scripts" 2>$null

Write-Host "Done. Add remote and push:"
Write-Host "  git remote add origin https://github.com/YOUR_USER/creator-video-rag.git"
Write-Host "  git branch -M main"
Write-Host "  git push -u origin main"
