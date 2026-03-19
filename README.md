# DocMind

**DocMind** is a backend-first document intelligence project focused on building a clean, extensible foundation for document ingestion, semantic retrieval, and LLM-powered question answering.

The current public version is **text-first**: it supports document upload, text extraction, chunking, vector search with pgvector, and answer generation with LLMs. The architecture is intentionally designed to be **multimodal-ready**, with future support planned for richer document assets such as tables, images, OCR-heavy files, and stronger evidence grounding.

This repository is maintained as a **portfolio / interview-facing backend engineering project**, with emphasis on:

- modular service boundaries
- async-first API design
- pluggable embedding provider (OpenAI or SBERT)
- vector retrieval with PostgreSQL + pgvector
- maintainable structure for future multimodal expansion

---

## Why this project

Many document chat demos stop at “upload a PDF and ask a question.”

DocMind is built with a broader engineering goal:

- separate ingestion, retrieval, and answer generation concerns
- keep the codebase extensible instead of tightly coupling everything to one LLM flow
- evolve from a text-first MVP into a richer document intelligence foundation

The goal is not just to produce answers, but to build a codebase that can support:

- better retrieval quality
- stronger evidence tracing
- multimodal asset handling
- more production-grade operational patterns over time

---

## Current status

### Implemented in the current public version

- FastAPI backend with modular structure
- async API layer
- document upload and local storage
- text extraction for supported documents
- text chunking and embedding generation
- semantic retrieval using PostgreSQL + pgvector
- LLM-based answer generation
- conversation/session-oriented question answering flow
- configurable embedding provider abstraction
- local development setup with Docker Compose
- async-aligned tests for core application paths

### Planned / in progress

The following items are part of the intended roadmap, but are **not fully implemented yet** in the current public version:

- full multimodal document parsing
- table extraction and table-aware retrieval
- image extraction and image-grounded QA
- OCR-heavy document support improvements
- stronger reranking beyond current heuristic approaches
- stricter citation grounding and claim-to-evidence validation
- background ingestion workflow for heavier document processing
- cloud/object storage support such as S3 or MinIO
- migration-oriented schema management
- frontend application / full end-to-end product layer

---

## Architecture overview

DocMind is currently a **backend-first** system with separation between API, application logic, infrastructure concerns, and persistence.

```text
backend/
├── app/
│   ├── api/               # FastAPI routes and request handling
│   ├── application/       # application services / orchestration logic
│   ├── core/              # settings, logging, shared config
│   ├── db/                # database session / base setup
│   ├── domains/           # project business modules and data models
│   └── infrastructure/    # storage, embeddings, LLM, document processing
├── tests/
├── pyproject.toml
└── docker-compose.yml
```

### Design goals

- keep business flow readable
- isolate infrastructure-specific code where practical
- make provider replacement easier
- support gradual evolution toward stronger retrieval and richer document understanding

This repository should currently be viewed as a **well-structured MVP / engineering foundation**, not as a fully production-hardened platform.

---

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

**text-first RAG with multimodal-ready architecture**

---

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

### Dev / Infra
- Docker Compose
- Poetry
- Python 3.11+

---

## Key engineering ideas

### 1. Backend-first, not demo-first
This repository prioritizes maintainable backend structure over a quick UI demo.

### 2. Embedding provider abstraction
Only the embedding provider is configurable (OpenAI or SBERT). LLM answers use OpenAI API.

### 3. Retrieval as a first-class concern
The system is built around chunk storage, vector search, and retrieval quality rather than treating retrieval as an afterthought.

### 4. Multimodal-ready direction
Although the current public version is text-focused, the structure is intended to support richer document assets in future iterations.

---

## What this project is not yet

To keep the project honest and easier to discuss in interviews, the current public version should **not** be overstated as:

It is **not yet**:

- a fully production-ready SaaS platform
- a complete multimodal RAG system
- a finished frontend + backend product
- a benchmark-heavy retrieval research project
- a distributed ingestion platform

Instead, it is currently best viewed as:

> a solid backend prototype for document intelligence, with clear extension points for future multimodal and production-grade capabilities

---

## Local development

### 1. Clone the repository

```bash
git clone https://github.com/Michael429-zzZ/docmind.git
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

### 4. Start PostgreSQL and supporting services

```bash
docker compose up -d
```

### 5. Run the backend

```bash
poetry run uvicorn app.main:app --reload
```

### 6. Open API docs

```text
http://127.0.0.1:8000/docs
```

---

## Example use cases

The current version is suitable for scenarios such as:

- uploading a PDF or other text-based document
- asking factual questions about document content
- retrieving semantically similar chunks
- experimenting with embedding providers
- demonstrating backend architecture for AI-enabled document systems

---

## Roadmap

### Phase 1 — current foundation
- [x] FastAPI backend structure
- [x] document upload flow
- [x] text extraction
- [x] chunking
- [x] embeddings
- [x] pgvector retrieval
- [x] LLM answer generation
- [x] local development setup

### Phase 2 — retrieval quality improvements
- [ ] stronger query rewriting strategy
- [ ] better follow-up question handling
- [ ] reranking improvements
- [ ] retrieval evaluation and benchmark cases
- [ ] better chunk selection for answer synthesis

### Phase 3 — multimodal capabilities
- [ ] table extraction
- [ ] image extraction
- [ ] OCR-enhanced parsing
- [ ] multimodal asset indexing
- [ ] stronger evidence grounding across text and structured assets

### Phase 4 — engineering hardening
- [ ] background ingestion workers or task orchestration
- [ ] storage abstraction for cloud/object storage
- [ ] migration-based schema management
- [ ] auth / rate limiting
- [ ] observability and metrics
- [ ] deployment-oriented configuration strategy

### Phase 5 — product layer
- [ ] frontend application
- [ ] better document management UX
- [ ] chat session history UI
- [ ] admin / ops support features

---

## Interview talking points

If you are reviewing this repository from an engineering interview perspective, the most relevant discussion points are:

- why a backend-first architecture was chosen
- how the project separates ingestion, retrieval, and answer generation
- trade-offs between speed of delivery and production hardening
- how text-first RAG can evolve toward multimodal document intelligence
- where current abstractions are sufficient and where refactoring is still needed
- how async APIs interact with AI workloads and blocking tasks
- how retrieval quality should be evaluated rather than assumed

---

## Known limitations

Current limitations include:

- the public version is primarily text-oriented
- multimodal asset extraction is not complete
- retrieval quality tuning is still evolving
- evidence grounding is not yet strict enough for high-trust use cases
- some engineering hardening steps are intentionally left for future phases

These limitations are explicit by design so the roadmap remains realistic and discussion-friendly.

---

## Future direction

The long-term goal of DocMind is to move from:

**document chat MVP**  
to  
**document intelligence platform foundation**

That means improving both:

- **AI capability**
- **engineering reliability**

The project is intentionally being built in stages so each layer remains understandable, testable, and replaceable.

---

## Author notes

This repository is maintained as a personal engineering project for:

- backend architecture practice
- AI application system design
- retrieval and document intelligence experimentation
- interview discussion and portfolio presentation

Feedback, architecture suggestions, and implementation critiques are welcome.

