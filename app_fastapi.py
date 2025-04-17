import logging

# Configure basic logging before importing anything
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("global.log", mode='a')
    ]
)

# Now import the application components
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers.agent import agent_router

# Create logger for this module
logger = logging.getLogger(__name__)
logger.info("Starting FastAPI application with DEBUG logging")

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

# Add routes
app.include_router(agent_router)

# Add a simple health check endpoint
@app.get("/health")
async def health_check():
    logger.debug("Health check endpoint called")
    return {"status": "ok", "message": "Service is running"}

# Log when the server starts
@app.on_event("startup")
async def startup_event():
    logger.info("Server started successfully")

# Log when the server shuts down
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Server shutting down")