"""
Organizations Management Utilities

This module handles loading and saving organization data,
including company details and templates.

Supports both:
- Neon PostgreSQL (cloud storage - for Streamlit Cloud)
- Local JSON file (fallback for local development)
"""

import json
import os
from typing import List, Dict, Any, Optional

ORGANIZATIONS_FILE = "generate_ap_fg_lg_lp/utils/organizations.json"

# Try to import Neon client
try:
    from settings.neon_client import (
        get_neon_connection,
        get_all_organizations as neon_get_all,
        insert_organization as neon_insert,
        update_organization as neon_update,
        delete_organization as neon_delete,
        init_organizations_table
    )
    NEON_AVAILABLE = True
except ImportError:
    NEON_AVAILABLE = False

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

def _convert_neon_org(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Neon row format to app format"""
    templates = row.get("templates")
    if isinstance(templates, str):
        try:
            templates = json.loads(templates)
        except:
            templates = {}

    return {
        "id": row.get("id"),
        "name": row.get("name", ""),
        "uen": row.get("uen", ""),
        "address": row.get("address", ""),
        "logo": row.get("logo_url", ""),  # Map logo_url to logo
        "templates": templates or {
            "course_proposal": "",
            "courseware": "",
            "assessment": "",
            "brochure": ""
        }
    }

def _convert_to_neon_format(org: Dict[str, Any]) -> Dict[str, Any]:
    """Convert app format to Neon row format"""
    data = {
        "name": org.get("name", ""),
        "uen": org.get("uen", ""),
        "address": org.get("address", ""),
        "logo": org.get("logo", ""),  # Will be stored as logo_url
        "templates": org.get("templates", {})
    }
    # Include id if present (for updates)
    if "id" in org:
        data["id"] = org["id"]
    return data

def get_organizations_from_neon() -> List[Dict[str, Any]]:
    """Load organizations from Neon PostgreSQL"""
    try:
        # Initialize table if needed
        init_organizations_table()
        rows = neon_get_all()
        organizations = [_convert_neon_org(row) for row in rows]
        return organizations
    except Exception as e:
        print(f"Error loading from Neon: {e}")
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
    """Load organizations - tries Neon first, falls back to JSON"""
    if NEON_AVAILABLE:
        try:
            orgs = get_organizations_from_neon()
            if orgs:
                return orgs
        except Exception as e:
            print(f"Neon unavailable: {e}")
        # If Neon returns empty or fails, try JSON as fallback
        print("Neon empty or unavailable, falling back to JSON")

    return get_organizations_from_json()

def save_organization_to_neon(org: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Save a single organization to Neon (insert or update)"""
    try:
        data = _convert_to_neon_format(org)

        if "id" in org and org["id"]:
            # Update existing
            result = neon_update(org["id"], data)
        else:
            # Insert new
            result = neon_insert(data)

        if result:
            return _convert_neon_org(result)
        return None
    except Exception as e:
        print(f"Error saving to Neon: {e}")
        return None

def save_organizations(organizations: List[Dict[str, Any]]) -> bool:
    """Save organizations - saves to JSON (primary) and Neon (secondary)"""
    json_success = True

    # Always save to JSON as primary storage
    try:
        os.makedirs(os.path.dirname(ORGANIZATIONS_FILE), exist_ok=True)
        with open(ORGANIZATIONS_FILE, 'w') as f:
            json.dump(organizations, f, indent=4)
    except Exception as e:
        print(f"Error saving to JSON: {e}")
        json_success = False

    # Also try to save to Neon (but don't fail if it doesn't work)
    if NEON_AVAILABLE:
        neon_errors = 0
        for org in organizations:
            result = save_organization_to_neon(org)
            if result is None:
                neon_errors += 1
        if neon_errors > 0:
            print(f"Warning: {neon_errors} organization(s) failed to sync to Neon")

    # Return success based on JSON save (primary storage)
    return json_success

def delete_organization_from_neon(org_id: int) -> bool:
    """Delete organization from Neon by ID"""
    try:
        return neon_delete(org_id)
    except Exception as e:
        print(f"Error deleting from Neon: {e}")
        return False

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
