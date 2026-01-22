"""
Neon PostgreSQL Client Module

Handles connection to Neon PostgreSQL for persistent storage of organizations and logos.
Replaces Supabase with direct PostgreSQL connection.
"""

import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
import json
import os

# Get Neon connection string from secrets or environment
def get_neon_connection_string() -> str:
    """Get Neon database connection string from secrets or environment"""
    return st.secrets.get("NEON_DATABASE_URL", os.environ.get("NEON_DATABASE_URL", ""))

_neon_connection: Optional[psycopg2.extensions.connection] = None

def get_neon_connection() -> psycopg2.extensions.connection:
    """Get or create Neon PostgreSQL connection"""
    global _neon_connection

    connection_string = get_neon_connection_string()
    if not connection_string:
        raise ValueError("NEON_DATABASE_URL not configured in secrets")

    # Check if connection is still valid, reconnect if needed
    if _neon_connection is None or _neon_connection.closed:
        _neon_connection = psycopg2.connect(connection_string)

    return _neon_connection

def close_neon_connection():
    """Close the Neon connection"""
    global _neon_connection
    if _neon_connection and not _neon_connection.closed:
        _neon_connection.close()
        _neon_connection = None

def init_organizations_table():
    """Initialize the organizations table if it doesn't exist"""
    conn = get_neon_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS organizations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    uen VARCHAR(50),
                    address TEXT,
                    logo_url TEXT,
                    templates JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error initializing organizations table: {e}")
        raise

def get_all_organizations() -> List[Dict[str, Any]]:
    """Fetch all organizations from Neon"""
    conn = get_neon_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM organizations ORDER BY name")
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error fetching organizations: {e}")
        return []

def get_organization_by_id(org_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single organization by ID"""
    conn = get_neon_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM organizations WHERE id = %s", (org_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching organization by ID: {e}")
        return None

def insert_organization(org: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert a new organization into Neon"""
    conn = get_neon_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            templates_json = json.dumps(org.get("templates", {}))
            cur.execute("""
                INSERT INTO organizations (name, uen, address, logo_url, templates)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (
                org.get("name", ""),
                org.get("uen", ""),
                org.get("address", ""),
                org.get("logo", ""),
                templates_json
            ))
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        conn.rollback()
        print(f"Error inserting organization: {e}")
        return None

def update_organization(org_id: int, org: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing organization in Neon"""
    conn = get_neon_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            templates_json = json.dumps(org.get("templates", {}))
            cur.execute("""
                UPDATE organizations
                SET name = %s, uen = %s, address = %s, logo_url = %s, templates = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
            """, (
                org.get("name", ""),
                org.get("uen", ""),
                org.get("address", ""),
                org.get("logo", ""),
                templates_json,
                org_id
            ))
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        conn.rollback()
        print(f"Error updating organization: {e}")
        return None

def delete_organization(org_id: int) -> bool:
    """Delete an organization from Neon"""
    conn = get_neon_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM organizations WHERE id = %s", (org_id,))
            conn.commit()
            return cur.rowcount > 0
    except Exception as e:
        conn.rollback()
        print(f"Error deleting organization: {e}")
        return False

def upsert_organization(org: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Insert or update organization (upsert by name)"""
    conn = get_neon_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            templates_json = json.dumps(org.get("templates", {}))
            cur.execute("""
                INSERT INTO organizations (name, uen, address, logo_url, templates)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET
                    uen = EXCLUDED.uen,
                    address = EXCLUDED.address,
                    logo_url = EXCLUDED.logo_url,
                    templates = EXCLUDED.templates,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
            """, (
                org.get("name", ""),
                org.get("uen", ""),
                org.get("address", ""),
                org.get("logo", ""),
                templates_json
            ))
            conn.commit()
            row = cur.fetchone()
            return dict(row) if row else None
    except Exception as e:
        conn.rollback()
        print(f"Error upserting organization: {e}")
        return None
