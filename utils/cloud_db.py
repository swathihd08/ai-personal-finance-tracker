"""Cloud database module using Supabase for persistent storage on Streamlit Cloud."""
import streamlit as st
import json
from typing import Optional, List, Dict, Any


def get_supabase_client():
    """Get or initialize Supabase client from Streamlit secrets."""
    try:
        from supabase import create_client, Client
        
        # Use environment variables or Streamlit secrets
        url = st.secrets.get("SUPABASE_URL") or ""
        key = st.secrets.get("SUPABASE_KEY") or ""
        
        if not url or not key:
            return None

        # Basic validation of URL
        if not (url.startswith("http://") or url.startswith("https://")):
            # avoid attempting DNS lookup on malformed URL
            st.warning("SUPABASE_URL in secrets looks invalid (missing http/https). Cloud storage will be disabled until secrets are corrected.")
            return None

        try:
            return create_client(url, key)
        except Exception as e:
            # Return None so the app falls back to local storage; caller will display a friendly message
            return None
    except Exception:
        return None


def init_cloud_tables(client) -> bool:
    """Initialize database tables if they don't exist."""
    if not client:
        return False
    
    try:
        # Tables are created manually via Supabase dashboard or admin API
        # This is a placeholder for when tables exist
        return True
    except Exception as e:
        st.error(f"Failed to initialize cloud tables: {e}")
        return False


def save_user_cloud(username: str, user_data: dict) -> bool:
    """Save user data to Supabase."""
    client = get_supabase_client()
    if not client:
        return False
    
    try:
        # Upsert user record
        response = client.table("users").upsert({
            "username": username,
            "data": json.dumps(user_data)
        }).execute()
        return True
    except Exception as e:
        msg = str(e)
        # Provide clearer guidance for common DNS/network errors
        if "Name or service not known" in msg or "Errno -2" in msg or "gaierror" in msg:
            st.warning("Cloud save failed: DNS lookup failed for SUPABASE_URL. Please check SUPABASE_URL in Streamlit Secrets and ensure the Supabase project URL is correct.")
        else:
            st.warning(f"Cloud save failed, using local storage: {msg}")
        return False


def load_user_cloud(username: str) -> Optional[dict]:
    """Load user data from Supabase."""
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        response = client.table("users").select("data").eq("username", username).execute()
        if response.data and len(response.data) > 0:
            return json.loads(response.data[0]["data"])
        return None
    except Exception:
        return None


def check_cloud_enabled() -> bool:
    """Check if cloud storage is enabled via secrets."""
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        return bool(url and key)
    except Exception:
        return False
