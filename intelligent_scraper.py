#!/usr/bin/env python3
"""
Intelligent Startup India Scraper
Comprehensive, ethical web scraper that actually works and gets real content
"""

import requests
import time
import json
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
from typing import List, Dict, Set, Optional
from loguru import logger
import hashlib
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

@dataclass
class ScrapedDocument:
    """Document structure for scraped content"""
    url: str
    title: str
    content: str
    section: str
    topic: str
    last_updated: str
    word_count: int
    content_hash: str
    source_type: str = "scraped"

class IntelligentStartupScraper:
    """Comprehensive scraper for Startup India website"""
    
    def __init__(self):
        self.base_url = "https://www.startupindia.gov.in"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        self.scraped_urls: Set[str] = set()
        self.documents: List[ScrapedDocument] = []
        self.output_dir = Path("./data/scraped")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Comprehensive URL patterns to scrape
        self.target_patterns = [
            # Main information pages
            "/content/sih/en/startup_recognition.html",
            "/content/sih/en/benefits.html", 
            "/content/sih/en/startup-india-initiative.html",
            "/content/sih/en/about-startup-india-initiative.html",
            
            # Funding and schemes
            "/content/sih/en/fund-of-funds.html",
            "/content/sih/en/seed-fund-scheme.html",
            "/content/sih/en/government-schemes.html",
            "/content/sih/en/startup-schemes.html",
            "/content/sih/en/incubator-framework.html",
            
            # Registration and processes
            "/content/sih/en/ipp.html",
            "/content/sih/en/public_procurement.html",
            "/content/sih/en/reources.html",
            "/content/sih/en/reources/startup_toolkit.html",
            
            # Special categories
            "/content/sih/en/women_entrepreneurs.html",
            "/content/sih/en/startup-india-learning-programme.html",
            
            # Resources and knowledge base
            "/content/sih/en/reources/knowledge-bank.html",
            "/content/sih/en/bloglist.html",
            
            # Recent initiatives
            "/national-startup-day/",
            "/content/sih/en/international.html",
        ]
        
        # Additional discovery URLs
        self.discovery_urls = [
            f"{self.base_url}/content/sih/en.html",
            f"{self.base_url}/sitemap.xml",
        ]
        
    def scrape_comprehensive_content(self) -> int:
        """Main scraping method that gets comprehensive content"""
        logger.info("🚀 Starting comprehensive Startup India content scraping...")
        
        # Step 1: Discover additional URLs
        discovered_urls = self._discover_urls()
        all_urls = set(self.target_patterns + discovered_urls)
        
        logger.info(f"📋 Found {len(all_urls)} URLs to scrape")
        
        # Step 2: Scrape content with threading for speed
        self._scrape_urls_threaded(all_urls)
        
        # Step 3: Save all documents
        total_saved = self._save_documents()
        
        logger.success(f"✅ Scraping completed! Saved {total_saved} documents with comprehensive content")
        return total_saved
    
    def _discover_urls(self) -> List[str]:
        """Discover additional URLs from sitemap and main pages"""
        discovered = []
        
        # Try to get sitemap
        try:
            sitemap_url = f"{self.base_url}/sitemap.xml"
            response = self._make_request(sitemap_url)
            if response and response.status_code == 200:
                urls = self._extract_urls_from_sitemap(response.text)
                discovered.extend(urls)
                logger.info(f"📄 Found {len(urls)} URLs from sitemap")
        except Exception as e:
            logger.warning(f"⚠️ Could not fetch sitemap: {e}")
        
        # Discover from main page
        try:
            main_response = self._make_request(f"{self.base_url}/content/sih/en.html")
            if main_response and main_response.status_code == 200:
                soup = BeautifulSoup(main_response.text, 'html.parser')
                links = self._extract_relevant_links(soup)
                discovered.extend(links)
                logger.info(f"🔗 Found {len(links)} additional URLs from main page")
        except Exception as e:
            logger.warning(f"⚠️ Could not scrape main page: {e}")
        
        return list(set(discovered))
    
    def _extract_urls_from_sitemap(self, sitemap_content: str) -> List[str]:
        """Extract URLs from sitemap XML"""
        urls = []
        try:
            soup = BeautifulSoup(sitemap_content, 'xml')
            for url_tag in soup.find_all('url'):
                loc = url_tag.find('loc')
                if loc and 'startupindia.gov.in' in loc.text:
                    # Filter for relevant content
                    url_path = loc.text.replace(self.base_url, '')
                    if any(keyword in url_path.lower() for keyword in 
                          ['startup', 'scheme', 'fund', 'benefit', 'registration', 'entrepreneur', 'innovation']):
                        urls.append(url_path)
        except Exception as e:
            logger.error(f"❌ Error parsing sitemap: {e}")
        
        return urls[:50]  # Limit to prevent overload
    
    def _extract_relevant_links(self, soup: BeautifulSoup) -> List[str]:
        """Extract relevant links from a page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('/'):
                # Filter for relevant content
                if any(keyword in href.lower() for keyword in 
                      ['startup', 'scheme', 'fund', 'benefit', 'registration', 'entrepreneur', 'innovation', 'incubator']):
                    links.append(href)
        
        return list(set(links))[:30]  # Limit to prevent overload
    
    def _scrape_urls_threaded(self, urls: Set[str]):
        """Scrape URLs using threading for better performance"""
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all scraping tasks
            future_to_url = {
                executor.submit(self._scrape_single_url, url): url 
                for url in urls
            }
            
            # Process completed tasks
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        self.documents.append(result)
                        logger.info(f"✅ Scraped: {url} ({len(result.content)} chars)")
                    else:
                        logger.warning(f"⚠️ No content from: {url}")
                except Exception as e:
                    logger.error(f"❌ Error scraping {url}: {e}")
                
                # Rate limiting
                time.sleep(random.uniform(0.5, 1.5))
    
    def _scrape_single_url(self, url_path: str) -> Optional[ScrapedDocument]:
        """Scrape a single URL and extract meaningful content"""
        if url_path in self.scraped_urls:
            return None
        
        full_url = urljoin(self.base_url, url_path)
        self.scraped_urls.add(url_path)
        
        response = self._make_request(full_url)
        if not response or response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract content
        title = self._extract_title(soup, url_path)
        content = self._extract_main_content(soup)
        
        if not content or len(content.strip()) < 100:
            return None
        
        # Determine topic and section
        topic = self._determine_topic(url_path, title, content)
        section = self._determine_section(url_path)
        
        # Create document
        content_hash = hashlib.md5(content.encode()).hexdigest()
        word_count = len(content.split())
        
        return ScrapedDocument(
            url=full_url,
            title=title,
            content=content,
            section=section,
            topic=topic,
            last_updated=time.strftime("%Y-%m-%d"),
            word_count=word_count,
            content_hash=content_hash
        )
    
    def _make_request(self, url: str) -> Optional[requests.Response]:
        """Make HTTP request with proper error handling"""
        try:
            response = self.session.get(url, timeout=30)
            return response
        except Exception as e:
            logger.warning(f"⚠️ Request failed for {url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup, url_path: str) -> str:
        """Extract page title"""
        # Try multiple title sources
        title_selectors = [
            'h1',
            '.page-title',
            '.main-title', 
            'title',
            '.breadcrumb-item:last-child'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                return element.get_text(strip=True)
        
        # Fallback to URL-based title
        return url_path.split('/')[-1].replace('-', ' ').replace('.html', '').title()
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from page"""
        # Remove unwanted elements
        for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', '.advertisement']):
            unwanted.decompose()
        
        # Try multiple content selectors
        content_selectors = [
            '.main-content',
            '.content-area',
            '.page-content',
            'main',
            '.container .row',
            'body'
        ]
        
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                # Extract text content
                paragraphs = []
                
                # Get all paragraphs, divs with text, and lists
                for tag in element.find_all(['p', 'div', 'li', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    text = tag.get_text(strip=True)
                    if text and len(text) > 20:  # Only meaningful content
                        paragraphs.append(text)
                
                content = '\n\n'.join(paragraphs)
                
                if len(content) > 200:  # Ensure we have substantial content
                    return self._clean_content(content)
        
        return ""
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\n\s*\n', '\n\n', content)
        
        # Remove common website artifacts
        content = re.sub(r'Click here.*?more', '', content, flags=re.IGNORECASE)
        content = re.sub(r'Read more.*?$', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*Home\s*>', '', content, flags=re.MULTILINE)
        
        return content.strip()
    
    def _determine_topic(self, url_path: str, title: str, content: str) -> str:
        """Determine document topic based on URL, title, and content"""
        text_to_analyze = f"{url_path} {title} {content[:500]}".lower()
        
        if any(word in text_to_analyze for word in ['eligibility', 'criteria', 'eligible', 'qualify']):
            return 'eligibility'
        elif any(word in text_to_analyze for word in ['fund', 'financial', 'investment', 'money', 'capital', 'seed']):
            return 'funding'
        elif any(word in text_to_analyze for word in ['register', 'registration', 'apply', 'application', 'dpiit']):
            return 'registration'
        elif any(word in text_to_analyze for word in ['benefit', 'tax', 'exemption', 'incentive']):
            return 'tax_benefits'
        elif any(word in text_to_analyze for word in ['document', 'requirement', 'paperwork', 'certificate']):
            return 'documents'
        elif any(word in text_to_analyze for word in ['woman', 'women', 'female']):
            return 'women_entrepreneurs'
        elif any(word in text_to_analyze for word in ['incubator', 'accelerator', 'innovation']):
            return 'incubation'
        else:
            return 'general'
    
    def _determine_section(self, url_path: str) -> str:
        """Determine document section from URL"""
        if 'scheme' in url_path:
            return 'schemes'
        elif 'fund' in url_path:
            return 'funding'
        elif 'benefit' in url_path:
            return 'benefits'
        elif 'recognition' in url_path or 'registration' in url_path:
            return 'registration'
        elif 'resource' in url_path or 'toolkit' in url_path:
            return 'resources'
        elif 'blog' in url_path:
            return 'blogs'
        else:
            return 'main'
    
    def _save_documents(self) -> int:
        """Save all scraped documents to files"""
        if not self.documents:
            logger.warning("⚠️ No documents to save!")
            return 0
        
        saved_count = 0
        
        for doc in self.documents:
            try:
                # Create filename
                safe_title = re.sub(r'[^\w\s-]', '', doc.title).strip()
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                filename = f"{doc.section}_{safe_title}_{doc.content_hash[:8]}.json"
                
                file_path = self.output_dir / filename
                
                # Save document
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(asdict(doc), f, indent=2, ensure_ascii=False)
                
                saved_count += 1
                
            except Exception as e:
                logger.error(f"❌ Error saving document {doc.title}: {e}")
        
        logger.success(f"💾 Saved {saved_count} documents to {self.output_dir}")
        return saved_count

def main():
    """Run the intelligent scraper"""
    scraper = IntelligentStartupScraper()
    total_documents = scraper.scrape_comprehensive_content()
    
    logger.info(f"🎉 Scraping completed! Total documents: {total_documents}")
    
    if total_documents > 0:
        logger.info(f"📁 Documents saved to: {scraper.output_dir}")
        logger.info("✅ Ready for processing into vector database!")
    else:
        logger.error("❌ No documents were scraped. Check the scraper configuration.")

if __name__ == "__main__":
    main() 