"""Response builder utilities for consistent API responses."""

import time
from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


def success_response(
    data: Any,
    message: str = "Success",
    status_code: int = 200
) -> JSONResponse:
    """
    Build a standardized success response.
    
    Args:
        data: Response data
        message: Success message
        status_code: HTTP status code
        
    Returns:
        JSONResponse with standardized format
    """
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "message": message,
            "data": data,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )


def error_response(
    error: str,
    detail: Optional[str] = None,
    code: str = "ERROR",
    status_code: int = 400,
    headers: Optional[Dict[str, str]] = None
) -> JSONResponse:
    """
    Build a standardized error response.
    
    Args:
        error: Error message
        detail: Additional error details
        code: Error code
        status_code: HTTP status code
        headers: Optional response headers
        
    Returns:
        JSONResponse with standardized error format
    """
    content = {
        "success": False,
        "error": error,
        "code": code,
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if detail:
        content["detail"] = detail
        
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=headers or {}
    )


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int,
    message: str = "Success"
) -> JSONResponse:
    """
    Build a standardized paginated response.
    
    Args:
        items: List of items for current page
        total: Total number of items
        page: Current page number
        page_size: Items per page
        message: Success message
        
    Returns:
        JSONResponse with pagination metadata
    """
    total_pages = (total + page_size - 1) // page_size
    
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": message,
            "data": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }
    )

