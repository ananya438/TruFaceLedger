# truFaceLedger

> **Tamper-evident Face ID & Live Social Reverse-Search anchored to the Polygon Blockchain.**  
> *Submission for Hackathon Goa 2026 — Task #3: Face ID + Blockchain Verification*

---

## Overview

**truFaceLedger** is an end-to-end Python pipeline that establishes an immutable, cryptographic chain of custody for facial media and its origin on the web:

1. **Face Identification:** Detects faces and extracts **InsightFace ArcFace 512-d** deep biometric embeddings and SHA-256 digests.
2. **Live Web/Social Search:** Performs a genuine reverse-image search via **SerpApi Google Lens** to identify matching public posts on X, Instagram, Facebook, and Reddit.
3. **Blockchain Anchor:** Encodes the cryptographic proof (face hash, image hash, post URL, timestamp) into calldata on the **Polygon Amoy Testnet (Chain ID 80002)**.
4. **On-Chain Verification:** Queries the mined transaction directly from the Polygon node, recomputes the cryptographic hash, and confirms a **100% match** (`STATUS: VERIFIED`).

---

## Pipeline Architecture

```
[ Input Image ]
       │
       ▼
[ 1. Face Identification ]   ──► InsightFace ArcFace (512-d Deep Biometrics + SHA-256)
       │
       ▼
[ 2. Live Reverse Search ]   ──► SerpApi Google Lens (Finds genuine matching post URL)
       │
       ▼
[ 3. Blockchain Writing ]    ──► Web3.py EIP-1559 Transaction to Polygon Amoy
       │
       ▼
[ 4. On-Chain Verification ] ──► Extracts calldata from block, recomputes hash ──► VERIFIED
```

---

## Quickstart

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials (`.env`)
Copy `.env.example` to `.env` and fill in your keys:
```env
SERPAPI_KEY=your_serpapi_key_here
ALCHEMY_RPC_URL=https://polygon-amoy.g.alchemy.com/v2/your_key
PRIVATE_KEY=your_private_key_here
WALLET_ADDRESS=0xYourWalletAddressHere
```

### 3. Run Pipeline
```bash
python main.py samples/ronaldo.jpg
```

---

## Live Example Output

```text
             truFaceLedger :: Face ID + Blockchain Verification
         Polygon Amoy Testnet (Chain ID 80002) | HH Goa 2026 (Task #3)

   Input Photo:   samples/ronaldo.jpg
   Absolute Path: C:\Users\nannu\Desktop\TruFaceLedger\samples\ronaldo.jpg

[Step 1] Detecting face and generating cryptographic encodings...
   1. Face Detected:       1 face(s)
   2. Detection Engine:    insightface_arcface_512d
   3. Vector Dimension:    512-d (ArcFace Deep Biometric)
   4. Image SHA-256 Hash:  5e0eb8786ebac6b55c91f2ca9819283ed4bc012bfb83d657642a1b988ae0ffb0
   5. Face Encoding Hash:  2fe9d2af0ae3985d2f36b2de49a64795c3d916e517b9631c3945b7518179c617
   6. Face Crop Saved:     crops\face_crop_ronaldo.jpg

[Step 2] Matching social media post (SerpApi Google Lens)...
   1. Performing live reverse image search with Google Lens...
   2. Match Status:        Found
   3. Source Platform:     x.com
   4. Matched URL:         https://x.com/TeamCRonaldo/status/2018367138268852254
   5. Post Title:          TCR. on X: "Hey @grok , show me how Cristiano Ronaldo would ...
   6. Similar Matches:     57

[Step 3] Hashing match data & writing to Polygon Amoy testnet...
   1. Record Hash (Digest): 385102dba1f27120da7b636cde1d73facc661b1ed2a41344f31a776443b73f73
   2. Transaction Status:   Submitted & Confirmed
   3. Transaction Hash:     0xfb82a7d678aab82bcf651b7ec61241abbd37af19c3580fea0ca2889dbfc7973f
   4. Block Number:         #46925346
   5. Gas Used:             48200 units
   6. Explorer Link:        https://amoy.polygonscan.com/tx/0xfb82a7d678aab82bcf651b7ec61241abbd37af19c3580fea0ca2889dbfc7973f

[Step 4] Re-verifying on-chain record...
   1. Querying Polygon Amoy node for transaction input data...
   2. Transaction data retrieved from Polygon Amoy.
   3. Stored Record Hash:     385102dba1f27120da7b636cde1d73facc661b1ed2a41344f31a776443b73f73
   4. Recomputed Record Hash: 385102dba1f27120da7b636cde1d73facc661b1ed2a41344f31a776443b73f73
   5. Integrity Check:        100% MATCH
   6. On-Chain Matched URL:   https://x.com/TeamCRonaldo/status/2018367138268852254
   7. On-Chain Image Hash:    5e0eb8786ebac6b55c91f2ca9819283ed4bc012bfb83d657642a1b988ae0ffb0
   8. On-Chain Face Hash:     2fe9d2af0ae3985d2f36b2de49a64795c3d916e517b9631c3945b7518179c617
   9. On-Chain Timestamp:     2026-09-07T01:16:26.935107+00:00

                       STATUS: VERIFIED
 Tamper-evident face verification record is immutably anchored on-chain.
```

---

## Project Structure

```
truFaceLedger/
├── main.py                 # Pipeline CLI orchestrator
├── face_module.py          # InsightFace ArcFace 512-d biometric extractor
├── search_module.py        # Live SerpApi Google Lens reverse search
├── blockchain_module.py    # Web3 Polygon Amoy transaction writer & on-chain reader
├── requirements.txt        # Package dependencies
├── .env.example            # Environment template
└── README.md               # Documentation
```

---

## Tech Stack & Specifications

* **Language:** Python 3.10+
* **Face Recognition:** InsightFace ArcFace (`buffalo_l`, 512-dimensional normalized vectors)
* **Search Engine:** SerpApi (Google Lens API with multi-host image fallback)
* **Blockchain Network:** Polygon Amoy Testnet (Chain ID `80002`)
* **RPC & Web3:** Alchemy Polygon Node + Web3.py (EIP-1559 Signed Calldata)
* **Block Explorer:** [PolygonScan Amoy](https://amoy.polygonscan.com/)
