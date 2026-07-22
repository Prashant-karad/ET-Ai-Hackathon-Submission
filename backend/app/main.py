from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import shutil
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from pydantic import BaseModel, Field
from pypdf import PdfReader
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
DATA_DIR = Path(os.getenv("APP_DATA_DIR", ROOT_DIR / "data"))
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DIR = DATA_DIR / "chroma"
MODEL_CACHE_DIR = DATA_DIR / "model_cache" / "all-MiniLM-L6-v2"
DB_PATH = DATA_DIR / "platform.db"
SAMPLE_DIR = ROOT_DIR / "sample_data"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MATCH_THRESHOLD = 0.45

EQUIPMENT_PATTERNS = [
    ("intake pump", "intake pump"),
    ("pump", "pump"),
    ("aeration blower", "aeration blower"),
    ("blower", "blower"),
    ("chemical dosing", "chemical dosing system"),
    ("dosing", "chemical dosing system"),
    ("clarifier", "clarifier"),
    ("filter", "filter train"),
    ("valve", "valve"),
    ("conveyor", "conveyor"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_runtime() -> None:
    for directory in (DATA_DIR, UPLOAD_DIR, CHROMA_DIR, MODEL_CACHE_DIR):
        directory.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                equipment_tag TEXT NOT NULL,
                uploaded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS expert_cards (
                id TEXT PRIMARY KEY,
                fingerprint TEXT UNIQUE NOT NULL,
                expert_name TEXT NOT NULL,
                role_experience TEXT NOT NULL,
                equipment_tag TEXT NOT NULL,
                card_text TEXT NOT NULL,
                captured_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS questions (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                asked_at TEXT NOT NULL
            );
            """
        )
        connection.commit()


def db_connection() -> sqlite3.Connection:
    ensure_runtime()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def collection() -> Any:
    ensure_runtime()
    # Chroma's default ONNX embedding function otherwise writes below Path.home(),
    # which is often protected on managed Windows accounts. Keep its model local
    # to this app's ignored runtime directory instead.
    ONNXMiniLM_L6_V2.DOWNLOAD_PATH = MODEL_CACHE_DIR
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name="knowledge_base", metadata={"hnsw:space": "cosine"}
    )


def infer_equipment_tag(text: str) -> str:
    tag = re.search(r"\b(?:P|B|M|V|PLC)[-_ ]?\d{2,4}\b", text, re.IGNORECASE)
    if tag:
        return tag.group(0).upper().replace(" ", "-")
    lowered = text.lower()
    for keyword, label in EQUIPMENT_PATTERNS:
        if keyword in lowered:
            return label
    return "general"


def chunks_for(text: str, words_per_chunk: int = 500) -> list[str]:
    words = re.findall(r"\S+", text)
    if not words:
        return []
    return [" ".join(words[index : index + words_per_chunk]) for index in range(0, len(words), words_per_chunk)]


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")
    if suffix == ".csv":
        rows = csv.reader(io.StringIO(content.decode("utf-8", errors="replace")))
        return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)
    if suffix == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
            if extracted.strip():
                return extracted
        except Exception:
            pass
        # A narrow recovery path for older/simple PDFs with readable text operators.
        recovered = "\n".join(re.findall(r"\(([^()]*)\)\s*Tj", content.decode("latin-1", errors="ignore")))
        if recovered.strip():
            return recovered
        raise HTTPException(status_code=422, detail="The PDF could not be read as text.")
    raise HTTPException(status_code=415, detail="Only .txt, .csv, and .pdf files are supported.")


def ingest_content(filename: str, content: bytes, persist_file: bool = True) -> dict[str, Any]:
    text = extract_text(filename, content).strip()
    if not text:
        raise HTTPException(status_code=422, detail="No readable text was found in this file.")
    chunks = chunks_for(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="The file did not contain enough text to index.")
    document_id = str(uuid.uuid4())
    uploaded_at = now_iso()
    equipment_tag = infer_equipment_tag(f"{filename} {text[:4000]}")
    source_name = Path(filename).name
    file_type = Path(filename).suffix.lower().lstrip(".")
    if persist_file:
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", source_name)
        (UPLOAD_DIR / f"{document_id}_{safe_name}").write_bytes(content)
    metadata = [
        {
            "source_name": source_name,
            "doc_type": "document",
            "equipment_tag": equipment_tag,
            "upload_date": uploaded_at,
            "record_id": document_id,
        }
        for _ in chunks
    ]
    collection().add(
        ids=[f"document-{document_id}-{index}" for index in range(len(chunks))],
        documents=chunks,
        metadatas=metadata,
    )
    with closing(db_connection()) as connection:
        connection.execute(
            "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
            (document_id, source_name, file_type, len(chunks), equipment_tag, uploaded_at),
        )
        connection.commit()
    return {
        "id": document_id,
        "source_name": source_name,
        "file_type": file_type,
        "chunk_count": len(chunks),
        "equipment_tag": equipment_tag,
        "uploaded_at": uploaded_at,
    }


class KnowledgeInput(BaseModel):
    expert_name: str = Field(min_length=2, max_length=120)
    role_experience: str = Field(min_length=2, max_length=240)
    equipment: str = Field(min_length=2, max_length=200)
    common_problem: str = Field(min_length=2, max_length=2000)
    first_check: str = Field(min_length=2, max_length=2000)
    root_cause: str = Field(min_length=2, max_length=2000)
    fix_workaround: str = Field(min_length=2, max_length=3000)
    junior_mistake: str = Field(min_length=2, max_length=2000)
    warning_sign: str = Field(default="", max_length=2000)


class SaveKnowledgeInput(KnowledgeInput):
    card_text: str = Field(min_length=20, max_length=12000)


class AskInput(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


def card_prompt(values: KnowledgeInput) -> str:
    answers_json = json.dumps(values.model_dump(), indent=2)
    return f'''You are helping preserve expert industrial knowledge before an experienced worker retires. Turn these short answers into a clean, well-structured 'Knowledge Card' in plain professional language. Keep it factual, don't invent details not implied by the answers. Format as:

Equipment: [equipment]
Issue Pattern: [expand from common_problem]
Root Cause: [expand from root_cause]
Expert Fix: [expand from fix_workaround]
Common Mistake to Avoid: [expand from junior_mistake]
Warning Signs: [expand from warning_sign, or 'Not specified' if empty]
Contributed by: [expert_name], [role]

Raw answers: {answers_json}'''


def local_card(values: KnowledgeInput) -> str:
    warning = values.warning_sign.strip() or "Not specified"
    return "\n".join(
        [
            f"Equipment: {values.equipment.strip()}",
            f"Issue Pattern: {values.common_problem.strip()}",
            f"Root Cause: {values.root_cause.strip()}",
            f"Expert Fix: {values.fix_workaround.strip()}",
            f"Common Mistake to Avoid: {values.junior_mistake.strip()}",
            f"Warning Signs: {warning}",
            f"Contributed by: {values.expert_name.strip()}, {values.role_experience.strip()}",
        ]
    )


def groq_completion(prompt: str, system: str) -> str | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    try:
        response = Groq(api_key=api_key).chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            temperature=0.2,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        return None


def source_payload(metadata: dict[str, Any], distance: float, index: int) -> dict[str, Any]:
    score = max(0.0, min(1.0, 1 - float(distance)))
    return {
        "citation": f"S{index}",
        "source_name": metadata.get("source_name", "Unknown source"),
        "doc_type": metadata.get("doc_type", "document"),
        "equipment_tag": metadata.get("equipment_tag", "general"),
        "score": round(score, 3),
    }


def local_answer(question: str, contexts: list[dict[str, Any]]) -> str:
    lines = ["Local retrieval mode — the following stored evidence is most relevant to your question:"]
    for item in contexts:
        label = "Expert knowledge" if item["source"]["doc_type"] == "expert_knowledge" else "Document excerpt"
        excerpt = item["text"].replace("\n", " ").strip()
        lines.append(f"\n{label} [{item['source']['citation']}]: {excerpt[:650]}")
    return "\n".join(lines)


def existing_document(source_name: str) -> bool:
    with closing(db_connection()) as connection:
        return connection.execute("SELECT 1 FROM documents WHERE source_name = ? LIMIT 1", (source_name,)).fetchone() is not None


app = FastAPI(title="Industrial Knowledge Intelligence Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    ensure_runtime()


@app.get("/api/dashboard")
def dashboard() -> dict[str, int]:
    with closing(db_connection()) as connection:
        documents = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        cards = connection.execute("SELECT COUNT(*) FROM expert_cards").fetchone()[0]
        questions = connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
    return {"documents": documents, "cards": cards, "questions": questions}


@app.get("/api/documents")
def list_documents() -> list[dict[str, Any]]:
    with closing(db_connection()) as connection:
        rows = connection.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or Path(file.filename).suffix.lower() not in {".txt", ".csv", ".pdf"}:
        raise HTTPException(status_code=415, detail="Choose a .txt, .csv, or .pdf file.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Files must be 10 MB or smaller.")
    return ingest_content(file.filename, content)


@app.post("/api/knowledge/generate")
def generate_knowledge(values: KnowledgeInput) -> dict[str, str]:
    generated = groq_completion(
        card_prompt(values),
        "You format practical industrial knowledge accurately and never add facts beyond the supplied answers.",
    )
    return {"card_text": generated or local_card(values), "mode": "groq" if generated else "local"}


@app.post("/api/knowledge/save")
def save_knowledge(values: SaveKnowledgeInput) -> dict[str, Any]:
    fingerprint = hashlib.sha256(
        f"{values.expert_name}|{values.equipment}|{values.card_text}".encode("utf-8")
    ).hexdigest()
    with closing(db_connection()) as connection:
        found = connection.execute("SELECT id FROM expert_cards WHERE fingerprint = ?", (fingerprint,)).fetchone()
        if found:
            return {"id": found["id"], "saved": False, "message": "This knowledge card has already been saved."}
    card_id = str(uuid.uuid4())
    captured_at = now_iso()
    equipment_tag = infer_equipment_tag(values.equipment) if infer_equipment_tag(values.equipment) != "general" else values.equipment.strip()
    collection().add(
        ids=[f"card-{card_id}"],
        documents=[values.card_text.strip()],
        metadatas=[
            {
                "source_name": values.expert_name.strip(),
                "doc_type": "expert_knowledge",
                "equipment_tag": equipment_tag,
                "role": values.role_experience.strip(),
                "captured_date": captured_at,
                "record_id": card_id,
            }
        ],
    )
    with closing(db_connection()) as connection:
        connection.execute(
            "INSERT INTO expert_cards VALUES (?, ?, ?, ?, ?, ?, ?)",
            (card_id, fingerprint, values.expert_name.strip(), values.role_experience.strip(), equipment_tag, values.card_text.strip(), captured_at),
        )
        connection.commit()
    return {"id": card_id, "saved": True, "message": "Knowledge card saved to the unified knowledge base."}


@app.post("/api/ask")
def ask_question(request: AskInput) -> dict[str, Any]:
    with closing(db_connection()) as connection:
        connection.execute("INSERT INTO questions VALUES (?, ?, ?)", (str(uuid.uuid4()), request.question, now_iso()))
        connection.commit()
    store = collection()
    if store.count() == 0:
        return {"answer": "No knowledge has been added yet. Upload a document or capture expert knowledge first.", "sources": [], "best_match_score": 0, "no_strong_match": True, "mode": "local"}
    results = store.query(query_texts=[request.question], n_results=min(5, store.count()), include=["documents", "metadatas", "distances"])
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    contexts = []
    for index, (text, metadata, distance) in enumerate(zip(documents, metadatas, distances), start=1):
        contexts.append({"text": text, "source": source_payload(metadata, distance, index)})
    best_score = contexts[0]["source"]["score"] if contexts else 0
    sources = [item["source"] for item in contexts]
    rendered_context = "\n\n".join(
        f"[{item['source']['citation']}] {item['source']['doc_type']} — {item['source']['source_name']}\n{item['text']}"
        for item in contexts
    )
    prompt = f'''You are an industrial knowledge assistant. Answer the question using ONLY the provided context below. If the context includes expert knowledge cards, clearly distinguish them from document excerpts in your answer. Cite which source each part of your answer came from using the supplied [S#] markers. If the context doesn't contain a relevant answer, say so clearly and suggest the user submit this as a new expert knowledge entry.

Context: {rendered_context}

Question: {request.question}'''
    generated = groq_completion(prompt, "Give concise, operationally useful answers. Never cite a source that is not provided.")
    return {
        "answer": generated or local_answer(request.question, contexts),
        "sources": sources,
        "best_match_score": best_score,
        "no_strong_match": best_score < MATCH_THRESHOLD,
        "mode": "groq" if generated else "local",
    }


@app.post("/api/demo/seed")
def seed_demo() -> dict[str, Any]:
    added_documents = 0
    for source in sorted(SAMPLE_DIR.glob("*")):
        if source.suffix.lower() not in {".txt", ".csv", ".pdf"} or existing_document(source.name):
            continue
        ingest_content(source.name, source.read_bytes(), persist_file=False)
        added_documents += 1
    demo_cards = [
        {
            "expert_name": "Maya Patel",
            "role_experience": "Senior Mechanical Technician, 18 years",
            "equipment": "Raw Water Intake Pump P-101",
            "common_problem": "Repeated low-flow alarms during hot weather despite the motor running at normal speed.",
            "first_check": "Check the suction strainer differential pressure and compare suction pressure with the operator log.",
            "root_cause": "Debris loading on the strainer and air entering through a worn suction-side gasket can reduce net positive suction head.",
            "fix_workaround": "Isolate and clean the strainer, replace leaking gasket material, prime the casing, then restart while watching suction pressure.",
            "junior_mistake": "Increasing speed before checking suction conditions, which worsens cavitation.",
            "warning_sign": "A crackling sound at the casing and fluctuating discharge pressure before the alarm occurs.",
        },
        {
            "expert_name": "Daniel Okoro",
            "role_experience": "Reliability Engineer, 14 years",
            "equipment": "Aeration Blower B-201",
            "common_problem": "Increasing vibration after a filter change or seasonal temperature swing.",
            "first_check": "Confirm inlet filter seating and compare vibration at both bearing housings before adjusting controls.",
            "root_cause": "An unevenly seated filter or loose coupling guard can create inlet restriction or a false vibration reading.",
            "fix_workaround": "Reseat the filter, inspect coupling hardware, and trend vibration after a controlled restart.",
            "junior_mistake": "Changing the variable-speed drive setting before verifying the mechanical installation.",
            "warning_sign": "A steady rise in inlet differential pressure paired with a new tonal vibration.",
        },
    ]
    added_cards = 0
    for raw in demo_cards:
        values = SaveKnowledgeInput(**raw, card_text=local_card(KnowledgeInput(**raw)))
        result = save_knowledge(values)
        if result["saved"]:
            added_cards += 1
    return {"message": "Demo data is ready.", "documents_added": added_documents, "cards_added": added_cards}
