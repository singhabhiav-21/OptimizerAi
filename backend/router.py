import json

import httpx
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
# AI modules
from backend.classifier import classify
from backend.financial_context import build_context_from_daos
from backend.healthScore import compute_health_score
from backend.ollama_client import call_llm
from backend.metrics import compute_metrics
from backend.agent import build_prompt, build_proactive_alerts
from backend.ollama_client import (
    set_model_override,
    get_model_override,
    AVAILABLE_MODELS,
    GROQ_API_KEY,        # ← add this
    OLLAMA_BASE_URL,     # ← add this too, you need it in list_models
)
router = APIRouter(prefix="/api/ai", tags=["AI Agent"])


class AnalyzeRequest(BaseModel):
    query: str


class ClassifyRequest(BaseModel):
    query: str


class ModelPreferenceRequest(BaseModel):
    model_tag: str | None  # None = auto (classifier routing)
    backend: str | None = None


def get_current_user(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    return user_id
@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    request: Request,
    user_id: int = Depends(get_current_user),  # ← your existing dep, works perfectly
):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    import time
    start = time.monotonic()

    # Step 1: classify
    routing = classify(body.query)

    # Step 2: fetch context using DAOs directly — no HTTP, no new DB connections
    # (reuses the connection pool your app already has open)
    ctx = await run_in_threadpool(build_context_from_daos, user_id)

    # Step 3: health score (pure Python)
    health = compute_health_score(ctx)

    # Step 4: build prompt
    prompt = build_prompt(routing.task_type, body.query, ctx, health)

    # Step 5: call LLM (Ollama locally, Groq on Render)
    try:
        llm_result = await call_llm(
            model_key=routing.model_key,
            prompt=prompt,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    latency_ms = int((time.monotonic() - start) * 1000)

    # Step 6: metrics
    cost = compute_metrics(
        model_key=routing.model_key,
        model_display=routing.model_display,
        prompt_tokens=llm_result["prompt_tokens"],
        completion_tokens=llm_result["completion_tokens"],
        latency_ms=latency_ms,
    )

    return {
        "answer": llm_result["text"],
        "task_type": routing.task_type,
        "model_used": routing.model_display,
        "model_key": routing.model_key,
        "routing_reasoning": routing.reasoning,
        "complexity": routing.complexity,
        "routing_confidence": routing.confidence,
        "backend_used": llm_result.get("backend", "unknown"),

        "health_score": health.overall,
        "health_grade": health.grade,
        "health_details": {
            "savings": health.savings_score,
            "cash_flow": health.cash_flow_score,
            "stability": health.spending_stability_score,
            "anomaly_risk": health.anomaly_risk_score,
        },
        "health_alerts": health.alerts,
        "health_strengths": health.strengths,

        "prompt_tokens": llm_result["prompt_tokens"],
        "completion_tokens": llm_result["completion_tokens"],
        "total_tokens": llm_result["total_tokens"],
        "latency_ms": latency_ms,
        "savings_display": cost.savings_display,
        "savings_vs_gpt4_usd": cost.savings_vs_gpt4_usd,

        "total_balance": ctx.total_balance,
        "monthly_income": ctx.monthly_income,
        "monthly_expenses": ctx.monthly_expenses,
        "net_cash_flow": ctx.net_cash_flow,
        "top_categories": ctx.top_categories,
        "anomaly_count": len(ctx.anomalies),
        "subscription_count": len(ctx.subscriptions),
        "days_until_threshold": ctx.days_until_threshold,
        "proactive_alerts": build_proactive_alerts(ctx, health),
    }


@router.get("/health-score")
async def get_health_score(
    request: Request,
    user_id: int = Depends(get_current_user),
):
    ctx = await run_in_threadpool(build_context_from_daos, user_id)
    health = compute_health_score(ctx)
    return {
        "overall": health.overall,
        "grade": health.grade,
        "summary": health.summary,
        "details": {
            "savings": health.savings_score,
            "cash_flow": health.cash_flow_score,
            "stability": health.spending_stability_score,
            "anomaly_risk": health.anomaly_risk_score,
        },
        "alerts": health.alerts,
        "strengths": health.strengths,
        "snapshot": {
            "total_balance": ctx.total_balance,
            "monthly_income": ctx.monthly_income,
            "monthly_expenses": ctx.monthly_expenses,
            "net_cash_flow": ctx.net_cash_flow,
            "top_categories": ctx.top_categories,
            "anomaly_count": len(ctx.anomalies),
            "subscription_count": len(ctx.subscriptions),
            "days_until_threshold": ctx.days_until_threshold,
        },
    }

@router.post("/analyze/stream")
async def analyze_stream(
    body: AnalyzeRequest,
    request: Request,
    user_id: int = Depends(get_current_user),
):
    if not body.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    routing = classify(body.query)
    ctx = await run_in_threadpool(build_context_from_daos, user_id)
    health = compute_health_score(ctx)
    prompt = build_prompt(routing.task_type, body.query, ctx, health)

    async def event_stream():
        override = get_model_override()

        # Determine actual model being used
        if override:
            actual_model = override["model_tag"]
            actual_backend = override["backend"]
        else:
            actual_model = routing.model_key
            actual_backend = "ollama"

        meta = {
            "type": "meta",
            "task_type": routing.task_type,
            "model_used": actual_model,
            "complexity": routing.complexity,
            "routing_confidence": routing.confidence,
            "health_score": health.overall,
            "health_grade": health.grade,
            "savings_vs_gpt4_usd": 0,
        }
        yield f"data: {json.dumps(meta)}\n\n"

        if override and override.get("backend") == "groq":
            from backend.ollama_client import _call_groq_direct
            result = await _call_groq_direct(override["model_tag"], prompt, 0.3, 900)
            yield f"data: {json.dumps({'type': 'token', 'text': result['text']})}\n\n"
        else:
            from backend.ollama_client import stream_ollama
            async for token in stream_ollama(routing.model_key, prompt):
                yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/classify")
async def classify_query(
    body: ClassifyRequest,
    user_id: int = Depends(get_current_user),
):
    d = classify(body.query)
    return {
        "task_type": d.task_type,
        "model": d.model_display,
        "model_key": d.model_key,
        "reasoning": d.reasoning,
        "complexity": d.complexity,
        "expected_tokens": d.expected_tokens,
        "confidence": d.confidence,
    }


@router.get("/status")
async def ai_status():
    from backend.ollama_client import check_backends
    return await check_backends()

@router.post("/model-preference")
async def set_model_preference(body: ModelPreferenceRequest):
    set_model_override(body.model_tag, body.backend)
    return {"status": "ok", "override": get_model_override()}

@router.get("/models")
async def list_models():
    # Get what's actually pulled in Ollama
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            pulled = [m["name"] for m in r.json().get("models", [])]
            print("Pulled models:", pulled)
    except:
        pulled = []

    groq_available = bool(GROQ_API_KEY)

    return {
        "current_override": get_model_override(),
        "ollama_models": [
            {"tag": tag, **info, "available": tag in pulled}
            for tag, info in AVAILABLE_MODELS.items()
            if info["size"] != "cloud"
        ],
        "groq_models": [
            {"tag": tag, **info, "available": groq_available}
            for tag, info in AVAILABLE_MODELS.items()
            if info["size"] == "cloud"
        ] if groq_available else [],
    }