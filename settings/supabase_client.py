"""
Supabase Client Module

Handles connection to Supabase for persistent storage of organizations and logos.
"""

import streamlit as st
from typing import Optional
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = "https://ssmkokzmlihjjwkrbfms.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNzbWtva3ptbGloamp3a3JiZm1zIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkwNDUzMjksImV4cCI6MjA4NDYyMTMyOX0.nSutDuy5QIOJy-LK1hC5R76cBVDzcI9p5J_WjX8neRU"

# Storage bucket name
LOGOS_BUCKET = "logos"

_supabase_client: Optional[Client] = None

def get_supabase_client() -> Client:
    """Get or create Supabase client (singleton pattern)"""
    global _supabase_client

    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    return _supabase_client

def get_logo_public_url(filename: str) -> str:
    """Get public URL for a logo file in storage"""
    return f"{SUPABASE_URL}/storage/v1/object/public/{LOGOS_BUCKET}/{filename}"
