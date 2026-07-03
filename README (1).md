# IITK Campus Assistant — A RAG System for IIT Kanpur Students

A Retrieval-Augmented Generation (RAG) chat assistant that answers student questions about
**academics, fee structure, facilities & amenities, hostels, clubs, fests, and the history**
of IIT Kanpur — grounded in real, cited content scraped from official institute sources.

> **Status:  In active development.** This repository currently contains the data ingestion
> pipeline and a working backend retrieval/query skeleton. Frontend and full production
> deployment are in progress. See [Roadmap](#roadmap) below.

---

## Why this project

IITK's academic and administrative information is spread across dozens of portals — DOAA,
DOSA, Gymkhana, individual department and club sites, and PDFs of ordinances and fee
structures. New students in particular have no single place to ask a plain-language question
like *"what's the hostel fee this year?"* or *"how do I join the coding club?"* and get a
sourced, trustworthy answer. This project builds that single entry point.

## What it does

- Ingests and cleans content from IITK's official web pages and PDFs into a structured corpus
- Retrieves the most relevant passages for a student's question using hybrid search
  (keyword + semantic)
- Generates a natural-language answer strictly grounded in retrieved content, with source
  citations attached to every answer — so factual claims (fees, deadlines, rules) can always
  be traced back to the original document
- Explicitly declines to guess when the answer isn't in the knowledge base, instead of
  hallucinating

## Architecture

```
┌──────────────────┐     ┌───────────────────────┐     ┌──────────────────────┐
│   1. Scraper      │────▶│   corpus.jsonl         │────▶│  2. Backend / RAG     │
│  (IITK sources)   │     │  (structured documents)│     │  (retrieve + generate)│
└──────────────────┘     └───────────────────────┘     └──────────┬────────────┘
                                                                    │  REST / SSE API
                                                                    ▼
                                                         ┌──────────────────────┐
                                                         │  3. Frontend (chat UI)│
                                                         │   [planned]           │
                                                         └──────────────────────┘
```

The system is split into three independently developed components connected by a fixed data
and API contract, so each piece can be built, tested, and swapped independently.

## Repository structure

```
.
├── scraper/
│   └── scrape_iitk.py      # Fetches & cleans IITK pages into corpus.jsonl
├── backend/
│   └── main.py             # FastAPI RAG service: retrieval + grounded generation
├── corpus.jsonl            # Generated output of the scraper (not committed; see below)
└── README.md
```

## Document schema

Every scraped document conforms to this structure, which is the contract between the scraper
and the backend:

```json
{
  "doc_id": "uuid4 string",
  "source_url": "https://...",
  "title": "Page or section title",
  "category": "academics | fees | facilities | clubs | fests | history | hostel | admissions | other",
  "subcategory": "optional, e.g. department or club name",
  "text": "cleaned plain text / markdown content",
  "scraped_at": "ISO 8601 timestamp",
  "content_hash": "sha256 of text, for change detection",
  "doc_type": "html | pdf"
}
```

## API contract

```
POST /api/query
{
  "query": "What is the hostel fee for BTech students?",
  "category_filter": ["fees", "hostel"],   // optional
  "stream": false
}
```

```json
{
  "answer": "Grounded, markdown-formatted answer text...",
  "sources": [
    { "doc_id": "...", "title": "...", "source_url": "...", "snippet": "..." }
  ],
  "confidence": "high | medium | low"
}
```

## Tech stack

| Layer       | Technology (current / planned)                                         |
|-------------|--------------------------------------------------------------------------|
| Scraping    | Python, `requests`, `BeautifulSoup4`, `pdfplumber` for PDF fee structures |
| Retrieval   | TF-IDF keyword search (current) → hybrid dense + BM25 with reranking (planned, via Qdrant) |
| Generation  | Claude API, grounded strictly in retrieved context                       |
| Backend API | FastAPI                                                                   |
| Frontend    | Next.js + Tailwind (planned)                                             |

## Getting started

```bash
# 1. Clone and install dependencies
git clone <this-repo-url>
cd iitk-rag-assistant
pip install -r requirements.txt   # requests, beautifulsoup4, pdfplumber, fastapi, uvicorn,
                                   # scikit-learn, anthropic

# 2. Run the scraper to build the corpus
python scraper/scrape_iitk.py

# 3. Set your Anthropic API key
export ANTHROPIC_API_KEY=your_key_here

# 4. Start the backend
uvicorn backend.main:app --reload

# 5. Query it
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the different hostels at IIT Kanpur?"}'
```

## Roadmap

- [x] Define shared document schema and API contract across all three workstreams
- [x] Build initial scraper for IITK public web pages
- [x] Stand up a working retrieval + grounded-generation backend (TF-IDF baseline)
- [ ] Extend scraper coverage: PDFs (fee structures, ordinances), all department pages, club/fest microsites
- [ ] Replace TF-IDF with hybrid dense + BM25 retrieval and cross-encoder reranking (Qdrant)
- [ ] Add conversation memory / session handling
- [ ] Build the Next.js frontend with IITK-themed UI, streaming responses, and inline citations
- [ ] Build an evaluation set (~20 known Q&A pairs across categories) to track answer accuracy
- [ ] Deploy end-to-end

## Team

This is a 3-person collaborative project split across data ingestion, backend/RAG, and
frontend workstreams, coordinated around the shared schema/API contract above so each
component can be developed and tested independently before integration.

## Disclaimer

This is an independent student project and is **not an official IIT Kanpur service**. Always
verify critical information (fees, deadlines, academic rules) against the institute's official
sources, which are linked as citations in every generated answer.
