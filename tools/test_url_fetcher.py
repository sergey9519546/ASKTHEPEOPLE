"""Quick test of URL fetcher service."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.url_fetcher import fetch_url_content

# Test with a simple, reliable URL
test_url = "https://example.com"

print(f"Testing URL fetcher with: {test_url}")
print("=" * 60)

result = fetch_url_content(test_url)

print(f"Success: {result['success']}")
print(f"Method: {result.get('method', 'N/A')}")
print(f"Size: {result.get('size', 0)} bytes")

if result['success']:
    content = result['content']
    print(f"Content preview (first 200 chars):")
    print(content[:200])
else:
    print(f"Error: {result.get('error', 'Unknown error')}")

print("=" * 60)
print("Test complete")
