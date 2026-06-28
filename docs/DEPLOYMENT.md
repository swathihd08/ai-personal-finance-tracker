# Deployment Guide

This document explains how to deploy `AI Personal Finance Tracker`.

## Option A — Streamlit Community Cloud (recommended)
1. Create a GitHub repository and push your project.
2. Visit https://share.streamlit.io and sign in with GitHub.
3. Click "New app" and select your repository, branch (e.g., `main`), and the `app.py` file as the entrypoint.
4. Deploy — Streamlit Cloud will install dependencies from `requirements.txt` and start the app.
5. If you need to set secrets (e.g., EMAIL credentials), add them in the app settings on Streamlit Cloud.

Notes:
- No Dockerfile required. Keep `requirements.txt` up to date.

## Option B — Docker (self-hosting, AWS/GCP/DigitalOcean)
1. Build locally:

```bash
docker build -t ai-finance-tracker:latest .
```

2. Run locally:

```bash
docker run -p 8501:8501 ai-finance-tracker:latest
```

3. Push the image to your container registry (Docker Hub / AWS ECR).
4. Deploy the container to your cloud provider using their standard steps.

## Option C — Heroku (container or Python buildpack)
- Use the provided `Procfile`. Deploy via Heroku Git or Container Registry.

## CI/CD
- A GitHub Actions workflow is included at `.github/workflows/ci.yml` that installs dependencies and runs a smoke test on push.

## Helpful tips
- Use a short-path workspace or a virtual environment to avoid long-path Windows issues.
- Keep `dataset/transactions_dataset.csv` in the repo for model reproducibility.

If you want, I can:
- Create a GitHub repo in your account and push these files (requires your GitHub token).
- Set up an automated deployment to a cloud provider (requires credentials).
