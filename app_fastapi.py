import logging
import sys
import os
from pathlib import Path

# Explicitly create and set permissions for the log file
log_file = "global.log"
try:
    # Make sure the file exists with write permissions
    Path(log_file).touch(exist_ok=True)
    os.chmod(log_file, 0o666)  # Set read/write permissions for all users
    print(f"Created/verified log file: {log_file}")
except Exception as e:
    print(f"Error creating log file: {str(e)}")

# Ensure we have a log directory
os.makedirs('logs', exist_ok=True)

# Configure logging with less verbose output and proper flush
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(stream=sys.stdout),
        logging.FileHandler(log_file, mode='a', encoding='utf-8')
    ]
)

# Force immediate log flush
class ImmediateFileHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

# Replace the standard file handler with our immediate-flush version
for i, handler in enumerate(logging.root.handlers):
    if isinstance(handler, logging.FileHandler) and not isinstance(handler, ImmediateFileHandler):
        # Replace with immediate handler
        new_handler = ImmediateFileHandler(handler.baseFilename, mode=handler.mode, encoding=handler.encoding)
        new_handler.setFormatter(handler.formatter)
        new_handler.setLevel(handler.level)
        logging.root.handlers[i] = new_handler

# Set specific loggers to higher levels to reduce noise
logging.getLogger("src.templates").setLevel(logging.WARNING)
logging.getLogger("src.prompt").setLevel(logging.WARNING)
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("fastapi").setLevel(logging.WARNING)

# Now import the application components
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from api.routers.agent import agent_router
import time
import asyncio

# Create logger for this module
logger = logging.getLogger(__name__)
logger.info("Starting FastAPI application")

app = FastAPI(
    title="Multi-Agent API",
    description="API for interacting with the multi-agent system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        # Set a timeout for the entire request processing
        response = await asyncio.wait_for(call_next(request), timeout=30.0)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(f"Request to {request.url.path} completed in {process_time:.2f}s")
        return response
    except asyncio.TimeoutError:
        process_time = time.time() - start_time
        logger.error(f"Request to {request.url.path} timed out after {process_time:.2f}s")
        return Response(
            content="Request processing timed out",
            status_code=504,  # Gateway Timeout
            media_type="text/plain"
        )
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Error processing request to {request.url.path} after {process_time:.2f}s: {str(e)}", exc_info=True)
        return Response(
            content=f"Internal server error: {str(e)}",
            status_code=500,
            media_type="text/plain"
        )

# Add routes
app.include_router(agent_router)

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    logger.info("Health check called")
    return {"status": "ok", "message": "Service is running"}

# Log when the server starts
@app.on_event("startup")
async def startup_event():
    logger.info("Server started successfully")
    # Force log flush to ensure startup is recorded
    for handler in logging.root.handlers:
        handler.flush()

# Log when the server shuts down
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Server shutting down")