# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher login to register and unregister students
- Public, view-only access to activity rosters

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Configure the teacher credentials in the server environment. Do not put
   credentials in a checked-in file:

   ```
   export TEACHER_USERNAME="teacher"
   export TEACHER_PASSWORD="choose-a-strong-password"
   ```

3. Start the application from the repository root:

   ```
   uvicorn app:app --app-dir src --reload
   ```

   Set `COOKIE_SECURE=true` when serving the app over HTTPS. Leave it unset only
   for local HTTP development.

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

Teacher sessions expire after eight hours and are stored in memory, so restarting
the server logs teachers out. Activity records are also in memory and reset when
the server restarts.

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| GET    | `/auth/status`                                                    | Check whether the current browser has a teacher session              |
| POST   | `/auth/login`                                                     | Log in with server-configured teacher credentials                    |
| POST   | `/auth/logout`                                                    | Log out the current teacher session                                  |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Teacher-only registration; requires the session CSRF token           |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Teacher-only removal; requires the session CSRF token                |

The login endpoint accepts a JSON body containing `username` and `password`.
Successful login sets an HTTP-only, SameSite=Strict session cookie and returns
a CSRF token. Include that token in the `X-CSRF-Token` header for signup,
unregister, and logout requests.

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
