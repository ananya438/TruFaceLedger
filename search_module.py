import os
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

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


def get_serpapi_keys() -> List[str]:
    raw = os.getenv("SERPAPI_KEY", "")
    return [k.strip() for k in raw.split(",") if k.strip()]


def upload_image_for_search(image_path: str) -> str:
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://catbox.moe/user/api.php",
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f},
                timeout=15
            )
            if resp.status_code == 200 and resp.text.startswith("http"):
                return resp.text.strip()
    except Exception:
        pass

    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://uguu.se/upload.php",
                files={"files[]": f},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                files = data.get("files", [])
                if files and files[0].get("url"):
                    return files[0]["url"]
    except Exception:
        pass

    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://tmpfiles.org/api/v1/upload",
                files={"file": f},
                timeout=15
            )
            if resp.status_code == 200:
                data = resp.json()
                raw_url = data.get("data", {}).get("url", "")
                if raw_url:
                    return raw_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
    except Exception:
        pass

    try:
        with open(image_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": f},
                timeout=15
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
        "/pin/" in l
    )


def verify_candidate_biometric(thumb_url: str, target_encoding: Optional[List[float]]) -> float:
    if not thumb_url or not target_encoding:
        return 0.0
    try:
        import cv2
        import numpy as np
        from face_module import extract_encoding_from_array, compute_vector_similarity
        resp = requests.get(thumb_url, timeout=6)
        if resp.status_code == 200:
            arr = cv2.imdecode(np.frombuffer(resp.content, np.uint8), cv2.IMREAD_COLOR)
            if arr is not None:
                cand_vec = extract_encoding_from_array(arr)
                if cand_vec:
                    return compute_vector_similarity(target_encoding, cand_vec)
    except Exception:
        pass
    return 0.0


def reverse_image_search(
    image_input: str,
    serpapi_key: Optional[str] = None,
    target_encoding: Optional[List[float]] = None
) -> Dict[str, Any]:
    api_keys = [serpapi_key] if serpapi_key else get_serpapi_keys()
    if not api_keys:
        raise ValueError("SERPAPI_KEY is not configured in .env file.")

    if image_input.startswith("http://") or image_input.startswith("https://"):
        public_url = image_input
    else:
        public_url = upload_image_for_search(image_input)

    serpapi_endpoint = "https://serpapi.com/search.json"
    matches = []
    last_error = "No reverse image matches found on the web."

    for key in api_keys:
        try:
            lens_params = {
                "engine": "google_lens",
                "url": public_url,
                "api_key": key,
                "hl": "en"
            }
            resp = requests.get(serpapi_endpoint, params=lens_params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if "error" not in data:
                    matches = data.get("visual_matches", [])
                    if matches:
                        break
            elif resp.status_code in [401, 429]:
                continue
        except Exception as e:
            last_error = str(e)
            continue

    if not matches:
        return {
            "success": False,
            "url": None,
            "title": None,
            "source": None,
            "thumbnail": None,
            "is_social_media": False,
            "total_matches_found": 0,
            "all_matches": [],
            "public_image_url": public_url,
            "error": last_error
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

    candidates = direct_social_matches + social_matches + parsed_matches
    selected_match = None

    for cand in candidates:
        if target_encoding and cand.get("thumbnail"):
            sim = verify_candidate_biometric(cand["thumbnail"], target_encoding)
            if sim < 0.40:
                continue
        selected_match = cand
        break

    if not selected_match:
        return {
            "success": False,
            "url": None,
            "title": None,
            "source": None,
            "thumbnail": None,
            "is_social_media": False,
            "total_matches_found": len(parsed_matches),
            "all_matches": parsed_matches[:15],
            "public_image_url": public_url,
            "error": "No verified social media post found matching this person's face."
        }

    return {
        "success": True,
        "url": selected_match["url"],
        "title": selected_match["title"],
        "source": selected_match["source"],
        "thumbnail": selected_match["thumbnail"],
        "is_social_media": selected_match.get("is_social_media", False),
        "total_matches_found": len(parsed_matches),
        "all_matches": parsed_matches[:15],
        "public_image_url": public_url,
        "error": None
    }
