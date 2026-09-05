# truFaceLedger 🛡️⛓️

> **Tamper-evident Face ID & Reverse-Image Social Verification anchored to the Polygon Amoy Blockchain.**  
> *Submission for Hackathon Goa 2026 — Task #3: Face ID + Blockchain Verification*

---

## 📌 Overview

**truFaceLedger** is a Python command-line pipeline that establishes an immutable, cryptographic chain of custody for facial media and its origin on the web. 

Given an input photo, **truFaceLedger**:
1. **Detects & encodes** the face and computes cryptographic SHA-256 digests.
2. **Executes a live reverse-image search** via SerpApi (Google Lens API) to discover genuine matching social media posts (Instagram, Twitter/X, Reddit, Facebook, TikTok, etc.).
3. **Anchors a tamper-evident verification record** directly onto the **Polygon Amoy Testnet (Chain ID 80002)** using Web3.py and an Alchemy RPC endpoint.
4. **Re-queries the blockchain**, extracts the raw transaction payload, recomputes the cryptographic hash, and confirms authenticity (`VERIFIED ✅`).

---

## 🚀 4-Step Pipeline Architecture

```
[ Input Photo ]
       │
       ▼
[ 1. Face Detection & Encoding ] ──► Extracts 128-d Vector, Bounding Box & SHA-256 Digests
       │
       ▼
[ 2. Live Reverse Image Search ] ──► SerpApi Google Lens identifies genuine social media post URL
       │
       ▼
[ 3. On-Chain Immutability ]     ──► Packs & signs payload to Polygon Amoy Testnet (Alchemy RPC)
       │
       ▼
[ 4. Blockchain Verification ]   ──► Fetches tx data, verifies hashes match ──► [ VERIFIED ✅ ]
```

---

## 📂 Project Structure

```
truFaceLedger/
├── main.py                 # Master CLI orchestrator with numbered, step-by-step output
├── face_module.py          # Face detection, 128-d feature encoding & face crop extraction
├── search_module.py        # Live reverse-image search (SerpApi Google Lens engine)
├── blockchain_module.py    # Polygon Amoy Web3 writer (EIP-1559) & on-chain verification reader
├── requirements.txt        # Python package dependencies
├── .env.example            # Template for environment variables and secrets
├── .env                    # Local configuration (never committed to git)
├── .gitignore              # Protects secrets, temporary crops, and cache
├── samples/                # Sample portrait images for testing
│   └── ronaldo.jpg
└── README.md               # Project documentation
```

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- **Python 3.10+** (Tested on Python 3.10 – 3.13)
- An active **Alchemy** account with a Polygon Amoy RPC endpoint
- A **SerpApi** API key
- A MetaMask wallet with a small amount of **Polygon Amoy testnet POL** (from [Polygon Faucet](https://faucet.polygon.technology/))

### 2. Clone Repository & Install Dependencies
```bash
# Clone the repository
git clone https://github.com/your-username/truFaceLedger.git
cd truFaceLedger

# Install required dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in your credentials:
```env
# SerpApi API Key
SERPAPI_KEY=your_serpapi_key_here

# Alchemy Polygon Amoy Testnet RPC
ALCHEMY_RPC_URL=https://polygon-amoy.g.alchemy.com/v2/your_alchemy_api_key

# MetaMask Private Key (without 0x prefix or with 0x)
PRIVATE_KEY=your_private_key_here

# Wallet Address
WALLET_ADDRESS=0xYourWalletAddressHere
```

> ⚠️ **Security Warning**: Your `.env` contains your private key and API tokens. Never commit `.env` to GitHub. The included `.gitignore` protects it automatically.

---

## 💻 How to Run

Execute the pipeline by passing any image file:

```bash
python main.py samples/ronaldo.jpg
```

### Example Terminal Output

```text
=============================================================================
             truFaceLedger :: Face ID + Blockchain Verification
         Polygon Amoy Testnet (Chain ID 80002) | HH Goa 2026 (Task #3)
=============================================================================

📸 Input Photo: samples/ronaldo.jpg
   Absolute Path: C:\Users\nannu\Desktop\truFaceLedger\samples\ronaldo.jpg
-----------------------------------------------------------------------------

[Step 1/4] Detecting face and generating cryptographic encodings...
   ✓ Face Detected! (Found 1 face(s))
   ✓ Detection Engine: opencv_haar_cascade (fallback)
   ✓ Image SHA-256 Hash: 5e0eb8786ebac6b55c91f2ca9819283ed4bc012bfb83d657642a1b988ae0ffb0
   ✓ Face Encoding SHA-256: 0358118952c2871e9b6cd4944d967ae6a690877b41b143b10cfd3efc3635e167
   ✓ Face Crop Saved: crops\face_crop_ronaldo.jpg

[Step 2/4] Searching for matching social media post (SerpApi Google Lens)...
   • Performing live reverse image search with Google Lens...
   ✓ Matching Post Found!
   ✓ Platform / Source: Instagram
   ✓ Matched URL: https://www.instagram.com/p/DY9CI1cDBEn/
   ✓ Post Title: Ronaldo fans are already manifesting a World Cup win for ...
   ✓ Total Similar Matches Discovered: 59

[Step 3/4] Hashing match data and writing to Polygon Amoy testnet...
   ✓ Record Hash (Digest): 6f76b0f4ad583092820adc243e58e573371fd49860c3b09937307c6cdab71df7
   ✓ Transaction Submitted & Confirmed!
   ✓ Transaction Hash: 0x8e576e7236828cd1952e9fbf41bb127eb51abc8bd5ea357ceba15caf64acea39
   ✓ Block Number: #46783479
   ✓ Gas Used: 47680 units
   ✓ Explorer Link: https://amoy.polygonscan.com/tx/0x8e576e7236828cd1952e9fbf41bb127eb51abc8bd5ea357ceba15caf64acea39

[Step 4/4] Re-verifying on-chain record...
   • Querying Polygon Amoy block for transaction input data...
   ✓ Transaction data retrieved from Polygon Amoy.
   ✓ Stored Record Hash:     6f76b0f4ad583092820adc243e58e573371fd49860c3b09937307c6cdab71df7
   ✓ Recomputed Record Hash: 6f76b0f4ad583092820adc243e58e573371fd49860c3b09937307c6cdab71df7
   ✓ On-Chain Matched URL:   https://www.instagram.com/p/DY9CI1cDBEn/
   ✓ On-Chain Image Hash:    5e0eb8786ebac6b55c91f2ca9819283ed4bc012bfb83d657642a1b988ae0ffb0
   ✓ On-Chain Face Hash:     0358118952c2871e9b6cd4944d967ae6a690877b41b143b10cfd3efc3635e167
   ✓ On-Chain Timestamp:     2026-09-05T09:51:56.377960+00:00

=============================================================================
                        VERIFIED ✅
 Tamper-evident face verification record is immutably anchored on-chain.
=============================================================================
```

---

## 🔗 Blockchain Specifications

- **Network**: Polygon Amoy Testnet
- **Chain ID**: `80002`
- **RPC Provider**: Alchemy (`https://polygon-amoy.g.alchemy.com/v2/...`)
- **Block Explorer**: [PolygonScan Amoy](https://amoy.polygonscan.com/)
- **Data Storage Mechanism**: Hex-encoded UTF-8 canonical JSON embedded in transaction input data field (`0x...`), authenticated with the sender's private key signature and mined into an immutable PoA block.

---

## ⚠️ Known Limitations

1. **SerpApi Rate Limits & API Quota**: Reverse image search relies on the SerpApi Google Lens engine; search frequency is constrained by the free tier monthly search quota.
2. **Reverse Search Indexing**: If a photograph is completely private, unpublished, or heavily modified with extreme filters, reverse image engines may not find an exact prior social media publication.
3. **Face Detection Lighting/Angle**: Extreme profiles (>60° yaw) or heavy occlusions may reduce detection confidence.
4. **Testnet vs Mainnet**: Deployed on Polygon Amoy testnet for zero-cost verifiable hackathon evaluation; production deployment would target Polygon POS Mainnet or Arbitrum/Optimism L2.
5. **Raw Transaction Payload vs Custom Smart Contract**: Data is stored directly in transaction calldata to avoid complex contract deployment overhead while maintaining 100% cryptographic immutability and verifiable access on-chain.

---

## 🏆 Hackathon Submission Checklist

- [x] Face detection & encoding from input image (`face_module.py`)
- [x] Live, genuine reverse image search matching real social media post URLs (`search_module.py`)
- [x] Tamper-evident proof anchored to Polygon Amoy testnet (`blockchain_module.py`)
- [x] On-chain re-verification confirming matching cryptographic hashes (`main.py`)
- [x] Clear step-by-step console output suitable for unedited screen recording
- [x] Zero hardcoded secrets (`.env` + `.env.example` + `os.getenv()`)
