Legal research tools are great at finding documents, but they struggle with actually answering questions across dozens of files while tracking precise citations. Most just return search results and call it a day.

So when I saw Elastic was hosting a hackathon celebrating Agent Builder, a framework for building AI agents with search and reasoning, I thought it'd be a great chance to tackle legal document analysis. Born JurisScope.

Built on Elasticsearch 8.11 serverless, JurisScope answers legal questions by orchestrating three agents in sequence. I created a demo case around a fictional AI hiring bias lawsuit (DataSure vs TechNova) with 16 documents including GDPR regulations, internal Slack messages, emails, and meeting notes.

When a user asks a question like "What GDPR violations did TechNova commit?", the search agent runs hybrid search (BM25 + vector embeddings) to find relevant chunks across all documents, then reranks them using Jina's reranker model. The answer agent takes those top chunks and generates a comprehensive response using Claude 4.5 Sonnet via Elasticsearch's inference API. Finally, the citation agent extracts precise snippets and page numbers for every claim, building clickable references that jump directly to the highlighted text in the source PDF.

For the table feature, I added a column generator where you can select documents and extract structured data using natural language prompts like "What legal violations are mentioned?" The system processes each document and builds a table in real-time.

The whole workflow is logged with agent steps and latency tracking. Search typically takes 150-300ms, answer generation 2-4 seconds, and citation extraction is near-instant. Elasticsearch's speed made it possible to search across thousands of chunks while maintaining citation accuracy.

Overall, this project taught me how to chain agents in a workflow, implement hybrid search with reranking, and build a legal research tool that actually answers questions instead of just returning search results.

#ElasticAgentBuilder #Hackathon
