# c2-Auth API

A production-ready FastAPI backend with PostgreSQL, SQLAlchemy 2.0 ORM, JWT authentication, and Role-Based Access Control (RBAC).

## Features

- ✅ **FastAPI** - Modern, fast web framework
- ✅ **PostgreSQL** - Robust relational database
- ✅ **SQLAlchemy 2.0** - Modern ORM with async support
- ✅ **JWT Authentication** - Secure token-based auth
- ✅ **RBAC** - Role-Based Access Control with permissions
- ✅ **Password Hashing** - Bcrypt for secure password storage
- ✅ **Async/Await** - Full async support throughout

## Project Structure

```
c2-auth/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── database.py          # Database configuration
│   ├── models/
│   │   └── user.py          # Database models
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
├── requirements.txt
├── .env.example
└── README.md
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update the values:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/c2_auth
SECRET_KEY=your-secret-key-here-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Create PostgreSQL Database

```bash
# Using psql
createdb c2_auth

# Or using PostgreSQL client
psql -U postgres
CREATE DATABASE c2_auth;
```

### 4. Initialize Database with Roles and Permissions

Before starting the application, you need to create initial roles and permissions. Start a Python shell:

```bash
python
```

Then run:

```python
import asyncio
from app.database import AsyncSessionLocal
from app.models.user import Role, Permission

async def init_db():
    async with AsyncSessionLocal() as session:
        # Create permissions
        permissions = [
            Permission(name="read_users"),
            Permission(name="write_users"),
            Permission(name="delete_users"),
            Permission(name="manage_roles"),
        ]
        session.add_all(permissions)
        await session.flush()
        
        # Create roles
        admin_role = Role(name="admin")
        user_role = Role(name="user")
        
        # Assign all permissions to admin
        admin_role.permissions = permissions
        
        # Assign limited permissions to user
        user_role.permissions = [p for p in permissions if p.name == "read_users"]
        
        session.add_all([admin_role, user_role])
        await session.commit()
        print("Database initialized with roles and permissions!")

asyncio.run(init_db())
```

### 5. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the application is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

#### Register User
```http
POST /auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "password123",
  "role": "admin"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "uuid-here",
    "email": "user@example.com",
    "username": "john_doe",
    "role": "admin"
  }
}
```

#### Login
```http
POST /auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "username": "john_doe",
  "email": "user@example.com",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "admin",
  "permissions": ["read_users", "write_users", "delete_users", "manage_roles"]
}
```

### Using Protected Endpoints

To access protected endpoints, include the JWT token in the Authorization header:

```http
GET /protected-endpoint
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Example: Creating Protected Endpoints

```python
from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user, require_permission
from app.models.user import User

router = APIRouter()

# Endpoint requiring authentication
@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"user": current_user.username}

# Endpoint requiring specific permission
@router.delete("/users/{user_id}", dependencies=[Depends(require_permission("delete_users"))])
async def delete_user(user_id: str):
    return {"message": f"User {user_id} deleted"}
```

## Database Models

### User
- `id` (UUID) - Primary key
- `email` (String) - Unique, indexed
- `username` (String)
- `password_hash` (String)
- `role_id` (Integer) - Foreign key to Role
- `is_active` (Boolean)
- `created_at` (DateTime)

### Role
- `id` (Integer) - Primary key
- `name` (String) - Unique (e.g., "admin", "user")

### Permission
- `id` (Integer) - Primary key
- `name` (String) - Unique (e.g., "read_users", "write_users")

### RolePermission
- `role_id` (Integer) - Foreign key to Role
- `permission_id` (Integer) - Foreign key to Permission

## Security Notes

1. **Change SECRET_KEY**: Always use a strong, random secret key in production
2. **CORS Configuration**: Update `allow_origins` in `main.py` for production
3. **HTTPS**: Always use HTTPS in production
4. **Database Credentials**: Never commit `.env` file to version control
5. **Token Expiration**: Adjust `ACCESS_TOKEN_EXPIRE_MINUTES` based on your security requirements

## Testing

### Example cURL Commands

**Register:**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "username": "admin",
    "password": "password123",
    "role": "admin"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'
```

## License

MIT
