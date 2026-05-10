from dataclasses import dataclass

# Cloud reference prices ($/1M tokens, input+output blended estimate)
CLOUD_PRICES_PER_1M = {
    "GPT-4": 30.00,
    "GPT-4o": 5.00,
    "Claude 3 Opus": 15.00,
    "Claude 3.5 Sonnet": 3.00,
    "GPT-3.5": 0.50,
}

# Local model = $0 (electricity negligible for demo purposes)
LOCAL_COST = 0.0


@dataclass
class CostMetrics:
    model_used: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    local_cost_usd: float

    # Savings vs cloud alternatives
    savings_vs_gpt4_usd: float
    savings_vs_gpt4o_usd: float
    savings_vs_gpt4_pct: float

    # Latency
    latency_ms: int

    # Human readable
    savings_display: str
    cost_display: str


def compute_metrics(
        model_key: str,
        model_display: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
) -> CostMetrics:
    total_tokens = prompt_tokens + completion_tokens
    tokens_in_millions = total_tokens / 1_000_000

    local_cost = 0.0

    gpt4_cost = CLOUD_PRICES_PER_1M["GPT-4"] * tokens_in_millions
    gpt4o_cost = CLOUD_PRICES_PER_1M["GPT-4o"] * tokens_in_millions

    savings_vs_gpt4 = gpt4_cost - local_cost
    savings_vs_gpt4o = gpt4o_cost - local_cost
    savings_pct = 100.0  # local = 100% savings vs cloud

    if gpt4_cost < 0.001:
        cost_display = "< $0.001"
        savings_display = f"Saved ~${gpt4_cost:.4f} vs GPT-4 | ~${gpt4o_cost:.4f} vs GPT-4o"
    else:
        cost_display = f"${local_cost:.4f}"
        savings_display = f"Saved ${savings_vs_gpt4:.4f} vs GPT-4 | ${savings_vs_gpt4o:.4f} vs GPT-4o"

    return CostMetrics(
        model_used=model_display,
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        local_cost_usd=local_cost,
        savings_vs_gpt4_usd=round(savings_vs_gpt4, 6),
        savings_vs_gpt4o_usd=round(savings_vs_gpt4o, 6),
        savings_vs_gpt4_pct=savings_pct,
        latency_ms=latency_ms,
        savings_display=savings_display,
        cost_display=cost_display,
    )


def estimate_prompt_tokens(text: str) -> int:
    """Rough token estimate before sending to model."""
    return max(1, len(text) // 4)