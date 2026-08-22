# OptimizerAi — Multi-Model Query Router

A routing layer that dispatches financial queries to one of four local LLMs based on task type, built on top of the FinTracker backend. Supports fully local inference via Ollama, with Groq available as a cloud fallback, plus a manual model override.

## Features

- **Multi-model routing** — routes each query to one of four LLMs (Phi-3, Gemma 3, Qwen 2.5, LLaMA 3) based on task classification
- **Local-first inference** — runs via [Ollama](https://ollama.com) by default; switches to Groq's cloud API by setting `LLM_BACKEND=groq`
- **Manual override** — lets the user pin a specific model/backend instead of automatic routing
- **Financial context building** — pulls transaction, balance, and category data into structured context before each LLM call
- **Financial health scoring** — computes a score from savings, cash flow, spending stability, and anomaly risk
- **Streaming responses** — streams tokens back via Server-Sent Events as they're generated
- **Backend status check** — reports whether Ollama/Groq are reachable and which models are available

## Tech Stack

Python, FastAPI, MySQL, Ollama, Groq API, httpx

## Prerequisites

- Python 3.10+
- MySQL server running locally (or reachable)
- [Ollama](https://ollama.com) installed, with the models you want pulled, e.g.:
  ```bash
  ollama pull phi3:mini
  ollama pull gemma3:4b
  ollama pull qwen2.5:7b
  ollama pull llama3
  ```
- (Optional) A free [Groq API key](https://console.groq.com) if you want cloud fallback instead of/alongside local inference

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/singhabhiav-21/OptimizerAi.git
   cd OptimizerAi
   ```

2. **Install dependencies**
   ```bash
   pip install -r fintracker_base/requirements.txt
   ```

3. **Create a `.env` file** in the project root with:
   ```env
   SECRET_KEY=your-secret-key-here

   # Database
   DB_HOST=localhost
   DB_PORT=3306
   DB_USER=your-mysql-user
   DB_PASSWORD=your-mysql-password
   DB_NAME=your-database-name

   # AI backend
   LLM_BACKEND=ollama          # or "groq"
   OLLAMA_BASE_URL=http://localhost:11434
   GROQ_API_KEY=your-groq-key  # only needed if using Groq
   ```

4. **Set up the MySQL database** — create the database named in `DB_NAME` and run any schema/setup scripts your FinTracker instance requires (schema not included in this snippet — check `databaseDAO/` for table definitions used by the DAOs).

5. **Start Ollama** (if using local inference)
   ```bash
   ollama serve
   ```

6. **Run the app**
   ```bash
   uvicorn fintracker_base.main:app --reload
   ```

The app will be available at `http://localhost:8000`. The AI router endpoints are mounted under `/api/ai`.

## Project Structure

```
backend/              # AI routing layer
  ollama_client.py     # Ollama/Groq LLM calls, model registry, override logic
  router.py            # FastAPI routes under /api/ai
  classifier.py         # Query classification for routing decisions
  financial_context.py # Builds context from user's financial data
  healthScore.py       # Financial health scoring logic
  agent.py             # Prompt construction, proactive alerts
  metrics.py            # Usage/performance metrics

fintracker_base/       # Core FinTracker backend
  main.py               # FastAPI entry point
  databaseDAO/          # Data access layer (accounts, transactions, users)
  Visuals/               # Reports, charts, exchange rates
  frontend/               # Templates and static assets
```

## Notes

- Model routing keys map to specific model tags — see `AVAILABLE_MODELS` in `backend/ollama_client.py` for the full list and their local resource requirements (2.2GB–4.7GB per model).
- Switching `LLM_BACKEND` to `groq` reroutes all calls to Groq's API using equivalent hosted models (no local GPU/RAM needed, but requires an API key).