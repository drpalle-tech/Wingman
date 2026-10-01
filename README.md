# Wingman

Code review and code generation for Python, C#/.NET and TypeScript/React, plus Q&A over your PDFs.
Wingman runs locally: a FastAPI backend that calls your Azure OpenAI deployment, and a React web UI.
A VS Code extension is next, built on the same API and client.

## What it does

- **Review**: attach files or paste code. Findings come with severity, category, exact lines (verified against your source) and a fix. Reviews cover correctness, security, resource and memory leaks, concurrency, error handling and design, using a checklist per language. Hard-coded secrets are caught by a deterministic scanner and removed before any code reaches the model.
- **Generate**: write new code, complete unfinished code, or refactor a file. Output streams in, and every file produced can be copied or downloaded.
- **Ask docs**: questions answered from uploaded PDFs (optional; needs Azure Storage and AI Search).

Attach `package.json`, a `.csproj`, `requirements.txt` or `pyproject.toml` as well, and Wingman detects your frameworks and versions and judges the code against them.

## Quick start

Backend (Python 3.11+):

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.template .env   # then fill in your Azure OpenAI settings
python main.py                 # http://127.0.0.1:8000, API docs at /docs
```

Frontend (Node 18+):

```powershell
cd frontend
npm install
npm run dev                    # http://localhost:3000
```

Set `VITE_API_URL` if the backend is not on `http://127.0.0.1:8000`.

## Configuration (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `AZURE_ENDPOINT` | required | Azure OpenAI resource endpoint, e.g. `https://<resource>.openai.azure.com/` |
| `AZURE_API_KEY` | required | API key for that resource |
| `DEPLOYMENT_NAME` | `gpt-5-mini` | Deployment to call |
| `LLM_MODEL` | `DEPLOYMENT_NAME` | Model name used for capabilities and pricing when the deployment is named differently |
| `AZURE_API_VERSION` | `2025-04-01-preview` | Azure OpenAI API version |
| `LLM_REASONING_EFFORT` | per task | `minimal`, `low`, `medium` or `high`; reasoning models only |
| `MAX_CONTEXT_CHARS` | `400000` | Largest request accepted |
| `HOST`, `PORT` | `127.0.0.1`, `8000` | Where the backend listens |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Browser origins allowed to call the API |
| `USAGE_DB_PATH` | `backend/data/usage.db` | SQLite file holding all-time token and cost history |
| `AZURE_STORAGE_*`, `SEARCH_*` | unset | Enable document Q&A |

## API

| Endpoint | Purpose |
|---|---|
| `POST /v1/review` | `{context, focus?, instructions?}` → `{summary, findings[], model, usage}` |
| `POST /v1/generate` | `{mode: new \| complete \| refactor, request, context}` → server-sent events: `start`, `delta`…, then `done` or `error` |
| `POST /chat` | Document Q&A |
| `POST /upload`, `GET /documents`, `DELETE /documents/{name}` | Manage PDFs |
| `GET /usage`, `/usage/history`, `/usage/report` | Token and cost tracking |

Both code endpoints take a context bundle. Clients send what they know, and the backend detects the rest:

```json
{
  "files": [
    {"path": "src/cart.py", "content": "...", "role": "target"},
    {"path": "requirements.txt", "content": "fastapi==0.104.1", "role": "config"}
  ],
  "selection": {"path": "src/cart.py", "start_line": 10, "end_line": 42},
  "diagnostics": [{"path": "src/cart.py", "line": 12, "severity": "error", "message": "...", "source": "pyright"}]
}
```

`role` is `target` (code to review or change), `related` (supporting code) or `config` (manifests and tool settings).

## Project layout

```
backend/
  main.py            app setup and document Q&A endpoints
  llm_client.py      model-agnostic LLM client with per-task settings
  assist/            code assistant: schemas, context rendering, secret scanner, review, generate, prompts/
  tests/             pytest suite
packages/client/     typed TypeScript client shared by the web UI, VS Code extension and CLI
frontend/            React web UI
evals/               samples with seeded bugs and a scorer for review quality
```

## Development

- Backend tests: `cd backend; .\venv\Scripts\python -m pytest`
- Client tests: `cd packages/client; npm test; npm run typecheck`
- After changing backend API models, regenerate the client types:
  `cd backend; .\venv\Scripts\python export_openapi.py`, then `cd ../packages/client; npm run generate`
- Prompts live in `backend/assist/prompts/`. Restart the backend after editing them.
- Review quality: with the backend running, `backend\venv\Scripts\python evals/run.py [--url ...] [--only py-]`. It reports how many seeded issues were found, noise on clean samples, anchoring and cost. Run it after every prompt or model change; results go to `evals/results/` (git-ignored).

Baseline (2026-09-28, `gpt-5-mini`): 24/24 seeded issues found, 3 critical/major findings across 3 clean samples, 100% of findings anchored to verified lines, about $0.09 for 15 reviews.

## Security notes

- The backend has no authentication. It binds to `127.0.0.1` and only accepts browser requests from `CORS_ORIGINS`; don't expose it on a network.
- Source code and prompts are never written to the logs.
- `.env` is git-ignored. Never commit it.
