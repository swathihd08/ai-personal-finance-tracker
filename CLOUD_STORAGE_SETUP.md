# Cloud Storage Setup Guide

The app now supports persistent cloud storage using Supabase (free PostgreSQL database) so your login info and transaction data are saved even when the app restarts.

## Quick Setup (5 minutes)

### Step 1: Create Supabase Account & Project
1. Go to https://supabase.com and sign up (free)
2. Create a new project
3. Wait for the project to be ready
4. Go to **Settings** → **API** and copy:
   - **Project URL** (looks like: `https://your-project.supabase.co`)
   - **Service Role Key** (under "service_role" section)

### Step 2: Create Database Tables
1. In Supabase, go to **SQL Editor**
2. Run this SQL to create the users table:

```sql
CREATE TABLE users (
  id BIGSERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  data JSONB NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_username ON users(username);
```

### Step 3: Configure Streamlit Cloud
1. Go to your Streamlit Cloud app: https://share.streamlit.io
2. Click your app → **Settings** (gear icon bottom right)
3. Go to **Secrets**
4. Add this content (replace with your values):

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-service-role-key"
```

5. Click **Save**
6. The app will auto-refresh

### Step 4: Test Persistence
1. Go to your app
2. Create a new account and add some transactions
3. Wait 5 minutes and refresh the page
4. Your data should still be there! ✅

## Local Development

For local testing with cloud storage:
1. Create `.streamlit/secrets.toml` in your project:

```toml
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-service-role-key"
```

2. Run: `streamlit run app.py`
3. The app will use cloud storage for persistence

## Fallback Behavior

- If cloud storage is not configured, the app automatically uses local JSON storage (works fine locally)
- On Streamlit Cloud without secrets, data persists only during your active session
- Once cloud storage is set up, it takes priority and data persists permanently

## Troubleshooting

**"Cloud save failed, using local storage"**
- Your Supabase secrets might be incorrect
- Check that SUPABASE_URL and SUPABASE_KEY are in Secrets
- Verify the format matches exactly

**Data still not persisting on Cloud?**
- Give it 1-2 minutes after adding secrets
- Refresh your Streamlit Cloud app settings page
- Check that Supabase project is active (not paused)

**Want to verify it's working?**
- Log into Supabase dashboard → **users** table
- You should see rows with your username after creating accounts

