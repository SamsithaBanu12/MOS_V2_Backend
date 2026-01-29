# c2-Auth Setup Guide

## Prerequisites

Before running the application, ensure you have:

1. **Python 3.9+** installed
2. **PostgreSQL** installed and running
3. **C++ Build Tools** (for Windows) - Required for some dependencies

### Installing C++ Build Tools (Windows)

If you encounter errors installing `asyncpg` or `pydantic-core`, you need Microsoft C++ Build Tools:

**Option 1: Install Visual Studio Build Tools**
1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Run the installer
3. Select "Desktop development with C++"
4. Install

**Option 2: Use Pre-built Wheels**
```bash
pip install --upgrade pip
pip install --only-binary :all: asyncpg pydantic-core
pip install -r requirements.txt
```

## Quick Start

### 1. Create PostgreSQL Database

```bash
# Using psql
createdb c2_auth

# Or using SQL
psql -U postgres
CREATE DATABASE c2_auth;
\q
```

### 2. Set Up Environment Variables

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+asyncpg://postgres:your_password@localhost:5432/c2_auth
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

**Important:** Replace `your_password` with your PostgreSQL password.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

If you encounter build errors, try:
```bash
pip install --only-binary :all: -r requirements.txt
```

### 4. Initialize Database

Run the initialization script to create roles and permissions:

```bash
python init_db.py
```

This creates:
- **Roles:** admin, user, moderator
- **Permissions:** read_users, write_users, delete_users, manage_roles, read_reports, write_reports

### 5. Start the Server

```bash
uvicorn app.main:app --reload
```

The API will be available at: http://localhost:8000

### 6. Test the API

**Option 1: Use the test script**
```bash
pip install requests  # Install requests if not already installed
python test_api.py
```

**Option 2: Use the interactive API docs**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Option 3: Use cURL**

Register a user:
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@example.com\",\"username\":\"admin\",\"password\":\"password123\",\"role\":\"admin\"}"
```

Login:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@example.com\",\"password\":\"password123\"}"
```

## Project Structure

```
c2-auth/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Settings management
│   ├── database.py          # Database configuration
│   ├── models/
│   │   └── user.py          # User, Role, Permission models
│   ├── schemas/
│   │   ├── user.py          # User schemas
│   │   └── auth.py          # Auth schemas
│   ├── auth/
│   │   ├── security.py      # Password & JWT utilities
│   │   └── dependencies.py  # Auth dependencies
│   ├── routers/
│   │   └── auth.py          # Auth endpoints
│   └── core/
│       └── exceptions.py    # Custom exceptions
├── init_db.py               # Database initialization
├── test_api.py              # API test script
├── requirements.txt         # Dependencies
├── .env                     # Environment variables (create this)
├── .env.example             # Environment template
└── README.md                # Documentation
```

## Common Issues

### Issue: "asyncpg" or "pydantic-core" build fails

**Solution:** Install C++ Build Tools or use pre-built wheels:
```bash
pip install --only-binary :all: asyncpg pydantic-core
```

### Issue: Database connection error

**Solution:** Check your DATABASE_URL in `.env`:
- Ensure PostgreSQL is running
- Verify username, password, and database name
- Test connection: `psql -U postgres -d c2_auth`

### Issue: "Role not found" during registration

**Solution:** Run the database initialization:
```bash
python init_db.py
```

### Issue: JWT token validation fails

**Solution:** Ensure SECRET_KEY in `.env` matches between server restarts

## Next Steps

1. **Add more endpoints** - Create protected routes using `get_current_user` and `require_permission`
2. **Add database migrations** - Use Alembic for schema changes
3. **Add tests** - Write unit and integration tests
4. **Deploy** - Configure for production (HTTPS, proper CORS, etc.)

## Example: Creating a Protected Endpoint

```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, require_permission
from app.models.user import User

router = APIRouter()

# Requires authentication
@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "email": current_user.email
    }

# Requires specific permission
@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_permission("delete_users"))]
)
async def delete_user(user_id: str):
    # Only users with "delete_users" permission can access
    return {"message": f"User {user_id} deleted"}
```

## Security Checklist

- [ ] Change SECRET_KEY in production
- [ ] Use HTTPS in production
- [ ] Configure CORS properly (don't use `allow_origins=["*"]`)
- [ ] Never commit `.env` file
- [ ] Use strong passwords
- [ ] Implement rate limiting
- [ ] Add request validation
- [ ] Enable logging and monitoring
