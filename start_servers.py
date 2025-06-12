#!/usr/bin/env python3
"""
Server startup script for the Startup India Chatbot
Starts both FastAPI backend and Streamlit frontend
"""

import subprocess
import sys
import time
import threading
import signal
import os

def print_banner():
    """Print startup banner"""
    banner = """
🚀 Startup India Chatbot - Server Launcher
==========================================
Starting FastAPI Backend and Streamlit Frontend...
    """
    print(banner)

def start_fastapi():
    """Start FastAPI server"""
    print("🔧 Starting FastAPI backend on http://localhost:8000")
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app:app", 
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ], check=True)
    except KeyboardInterrupt:
        print("FastAPI server stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error starting FastAPI: {e}")

def start_streamlit():
    """Start Streamlit server"""
    print("🎨 Starting Streamlit frontend on http://localhost:8501")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", 
            "run", "streamlit_app.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ], check=True)
    except KeyboardInterrupt:
        print("Streamlit server stopped")
    except subprocess.CalledProcessError as e:
        print(f"Error starting Streamlit: {e}")

def check_data():
    """Check if data and embeddings exist"""
    from pathlib import Path
    
    data_dir = Path("./data")
    embeddings_dir = Path("./embeddings")
    
    data_files = list(data_dir.glob("*.txt")) if data_dir.exists() else []
    embeddings_exist = embeddings_dir.exists() and any(embeddings_dir.iterdir())
    
    if not data_files:
        print("⚠️  Warning: No data files found. Run 'python scraper.py' first.")
        return False
    
    if not embeddings_exist:
        print("⚠️  Warning: No embeddings found. Run 'python embedder.py' first.")
        return False
    
    print(f"✅ Found {len(data_files)} data files and embeddings are ready")
    return True

def main():
    """Main function to start both servers"""
    print_banner()
    
    # Check if data is ready
    if not check_data():
        print("\n🚨 Data not ready! Please run the pipeline first:")
        print("   python run_pipeline.py")
        print("   OR")
        print("   python scraper.py && python embedder.py")
        return
    
    print("\n🚀 Starting servers...")
    
    # Start FastAPI in a separate thread
    fastapi_thread = threading.Thread(target=start_fastapi, daemon=True)
    fastapi_thread.start()
    
    # Wait a moment for FastAPI to start
    time.sleep(3)
    
    print("\n" + "="*50)
    print("🎉 Servers are starting!")
    print("📍 FastAPI Backend: http://localhost:8000")
    print("📍 Streamlit Frontend: http://localhost:8501")
    print("📖 API Docs: http://localhost:8000/docs")
    print("="*50)
    print("\nPress Ctrl+C to stop both servers")
    
    try:
        # Start Streamlit in main thread
        start_streamlit()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        print("Goodbye! 👋")

if __name__ == "__main__":
    main() 