import os
import chromadb
from groq import Groq
from typing import List, Optional
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data"
COLLECTION_PREFIX = "video_"
MODEL_NAME = "llama-3.1-8b-instant"

_client: Optional[chromadb.Client] = None

def get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set")
    return Groq(api_key=api_key)

def get_chroma_client():
    """Get or create ChromaDB client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(DATA_DIR / "chroma"))
    return _client

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Split text into overlapping chunks."""
    chunks = []
    words = text.split()

    for i in range(0, len(words), chunk_size - overlap):
        chunk = ' '.join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)

    return chunks

def index_transcript(video_id: str, transcript: str):
    """Index transcript chunks in ChromaDB for retrieval."""
    client = get_chroma_client()
    collection_name = f"{COLLECTION_PREFIX}{video_id}"

    try:
        client.delete_collection(collection_name)
    except:
        pass

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    chunks = chunk_text(transcript)

    if not chunks:
        return

    collection.add(
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        metadatas=[{"chunk_index": i} for i in range(len(chunks))]
    )

def retrieve_context(video_id: str, question: str, n_results: int = 3) -> List[str]:
    """Retrieve relevant context chunks for a question."""
    client = get_chroma_client()
    collection_name = f"{COLLECTION_PREFIX}{video_id}"

    try:
        collection = client.get_collection(collection_name)
    except:
        return []

    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )

    return results['documents'][0] if results['documents'] else []

def answer_question(video_id: str, question: str, title: str = "") -> dict:
    """Answer a question about the video using RAG."""

    context_chunks = retrieve_context(video_id, question)

    if not context_chunks:
        return {
            'answer': "I don't have enough context to answer this question. Please process the video first.",
            'relevant_context': []
        }

    context = "\n\n".join(context_chunks)

    client = get_groq_client()

    prompt = f"""You are a helpful assistant answering questions about a video.

Video Title: {title}

Relevant Context from the video transcript:
{context}

Question: {question}

Please answer the question based ONLY on the context provided above. If the answer cannot be found in the context, say "I couldn't find information about that in this video."

Answer:"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=1000,
    )

    return {
        'answer': response.choices[0].message.content,
        'relevant_context': context_chunks
    }

def cleanup_index(video_id: str):
    """Remove video index from ChromaDB."""
    client = get_chroma_client()
    collection_name = f"{COLLECTION_PREFIX}{video_id}"

    try:
        client.delete_collection(collection_name)
    except:
        pass
