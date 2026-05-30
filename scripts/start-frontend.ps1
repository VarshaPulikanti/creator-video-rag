# Start Next.js frontend (run from project root)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location "$root\frontend"

if (-not (Test-Path "node_modules")) {
    npm install
}

npm run dev
