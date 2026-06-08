from typing import List

_model = None

def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            print("[✓] Embedding model loaded")
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
    return _model

async def get_embedding(text: str) -> List[float]:
    model = _get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()