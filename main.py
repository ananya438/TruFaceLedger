"""
main.py
truFaceLedger - End-to-End Face ID & Blockchain Verification Pipeline
Hackathon: Hackathon Goa 2026 (Task #3: Face ID + Blockchain Verification)

Pipeline Flow:
  1. Input Photo -> Detect & Encode Face -> Save Face Crop
  2. Live Reverse Image Search via SerpApi Google Lens -> 2-Way Biometric Verification
  3. Hash Data (Image + Face Vector + Match URL) -> Write Record to Polygon Amoy Testnet
  4. Fetch On-Chain Data -> Recompute Cryptographic Hash -> Confirm Match (STATUS: VERIFIED)

Usage:
  python main.py path/to/photo.jpg
"""

import sys
import os
import time
from pathlib import Path
from dotenv import load_dotenv

# Import local pipeline modules
from face_module import detect_and_encode_face
from search_module import reverse_image_search
from blockchain_module import write_record, read_record

# Load secrets and settings from .env file
load_dotenv()


def print_banner():
    """Prints a styled CLI banner for clean screen recording."""
    banner = """
             truFaceLedger :: Face ID + Blockchain Verification
         Polygon Amoy Testnet (Chain ID 80002) | HH Goa 2026 (Task #3)
"""
    print(banner)


def run_pipeline(image_path: str):
    """
    Executes the 4-step pipeline end-to-end with clear formatted console output.
    """
    print_banner()

    # Verify input image exists
    if not os.path.exists(image_path):
        print(f"ERROR: Target image file not found: {image_path}")
        print("Please provide a valid path to an image file (e.g. python main.py samples/ronaldo.jpg)")
        sys.exit(1)

    print(f"   Input Photo:   {image_path}")
    print(f"   Absolute Path: {os.path.abspath(image_path)}\n")

    # -------------------------------------------------------------------------
    # STEP 1: Detect & Encode Face
    # -------------------------------------------------------------------------
    print("[Step 1] Detecting face and generating cryptographic encodings...")
    try:
        face_result = detect_and_encode_face(image_path, crop_output_dir="crops")
    except Exception as e:
        print(f"ERROR during face detection: {str(e)}")
        sys.exit(1)

    if not face_result["success"]:
        print(f"Face Detection Failed: {face_result.get('error', 'No face found.')}")
        print("Tip: Provide an image with a clearer portrait view of the person.")
        sys.exit(1)

    print(f"   1. Face Detected:       {face_result['face_count']} face(s)")
    print(f"   2. Detection Engine:    {face_result['engine']}")
    print(f"   3. Image SHA-256 Hash:  {face_result['image_hash']}")
    print(f"   4. Face Encoding Hash:  {face_result['face_encoding_hash']}")
    if face_result.get("crop_path"):
        print(f"   5. Face Crop Saved:     {face_result['crop_path']}")

    # -------------------------------------------------------------------------
    # STEP 2: Reverse-Image Search with 2-Way Biometric Verification
    # -------------------------------------------------------------------------
    print("\n[Step 2] Matching social media post (SerpApi Google Lens)...")
    
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key or serpapi_key.startswith("your_"):
        print("ERROR: SERPAPI_KEY is missing or unconfigured in .env file.")
        print("Please configure your SerpApi key in .env to enable reverse image searches.")
        sys.exit(1)

    search_target = image_path
    face_encoding = face_result.get("face_encoding")
    print(f"   1. Performing live reverse image search with Google Lens...")
    
    try:
        search_result = reverse_image_search(search_target, input_encoding=face_encoding)
    except Exception as e:
        print(f"ERROR: Reverse image search failed: {str(e)}")
        sys.exit(1)

    if not search_result["success"] or not search_result["url"]:
        if face_result.get("crop_path"):
            print("   • Retrying search with cropped face...")
            search_result = reverse_image_search(face_result["crop_path"], input_encoding=face_encoding)

    # If visual similarity threshold was not met (Private/Unpublished Photo)
    if not search_result["success"] or not search_result["url"]:
        print("   2. Match Status:        REJECTED (No Authentic Public Match)")
        print(f"   3. Visual Similarity:   {search_result.get('similarity_score', 0.0) * 100:.1f}%")
        print("\n                       STATUS: UNVERIFIED (REJECTED)")
        print(f" Notice: {search_result.get('error', 'Visual similarity below verification threshold.')}")
        print(" Reason: Image is private or unpublished. Skipping blockchain write to prevent false records.\n")
        sys.exit(0)

    print(f"   2. Match Status:        Found (Confidence: {search_result.get('similarity_score', 1.0) * 100:.1f}%)")
    print(f"   3. Source Platform:     {search_result['source']}")
    print(f"   4. Matched URL:         {search_result['url']}")
    if search_result.get("title"):
        print(f"   5. Post Title:          {search_result['title'][:80]}")
    print(f"   6. Similar Matches:     {search_result['total_matches_found']}")

    # -------------------------------------------------------------------------
    # STEP 3: Hashing & Writing to Polygon Amoy Testnet
    # -------------------------------------------------------------------------
    print("\n[Step 3] Hashing match data & writing to Polygon Amoy testnet...")
    
    rpc_url = os.getenv("ALCHEMY_RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")
    if not rpc_url or not private_key:
        print("ERROR: ALCHEMY_RPC_URL or PRIVATE_KEY is missing in .env file.")
        sys.exit(1)

    match_metadata = {
        "title": search_result.get("title"),
        "source": search_result.get("source"),
        "is_social_media": search_result.get("is_social_media"),
        "similarity_score": search_result.get("similarity_score"),
        "thumbnail": search_result.get("thumbnail"),
        "search_engine": "SerpApi Google Lens"
    }

    try:
        tx_result = write_record(
            image_hash=face_result["image_hash"],
            face_encoding_hash=face_result["face_encoding_hash"],
            match_url=search_result["url"],
            metadata=match_metadata
        )
    except Exception as e:
        print(f"ERROR: Blockchain transaction failed: {str(e)}")
        sys.exit(1)

    print(f"   1. Record Hash (Digest): {tx_result['record_hash']}")
    print(f"   2. Transaction Status:   Submitted & Confirmed")
    print(f"   3. Transaction Hash:     {tx_result['tx_hash']}")
    print(f"   4. Block Number:         #{tx_result['block_number']}")
    print(f"   5. Gas Used:             {tx_result['gas_used']} units")
    print(f"   6. Explorer Link:        {tx_result['explorer_url']}")

    # -------------------------------------------------------------------------
    # STEP 4: Re-Verifying On-Chain Record
    # -------------------------------------------------------------------------
    print("\n[Step 4] Re-verifying on-chain record...")
    print("   1. Querying Polygon Amoy node for transaction input data...")
    
    time.sleep(2)

    try:
        verify_result = read_record(tx_result["tx_hash"])
    except Exception as e:
        print(f"ERROR: Verification failed during blockchain lookup: {str(e)}")
        sys.exit(1)

    if not verify_result["verified"]:
        print("\n                       STATUS: UNVERIFIED (FAILED)")
        print(f" ERROR: {verify_result.get('error', 'Cryptographic hash mismatch.')}\n")
        sys.exit(1)

    on_chain_record = verify_result["record"]
    print("   2. Transaction data retrieved from Polygon Amoy.")
    print(f"   3. Stored Record Hash:     {verify_result['stored_hash']}")
    print(f"   4. Recomputed Record Hash: {verify_result['recomputed_hash']}")
    print(f"   5. Integrity Check:        100% MATCH")
    print(f"   6. On-Chain Matched URL:   {on_chain_record.get('match_url')}")
    print(f"   7. On-Chain Image Hash:    {on_chain_record.get('image_hash')}")
    print(f"   8. On-Chain Face Hash:     {on_chain_record.get('face_encoding_hash')}")
    print(f"   9. On-Chain Timestamp:     {on_chain_record.get('timestamp')}")

    print("\n                       STATUS: VERIFIED")
    print(" Tamper-evident face verification record is immutably anchored on-chain.\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <path/to/photo.jpg>")
        print("\nExample:")
        print("  python main.py samples/ronaldo.jpg")
        sys.exit(1)

    input_img = sys.argv[1]
    run_pipeline(input_img)


if __name__ == "__main__":
    main()
