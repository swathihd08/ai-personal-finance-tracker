# AI Personal Finance Tracker

A production-style personal finance tracker built with Streamlit, Python, scikit-learn, Plotly, and joblib.

## Features
- Secure login/signup with password hashing
- Upload CSV/Excel bank statements
- Manual transaction entry
- AI-based expense categorization with scikit-learn
- Interactive dashboards and charts
- Budget alerts and savings insights
- Search/filter/export functionality
- Dark mode responsive UI

## Run locally
1. Install dependencies:
   pip install -r requirements.txt
2. Start the app:
   streamlit run app.py

## Project structure
- app.py — main Streamlit application
- utils/auth.py — authentication and user storage
- utils/data_utils.py — parsing, summaries, and reports
- utils/ml_utils.py — training and prediction pipeline
- dataset/transactions_dataset.csv — sample training dataset
- models/ — saved ML artifacts
