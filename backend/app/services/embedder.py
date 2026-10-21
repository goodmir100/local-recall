import numpy as np
_model = None

def embed_text(text: str) -> np.ndarray | None:
    if not text.strip(): return None
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from ..core.config import settings
        # Offline-first: only load a model already present in the local cache.
        _model = SentenceTransformer(settings.embedding_model, local_files_only=True)
    return _model.encode(text[:8000], normalize_embeddings=True)
