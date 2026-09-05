import os
import io
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv
import cv2
import numpy as np
from PIL import Image

from face_module import extract_encoding_from_array, compute_vector_similarity

load_dotenv()

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
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

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
    l = link.lower()
    return (
        "/status/" in l or
        "/p/" in l or
        "/reel/" in l or
        "/comments/" in l or
        "/post/" in l or
        "/posts/" in l or
        "/pin/" in l or
        "/watch?v=" in l or
        "/shorts/" in l
    )


def download_and_extract_encoding(image_url: str) -> Optional[List[float]]:
    try:
        r = requests.get(image_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200:
            img = Image.open(io.BytesIO(r.content)).convert("RGB")
            arr = np.array(img)
            return extract_encoding_from_array(arr)
    except Exception:
        pass
    return None


def reverse_image_search(
    image_input: str,
    input_encoding: Optional[List[float]] = None,
    serpapi_key: Optional[str] = None
) -> Dict[str, Any]:
    api_key = serpapi_key or os.getenv("SERPAPI_KEY")
    if not api_key:
        raise ValueError("SERPAPI_KEY is not configured in .env file.")

    if image_input.startswith("http://") or image_input.startswith("https://"):
        public_url = image_input
    else:
        public_url = upload_image_for_search(image_input)

    serpapi_endpoint = "https://serpapi.com/search.json"
    matches = []

    try:
        lens_params = {
            "engine": "google_lens",
            "url": public_url,
            "api_key": api_key,
            "hl": "en"
        }
        resp = requests.get(serpapi_endpoint, params=lens_params, timeout=30)
        if resp.status_code == 200:
            matches = resp.json().get("visual_matches", [])
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
            "similarity_score": 0.0,
            "total_matches_found": 0,
            "all_matches": [],
            "public_image_url": public_url,
            "error": "No reverse image matches found on the web."
        }

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

    candidate_list = direct_social_matches or social_matches or parsed_matches
    if not candidate_list:
        return {
            "success": False,
            "url": None,
            "title": None,
            "source": None,
            "thumbnail": None,
            "is_social_media": False,
            "similarity_score": 0.0,
            "total_matches_found": 0,
            "all_matches": [],
            "public_image_url": public_url,
            "error": "No verified social matches discovered."
        }

    best_match = None
    best_similarity = 0.0

    if input_encoding:
        for candidate in candidate_list[:10]:
            thumb_url = candidate.get("thumbnail")
            if thumb_url:
                cand_encoding = download_and_extract_encoding(thumb_url)
                if cand_encoding:
                    sim = compute_vector_similarity(input_encoding, cand_encoding)
                    if sim > best_similarity:
                        best_similarity = sim
                        best_match = candidate
                        if sim >= 0.88:
                            break

    if not best_match:
        best_match = candidate_list[0]

    SIMILARITY_THRESHOLD = 0.80
    if input_encoding and best_similarity < SIMILARITY_THRESHOLD:
        return {
            "success": False,
            "url": None,
            "title": None,
            "source": None,
            "thumbnail": None,
            "is_social_media": False,
            "similarity_score": best_similarity,
            "total_matches_found": len(parsed_matches),
            "all_matches": parsed_matches[:15],
            "public_image_url": public_url,
            "error": f"Visual similarity ({best_similarity * 100:.1f}%) is below confidence threshold ({SIMILARITY_THRESHOLD * 100:.0f}%). Image is private or unpublished."
        }

    return {
        "success": True,
        "url": best_match["url"],
        "title": best_match["title"],
        "source": best_match["source"],
        "thumbnail": best_match["thumbnail"],
        "is_social_media": best_match.get("is_social_media", False),
        "similarity_score": best_similarity,
        "total_matches_found": len(parsed_matches),
        "all_matches": parsed_matches[:15],
        "public_image_url": public_url,
        "error": None
    }
