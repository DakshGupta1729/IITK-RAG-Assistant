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
