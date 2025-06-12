import os
import hashlib
import struct
from pathlib import Path
from typing import List, Dict
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


class GroqEmbeddings(Embeddings):
    """Custom embeddings class that creates deterministic embeddings from text"""
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search docs"""
        return [self._get_embedding(text) for text in texts]
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query text"""
        return self._get_embedding(text)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Create a fast deterministic embedding from text hash"""
        # Create hash of the text
        text_hash = hashlib.sha256(text.encode()).digest()
        
        # Convert hash to 1536 floats
        embedding = []
        for i in range(1536):
            # Use different bytes of hash, cycling through
            byte_idx = i % len(text_hash)
            val = (text_hash[byte_idx] / 255.0) - 0.5  # Normalize to [-0.5, 0.5]
            embedding.append(val)
            
        return embedding


class DocumentEmbedder:
    def __init__(self, data_dir="./data", embeddings_dir="./embeddings"):
        self.data_dir = Path(data_dir)
        self.embeddings_dir = Path(embeddings_dir)
        self.embeddings_dir.mkdir(exist_ok=True)
        
        # Configure API using environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        GROQ_API_KEY = os.getenv("GROQ_API_KEY")
        GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY not found in environment variables. Please check your .env file.")
            
        os.environ["OPENAI_API_KEY"] = GROQ_API_KEY
        os.environ["OPENAI_API_BASE"] = GROQ_BASE_URL
        
        # Initialize embeddings using our custom implementation
        # Groq doesn't actually support embedding models, so we use deterministic embeddings
        self.embeddings = GroqEmbeddings()
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.embeddings_dir)
        )
        self.collection_name = "startup_db"
        
    def load_documents(self) -> List[Document]:
        """Load all text files from data directory"""
        documents = []
        
        if not self.data_dir.exists():
            print(f"Data directory {self.data_dir} does not exist")
            return documents
            
        text_files = list(self.data_dir.glob("*.txt"))
        print(f"Found {len(text_files)} text files")
        
        for file_path in text_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract metadata from file content
                lines = content.split('\n')
                title = "Unknown"
                url = "Unknown"
                
                for line in lines[:5]:  # Check first 5 lines for metadata
                    if line.startswith("Title:"):
                        title = line.replace("Title:", "").strip()
                    elif line.startswith("URL:"):
                        url = line.replace("URL:", "").strip()
                
                # Remove metadata from content
                content_start = content.find("Content:")
                if content_start != -1:
                    content = content[content_start + 8:].strip()
                
                # Create document with metadata
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(file_path),
                        "title": title,
                        "url": url,
                        "filename": file_path.name
                    }
                )
                documents.append(doc)
                
            except Exception as e:
                print(f"Error loading {file_path}: {str(e)}")
                
        return documents
    
    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into chunks"""
        print("Chunking documents...")
        chunked_docs = []
        
        for doc in documents:
            chunks = self.text_splitter.split_text(doc.page_content)
            
            for i, chunk in enumerate(chunks):
                chunked_doc = Document(
                    page_content=chunk,
                    metadata={
                        **doc.metadata,
                        "chunk_id": i,
                        "total_chunks": len(chunks)
                    }
                )
                chunked_docs.append(chunked_doc)
        
        print(f"Created {len(chunked_docs)} chunks from {len(documents)} documents")
        return chunked_docs
    
    def create_embeddings(self, documents: List[Document]):
        """Create embeddings and store in ChromaDB"""
        print("Creating embeddings...")
        
        try:
            # Try to get existing collection or create new one
            try:
                collection = self.chroma_client.get_collection(name=self.collection_name)
                print("Found existing collection, clearing it...")
                self.chroma_client.delete_collection(name=self.collection_name)
            except:
                pass
            
            # Create new collection
            collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            # Prepare data for ChromaDB
            texts = [doc.page_content for doc in documents]
            metadatas = [doc.metadata for doc in documents]
            ids = [f"doc_{i}" for i in range(len(documents))]
            
            # Create embeddings in batches
            batch_size = 5  # Smaller batches for faster processing
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_metadatas = metadatas[i:i + batch_size]
                batch_ids = ids[i:i + batch_size]
                
                batch_num = i//batch_size + 1
                total_batches = (len(texts) + batch_size - 1)//batch_size
                print(f"Processing batch {batch_num}/{total_batches} ({len(batch_texts)} texts)")
                
                try:
                    # Generate embeddings using custom method
                    embeddings_list = self.embeddings.embed_documents(batch_texts)
                    print(f"  ✅ Created {len(embeddings_list)} embeddings")
                    
                    # Add to ChromaDB
                    collection.add(
                        embeddings=embeddings_list,
                        documents=batch_texts,
                        metadatas=batch_metadatas,
                        ids=batch_ids
                    )
                    
                except Exception as e:
                    print(f"Error processing batch {i//batch_size + 1}: {str(e)}")
                    continue
            
            print(f"Successfully created embeddings for {len(documents)} document chunks")
            
        except Exception as e:
            print(f"Error creating embeddings: {str(e)}")
            raise
    
    def search_similar(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search for similar documents"""
        try:
            collection = self.chroma_client.get_collection(name=self.collection_name)
            
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Search for similar documents
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i]
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching: {str(e)}")
            return []
    
    def process_all(self):
        """Complete pipeline: load, chunk, and embed documents"""
        print("Starting document processing pipeline...")
        
        # Load documents
        documents = self.load_documents()
        if not documents:
            print("No documents found to process")
            print("Make sure you have run the scraper first: python scraper.py")
            return False
        
        # Chunk documents
        chunked_docs = self.chunk_documents(documents)
        if not chunked_docs:
            print("No chunks created from documents")
            return False
        
        # Create embeddings
        try:
            self.create_embeddings(chunked_docs)
            print("Document processing completed!")
            return True
        except Exception as e:
            print(f"Failed to create embeddings: {str(e)}")
            print("This might be due to API issues or version incompatibilities.")
            return False


def main():
    embedder = DocumentEmbedder()
    embedder.process_all()


if __name__ == "__main__":
    main() 