import json
import time
import httpx
import os
from typing import Optional

LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama").lower()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

# ── Model routing tables ──────────────────────────────────────────────────────

OLLAMA_MODELS = {
    "phi3_mini": "phi3:mini",
    "gemma3": "gemma3:4b",
    "qwen2_5":"qwen2.5:7b",
    "llama3": "llama3:latest"
}

# Groq: free models, very fast (~300 tokens/sec)
# All map to llama3 variants since Groq doesn't have phi3
GROQ_MODELS = {
    "phi3_mini": "llama-3.1-8b-instant",  # fast, cheap equivalent
    "gemma3":"gemma3:4b",
    "llama3": "llama-3.3-70b-versatile",  # heavy reasoning tasks
}

SYSTEM_PROMPT = """You are an intelligent financial analysis agent embedded in FinTracker.
You have the user's real financial data. Be specific with numbers. Give concrete action recommendations.
Never use filler phrases. Always end with 1-3 specific action items."""


async def call_llm(
        model_key: str,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 900,
) -> dict:
    """
    Routes to Ollama or Groq based on LLM_BACKEND env var.
    Returns: {text, prompt_tokens, completion_tokens, total_tokens, backend}
    """
    override = get_model_override()
    if override:
        if override["backend"] == "groq":
            return await _call_groq_direct(override["model_tag"], prompt, temperature, max_tokens)
        else:
            return await _call_ollama_direct(override["model_tag"], prompt, temperature, max_tokens)
    # default routing
    if LLM_BACKEND == "groq":
        return await _call_groq_direct(model_key, prompt, temperature, max_tokens)
    return await _call_ollama_direct(model_key, prompt, temperature, max_tokens)


async def _call_ollama_direct(model_tag, prompt, temperature, max_tokens):
    payload = {
        "model": model_tag,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
        resp.raise_for_status()
        data = resp.json()
    text = data.get("message", {}).get("content", "")
    return {
        "text": text,
        "prompt_tokens": data.get("prompt_eval_count", len(prompt) // 4),
        "completion_tokens": data.get("eval_count", len(text) // 4),
        "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
        "backend": f"ollama/{model_tag}",
    }

async def _call_groq_direct(model_tag, prompt, temperature, max_tokens):
    payload = {
        "model": model_tag,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{GROQ_BASE_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    return {
        "text": text,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "total_tokens": usage.get("total_tokens", 0),
        "backend": f"groq/{model_tag}",
    }

async def check_backends() -> dict:
    status = {"llm_backend": LLM_BACKEND}

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])]
            status["ollama"] = {"status": "online", "models": models}
    except Exception as e:
        status["ollama"] = {"status": "offline", "error": str(e)}

    # Check Groq
    status["groq"] = {
        "status": "configured" if GROQ_API_KEY else "no_api_key",
        "note": "Get free key at console.groq.com" if not GROQ_API_KEY else "Ready",
    }

    status["active_backend"] = LLM_BACKEND
    return status


async def stream_ollama(model_key: str, prompt: str, temperature: float = 0.3, max_tokens: int = 900):
    """
    Async generator that yields text chunks as they arrive from Ollama.
    """
    override = get_model_override()
    if override and override["backend"] != "groq":
        model_tag = override["model_tag"]
    else:
        model_tag = OLLAMA_MODELS.get(model_key, "phi3:mini")

    payload = {
        "model": model_tag,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": True,  # ← key change
        "options": {"temperature": temperature, "num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/chat", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                except Exception:
                    continue

AVAILABLE_MODELS = {
    "phi3:mini":    {"name": "Phi-3 Mini",      "size": "2.2GB", "speed": "fast",   "quality": "good"},
    "gemma3:4b":    {"name": "Gemma 3 4B",      "size": "3.3GB", "speed": "medium", "quality": "good"},
    "llama3:latest":{"name": "LLaMA 3 8B",      "size": "4.7GB", "speed": "slow",   "quality": "best"},
    "qwen2.5:7b": {"name": "Qwen 2.5 7B", "size": "4.7GB", "speed": "medium", "quality": "great"},

    # Groq models
    "llama-3.1-8b-instant":  {"name": "LLaMA 3.1 8B (Groq)",  "size": "cloud", "speed": "fast",   "quality": "good"},
    "llama-3.3-70b-versatile":{"name": "LLaMA 3.3 70B (Groq)", "size": "cloud", "speed": "medium", "quality": "best"},
}

# User-overridable model (None = use classifier routing)
_user_model_override: dict | None = None


def set_model_override(model_tag: str | None, backend: str | None = None):
    global _user_model_override
    if model_tag is None:
        _user_model_override = None
    else:
        _user_model_override = {"model_tag": model_tag, "backend": backend}


def get_model_override():
    return _user_model_override

