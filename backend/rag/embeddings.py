"""Embedding generation for Armenian text"""

import os
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        # all-MiniLM-L6-v2 supports 100+ languages including Armenian
        _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    return _model

async def get_embedding(text: str) -> List[float]:
    """Generate embedding for text"""
    model = get_model()
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()

async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Batch embedding generation"""
    model = get_model()
    embeddings = model.encode(texts, convert_to_numpy=True)
    return embeddings.tolist()
