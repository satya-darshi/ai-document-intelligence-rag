import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Document
from app.services.retrieval import retrieve


BASE_DIR = Path(__file__).resolve().parents[2]
DATASET = BASE_DIR / "tests" / "eval_questions.json"


def evaluate(db: Session) -> dict:
    cases = json.loads(DATASET.read_text())
    documents = db.query(Document).filter(Document.status == "ready").all()
    if not documents:
        return {"cases": 0, "hit_rate": 0.0, "message": "No ready documents found."}

    hits = 0
    for case in cases:
        chunks = retrieve(case["question"], [document.id for document in documents], db, limit=5)
        filenames = {chunk.filename for chunk in chunks}
        if case["expected_filename"] in filenames:
            hits += 1
    return {"cases": len(cases), "hits": hits, "hit_rate": hits / len(cases) if cases else 0.0}


if __name__ == "__main__":
    with SessionLocal() as db:
        print(json.dumps(evaluate(db), indent=2))
