# LinkedIn Post - Elasticsearch Agent Builder Hackathon

---

AI search tools are great at finding documents, but they struggle with complex legal research where you need to reason across dozens of files, track citations, and actually answer questions like "What GDPR violations does this company have?" Most tools just return relevant chunks and call it a day.

So when I saw Elastic was hosting a hackathon celebrating Agent Builder, a framework that lets you build multi-step AI agents that actually reason and use tools, I thought it'd be a great chance to tackle real legal research workflows. Born JurisScope.

Built on Elasticsearch 8.11 serverless, JurisScope turns legal document analysis into intelligent multi-agent orchestration. I created a demo case around a fictional AI hiring bias lawsuit (DataSure vs TechNova) with 16 documents including GDPR regulations, internal Slack messages, emails, and meeting notes.

When a user asks a question, the orchestrator agent first decides which specialized agent to call. The retrieval agent uses Elasticsearch's hybrid search (BM25 + vector embeddings) to find relevant chunks across all documents. The citation agent then validates every claim and tracks exact snippets with page numbers. For compliance questions, the compliance agent runs ES|QL queries to extract structured data like violation types and penalty estimates.

The agents communicate through a workflow system, passing context between steps. All of this runs on Agent Builder's framework, which handles tool selection, state management, and multi-hop reasoning automatically.

For the table analysis feature, I built a custom column generator that lets users select documents and extract structured attributes using natural language prompts. Want to extract "What legal violations are mentioned?" across 10 documents? The agent processes each one and builds a table in real-time.

Overall, this project taught me how to orchestrate multiple agents, implement hybrid search with reranking, and design agent workflows that actually solve multi-step problems instead of just returning search results. Elasticsearch's speed made it possible to search across thousands of chunks in milliseconds while maintaining citation accuracy.

🔗 [GitHub repo link]
🎥 [Demo video link]

#ElasticAgentBuilder #Hackathon
