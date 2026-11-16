"""
app/rag.py
RAG (Retrieval-Augmented Generation) for answering AapleSeva questions.

Retrieves top-k relevant document chunks via semantic search, then sends them
with the user question to an LLM for a grounded answer. The LLM is instructed
to cite sources by document title and page number, and to say "I don't know"
when the retrieved context does not contain an answer.

Usage:
    from app.rag import answer_question
    
    result = answer_question("What is the time limit for a caste certificate?")
    print(result["answer"])
    print(result["sources"])
"""

from __future__ import annotations

import json
from typing import Any

from app.embed import search
from app.llm import get_provider, LLMResponse


# System prompt that instructs the LLM on RAG behavior.
RAG_SYSTEM_PROMPT = """You are an assistant for the AapleSeva (Maharashtra Right to Service) portal.

Your job is to answer questions using ONLY the retrieved document excerpts provided below. Follow these rules strictly:

1. **Answer from context only**: Base your answer exclusively on the information in the retrieved documents. Do not use external knowledge.

2. **Cite your sources**: When you provide information, cite the source document by title and page number (if available). Use the format: [Document Title, page X] or [Document Title] if no page is given.

3. **Say "I don't know" when appropriate**: If the retrieved documents do not contain information to answer the question, respond with: "I don't know based on the available documents." Do NOT make up an answer or guess.

4. **Be concise and direct**: Answer in 2-4 sentences. Include only relevant information.

5. **Handle Marathi/Devanagari text**: The documents may contain Marathi text in Devanagari script. Quote or reference it accurately when needed.

Retrieved Documents:
{context}

User Question: {question}

Answer the question following the rules above. If you cite sources, list them at the end in a "Sources:" section."""


def format_context(chunks: list[dict[str, Any]]) -> str:
    """Format retrieved chunks into a numbered context block for the LLM."""
    if not chunks:
        return "(No relevant documents found)"
    
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        title = chunk.get("title", "Unknown")
        page = chunk.get("page")
        source = chunk.get("source", "")
        text = chunk.get("text", "")
        
        page_str = f", page {page}" if page else ""
        lines.append(f"[{idx}] {title}{page_str}")
        lines.append(f"Source: {source}")
        lines.append(f"Distance: {chunk.get('distance', 'N/A')}")
        lines.append(f"{text}\n")
    
    return "\n".join(lines)


def answer_question(
    question: str,
    top_k: int = 5,
    db_path: str | None = None,
    provider: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 600,
) -> dict[str, Any]:
    """
    Answer a question using RAG: retrieve relevant chunks, send to LLM.
    
    Returns a dict with:
        - question: the input question
        - answer: the LLM's response text
        - sources: list of dicts with {title, page, source, distance} for each chunk
        - retrieved_count: number of chunks retrieved
        - provider: LLM provider used
        - model: LLM model used
        - mock: whether the LLM response was mocked
    """
    # Step 1: Retrieve relevant chunks via semantic search
    chunks = search(question, db_path=db_path, n_results=top_k)
    
    # Step 2: Format context for LLM
    context = format_context(chunks)
    
    # Step 3: Build prompt with system instructions
    prompt = RAG_SYSTEM_PROMPT.format(context=context, question=question)
    
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": question},
    ]
    
    # Step 4: Call LLM
    llm = get_provider(provider=provider)
    response: LLMResponse = llm.chat(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    
    # Step 5: Extract source metadata for caller
    sources = [
        {
            "title": c.get("title", ""),
            "page": c.get("page"),
            "source": c.get("source", ""),
            "distance": c.get("distance", 0.0),
        }
        for c in chunks
    ]
    
    return {
        "question": question,
        "answer": response.text,
        "sources": sources,
        "retrieved_count": len(chunks),
        "provider": response.provider,
        "model": response.model,
        "mock": response.mock,
    }


def main():
    """CLI demo: answer a single question."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m app.rag 'Your question here'")
        return 1
    
    question = " ".join(sys.argv[1:])
    result = answer_question(question)
    
    print(f"Q: {result['question']}\n")
    print(f"A: {result['answer']}\n")
    print(f"Retrieved: {result['retrieved_count']} chunks")
    print(f"Provider: {result['provider']} / {result['model']}")
    if result['mock']:
        print("(mock mode)")
    
    if result['sources']:
        print("\nSources:")
        for src in result['sources']:
            page_str = f", page {src['page']}" if src['page'] else ""
            print(f"  - {src['title']}{page_str} [distance: {src['distance']}]")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
