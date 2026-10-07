import json
import os


# Data file lives next to this script
DATA_FILE = os.path.join(os.path.dirname(__file__), "users.json")


# Load users and the next ID counter
def load_data():
    if not os.path.exists(DATA_FILE):
        return [], 1

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return [], 1

    users = data.get("users", [])

    # Keep the counter safe even if the file was edited by hand
    highest_id = max((u["id"] for u in users), default=0)
    next_id = max(data.get("next_id", 1), highest_id + 1)

    return users, next_id


# Save users and the next ID counter
def save_data(users, next_id):
    temp_file = DATA_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(
            {"users": users, "next_id": next_id},
            f,
            indent=2,
        )

    # Replace the old file only after the new one is fully written
    os.replace(temp_file, DATA_FILE)