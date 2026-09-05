import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from hexbytes import HexBytes

AMOY_CHAIN_ID = 80002
POLYGONSCAN_AMOY_BASE = "https://amoy.polygonscan.com/tx/"


def get_web3_instance(rpc_url: Optional[str] = None) -> Web3:
    endpoint = rpc_url or os.getenv("ALCHEMY_RPC_URL")
    if not endpoint:
        raise ValueError("ALCHEMY_RPC_URL is not configured. Please check your .env file.")

    w3 = Web3(Web3.HTTPProvider(endpoint))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    if not w3.is_connected():
        raise ConnectionError("Failed to connect to Polygon Amoy RPC endpoint.")
    
    return w3


def calculate_record_hash(record: Dict[str, Any]) -> str:
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
    w3 = get_web3_instance(rpc_url)
    
    priv_key = private_key or os.getenv("PRIVATE_KEY")
    if not priv_key:
        raise ValueError("PRIVATE_KEY is missing from environment. Add it to .env")

    if priv_key.startswith("0x"):
        priv_key = priv_key[2:]

    account = w3.eth.account.from_key(priv_key)
    sender_address = wallet_address or os.getenv("WALLET_ADDRESS") or account.address
    sender_address = Web3.to_checksum_address(sender_address)

    timestamp_iso = datetime.now(timezone.utc).isoformat()
    record_payload = {
        "protocol": "truFaceLedger-v1",
        "timestamp": timestamp_iso,
        "image_hash": image_hash,
        "face_encoding_hash": face_encoding_hash,
        "match_url": match_url,
        "metadata": metadata or {}
    }

    record_digest = calculate_record_hash(record_payload)
    record_payload["record_hash"] = record_digest

    json_bytes = json.dumps(record_payload, separators=(',', ':')).encode("utf-8")
    hex_data = "0x" + json_bytes.hex()

    balance = w3.eth.get_balance(sender_address)
    if balance == 0:
        raise ValueError(f"Wallet {sender_address} has 0 POL balance on Polygon Amoy testnet.")

    nonce = w3.eth.get_transaction_count(sender_address, 'pending')
    chain_id = w3.eth.chain_id
    
    try:
        max_priority_fee = w3.eth.max_priority_fee
    except Exception:
        max_priority_fee = w3.to_wei(30, 'gwei')

    latest_block = w3.eth.get_block('latest')
    base_fee = latest_block.get('baseFeePerGas', w3.to_wei(25, 'gwei'))
    max_fee = base_fee * 2 + max_priority_fee

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
        tx_params["gas"] = int(estimated_gas * 1.2)
    except Exception:
        tx_params["gas"] = 65000

    signed_tx = w3.eth.account.sign_transaction(tx_params, private_key=priv_key)
    tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    tx_hash_hex = tx_hash_bytes.to_0x_hex()
    explorer_url = f"{POLYGONSCAN_AMOY_BASE}{tx_hash_hex}"

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


def read_record(tx_hash: str, rpc_url: Optional[str] = None) -> Dict[str, Any]:
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
