#!/usr/bin/env python3
"""
StartupGuru Main CLI - Ethical Version
Production AI Assistant for Startup India (using existing content)
"""

import sys
import subprocess
import time
import click
from loguru import logger

from config import APP_NAME, APP_VERSION
from document_processor import StartupGuruProcessor
from query_handler import StartupGuruQueryHandler


@click.group()
@click.version_option(version=APP_VERSION, prog_name=APP_NAME)
def cli():
    """StartupGuru - Production AI Assistant for Startup India"""
    logger.info(f"🚀 {APP_NAME} v{APP_VERSION}")


@cli.command()
def process():
    """Process existing content and create embeddings ethically"""
    logger.info("🧠 Starting ethical document processing...")
    
    try:
        processor = StartupGuruProcessor()
        total_processed = processor.process_existing_content()
        
        if total_processed > 0:
            logger.success("✅ Document processing completed!")
            logger.info(f"📊 Processed: {total_processed} documents from existing content")
            
            # Test the search functionality
            logger.info("🔍 Testing search functionality...")
            test_results = processor.search_similar("eligibility criteria for startups", top_k=3)
            logger.info(f"✅ Search test successful! Found {len(test_results)} results")
            
            for i, result in enumerate(test_results[:2]):
                title = result.get('metadata', {}).get('title', 'Unknown')
                similarity = result.get('similarity', 0)
                logger.info(f"  {i+1}. {title} (similarity: {similarity:.3f})")
        else:
            logger.warning("⚠️ No content processed. Check your data directory.")
            
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}")
        sys.exit(1)


@cli.command()
def pipeline():
    """Run complete ethical pipeline: process → verify → ready"""
    logger.info(f"🚀 Starting ethical {APP_NAME} pipeline...")
    
    start_time = time.time()
    
    try:
        # Step 1: Processing existing content
        logger.info("📋 Step 1/3: Processing Existing Content")
        processor = StartupGuruProcessor()
        total_processed = processor.process_existing_content()
        
        if total_processed == 0:
            logger.error("❌ No content to process! Check your data directory.")
            sys.exit(1)
            
        logger.success(f"✅ Processed {total_processed} documents")
        
        # Step 2: Verification
        logger.info("📋 Step 2/3: System Verification")
        handler = StartupGuruQueryHandler()
        
        # Test query
        test_result = handler.process_query("What is Startup India?")
        if test_result.get('confidence', 0) > 0.3:
            logger.success("✅ System verification passed!")
        else:
            logger.warning("⚠️ System verification: Low confidence responses")
        
        # Step 3: Ready to deploy
        logger.info("📋 Step 3/3: Deployment Ready")
        
        total_time = time.time() - start_time
        logger.success(f"🎉 Pipeline completed in {total_time:.1f} seconds!")
        
        # Display final stats
        collection_stats = processor.get_collection_stats()
        logger.info("📊 Final System Stats:")
        logger.info(f"  • Documents: {collection_stats['total_documents']:,}")
        logger.info(f"  • Ready for deployment: ✅")
        
        logger.info("\n🚀 Next steps:")
        logger.info("  • Run 'python startupguru_main.py serve' for API")
        logger.info("  • Run 'python startupguru_main.py frontend' for UI")
        logger.info("  • Run 'python startupguru_main.py deploy' for both")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        sys.exit(1)


@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind the server')
@click.option('--port', default=8000, help='Port to bind the server')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def serve(host: str, port: int, reload: bool):
    """Start the FastAPI server"""
    logger.info(f"🚀 Starting {APP_NAME} API server...")
    
    try:
        import uvicorn
        uvicorn.run(
            "startupguru_api:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ Server failed to start: {e}")
        sys.exit(1)


@cli.command()
@click.option('--port', default=8501, help='Port for Streamlit app')
def frontend(port: int):
    """Start the Streamlit frontend"""
    logger.info(f"🎨 Starting {APP_NAME} frontend...")
    
    try:
        subprocess.run([
            "streamlit", "run", "startupguru_app.py",
            "--server.port", str(port),
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ])
    except Exception as e:
        logger.error(f"❌ Frontend failed to start: {e}")
        sys.exit(1)


@cli.command()
def deploy():
    """Deploy both backend and frontend"""
    logger.info(f"🚀 Deploying {APP_NAME}...")
    
    try:
        # Start API server in background
        api_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "startupguru_api:app",
            "--host", "0.0.0.0", "--port", "8000"
        ])
        
        time.sleep(3)  # Wait for API to start
        logger.info("✅ API server started on http://localhost:8000")
        
        # Start Streamlit frontend
        logger.info("🎨 Starting frontend on http://localhost:8501")
        subprocess.run([
            "streamlit", "run", "startupguru_app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ])
        
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down...")
        api_process.terminate()
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        sys.exit(1)


@cli.command()
def test():
    """Test the complete system"""
    logger.info(f"🧪 Testing {APP_NAME} system...")
    
    try:
        # Test document processor
        processor = StartupGuruProcessor()
        stats = processor.get_collection_stats()
        
        if stats['total_documents'] == 0:
            logger.error("❌ No documents found in collection! Run 'process' first.")
            sys.exit(1)
        
        logger.success(f"✅ Found {stats['total_documents']} documents")
        
        # Test query handler
        handler = StartupGuruQueryHandler()
        
        test_queries = [
            "What is Startup India?",
            "How to register a startup?",
            "What are the eligibility criteria?",
            "What funding options are available?"
        ]
        
        for query in test_queries:
            result = handler.process_query(query)
            confidence = result.get('confidence', 0)
            
            if confidence > 0.3:
                logger.success(f"✅ Query '{query[:30]}...': {confidence:.1%} confidence")
            else:
                logger.warning(f"⚠️ Query '{query[:30]}...': {confidence:.1%} confidence (low)")
        
        logger.success("🎉 System testing completed!")
        
    except Exception as e:
        logger.error(f"❌ Testing failed: {e}")
        sys.exit(1)


@cli.command()
def stats():
    """Show system statistics"""
    try:
        processor = StartupGuruProcessor()
        stats = processor.get_collection_stats()
        
        logger.info(f"📊 {APP_NAME} System Statistics")
        logger.info(f"  • Total Documents: {stats['total_documents']:,}")
        logger.info(f"  • Topics: {len(stats.get('topics', {}))}")
        logger.info(f"  • Sections: {len(stats.get('sections', {}))}")
        
        # Query stats if available
        try:
            handler = StartupGuruQueryHandler()
            query_stats = handler.get_query_stats()
            logger.info(f"  • Total Queries Processed: {query_stats.get('total_queries', 0)}")
        except:
            logger.info("  • Query Handler: Not initialized")
        
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to reset all data?')
def reset():
    """Reset all data (delete collection and logs)"""
    logger.info("🗑️ Resetting all data...")
    
    try:
        processor = StartupGuruProcessor()
        processor.delete_collection()
        
        # Clear logs
        import shutil
        from pathlib import Path
        from config import PATHS
        
        logs_dir = Path(PATHS["logs"])
        if logs_dir.exists():
            shutil.rmtree(logs_dir)
            logs_dir.mkdir(parents=True, exist_ok=True)
        
        logger.success("✅ All data reset successfully!")
        logger.info("Run 'python startupguru_main.py process' to rebuild")
        
    except Exception as e:
        logger.error(f"❌ Reset failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli() 