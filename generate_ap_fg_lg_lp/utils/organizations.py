"""
Organizations Management Utilities

This module handles loading and saving organization data,
including company details and templates.

Supports both:
- Supabase (cloud storage - for Streamlit Cloud)
- Local JSON file (fallback for local development)
"""

import json
import os
from typing import List, Dict, Any, Optional

ORGANIZATIONS_FILE = "generate_ap_fg_lg_lp/utils/organizations.json"

# Try to import Supabase client
try:
    from settings.supabase_client import get_supabase_client, get_logo_public_url, LOGOS_BUCKET
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False

def _ensure_org_fields(org: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure organization has all required fields"""
    if "templates" not in org:
        org["templates"] = {
            "course_proposal": "",
            "courseware": "",
            "assessment": "",
            "brochure": ""
        }
    if "address" not in org:
        org["address"] = ""
    if "logo" not in org:
        org["logo"] = ""
    return org

def _convert_supabase_org(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Supabase row format to app format"""
    return {
        "id": row.get("id"),
        "name": row.get("name", ""),
        "uen": row.get("uen", ""),
        "address": row.get("address", ""),
        "logo": row.get("logo_url", ""),  # Map logo_url to logo
        "templates": row.get("templates") or {
            "course_proposal": "",
            "courseware": "",
            "assessment": "",
            "brochure": ""
        }
    }

def _convert_to_supabase_format(org: Dict[str, Any]) -> Dict[str, Any]:
    """Convert app format to Supabase row format"""
    data = {
        "name": org.get("name", ""),
        "uen": org.get("uen", ""),
        "address": org.get("address", ""),
        "logo_url": org.get("logo", ""),  # Map logo to logo_url
        "templates": org.get("templates", {})
    }
    # Include id if present (for updates)
    if "id" in org:
        data["id"] = org["id"]
    return data

def get_organizations_from_supabase() -> List[Dict[str, Any]]:
    """Load organizations from Supabase"""
    try:
        client = get_supabase_client()
        response = client.table("organizations").select("*").execute()
        organizations = [_convert_supabase_org(row) for row in response.data]
        return organizations
    except Exception as e:
        print(f"Error loading from Supabase: {e}")
        return []

def get_organizations_from_json() -> List[Dict[str, Any]]:
    """Load organizations from local JSON file"""
    try:
        if os.path.exists(ORGANIZATIONS_FILE):
            with open(ORGANIZATIONS_FILE, 'r') as f:
                organizations = json.load(f)
            return [_ensure_org_fields(org) for org in organizations]
    except Exception as e:
        print(f"Error loading from JSON: {e}")
    return []

def get_organizations() -> List[Dict[str, Any]]:
    """Load organizations - tries Supabase first, falls back to JSON"""
    if SUPABASE_AVAILABLE:
        orgs = get_organizations_from_supabase()
        if orgs:
            return orgs
        # If Supabase returns empty, try JSON as fallback
        print("Supabase empty or unavailable, falling back to JSON")

    return get_organizations_from_json()

def save_organization_to_supabase(org: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Save a single organization to Supabase (insert or update)"""
    try:
        client = get_supabase_client()
        data = _convert_to_supabase_format(org)

        if "id" in org and org["id"]:
            # Update existing
            response = client.table("organizations").update(data).eq("id", org["id"]).execute()
        else:
            # Insert new (remove id for insert)
            data.pop("id", None)
            response = client.table("organizations").insert(data).execute()

        if response.data:
            return _convert_supabase_org(response.data[0])
        return None
    except Exception as e:
        print(f"Error saving to Supabase: {e}")
        return None

def save_organizations(organizations: List[Dict[str, Any]]) -> bool:
    """Save organizations - saves to JSON (primary) and Supabase (secondary)"""
    json_success = True

    # Always save to JSON as primary storage
    try:
        os.makedirs(os.path.dirname(ORGANIZATIONS_FILE), exist_ok=True)
        with open(ORGANIZATIONS_FILE, 'w') as f:
            json.dump(organizations, f, indent=4)
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        json_success = False

    # Also try to save to Supabase (but don't fail if it doesn't work)
    if SUPABASE_AVAILABLE:
        supabase_errors = 0
        for org in organizations:
            result = save_organization_to_supabase(org)
            if result is None:
                supabase_errors += 1
        if supabase_errors > 0:
            print(f"⚠️ Warning: {supabase_errors} organization(s) failed to sync to Supabase")

    # Return success based on JSON save (primary storage)
    return json_success

def delete_organization_from_supabase(org_id: int) -> bool:
    """Delete organization from Supabase by ID"""
    try:
        client = get_supabase_client()
        client.table("organizations").delete().eq("id", org_id).execute()
        return True
    except Exception as e:
        print(f"Error deleting from Supabase: {e}")
        return False

def upload_logo_to_supabase(file_bytes: bytes, filename: str) -> Optional[str]:
    """Upload logo to Supabase storage and return public URL"""
    if not SUPABASE_AVAILABLE:
        return None

    try:
        client = get_supabase_client()
        # Upload file to storage
        client.storage.from_(LOGOS_BUCKET).upload(
            filename,
            file_bytes,
            {"content-type": "image/jpeg", "upsert": "true"}
        )
        # Return public URL
        return get_logo_public_url(filename)
    except Exception as e:
        print(f"Error uploading logo to Supabase: {e}")
        return None

def get_organization_by_name(name: str) -> Dict[str, Any]:
    """Get specific organization by name"""
    organizations = get_organizations()
    for org in organizations:
        if org["name"] == name:
            return org
    return {}

def get_default_organization() -> Dict[str, Any]:
    """Get Tertiary Infotech as default organization"""
    organizations = get_organizations()
    for org in organizations:
        if "tertiary infotech" in org["name"].lower():
            return org

    # Return first organization if Tertiary Infotech not found
    if organizations:
        return organizations[0]

    # Fallback empty organization
    return {
        "name": "Tertiary Infotech Academy Pte Ltd",
        "uen": "201200696W",
        "logo": "common/logo/tertiary_infotech_pte_ltd.jpg",
        "address": "",
        "templates": {
            "course_proposal": "",
            "courseware": "",
            "assessment": "",
            "brochure": ""
        }
    }

def replace_company_branding(content: str, company: Dict[str, Any]) -> str:
    """Replace company branding placeholders in content"""
    replacements = {
        "{{COMPANY_NAME}}": company.get("name", ""),
        "{{COMPANY_UEN}}": company.get("uen", ""),
        "{{COMPANY_ADDRESS}}": company.get("address", ""),
        "{{COMPANY_LOGO}}": company.get("logo", ""),
        # Legacy support
        "Tertiary Infotech Pte Ltd": company.get("name", "Tertiary Infotech Academy Pte Ltd"),
        "201200696W": company.get("uen", "201200696W")
    }

    result = content
    for placeholder, replacement in replacements.items():
        result = result.replace(placeholder, replacement)

    return result
