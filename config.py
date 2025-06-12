"""
StartupGuru Configuration
Production-quality configuration management for the Startup India chatbot
"""

import os
from pathlib import Path
from typing import Dict, Any
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# App Branding
APP_NAME = "StartupGuru"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "AI-powered assistant for Startup India policies, funding, and registration"

# API Configuration - Now using environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama3-8b-8192")

# Alternative API keys (for fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY", "")

# Database Configuration
CHROMA_DB_PATH = "./startupguru_db"
COLLECTION_NAME = "startup_documents"

# Scraping Configuration
BASE_URL = "https://www.startupindia.gov.in"
SCRAPING_CONFIG = {
    "timeout": 60000,  # 60 seconds
    "wait_for": "networkidle",
    "concurrent_limit": 5,
    "retry_count": 3,
    "delay_between_requests": 2,  # seconds
}

# Content Processing
CHUNK_CONFIG = {
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "separators": ["\n\n", "\n", ".", "!", "?", ";", ",", " "],
}

# Embedding Configuration
EMBEDDING_CONFIG = {
    "model_name": "sentence-transformers/all-MiniLM-L6-v2",
    "device": "cpu",
    "batch_size": 32,
}

# Retrieval Configuration
RETRIEVAL_CONFIG = {
    "top_k": 8,
    "score_threshold": 0.1,  # Much lower threshold for broader search
    "max_context_length": 4000,
}

# Query Handling
QUERY_CONFIG = {
    "max_query_length": 500,
    "min_confidence": 0.3,
    "max_docs_retrieved": 10,
    "fallback_enabled": True,
}

# File Paths
PATHS = {
    "data": Path("./data"),
    "scraped_content": Path("./data/scraped"),
    "chroma_db": Path("./data/chroma_db"),
    "logs": Path("./logs"),
    "query_log": Path("./logs/query_log.csv"),
    "error_log": Path("./logs/error.log"),
}

# ChromaDB Configuration
CHROMA_DB_PATH = PATHS["chroma_db"]
COLLECTION_NAME = "startup_guru_docs"

# Create directories
for path in PATHS.values():
    if path.suffix == "":  # It's a directory
        path.mkdir(exist_ok=True, parents=True)
    else:  # It's a file, create parent directory
        path.parent.mkdir(exist_ok=True, parents=True)

# Logging Configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.FileHandler",
            "filename": str(PATHS["error_log"]),
            "formatter": "detailed",
            "level": "INFO"
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO"
        }
    },
    "loggers": {
        "startupguru": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": False
        }
    }
}

# FAQ Templates for better query matching
FAQ_PATTERNS = {
    "startup_definition": [
        "what is startup india",
        "what is a startup",
        "startup definition",
        "startup meaning"
    ],
    "eligibility": [
        "eligibility criteria",
        "am i eligible",
        "who can apply",
        "qualification requirements",
        "eligible for startup"
    ],
    "registration": [
        "how to register",
        "registration process",
        "startup registration",
        "how to apply",
        "application process"
    ],
    "funding": [
        "funding options",
        "financial support",
        "grants available",
        "investment schemes",
        "money for startup"
    ],
    "tax_benefits": [
        "tax exemption",
        "tax benefits",
        "income tax",
        "tax relief",
        "taxation for startup"
    ],
    "documents": [
        "required documents",
        "what documents needed",
        "paperwork required",
        "application documents"
    ]
}

# Response Templates
RESPONSE_TEMPLATES = {
    "fallback": "I'm StartupGuru, designed to help with Startup India-related queries. Could you rephrase your question about startup policies, funding, registration, or eligibility?",
    "no_results": "I couldn't find relevant information in the Startup India portal for your query. Please try rephrasing or asking about specific topics like eligibility, funding, or registration.",
    "error": "I'm experiencing technical difficulties. Please try again in a moment.",
    "confidence_low": "I found some information, but I'm not fully confident it answers your question. Here's what I found:"
}

# URLs to scrape (comprehensive list)
SCRAPING_URLS = [
    # Main pages
    f"{BASE_URL}/content/sih/en.html",
    f"{BASE_URL}/content/sih/en/startup-schemes.html",
    f"{BASE_URL}/content/sih/en/government-schemes.html",
    f"{BASE_URL}/content/sih/en/ipp.html",
    f"{BASE_URL}/content/sih/en/reources.html",
    
    # Registration and eligibility
    f"{BASE_URL}/content/sih/en/startup_recognition.html",
    f"{BASE_URL}/content/sih/en/benefits.html",
    f"{BASE_URL}/content/sih/en/startup-india-initiative.html",
    
    # Funding and support
    f"{BASE_URL}/content/sih/en/fund-of-funds.html",
    f"{BASE_URL}/content/sih/en/incubator-framework.html",
    f"{BASE_URL}/content/sih/en/seed-fund-scheme.html",
    
    # Specific schemes
    f"{BASE_URL}/content/sih/en/women_entrepreneurs.html",
    f"{BASE_URL}/content/sih/en/public_procurement.html",
    f"{BASE_URL}/content/sih/en/startup-india-learning-programme.html",
    
    # Resources
    f"{BASE_URL}/content/sih/en/reources/startup_toolkit.html",
    f"{BASE_URL}/content/sih/en/reources/idea_bank.html",
    f"{BASE_URL}/content/sih/en/reources/startup-stories.html",
]

def get_config() -> Dict[str, Any]:
    """Return complete configuration dictionary"""
    return {
        "app": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "description": APP_DESCRIPTION
        },
        "api": {
            "groq_key": GROQ_API_KEY,
            "groq_base_url": GROQ_BASE_URL,
            "groq_model": GROQ_MODEL,
            "openai_key": OPENAI_API_KEY,
            "together_key": TOGETHER_API_KEY
        },
        "database": {
            "chroma_path": CHROMA_DB_PATH,
            "collection_name": COLLECTION_NAME
        },
        "scraping": SCRAPING_CONFIG,
        "chunking": CHUNK_CONFIG,
        "embedding": EMBEDDING_CONFIG,
        "retrieval": RETRIEVAL_CONFIG,
        "query": QUERY_CONFIG,
        "paths": {str(k): str(v) for k, v in PATHS.items()},
        "faq_patterns": FAQ_PATTERNS,
        "response_templates": RESPONSE_TEMPLATES,
        "scraping_urls": SCRAPING_URLS
    }

# Initialize logging
import logging.config
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger("startupguru") 