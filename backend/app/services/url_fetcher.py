"""
URL fetching service for source material ingestion.

Tiered strategy:
1. Premium tier (if API keys configured): Firecrawl (best) → Jina Pro
2. Free tier: Jina Reader API (no auth required)
3. Fallback: Custom urllib + regex extractor

Fetches content from URLs and stores them as text files in the uploads directory.
"""

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

from app.utils.logger import get_logger

logger = get_logger(__name__)

# Environment variables for premium services
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY")
JINA_API_KEY = os.environ.get("JINA_API_KEY")  # For Jina AI Pro features

# Maximum content size to fetch (10 MB)
MAX_CONTENT_SIZE = 10 * 1024 * 1024

# Timeout for URL requests
REQUEST_TIMEOUT = 30  # seconds
FIRECRAWL_TIMEOUT = 60  # Firecrawl can take longer for complex pages

# User agent to avoid bot detection
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Jina Reader API endpoint (free, no auth required)
JINA_READER_URL = "https://r.jina.ai/"


def fetch_with_firecrawl(url: str) -> Dict[str, any]:
    """
    Fetch URL using Firecrawl API (premium, best for LLM pipelines).
    
    Firecrawl extracts clean markdown optimized for LLM consumption.
    Requires FIRECRAWL_API_KEY environment variable.
    
    API: https://docs.firecrawl.dev/api-reference/endpoint/scrape
    Cost: ~$0.83 per 1000 pages (starter plan $83/mo for 100k pages)
    """
    if not FIRECRAWL_API_KEY:
        return {"success": False, "error": "Firecrawl API key not configured"}
    
    try:
        # Firecrawl v1 scrape endpoint
        api_url = "https://api.firecrawl.dev/v1/scrape"
        
        payload = {
            "url": url,
            "formats": ["markdown"],  # Get clean markdown output
            "onlyMainContent": True,  # Skip headers/footers/ads
        }
        
        headers = {
            "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
            "Content-Type": "application/json"
        }
        
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=FIRECRAWL_TIMEOUT) as response:
            result = json.loads(response.read())
            
            if not result.get("success"):
                return {"success": False, "error": result.get("error", "Firecrawl failed")}
            
            markdown = result.get("data", {}).get("markdown", "")
            
            if not markdown:
                return {"success": False, "error": "No content extracted"}
            
            return {
                "success": True,
                "content": markdown,
                "size": len(markdown),
                "method": "firecrawl"
            }
    
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore") if e.fp else ""
        logger.warning(f"Firecrawl HTTP {e.code}: {error_body[:200]}")
        return {"success": False, "error": f"Firecrawl HTTP {e.code}"}
    except Exception as e:
        logger.warning(f"Firecrawl error for {url}: {e}")
        return {"success": False, "error": f"Firecrawl failed: {str(e)}"}


def fetch_with_jina_reader(url: str) -> Dict[str, any]:
    """
    Fetch URL using Jina Reader API (free, no auth required).
    
    Jina Reader converts any URL to clean markdown by prepending r.jina.ai/
    Free tier: unlimited requests, no auth
    Pro tier: Enhanced features with JINA_API_KEY
    
    API: https://jina.ai/reader
    Cost: FREE (Pro features: ~$0.05/M tokens after 10M free)
    """
    try:
        # Prepend Jina Reader endpoint to the target URL
        jina_url = f"{JINA_READER_URL}{url}"
        
        headers = {"User-Agent": USER_AGENT}
        
        # If Jina API key is available, use it for pro features
        if JINA_API_KEY:
            headers["Authorization"] = f"Bearer {JINA_API_KEY}"
        
        req = urllib.request.Request(jina_url, headers=headers)
        
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            content = response.read().decode("utf-8", errors="ignore")
            
            if not content or len(content) < 50:
                return {"success": False, "error": "No content returned"}
            
            return {
                "success": True,
                "content": content,
                "size": len(content),
                "method": "jina_reader"
            }
    
    except urllib.error.HTTPError as e:
        logger.warning(f"Jina Reader HTTP {e.code} for {url}")
        return {"success": False, "error": f"Jina Reader HTTP {e.code}"}
    except Exception as e:
        logger.warning(f"Jina Reader error for {url}: {e}")
        return {"success": False, "error": f"Jina Reader failed: {str(e)}"}


def extract_text_from_html(html_bytes: bytes) -> str:
    """
    Extract readable text from HTML content.
    
    Simple extraction: removes script/style tags, then strips HTML tags.
    Fallback for when premium services aren't available.
    """
    try:
        html = html_bytes.decode("utf-8", errors="ignore")
    except Exception:
        # Fall back to latin-1 if utf-8 fails
        html = html_bytes.decode("latin-1", errors="ignore")
    
    # Remove script and style tags with their content
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", " ", html)
    
    # Decode HTML entities
    text = text.replace("&nbsp;", " ")
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    
    return text


def fetch_with_custom_extractor(url: str) -> Dict[str, any]:
    """
    Fallback: fetch URL directly and extract text with custom regex.
    
    Simple extraction for when premium services fail or are unavailable.
    Works best for simple HTML pages and plain text content.
    """
    try:
        # Validate URL
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return {"success": False, "error": "Only HTTP/HTTPS URLs supported"}
        
        # Create request with headers to avoid bot detection
        req = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,text/*"}
        )
        
        # Fetch with timeout
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            content_length = response.headers.get("Content-Length")
            
            # Check size before reading
            if content_length and int(content_length) > MAX_CONTENT_SIZE:
                return {
                    "success": False,
                    "error": f"Content too large ({int(content_length)} bytes, max {MAX_CONTENT_SIZE})"
                }
            
            # Read content
            raw_content = response.read()
            
            if len(raw_content) > MAX_CONTENT_SIZE:
                return {
                    "success": False,
                    "error": f"Content too large ({len(raw_content)} bytes)"
                }
            
            # Extract text based on content type
            if "html" in content_type:
                text_content = extract_text_from_html(raw_content)
            elif "text" in content_type or "json" in content_type:
                text_content = raw_content.decode("utf-8", errors="ignore")
            else:
                # Try to decode as text anyway
                try:
                    text_content = raw_content.decode("utf-8", errors="ignore")
                except Exception:
                    return {
                        "success": False,
                        "error": f"Unsupported content type: {content_type}"
                    }
            
            return {
                "success": True,
                "content": text_content,
                "size": len(text_content),
                "method": "custom_extractor"
            }
    
    except urllib.error.HTTPError as e:
        return {"success": False, "error": f"HTTP {e.code}: {e.reason}"}
    except urllib.error.URLError as e:
        return {"success": False, "error": f"URL error: {e.reason}"}
    except TimeoutError:
        return {"success": False, "error": "Request timed out"}
    except Exception as e:
        logger.exception(f"Unexpected error fetching {url}")
        return {"success": False, "error": f"Failed to fetch: {str(e)}"}


def fetch_url_content(url: str) -> Dict[str, any]:
    """
    Fetch content from a single URL using tiered strategy.
    
    Strategy:
    1. If FIRECRAWL_API_KEY: try Firecrawl (best quality)
    2. Try Jina Reader (free, no auth)
    3. Fall back to custom extractor
    
    Returns:
        Dict with keys: success (bool), content (str), error (str), size (int), method (str)
    """
    # Tier 1: Firecrawl (if API key available)
    if FIRECRAWL_API_KEY:
        logger.info(f"Trying Firecrawl for {url}")
        result = fetch_with_firecrawl(url)
        if result["success"]:
            logger.info(f"✓ Firecrawl succeeded for {url} ({result['size']} bytes)")
            return result
        logger.info(f"Firecrawl failed: {result.get('error')}, trying Jina Reader")
    
    # Tier 2: Jina Reader (free, always available)
    logger.info(f"Trying Jina Reader for {url}")
    result = fetch_with_jina_reader(url)
    if result["success"]:
        logger.info(f"✓ Jina Reader succeeded for {url} ({result['size']} bytes)")
        return result
    logger.info(f"Jina Reader failed: {result.get('error')}, falling back to custom extractor")
    
    # Tier 3: Custom extractor (last resort)
    logger.info(f"Trying custom extractor for {url}")
    result = fetch_with_custom_extractor(url)
    if result["success"]:
        logger.info(f"✓ Custom extractor succeeded for {url} ({result['size']} bytes)")
    else:
        logger.warning(f"✗ All methods failed for {url}: {result.get('error')}")
    return result


def sanitize_filename(url: str) -> str:
    """
    Generate a safe filename from a URL.
    
    Uses the last path segment or domain name, removes special characters.
    """
    parsed = urlparse(url)
    # Try to use the last meaningful path segment
    path_parts = [p for p in parsed.path.split("/") if p and p != "index.html"]
    
    if path_parts:
        base = path_parts[-1]
        # Remove file extension if present
        base = re.sub(r"\.[a-zA-Z0-9]+$", "", base)
    else:
        # Use domain name
        base = parsed.netloc.replace("www.", "")
    
    # Remove special characters, keep alphanumeric and dashes
    safe = re.sub(r"[^a-zA-Z0-9\-_]", "_", base)
    # Collapse multiple underscores
    safe = re.sub(r"_+", "_", safe)
    # Trim to reasonable length
    safe = safe[:100]
    
    return safe or "fetched_content"


def fetch_and_store_urls(urls: List[str], upload_dir: Path) -> Dict[str, any]:
    """
    Fetch multiple URLs and store their content as text files.
    
    Args:
        urls: List of URLs to fetch
        upload_dir: Directory to store fetched content
    
    Returns:
        Dict with keys:
            - files: List of successfully fetched files [{name, size, source_url, method}]
            - errors: List of failures [{url, error}]
    """
    results = {"files": [], "errors": []}
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
        
        logger.info(f"Fetching URL: {url}")
        fetch_result = fetch_url_content(url)
        
        if not fetch_result["success"]:
            logger.warning(f"Failed to fetch {url}: {fetch_result['error']}")
            results["errors"].append({"url": url, "error": fetch_result["error"]})
            continue
        
        # Generate filename
        base_name = sanitize_filename(url)
        filename = f"{base_name}.txt"
        
        # Ensure unique filename
        counter = 1
        filepath = upload_dir / filename
        while filepath.exists():
            filename = f"{base_name}_{counter}.txt"
            filepath = upload_dir / filename
            counter += 1
        
        # Write content
        try:
            filepath.write_text(fetch_result["content"], encoding="utf-8")
            logger.info(f"Stored {url} as {filename} ({fetch_result['size']} bytes)")
            
            results["files"].append({
                "name": filename,
                "size": fetch_result["size"],
                "source_url": url,
                "method": fetch_result.get("method", "unknown")
            })
        except Exception as e:
            logger.exception(f"Failed to write {filename}")
            results["errors"].append({"url": url, "error": f"Failed to save: {str(e)}"})
    
    return results
