# DocMind

DocMind is a document question-answering backend built with FastAPI, PostgreSQL, and pgvector.

It provides a backend flow for document upload, text extraction, chunking, embedding generation, vector retrieval, and answer generation with an LLM.

## Current scope

The current public version focuses on text-based document QA.

Included today:
- document upload
- text extraction and chunking
- embedding generation
- vector retrieval with pgvector
- answer generation with an LLM
- basic conversation follow-up handling
- basic async tests for selected application paths

Planned next steps:
- multimodal parsing
- table and image-aware extraction
- stronger citation grounding
- retrieval quality improvements
- production hardening

## Current status

This repository should be viewed as an MVP backend, not a production-ready system.

What it is good for:
- showing backend architecture and module boundaries
- demonstrating a document QA request flow end to end
- iterating on retrieval and answer generation logic

What it is not yet:
- a fully productionized document intelligence platform
- a complete multimodal document parser
- a benchmarked retrieval system with formal offline evaluation

## Architecture overview

A simplified view of the backend layout:

```text
backend/
├── app/
│   ├── api/
│   ├── application/
│   ├── core/
│   ├── db/
│   ├── domains/
│   ├── infrastructure/
│   ├── models/
│   └── main.py
├── migrations/
├── tests/
├── pyproject.toml
├── poetry.lock
└── requirements.txt
```

## Design notes

- API, retrieval, and answer generation are separated into different modules.
- The embedding provider can be switched without changing the main request flow.
- The current implementation favors readability and iteration speed over optimization.
- The repository is intentionally scoped as an MVP backend.

## Core flow

The current request flow is:

1. upload a document
2. extract text content
3. chunk the extracted content
4. generate embeddings
5. store chunks and vectors in PostgreSQL + pgvector
6. retrieve relevant chunks for a query
7. generate an answer using retrieved context
8. return the answer with supporting context metadata

The current implementation is best described as:

**a text-based RAG backend for document QA**

## Tech stack

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- pgvector
- Pydantic

### AI / Retrieval
- OpenAI API
- Sentence Transformers
- vector similarity search with pgvector

### Dev
- Poetry
- Python 3.11+
- pip-compatible dependency setup

## Local development

### 1. Clone the repository

```bash
git clone https://github.com/michael-chow-arch/docmind.git
cd docmind/backend
```

### 2. Install dependencies

Using Poetry:

```bash
poetry install
```

Or with pip if needed:

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in `backend/` and configure values such as:

```env
APP_NAME=DocMind
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docmind
OPENAI_API_KEY=your_api_key_here
EMBEDDING_PROVIDER=sbert
EMBEDDING_DIM=384
AUTO_CREATE_TABLES=true
```

Only the embedding provider is configurable (`sbert` or `openai`). LLM answers use OpenAI API. Use `EMBEDDING_DIM=1536` when `EMBEDDING_PROVIDER=openai`.

### 4. Run the backend

```bash
poetry run uvicorn app.main:app --reload
```

## Example use cases

The current version is suitable for:
- uploading a text-based document
- asking factual questions about document content
- retrieving semantically similar chunks
- experimenting with embedding providers
- demonstrating backend architecture for an AI-enabled document system

## Known limitations

Current limitations include:
- the public version is primarily text-oriented
- multimodal asset extraction is not complete
- retrieval quality tuning is still evolving
- evidence grounding is not yet strict enough for high-trust use cases
- some engineering hardening steps are intentionally left for future phases
