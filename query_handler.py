"""
StartupGuru Query Handler
Synchronous RAG pipeline for ethical document retrieval and response generation
"""

import csv
import json
import time
import re
from typing import Dict, List, Optional
from pathlib import Path

from groq import Groq
from loguru import logger

from config import (
    GROQ_API_KEY, GROQ_MODEL, QUERY_CONFIG, PATHS,
    APP_NAME, FAQ_PATTERNS, get_config
)
from document_processor import StartupGuruProcessor


class StartupGuruQueryHandler:
    """Synchronous query handler for StartupGuru"""
    
    def __init__(self):
        self.config = get_config()
        self.processor = StartupGuruProcessor()
        self.client = Groq(api_key=GROQ_API_KEY)
        
        # Response templates
        self.templates = {
            "greeting": f"Hello! I'm {APP_NAME}, your AI assistant for Startup India information. How can I help you today?",
            "no_results": "I couldn't find specific information about your query in my knowledge base. Could you try rephrasing your question or ask about startup registration, eligibility criteria, or funding schemes?",
            "confidence_low": "Based on the available information, here's what I found (though I'm not completely certain this fully answers your question):",
            "error": "I apologize, but I encountered an error while processing your request. Please try again or contact support if the issue persists.",
            "fallback": "I can help you with questions about Startup India policies, registration procedures, eligibility criteria, funding schemes, and related topics. Please ask a more specific question."
        }
        
        # FAQ patterns
        self.faq_patterns = FAQ_PATTERNS
        
        # Setup query logging
        self.query_log_file = PATHS["query_log"]
        self._initialize_query_log()

    def _initialize_query_log(self) -> None:
        """Initialize query log CSV file"""
        if not self.query_log_file.exists():
            self.query_log_file.parent.mkdir(exist_ok=True, parents=True)
            with open(self.query_log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'query', 'response', 'confidence', 
                    'retrieved_docs', 'processing_time', 'topic_detected',
                    'fallback_used', 'user_session'
                ])

    def process_query(
        self, 
        query: str, 
        user_session: str = "default",
        include_debug: bool = False
    ) -> Dict:
        """Process user query with full RAG pipeline"""
        start_time = time.time()
        
        logger.info(f"🔍 Processing query: {query[:50]}...")
        
        try:
            # Step 1: Validate and preprocess query
            validation_result = self._validate_query(query)
            if not validation_result["valid"]:
                return self._create_error_response(validation_result["message"])
            
            processed_query = self._preprocess_query(query)
            
            # Step 2: Detect query intent and topic
            intent_info = self._detect_query_intent(processed_query)
            
            # Step 3: Retrieve relevant documents
            retrieved_docs = self._retrieve_documents(
                processed_query, 
                intent_info
            )
            
            # Step 4: Check retrieval confidence
            confidence = self._calculate_confidence(retrieved_docs, intent_info)
            
            # Step 5: Generate response based on confidence
            if confidence < QUERY_CONFIG["min_confidence"]:
                response = self._handle_low_confidence(
                    processed_query, retrieved_docs, intent_info
                )
            else:
                response = self._generate_response(
                    processed_query, retrieved_docs, intent_info
                )
            
            # Step 6: Post-process response
            final_response = self._post_process_response(response, retrieved_docs)
            
            # Step 7: Log query
            processing_time = time.time() - start_time
            self._log_query(
                query, final_response, confidence, retrieved_docs, 
                processing_time, intent_info, user_session
            )
            
            # Step 8: Prepare final result
            result = {
                "response": final_response["text"],
                "confidence": confidence,
                "sources": final_response["sources"],
                "topic_detected": intent_info["topic"],
                "processing_time": processing_time,
                "retrieved_docs_count": len(retrieved_docs)
            }
            
            if include_debug:
                result["debug"] = {
                    "processed_query": processed_query,
                    "intent_info": intent_info,
                    "retrieved_docs": retrieved_docs[:2],  # First 2 for debugging
                    "confidence_breakdown": final_response.get("confidence_breakdown", {})
                }
            
            logger.success(f"✅ Query processed in {processing_time:.2f}s (confidence: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"❌ Error processing query: {e}")
            processing_time = time.time() - start_time
            
            self._log_query(
                query, {"text": self.templates["error"], "sources": []}, 
                0.0, [], processing_time, {"topic": "error"}, user_session
            )
            
            return self._create_error_response(self.templates["error"])

    def _validate_query(self, query: str) -> Dict:
        """Validate user query"""
        if not query or not query.strip():
            return {"valid": False, "message": "Please enter a question."}
        
        if len(query) > QUERY_CONFIG["max_query_length"]:
            return {
                "valid": False, 
                "message": f"Query too long. Please keep it under {QUERY_CONFIG['max_query_length']} characters."
            }
        
        return {"valid": True, "message": ""}

    def _preprocess_query(self, query: str) -> str:
        """Preprocess and clean query"""
        # Normalize whitespace
        query = re.sub(r'\s+', ' ', query).strip()
        
        # Handle common query prefixes
        prefixes_to_remove = [
            r'^(can you|could you|please|tell me|what is|what are|how to|how do|how can)\s*',
            r'^(i want to know|i need to know|i am looking for)\s*',
        ]
        
        for prefix in prefixes_to_remove:
            query = re.sub(prefix, '', query, flags=re.IGNORECASE)
        
        return query.strip()

    def _detect_query_intent(self, query: str) -> Dict:
        """Detect query intent and topic"""
        query_lower = query.lower()
        
        # Topic detection based on keywords
        topic_keywords = {
            "eligibility": ["eligibility", "criteria", "qualify", "qualification", "eligible", "who can"],
            "registration": ["register", "registration", "apply", "application", "how to register", "process"],
            "funding": ["funding", "fund", "money", "grant", "scheme", "financial", "investment", "loan"],
            "tax_benefits": ["tax", "exemption", "benefit", "deduction", "income tax", "relief"],
            "documents": ["document", "paperwork", "certificate", "proof", "required documents"],
            "startup_definition": ["what is startup", "startup meaning", "definition", "startup india"]
        }
        
        intent_scores = {}
        for topic, keywords in topic_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                intent_scores[topic] = score
        
        # Determine primary topic
        if intent_scores:
            primary_topic = max(intent_scores.items(), key=lambda x: x[1])[0]
        else:
            primary_topic = "general"
        
        # Query type detection
        if any(word in query_lower for word in ["what", "definition", "meaning", "explain"]):
            query_type = "definition"
        elif any(word in query_lower for word in ["how", "process", "step", "procedure"]):
            query_type = "process"
        elif any(word in query_lower for word in ["eligibility", "criteria", "qualify", "who can"]):
            query_type = "criteria"
        elif any(word in query_lower for word in ["list", "types", "options", "available"]):
            query_type = "list"
        else:
            query_type = "general"
        
        return {
            "topic": primary_topic,
            "query_type": query_type,
            "intent_scores": intent_scores,
            "keywords_found": [kw for topic, keywords in topic_keywords.items() 
                             for kw in keywords if kw in query_lower]
        }

    def _retrieve_documents(self, query: str, intent_info: Dict) -> List[Dict]:
        """Retrieve relevant documents from vector store"""
        try:
            # Primary search with topic filter if specific topic detected
            filters = None
            if intent_info["topic"] != "general" and intent_info["intent_scores"].get(intent_info["topic"], 0) > 1:
                filters = {"topic": intent_info["topic"]}
            
            # Retrieve documents
            results = self.processor.search_similar(
                query, 
                top_k=QUERY_CONFIG["max_docs_retrieved"],
                filters=filters
            )
            
            # Log retrieval results
            logger.info(f"📄 Retrieved {len(results)} documents")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error retrieving documents: {e}")
            return []

    def _calculate_confidence(self, retrieved_docs: List[Dict], intent_info: Dict) -> float:
        """Calculate confidence score for retrieved results"""
        if not retrieved_docs:
            return 0.0
        
        # Base confidence from similarity scores
        similarities = [doc.get("similarity", 0.0) for doc in retrieved_docs]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        
        # Topic relevance boost
        topic_boost = 0.1 if intent_info["topic"] != "general" else 0.0
        
        # Multiple results boost
        results_boost = min(0.1, len(retrieved_docs) * 0.02)
        
        # Calculate final confidence
        confidence = min(1.0, avg_similarity + topic_boost + results_boost)
        
        return confidence

    def _handle_low_confidence(
        self, 
        query: str, 
        retrieved_docs: List[Dict], 
        intent_info: Dict
    ) -> Dict:
        """Handle queries with low confidence scores"""
        
        # If we have some results but low confidence, mention uncertainty
        if retrieved_docs:
            response_text = self.templates["confidence_low"] + "\n\n"
            response_text += self._generate_basic_response(query, retrieved_docs[:2])
            
            return {
                "text": response_text,
                "sources": self._extract_sources(retrieved_docs[:2]),
                "confidence_breakdown": {
                    "retrieval_confidence": "low",
                    "reason": "Low similarity scores"
                }
            }
        
        # No relevant results found
        return {
            "text": self.templates["no_results"],
            "sources": [],
            "confidence_breakdown": {
                "retrieval_confidence": "none",
                "reason": "No relevant documents found"
            }
        }

    def _generate_response(
        self, 
        query: str, 
        retrieved_docs: List[Dict], 
        intent_info: Dict
    ) -> Dict:
        """Generate response using LLM with retrieved context"""
        
        # Prepare context from retrieved documents
        context_parts = []
        for i, doc in enumerate(retrieved_docs[:4]):  # Use top 4 documents
            content = doc["content"]
            if len(content) > 800:  # Truncate long content
                content = content[:800] + "..."
            
            context_parts.append(f"[Document {i+1}]:\n{content}")
        
        context = "\n\n".join(context_parts)
        
        # Create prompt
        prompt = self._create_prompt(query, context, intent_info["query_type"], intent_info)
        
        try:
            # Call LLM
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {
                        "role": "system", 
                        "content": f"You are {APP_NAME}, an expert assistant for Startup India policies and procedures."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.1,
                top_p=0.9
            )
            
            response_text = response.choices[0].message.content.strip()
            
            return {
                "text": response_text,
                "sources": self._extract_sources(retrieved_docs),
                "confidence_breakdown": {
                    "retrieval_confidence": "high",
                    "llm_response": "generated"
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating LLM response: {e}")
            # Fallback to basic response
            return {
                "text": self._generate_basic_response(query, retrieved_docs),
                "sources": self._extract_sources(retrieved_docs),
                "confidence_breakdown": {
                    "retrieval_confidence": "high",
                    "llm_response": "fallback"
                }
            }

    def _create_prompt(self, query: str, context: str, query_type: str, intent_info: Dict) -> str:
        """Create specialized prompt based on query type"""
        
        base_instruction = f"""You are {APP_NAME}, an expert assistant for Startup India information. 
Use ONLY the provided context to answer the user's question accurately and comprehensively.

Context:
{context}

User Question: {query}

Guidelines:
- Answer based ONLY on the provided context
- Be specific, detailed, and helpful
- Include relevant procedures, requirements, or criteria when applicable
- If the context doesn't fully answer the question, say so clearly
- Format your response with bullet points or numbered lists when appropriate
- Mention specific schemes, programs, or documents when relevant"""

        if query_type == "definition":
            specific_instruction = "\n- Provide a clear definition and explanation\n- Include any relevant categories or types\n- Mention key characteristics or features"
        elif query_type == "process":
            specific_instruction = "\n- Provide step-by-step instructions\n- Include required documents or prerequisites\n- Mention timeframes if available\n- Highlight important deadlines or conditions"
        elif query_type == "criteria":
            specific_instruction = "\n- List all eligibility criteria clearly\n- Organize by categories if applicable\n- Include any exclusions or special conditions\n- Mention verification requirements"
        elif query_type == "list":
            specific_instruction = "\n- Provide a comprehensive list\n- Categorize items if applicable\n- Include brief descriptions for each item\n- Mention any application procedures if relevant"
        else:
            specific_instruction = "\n- Provide a comprehensive answer\n- Include all relevant details from the context"
        
        return base_instruction + specific_instruction + "\n\nAnswer:"

    def _generate_basic_response(self, query: str, retrieved_docs: List[Dict]) -> str:
        """Generate basic response without LLM (fallback)"""
        if not retrieved_docs:
            return self.templates["no_results"]
        
        # Extract key information from retrieved documents
        response_parts = []
        for doc in retrieved_docs[:2]:
            content = doc["content"]
            if len(content) > 300:
                content = content[:300] + "..."
            
            title = doc.get("metadata", {}).get("title", "Document")
            response_parts.append(f"According to {title}: {content}")
        
        return "\n\n".join(response_parts)

    def _extract_sources(self, retrieved_docs: List[Dict]) -> List[Dict]:
        """Extract source information from retrieved documents"""
        sources = []
        for doc in retrieved_docs:
            metadata = doc.get("metadata", {})
            source = {
                "title": metadata.get("title", "Unknown Document"),
                "url": metadata.get("url", ""),
                "topic": metadata.get("topic", "general"),
                "similarity": round(doc.get("similarity", 0.0), 3)
            }
            sources.append(source)
        
        return sources

    def _post_process_response(self, response: Dict, retrieved_docs: List[Dict]) -> Dict:
        """Post-process the response for better formatting"""
        text = response["text"]
        
        # Add source attribution if not present
        if "Source:" not in text and retrieved_docs:
            main_source = retrieved_docs[0].get("metadata", {}).get("url", "")
            if main_source and main_source != "internal://faq":
                text += f"\n\nSource: {main_source}"
        
        # Clean up formatting
        text = re.sub(r'\n{3,}', '\n\n', text)  # Remove excessive line breaks
        text = text.strip()
        
        response["text"] = text
        return response

    def _log_query(
        self, 
        query: str, 
        response: Dict, 
        confidence: float,
        retrieved_docs: List[Dict], 
        processing_time: float, 
        intent_info: Dict,
        user_session: str
    ) -> None:
        """Log query for analytics"""
        try:
            with open(self.query_log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    time.strftime('%Y-%m-%d %H:%M:%S'),
                    query,
                    response["text"][:200] + "..." if len(response["text"]) > 200 else response["text"],
                    confidence,
                    len(retrieved_docs),
                    round(processing_time, 3),
                    intent_info["topic"],
                    confidence < QUERY_CONFIG["min_confidence"],
                    user_session
                ])
        except Exception as e:
            logger.error(f"❌ Error logging query: {e}")

    def _create_error_response(self, message: str) -> Dict:
        """Create standardized error response"""
        return {
            "response": message,
            "confidence": 0.0,
            "sources": [],
            "topic_detected": "error",
            "processing_time": 0.0,
            "retrieved_docs_count": 0
        }

    def get_query_stats(self) -> Dict:
        """Get query statistics"""
        try:
            if not self.query_log_file.exists():
                return {"total_queries": 0}
            
            with open(self.query_log_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                queries = list(reader)
            
            if not queries:
                return {"total_queries": 0}
            
            total_queries = len(queries)
            avg_confidence = sum(float(q.get('confidence', 0)) for q in queries) / total_queries
            avg_processing_time = sum(float(q.get('processing_time', 0)) for q in queries) / total_queries
            
            # Topic distribution
            topics = [q.get('topic_detected', 'unknown') for q in queries]
            topic_counts = {topic: topics.count(topic) for topic in set(topics)}
            
            return {
                "total_queries": total_queries,
                "average_confidence": round(avg_confidence, 3),
                "average_processing_time": round(avg_processing_time, 3),
                "topic_distribution": topic_counts,
                "last_query_time": queries[-1].get('timestamp', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting query stats: {e}")
            return {"error": str(e)}


def main():
    """Test query handler"""
    handler = StartupGuruQueryHandler()
    
    # Test queries
    test_queries = [
        "What is startup eligibility criteria?",
        "How to register a startup?",
        "What funding schemes are available?"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: {query}")
        result = handler.process_query(query, include_debug=True)
        print(f"✅ Response: {result['response'][:100]}...")
        print(f"📊 Confidence: {result['confidence']:.3f}")
        print(f"🎯 Topic: {result['topic_detected']}")


if __name__ == "__main__":
    main() 