import json
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def ensure_outputs_dir() -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUTS_DIR


def save_json(filename: str, data: Any, subdir: Optional[str] = None) -> Path:
    base_dir = ensure_outputs_dir()

    if subdir:
        base_dir = base_dir / subdir
        base_dir.mkdir(parents=True, exist_ok=True)

    file_path = base_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)

    return file_path


def load_json(filename: str, subdir: Optional[str] = None) -> Any:
    base_dir = ensure_outputs_dir()

    if subdir:
        base_dir = base_dir / subdir

    file_path = base_dir / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def pretty_print(title: str, data: Any) -> None:
    print(f"\n{'=' * 20} {title} {'=' * 20}")
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2))
    else:
        print(data)
    print(f"{'=' * (42 + len(title))}\n")


def assert_regtest(blockchain_info: Dict[str, Any]) -> None:
    chain = blockchain_info.get("chain")
    if chain != "regtest":
        raise RuntimeError(
            f"Expected node to run on 'regtest', but got '{chain}'. "
            "Start bitcoind in regtest mode and verify bitcoin.conf / RPC settings."
        )


def require_successful_signing(sign_result: Dict[str, Any]) -> str:
    if not sign_result.get("complete", False):
        errors = sign_result.get("errors", [])
        raise RuntimeError(
            f"Transaction signing incomplete. Errors: {json.dumps(errors, indent=2)}"
        )

    signed_hex = sign_result.get("hex")
    if not signed_hex:
        raise RuntimeError("Signed transaction hex missing in sign result.")

    return signed_hex


def find_vout_for_address(decoded_tx: Dict[str, Any], address: str) -> Optional[Dict[str, Any]]:
    for vout in decoded_tx.get("vout", []):
        script_pub_key = vout.get("scriptPubKey", {})
        addresses = script_pub_key.get("addresses", [])
        single_address = script_pub_key.get("address")

        if single_address == address:
            return vout

        if address in addresses:
            return vout

    return None


def extract_tx_summary(decoded_tx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "txid": decoded_tx.get("txid"),
        "hash": decoded_tx.get("hash"),
        "version": decoded_tx.get("version"),
        "size": decoded_tx.get("size"),
        "vsize": decoded_tx.get("vsize"),
        "weight": decoded_tx.get("weight"),
        "locktime": decoded_tx.get("locktime"),
        "vin_count": len(decoded_tx.get("vin", [])),
        "vout_count": len(decoded_tx.get("vout", [])),
    }


def extract_output_script_details(vout: Dict[str, Any]) -> Dict[str, Any]:
    script_pub_key = vout.get("scriptPubKey", {})

    return {
        "value": vout.get("value"),
        "n": vout.get("n"),
        "scriptpubkey_type": script_pub_key.get("type"),
        "scriptpubkey_asm": script_pub_key.get("asm"),
        "scriptpubkey_hex": script_pub_key.get("hex"),
        "address": script_pub_key.get("address"),
        "addresses": script_pub_key.get("addresses", []),
    }


def extract_input_script_details(vin: Dict[str, Any]) -> Dict[str, Any]:
    script_sig = vin.get("scriptSig", {})

    return {
        "txid": vin.get("txid"),
        "vout": vin.get("vout"),
        "sequence": vin.get("sequence"),
        "scriptsig_asm": script_sig.get("asm"),
        "scriptsig_hex": script_sig.get("hex"),
        "txinwitness": vin.get("txinwitness", []),
    }


def extract_full_script_view(decoded_tx: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tx_summary": extract_tx_summary(decoded_tx),
        "inputs": [extract_input_script_details(vin) for vin in decoded_tx.get("vin", [])],
        "outputs": [extract_output_script_details(vout) for vout in decoded_tx.get("vout", [])],
    }


def select_utxo_for_address(
    utxos: List[Dict[str, Any]],
    address: str,
    min_amount: float = 0.0,) -> Optional[Dict[str, Any]]:
    candidates = [
        utxo
        for utxo in utxos
        if utxo.get("address") == address and float(utxo.get("amount", 0)) >= min_amount
    ]

    if not candidates:
        return None

    candidates.sort(key=lambda x: float(x.get("amount", 0)), reverse=True)
    return candidates[0]


def build_spending_input(utxo: Dict[str, Any]) -> Dict[str, Any]:
    if "txid" not in utxo or "vout" not in utxo:
        raise ValueError("UTXO must contain 'txid' and 'vout'.")

    return {
        "txid": utxo["txid"],
        "vout": utxo["vout"],
    }


def build_single_output(address: str, amount: float) -> Dict[str, float]:
    return {address: amount}


def summarize_utxo(utxo: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "txid": utxo.get("txid"),
        "vout": utxo.get("vout"),
        "address": utxo.get("address"),
        "amount": utxo.get("amount"),
        "confirmations": utxo.get("confirmations"),
        "spendable": utxo.get("spendable"),
        "solvable": utxo.get("solvable"),
        "desc": utxo.get("desc"),
    }


def write_text(filename: str, content: str, subdir: Optional[str] = None) -> Path:
    base_dir = ensure_outputs_dir()

    if subdir:
        base_dir = base_dir / subdir
        base_dir.mkdir(parents=True, exist_ok=True)

    file_path = base_dir / filename
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return file_path