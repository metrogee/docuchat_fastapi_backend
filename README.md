# DocuChat FastAPI Backend

A Python/FastAPI backend for the DocuChat application, built with a layered architecture and PostgreSQL.

## Architecture

```text
Client / Swagger
       ↓
FastAPI Routes
       ↓
Services
       ↓
Repositories
       ↓
SQLAlchemy Models
       ↓
PostgreSQL
```

Authentication is handled through FastAPI dependencies:

```text
Request
   ↓
require_auth()
   ↓
Extract Bearer Token
   ↓
Verify JWT
   ↓
Check Token Type
   ↓
Find User
   ↓
Authenticated User
   ↓
Protected Route
```

## Tech Stack

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Alembic
* Pydantic
* PyJWT
* bcrypt
* pytest
* pytest-cov
* GitHub Actions

## Project Structure

```text
docuchat_fastapi_backend/
│
├── config/
│
├── controllers/
│   └── health_controller.py
│
├── database/
│   ├── database.py
│   └── models.py
│
├── middleware/
│   ├── auth.py
│   └── error_handler.py
│
├── repositories/
│   ├── user_repository.py
│   ├── refresh_token_repository.py
│   └── document_repository.py
│
├── routes/
│   ├── routes.py
│   ├── auth_routes.py
│   ├── document_routes.py
│   └── api_router.py
│
├── schemas/
│   └── auth.py
│
├── services/
│   ├── auth_service.py
│   ├── user_service.py
│   └── document_service.py
│
├── src/
│   └── events.py
│
├── utils/
│   ├── errors.py
│   ├── jwt.py
│   ├── password.py
│   └── token.py
│
├── migrations/
│
├── tests/
│   ├── unit/
│   └── integration/
│
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── server.py
```

## Requirements

Make sure you have:

* Python 3.13+
* PostgreSQL
* Git

## Installation

Clone the repository and enter the project directory.

### Windows

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

## Environment Variables

Create a `.env` file in the project root.

Use `.env.example` as the template:

```text
DATABASE_URL=postgresql://username:password@localhost:5432/docuchat
JWT_ACCESS_SECRET=your-access-secret
JWT_REFRESH_SECRET=your-refresh-secret
```

Do not commit `.env` to Git.

## Database Setup

Create the PostgreSQL databases required by the application and tests.

The application uses:

```text
docuchat
```

The test suite uses a separate database:

```text
docuchat_test
```

Run the database migrations:

```powershell
alembic upgrade head
```

To check the current migration:

```powershell
alembic current
```

To check whether new migrations are required:

```powershell
alembic check
```

## Start the Server

Run:

```powershell
.venv\Scripts\python.exe server.py
```

The API runs on:

```text
http://localhost:3000
```

## API Documentation

Swagger UI:

```text
http://localhost:3000/docs
```

ReDoc:

```text
http://localhost:3000/redoc
```

## Authentication Endpoints

The authentication API is available under:

```text
/api/v1/auth
```

Available endpoints:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
POST /api/v1/auth/logout
```

Access tokens are JWTs and are sent using the Bearer authentication scheme:

```text
Authorization: Bearer <access_token>
```

## Protected Routes

Example protected endpoint:

```text
GET /api/v1/protected
```

Role-based authorization:

```text
GET /api/v1/admin-only
```

Tier-based authorization:

```text
GET /api/v1/pro-only
```

## Documents

Document endpoints are available under:

```text
/api/v1/documents
```

Document access is authenticated and associated with the authenticated user.

## Error Handling

The application uses custom application errors:

* `ValidationError`
* `UnauthorizedError`
* `ForbiddenError`
* `NotFoundError`
* `ConflictError`

Unexpected programming errors return a generic response rather than exposing internal stack traces:

```json
{
  "success": false,
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

## Testing

The project uses pytest.

Run the complete test suite:

```powershell
.venv\Scripts\python.exe -m pytest -v
```

Run tests with coverage:

```powershell
.venv\Scripts\python.exe -m pytest -v --cov=. --cov-report=term --cov-report=html
```

The HTML coverage report is generated in:

```text
htmlcov/
```

The tests use the separate `docuchat_test` PostgreSQL database so application data is not mixed with test data.

The test suite includes:

* User service unit tests
* Authentication service unit tests
* Password utility tests
* JWT tests
* Authentication integration tests
* Protected route tests
* Error handling tests
* Event listener tests

## CI

GitHub Actions runs the test suite:

* On pushes to `main`
* On pull requests targeting `main`

The CI pipeline:

1. Sets up Python
2. Installs dependencies
3. Starts PostgreSQL
4. Runs Alembic migrations
5. Runs pytest with coverage
6. Uploads the HTML coverage report as a GitHub Actions artifact

## Environment and Secrets

Never commit the real `.env` file.

The repository should contain:

```text
.env.example
```

with placeholder values only.

The `.gitignore` file excludes:

```text
.env
.venv/
__pycache__/
.pytest_cache/
htmlcov/
```

## Development Workflow

After making changes:

```powershell
.venv\Scripts\python.exe -m pytest -v
```

For coverage:

```powershell
.venv\Scripts\python.exe -m pytest -v --cov=. --cov-report=term --cov-report=html
```

For database changes:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Check Git status before committing:

```powershell
git status
```

## License

This project is developed as part of the DocuChat AI Backend Engineer Bootcamp.
