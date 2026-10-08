import json
import os
import tempfile

from dotenv import load_dotenv

load_dotenv()


# Where the data lives
BLOB_PATH = "students/users.json"

# On Vercel only /tmp is writable, so save the file there.
# Locally, save next to this script.
if os.getenv("VERCEL"):
    LOCAL_FILE = os.path.join(tempfile.gettempdir(), "users.json")
else:
    LOCAL_FILE = os.path.join(os.path.dirname(__file__), "users.json")


# Use the cloud only when a token is configured
def use_cloud():
    return bool(os.getenv("BLOB_READ_WRITE_TOKEN"))


def get_client():
    from vercel.blob import BlobClient

    return BlobClient()


# Keep the counter safe even if the data was edited by hand
def build_state(data):
    users = data.get("users", [])
    highest_id = max((u["id"] for u in users), default=0)
    next_id = max(data.get("next_id", 1), highest_id + 1)
    return users, next_id


# ---------------- Cloud storage ----------------

def load_cloud():
    client = get_client()
    result = client.get(BLOB_PATH, access="private")

    if result is None or result.status_code != 200:
        return [], 1

    raw = b"".join(chunk for chunk in result.stream)

    try:
        data = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return [], 1

    return build_state(data)


def save_cloud(users, next_id):
    client = get_client()

    body = json.dumps(
        {"users": users, "next_id": next_id},
        indent=2,
    ).encode("utf-8")

    client.put(
        BLOB_PATH,
        body,
        access="private",
        content_type="application/json",
        overwrite=True,
    )


# ---------------- Local file ----------------

def load_local():
    if not os.path.exists(LOCAL_FILE):
        return [], 1

    try:
        with open(LOCAL_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return [], 1

    return build_state(data)


def save_local(users, next_id):
    temp_file = LOCAL_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump({"users": users, "next_id": next_id}, f, indent=2)

    os.replace(temp_file, LOCAL_FILE)


# ---------------- Public functions used by main.py ----------------

def load_data():
    if use_cloud():
        return load_cloud()

    return load_local()


def save_data(users, next_id):
    if use_cloud():
        save_cloud(users, next_id)
    else:
        save_local(users, next_id)