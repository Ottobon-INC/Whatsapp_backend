# rag.py
import os

import supabase_client  # ensures .env is loaded once
from openai import OpenAI

EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise Exception("OPENAI_API_KEY missing")

client = OpenAI(api_key=_api_key)


def generate_embedding(text: str):
    """
    Converts text into a 1536-dimensional embedding vector using OpenAI.
    """
    cleaned = text.strip().replace("\n", " ")

    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=cleaned
    )

    return resp.data[0].embedding


def generate_embeddings_batch(texts: list) -> list:
    """
    Converts a list of texts into embedding vectors using OpenAI's batch API.
    More efficient than calling generate_embedding() individually for each text.
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors (each 1536 dimensions)
    """
    if not texts:
        return []
    
    # Clean all texts
    cleaned_texts = [text.strip().replace("\n", " ") for text in texts]
    
    # OpenAI embeddings API accepts a list of inputs
    resp = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=cleaned_texts
    )
    
    # Return embeddings in the same order as input texts
    return [item.embedding for item in resp.data]
