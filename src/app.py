"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi import Header, Request, Response
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from dataclasses import dataclass
import hashlib
import hmac
import os
from pathlib import Path
import secrets
import time

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

SESSION_COOKIE = "teacher_session"
SESSION_TTL_SECONDS = 8 * 60 * 60


@dataclass
class TeacherSession:
    csrf_token: str
    expires_at: float


teacher_sessions: dict[str, TeacherSession] = {}


class TeacherCredentials(BaseModel):
    username: str
    password: str


def _session_key(session_token: str) -> str:
    return hashlib.sha256(session_token.encode("utf-8")).hexdigest()


def _get_teacher_session(request: Request) -> TeacherSession | None:
    session_token = request.cookies.get(SESSION_COOKIE)
    if not session_token:
        return None

    key = _session_key(session_token)
    session = teacher_sessions.get(key)
    if session and session.expires_at <= time.time():
        del teacher_sessions[key]
        return None
    return session


def _require_teacher(request: Request, csrf_token: str | None) -> TeacherSession:
    session = _get_teacher_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="Teacher login required")
    if not csrf_token or not hmac.compare_digest(csrf_token, session.csrf_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return session


# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/auth/status")
def get_auth_status(request: Request, response: Response):
    session = _get_teacher_session(request)
    response.headers["Cache-Control"] = "no-store"
    return {
        "authenticated": session is not None,
        "csrf_token": session.csrf_token if session else None,
    }


@app.post("/auth/login")
def login(credentials: TeacherCredentials, response: Response):
    expected_username = os.environ.get("TEACHER_USERNAME")
    expected_password = os.environ.get("TEACHER_PASSWORD")
    if not expected_username or not expected_password:
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured on the server",
        )

    username_matches = hmac.compare_digest(
        credentials.username, expected_username
    )
    password_matches = hmac.compare_digest(
        credentials.password, expected_password
    )
    if not username_matches or not password_matches:
        raise HTTPException(status_code=401, detail="Invalid teacher credentials")

    session_token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    teacher_sessions[_session_key(session_token)] = TeacherSession(
        csrf_token=csrf_token,
        expires_at=time.time() + SESSION_TTL_SECONDS,
    )

    response.set_cookie(
        key=SESSION_COOKIE,
        value=session_token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"message": "Logged in", "csrf_token": csrf_token}


@app.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    x_csrf_token: str | None = Header(default=None),
):
    _require_teacher(request, x_csrf_token)
    session_token = request.cookies.get(SESSION_COOKIE)
    if session_token:
        teacher_sessions.pop(_session_key(session_token), None)

    response.delete_cookie(
        key=SESSION_COOKIE,
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
        samesite="strict",
        path="/",
    )
    response.headers["Cache-Control"] = "no-store"
    return {"message": "Logged out"}


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
):
    """Sign up a student for an activity"""
    _require_teacher(request, x_csrf_token)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    request: Request,
    x_csrf_token: str | None = Header(default=None),
):
    """Unregister a student from an activity"""
    _require_teacher(request, x_csrf_token)

    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
