"""
API routes for source material management.

Handles URL fetching for source material ingestion.
"""

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from app.services.url_fetcher import fetch_and_store_urls
from app.utils.logger import get_logger
from app.utils.safe_url import SafeUrlError, assert_public_http_url

logger = get_logger(__name__)

sources_bp = Blueprint("sources", __name__, url_prefix="/api/sources")


@sources_bp.route("/fetch", methods=["POST"])
def fetch_urls():
    """
    Fetch content from URLs and store as source material files.
    
    Request body:
        {
            "urls": ["https://example.com/article", "https://..."],
            "simulation_id": "optional_sim_id"  # For future use with persistent sims
        }
    
    Response:
        {
            "success": true,
            "files": [
                {"name": "article.txt", "size": 12345, "source_url": "https://..."}
            ],
            "errors": [
                {"url": "https://...", "error": "Failed to fetch: ..."}
            ]
        }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "error": "JSON body required"}), 400
        
        urls = data.get("urls", [])
        
        # Validate input
        if not urls or not isinstance(urls, list):
            return jsonify({
                "success": False,
                "error": "urls array required"
            }), 400
        
        # Limit to 10 URLs per request
        if len(urls) > 10:
            return jsonify({
                "success": False,
                "error": "Maximum 10 URLs per request"
            }), 400
        
        # Validate URL format and refuse anything that points back into the
        # deployment's own network (SSRF). Rejected at the boundary so a bad URL
        # never reaches the fetcher; url_fetcher re-checks for defence in depth.
        valid_urls = []
        for url in urls:
            url = str(url).strip()
            try:
                assert_public_http_url(url)
            except SafeUrlError as exc:
                return jsonify({
                    "success": False,
                    "error": f"Invalid URL: {exc}"
                }), 400
            valid_urls.append(url)
        
        if not valid_urls:
            return jsonify({
                "success": False,
                "error": "No valid URLs provided"
            }), 400
        
        # Get upload directory from config
        upload_dir = current_app.config.get("UPLOAD_FOLDER")
        if not upload_dir:
            logger.error("UPLOAD_FOLDER not configured")
            return jsonify({
                "success": False,
                "error": "Server configuration error"
            }), 500
        
        # Create uploads directory if needed
        from pathlib import Path
        upload_path = Path(upload_dir)
        upload_path.mkdir(parents=True, exist_ok=True)
        
        # Fetch URLs
        logger.info(f"Fetching {len(valid_urls)} URLs")
        results = fetch_and_store_urls(valid_urls, upload_path)
        
        # Log summary
        success_count = len(results["files"])
        error_count = len(results["errors"])
        logger.info(f"URL fetch complete: {success_count} succeeded, {error_count} failed")
        
        return jsonify({
            "success": True,
            "files": results["files"],
            "errors": results["errors"]
        }), 200
    
    except BadRequest as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.exception("Error in fetch_urls endpoint")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500
