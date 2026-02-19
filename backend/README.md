# Clause Backend API

FastAPI backend for Clause - Legal AI workbench with hybrid search and multi-agent system.

## Features

- **Document Ingestion**: Upload PDFs, process with Document AI, extract text with bounding boxes
- **Hybrid Search**: BM25 + kNN vector search with RRF fusion in Elasticsearch
- **AI-Powered Q&A**: Answer questions using Gemini 1.5 Pro with citation markers
- **Pixel-Perfect Citations**: Deep-link to exact passages with bounding box highlights
- **GCP Native**: Cloud Storage, Firestore, Vertex AI, Document AI

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env.local` and fill in your values:

```bash
cp .env.example ../.env.local
```

Important: Complete the manual setup tasks in `../TODO.md` first!

### 3. Run the Server

```bash
python -m uvicorn main:app --reload --port 8002
```

The API will be available at: http://localhost:8002

API documentation: http://localhost:8002/docs

## API Endpoints

### Document Upload
- `POST /api/upload` - Generate signed URL for document upload
- `POST /api/upload/local` - Upload local file directly (for testing)

### Q&A
- `POST /api/ask` - Ask a question and get answer with citations
- `GET /api/query/{query_id}` - Get query log for traceability

### Documents
- `GET /api/doc/{doc_id}` - Get document metadata
- `GET /api/signed-url/{doc_id}` - Get signed URL for PDF viewing
- `GET /api/documents` - List documents (optionally filtered by project)
- `GET /api/doc/{doc_id}/spans` - Get span map for citation highlighting

### Projects
- `GET /api/projects` - List projects
- `POST /api/projects` - Create a new project

### Health
- `GET /healthz` - Health check endpoint
- `GET /` - API information

## Architecture

```
backend/
├── main.py                 # FastAPI application
├── config.py              # Configuration management
├── services/              # GCP service integrations
│   ├── document_ai.py     # Document AI OCR
│   ├── vertex_ai.py       # Embeddings and Gemini LLM
│   ├── elasticsearch.py   # Hybrid search
│   ├── firestore.py       # Metadata storage
│   ├── gcs.py            # Cloud Storage
│   └── ingestion.py      # Document ingestion pipeline
└── routes/               # API routes
    ├── upload.py         # Upload endpoints
    ├── ask.py           # Q&A endpoints
    └── documents.py     # Document management
```

## Testing with Demo Files

Test with the demo-case PDFs:

```python
import requests

# Upload a local file
response = requests.post(
    "http://localhost:8002/api/upload/local",
    json={
        "file_path": "/Users/anhlam/clause/demo-case/regulations/AI_Act_Final.pdf",
        "project_id": "demo-project",
        "doc_title": "EU AI Act - Final Version"
    }
)

doc_id = response.json()["doc_id"]

# Ask a question
response = requests.post(
    "http://localhost:8002/api/ask",
    json={
        "query": "Define what high-risk AI means under the EU AI Act",
        "project_id": "demo-project",
        "k": 5
    }
)

print(response.json())
```

## Deployment

### Docker

```bash
docker build -t clause-backend .
docker run -p 8002:8002 --env-file ../.env.local clause-backend
```

### Cloud Run

```bash
gcloud run deploy clause-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=clause-475719
```

## Development

- **Auto-reload**: Use `--reload` flag with uvicorn for development
- **API Docs**: Visit `/docs` for interactive Swagger UI
- **Logging**: Set `LOG_LEVEL=DEBUG` for verbose logging

## Troubleshooting

1. **Elasticsearch connection failed**: Make sure Elasticsearch is running on the configured URL
2. **Document AI not configured**: Complete step 3 in `TODO.md` to create a processor
3. **GCS permission denied**: Ensure service account has Storage Admin role
4. **Firestore not found**: Initialize Firestore database in GCP Console

See `../TODO.md` for complete setup checklist.

