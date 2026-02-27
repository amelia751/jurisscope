# JurisScope

**AI-Enabled Legal Research Workbench** built for the Elasticsearch Agent Builder Hackathon 2026.

JurisScope helps legal professionals analyze documents, find relevant information, and get cited answers using a multi-agent AI system enabled by Elastic Agent Builder.

---

## Features

### 🔍 Discover Tab — AI-Powered Q&A
Ask natural language questions and get comprehensive answers with citations from your document vault.

- **Hybrid Search**: Combines BM25 keyword search with vector similarity (Jina embeddings)
- **Intelligent Reranking**: Uses Jina reranker for better relevance
- **LLM-Generated Answers**: Claude 4.5 Sonnet synthesizes information from multiple documents
- **Clickable Citations**: Hover over [1], [2] markers to see source snippets

### 📁 Vault Tab — Document Management
Upload and organize legal documents in a structured evidence vault.

- **PDF Processing**: Automatic text extraction and chunking
- **Real-time Upload**: SSE streaming shows processing progress
- **Elasticsearch Indexing**: Documents indexed with embeddings for semantic search

### 📊 Table Tab — Structured Analysis
Extract metadata from documents into a spreadsheet-like view.

- **Batch Analysis**: Auto-extract date, document type, author, summary
- **Custom Columns**: Add your own questions (e.g., "What penalties are mentioned?")
- **Export**: Download analysis as CSV

### 🔀 A2A Orchestration — Multi-Agent Workflow
Every query runs through a 3-agent pipeline, visible in the UI:

```
search-agent → answer-agent → citation-agent
```

| Agent | Tool | Action |
|-------|------|--------|
| **search-agent** | `jurisscope.legal_search` | Hybrid search + reranking |
| **answer-agent** | Elastic Inference (Claude) | Generate cited answer |
| **citation-agent** | `jurisscope.citation_finder` | Extract precise references |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js 15)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │ Discover │  │  Vault   │  │  Table   │                       │
│  │  (Q&A)   │  │ (Upload) │  │(Analysis)│                       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                       │
└───────┼─────────────┼─────────────┼─────────────────────────────┘
        │             │             │
        ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  A2A Orchestration                        │   │
│  │  search-agent → answer-agent → citation-agent            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────┐  ┌───────────┴───────────┐  ┌───────────────┐   │
│  │ Embedding │  │   Elastic Inference   │  │  Elasticsearch │   │
│  │  Service  │  │  (Claude, GPT, Jina)  │  │    Service     │   │
│  └───────────┘  └───────────────────────┘  └───────────────┘   │
└─────────────────────────────────────────────────────────────────┘
        │                     │                      │
        ▼                     ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Elastic Cloud                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Agent Builder  │  │   Inference     │  │  Elasticsearch  │ │
│  │    3 Agents     │  │   Endpoints     │  │   (Documents)   │ │
│  │    2 Tools      │  │ Claude/GPT/Jina │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Elastic Agent Builder Integration

### Agents (in Kibana)

| Agent | Description | Tools |
|-------|-------------|-------|
| `search-agent` | Finds relevant legal documents using hybrid search | `jurisscope.legal_search` |
| `answer-agent` | Generates answers from retrieved documents | `jurisscope.legal_search` |
| `citation-agent` | Provides precise citations with page numbers | `jurisscope.citation_finder` |

### Tools (ES|QL)

| Tool | Type | Description |
|------|------|-------------|
| `jurisscope.legal_search` | ES|QL | Searches `jurisscope-documents` index |
| `jurisscope.citation_finder` | ES|QL | Finds article references and citations |

### Inference Endpoints

| Endpoint | Model | Purpose |
|----------|-------|---------|
| `.jina-embeddings-v3` | Jina Embeddings v3 | Document & query embeddings |
| `.jina-reranker-v3` | Jina Reranker | Result reranking |
| `.anthropic-claude-4.5-sonnet-chat_completion` | Claude 4.5 Sonnet | Answer generation |
| `.openai-gpt-4.1-mini-chat_completion` | GPT-4.1 Mini | Fast extraction tasks |

---

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Elastic Cloud account with Agent Builder enabled

### 1. Clone & Setup

```bash
git clone https://github.com/your-repo/jurisscope.git
cd jurisscope
```

### 2. Configure Environment

Create `.env.local` in the root:

```env
# Elasticsearch
ELASTICSEARCH_ENDPOINT=https://your-project.es.us-central1.gcp.elastic.cloud:443
ELASTICSEARCH_API_KEY=your-api-key

# Backend
NEXT_PUBLIC_API_URL=http://localhost:8005
BACKEND_URL=http://localhost:8005
```

### 3. Start Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```

### 4. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Open Application

- Frontend: http://localhost:3005
- Backend API: http://localhost:8005/docs

---

## Demo Case: DataSure vs TechNova

The app includes a pre-loaded demo case for testing:

**Scenario**: TechNova's AI hiring platform (InsightPredict) was found to have algorithmic bias. DataSure, an advocacy group, filed a complaint alleging GDPR and EU AI Act violations.

**Documents include**:
- GDPR Regulation (full text)
- EU AI Act (excerpts)
- Internal Slack communications
- Email threads
- Complaint letters
- Meeting notes
- Risk assessments

### Sample Questions

```
What GDPR violations did TechNova commit?
What are the key compliance gaps under the AI Act?
What settlement terms were proposed?
Who are the key individuals in the case?
```

See [TESTING.md](TESTING.md) for a comprehensive list of test questions.

---

## API Endpoints

### Q&A
- `POST /api/ask` — Ask a question with A2A orchestration
- `GET /api/query/{query_id}` — Get query log

### Documents
- `POST /api/upload/browser` — Upload documents
- `GET /api/documents` — List documents
- `DELETE /api/documents/{doc_id}` — Delete document

### Table Analysis
- `POST /api/table/batch-analyze` — Run batch analysis
- `POST /api/table/custom-column` — Add custom column
- `GET /api/table/job/{job_id}` — Get job status

### Agents (Elastic Agent Builder)
- `GET /api/agents` — List registered agents
- `GET /api/agents/tools` — List custom tools
- `POST /api/a2a/orchestrate` — Direct A2A orchestration

---

## Project Structure

```
jurisscope/
├── frontend/                 # Next.js 15 app
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # UI components
│   │   └── actions/         # Server actions
│   └── package.json
│
├── backend/                  # FastAPI backend
│   ├── routes/              # API endpoints
│   │   ├── ask.py           # Q&A with A2A
│   │   ├── a2a.py           # A2A orchestration
│   │   ├── documents.py     # Document management
│   │   └── table_analysis.py
│   ├── services/            # Business logic
│   │   ├── elasticsearch.py # ES client
│   │   ├── embeddings.py    # Jina embeddings
│   │   └── elastic_inference.py
│   └── main.py
│
├── demo-cases/              # Sample legal documents
│   ├── regulations/
│   ├── communications/
│   └── legal_correspondence/
│
├── TESTING.md               # Test questions & guide
└── README.md
```

---

## License

MIT License — See [LICENSE](LICENSE) for details.

