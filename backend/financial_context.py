import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

# Your existing DAOs — import directly
from fintracker_base.databaseDAO.Account.account_dao import get_all_accounts
from fintracker_base.databaseDAO.transaction.transaction_DAO import get_all_transactions
from fintracker_base.Visuals.ExchangeRates import get_currency_converter


@dataclass
class FinancialContext:
    user_id: int
    accounts: list
    transactions: list

    total_balance: float = 0.0
    monthly_income: float = 0.0
    monthly_expenses: float = 0.0
    net_cash_flow: float = 0.0

    top_categories: dict = field(default_factory=dict)
    monthly_totals: dict = field(default_factory=dict)
    subscriptions: list = field(default_factory=list)
    anomalies: list = field(default_factory=list)

    avg_monthly_expenses_3m: float = 0.0
    expense_change_pct: float = 0.0
    days_until_threshold: Optional[int] = None
    summary_text: str = ""


def build_context_from_daos(user_id: int) -> FinancialContext:
    """
    Synchronous. Call via run_in_threadpool() from async endpoints.
    Uses your existing DAO functions — no new DB connections opened.
    """
    accounts = get_all_accounts(user_id) or []
    transactions = get_all_transactions(user_id) or []

    accounts = _normalize(accounts)
    transactions = _normalize(transactions)

    ctx = FinancialContext(
        user_id=user_id,
        accounts=accounts,
        transactions=transactions,
    )
    _compute(ctx)
    return ctx


def _normalize(items):
    """Convert ORM objects to dicts if needed."""
    result = []
    for item in items:
        if isinstance(item, dict):
            result.append(item)
        elif hasattr(item, '__dict__'):
            result.append({k: v for k, v in item.__dict__.items() if not k.startswith('_')})
        else:
            result.append(item)
    return result


def _compute(ctx: FinancialContext, total_balance: float = None):
    if total_balance is not None:
        ctx.total_balance = total_balance
    else:
        # fallback — same currency assumed
        ctx.total_balance = sum(float(a.get("account_balance", a.get("balance", 0)) or 0) for a in ctx.accounts)

    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    prev_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

    by_month = defaultdict(lambda: {"income": 0.0, "expenses": 0.0})
    cat_by_month = defaultdict(lambda: defaultdict(float))
    desc_by_month = defaultdict(set)

    for tx in ctx.transactions:
        raw_date = (
                tx.get("transaction_date") or
                tx.get("date") or
                tx.get("created_at") or
                str(now.date())
        )
        try:
            month_key = datetime.fromisoformat(str(raw_date)[:10]).strftime("%Y-%m")
        except Exception:
            month_key = current_month

        raw_amount = float(tx.get("amount", 0) or 0)
        amount = abs(raw_amount)
        tx_type = str(tx.get("type", tx.get("transaction_type", ""))).lower()
        is_income = raw_amount > 0 or tx_type in ("income", "credit", "deposit")

        if is_income:
            by_month[month_key]["income"] += amount
        else:
            by_month[month_key]["expenses"] += amount
            cat_name = str(tx.get("category_name", tx.get("name", "other"))).lower()
            cat_by_month[month_key][cat_name] += amount

        desc = str(tx.get("name", tx.get("description", ""))).strip().lower()
        if desc and len(desc) > 2:
            desc_by_month[desc].add(month_key)

    ctx.monthly_totals = {k: dict(v) for k, v in by_month.items()}
    ctx.monthly_income = by_month[current_month]["income"]
    ctx.monthly_expenses = by_month[current_month]["expenses"]
    ctx.net_cash_flow = ctx.monthly_income - ctx.monthly_expenses

    recent = [by_month[m]["expenses"] for m in sorted(by_month)[-3:]]
    ctx.avg_monthly_expenses_3m = statistics.mean(recent) if recent else ctx.monthly_expenses

    prev_exp = by_month[prev_month]["expenses"]
    if prev_exp > 0:
        ctx.expense_change_pct = round(((ctx.monthly_expenses - prev_exp) / prev_exp) * 100, 1)

    ctx.top_categories = dict(
        sorted(cat_by_month[current_month].items(), key=lambda x: x[1], reverse=True)[:6]
    )

    ctx.subscriptions = [d for d, months in desc_by_month.items() if len(months) >= 2][:10]

    cat_amounts = defaultdict(list)
    for tx in ctx.transactions:
        amt = abs(float(tx.get("amount", 0) or 0))
        cat = str(tx.get("category_name", tx.get("name", "other"))).lower()
        cat_amounts[cat].append((amt, tx))

    for cat, entries in cat_amounts.items():
        amounts = [e[0] for e in entries]
        if len(amounts) < 3:
            continue
        mean = statistics.mean(amounts)
        stdev = statistics.stdev(amounts)
        if stdev == 0:
            continue
        for amt, tx in entries:
            z = (amt - mean) / stdev
            if z > 2.5:
                ctx.anomalies.append({
                    "name": tx.get("name", "Unknown"),
                    "amount": amt,
                    "category": cat,
                    "mean": round(mean, 2),
                    "z_score": round(z, 2),
                })

    if ctx.net_cash_flow < 0:
        savings = [a for a in ctx.accounts if "sav" in str(a.get("type", "")).lower()]
        if savings:
            bal = sum(float(a.get("balance", 0)) for a in savings)
            daily_burn = abs(ctx.net_cash_flow) / 30
            if daily_burn > 0 and bal > 1000:
                ctx.days_until_threshold = int((bal - 1000) / daily_burn)

    ctx.summary_text = _summary(ctx)


def _summary(ctx: FinancialContext) -> str:
    lines = [
        f"FINANCIAL SNAPSHOT (user {ctx.user_id})",
        f"Accounts: {len(ctx.accounts)} | Total balance: ${ctx.total_balance:,.2f}",
        f"This month — Income: ${ctx.monthly_income:,.2f} | Expenses: ${ctx.monthly_expenses:,.2f} | Net: ${ctx.net_cash_flow:+,.2f}",
        f"3-month avg expenses: ${ctx.avg_monthly_expenses_3m:,.2f} | MoM change: {ctx.expense_change_pct:+.1f}%",
        "",
        "TOP SPENDING CATEGORIES:",
    ]
    for cat, amt in ctx.top_categories.items():
        lines.append(f"  {cat.title()}: ${amt:,.2f}")
    if ctx.subscriptions:
        lines.append(f"\nRECURRING CHARGES ({len(ctx.subscriptions)}): {', '.join(ctx.subscriptions[:5])}")
    if ctx.anomalies:
        lines.append(f"\nANOMALIES ({len(ctx.anomalies)}):")
        for a in ctx.anomalies[:3]:
            lines.append(f"  {a['name']}: ${a['amount']:.2f} (avg ${a['mean']:.2f} in {a['category']})")
    if ctx.days_until_threshold:
        lines.append(f"\n⚠ WARNING: Savings may fall below $1,000 in {ctx.days_until_threshold} days")
    return "\n".join(lines)

def build_context_from_daos(user_id: int, base_currency: str = "USD") -> FinancialContext:
    accounts = get_all_accounts(user_id) or []
    transactions = get_all_transactions(user_id) or []

    accounts = _normalize(accounts)
    transactions = _normalize(transactions)

    # ← Currency conversion using your existing converter
    converter = get_currency_converter()
    converted = converter.convert_accounts(accounts, base_currency)
    total_balance = converted["total_balance"]

    ctx = FinancialContext(
        user_id=user_id,
        accounts=accounts,
        transactions=transactions,
    )
    _compute(ctx, total_balance)
    return ctx
