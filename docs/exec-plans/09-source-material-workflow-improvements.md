---
title: "Source Material Workflow Improvements"
status: "Proposed"
version: "1.0.0"
owner: "askthepeople-architect"
created: "2026-08-03"
last_reviewed: "2026-08-03"
---

# Source Material Workflow Improvements

## Problem Statement

Current workflow requires users to manually gather and upload files before running any simulation. This creates friction:

1. **Manual download-upload cycle** — users find URLs, download files, then upload them
2. **Source material is required** — can't run exploration with just a decision/scenario (frontend/src/views/Home.vue:404 blocks submission if `files.value.length === 0`)
3. **No URL ingestion** — no way to directly provide article/doc links
4. **"Just ask the question" not possible** — even for quick exploratory runs

User request: *"all they have to do is ask the questions or scenario, and if they have any research files or data they can upload"*

## Proposed Three-Tier Solution

### Tier 1: Decision-Only Mode (Quickest Win)

**Goal:** Make source files optional so users can run simulations with just a decision/scenario.

**Changes:**
- `frontend/src/views/Home.vue:404` — remove `files.value.length > 0` from `canSubmit` guard
- Update help text: "Source material optional — upload files or paste URLs to ground personas in specific context"
- Backend already handles zero-file case (generates personas from decision text via OASIS)
- Add note in results: "This exploration used only the decision text. Upload sources for context-grounded personas."

**Value:** Immediate. Users can "just ask" without gathering materials first.

**Effort:** 1-2 hours (frontend conditional + UX copy).

### Tier 2: URL Ingestion (High Value)

**Goal:** Let users paste URLs (articles, PDFs, docs) and have backend fetch them automatically.

**Changes:**

**Frontend (`Home.vue`):**
- Add textarea for URLs (one per line) below file upload area
- Display fetched URLs in same list as uploaded files (with loading state)
- Max 10 URLs (aligns with MAX_SOURCE_FILES=10)

**Backend (new route `POST /api/sources/fetch`):**
- Accept `{"urls": ["https://...", "https://..."]}`
- Use Firecrawl skill (available in skill list) or requests + BeautifulSoup
- Extract text content, store as `.txt` or `.md` in uploads/
- Return file metadata same as upload endpoint
- Rate limit: 10 URLs/request, 30 seconds timeout per URL

**Integration points:**
- `setPendingUpload()` accepts both `files` array and `fetchedUrls` array
- Backend `prepare_simulation_task` treats fetched content same as uploaded files

**Value:** High. Eliminates download-upload friction for web sources (articles, docs, research).

**Effort:** 4-6 hours (backend endpoint + Firecrawl integration + frontend UI).

### Tier 3: Auto-Research Mode (Nice-to-Have)

**Goal:** "Find sources for me" — system searches web based on decision text and suggests relevant articles.

**Changes:**
- Button: "Find relevant sources" (disabled while loading)
- Backend calls web search API (Brave, Perplexity, or Exa)
- Returns top 10 results with title, URL, snippet
- User checks which to include
- System fetches checked URLs (Tier 2 flow)

**Value:** Medium. Useful when user doesn't know what sources exist. Lower priority than Tier 1-2.

**Effort:** 6-8 hours (search API integration + selection UI + async job handling).

## Implementation Priority

**Phase 1 (ship now):** Tier 1 — decision-only mode
- Unblocks "just ask the question" use case
- Minimal code change, high user impact
- 1-2 hours

**Phase 2 (next sprint):** Tier 2 — URL ingestion
- High value, moderate effort
- Addresses 80% of "manual upload" friction
- 4-6 hours

**Phase 3 (backlog):** Tier 3 — auto-research
- Nice-to-have, not blocking
- Consider after validating Tier 1-2 usage
- 6-8 hours

## Technical Considerations

### Tier 1: Decision-Only Mode

**Backend impact:** None. `backend/app/services/oasis_profile_generator.py` already generates personas from decision text when no source material provided (OASIS's default behavior).

**Frontend changes:**
```javascript
// Home.vue line 401-409
const canSubmit = computed(
  () =>
    formData.value.simulationRequirement.trim().length >= 12 &&
    usePolicyAcknowledged.value &&
    // REMOVED: files.value.length > 0
);
```

**UX copy updates:**
- "Source material (optional)" heading
- Help text: "Upload files or paste URLs to ground personas in specific context. Or skip to explore with just your decision."
- Results disclaimer when `human_respondent_count === 0 && source_file_count === 0`: "⚠️ No source material — personas generated from decision text only. Upload sources for context-grounded exploration."

### Tier 2: URL Ingestion

**New backend route:**
```python
# backend/app/api/sources.py
from flask import Blueprint, request, jsonify
from app.services.url_fetcher import fetch_and_store_urls

sources_bp = Blueprint("sources", __name__, url_prefix="/api/sources")

@sources_bp.route("/fetch", methods=["POST"])
def fetch_urls():
    """
    Accept URLs, fetch content, store as files.
    Returns file metadata compatible with upload endpoint.
    """
    data = request.get_json()
    urls = data.get("urls", [])
    
    if not urls or not isinstance(urls, list):
        return jsonify({"success": False, "error": "urls array required"}), 400
    
    if len(urls) > 10:
        return jsonify({"success": False, "error": "max 10 URLs"}), 400
    
    # Async job or sync with timeout
    results = fetch_and_store_urls(urls, timeout=30)
    
    return jsonify({
        "success": True,
        "files": results["files"],
        "errors": results["errors"]  # URLs that failed to fetch
    }), 200
```

**Firecrawl integration:**
Use existing Firecrawl skill from skill list or direct API:
```python
# backend/app/services/url_fetcher.py
import requests
from pathlib import Path

def fetch_and_store_urls(urls, timeout=30):
    results = {"files": [], "errors": []}
    
    for url in urls:
        try:
            # Option 1: Firecrawl API (if key available)
            # Option 2: requests + BeautifulSoup fallback
            response = requests.get(url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 ..."
            })
            response.raise_for_status()
            
            # Extract text (simple: .text; better: BeautifulSoup)
            content = extract_text(response.content)
            
            # Store as .txt file
            filename = sanitize_filename(url) + ".txt"
            filepath = UPLOAD_DIR / filename
            filepath.write_text(content, encoding="utf-8")
            
            results["files"].append({
                "name": filename,
                "size": len(content),
                "source_url": url
            })
        except Exception as e:
            results["errors"].append({"url": url, "error": str(e)})
    
    return results
```

**Frontend:**
```vue
<!-- Home.vue: add URL input section -->
<div class="url-section">
  <label for="source-urls">Or paste URLs (one per line)</label>
  <textarea
    id="source-urls"
    v-model="urlInput"
    placeholder="https://example.com/article&#10;https://example.com/research.pdf"
    rows="4"
  ></textarea>
  <button @click="fetchUrls" :disabled="!urlInput.trim() || fetchingUrls">
    {{ fetchingUrls ? "Fetching..." : "Fetch URLs" }}
  </button>
</div>

<script>
const urlInput = ref("");
const fetchingUrls = ref(false);

async function fetchUrls() {
  const urls = urlInput.value
    .split("\n")
    .map(u => u.trim())
    .filter(u => u.startsWith("http"));
  
  if (urls.length === 0) return;
  
  fetchingUrls.value = true;
  try {
    const response = await api.post("/sources/fetch", { urls });
    // Add fetched files to files.value array
    files.value.push(...response.data.files);
    urlInput.value = ""; // Clear input
    
    if (response.data.errors.length > 0) {
      // Show toast with failed URLs
    }
  } catch (error) {
    // Handle error
  } finally {
    fetchingUrls.value = false;
  }
}
</script>
```

### Tier 3: Auto-Research

**Backend:**
- New route: `POST /api/sources/research` with `{"query": "decision text"}`
- Calls Brave Search API or Perplexity or Exa
- Returns: `[{title, url, snippet}, ...]`

**Frontend:**
- "Find relevant sources" button
- Modal with search results checkboxes
- "Fetch selected" → calls Tier 2 URL fetch endpoint

**Defer to backlog** — validate Tier 1-2 usage first.

## Gate Alignment

**Gate 0 (Immediate correctness):** Not affected.

**Gate 1 (Typed API boundary):** URL fetch endpoint should use Pydantic models for request/response validation.

**Gate 3 (Canonical persistence):** Fetched URLs should be stored with provenance (source URL, fetch timestamp, content hash).

## Success Metrics

**Tier 1:**
- % of simulations with zero source files (target: >30%)
- User feedback: "faster to start" sentiment

**Tier 2:**
- % of simulations using URL ingestion vs file upload
- Average URLs per simulation
- URL fetch failure rate (target: <10%)

**Tier 3:**
- % of users clicking "Find relevant sources"
- % of auto-research results included in simulation

## References

- **Current file upload:** `frontend/src/views/Home.vue:401-409` (canSubmit guard)
- **OASIS persona generation:** `backend/app/services/oasis_profile_generator.py`
- **Firecrawl skills:** Available in skill list (`firecrawl-scrape`, `firecrawl-download`)
- **Product Truth Contract:** `docs/product/PRODUCT_TRUTH_CONTRACT.md` — ensure "0 human respondents" disclaimer remains regardless of source mode
