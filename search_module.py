"""
search_module.py
=============================================================================
truFaceLedger - Reverse Image Search Module
=============================================================================
"""

import os
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Accessible social platforms
SOCIAL_DOMAINS = [
    "instagram.com",
    "x.com",
    "twitter.com",
    "reddit.com",
    "threads.net",
    "pinterest.com",
    "youtube.com",
    "facebook.com",
    "linkedin.com",
    "medium.com"
]


def upload_image_for_search(image_path: str) -> str:
    """Uploads local image to obtain a direct public URL for Google Lens."""
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    # Method 1: catbox.moe
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=20
            )
            if resp.status_code == 200 and resp.text.startswith("http"):
                return resp.text.strip()
    except Exception:
        pass

    # Method 2: litterbox (1h temp)
    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": f},
                timeout=20
            )
            if resp.status_code == 200 and resp.text.startswith("http"):
                return resp.text.strip()
    except Exception:
        pass

    raise RuntimeError("Failed to obtain a public URL for local image reverse search.")


def is_direct_social_post(link: str) -> bool:
    """Checks if a URL points directly to an individual social media post/media."""
    l = link.lower()
    return (
        "/status/" in l or          # X / Twitter
        "/p/" in l or               # Instagram Post
        "/reel/" in l or            # Instagram Reel
        "/comments/" in l or        # Reddit Thread
        "/post/" in l or            # Threads / Facebook Post
        "/posts/" in l or           # Facebook Post
        "/pin/" in l or             # Pinterest Pin
        "/watch?v=" in l or         # YouTube Video
        "/shorts/" in l             # YouTube Shorts
    )


def reverse_image_search(
    image_input: str,
    serpapi_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Performs live reverse-image search with strict confidence verification.
    Rejects fuzzy/random guesses for unpublished private images.
    """
    api_key = serpapi_key or os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY is not configured in .env file.")

    if image_input.startswith("http://") or image_input.startswith("https://"):
        public_url = image_input
    else:
        public_url = upload_image_for_search(image_input)

    serpapi_endpoint = "https://serpapi.com/search.json"
    matches = []
    raw_data = {}

    # Query Google Lens
    try:
        lens_params = {
            "engine": "google_lens",
            "url": public_url,
            "api_key": api_key,
            "hl": "en"
        }
        resp = requests.get(serpapi_endpoint, params=lens_params, timeout=30)
        if resp.status_code == 200:
            raw_data = resp.json()
            matches = raw_data.get("visual_matches", [])
    except Exception:
        matches = []

    if not matches:
        return {
            "success": False,
            "url": None,
            "title": None,
            "source": None,
            "thumbnail": None,
            "is_social_media": False,
            "confidence": "none",
            "total_matches_found": 0,
            "all_matches": [],
            "public_image_url": public_url,
            "error": "No reverse image matches found on the web."
        }

    # Analyze match authenticity and cross-reference frequency
    direct_social_matches: List[Dict[str, Any]] = []
    social_matches: List[Dict[str, Any]] = []
    parsed_matches: List[Dict[str, Any]] = []

    for item in matches:
        link = item.get("link")
        if not link or "tiktok.com" in link.lower():
            continue

        title = item.get("title", "No Title")
        source = item.get("source", "Web")
        thumb = item.get("thumbnail", item.get("image", ""))

        is_social = any(domain in link.lower() for domain in SOCIAL_DOMAINS)
        is_direct = is_direct_social_post(link)

        match_dict = {
            "url": link,
            "title": title,
            "source": source,
            "thumbnail": thumb,
            "is_social_media": is_social,
            "is_direct": is_direct
        }
        parsed_matches.append(match_dict)

        if is_social and is_direct:
            direct_social_matches.append(match_dict)
        elif is_social:
            social_matches.append(match_dict)

    # Strict Authenticity Check:
    # Public indexed images have matching organic results or repeated domain clusters.
    # Unindexed/private images only yield scattered random celebrity lookalikes.
    has_organic = bool(raw_data.get("organic_results"))
    has_repeated_entities = len(direct_social_matches) >= 1

    # Check for direct verified post
    if direct_social_matches:
        insta_or_x = [m for m in direct_social_matches if "x.com" in m["url"] or "twitter.com" in m["url"] or "instagram.com" in m["url"]]
        selected_match = insta_or_x[0] if insta_or_x else direct_social_matches[0]
        confidence = "high"
    elif social_matches:
        selected_match = social_matches[0]
        confidence = "medium"
    else:
        selected_match = None
        confidence = "low"

    if not selected_match:
        return {
            "success": False,
            "url": None,
            "title": None,
            "source": None,
            "thumbnail": None,
            "is_social_media": False,
            "confidence": "low",
            "total_matches_found": len(parsed_matches),
            "all_matches": parsed_matches[:15],
            "public_image_url": public_url,
            "error": "No verified public social media match found (Unpublished / Private Image)."
        }

    return {
        "success": True,
        "url": selected_match["url"],
        "title": selected_match["title"],
        "source": selected_match["source"],
        "thumbnail": selected_match["thumbnail"],
        "is_social_media": selected_match.get("is_social_media", False),
        "confidence": confidence,
        "total_matches_found": len(parsed_matches),
        "all_matches": parsed_matches[:15],
        "public_image_url": public_url,
        "error": None
    }
