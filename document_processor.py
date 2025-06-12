#!/usr/bin/env python3
"""
Enhanced Document Processor for StartupGuru
Processes scraped documents and creates embeddings for vector database
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from loguru import logger
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from config import *
from datetime import datetime
import hashlib

class StartupGuruProcessor:
    """Enhanced processor for Startup India scraped content"""
    
    def __init__(self):
        logger.info("🚀 Initializing StartupGuru Document Processor...")
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(EMBEDDING_CONFIG["model_name"])
        logger.info(f"✅ Loaded embedding model: {EMBEDDING_CONFIG['model_name']}")
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))
        self.collection_name = COLLECTION_NAME
        
        try:
            # Try to get existing collection
            self.collection = self.chroma_client.get_collection(self.collection_name)
            logger.info(f"✅ Connected to existing collection: {self.collection_name}")
        except:
            # Create new collection
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"description": "StartupGuru documents with intelligent chunking"}
            )
            logger.info(f"✅ Created new collection: {self.collection_name}")
        
        # Initialize text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_CONFIG["chunk_size"],
            chunk_overlap=CHUNK_CONFIG["chunk_overlap"],
            separators=CHUNK_CONFIG["separators"]
        )
        
    def process_scraped_content(self) -> int:
        """Process all scraped content files"""
        logger.info("📁 Processing scraped content files...")
        
        scraped_dir = PATHS["data"] / "scraped"
        if not scraped_dir.exists():
            logger.error(f"❌ Scraped content directory not found: {scraped_dir}")
            return 0
        
        json_files = list(scraped_dir.glob("*.json"))
        logger.info(f"📄 Found {len(json_files)} scraped files to process")
        
        total_processed = 0
        all_documents = []
        
        for file_path in json_files:
            try:
                processed_count = self._process_single_file(file_path)
                total_processed += processed_count
                logger.info(f"✅ Processed {file_path.name}: {processed_count} chunks")
            except Exception as e:
                logger.error(f"❌ Error processing {file_path.name}: {e}")
        
        # Create and store embeddings for all documents
        if all_documents:
            self._create_and_store_embeddings(all_documents)
        
        # Add FAQ patterns
        self._create_faq_embeddings()
        
        # Save processing stats
        stats = self._save_processing_stats(all_documents)
        
        logger.info(f"✅ Processing completed! Total chunks: {total_processed}")
        return total_processed
        
    def _process_single_file(self, file_path: Path) -> int:
        """Process a single scraped document file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scraped_doc = json.load(f)
            
            # Validate required fields
            required_fields = ['title', 'content', 'url', 'topic', 'section']
            if not all(field in scraped_doc for field in required_fields):
                logger.warning(f"⚠️ Missing required fields in {file_path.name}")
                return 0
            
            # Skip if content is too short
            if len(scraped_doc['content']) < 200:
                logger.warning(f"⚠️ Content too short in {file_path.name}")
                return 0
            
            # Create chunks and store in collection
            return self._chunk_and_store_document(scraped_doc)
            
        except Exception as e:
            logger.error(f"❌ Error processing file {file_path}: {e}")
            return 0
    
    def _chunk_and_store_document(self, scraped_doc: Dict) -> int:
        """Chunk document and create Document objects"""
        # Split content into chunks
        chunks = self.text_splitter.split_text(scraped_doc['content'])
        
        documents = []
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Skip very small chunks
                continue
                
            # Create unique chunk ID
            chunk_id = f"{scraped_doc['url']}#{i}"
            chunk_hash = hashlib.md5(chunk_id.encode()).hexdigest()
            
            # Create metadata
            metadata = {
                "title": scraped_doc['title'],
                "url": scraped_doc['url'],
                "topic": scraped_doc['topic'],
                "section": scraped_doc['section'],
                "source_type": scraped_doc.get('source_type', 'scraped'),
                "chunk_id": chunk_hash,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "chunk_length": len(chunk),
                "word_count": len(chunk.split()),
                "last_updated": scraped_doc.get('last_updated', datetime.now().isoformat())
            }
            
            # Create Document object
            doc = Document(
                page_content=chunk,
                metadata=metadata
            )
            documents.append(doc)
        
        # Store in collection
        if documents:
            self._create_and_store_embeddings(documents)
        
        return len(documents)
    
    def _create_and_store_embeddings(self, documents: List[Document]) -> None:
        """Create embeddings and store in ChromaDB"""
        if not documents:
            return
            
        logger.info("🔮 Creating embeddings and storing in vector database...")
        
        # Process in batches
        batch_size = EMBEDDING_CONFIG["batch_size"]
        total_batches = (len(documents) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(documents))
            batch_docs = documents[start_idx:end_idx]
            
            try:
                logger.info(f"Processing batch {batch_idx + 1}/{total_batches} ({len(batch_docs)} documents)")
                
                # Extract content and metadata
                texts = [doc.page_content for doc in batch_docs]
                metadatas = [doc.metadata for doc in batch_docs]
                ids = [doc.metadata["chunk_id"] for doc in batch_docs]
                
                # Create embeddings
                embeddings = self.embedding_model.encode(
                    texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True
                ).tolist()
                
                # Store in ChromaDB
                self.collection.add(
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                    ids=ids
                )
                
                logger.info(f"✅ Stored batch {batch_idx + 1}/{total_batches}")
                
            except Exception as e:
                logger.error(f"❌ Error processing batch {batch_idx + 1}: {e}")

    def _create_faq_embeddings(self) -> None:
        """Create special embeddings for FAQ patterns"""
        logger.info("❓ Creating FAQ pattern embeddings...")
        
        faq_documents = []
        
        for category, patterns in FAQ_PATTERNS.items():
            for pattern in patterns:
                faq_doc = Document(
                    page_content=f"FAQ: {pattern}",
                    metadata={
                        "title": f"FAQ - {category}",
                        "url": "internal://faq",
                        "topic": category,
                        "section": "faq",
                        "source_type": "faq_pattern",
                        "chunk_id": f"faq_{category}_{hash(pattern)}",
                        "chunk_index": 0,
                        "total_chunks": 1,
                        "chunk_length": len(pattern),
                        "word_count": len(pattern.split())
                    }
                )
                faq_documents.append(faq_doc)
        
        # Create and store FAQ embeddings
        if faq_documents:
            self._create_and_store_embeddings(faq_documents)
            logger.info(f"✅ Created {len(faq_documents)} FAQ pattern embeddings")

    def search_similar(self, query: str, top_k: int = None, filters: Dict = None) -> List[Dict]:
        """Search for similar documents"""
        if top_k is None:
            top_k = RETRIEVAL_CONFIG['top_k']
        
        try:
            # Create query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Prepare where clause for filtering
            where_clause = {}
            if filters:
                where_clause.update(filters)
            
            # Search in ChromaDB - increase search size to allow for filtering
            search_size = max(top_k * 3, 20)  # Search more to account for filtering
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=search_size,
                where=where_clause if where_clause else None
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                similarity = 1 - results['distances'][0][i]  # Convert distance to similarity
                result = {
                    "id": results['ids'][0][i],
                    "content": results['documents'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "distance": results['distances'][0][i],
                    "similarity": similarity
                }
                formatted_results.append(result)
            
            # Filter by confidence threshold
            min_similarity = RETRIEVAL_CONFIG['score_threshold']
            filtered_results = [
                r for r in formatted_results 
                if r['similarity'] >= min_similarity
            ]
            
            # Return only top_k results
            return filtered_results[:top_k]
            
        except Exception as e:
            logger.error(f"❌ Error searching similar documents: {e}")
            return []

    def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        try:
            count = self.collection.count()
            
            # Get sample of metadata to analyze
            sample_results = self.collection.get(limit=min(1000, count))
            
            stats = {
                "total_documents": count,
                "topics": {},
                "sections": {},
                "source_types": {}
            }
            
            for metadata in sample_results.get('metadatas', []):
                # Count topics
                topic = metadata.get('topic', 'unknown')
                stats['topics'][topic] = stats['topics'].get(topic, 0) + 1
                
                # Count sections
                section = metadata.get('section', 'unknown')
                stats['sections'][section] = stats['sections'].get(section, 0) + 1
                
                # Count source types
                source_type = metadata.get('source_type', 'unknown')
                stats['source_types'][source_type] = stats['source_types'].get(source_type, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting collection stats: {e}")
            return {"total_documents": 0, "topics": {}, "sections": {}, "source_types": {}}

    def _save_processing_stats(self, documents: List[Document]) -> Dict:
        """Save processing statistics"""
        stats = {
            "processed_at": datetime.now().isoformat(),
            "total_documents": len(documents),
            "total_chunks": len(documents),
            "collection_count": self.collection.count(),
            "topics": {},
            "sections": {},
            "avg_chunk_length": 0,
            "total_words": 0
        }
        
        # Calculate detailed stats
        chunk_lengths = []
        total_words = 0
        
        for doc in documents:
            # Topic distribution
            topic = doc.metadata.get("topic", "unknown")
            stats["topics"][topic] = stats["topics"].get(topic, 0) + 1
            
            # Section distribution
            section = doc.metadata.get("section", "unknown")
            stats["sections"][section] = stats["sections"].get(section, 0) + 1
            
            # Length stats
            chunk_length = len(doc.page_content)
            chunk_lengths.append(chunk_length)
            
            word_count = doc.metadata.get("word_count", len(doc.page_content.split()))
            total_words += word_count
        
        stats["avg_chunk_length"] = np.mean(chunk_lengths) if chunk_lengths else 0
        stats["total_words"] = total_words
        
        # Save stats to file
        stats_dir = Path("./logs")
        stats_dir.mkdir(exist_ok=True)
        stats_file = stats_dir / "processing_stats.json"
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved processing stats to {stats_file}")
        return stats

    def delete_collection(self) -> bool:
        """Delete the entire collection"""
        try:
            self.chroma_client.delete_collection(self.collection_name)
            logger.info(f"✅ Deleted collection: {self.collection_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error deleting collection: {e}")
            return False


def main():
    """Run document processing on scraped content"""
    processor = StartupGuruProcessor()
    total_processed = processor.process_scraped_content()
    
    logger.info(f"🎉 Processing completed!")
    logger.info(f"📊 Stats: Total processed {total_processed} documents")
    
    # Test search
    test_results = processor.search_similar("What is startup eligibility criteria?", top_k=5)
    logger.info(f"🔍 Test search returned {len(test_results)} results")
    
    if test_results:
        logger.info(f"🎯 Best match similarity: {test_results[0]['similarity']:.3f}")


if __name__ == "__main__":
    main() 