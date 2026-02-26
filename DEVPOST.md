# JurisScope - Devpost Submission

## Inspiration

Legal research is painfully slow. Lawyers and compliance teams spend hours reading through dozens of documents just to answer questions like "What GDPR violations did this company commit?" or "What evidence supports bias in this AI system?" Current AI search tools help you find relevant documents, but they don't actually answer your questions with precise citations — they just return chunks of text and expect you to piece it together yourself.

When I saw Elastic was hosting a hackathon for Agent Builder, I realized this was the perfect use case for multi-agent workflows. Instead of just searching, I could build agents that search, answer, and cite in sequence — turning legal document analysis from a manual research task into an automated Q&A system.

## What it does

JurisScope is a legal research workbench that answers questions across multiple documents with precise citations. I built a demo case around a fictional AI hiring bias lawsuit (DataSure vs TechNova) with 16 documents including EU regulations, internal communications, meeting notes, and legal correspondence.

**The 3-agent pipeline:**

1. **Search Agent**: Runs hybrid search (BM25 + vector embeddings) across all documents, then reranks results using Jina's reranker model to surface the most relevant chunks.

2. **Answer Agent**: Takes the top chunks and generates a comprehensive answer using Claude 4.5 Sonnet via Elasticsearch's inference API. The answer is structured with citations [1], [2], etc.

3. **Citation Agent**: Extracts precise snippets (up to 350 chars) and page numbers for every reference, building clickable citations that jump directly to the highlighted text in the source PDF.

**Additional features:**

- **Table Analysis**: Select documents and extract structured data using natural language prompts. Ask "What legal violations are mentioned?" and it builds a table with extracted values for each document.

- **Workflow Logging**: Every query logs agent steps, latency, and results for full traceability.

- **Document Management**: Upload PDFs, track processing status, view documents with in-browser highlighting.

**Example query:**
> "What specific bias did Sofia Rodriguez find in TechNova's AI system?"

JurisScope returns a detailed answer citing exact statistics (gender gap: 7.1 points, p < 0.001), the testing methodology, and ethnicity bias results — all with clickable citations to the source emails and Slack messages.

## How I built it

**Backend (FastAPI + Python):**
- Elasticsearch 8.11 serverless for document storage and hybrid search
- Agent Builder framework for orchestrating the 3-agent workflow
- Jina embeddings v3 for vector search
- Jina reranker v3 for relevance scoring
- Claude 4.5 Sonnet via Elasticsearch inference API
- PyMuPDF for PDF text extraction and bounding box detection
- Local metadata service for tracking uploads, projects, and query logs

**Frontend (Next.js 15 + TypeScript):**
- Next.js 15 with App Router and Turbopack
- Tailwind CSS for UI
- React PDF viewer with highlighting
- Real-time citation popover on hover
- Workflow visualization showing agent steps and latency

**Data Processing Pipeline:**
1. User uploads PDF → FastAPI endpoint
2. PyMuPDF extracts text, bounding boxes, and page metadata
3. Text is chunked (500 chars with 100 char overlap)
4. Each chunk is embedded using Jina embeddings v3
5. Chunks stored in Elasticsearch with vectors, metadata, and bounding boxes

**Search Pipeline:**
1. User query embedded with Jina
2. Hybrid search combines BM25 (keyword) + kNN (vector) with RRF (Reciprocal Rank Fusion)
3. Top 20 results reranked using Jina reranker
4. Top 5 passed to answer agent

**Agent Workflow:**
```python
# routes/ask.py - A2A orchestration
workflow = []

# Step 1: search-agent
hits = es_service.hybrid_search(query_text, query_vector, project_id)
reranked = rerank_passages(query, hits)
workflow.append({"agent": "search-agent", "duration_ms": 250})

# Step 2: answer-agent
answer = generate_answer_with_elastic(query, reranked[:5])
workflow.append({"agent": "answer-agent", "duration_ms": 3200})

# Step 3: citation-agent
citations = build_citations(reranked[:5])
workflow.append({"agent": "citation-agent", "duration_ms": 15})
```

**Demo Case Documents:**
I created 16 realistic legal documents across 5 categories:
- Regulations (GDPR, EU AI Act)
- Internal communications (Slack export, email threads)
- Legal correspondence (complaint letter, settlement proposal)
- Governance docs (compliance assessment, DPA agreement)
- Case summaries (news article, meeting notes)

## Challenges I ran into

**Citation accuracy**: The hardest part was tracking exact snippets and page numbers. Initially, citations were vague ("mentioned in Email_Thread_AI_Risk.txt"). I had to store bounding boxes for every chunk during PDF processing, then build a citation system that maps [1], [2] markers to exact page locations with clickable URLs that highlight the text.

**Hybrid search tuning**: Balancing BM25 vs vector search was tricky. Pure vector search missed exact keyword matches (like "Article 10" or "GDPR"). Pure BM25 missed semantic similarity. I settled on RRF (Reciprocal Rank Fusion) which combines both, then added reranking on top for better relevance.

**Reranking integration**: Elasticsearch's inference API for reranking was new to me. I had to learn how to batch passages, call the Jina reranker endpoint, and reorder results based on relevance scores without breaking the citation mapping.

**Answer quality**: Claude sometimes hallucinated citations or added claims not found in the documents. I had to refine the system prompt to be very strict: "Answer based ONLY on the provided documents. ALWAYS cite sources using [n] markers. Never invent information."

**Table feature complexity**: Building the column generator required calling the LLM once per document per column, which could be slow. I added streaming updates so users see results appear incrementally instead of waiting for the whole table.

## Accomplishments that I'm proud of

✅ **Built end-to-end in 5 weeks** — from idea to working demo with 16 documents

✅ **3-agent pipeline with full workflow logging** — every query shows which agent did what and how long it took

✅ **Precise citation tracking** — citations jump to exact page locations with text highlighting in the PDF viewer

✅ **Hybrid search + reranking** — combines keyword and semantic search with reranking for better relevance

✅ **Table analysis feature** — extract structured data across multiple documents using natural language

✅ **Realistic demo case** — created a fictional lawsuit with regulations, internal docs, and legal correspondence that feels authentic

✅ **Clean UI** — designed a polished interface that doesn't look like a typical hackathon project

## What I learned

**Agent orchestration**: I learned how to chain agents in a sequential workflow where each agent's output feeds into the next. The search agent produces chunks → answer agent consumes chunks → citation agent formats references.

**Hybrid search with reranking**: I now understand why hybrid search (BM25 + vector) outperforms either method alone, and how reranking adds a second layer of relevance scoring.

**Elasticsearch inference API**: I learned how to use Elasticsearch's built-in inference endpoints for embeddings, reranking, and LLM chat completion instead of calling external APIs.

**Citation systems**: Building accurate citations taught me about bounding box tracking, chunk-to-page mapping, and URL construction for deep linking into PDFs.

**Agent Builder framework**: I learned how Elasticsearch Agent Builder handles tool selection and workflow management, making it easier to build multi-step AI agents.

**Legal domain modeling**: Creating 16 realistic legal documents taught me about GDPR structure, AI Act requirements, and how real legal cases are documented.

## What's next for JurisScope

**Multi-document comparison**: Add an agent that compares claims across documents. Example: "What contradictions exist between TechNova's public statements and internal emails?"

**Timeline extraction**: Build a timeline agent that extracts events, dates, and sequences from documents and visualizes them chronologically.

**Export to legal formats**: Generate legal briefs, memos, or compliance reports from Q&A sessions.

**Bulk document upload**: Support uploading entire case folders (50+ documents) with progress tracking and batch processing.

**Custom reranking models**: Fine-tune reranking models on legal domain data for better relevance in specific practice areas (GDPR, AI Act, employment law).

**Collaborative workspaces**: Allow teams to share projects, annotate documents, and collaborate on research.

**ES|QL integration**: Add a compliance agent that runs structured queries using ES|QL to extract specific data like violation types, penalty amounts, and risk scores.

---

## Built With

**Languages & Frameworks:**
- Python 3.11
- TypeScript
- FastAPI
- Next.js 15
- React 19

**Cloud & Databases:**
- Elasticsearch 8.11 (serverless)
- Elasticsearch Agent Builder
- PostgreSQL (Prisma ORM)

**AI & ML:**
- Jina embeddings v3
- Jina reranker v3
- Claude 4.5 Sonnet (via Elastic inference)
- GPT-4.1 (fallback via Elastic inference)

**Libraries & Tools:**
- PyMuPDF (PDF processing)
- Tailwind CSS
- React PDF viewer
- Docker

---

**GitHub**: [Link to repo]
**Demo Video**: [Link to video]
**Live Demo**: [Link if deployed]
