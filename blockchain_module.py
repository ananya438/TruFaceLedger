"""
blockchain_module.py
=============================================================================
truFaceLedger - Blockchain Verification Module (Polygon Amoy Testnet)
=============================================================================
This module handles writing cryptographic verification records to the Polygon
Amoy testnet (Chain ID 80002) using Web3.py and Alchemy RPC, and re-fetching /
verifying the tamper-evident records directly from the blockchain.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from hexbytes import HexBytes

# Polygon Amoy Testnet Chain ID
AMOY_CHAIN_ID = 80002
POLYGONSCAN_AMOY_BASE = "https://amoy.polygonscan.com/tx/"


def get_web3_instance(rpc_url: Optional[str] = None) -> Web3:
    """
    Initializes and returns a Web3 instance configured for Polygon Amoy testnet
    with Proof-of-Authority (PoA) middleware enabled.
    """
    endpoint = rpc_url or os.getenv("ALCHEMY_RPC_URL")
    if not endpoint:
        raise ValueError("ALCHEMY_RPC_URL is not configured. Please check your .env file.")

    w3 = Web3(Web3.HTTPProvider(endpoint))
    
    # Inject PoA middleware required for Polygon chains (extraData > 32 bytes)
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        raise ConnectionError(f"Failed to connect to Polygon Amoy RPC at {endpoint[:45]}...")
    
    return w3


def calculate_record_hash(record: Dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 hash of a verification record dictionary."""
    # Exclude record_hash itself when computing the hash
    cleaned = {k: v for k, v in record.items() if k != "record_hash"}
    serialized = json.dumps(cleaned, sort_keys=True).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def write_record(
    image_hash: str,
    face_encoding_hash: str,
    match_url: str,
    metadata: Optional[Dict[str, Any]] = None,
    rpc_url: Optional[str] = None,
    private_key: Optional[str] = None,
    wallet_address: Optional[str] = None
) -> Dict[str, Any]:
    """
    Packs the face match proof and metadata into a tamper-evident payload,
    signs an on-chain transaction on Polygon Amoy testnet, broadcasts it,
    and returns the confirmed transaction details.

    Args:
        image_hash: SHA-256 hash of the input image
        face_encoding_hash: SHA-256 hash of the extracted face encoding vector
        match_url: URL of the genuine matching social media post / page
        metadata: Additional metadata (e.g. source platform, title, timestamp)
        rpc_url: Optional Alchemy RPC URL override
        private_key: Optional MetaMask private key override
        wallet_address: Optional Wallet address override

    Returns:
        dict: Transaction receipt details, explorer URL, and on-chain payload
    """
    w3 = get_web3_instance(rpc_url)
    
    priv_key = private_key or os.getenv("PRIVATE_KEY")
    if not priv_key:
        raise ValueError("PRIVATE_KEY is missing from environment. Add it to .env")

    # Clean private key format
    if priv_key.startswith("0x"):
        priv_key = priv_key[2:]

    # Derive or validate sender account
    account = w3.eth.account.from_key(priv_key)
    sender_address = wallet_address or os.getenv("WALLET_ADDRESS") or account.address
    sender_address = Web3.to_checksum_address(sender_address)

    # Prepare canonical record payload
    timestamp_iso = datetime.now(timezone.utc).isoformat()
    record_payload = {
        "protocol": "truFaceLedger-v1",
        "timestamp": timestamp_iso,
        "image_hash": image_hash,
        "face_encoding_hash": face_encoding_hash,
        "match_url": match_url,
        "metadata": metadata or {}
    }

    # Generate and attach the record cryptographic digest
    record_digest = calculate_record_hash(record_payload)
    record_payload["record_hash"] = record_digest

    # Serialize to JSON and encode to hex
    json_bytes = json.dumps(record_payload, separators=(',', ':')).encode("utf-8")
    hex_data = "0x" + json_bytes.hex()

    # Check wallet balance
    balance = w3.eth.get_balance(sender_address)
    if balance == 0:
        raise ValueError(
            f"Wallet {sender_address} has 0 POL balance on Polygon Amoy testnet. "
            "Please fund your wallet with Amoy testnet POL."
        )

    # Prepare transaction parameters
    nonce = w3.eth.get_transaction_count(sender_address, 'pending')
    chain_id = w3.eth.chain_id
    
    # Gas pricing (EIP-1559)
    try:
        max_priority_fee = w3.eth.max_priority_fee
    except Exception:
        max_priority_fee = w3.to_wei(30, 'gwei')

    latest_block = w3.eth.get_block('latest')
    base_fee = latest_block.get('baseFeePerGas', w3.to_wei(25, 'gwei'))
    max_fee = base_fee * 2 + max_priority_fee

    # Estimate gas for data payload (transfer 0 POL to self with embedded payload)
    tx_params = {
        "chainId": chain_id,
        "from": sender_address,
        "to": sender_address,
        "value": 0,
        "nonce": nonce,
        "data": hex_data,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority_fee,
    }

    try:
        estimated_gas = w3.eth.estimate_gas(tx_params)
        # Add 20% safety margin
        tx_params["gas"] = int(estimated_gas * 1.2)
    except Exception:
        tx_params["gas"] = 65000

    # Sign transaction
    signed_tx = w3.eth.account.sign_transaction(tx_params, private_key=priv_key)

    # Broadcast transaction
    tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hash_hex = tx_hash_bytes.to_0x_hex()
    explorer_url = f"{POLYGONSCAN_AMOY_BASE}{tx_hash_hex}"

    # Wait for confirmation receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=120)

    if receipt.status != 1:
        raise RuntimeError(f"Transaction failed on Polygon Amoy. Tx Hash: {tx_hash_hex}")

    return {
        "success": True,
        "tx_hash": tx_hash_hex,
        "block_number": receipt.blockNumber,
        "gas_used": receipt.gasUsed,
        "explorer_url": explorer_url,
        "sender": sender_address,
        "record": record_payload,
        "record_hash": record_digest
    }


def read_record(
    tx_hash: str,
    rpc_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetches an on-chain transaction from Polygon Amoy, decodes the stored payload,
    recomputes the record hash, and verifies tamper-evident authenticity.

    Args:
        tx_hash: Hex transaction hash (0x...)
        rpc_url: Optional RPC URL override

    Returns:
        dict: {
            "verified": bool,
            "tx_hash": str,
            "block_number": int,
            "record": dict,
            "recomputed_hash": str,
            "stored_hash": str,
            "error": str or None
        }
    """
    w3 = get_web3_instance(rpc_url)

    try:
        tx = w3.eth.get_transaction(tx_hash)
    except Exception as e:
        return {
            "verified": False,
            "tx_hash": tx_hash,
            "block_number": None,
            "record": None,
            "recomputed_hash": None,
            "stored_hash": None,
            "error": f"Failed to retrieve transaction from Polygon Amoy: {str(e)}"
        }

    input_data = tx.get("input")
    if not input_data or input_data == "0x":
        return {
            "verified": False,
            "tx_hash": tx_hash,
            "block_number": tx.get("blockNumber"),
            "record": None,
            "recomputed_hash": None,
            "stored_hash": None,
            "error": "No data payload found in this transaction."
        }

    # Convert HexBytes or hex string to UTF-8 string
    try:
        if isinstance(input_data, HexBytes):
            raw_bytes = bytes(input_data)
        elif isinstance(input_data, str):
            clean_hex = input_data[2:] if input_data.startswith("0x") else input_data
            raw_bytes = bytes.fromhex(clean_hex)
        else:
            raw_bytes = bytes(input_data)

        decoded_json_str = raw_bytes.decode("utf-8")
        record = json.loads(decoded_json_str)
    except Exception as e:
        return {
            "verified": False,
            "tx_hash": tx_hash,
            "block_number": tx.get("blockNumber"),
            "record": None,
            "recomputed_hash": None,
            "stored_hash": None,
            "error": f"Failed to decode on-chain JSON payload: {str(e)}"
        }

    # Recompute record hash to verify tamper evidence
    stored_hash = record.get("record_hash")
    recomputed_hash = calculate_record_hash(record)
    is_valid = (stored_hash is not None) and (stored_hash.lower() == recomputed_hash.lower())

    return {
        "verified": is_valid,
        "tx_hash": tx_hash,
        "block_number": tx.get("blockNumber"),
        "record": record,
        "recomputed_hash": recomputed_hash,
        "stored_hash": stored_hash,
        "error": None if is_valid else "Hash mismatch! On-chain payload may have been modified or corrupted."
    }


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv()

    if len(sys.argv) < 2:
        print("Usage: python blockchain_module.py <tx_hash>")
        sys.exit(1)

    query_tx = sys.argv[1]
    res = read_record(query_tx)
    print(json.dumps(res, indent=2))
