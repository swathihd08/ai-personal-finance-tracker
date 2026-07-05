from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import pandas as pd
from fpdf import FPDF

from utils.ml_utils import predict_category

ROOT_DIR = Path(__file__).resolve().parents[1]


def infer_transaction_type(amount: float, description: str) -> str:
    lowered = description.lower()
    income_keywords = ["salary", "refund", "bonus", "commission", "interest", "investment", "dividend", "income"]
    if any(keyword in lowered for keyword in income_keywords) or amount < 0:
        return "income"
    return "expense"


def _resolve_category(description: str, category: str | None, transaction_type: str) -> str:
    if category and str(category).strip() and str(category).strip().lower() not in {"others", "unknown", ""}:
        return str(category).strip()
    if transaction_type == "income":
        return "Salary" if "salary" in description.lower() else "Income"
    return predict_category(description)


def parse_uploaded_file(uploaded_file) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    normalized = {}
    for column in df.columns:
        normalized[column.lower().strip()] = column

    rename_map = {}
    for source_name, target_name in {"date": "date", "description": "description", "amount": "amount", "account": "account", "payment method": "payment_method", "category": "category"}.items():
        if source_name in normalized:
            rename_map[normalized[source_name]] = target_name
    df = df.rename(columns=rename_map)

    if "date" not in df.columns:
        raise ValueError("Uploaded file must contain a date column")
    if "description" not in df.columns:
        raise ValueError("Uploaded file must contain a description column")
    if "amount" not in df.columns:
        raise ValueError("Uploaded file must contain an amount column")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["description"] = df["description"].fillna("Unknown").astype(str)
    df["account"] = df.get("account", pd.Series(["Unknown"] * len(df))).fillna("Unknown").astype(str)
    df["payment_method"] = df.get("payment_method", pd.Series(["Unknown"] * len(df))).fillna("Unknown").astype(str)
    df["type"] = df.apply(lambda row: infer_transaction_type(float(row["amount"]), str(row["description"])), axis=1)
    df["category"] = df.apply(lambda row: _resolve_category(str(row["description"]), row.get("category"), str(row["type"])), axis=1)
    df["source"] = "upload"
    return df[["date", "description", "amount", "account", "payment_method", "category", "type", "source"]].dropna(subset=["date", "amount"]).reset_index(drop=True)


def prepare_transaction_records(df: pd.DataFrame) -> list[dict]:
    return [
        {
            "date": row["date"].strftime("%Y-%m-%d"),
            "description": str(row["description"]),
            "amount": float(row["amount"]),
            "account": str(row.get("account", "Unknown")),
            "payment_method": str(row.get("payment_method", "Unknown")),
            "category": _resolve_category(str(row["description"]), str(row.get("category", "")), str(row.get("type", "expense"))),
            "type": str(row.get("type", "expense")),
            "source": str(row.get("source", "upload")),
        }
        for _, row in df.iterrows()
    ]


def transaction_to_dataframe(transactions: list[dict]) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=["date", "description", "amount", "account", "payment_method", "category", "type", "source"])
    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df["category"] = df["category"].fillna("Others")
    df["payment_method"] = df["payment_method"].fillna("Unknown")
    df["account"] = df["account"].fillna("Unknown")
    df["type"] = df.get("type", pd.Series(["expense"] * len(df))).fillna("expense")
    return df.sort_values("date", ascending=False).reset_index(drop=True)


def apply_filters(df: pd.DataFrame, start_date, end_date, category_filter: str, payment_filter: str, amount_min: float, amount_max: float) -> pd.DataFrame:
    filtered = df.copy()
    if filtered.empty:
        return filtered
    filtered = filtered[(filtered["date"] >= pd.Timestamp(start_date)) & (filtered["date"] <= pd.Timestamp(end_date))]
    if category_filter != "All":
        filtered = filtered[filtered["category"] == category_filter]
    if payment_filter != "All":
        filtered = filtered[filtered["payment_method"] == payment_filter]
    filtered = filtered[(filtered["amount"] >= amount_min) & (filtered["amount"] <= amount_max)]
    return filtered.sort_values("date", ascending=False).reset_index(drop=True)


def compute_summary(transactions: list[dict]) -> dict:
    if not transactions:
        return {
            "total_income": 0.0,
            "total_expenses": 0.0,
            "savings": 0.0,
            "savings_rate": 0.0,
            "current_balance": 0.0,
        }
    df = transaction_to_dataframe(transactions)
    total_income = float(df.loc[df["type"] == "income", "amount"].sum())
    total_expenses = float(df.loc[df["type"] == "expense", "amount"].sum())
    savings = total_income - total_expenses
    savings_rate = savings / total_income if total_income else 0.0
    return {
        "total_income": total_income,
        "total_expenses": total_expenses,
        "savings": savings,
        "savings_rate": savings_rate,
        "current_balance": savings,
    }


def build_dashboard_data(transactions: list[dict]) -> dict:
    df = transaction_to_dataframe(transactions)
    return {
        "summary": compute_summary(transactions),
        "df": df,
    }


def generate_budget_alerts(transactions: list[dict], budgets: dict) -> list[str]:
    alerts = []
    df = transaction_to_dataframe(transactions)
    expense_df = df[df["type"] == "expense"].copy()
    for category, budget in budgets.items():
        if not budget:
            continue
        spent = float(expense_df.loc[expense_df["category"] == category, "amount"].sum()) if category in expense_df["category"].values else 0.0
        if spent > float(budget):
            alerts.append(f"⚠ You have exceeded your {category} budget by ₹{spent - float(budget):,.0f}.")
    return alerts


def generate_insights(transactions: list[dict]) -> list[str]:
    if not transactions:
        return ["Add transactions to see savings insights."]
    df = transaction_to_dataframe(transactions)
    expense_df = df[df["type"] == "expense"]
    category_summary = expense_df.groupby("category").agg(amount=("amount", "sum")).reset_index().sort_values("amount", ascending=False)
    if category_summary.empty:
        return ["You are on track with your spending."]
    top_category = category_summary.iloc[0]["category"]
    top_amount = float(category_summary.iloc[0]["amount"])
    summary = compute_summary(transactions)
    insights = [
        f"You saved ₹{summary['savings']:,.0f} this month.",
        f"{top_category} is your largest spending category at ₹{top_amount:,.0f}.",
        "Try reducing discretionary spending to improve your savings rate.",
    ]
    return insights


def build_next_month_prediction(transactions: list[dict]) -> float:
    if not transactions:
        return 0.0
    df = transaction_to_dataframe(transactions)
    monthly = df.groupby(df["date"].dt.to_period("M")).agg(amount=("amount", "sum"))
    if monthly.empty:
        return 0.0
    values = monthly["amount"].astype(float).to_list()
    if len(values) < 2:
        return values[-1] if values else 0.0
    x = list(range(1, len(values) + 1))
    trend = sum((x[i] * values[i]) for i in range(len(values))) / sum(x)
    return float(max(0, trend))


def export_transactions_excel(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue()


def export_transactions_pdf(df: pd.DataFrame) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    pdf.cell(200, 10, txt="AI Personal Finance Tracker - Summary", ln=True, align="C")
    pdf.ln(5)
    for _, row in df.head(10).iterrows():
        # Convert to string and remove problematic Unicode characters
        date_str = str(row['date'])
        desc_str = str(row['description']).replace('₹', 'Rs.').replace('€', 'E').replace('£', 'L')
        amount_str = str(row['amount'])
        cat_str = str(row['category'])
        # Use latin-1 encoding for PDF compatibility
        txt = f"{date_str} | {desc_str} | Rs.{amount_str} | {cat_str}"
        txt = txt.encode('latin-1', errors='replace').decode('latin-1')
        pdf.multi_cell(190, 6, txt=txt)
    buffer = io.BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()
