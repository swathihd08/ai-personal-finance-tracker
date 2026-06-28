import json
from pathlib import Path
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.auth import (
    authenticate_user,
    create_user,
    ensure_storage,
    load_user_store,
    save_user_store,
)
from utils.data_utils import (
    build_dashboard_data,
    compute_summary,
    export_transactions_excel,
    export_transactions_pdf,
    infer_transaction_type,
    parse_uploaded_file,
    prepare_transaction_records,
    transaction_to_dataframe,
    apply_filters,
    generate_budget_alerts,
    generate_insights,
    build_next_month_prediction,
)
from utils.ml_utils import ensure_model_ready, predict_category, get_model_metrics


st.set_page_config(page_title="AI Personal Finance Tracker", page_icon="💰", layout="wide")
ensure_storage()


def inject_css() -> None:
    st.markdown(
        """
        <style>
            :root { color-scheme: dark; }
            .stApp { background: linear-gradient(135deg, #0f172a 0%, #111827 35%, #1f2937 100%); }
            .stMetric { background: rgba(255,255,255,0.06); padding: 16px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.08); }
            .block-container { padding-top: 2rem; padding-bottom: 2rem; }
            div[data-testid="stSidebar"] { background: #020617; }
            .stTabs [data-baseweb="tab-list"] { gap: 8px; }
            .stTabs [data-baseweb="tab"] { border-radius: 999px; padding: 8px 16px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()


def get_current_user_data() -> tuple[dict, list[dict], dict]:
    store = load_user_store()
    username = st.session_state.get("current_user")
    if not username:
        return store, [], {}
    user_data = store.get(username, {})
    transactions = user_data.get("transactions", [])
    budgets = user_data.get("budgets", {})
    return store, transactions, budgets


def save_current_user_data(store: dict, transactions: list[dict], budgets: dict) -> None:
    username = st.session_state.get("current_user")
    if not username:
        return
    store[username] = {
        **store.get(username, {}),
        "transactions": transactions,
        "budgets": budgets,
        "full_name": store.get(username, {}).get("full_name", username),
        "password_hash": store.get(username, {}).get("password_hash", ""),
    }
    save_user_store(store)


def render_auth() -> None:
    st.title("💸 AI Personal Finance Tracker")
    st.caption("Upload statements, categorize expenses with AI, and take control of your money.")

    auth_tab, signup_tab = st.tabs(["Login", "Sign Up"])

    with auth_tab:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Log in", use_container_width=True):
            user = authenticate_user(username, password)
            if user:
                st.session_state.authenticated = True
                st.session_state.current_user = username
                st.rerun()
            else:
                st.error("Invalid username or password")

    with signup_tab:
        full_name = st.text_input("Full Name", key="signup_name")
        username = st.text_input("New Username", key="signup_user")
        password = st.text_input("Create Password", type="password", key="signup_pass")
        if st.button("Create account", use_container_width=True):
            if not username or not password:
                st.warning("Please provide a username and password")
            else:
                success = create_user(username, password, full_name=full_name)
                if success:
                    st.success("Account created. Please log in.")
                else:
                    st.error("Username already exists")


def render_dashboard(transactions: list[dict], budgets: dict) -> None:
    summary = compute_summary(transactions)
    st.subheader("📊 Financial Dashboard")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Income", f"₹{summary['total_income']:,.0f}")
    col2.metric("Total Expenses", f"₹{summary['total_expenses']:,.0f}")
    col3.metric("Savings", f"₹{summary['savings']:,.0f}")
    col4.metric("Savings Rate", f"{summary['savings_rate']:.1%}")
    col5.metric("Current Balance", f"₹{summary['current_balance']:,.0f}")

    if transactions:
        df = transaction_to_dataframe(transactions)
        monthly = df.groupby(df["date"].dt.to_period("M")).agg(total_expense=("amount", "sum"), total_income=("amount", lambda s: s.sum() if "income" in s.name else 0))
        monthly = monthly.reset_index()
        monthly["date"] = monthly["date"].astype(str)

        fig1 = px.line(monthly, x="date", y="total_expense", markers=True, title="Monthly Spending")
        fig2 = px.pie(df[df["type"] == "expense"], names="category", values="amount", title="Expense by Category")
        fig3 = px.bar(df.groupby("date").agg(amount=("amount", "sum")).reset_index(), x="date", y="amount", title="Daily Spending Trend")
        fig4 = px.bar(df.groupby("category").agg(amount=("amount", "sum")).reset_index().sort_values("amount", ascending=False), x="category", y="amount", title="Top Spending Categories")

        c1, c2 = st.columns(2)
        c1.plotly_chart(fig1, use_container_width=True)
        c2.plotly_chart(fig2, use_container_width=True)
        c1.plotly_chart(fig3, use_container_width=True)
        c2.plotly_chart(fig4, use_container_width=True)

        st.subheader("🧠 AI Savings Insights")
        insights = generate_insights(transactions)
        for insight in insights:
            st.info(insight)

        st.subheader("🚨 Budget Alerts")
        alerts = generate_budget_alerts(transactions, budgets)
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.success("No budget alerts at the moment.")

        st.subheader("🔮 Next Month Forecast")
        forecast = build_next_month_prediction(transactions)
        st.metric("Predicted Next Month Spending", f"₹{forecast:,.0f}")
    else:
        st.info("Add transactions to unlock dashboards and insights.")


def render_transactions(transactions: list[dict], store: dict) -> None:
    st.subheader("🧾 Transactions")
    df = transaction_to_dataframe(transactions)

    with st.expander("Manual Entry"):
        col1, col2, col3 = st.columns(3)
        manual_date = col1.date_input("Date", value=datetime.today())
        manual_description = col2.text_input("Description")
        manual_amount = col3.number_input("Amount", min_value=0.0, step=1.0)
        col4, col5, col6 = st.columns(3)
        payment_method = col4.selectbox("Payment Method", ["Card", "Cash", "UPI", "Bank Transfer", "Wallet"])
        category = col5.text_input("Category (optional)")
        type_value = col6.selectbox("Type", ["Expense", "Income"])
        if st.button("Save Transaction"):
            if manual_description:
                resolved_category = category.strip() or ("Salary" if type_value == "Income" else "")
                if not resolved_category:
                    from utils.data_utils import _resolve_category

                    resolved_category = _resolve_category(manual_description, "", "income" if type_value == "Income" else "expense")
                record = {
                    "date": manual_date.strftime("%Y-%m-%d"),
                    "description": manual_description,
                    "amount": float(manual_amount),
                    "payment_method": payment_method,
                    "category": resolved_category,
                    "account": "Manual",
                    "type": "income" if type_value == "Income" else "expense",
                    "source": "manual",
                }
                transactions.append(record)
                save_current_user_data(store, transactions, store.get(st.session_state.current_user, {}).get("budgets", {}))
                st.success("Transaction saved")
                st.rerun()

    with st.expander("Upload Statement"):
        uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"])
        if uploaded is not None:
            parsed_df = parse_uploaded_file(uploaded)
            st.dataframe(parsed_df, use_container_width=True)
            if st.button("Import Uploaded Records"):
                prepared = prepare_transaction_records(parsed_df)
                transactions.extend(prepared)
                save_current_user_data(store, transactions, store.get(st.session_state.current_user, {}).get("budgets", {}))
                st.success(f"Imported {len(prepared)} transactions")
                st.rerun()

    with st.expander("Filter Transactions"):
        col1, col2, col3, col4 = st.columns(4)
        start_date = col1.date_input("Start Date", value=df["date"].min() if not df.empty else datetime.today())
        end_date = col2.date_input("End Date", value=df["date"].max() if not df.empty else datetime.today())
        category_filter = col3.selectbox("Category", ["All", *sorted(df["category"].dropna().unique().tolist())])
        payment_filter = col4.selectbox("Payment Method", ["All", *sorted(df["payment_method"].dropna().unique().tolist())])
        amount_min = st.number_input("Minimum Amount", min_value=0.0, value=0.0, step=1.0)
        amount_max = st.number_input("Maximum Amount", min_value=0.0, value=float(df["amount"].max()) if not df.empty else 10000.0, step=1.0)

    filtered = apply_filters(df, start_date, end_date, category_filter, payment_filter, amount_min, amount_max)
    st.dataframe(filtered, use_container_width=True)


def render_budgets(transactions: list[dict], budgets: dict, store: dict) -> None:
    st.subheader("🎯 Monthly Budgets")
    predefined = ["Food", "Grocery", "Shopping", "Fuel", "Entertainment", "Medical", "Travel", "Bills", "Education", "Rent", "EMI", "Others"]
    updated_budgets = dict(budgets)
    for category in predefined:
        current_value = updated_budgets.get(category, 0)
        updated_budgets[category] = st.number_input(f"{category} Budget", min_value=0.0, value=float(current_value), step=100.0, key=f"budget_{category}")
    if st.button("Save Budgets"):
        save_current_user_data(store, transactions, updated_budgets)
        st.success("Budgets updated")

    df = transaction_to_dataframe(transactions)
    expense_df = df[df["type"] == "expense"]
    if not expense_df.empty:
        st.subheader("Budget Usage")
        for category in predefined:
            spend = float(expense_df[expense_df["category"] == category]["amount"].sum()) if category in expense_df["category"].values else 0.0
            budget = updated_budgets.get(category, 0)
            if budget:
                progress = min(spend / budget, 1.0)
                st.progress(progress)
                st.caption(f"{category}: ₹{spend:,.0f} / ₹{budget:,.0f}")


def render_insights(transactions: list[dict]) -> None:
    st.subheader("💡 Financial Insights")
    insights = generate_insights(transactions)
    for insight in insights:
        st.info(insight)

    st.subheader("📈 Expense Prediction")
    forecast = build_next_month_prediction(transactions)
    st.metric("Predicted Next Month Spending", f"₹{forecast:,.0f}")

    st.subheader("🩺 Financial Health Score")
    summary = compute_summary(transactions)
    score = max(0, min(100, 50 + summary["savings_rate"] * 50))
    st.progress(score / 100)
    st.write(f"Health Score: {score:.0f}/100")


def render_reports(transactions: list[dict], store: dict) -> None:
    st.subheader("📥 Export Reports")
    df = transaction_to_dataframe(transactions)
    if df.empty:
        st.info("No transactions available to export")
        return
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    excel_bytes = export_transactions_excel(df)
    pdf_bytes = export_transactions_pdf(df)

    st.download_button("Download CSV", csv_bytes, file_name="transactions.csv", mime="text/csv")
    st.download_button("Download Excel", excel_bytes, file_name="transactions.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.download_button("Download PDF Summary", pdf_bytes, file_name="finance_summary.pdf", mime="application/pdf")

    st.dataframe(df, use_container_width=True)


def render_model_page() -> None:
    st.subheader("🤖 ML Expense Categorization")
    with st.spinner("Training and evaluating models..."):
        model_info = ensure_model_ready()
    metrics = get_model_metrics()
    st.write("Best model:", model_info["best_model"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Accuracy", f"{metrics['accuracy']:.2%}")
    col2.metric("Precision", f"{metrics['precision']:.2%}")
    col3.metric("Recall", f"{metrics['recall']:.2%}")
    col4.metric("F1 Score", f"{metrics['f1']:.2%}")

    st.subheader("Category Prediction")
    desc = st.text_input("Enter a transaction description")
    if st.button("Predict Category") and desc:
        category = predict_category(desc)
        st.success(f"Predicted category: {category}")

    st.subheader("Confusion Matrix")
    conf = np.array(metrics["confusion_matrix"])
    fig = px.imshow(conf, labels=dict(x="Predicted", y="Actual"), x=metrics["labels"], y=metrics["labels"], title="Confusion Matrix")
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    if not st.session_state.get("authenticated", False):
        render_auth()
        return

    store, transactions, budgets = get_current_user_data()
    st.sidebar.title(f"👋 {st.session_state.current_user}")
    page = st.sidebar.radio("Navigation", ["Dashboard", "Transactions", "Budgets", "Insights", "Reports", "Model"])

    if page == "Dashboard":
        render_dashboard(transactions, budgets)
    elif page == "Transactions":
        render_transactions(transactions, store)
    elif page == "Budgets":
        render_budgets(transactions, budgets, store)
    elif page == "Insights":
        render_insights(transactions)
    elif page == "Reports":
        render_reports(transactions, store)
    else:
        render_model_page()


if __name__ == "__main__":
    main()
