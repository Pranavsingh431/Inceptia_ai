"""
StartupGuru API
Production-quality FastAPI backend with comprehensive endpoints
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from loguru import logger

from config import APP_NAME, APP_VERSION, APP_DESCRIPTION, get_config
from query_handler import StartupGuruQueryHandler
from document_processor import StartupGuruProcessor
# from smart_scraper import StartupGuruScraper  # Disabled in ethical version


# Pydantic Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=500, description="User query")
    session_id: Optional[str] = Field(None, description="User session ID")
    include_debug: bool = Field(False, description="Include debug information")


class ChatResponse(BaseModel):
    response: str = Field(..., description="Generated response")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    sources: List[Dict] = Field(..., description="Source documents")
    topic_detected: str = Field(..., description="Detected topic")
    processing_time: float = Field(..., description="Processing time in seconds")
    session_id: str = Field(..., description="Session ID")
    debug: Optional[Dict] = Field(None, description="Debug information")


class SystemStats(BaseModel):
    app_name: str
    app_version: str
    status: str
    document_count: int
    query_stats: Dict
    collection_stats: Dict
    uptime: str


class ProcessingStatus(BaseModel):
    status: str
    message: str
    progress: Optional[Dict] = None


# Initialize FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=APP_DESCRIPTION,
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

# Global components
query_handler: Optional[StartupGuruQueryHandler] = None
processor: Optional[StartupGuruProcessor] = None
app_start_time = datetime.now()

# Background processing status
background_status = {"scraping": "idle", "processing": "idle"}


@app.on_event("startup")
async def startup_event():
    """Initialize application components"""
    global query_handler, processor
    
    logger.info(f"🚀 Starting {APP_NAME} v{APP_VERSION}")
    
    try:
        # Initialize processor
        processor = StartupGuruProcessor()
        logger.success("✅ Document processor initialized")
        
        # Initialize query handler
        query_handler = StartupGuruQueryHandler()
        logger.success("✅ Query handler initialized")
        
        # Check if we have documents
        stats = processor.get_collection_stats()
        if stats["total_documents"] == 0:
            logger.warning("⚠️ No documents found in collection. Consider running scraper and processor.")
        else:
            logger.success(f"✅ Found {stats['total_documents']} documents in collection")
            
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise


@app.get("/", response_model=Dict)
async def root():
    """Root endpoint with app information"""
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "status": "running",
        "endpoints": {
            "chat": "/chat",
            "health": "/health",
            "stats": "/stats",
            "scrape": "/scrape",
            "process": "/process",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check if components are initialized
        if not query_handler or not processor:
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "message": "Components not initialized"}
            )
        
        # Check collection status
        stats = processor.get_collection_stats()
        
        return {
            "status": "healthy",
            "app": APP_NAME,
            "version": APP_VERSION,
            "document_count": stats["total_documents"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "message": str(e)}
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    if not query_handler:
        raise HTTPException(status_code=503, detail="Query handler not initialized")
    
    # Generate session ID if not provided
    session_id = request.session_id or str(uuid.uuid4())
    
    try:
        logger.info(f"💬 Processing chat request: {request.message[:50]}...")
        
        # Process query (always include debug for comprehensive responses)
        result = query_handler.process_query(
            query=request.message,
            user_session=session_id,
            include_debug=True  # Always include debug for better responses
        )
        
        # Create response
        response = ChatResponse(
            response=result["response"],
            confidence=result["confidence"],
            sources=result["sources"],
            topic_detected=result["topic_detected"],
            processing_time=result["processing_time"],
            session_id=session_id,
            debug=result.get("debug")  # Always include debug info
        )
        
        logger.success(f"✅ Chat response generated (confidence: {result['confidence']:.2f})")
        return response
        
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/stats", response_model=SystemStats)
async def get_stats():
    """Get comprehensive system statistics"""
    if not query_handler or not processor:
        raise HTTPException(status_code=503, detail="Components not initialized")
    
    try:
        # Get collection stats
        collection_stats = processor.get_collection_stats()
        
        # Get query stats
        query_stats = query_handler.get_query_stats()
        
        # Calculate uptime
        uptime = datetime.now() - app_start_time
        uptime_str = f"{uptime.days}d {uptime.seconds//3600}h {(uptime.seconds//60)%60}m"
        
        return SystemStats(
            app_name=APP_NAME,
            app_version=APP_VERSION,
            status="running",
            document_count=collection_stats["total_documents"],
            query_stats=query_stats,
            collection_stats=collection_stats,
            uptime=uptime_str
        )
        
    except Exception as e:
        logger.error(f"❌ Stats error: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


@app.post("/scrape", response_model=ProcessingStatus)
async def start_scraping(background_tasks: BackgroundTasks):
    """Ethical version - uses existing content only"""
    return ProcessingStatus(
        status="not_available",
        message="Scraping disabled in ethical version. System uses existing content files."
    )


@app.get("/scrape/status")
async def get_scraping_status():
    """Get scraping status"""
    return {
        "status": background_status["scraping"],
        "processing_status": background_status["processing"]
    }


@app.post("/process", response_model=ProcessingStatus)
async def start_processing(
    background_tasks: BackgroundTasks,
    force_rebuild: bool = False
):
    """Start document processing in background"""
    if background_status["processing"] == "running":
        raise HTTPException(status_code=409, detail="Processing already in progress")
    
    background_tasks.add_task(run_processing_task, force_rebuild)
    
    return ProcessingStatus(
        status="started",
        message="Document processing started in background. Check /process/status for progress."
    )


@app.get("/process/status")
async def get_processing_status():
    """Get processing status"""
    return {
        "status": background_status["processing"],
        "scraping_status": background_status["scraping"]
    }


@app.post("/reload")
async def reload_system(background_tasks: BackgroundTasks):
    """Reload entire system (scrape + process)"""
    if background_status["scraping"] == "running" or background_status["processing"] == "running":
        raise HTTPException(status_code=409, detail="System reload already in progress")
    
    background_tasks.add_task(run_full_reload)
    
    return ProcessingStatus(
        status="started",
        message="Full system reload started. This includes scraping and processing."
    )


@app.delete("/collection")
async def delete_collection():
    """Delete the entire document collection"""
    if not processor:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    try:
        success = processor.delete_collection()
        if success:
            return {"status": "success", "message": "Collection deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete collection")
            
    except Exception as e:
        logger.error(f"❌ Delete collection error: {e}")
        raise HTTPException(status_code=500, detail=f"Error deleting collection: {str(e)}")


@app.get("/search")
async def search_documents(
    query: str,
    top_k: int = 5,
    topic_filter: Optional[str] = None
):
    """Search documents directly (for debugging)"""
    if not processor:
        raise HTTPException(status_code=503, detail="Processor not initialized")
    
    try:
        filters = {"topic": topic_filter} if topic_filter else None
        results = processor.search_similar(query, top_k=top_k, filters=filters)
        
        return {
            "query": query,
            "results_count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"❌ Search error: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")


# Background Tasks
async def run_scraping_task():
    """Background task - ethical version uses existing content"""
    global background_status
    
    background_status["scraping"] = "not_available"
    logger.info("ℹ️ Scraping disabled in ethical version")


async def run_processing_task(force_rebuild: bool = False):
    """Background task for document processing"""
    global background_status, processor
    
    background_status["processing"] = "running"
    logger.info("🔧 Starting background processing task...")
    
    try:
        if not processor:
            processor = StartupGuruProcessor()
        
        stats = processor.process_existing_content()
        
        background_status["processing"] = "completed"
        logger.success(f"✅ Processing completed: {stats}")
        
    except Exception as e:
        background_status["processing"] = "failed"
        logger.error(f"❌ Processing failed: {e}")


async def run_full_reload():
    """Background task for full system reload - ethical version"""
    global background_status
    
    try:
        # Ethical version - just process existing content
        background_status["processing"] = "running"
        
        if not processor:
            processor = StartupGuruProcessor()
        
        stats = processor.process_existing_content()
        background_status["processing"] = "completed"
        
        logger.success(f"✅ Full system reload completed: {stats} documents processed")
        
    except Exception as e:
        background_status["processing"] = "failed"
        logger.error(f"❌ Full reload failed: {e}")


# Error Handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


if __name__ == "__main__":
    uvicorn.run(
        "startupguru_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    ) 