from backend.financial_context import FinancialContext
from backend.healthScore import HealthScore

PROMPTS = {
    "spending_summary": """
{context}

QUESTION: {query}

Analyze spending. Give:
1. Breakdown of where money is going with actual dollar amounts
2. Which categories are highest relative to necessity
3. Specific dollar amount realistically saveable this month
4. One concrete action to take this week
""",
    "trend_analysis": """
{context}

QUESTION: {query}

Analyze trends across months shown. Give:
1. Key rising/falling categories with % change
2. Whether trajectory is concerning or healthy
3. Projected impact if trend continues 3 more months
4. Specific dollar intervention target
""",
    "anomaly_detection": """
{context}

QUESTION: {query}

Review the anomalies listed. Give:
1. Which are most suspicious and why
2. Whether pattern suggests fraud, billing error, or lifestyle change
3. Specific transactions to verify immediately
""",
    "subscription_detection": """
{context}

QUESTION: {query}

Analyze recurring charges. Give:
1. Estimated monthly total of all recurring charges
2. Which are likely forgotten or unused
3. Estimated annual savings if low-value ones are cancelled
4. Priority order for what to cancel first
""",
    "forecasting": """
{context}

QUESTION: {query}

Forecast using real data above:
1. Projected balance in 30, 60, 90 days at current spend rate (exact numbers)
2. Key risk if a large unexpected expense hits
3. Monthly savings target to improve trajectory
4. Specific milestone achievable and by when
""",
    "what_if_simulation": """
{context}

QUESTION: {query}

Run the what-if scenario using real numbers:
1. Current state baseline (exact figures)
2. Projected state under the scenario
3. Time to goal under conservative / moderate / aggressive effort
4. Recommended action plan
""",
    "health_score": """
{context}

HEALTH SCORE: {health_score}/100 (Grade {health_grade})
Savings: {savings_score}/100 | Cash Flow: {cash_flow_score}/100 | Stability: {stability_score}/100 | Anomaly Risk: {anomaly_score}/100

QUESTION: {query}

Explain the score:
1. What each sub-score means for this specific user
2. Top 2 factors dragging the score down
3. Fastest path to +10 points
4. Realistic score achievable in 90 days
""",
    "recommendation": """
{context}

QUESTION: {query}

Provide financial recommendations:
1. Top 3 specific actions ranked by dollar impact (include exact amounts)
2. One quick win implementable today
3. One structural change for long-term improvement
""",
    "general_qa": """
{context}

QUESTION: {query}

Answer using the financial data above. Be specific with numbers.
End with at least one concrete action.
""",
}


def build_prompt(task_type: str, query: str, ctx: FinancialContext, health: HealthScore) -> str:
    template = PROMPTS.get(task_type, PROMPTS["general_qa"])
    return template.format(
        context=ctx.summary_text,
        query=query,
        health_score=health.overall,
        health_grade=health.grade,
        savings_score=health.savings_score,
        cash_flow_score=health.cash_flow_score,
        stability_score=health.spending_stability_score,
        anomaly_score=health.anomaly_risk_score,
    )


def build_proactive_alerts(ctx: FinancialContext, health: HealthScore) -> list:
    alerts = []
    if ctx.expense_change_pct > 25:
        alerts.append(f"Spending up {ctx.expense_change_pct:.0f}% vs last month")
    if ctx.net_cash_flow < 0:
        alerts.append(f"Negative cash flow: ${abs(ctx.net_cash_flow):,.0f} deficit this month")
    if ctx.days_until_threshold and ctx.days_until_threshold < 60:
        alerts.append(f"Savings may fall below threshold in {ctx.days_until_threshold} days")
    if len(ctx.anomalies) > 0:
        alerts.append(f"{len(ctx.anomalies)} unusual transaction(s) detected")
    if len(ctx.subscriptions) > 3:
        alerts.append(f"{len(ctx.subscriptions)} recurring charges detected")
    if health.overall < 50:
        alerts.append(f"Health score {health.overall}/100 — multiple risk factors")
    return alerts