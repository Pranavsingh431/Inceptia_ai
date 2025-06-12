from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from openai import OpenAI
from typing import List, Dict
from embedder import DocumentEmbedder
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(title="Startup India Chatbot API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure API using environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY not found in environment variables. Please check your .env file.")

# Configure environment for OpenAI compatibility
os.environ["OPENAI_API_KEY"] = GROQ_API_KEY
os.environ["OPENAI_API_BASE"] = GROQ_BASE_URL

# Initialize OpenAI client with Groq
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url=GROQ_BASE_URL
)

# Initialize embedder
embedder = DocumentEmbedder()


class ChatRequest(BaseModel):
    message: str
    max_results: int = 5


class ChatResponse(BaseModel):
    response: str
    sources: List[Dict]
    context_used: str


class ReloadResponse(BaseModel):
    success: bool
    message: str


@app.get("/")
async def root():
    return {"message": "Startup India Chatbot API is running!"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint that retrieves relevant context and generates answers using Groq API
    """
    try:
        # Search for relevant context
        search_results = embedder.search_similar(request.message, request.max_results)
        
        if not search_results:
            return ChatResponse(
                response="I don't have any information about that topic in my knowledge base. Please make sure the documents have been scraped and embedded.",
                sources=[],
                context_used=""
            )
        
        # Prepare context from search results
        context_parts = []
        sources = []
        
        for result in search_results:
            context_parts.append(result["content"])
            sources.append({
                "title": result["metadata"].get("title", "Unknown"),
                "url": result["metadata"].get("url", "Unknown"),
                "filename": result["metadata"].get("filename", "Unknown"),
                "distance": result["distance"]
            })
        
        context = "\n\n".join(context_parts)
        
        # Create prompt for Groq
        prompt = f"""You are a helpful and accurate assistant for Startup India information. Use only the following context to answer the user's question. Be specific and comprehensive in your response.

Context:
{context}

User Question: {request.message}

Instructions:
- Answer only based on the provided context
- Be specific and detailed in your response
- If the context doesn't contain enough information to answer the question, say "I don't have enough information in my knowledge base to answer that question."
- Include relevant details, procedures, eligibility criteria, or requirements when applicable
- Format your response clearly with bullet points or numbered lists when appropriate

Answer:"""

        # Call Groq API
        try:
            response = client.chat.completions.create(
                model="llama3-8b-8192",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for Startup India information."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            answer = response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error calling Groq API: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
        
        return ChatResponse(
            response=answer,
            sources=sources,
            context_used=context[:500] + "..." if len(context) > 500 else context
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/reload", response_model=ReloadResponse)
async def reload_documents():
    """
    Reload and re-embed all documents
    """
    try:
        # Run the embedder process
        embedder.process_all()
        
        return ReloadResponse(
            success=True,
            message="Documents successfully reloaded and re-embedded"
        )
        
    except Exception as e:
        print(f"Error reloading documents: {str(e)}")
        return ReloadResponse(
            success=False,
            message=f"Error reloading documents: {str(e)}"
        )


@app.get("/stats")
async def get_stats():
    """
    Get statistics about the knowledge base
    """
    try:
        from pathlib import Path
        
        data_dir = Path("./data")
        embeddings_dir = Path("./embeddings")
        
        # Count text files
        text_files = list(data_dir.glob("*.txt")) if data_dir.exists() else []
        
        # Check if embeddings exist
        embeddings_exist = embeddings_dir.exists() and any(embeddings_dir.iterdir())
        
        return {
            "text_files_count": len(text_files),
            "embeddings_exist": embeddings_exist,
            "data_directory": str(data_dir),
            "embeddings_directory": str(embeddings_dir)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)