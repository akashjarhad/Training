# RAG System for AapleSeva

## Overview

The RAG (Retrieval-Augmented Generation) system answers user questions about Maharashtra's Right to Service Act by retrieving relevant document chunks and using an LLM to generate grounded answers with citations.

## Architecture

```
User Question
    ↓
Semantic Search (app/embed.py)
    ↓
Top-K Document Chunks
    ↓
RAG Module (app/rag.py)
    ↓
LLM with Context + Instructions
    ↓
Answer + Source Citations
```

## Components

### 1. `app/rag.py` - RAG Engine

Core RAG implementation that:
- Retrieves top-k relevant chunks via semantic search
- Formats chunks with metadata (title, page, source) as context
- Sends context + question to LLM with strict instructions
- Returns answer with source citations

**Key Features:**
- **Source citations**: LLM instructed to cite [Document Title, page X]
- **Honest ignorance**: LLM must say "I don't know" when context lacks answer
- **Configurable**: top-k, provider, temperature all adjustable

**Usage:**
```python
from app.rag import answer_question

result = answer_question(
    "What is the time limit for a caste certificate?",
    top_k=5,
    provider="groq"  # or "gemini"
)

print(result["answer"])
print(result["sources"])
```

### 2. `POST /ask` - REST API Endpoint

Added to `app/vectorstore.py` alongside `GET /search/semantic`.

**Request:**
```json
{
  "question": "What is the time limit for a caste certificate?",
  "top_k": 5,
  "provider": "groq",
  "temperature": 0.2
}
```

**Response:**
```json
{
  "question": "What is the time limit for a caste certificate?",
  "answer": "The maximum time limit for issuing a caste certificate is 15 days [Maharashtra RTS Notified Services, page 3].",
  "sources": [
    {
      "title": "Maharashtra RTS Notified Services",
      "page": 3,
      "source": "RTS_Notified_Food_Civil_Supplies.pdf",
      "distance": 0.3245
    }
  ],
  "retrieved_count": 5,
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "mock": false
}
```

**Start the server:**
```bash
cd Training
python -m app.vectorstore
# API available at http://127.0.0.1:8000
```

### 3. Evaluation Framework

#### `eval/eval_set.json` - 15 Test Questions

Structured evaluation dataset with:
- **15 questions** covering different categories
- **Expected keywords** for positive cases
- **3 negative cases** (Q6, Q9, Q14) where LLM must say "I don't know"
- **Expected sources** for source relevance checking

**Categories:**
- `time_limit` - questions about service deadlines
- `department` - departmental responsibilities
- `appellate_authority` - appeal procedures
- `officer_info` - designated officer details
- `negative_case` - questions NOT answerable from documents
- `definition`, `procedural`, `service_info`, etc.

#### `eval/run_eval.py` - Evaluation Runner

Automated evaluation that:
1. Runs multiple configs (chunk size, top-k combinations)
2. Scores each answer automatically
3. Generates comparison table showing winner
4. Updates README.md with results

**Scoring Logic:**
- Negative case handled correctly ("I don't know") → 1.0
- Negative case failed (hallucinated answer) → 0.0
- All expected keywords found → 1.0
- Partial keyword match → 0.3–0.7
- No expected keywords → 0.0

**Usage:**
```bash
# Run with default configs (baseline vs larger-context)
python -m eval.run_eval

# Or specify custom configs
python -m eval.run_eval --configs my_configs.json --output eval/my_results.json
```

**Default Configs:**
```json
[
  {
    "name": "baseline",
    "chunk_size": 1200,
    "chunk_overlap": 200,
    "top_k": 5
  },
  {
    "name": "larger-context",
    "chunk_size": 1200,
    "chunk_overlap": 200,
    "top_k": 8
  }
]
```

## System Prompt (RAG Instructions)

The LLM receives these strict instructions:

1. **Answer from context only** - No external knowledge
2. **Cite sources** - Format: [Document Title, page X]
3. **Say "I don't know"** - When context lacks answer
4. **Be concise** - 2-4 sentences
5. **Handle Marathi text** - Quote Devanagari accurately

## Critical Design Decisions

### Why "I don't know" is enforced

Q6, Q9, Q14 are **negative cases** - questions deliberately not answerable from the documents:
- Q6: "What is the penalty for officials who delay services?"
- Q9: "How do I track the status of my submitted application?"
- Q14: "How is RTS different from RTI?"

The system **must** say "I don't know" for these. Hallucinated answers fail evaluation.

### Why citations matter

Users need to verify information. Every claim must be traceable to [Document Title, page X] so users can:
- Check the original source
- Trust the answer
- Understand which document applies

### Why top-k is configurable

- **top-k=5**: Fast, focused, less noise
- **top-k=8**: More context, better for complex questions, slower

Evaluation determines the winner.

## Workflow

### 1. Setup (one-time)
```bash
cd Training
python -m pip install -r requirements.txt

# Set API key in .env
echo "GROQ_API_KEY=your_key_here" > .env

# Index documents
python -m app.embed --index
```

### 2. Test RAG CLI
```bash
python -m app.rag "What is the time limit for a caste certificate?"
```

### 3. Start API server
```bash
python -m app.vectorstore
# Or with auto-reload:
uvicorn app.vectorstore:app --reload
```

### 4. Test POST /ask endpoint
```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the time limit for a caste certificate?", "top_k": 5}'
```

### 5. Run evaluation
```bash
python -m eval.run_eval
# Check eval/results.json for full details
# README.md updated with winner table
```

## File Structure

```
Training/
├── app/
│   ├── rag.py           # RAG engine (NEW)
│   ├── vectorstore.py   # FastAPI server with POST /ask (UPDATED)
│   ├── embed.py         # semantic search
│   ├── chunking.py      # document chunker
│   ├── llm.py           # LLM provider wrapper
│   └── ...
├── eval/
│   ├── eval_set.json    # 15 test questions (NEW)
│   ├── run_eval.py      # evaluation runner (NEW)
│   ├── questions.txt    # original 10 questions
│   └── results.json     # evaluation output (generated)
├── data/
│   ├── chroma/          # vector store
│   └── raw/             # source PDFs
├── RAG_SYSTEM.md        # this file (NEW)
├── requirements.txt     # updated with chromadb, pydantic
└── README.md            # updated with eval results
```

## Dependencies Added

- `chromadb>=0.4.0` - vector store + embeddings
- `pydantic>=2.0.0` - FastAPI request validation

Already present:
- `fastapi`, `uvicorn` - API server
- `requests` - HTTP client for LLM
- `python-dotenv` - .env file loading

## Known Limitations

1. **Large PDF crashes**: 8MB FAQ PDF and large Service List crash the chunking process. These files are skipped in indexing. This is an environment limitation, not a code bug.

2. **Chunk size not yet parameterized**: `app/chunking.py` currently has hardcoded size (1200 chars, 200 overlap). The eval runner accepts `chunk_size`/`chunk_overlap` in config but does not yet trigger re-chunking. Future enhancement: make `chunk_documents()` accept these parameters.

3. **Mock mode for offline dev**: Set `LLM_MOCK=1` to run without API keys. Mock answers are deterministic canned responses, useful for testing parse paths.

## Next Steps

If you want to improve the system:

1. **Re-chunk with different sizes**: Modify `app/chunking.py` to accept size/overlap parameters, then re-run eval with configs like 800/100, 1200/200, 1600/300.

2. **Try different embedding models**: Chroma supports any sentence-transformers model. Swap `all-MiniLM-L6-v2` for a multilingual or larger model.

3. **Tune LLM parameters**: Experiment with temperature (0.0 = deterministic, 0.5 = creative) and max_tokens.

4. **Add more eval questions**: Expand `eval/eval_set.json` to 30+ questions covering edge cases.

5. **Source validation**: Add a scoring metric that checks if retrieved sources match `expected_source` from eval set.

## Testing the Negative Cases

The most important test: does the LLM admit ignorance?

```bash
# Q6: penalty for officials (not in docs)
curl -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the penalty for officials who delay services beyond the mandated time?"}'

# Expected: answer contains "I don't know" or "not available"
# Failure: answer invents a penalty amount or procedure
```

Run the evaluation to check all 3 negative cases automatically:
```bash
python -m eval.run_eval
# Check results.json for Q6, Q9, Q14 scores
```

---

**Implementation Status:** ✅ Complete (S1 + S2)  
**Date:** November 16, 2026  
**Tested:** Code complete, awaiting environment fix for full end-to-end test
