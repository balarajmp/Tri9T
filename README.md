# Tri9T Backend API

A production-quality, clean-architecture backend application built with **FastAPI**, **SQLAlchemy 2.0 (SQLite)**, and **Motor/MongoDB**.

## Features & Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs.
- **SQLAlchemy 2.0**: Relational database ORM utilizing async SQLite (via `aiosqlite`).
- **Motor**: Asynchronous MongoDB client for NoSQL operations.
- **Pydantic v2**: Secure request validation and response serialization.
- **Alembic**: Async-ready database migrations.
- **Pytest**: Full testing suite featuring in-memory SQL database fixtures and in-memory async MongoDB mocks.
- **Clean Architecture**: Strong decoupling of concerns (API -> Services -> Repositories -> Models/Schemas).

---

## Project Structure

```text
Tri9T/
├── app/
│   ├── main.py                  # App entry point, CORS, lifespan handlers
│   ├── api/                     # API Routers & dependency injection
│   │   ├── deps.py              # Dependency injection factories
│   │   └── v1/
│   │       ├── router.py        # Router composition
│   │       └── endpoints/       # Specific router paths
│   ├── core/                    # Core configs
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # SQLite Async Engine & MongoDB Connection managers
│   │   └── logging.py           # Rotation logging setup
│   ├── models/                  # DB Models
│   │   ├── sql/                 # SQLAlchemy 2.0 ORM models
│   │   └── nosql/               # Document models
│   ├── repositories/            # Data Access Layers (Repositories)
│   │   ├── base.py              # Generic Repository interface
│   │   ├── sql_repository.py    # Base SQLAlchemy repository implementation
│   │   ├── nosql_repository.py  # Base MongoDB repository implementation
│   │   └── ...                  # Entity-specific repositories
│   ├── schemas/                 # Pydantic validation schemas
│   └── services/                # Business logic services
├── migrations/                  # Alembic DB migration files
├── tests/                       # Complete test suite (Pytest)
├── .env.example                 # Environment variables template
├── alembic.ini                  # Alembic configuration
├── requirements.txt             # Project dependencies
└── README.md                    # This documentation file
```

---

## Getting Started

### 1. Setup Environment
Clone the project, then create and activate a Python virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Linux/macOS
.venv\Scripts\activate     # On Windows (PowerShell)
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Settings
Copy `.env.example` to `.env` and adjust the variables as required:
```bash
cp .env.example .env
```

---

## Database Migrations (Alembic)

The SQLite database migrations are handled asynchronously.

- **Generate a new migration:**
  ```bash
  alembic revision --autogenerate -m "Describe migration"
  ```
- **Apply migrations to the database:**
  ```bash
  alembic upgrade head
  ```

---

## Running the Application

Start the local Uvicorn development server:
```bash
uvicorn app.main:app --reload
```

Interactive API documentation will be available at:
- **Swagger UI**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **ReDoc**: [http://localhost:8000/api/v1/redoc](http://localhost:8000/api/v1/redoc)

---

## Running the Test Suite

The test suite runs completely isolated:
- SQL database is mocked using an **in-memory SQLite** instance.
- MongoDB database is mocked using an **in-memory MongoDB mock**, requiring no running local MongoDB services.

Run all tests via `pytest`:
```bash
pytest
```
