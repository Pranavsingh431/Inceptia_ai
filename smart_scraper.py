"""
StartupGuru Smart Scraper
HARDCORE web scraping with full anti-detection and CloudFlare bypass
"""

import asyncio
import json
import time
import random
from pathlib import Path
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import re

import fitz  # PyMuPDF
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from playwright_stealth import stealth_async
from bs4 import BeautifulSoup
import requests
from loguru import logger
import html2text

from config import (
    BASE_URL, SCRAPING_CONFIG, SCRAPING_URLS, PATHS, 
    APP_NAME, get_config
)


class StartupGuruScraper:
    """Production-quality scraper with hardcore anti-detection"""
    
    def __init__(self):
        self.config = get_config()
        self.scraped_urls: Set[str] = set()
        self.scraped_content: List[Dict] = []
        self.pdf_cache: Dict[str, str] = {}
        
        # Setup paths
        self.output_dir = Path(PATHS["scraped_content"])
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # Real browser user agents (constantly updated)
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        ]
        
        # Content filters (to exclude navigation, footer, etc.)
        self.exclude_selectors = [
            'nav', 'footer', 'header', '.nav', '.navbar', '.footer',
            '.header', '.menu', '.sidebar', '.breadcrumb', '.pagination',
            '.social-media', '.contact-info', '.advertisement', '.ads',
            '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
            'script', 'style', 'meta', 'link', 'noscript'
        ]
        
        # Important content selectors
        self.content_selectors = [
            'main', '.main-content', '.content', '.page-content',
            'article', '.article', '.text-content', '.description',
            '.scheme-details', '.eligibility', '.benefits', '.process',
            '.faq', '.guidelines', '.criteria', '.requirements',
            '.container', '.wrapper', '.inner-content'
        ]

    async def scrape_all(self) -> List[Dict]:
        """Main scraping orchestrator with hardcore anti-detection"""
        logger.info(f"🚀 Starting {APP_NAME} HARDCORE scraping with anti-detection")
        
        async with async_playwright() as p:
            # Launch browser with stealth mode
            browser = await p.chromium.launch(
                headless=False,  # Start visible to mimic real user
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--disable-default-apps",
                    "--disable-extensions",
                    "--disable-plugins",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-component-extensions-with-background-pages",
                    "--no-default-browser-check",
                    "--autoplay-policy=user-gesture-required",
                    "--disable-background-downloads",
                    "--disable-add-to-shelf",
                    "--disable-client-side-phishing-detection",
                    "--disable-datasaver-prompt",
                    "--disable-default-apps",
                    "--disable-domain-reliability",
                    "--no-pings",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor"
                ]
            )
            
            try:
                # Create stealth context
                context = await self._create_stealth_context(browser)
                
                # Phase 1: Scrape main pages with hardcore methods
                await self._scrape_main_pages_hardcore(context)
                
                # Phase 2: Discover and scrape additional pages
                await self._discover_additional_pages(context)
                
                # Phase 3: Process PDFs (if any found)
                await self._process_pdfs()
                
                # Phase 4: Clean and structure content
                self._clean_and_structure_content()
                
                # Phase 5: Save results
                await self._save_results()
                
                logger.success(f"✅ HARDCORE Scraping completed! {len(self.scraped_content)} documents processed")
                return self.scraped_content
                
            finally:
                await browser.close()

    async def _create_stealth_context(self, browser: Browser) -> BrowserContext:
        """Create a stealth browser context that bypasses detection"""
        user_agent = random.choice(self.user_agents)
        
        context = await browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False,
            locale='en-US',
            timezone_id='America/New_York',
            permissions=['geolocation'],
            geolocation={'latitude': 40.7128, 'longitude': -74.0060},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Cache-Control': 'max-age=0',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"macOS"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Connection': 'keep-alive'
            }
        )
        
        return context

    async def _scrape_main_pages_hardcore(self, context: BrowserContext) -> None:
        """Scrape all predefined important pages with hardcore techniques"""
        logger.info("📄 HARDCORE Scraping main pages...")
        
        for i, url in enumerate(SCRAPING_URLS):
            try:
                logger.info(f"🎯 Attempting HARDCORE scrape {i+1}/{len(SCRAPING_URLS)}: {url}")
                
                # Random delay between requests (2-8 seconds)
                if i > 0:
                    delay = random.uniform(2.0, 8.0)
                    logger.info(f"⏱️ Strategic delay: {delay:.2f}s")
                    await asyncio.sleep(delay)
                
                success = await self._scrape_single_page_hardcore(context, url)
                
                if success:
                    logger.success(f"✅ Successfully scraped: {url}")
                else:
                    logger.warning(f"⚠️ Partial/failed scrape: {url}")
                    
            except Exception as e:
                logger.error(f"💥 Failed to scrape {url}: {e}")

    async def _scrape_single_page_hardcore(self, context: BrowserContext, url: str) -> bool:
        """Hardcore single page scraping with multiple fallback strategies"""
        if url in self.scraped_urls:
            return False
            
        self.scraped_urls.add(url)
        page = await context.new_page()
        
        try:
            # Apply stealth mode
            await stealth_async(page)
            
            # Set random viewport
            width = random.randint(1200, 1920)
            height = random.randint(800, 1080)
            await page.set_viewport_size({"width": width, "height": height})
            
            # Navigate with realistic behavior
            await page.goto(url, timeout=30000, wait_until='domcontentloaded')
            
            # Wait for page to fully load + random delay
            await asyncio.sleep(random.uniform(2.0, 5.0))
            
            # Check if we hit CloudFlare or similar protection
            page_content = await page.content()
            if self._is_blocked_content(page_content):
                logger.warning(f"🛡️ Detected anti-bot protection, trying bypass...")
                success = await self._bypass_protection(page, url)
                if not success:
                    return False
            
            # Simulate human behavior
            await self._simulate_human_behavior(page)
            
            # Wait for dynamic content
            await page.wait_for_load_state('networkidle', timeout=10000)
            
            # Handle dynamic content (dropdowns, etc.)
            await self._handle_dynamic_content(page)
            
            # Extract content with multiple strategies
            content = await self._extract_page_content_hardcore(page, url)
            
            if content and content.get("content", "").strip():
                self.scraped_content.append(content)
                return True
                
        except Exception as e:
            logger.error(f"💥 Hardcore scraping error for {url}: {e}")
            
        finally:
            await page.close()
            
        return False

    def _is_blocked_content(self, content: str) -> bool:
        """Detect if page is showing anti-bot protection"""
        blocked_indicators = [
            "cloudflare",
            "access denied",
            "checking your browser",
            "enable javascript and cookies",
            "request could not be satisfied",
            "ray id:",
            "security check",
            "bot protection",
            "ddos protection",
            "challenge-form"
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in blocked_indicators)

    async def _bypass_protection(self, page: Page, url: str) -> bool:
        """Attempt to bypass CloudFlare and other protections"""
        logger.info("🔧 Attempting protection bypass...")
        
        try:
            # Strategy 1: Wait for CloudFlare challenge to complete
            logger.info("⏳ Waiting for challenge completion...")
            await asyncio.sleep(10)  # Wait for CloudFlare to process
            
            # Strategy 2: Look for and click challenge elements
            challenge_selectors = [
                'input[type="checkbox"]',
                '#challenge-form button',
                '.challenge-form button',
                'button[type="submit"]'
            ]
            
            for selector in challenge_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements:
                    try:
                        await element.click()
                        await asyncio.sleep(3)
                        logger.info(f"🔘 Clicked challenge element: {selector}")
                    except:
                        continue
            
            # Strategy 3: Wait for redirect or content change
            await page.wait_for_load_state('networkidle', timeout=15000)
            
            # Strategy 4: Check if we're now on the actual page
            current_content = await page.content()
            if not self._is_blocked_content(current_content):
                logger.success("✅ Protection bypass successful!")
                return True
            
            # Strategy 5: Try refreshing the page
            logger.info("🔄 Trying page refresh...")
            await page.reload(wait_until='networkidle')
            await asyncio.sleep(5)
            
            final_content = await page.content()
            if not self._is_blocked_content(final_content):
                logger.success("✅ Protection bypass successful after refresh!")
                return True
                
        except Exception as e:
            logger.error(f"💥 Protection bypass failed: {e}")
        
        logger.error("❌ Could not bypass protection")
        return False

    async def _simulate_human_behavior(self, page: Page) -> None:
        """Simulate realistic human browsing behavior"""
        try:
            # Random mouse movements
            await page.mouse.move(random.randint(100, 800), random.randint(100, 600))
            await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Random scroll
            scroll_amount = random.randint(200, 800)
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(random.uniform(1.0, 2.0))
            
            # Another scroll
            await page.evaluate(f"window.scrollBy(0, {random.randint(-200, 400)})")
            await asyncio.sleep(random.uniform(0.5, 1.0))
            
        except Exception as e:
            logger.warning(f"Human behavior simulation failed: {e}")

    async def _handle_dynamic_content(self, page: Page) -> None:
        """Handle dropdowns, collapsible sections, and dynamic content"""
        try:
            # Click on common expandable elements
            expandable_selectors = [
                'button[aria-expanded="false"]',
                '.accordion-toggle',
                '.collapsible-header',
                '.dropdown-toggle',
                '[role="button"][aria-expanded="false"]',
                '.expand-button',
                '.show-more',
                '.read-more',
                '.view-more'
            ]
            
            for selector in expandable_selectors:
                elements = await page.query_selector_all(selector)
                for element in elements[:8]:  # Expand up to 8 elements
                    try:
                        await element.click()
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                    except:
                        continue
                        
            # Handle FAQ sections specifically
            faq_selectors = [
                '.faq-item', '.question', '.accordion-item',
                '.faq-question', '.qa-item', '.help-item'
            ]
            
            for selector in faq_selectors:
                elements = await page.query_selector_all(selector)
                for faq in elements[:12]:  # Process up to 12 FAQ items
                    try:
                        await faq.click()
                        await asyncio.sleep(random.uniform(0.3, 0.8))
                    except:
                        continue
                        
        except Exception as e:
            logger.warning(f"Error handling dynamic content: {e}")

    async def _extract_page_content_hardcore(self, page: Page, url: str) -> Dict:
        """Extract and clean content from a page with multiple strategies"""
        try:
            # Get page title
            title = await page.title()
            
            # Strategy 1: Direct text extraction
            main_text = ""
            try:
                main_text = await page.evaluate("""
                    () => {
                        // Remove scripts, styles, and other unwanted elements
                        const unwanted = document.querySelectorAll('script, style, nav, footer, header, .nav, .navbar, .footer, .header, .menu, .sidebar, .breadcrumb, .pagination');
                        unwanted.forEach(el => el.remove());
                        
                        // Get main content
                        const main = document.querySelector('main') || document.querySelector('.main-content') || document.querySelector('.content') || document.body;
                        return main ? main.innerText : document.body.innerText;
                    }
                """)
            except:
                pass
            
            # Strategy 2: HTML parsing with BeautifulSoup
            if not main_text or len(main_text) < 100:
                try:
                    html_content = await page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Remove unwanted elements
                    for selector in self.exclude_selectors:
                        for element in soup.select(selector):
                            element.decompose()
                    
                    # Extract main content
                    for selector in self.content_selectors:
                        content_elements = soup.select(selector)
                        if content_elements:
                            main_text = " ".join([elem.get_text(strip=True) for elem in content_elements])
                            break
                    
                    # Fallback to body content
                    if not main_text:
                        body = soup.find('body')
                        if body:
                            main_text = body.get_text(strip=True)
                            
                except Exception as e:
                    logger.warning(f"HTML parsing failed: {e}")
            
            # Strategy 3: Use html2text as last resort
            if not main_text or len(main_text) < 50:
                try:
                    html_content = await page.content()
                    h = html2text.HTML2Text()
                    h.ignore_links = True
                    h.ignore_images = True
                    main_text = h.handle(html_content)
                except:
                    main_text = "Content extraction failed"
            
            # Clean content
            cleaned_content = self._clean_text_content(main_text)
            
            # Extract metadata
            metadata = await self._extract_metadata_hardcore(page, url)
            
            # Create content document
            content_doc = {
                "id": f"startup_guru_{len(self.scraped_content)}",
                "title": title or "Untitled",
                "url": url,
                "content": cleaned_content,
                "content_type": "webpage",
                "scraped_at": time.time(),
                "word_count": len(cleaned_content.split()),
                "metadata": metadata
            }
            
            return content_doc
            
        except Exception as e:
            logger.error(f"Content extraction failed for {url}: {e}")
            return {}

    def _clean_text_content(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n+', '\n', text)
        
        # Remove special characters but keep essential punctuation
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\'\"]+', ' ', text)
        
        # Remove common navigation text
        nav_phrases = [
            "skip to main content", "skip to content", "main navigation",
            "breadcrumb", "you are here", "current page", "search this site",
            "back to top", "scroll to top", "print this page", "share this page"
        ]
        
        for phrase in nav_phrases:
            text = re.sub(phrase, '', text, flags=re.IGNORECASE)
        
        # Clean up spacing again
        text = ' '.join(text.split())
        
        return text.strip()

    async def _extract_metadata_hardcore(self, page: Page, url: str) -> Dict:
        """Extract comprehensive metadata from page"""
        metadata = {"url": url}
        
        try:
            # Extract meta tags
            meta_data = await page.evaluate("""
                () => {
                    const meta = {};
                    document.querySelectorAll('meta').forEach(tag => {
                        const name = tag.getAttribute('name') || tag.getAttribute('property');
                        const content = tag.getAttribute('content');
                        if (name && content) {
                            meta[name] = content;
                        }
                    });
                    
                    // Extract structured data
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    const structured_data = [];
                    scripts.forEach(script => {
                        try {
                            structured_data.push(JSON.parse(script.textContent));
                        } catch (e) {}
                    });
                    
                    return {meta, structured_data};
                }
            """)
            
            metadata.update(meta_data.get("meta", {}))
            if meta_data.get("structured_data"):
                metadata["structured_data"] = meta_data["structured_data"]
                
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")
        
        return metadata

    async def _discover_additional_pages(self, context: BrowserContext) -> None:
        """Discover and scrape additional important pages"""
        if len(self.scraped_content) == 0:
            logger.warning("No initial content scraped, skipping discovery phase")
            return
            
        logger.info("🔍 Discovering additional pages...")
        
        # For now, focus on the main pages since we're having issues
        # We can expand this later once basic scraping works
        pass

    async def _process_pdfs(self) -> None:
        """Process any PDF documents found"""
        logger.info("📄 Processing PDFs...")
        # Implementation for PDF processing if any PDFs are discovered
        pass

    def _clean_and_structure_content(self) -> None:
        """Clean and structure all scraped content"""
        logger.info("🧹 Cleaning and structuring content...")
        
        # Remove duplicates based on content similarity
        unique_content = []
        for content in self.scraped_content:
            is_duplicate = False
            for existing in unique_content:
                if self._content_similarity(content.get("content", ""), existing.get("content", "")) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_content.append(content)
        
        self.scraped_content = unique_content
        logger.info(f"✅ Kept {len(self.scraped_content)} unique documents")

    def _content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two content strings"""
        if not content1 or not content2:
            return 0.0
        
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0

    async def _save_results(self) -> None:
        """Save all scraped content to files"""
        logger.info("💾 Saving results...")
        
        # Save combined JSON
        output_file = self.output_dir / "scraped_content.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.scraped_content, f, indent=2, ensure_ascii=False)
        
        # Save individual files
        for i, content in enumerate(self.scraped_content):
            filename = self._sanitize_filename(f"{content.get('title', 'untitled')}_{i}")
            individual_file = self.output_dir / f"{filename}.json"
            
            with open(individual_file, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=2, ensure_ascii=False)
        
        logger.success(f"✅ Saved {len(self.scraped_content)} files to {self.output_dir}")

    def _sanitize_filename(self, title: str) -> str:
        """Sanitize title for use as filename"""
        # Remove invalid characters and limit length
        sanitized = re.sub(r'[^\w\s-]', '', title)
        sanitized = re.sub(r'[\s_-]+', '_', sanitized)
        return sanitized[:50].strip('_')


async def main():
    """Test the hardcore scraper"""
    scraper = StartupGuruScraper()
    results = await scraper.scrape_all()
    
    logger.info(f"🎉 Scraping completed with {len(results)} documents")
    for doc in results:
        logger.info(f"📄 {doc.get('title', 'Untitled')} - {doc.get('word_count', 0)} words")


if __name__ == "__main__":
    asyncio.run(main()) 