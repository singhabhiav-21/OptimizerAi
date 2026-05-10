from dataclasses import dataclass
from typing import Literal
from backend.financial_context import FinancialContext


@dataclass
class HealthScore:
    overall: int  # 0-100
    savings_score: int  # 0-100
    cash_flow_score: int  # 0-100
    spending_stability_score: int  # 0-100
    anomaly_risk_score: int  # 0-100

    grade: Literal["A", "B", "C", "D", "F"]
    summary: str
    alerts: list[str]
    strengths: list[str]


def compute_health_score(ctx: FinancialContext) -> HealthScore:
    alerts = []
    strengths = []

    # ── 1. Savings Score (0-100) ─────────────────────────────────────────────
    # Based on: balance vs monthly expenses ratio (emergency fund metric)
    savings_score = 50  # baseline
    if ctx.avg_monthly_expenses_3m > 0:
        months_covered = ctx.total_balance / ctx.avg_monthly_expenses_3m
        if months_covered >= 6:
            savings_score = 100
            strengths.append(f"Strong emergency fund ({months_covered:.1f} months of expenses covered)")
        elif months_covered >= 3:
            savings_score = 75
            strengths.append(f"Adequate emergency fund ({months_covered:.1f} months covered)")
        elif months_covered >= 1:
            savings_score = 50
            alerts.append(f"Emergency fund covers only {months_covered:.1f} months — target is 3–6 months")
        else:
            savings_score = 20
            alerts.append("⚠ Critical: Emergency fund below 1 month of expenses")
    else:
        savings_score = 40

    # ── 2. Cash Flow Score (0-100) ────────────────────────────────────────────
    cash_flow_score = 50
    if ctx.monthly_income > 0:
        savings_rate = ctx.net_cash_flow / ctx.monthly_income
        if savings_rate >= 0.20:
            cash_flow_score = 100
            strengths.append(f"Excellent savings rate: {savings_rate * 100:.0f}% of income saved this month")
        elif savings_rate >= 0.10:
            cash_flow_score = 78
            strengths.append(f"Healthy savings rate: {savings_rate * 100:.0f}%")
        elif savings_rate >= 0:
            cash_flow_score = 55
            alerts.append(f"Low savings rate this month: {savings_rate * 100:.0f}% (target: 20%)")
        else:
            cash_flow_score = 20
            alerts.append(f"⚠ Negative cash flow this month: spending exceeds income by ${abs(ctx.net_cash_flow):,.0f}")
    elif ctx.net_cash_flow < 0:
        cash_flow_score = 15
        alerts.append(f"⚠ Negative cash flow: ${abs(ctx.net_cash_flow):,.0f} deficit this month")

    # ── 3. Spending Stability Score (0-100) ───────────────────────────────────
    stability_score = 75  # default good
    change = ctx.expense_change_pct
    if abs(change) <= 5:
        stability_score = 95
        strengths.append("Consistent spending pattern — low variance month-over-month")
    elif abs(change) <= 15:
        stability_score = 75
    elif abs(change) <= 30:
        stability_score = 50
        direction = "up" if change > 0 else "down"
        alerts.append(f"Spending shifted {change:+.0f}% {direction} vs last month")
    else:
        stability_score = 25
        alerts.append(f"⚠ Large spending spike: {change:+.0f}% vs last month — review transactions")

    # ── 4. Anomaly Risk Score (0-100, higher = lower risk) ───────────────────
    anomaly_count = len(ctx.anomalies)
    if anomaly_count == 0:
        anomaly_score = 100
        strengths.append("No unusual transactions detected")
    elif anomaly_count <= 2:
        anomaly_score = 70
        alerts.append(f"{anomaly_count} unusual transaction(s) detected — verify these are expected")
    elif anomaly_count <= 5:
        anomaly_score = 45
        alerts.append(f"⚠ {anomaly_count} anomalous transactions detected — possible unauthorized charges")
    else:
        anomaly_score = 20
        alerts.append(f"🚨 {anomaly_count} anomalous transactions — immediate review recommended")

    # ── Overall Score (weighted average) ─────────────────────────────────────
    overall = int(
        savings_score * 0.30 +
        cash_flow_score * 0.35 +
        stability_score * 0.20 +
        anomaly_score * 0.15
    )

    # Grade
    if overall >= 85:
        grade = "A"
    elif overall >= 70:
        grade = "B"
    elif overall >= 55:
        grade = "C"
    elif overall >= 40:
        grade = "D"
    else:
        grade = "F"

    # Summary
    summary = _build_summary(overall, grade, ctx, alerts)

    return HealthScore(
        overall=overall,
        savings_score=savings_score,
        cash_flow_score=cash_flow_score,
        spending_stability_score=stability_score,
        anomaly_risk_score=anomaly_score,
        grade=grade,
        summary=summary,
        alerts=alerts,
        strengths=strengths,
    )


def _build_summary(overall: int, grade: str, ctx: FinancialContext, alerts: list) -> str:
    if overall >= 85:
        tone = "Your finances are in excellent shape."
    elif overall >= 70:
        tone = "Your finances are generally healthy with a few areas to watch."
    elif overall >= 55:
        tone = "Your financial health needs attention in several areas."
    else:
        tone = "Your finances are under stress — immediate action recommended."

    details = []
    if ctx.days_until_threshold is not None:
        details.append(f"At current burn rate, savings may fall below threshold in {ctx.days_until_threshold} days.")
    if ctx.expense_change_pct > 20:
        details.append(f"Spending is up {ctx.expense_change_pct:.0f}% vs last month.")
    if ctx.subscriptions:
        details.append(f"{len(ctx.subscriptions)} recurring charges detected.")

    return tone + (" " + " ".join(details) if details else "")