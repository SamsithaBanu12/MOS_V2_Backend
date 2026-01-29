from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AuthenticationError(HTTPException):
    """Custom exception for authentication errors."""
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status_code=401, detail=detail)


class PermissionDeniedError(HTTPException):
    """Custom exception for permission denied errors."""
    
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=403, detail=detail)


class ResourceNotFoundError(HTTPException):
    """Custom exception for resource not found errors."""
    
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)


class ValidationError(HTTPException):
    """Custom exception for validation errors."""
    
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(status_code=400, detail=detail)
