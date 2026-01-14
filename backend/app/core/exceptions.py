from fastapi import Request
from fastapi.responses import JSONResponse
import logging
import traceback
from .config import settings

logger = logging.getLogger(__name__)

async def global_exception_handler(request: Request, exc: Exception):

    logger.error(f"Global exception: {exc}")
    logger.error(traceback.format_exc())
    
    content = {
        "message": "Internal Server Error"
    }
    
    if not settings.is_production:
        content["detail"] = str(exc)
    
    return JSONResponse(
        status_code=500,
        content=content
    )
