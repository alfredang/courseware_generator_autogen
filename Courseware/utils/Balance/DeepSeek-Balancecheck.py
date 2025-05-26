import requests
from datetime import datetime
import os
import json
import streamlit as st

# Replace with your actual DeepSeek API key
DEEPSEEK_API_KEY = st.secrets['DEEPSEEK_API_KEY']

# Directory to store balance files (same directory as this script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# File to store usage history
HISTORY_FILE = os.path.join(SCRIPT_DIR, "api_usage_log.json")
# File to store the latest balance
LATEST_BALANCE_FILE = os.path.join(SCRIPT_DIR, "latest_balance.json")

def load_latest_balance():
    if os.path.exists(LATEST_BALANCE_FILE):
        with open(LATEST_BALANCE_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return None
    return None

def save_latest_balance(balance_data):
    with open(LATEST_BALANCE_FILE, "w") as f:
        json.dump(balance_data, f, indent=4)

# Load existing history if available
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r") as f:
        usage_history = json.load(f)
else:
    usage_history = []

# Display the last stored balance before making a new API call
last_balance = load_latest_balance()
if last_balance:
    print("Last Stored Balance Info:")
    print(f"Is Available: {last_balance.get('is_available')}")
    print("Balance Infos:")
    for info in last_balance.get("balance_infos", []):
        print(info)
    print("--- End of Last Stored Balance ---\n")
else:
    print("No previous balance info found.\n")

# API endpoint
url = "https://api.deepseek.com/user/balance"

# Set up the headers with your API key
headers = {
    "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
    "Accept": "application/json"
}

# Make the GET request
response = requests.get(url, headers=headers)

# Check for success
if response.status_code == 200:
    data = response.json()

    # Store usage record
    usage_record = {
        "timestamp": datetime.now().isoformat(),
        "is_available": data.get('is_available'),
        "balance_infos": data.get('balance_infos', [])
    }
    usage_history.append(usage_record)

    # Print current balance info
    print("Current Balance Info:")
    print(f"Is Available: {data.get('is_available')}")
    print("Balance Infos:")
    for info in data.get("balance_infos", []):
        print(info)

    # Save updated history
    with open(HISTORY_FILE, "w") as f:
        json.dump(usage_history, f, indent=4)

    # Save the latest balance
    save_latest_balance({
        "is_available": data.get('is_available'),
        "balance_infos": data.get('balance_infos', [])
    })
else:
    print(f"Failed to get balance. Status code: {response.status_code}")
    print("Response:", response.text)

# Print usage history
print("\n--- API Usage History ---")
for i, record in enumerate(usage_history, 1):
    print(f"\nRecord {i}:")
    print(f"Timestamp: {record['timestamp']}")
    print(f"Is Available: {record['is_available']}")
    print("Balance Infos:", record['balance_infos'])
