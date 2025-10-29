"""Decorator utilities for common patterns like error handling and caching."""

import functools
import logging
import time
from typing import Callable, Any
from fastapi import HTTPException

logger = logging.getLogger(__name__)


def handle_errors(error_message: str = "An error occurred"):
    """
    Decorator to handle exceptions and convert them to HTTPExceptions.
    
    Args:
        error_message: Default error message
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"{error_message}: {str(e)}"
                )
        return wrapper
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """
    Decorator to log function execution time.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"{func.__name__} executed in {execution_time:.3f}s"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"{func.__name__} failed after {execution_time:.3f}s: {e}"
            )
            raise
    return wrapper


def cache_result(ttl: int = 300):
    """
    Decorator to cache function results.
    
    Args:
        ttl: Time to live in seconds
        
    Returns:
        Decorated function
    
    Note:
        This is a simple in-memory cache. For production,
        use Redis caching instead.
    """
    cache: dict[str, tuple[Any, float]] = {}
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Check if cached result exists and is not expired
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = (result, time.time())
            
            # Clean up expired cache entries
            current_time = time.time()
            expired_keys = [
                k for k, (_, ts) in cache.items()
                if current_time - ts >= ttl
            ]
            for key in expired_keys:
                del cache[key]
            
            return result
        return wrapper
    return decorator


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0):
    """
    Decorator to retry function on failure.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed for "
                            f"{func.__name__}: {e}. Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for "
                            f"{func.__name__}: {e}"
                        )
            
            raise last_exception
        return wrapper
    return decorator


import asyncio  # Move import to avoid issues

