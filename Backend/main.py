import os
import json
import re
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI

from storage import load_data, save_data


# Load environment variables
load_dotenv()


# Get OpenRouter API key
api_key = os.getenv("OPENROUTER_API_KEY")


# Create OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)


# Current data. Reloaded from storage at the start of every request,
# because on Vercel several server copies may be running at once.
users = []
next_id = 1


def refresh_state():
    global users, next_id

    try:
        users, next_id = load_data()
    except Exception as error:
        print("Storage load failed:", error)
        raise HTTPException(
            status_code=503,
            detail="Storage is unavailable. Please try again.",
        )


# Create FastAPI application
app = FastAPI()

# All real routes live under /api, because Vercel's vercel.json
# only forwards paths matching /api/(.*) to this backend service.
router = APIRouter(prefix="/api", dependencies=[Depends(refresh_state)])


# Allowed frontend origins.
# Locally this defaults to the Vite dev servers.
# When deployed, set ALLOWED_ORIGINS to your frontend URL(s),
# separated by commas, with no trailing slash.
default_origins = "http://localhost:5173,http://localhost:5174"

allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", default_origins).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Save the current state to storage
def persist():
    try:
        save_data(users, next_id)
    except Exception as error:
        print("Storage save failed:", error)
        raise HTTPException(
            status_code=503,
            detail="Could not save data. Please try again.",
        )


# ---------------- Request models ----------------

class CommandRequest(BaseModel):
    command: str


class UserCreate(BaseModel):
    name: str
    email: str
    age: int


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    age: Optional[int] = None


# ---------------- LLM prompt ----------------

SYSTEM_PROMPT = """
You are a CRUD command interpreter.

The available user fields are:

- name
- email
- age

Interpret the user's command and return ONLY valid JSON.
Do not add explanations. Do not use markdown.

Supported actions: "create", "update", "delete".

--- CREATE ---
All three fields (name, email, age) are required.
Use exactly this structure:

{
  "action": "create",
  "name": "value or null",
  "email": "value or null",
  "age": null,
  "missing_fields": []
}

If any required fields are missing, put their names
inside the "missing_fields" array.

Example:
User command: Create user Ali
Return:
{"action": "create", "name": "Ali", "email": null, "age": null, "missing_fields": ["email", "age"]}

Example:
User command: Create user Ali, ali@gmail.com, age 22
Return:
{"action": "create", "name": "Ali", "email": "ali@gmail.com", "age": 22, "missing_fields": []}

--- UPDATE ---
"name" is the name of the EXISTING user to update.
"changes" contains only the fields to change. Use null for fields
that are not being changed.

{
  "action": "update",
  "name": "existing user's name",
  "changes": {
    "name": null,
    "email": null,
    "age": null
  }
}

Example:
User command: Update Ali's age to 25
Return:
{"action": "update", "name": "Ali", "changes": {"name": null, "email": null, "age": 25}}

Example:
User command: Change Ali's email to new@gmail.com
Return:
{"action": "update", "name": "Ali", "changes": {"name": null, "email": "new@gmail.com", "age": null}}

--- DELETE ---
{
  "action": "delete",
  "name": "existing user's name"
}

Example:
User command: Delete Ali
Return:
{"action": "delete", "name": "Ali"}

If the command is not a create, update, or delete request, return:
{"action": "unknown"}

Return JSON only.
"""


# ---------------- Helpers ----------------

# Extract JSON even if the model adds fences or extra text
def extract_json(text):
    if not text:
        return None

    text = re.sub(r"```(?:json)?", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None

    return None


# Find users by name (case-insensitive)
def find_users_by_name(name):
    if not name:
        return []

    return [
        user for user in users
        if user["name"].lower() == str(name).strip().lower()
    ]


# Find a user by ID
def find_user_by_id(user_id):
    for user in users:
        if user["id"] == user_id:
            return user
    return None


# Validation helpers: return an error message, or None if valid
def check_name(name):
    if name is None or not str(name).strip():
        return "A valid name is required."
    return None


def check_email(email):
    if email is None or not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(email).strip()
    ):
        return "A valid email is required."
    return None


def check_age(age):
    try:
        age = int(age)
    except (TypeError, ValueError):
        return "Age must be a number."

    if age < 0 or age > 120:
        return "Age must be between 0 and 120."

    return None


# Create a user (shared by the AI route and POST /users)
def create_user(name, email, age):
    global next_id

    new_user = {
        "id": next_id,
        "name": str(name).strip(),
        "email": str(email).strip(),
        "age": int(age),
    }

    next_id += 1
    users.append(new_user)
    persist()

    return new_user


# ---------------- Basic routes ----------------

@router.get("/")
def root():
    return {"message": "FastAPI backend is working"}


@router.get("/test")
def test():
    return {"message": "React can connect to FastAPI"}


# ---------------- Normal CRUD routes ----------------

# Get all users
@router.get("/users")
def get_users():
    return users


# Create a user
@router.post("/users")
def add_user(user: UserCreate):
    error = (
        check_name(user.name)
        or check_email(user.email)
        or check_age(user.age)
    )

    if error:
        raise HTTPException(status_code=400, detail=error)

    new_user = create_user(user.name, user.email, user.age)

    return {
        "message": "User created successfully.",
        "user": new_user
    }


# Update a user
@router.put("/users/{user_id}")
def update_user(user_id: int, changes: UserUpdate):
    user = find_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if (
        changes.name is None
        and changes.email is None
        and changes.age is None
    ):
        raise HTTPException(
            status_code=400, detail="No changes were provided."
        )

    # Validate every change before applying any of them
    error = None

    if changes.name is not None:
        error = check_name(changes.name)

    if not error and changes.email is not None:
        error = check_email(changes.email)

    if not error and changes.age is not None:
        error = check_age(changes.age)

    if error:
        raise HTTPException(status_code=400, detail=error)

    if changes.name is not None:
        user["name"] = changes.name.strip()

    if changes.email is not None:
        user["email"] = changes.email.strip()

    if changes.age is not None:
        user["age"] = changes.age

    persist()

    return {
        "message": "User updated successfully.",
        "user": user
    }


# Delete a user
@router.delete("/users/{user_id}")
def delete_user(user_id: int):
    user = find_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    users.remove(user)
    persist()

    return {
        "message": "User deleted successfully.",
        "user": user
    }


# ---------------- AI command route ----------------

@router.post("/command")
def command(request: CommandRequest):

    # Ask the LLM to understand the command
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.command},
        ],
    )

    answer = response.choices[0].message.content
    result = extract_json(answer)

    if not isinstance(result, dict):
        return {
            "message": "The AI returned an invalid response.",
            "ai_response": answer
        }

    action = result.get("action")

    # ---------------- CREATE ----------------
    if action == "create":

        missing_fields = result.get("missing_fields", [])

        if missing_fields:
            return {
                "message": (
                    "Missing required fields: "
                    + ", ".join(missing_fields)
                ),
                "action": action,
                "name": result.get("name"),
                "email": result.get("email"),
                "age": result.get("age"),
                "missing_fields": missing_fields
            }

        name = result.get("name")
        email = result.get("email")
        age = result.get("age")

        error = check_name(name) or check_email(email) or check_age(age)

        if error:
            return {"message": error}

        new_user = create_user(name, email, age)

        return {
            "message": "User created successfully.",
            "user": new_user
        }

    # ---------------- UPDATE ----------------
    if action == "update":

        matches = find_users_by_name(result.get("name"))

        if not matches:
            return {
                "message": f"No user found with name '{result.get('name')}'."
            }

        if len(matches) > 1:
            return {
                "message": (
                    f"Multiple users are named '{result.get('name')}'. "
                    "Please be more specific."
                ),
                "matches": matches
            }

        user = matches[0]
        changes = result.get("changes") or {}

        new_name = changes.get("name")
        new_email = changes.get("email")
        new_age = changes.get("age")

        if new_name is None and new_email is None and new_age is None:
            return {"message": "No changes were provided."}

        error = None

        if new_name is not None:
            error = check_name(new_name)

        if not error and new_email is not None:
            error = check_email(new_email)

        if not error and new_age is not None:
            error = check_age(new_age)

        if error:
            return {"message": error}

        if new_name is not None:
            user["name"] = str(new_name).strip()

        if new_email is not None:
            user["email"] = str(new_email).strip()

        if new_age is not None:
            user["age"] = int(new_age)

        persist()

        return {
            "message": "User updated successfully.",
            "user": user
        }

    # ---------------- DELETE ----------------
    if action == "delete":

        matches = find_users_by_name(result.get("name"))

        if not matches:
            return {
                "message": f"No user found with name '{result.get('name')}'."
            }

        if len(matches) > 1:
            return {
                "message": (
                    f"Multiple users are named '{result.get('name')}'. "
                    "Please be more specific."
                ),
                "matches": matches
            }

        user = matches[0]
        users.remove(user)
        persist()

        return {
            "message": "User deleted successfully.",
            "user": user
        }

    # Unknown action
    return {
        "message": "Unsupported CRUD action.",
        "action": action
    }


# Mount all /api routes onto the app
app.include_router(router)