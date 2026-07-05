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
            
        return create_client(url, key)
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
        st.warning(f"Cloud save failed, using local storage: {e}")
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
