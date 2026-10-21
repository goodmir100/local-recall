"""Local FTS5 and semantic search with reciprocal-rank fusion."""

import numpy as np

from ..core.db import connection
from .embedder import embed_text


def hybrid_search(query: str, limit: int = 50, app: str | None = None,
                  date_from: str | None = None, date_to: str | None = None,
                  vector_only: bool = False, lexical_only: bool = False) -> list[dict]:
    query = query.strip()
    if not query:
        return []
    limit = min(max(limit, 1), 200)
    clauses, params = [], []
    if app:
        clauses.append("c.process_name LIKE ?")
        params.append(f"%{app}%")
    if date_from:
        clauses.append("c.captured_at >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("c.captured_at <= ?")
        params.append(date_to)
    filters = (" AND " + " AND ".join(clauses)) if clauses else ""
    tokens = [token.replace('"', '""') for token in query.split() if token.strip('"')]
    fts_query = " OR ".join(f'"{token}"' for token in tokens)
    select = "c.id,c.captured_at,c.process_name,c.window_title,c.ocr_text"
    with connection() as db:
        lexical = (db.execute(
            f"SELECT {select},bm25(captures_fts) AS rank FROM captures_fts "
            f"JOIN captures c ON c.id=captures_fts.rowid WHERE captures_fts MATCH ?{filters} "
            "ORDER BY rank LIMIT ?", (fts_query, *params, max(limit * 5, 100))
        ).fetchall() if fts_query and not vector_only else [])
        vectors = db.execute(
            f"SELECT {select},c.embedding FROM captures c WHERE c.embedding IS NOT NULL{filters}", params
        ).fetchall() if not lexical_only else []

    scored: dict[int, dict] = {}
    for position, row in enumerate(lexical, 1):
        item = {key: row[key] for key in ("id", "captured_at", "process_name", "window_title", "ocr_text")}
        scored[row["id"]] = {**item, "score": 1 / (60 + position), "similarity": 0.0}

    if lexical_only:
        needle = None
    else:
        try:
            needle = embed_text(query)
        except (OSError, RuntimeError, ImportError, ValueError):
            needle = None
    if needle is not None:
        matches = []
        for row in vectors:
            vec = np.frombuffer(row["embedding"], dtype=np.float32)
            if vec.shape != needle.shape or not vec.size:
                continue
            similarity = float(np.dot(needle, vec) / (np.linalg.norm(needle) * np.linalg.norm(vec) + 1e-12))
            matches.append((similarity, row))
        matches.sort(key=lambda item: item[0], reverse=True)
        for position, (similarity, row) in enumerate(matches[:max(limit * 5, 100)], 1):
            item = scored.get(row["id"])
            if item is None:
                item = {key: row[key] for key in ("id", "captured_at", "process_name", "window_title", "ocr_text")}
                item.update(score=0.0, similarity=0.0)
                scored[row["id"]] = item
            item["score"] += 1 / (60 + position)
            item["similarity"] = round(similarity, 4)

    ranked = sorted(scored.values(), key=lambda item: item["score"], reverse=True)
    return [{key: value for key, value in item.items() if key != "score"} for item in ranked[:limit]]
