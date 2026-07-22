# Plant Knowledge Desk

A local full-stack industrial knowledge platform for preserving expert field knowledge and searching it alongside operating documents. It is deliberately built as a calm engineering workspace rather than a generic chat interface.

## What it does

- Ingests `.txt`, `.csv`, and text-based `.pdf` documents into a persistent local Chroma knowledge base.
- Captures operational experience through a nine-step, one-question-at-a-time expert wizard.
- Produces an editable Knowledge Card before it is saved and makes accidental duplicate saves idempotent.
- Searches both document chunks and confirmed expert cards together, with source labels and citations.
- Uses Groq when configured, while preserving a fully working, clearly labelled local fallback mode when it is not.
- Includes detailed water-treatment demo files and a one-click demo seed action.

## Prerequisites

- Python 3.11 or newer (with `venv` available)
- Node.js 20 or newer
- Optional: a Groq API key for generated cards and synthesized answers

## First-time setup

Open PowerShell in the repository root. Create and activate the Python virtual environment **first**:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
Copy-Item .\.env.example .\backend\.env
```

Edit `backend/.env` and set `GROQ_API_KEY` only if Groq mode is required. Do not put a key in source code or commit this file.

On the first document or card indexing action, Chroma downloads its default local embedding model once. It is cached in `backend/data/model_cache/` and is ignored by Git. Keep an internet connection available for that first index; later searches work from the local cache.

Install the frontend packages:

```powershell
cd .\frontend
npm install
cd ..
```

## Run locally

Use two PowerShell terminals, both with the virtual environment activated where applicable.

**Terminal 1 — API**

```powershell
.\.venv\Scripts\Activate.ps1
cd .\backend
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — web app**

```powershell
cd .\frontend
npm run dev
```

Open the URL printed by Vite, normally `http://localhost:5173`.

## Demonstrate the complete flow

1. Select **Load demo data** in the app header.
2. In **Ask**, try: `What should I check first for a P-101 low-flow alarm?`
3. Verify that the sources include both a document and expert card when applicable.
4. Open **Capture Expert Knowledge** and complete the nine short prompts.
5. Review/edit the Knowledge Card, then select **Confirm & save card**.
6. Ask a question using the newly captured asset or failure pattern.

You can alternatively upload the bundled source files manually from `backend/sample_data/`.

## Tests and production build

```powershell
.\.venv\Scripts\Activate.ps1
$env:PYTHONPATH = (Resolve-Path .\backend)
pytest .\backend\tests -q

cd .\frontend
npm run build
```

## Data and Git safety

The following stay local and are ignored by Git: API keys, virtual environments, uploaded files, SQLite data, and Chroma vector data. The tracked synthetic demo files contain no credentials or real plant data.

Before pushing, review the working tree:

```powershell
git status
git add .
git commit -m "Build Plant Knowledge Desk"
git remote add origin <your-github-repository-url>
git push -u origin main
```

If a Groq key was ever pasted into a public location, revoke it in Groq and create a replacement before use.
