"""
Supabase Client Module (DEPRECATED - Use Neon PostgreSQL instead)

Handles connection to Supabase for persistent storage of organizations and logos.
Note: This module is being phased out in favor of Neon PostgreSQL.
"""

import streamlit as st
import os
from typing import Optional
from supabase import create_client, Client

# Get Supabase configuration from secrets or environment (no hardcoded keys)
SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

# Storage bucket name
LOGOS_BUCKET = "logos"

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client (singleton pattern)"""
    global _supabase_client

    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Supabase credentials not configured in secrets")

    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    return _supabase_client

def get_logo_public_url(filename: str) -> str:
    """Get public URL for a logo file in storage"""
    if not SUPABASE_URL:
        return ""
    return f"{SUPABASE_URL}/storage/v1/object/public/{LOGOS_BUCKET}/{filename}"
