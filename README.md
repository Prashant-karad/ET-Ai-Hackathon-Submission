# Plant Knowledge Desk

> A local-first industrial knowledge intelligence platform that turns operating documents and experienced engineers’ practical insight into one searchable knowledge base.

Plant Knowledge Desk preserves the things that are usually hard to capture: the first check an experienced technician makes, the failure pattern they recognise, the shortcut they trust, and the mistake they know to avoid. It keeps this expert knowledge beside manuals, logs, and procedures—then makes both available through a cited question-and-answer experience.

## Why this project matters

Industrial teams often have two separate sources of truth:

- formal documents that explain the intended process;
- experienced people who know what actually happens when equipment starts to fail.

When experienced workers move on, their diagnostic judgement can disappear with them. This project provides a focused workflow to capture that judgement in a structured, reviewable form, then retrieve it alongside the original operational documentation.

## Product highlights

| Capability | What it delivers |
| --- | --- |
| **Document ingestion** | Upload `.txt`, `.csv`, and text-based `.pdf` files. Content is chunked into approximately 500-word passages and indexed locally. |
| **Expert knowledge capture** | A calm nine-step handover wizard gathers one practical answer at a time and generates an editable Knowledge Card. |
| **Unified retrieval** | Document passages and expert cards are embedded in the same Chroma collection and retrieved together. |
| **Cited answers** | Every answer identifies its source material and clearly distinguishes `📄 Document` evidence from `🧠 Expert knowledge`. |
| **Local-first resilience** | With Groq configured, the app generates refined cards and answer synthesis. Without a key, deterministic local fallback mode keeps the core workflow usable. |
| **Demo-ready data** | Detailed water-treatment documentation and expert scenarios are included for a credible end-to-end demonstration. |

## How the knowledge flow works

```text
Operating manuals / logs / procedures ─┐
                                       ├─► Local Chroma knowledge base ─► Cited answer
Experienced engineer capture wizard ──┘
             │
             └─► Reviewed Knowledge Card
```

1. **Ingest** a document or capture field experience.
2. **Review** generated expert knowledge before it becomes permanent.
3. **Store** all searchable content in one persistent local vector collection.
4. **Ask** operational questions and inspect the cited supporting sources.

## Core user journey

### 1. Ingest trusted documents

The **Ingest Documents** tab accepts `.txt`, `.csv`, and `.pdf` files up to 10 MB. The backend extracts text, splits it into approximately 500-word chunks, detects an equipment tag where possible, and stores each chunk with source metadata.

### 2. Capture practical engineering knowledge

The **Capture Expert Knowledge** tab is the primary workflow. It intentionally asks one question at a time so the experience feels like an engineering handover—not a chatbot.

The wizard captures:

1. Expert name
2. Role and experience
3. Equipment or asset
4. Common failure pattern
5. First diagnostic check
6. Typical root cause
7. Fix or workaround
8. Common junior mistake
9. Optional early warning sign

The resulting Knowledge Card remains editable until the user selects **Confirm & save card**. Duplicate saves are safely handled as idempotent operations.

### 3. Ask a question

The **Ask** tab retrieves the five closest matches across both document and expert sources. It presents a cited answer and a source panel with match confidence. If the knowledge base has no strong match, the UI directs the user back to expert capture.

## Technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, Tailwind CSS |
| Backend | Python, FastAPI, Pydantic |
| Operational data | SQLite |
| Vector search | ChromaDB with Chroma’s default local embedding function |
| Optional LLM | Groq (`llama-3.3-70b-versatile`) |
| Document extraction | `pypdf`, Python standard-library CSV/text handling |

## Repository layout

```text
.
├── backend/
│   ├── app/main.py              # FastAPI application and knowledge services
│   ├── sample_data/             # Version-controlled water-treatment demo sources
│   ├── tests/                   # Backend unit tests
│   └── requirements.txt
├── frontend/
│   └── src/                     # React single-page application
├── .env.example                 # Safe environment-variable template
├── .gitignore                   # Excludes secrets, local data, dependencies, and caches
├── pytest.ini                   # Isolated test configuration
└── README.md
```

## Quick start

### Prerequisites

- Python 3.11+ with `venv` available
- Node.js 20+
- Optional: a Groq API key for LLM-generated cards and synthesized answers

### 1. Create the virtual environment and install backend packages

From the repository root, use the Python executable available on your machine:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
Copy-Item .\.env.example .\backend\.env
```

If you use Anaconda, substitute its Python path when creating the environment:

```powershell
& 'C:\Users\prash\anaconda3\python.exe' -m venv .venv
```

The commands deliberately call `.venv\Scripts\python.exe` directly, so they work even if PowerShell blocks activation scripts.

### 2. Configure Groq — optional

Edit `backend/.env`:

```dotenv
GROQ_API_KEY=your_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

Never commit this file. If no key is configured, the application remains functional in **Local retrieval mode**.

### 3. Install frontend packages

```powershell
cd .\frontend
npm install
cd ..
```

### 4. Run the application

Open two terminals.

**Terminal 1 — FastAPI**

```cmd
cd /d "C:\Users\prash\Downloads\ET AI submission\backend"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — React app**

```cmd
cd /d "C:\Users\prash\Downloads\ET AI submission\frontend"
npm.cmd run dev
```

Open the Vite URL shown in the terminal—normally [http://localhost:5173](http://localhost:5173).

## Demo script

The fastest demo uses **Load demo data** in the application header. It adds sample documents and two expert knowledge cards only once, so the action is safe to repeat.

For a stronger video demonstration, upload the included files manually through **Ingest Documents**:

- `backend/sample_data/raw_water_intake_pump_manual.txt`
- `backend/sample_data/chemical_dosing_shift_log.csv`
- `backend/sample_data/aeration_blower_maintenance.pdf`

Then ask these questions:

```text
What should I check first for a P-101 low-flow alarm?
```

```text
What should I inspect when Aeration Blower B-201 vibration rises after a filter change?
```

```text
What caused the high discharge pressure alarm on the alum dosing pump?
```

For the expert-capture portion of the demo, create a card for **Raw Water Intake Pump P-101** using a low-flow pattern, a suction-strainer first check, and cavitation warning signs. Then ask:

```text
What do experienced technicians recommend before increasing P-101 speed during low flow?
```

The result should visibly demonstrate both `📄` document evidence and `🧠` expert guidance.

## API surface

| Endpoint | Purpose |
| --- | --- |
| `GET /api/dashboard` | Returns document, expert-card, and question counts. |
| `GET /api/documents` | Lists ingested document records. |
| `POST /api/documents/upload` | Uploads and indexes one supported document. |
| `POST /api/knowledge/generate` | Produces a reviewable Knowledge Card draft. |
| `POST /api/knowledge/save` | Saves a confirmed expert card to SQLite and Chroma. |
| `POST /api/ask` | Retrieves unified matches and produces a cited answer. |
| `POST /api/demo/seed` | Loads the bundled demo sources and cards idempotently. |

## Testing and build verification

Run backend tests from the repository root:

```cmd
.venv\Scripts\python.exe -m pytest -q
```

Build the production frontend:

```cmd
cd frontend
npm.cmd run build
```

## Local data and security

The following are intentionally excluded from Git:

- `backend/.env` and API keys
- `.venv/` and `frontend/node_modules/`
- SQLite records, Chroma vectors, uploaded files, and local model cache under `backend/data/`

On the first indexing operation, Chroma downloads its default embedding model once and stores it in `backend/data/model_cache/`. Keep an internet connection available for that initial download; future indexing and retrieval use the cached local model.

## Troubleshooting

| Situation | Resolution |
| --- | --- |
| PowerShell blocks `Activate.ps1` | Use `.venv\Scripts\python.exe` directly, as shown above. |
| First ingest appears slow | Chroma is downloading its local embedding model. Leave the first indexing action running. |
| No Groq key available | Continue in Local retrieval mode; ingestion, capture, saving, and search still work. |
| Port 8000 or 5173 is already in use | Stop the previous process or select another port and update `VITE_API_URL` accordingly. |
| Upload rejected | Confirm it is `.txt`, `.csv`, or text-based `.pdf`, is 10 MB or less, and contains extractable text. |

## GitHub-ready by design

The repository includes a configured `.gitignore`, dependency manifests, synthetic demo data, tests, and reproducible local run instructions. It is safe to commit and share without exposing local knowledge-base records or secrets.

---

Built to help industrial teams turn hard-won experience into durable, searchable operational knowledge.
