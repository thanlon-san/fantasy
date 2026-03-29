"""
API improvements and utilities
Add this to your API to get health checks, validation, and better error handling
"""

from fastapi import HTTPException, Request
from datetime import datetime
from typing import Dict, Any
import requests

from shared.logger import get_logger
from src.constants import (
    validate_week_number,
    MIN_VALID_WEEK,
    MAX_VALID_WEEK,
    get_current_nfl_week
)

logger = get_logger(__name__)


def validate_week_param(week: int) -> int:
    """
    Validate week parameter from API request
    
    Args:
        week: Week number to validate
    
    Returns:
        Validated week number
    
    Raises:
        HTTPException: If week is invalid
    """
    if not validate_week_number(week):
        logger.warning(f"Invalid week number requested: {week}")
        raise HTTPException(
            status_code=400,
            detail=f"Week must be between {MIN_VALID_WEEK} and {MAX_VALID_WEEK}"
        )
    return week


def create_health_check_endpoint(app, get_fetcher_func):
    """
    Add a health check endpoint to the FastAPI app
    
    Usage:
        from api_improvements import create_health_check_endpoint
        create_health_check_endpoint(app, get_fetcher)
    """
    @app.get("/health", tags=["System"])
    def health_check():
        """
        Health check endpoint
        Returns system status and connectivity
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "current_nfl_week": get_current_nfl_week()
        }
        
        # Test ESPN connection
        try:
            fetcher = get_fetcher_func()
            if fetcher and fetcher.league:
                health_status["espn_connection"] = "connected"
                health_status["league_name"] = fetcher.league.settings.name if hasattr(fetcher.league, 'settings') else "Unknown"
            else:
                health_status["espn_connection"] = "not_initialized"
        except Exception as e:
            logger.error(f"Health check ESPN connection failed: {e}")
            health_status["espn_connection"] = "error"
            health_status["espn_error"] = str(e)
        
        return health_status
    
    logger.info("Health check endpoint added at /health")


def create_info_endpoint(app):
    """
    Add an API info endpoint
    
    Usage:
        from api_improvements import create_info_endpoint
        create_info_endpoint(app)
    """
    @app.get("/", tags=["System"])
    def api_info():
        """
        API information and available endpoints
        """
        return {
            "name": "Fantasy Football API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health - System health check",
                "league": "/api/league - League information",
                "standings": "/api/standings - Current standings",
                "matchups": "/api/matchups/{week} - Week matchups",
                "stats": "/api/stats/week/{week} - Week statistics",
                "teams": "/api/teams - All teams",
                "team_detail": "/api/teams/{team_id} - Team details"
            },
            "docs": "/docs - Interactive API documentation"
        }
    
    logger.info("Info endpoint added at /")


def add_request_logging_middleware(app):
    """
    Add request logging middleware
    
    Usage:
        from api_improvements import add_request_logging_middleware
        add_request_logging_middleware(app)
    """
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Log all API requests"""
        start_time = datetime.now()
        
        # Log request
        logger.info(f"{request.method} {request.url.path} - Start")
        
        # Process request
        try:
            response = await call_next(request)
            duration = (datetime.now() - start_time).total_seconds()
            
            # Log response
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Duration: {duration:.3f}s"
            )
            
            return response
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            logger.error(
                f"{request.method} {request.url.path} - "
                f"Error: {e} - "
                f"Duration: {duration:.3f}s"
            )
            raise
    
    logger.info("Request logging middleware added")


def add_error_handler(app):
    """
    Add global error handler
    
    Usage:
        from api_improvements import add_error_handler
        add_error_handler(app)
    """
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions"""
        logger.error(
            f"Unhandled exception on {request.method} {request.url.path}: {exc}",
            exc_info=True
        )
        return {
            "error": "Internal server error",
            "detail": str(exc) if app.debug else "An error occurred"
        }
    
    logger.info("Global error handler added")


# Quick setup function
def setup_api_improvements(app, get_fetcher_func, enable_rate_limit: bool = True):
    """
    One-stop setup for all API improvements
    
    Usage:
        from api_improvements import setup_api_improvements
        setup_api_improvements(app, get_fetcher, enable_rate_limit=True)
    """
    # Add health check
    create_health_check_endpoint(app, get_fetcher_func)
    
    # Add info endpoint
    create_info_endpoint(app)
    
    # Add request logging
    add_request_logging_middleware(app)
    
    # Add error handler
    add_error_handler(app)
    
    # Optionally add rate limiting
    if enable_rate_limit:
        try:
            from slowapi import Limiter, _rate_limit_exceeded_handler
            from slowapi.util import get_remote_address
            from slowapi.errors import RateLimitExceeded
            
            limiter = Limiter(key_func=get_remote_address)
            app.state.limiter = limiter
            app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
            logger.info("Rate limiting enabled")
        except ImportError:
            logger.warning("slowapi not installed, rate limiting disabled")
    
    logger.info("✅ All API improvements added successfully")


if __name__ == "__main__":
    print("API Improvements Module")
    print("=" * 60)
    print("\nTo use these improvements, add to your api.py:")
    print("\n  from api_improvements import setup_api_improvements")
    print("  setup_api_improvements(app, get_fetcher)")
    print("\nOr add individually:")
    print("  create_health_check_endpoint(app, get_fetcher)")
    print("  create_info_endpoint(app)")
    print("  add_request_logging_middleware(app)")

