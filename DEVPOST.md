# JurisScope - Devpost Submission

## Brief Description (~400 words)

**Problem Solved:**

Legal discovery is broken. The average lawsuit involves 1,000+ documents—depositions, contracts, emails, regulations—and lawyers spend 60-70% of case time just reading through them. At $300-500/hour for associates, discovery can cost clients $50,000-200,000 per case. Current AI search tools return relevant document chunks but don't actually answer questions with precise citations. They expect lawyers to manually piece together evidence from dozens of files.

**Solution - JurisScope:**

I built an AI-powered legal discovery platform using Elastic Agent Builder that answers questions across hundreds of documents with lawyer-grade precision. Upload your case files, ask questions in plain English like "What GDPR violations occurred?", and get comprehensive answers with exact citations—page numbers, quotes, and clickable references to source PDFs.

**Elastic Agent Builder Features Used:**

I leveraged Agent Builder's agent-to-agent orchestration to create three custom agents working in sequence:

1. **Search Agent**: Embeds the user query using Jina embeddings v3 (via Elasticsearch inference API) and performs hybrid search combining BM25 (keyword) and kNN (vector) with RRF (Reciprocal Rank Fusion). Results are reranked using Jina reranker v3 through Elastic's inference endpoint for maximum relevance.

2. **Answer Agent**: Takes the top-ranked chunks and generates a comprehensive legal response using Claude 4.5 Sonnet via Elasticsearch's inference API, configured with low temperature to minimize hallucinations. Every answer must include citation markers [1], [2], etc.

3. **Citation Agent**: Extracts precise references with page numbers and snippets, building clickable deep-link citations that jump directly to highlighted passages in source PDFs.

Each agent has access to a custom tool called `jurisscope.legal_search` that performs project-scoped hybrid search across case documents. Agent Builder orchestrates the workflow: Search → Answer → Citations, with full latency logging at each step.

**Features I Liked:**

1. **Elasticsearch Inference API Integration**: I loved how seamlessly Agent Builder integrates with Elastic's inference endpoints. I could swap between embedding models (Jina v3, OpenAI), reranking models, and LLMs (Claude 4.5, GPT-4.1) without changing agent code—just configuration. This made experimentation incredibly fast.

2. **Agent-to-Agent Workflow Orchestration**: Agent Builder's workflow system handles context passing between agents automatically. The search agent's results flow into the answer agent, which flows into the citation agent—all tracked with timestamps and step logging. I didn't have to build my own orchestration layer.

3. **Custom Tool Framework**: Defining the `jurisscope.legal_search` tool with project_id scoping was straightforward. Agent Builder handles tool selection and parameter passing, letting me focus on the search logic itself.

**Challenges:**

- **Citation accuracy**: Mapping [1], [2] markers to exact page locations with bounding boxes required careful tracking through the entire pipeline.
- **Hybrid search tuning**: Balancing BM25 vs vector search was tricky—pure vector missed keyword matches like "Article 10", pure BM25 missed semantics.
- **Answer quality**: Claude sometimes hallucinated citations, requiring strict system prompts: "Answer ONLY from provided documents."

**Demo Case:**

I created DataSure vs TechNova, a fictional AI hiring bias lawsuit with 16 realistic documents: GDPR regulations, EU AI Act, internal Slack messages, email threads, meeting notes, and legal correspondence.

---

## How I Built It

**Elastic Agent Builder Architecture:**

The core intelligence runs on Elastic Agent Builder with three custom agents:

```python
# Search Agent with custom legal_search tool
@tool(name="jurisscope.legal_search")
def legal_search(query: str, project_id: str, k: int = 5):
    """Project-scoped hybrid search across case documents"""
    embedding = jina_embed(query)  # Via Elastic inference
    results = es.hybrid_search(query, embedding, project_id)
    reranked = jina_rerank(query, results)  # Via Elastic inference
    return reranked[:k]

# Answer Agent using Claude 4.5 via Elastic inference
answer = elastic_inference.chat_completion(
    messages=[{"role": "user", "content": prompt}],
    model=".anthropic-claude-4.5-sonnet-chat_completion",
    temperature=0.1  # Low temp for legal precision
)

# Citation Agent extracts references
citations = extract_citations(answer, search_results)
```

**Data Processing Pipeline:**

1. User uploads PDF → FastAPI endpoint
2. PyMuPDF extracts text with bounding boxes per page
3. Text chunked (500 chars, 100 char overlap)
4. Chunks embedded with Jina v3 (via Elastic inference)
5. Stored in Elasticsearch 8.11 serverless with vectors + metadata

**Search Pipeline:**

1. Query embedded with Jina (Elastic inference endpoint)
2. Hybrid search: BM25 + kNN with RRF fusion
3. Top 20 results reranked with Jina reranker (Elastic inference)
4. Top 5 passed to answer agent

**Tech Stack:**

- **Backend**: FastAPI, Python 3.11, PyMuPDF
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, React PDF viewer
- **Elastic Stack**: Elasticsearch 8.11 serverless, Agent Builder, Inference API
- **AI Models**: Jina embeddings v3, Jina reranker v3, Claude 4.5 Sonnet, GPT-4.1 (fallback)
- **Database**: PostgreSQL with Prisma ORM for project metadata

---

## Challenges I Ran Into

**Citation accuracy**: Initially, citations were vague ("mentioned in Email_Thread.txt"). I had to store bounding boxes for every chunk during PDF processing, then build a system that maps [1], [2] markers to exact page locations with clickable URLs that highlight text.

**Hybrid search tuning**: Pure vector search missed exact keyword matches ("Article 10", "GDPR"). Pure BM25 missed semantic similarity. I settled on RRF (Reciprocal Rank Fusion) combining both, plus reranking for relevance.

**Reranking integration**: Learning Elasticsearch's inference API for reranking was new. I had to batch passages, call Jina reranker, and reorder results without breaking citation mapping.

**Answer quality**: Claude sometimes hallucinated citations. I refined system prompts: "Answer based ONLY on provided documents. ALWAYS cite sources using [n] markers. Never invent information."

**Table feature complexity**: Building the column generator required calling the LLM once per document per column, which was slow. I added streaming updates for incremental results.

---

## Accomplishments That I'm Proud Of

✅ **3-agent pipeline with Agent Builder** — seamless orchestration with workflow logging
✅ **Elasticsearch inference API mastery** — embeddings, reranking, and LLM all through Elastic
✅ **Precise citation tracking** — citations jump to exact page locations with PDF highlighting
✅ **Hybrid search + reranking** — BM25 + vector + reranking for legal-grade relevance
✅ **Table analysis feature** — extract structured data using natural language across documents
✅ **Realistic 16-document demo case** — GDPR, AI Act, Slack logs, emails, meeting notes
✅ **Clean, polished UI** — doesn't look like a hackathon project

---

## What I Learned

**Agent-to-agent orchestration**: How to chain agents sequentially where each agent's output feeds the next. Search → Answer → Citations, all managed by Agent Builder's workflow system.

**Elasticsearch inference API**: Using Elastic's built-in endpoints for embeddings, reranking, and LLMs instead of external APIs—simplified architecture and improved latency.

**Hybrid search superiority**: Why BM25 + vector outperforms either alone, and how reranking adds a critical second layer of relevance.

**Custom tool design in Agent Builder**: Defining tools with clear parameters and return types, letting Agent Builder handle selection and orchestration.

**Citation systems**: Bounding box tracking, chunk-to-page mapping, and URL construction for deep linking into PDFs.

**Legal domain modeling**: GDPR structure, AI Act requirements, and how real legal cases are documented.

---

## What's Next for JurisScope

**Multi-document comparison agent**: Compare claims across documents. E.g., "What contradictions exist between TechNova's public statements and internal emails?"

**Timeline extraction agent**: Extract events, dates, sequences and visualize chronologically.

**Compliance agent with ES|QL**: Run structured queries to extract violation types, penalty amounts, and risk scores.

**Export to legal formats**: Generate legal briefs, memos, compliance reports from Q&A sessions.

**Bulk document upload**: Support 50+ document case folders with batch processing.

**Fine-tuned reranking models**: Domain-specific models for GDPR, AI Act, employment law.

**Collaborative workspaces**: Team sharing, annotations, collaborative research.

---

## Built With

- Elasticsearch 8.11 (serverless)
- Elasticsearch Agent Builder
- Elasticsearch Inference API
- Python 3.11
- FastAPI
- Next.js 15
- TypeScript
- React 19
- PostgreSQL
- Jina embeddings v3
- Jina reranker v3
- Claude 4.5 Sonnet
- GPT-4.1
- PyMuPDF
- Tailwind CSS
- Docker

---

**GitHub**: https://github.com/amelia751/jurisscope
**Demo Video**: [Link to be added]
**Live Demo**: [Link to be added]
