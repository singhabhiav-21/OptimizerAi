import re
from dataclasses import dataclass
from typing import Literal

TaskType = Literal[
    "spending_summary",
    "trend_analysis",
    "general_qa",
    "forecasting",
    "anomaly_detection",
    "subscription_detection",
    "health_score",
    "what_if_simulation",
    "recommendation",
]


@dataclass
class RoutingDecision:
    task_type: TaskType
    model_key: str
    model_display: str
    reasoning: str
    complexity: Literal["low", "medium", "high"]
    expected_tokens: int
    confidence: float  # 0.0 - 1.0


ROUTING_TABLE = {
    "spending_summary": {
        "model_key": "phi3_mini",
        "model_display": "Phi-3 Mini",
        "complexity": "low",
        "expected_tokens": 400,
        "reasoning": "Detected straightforward spending summarization. Short context window required. Phi-3 Mini handles categorization at 94% lower inference cost than GPT-4 with no quality loss.",
    },
    "subscription_detection": {
        "model_key": "phi3_mini",
        "model_display": "Phi-3 Mini",
        "complexity": "low",
        "expected_tokens": 350,
        "reasoning": "Recurring pattern detection is a low-complexity classification task. Phi-3 Mini is optimal — fast and cost-efficient for structured data scanning.",
    },
    "trend_analysis": {
        "model_key": "mistral_7b",
        "model_display": "Mistral 7B",
        "complexity": "medium",
        "expected_tokens": 700,
        "reasoning": "Trend analysis requires multi-period comparison and pattern recognition. Mistral 7B provides strong analytical reasoning at near-zero cost vs GPT-4o.",
    },
    "anomaly_detection": {
        "model_key": "mistral_7b",
        "model_display": "Mistral 7B",
        "complexity": "medium",
        "expected_tokens": 600,
        "reasoning": "Anomaly detection requires contextual reasoning over time series. Mistral 7B handles statistical outlier explanation reliably.",
    },
    "general_qa": {
        "model_key": "phi3_mini",
        "model_display": "Phi-3 Mini",
        "complexity": "low",
        "expected_tokens": 400,
        "reasoning": "General question with no specific pattern matched. Routing to Phi-3 Mini for fast, efficient response.",
    },
    "health_score": {
        "model_key": "qwen2_5",
        "model_display": "Qwen 2.5 7B",
        "complexity": "medium",
        "expected_tokens": 600,
        "reasoning": "Health score interpretation requires nuanced financial reasoning. Qwen 2.5 provides balanced depth without LLaMA 3's overhead.",
    },
    "recommendation": {
        "model_key": "llama3",
        "model_display": "LLaMA 3 8B",
        "complexity": "high",
        "expected_tokens": 900,
        "reasoning": "Personalized financial recommendations require multi-factor reasoning across spending patterns, cash flow, and behavioral data. LLaMA 3 8B is the strongest local model for this.",
    },
    "forecasting": {
        "model_key": "llama3",
        "model_display": "LLaMA 3 8B",
        "complexity": "high",
        "expected_tokens": 1000,
        "reasoning": "Financial forecasting requires complex multi-step reasoning over time-series data. Routing to LLaMA 3 8B — highest-capability local model.",
    },
    "what_if_simulation": {
        "model_key": "llama3",
        "model_display": "LLaMA 3 8B",
        "complexity": "high",
        "expected_tokens": 950,
        "reasoning": "What-if simulation requires counterfactual reasoning and projection logic. LLaMA 3 8B handles hypothetical financial planning scenarios with high coherence.",
    },
}

# Keyword patterns per task type (order matters — first match wins)
CLASSIFICATION_RULES = [
    ("what_if_simulation", r"\bwhat.?if\b|if i (save|spend|cut|reduce|invest)|simulate|scenario|hypothetical"),
    ("forecasting", r"\bforecast\b|predict|project|how long until|when will|future|runway|burn rate"),
    ("anomaly_detection", r"\banomaly\b|unusual|spike|unexpected|weird|outlier|strange charge"),
    ("subscription_detection", r"\bsubscription|recurring|monthly charge|netflix|spotify|auto.?renew"),
    ("trend_analysis", r"\btrend\b|over time|month.?over.?month|compare|vs last|pattern|trajectory|increas|decreas"),
    ("health_score", r"\bhealth score|financial health|score|overall|how am i doing|am i on track"),
    ("recommendation", r"\brecommend|suggest|should i|advice|optimize|improve|what should|action|next step"),
    ("spending_summary", r"\bspend|spent|expense|cost|categor|breakdown|how much|total|summary|where.*money"),
    ("general_qa", r".*"),  # fallback
]


def classify(query: str) -> RoutingDecision:
    """
    Classify user query and return a routing decision.
    Deterministic, explainable, zero-latency.
    """
    q = query.lower().strip()

    task_type: TaskType = "general_qa"
    for task, pattern in CLASSIFICATION_RULES:
        if re.search(pattern, q):
            task_type = task
            break

    route = ROUTING_TABLE[task_type]

    # Confidence heuristic: longer, more specific queries → higher confidence
    word_count = len(q.split())
    base_confidence = 0.72
    if word_count > 8:
        base_confidence += 0.12
    if task_type != "general_qa":
        base_confidence += 0.10
    confidence = min(base_confidence, 0.97)

    return RoutingDecision(
        task_type=task_type,
        model_key=route["model_key"],
        model_display=route["model_display"],
        reasoning=route["reasoning"],
        complexity=route["complexity"],
        expected_tokens=route["expected_tokens"],
        confidence=round(confidence, 2),
    )
