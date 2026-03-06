"""
NarrativeFlow FastAPI Application
Main entry point for the API server
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio
import uvicorn
from typing import Dict

# Import routers
from app.api.narratives import router as narratives_router
from app.api.alerts import router as alerts_router
from app.api.analysis import router as analysis_router
from app.api.backtest_routes import router as backtest_router

# Create FastAPI app
app = FastAPI(
    title="NarrativeFlow API",
    description="Crypto Narrative Rotation Tracker - Detect narrative momentum before price moves",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(narratives_router)
app.include_router(alerts_router)
app.include_router(analysis_router)
app.include_router(backtest_router)

# Health check endpoint
@app.get("/health")
async def health_check() -> Dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "NarrativeFlow API",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root() -> Dict:
    """Root endpoint with API information."""
    return {
        "name": "NarrativeFlow API",
        "description": "Crypto Narrative Rotation Tracker",
        "version": "1.0.0",
        "thesis": "Detect narrative momentum before price moves",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "narratives": "/narratives",
            "divergences": "/divergences",
            "alerts": "/alerts",
            "analysis": "/analysis",
            "backtest": "/backtest"
        },
        "data_sources": [
            "Social: X/Twitter, Reddit, Telegram",
            "On-chain: DeFiLlama, CoinGecko",
            "Market: Binance, DEX volumes"
        ],
        "narratives_tracked": [
            "AI", "RWA", "DePIN", "Memecoins", "L2", "Gaming", "DeFi", "NFT"
        ]
    }

# System metrics endpoint
@app.get("/metrics")
async def get_metrics() -> Dict:
    """Get system performance metrics."""
    try:
        # Import performance tracker
        from app.services.performance import PerformanceTracker
        tracker = PerformanceTracker()

        return {
            "success": True,
            "metrics": tracker.get_metrics(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "metrics": {
                "data_collection": {
                    "throughput_per_second": 0,
                    "total_processed": 0,
                    "errors": 0
                },
                "classification": {
                    "speed_ms": 0,
                    "accuracy": 0,
                    "total_classified": 0
                },
                "system": {
                    "uptime_hours": 0,
                    "memory_usage_mb": 0,
                    "cpu_usage_percent": 0
                }
            }
        }

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("=" * 80)
    print("NARRATIVEFLOW API STARTING")
    print("=" * 80)
    print("Initializing services...")

    try:
        # Initialize database connections
        from app.services.database import init_database
        await init_database()
        print("✓ Database initialized")

        # Start background tasks
        from app.services.collector import DataCollector
        collector = DataCollector()
        asyncio.create_task(collector.start())
        print("✓ Data collector started")

        # Initialize AI analyzer
        from app.services.ai_analyzer import AIAnalyzer
        analyzer = AIAnalyzer()
        await analyzer.initialize()
        print("✓ AI analyzer initialized")

        print("=" * 80)
        print("ALL SYSTEMS OPERATIONAL")
        print("API docs available at: http://localhost:8000/docs")
        print("=" * 80)

    except Exception as e:
        print(f"ERROR during startup: {e}")
        print("Some services may not be available")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("Shutting down NarrativeFlow API...")
    # Add cleanup tasks here
    print("Shutdown complete")

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )