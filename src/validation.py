from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from src.utils import extract_full_script_view, extract_tx_summary


class ValidationManager:
    """
    Script-analysis and report-helper utilities for the CS216 Bitcoin assignment.

    Focus:
    - legacy P2PKH script analysis
    - P2SH-P2WPKH script analysis
    - btcdeb command preparation
    - comparison helpers for Part 3
    """

    @staticmethod
    def get_input(decoded_tx: Dict[str, Any], vin_index: int = 0) -> Dict[str, Any]:
        vin_list = decoded_tx.get("vin", [])
        if vin_index >= len(vin_list):
            raise IndexError(f"Input index {vin_index} out of range.")
        return vin_list[vin_index]

    @staticmethod
    def get_output(decoded_tx: Dict[str, Any], vout_index: int) -> Dict[str, Any]:
        vout_list = decoded_tx.get("vout", [])
        if vout_index >= len(vout_list):
            raise IndexError(f"Output index {vout_index} out of range.")
        return vout_list[vout_index]

    @staticmethod
    def get_output_for_address(decoded_tx: Dict[str, Any], address: str) -> Optional[Dict[str, Any]]:
        for vout in decoded_tx.get("vout", []):
            spk = vout.get("scriptPubKey", {})
            if spk.get("address") == address:
                return vout
            if address in spk.get("addresses", []):
                return vout
        return None

    @staticmethod
    def extract_required_fields(
        decoded_tx: Dict[str, Any],
        vin_index: int = 0,
        vout_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Extract the exact fields emphasized by the assignment/lecture:
        - scriptPubKey.asm and type
        - scriptSig.asm
        - txinwitness
        - size, vsize, weight
        """
        vin = ValidationManager.get_input(decoded_tx, vin_index)

        result = {
            "txid": decoded_tx.get("txid"),
            "size": decoded_tx.get("size"),
            "vsize": decoded_tx.get("vsize"),
            "weight": decoded_tx.get("weight"),
            "input": {
                "txid": vin.get("txid"),
                "vout": vin.get("vout"),
                "scriptSig": {
                    "asm": vin.get("scriptSig", {}).get("asm"),
                    "hex": vin.get("scriptSig", {}).get("hex"),
                },
                "txinwitness": vin.get("txinwitness", []),
            },
        }

        if vout_index is not None:
            vout = ValidationManager.get_output(decoded_tx, vout_index)
            result["output"] = {
                "n": vout.get("n"),
                "value": vout.get("value"),
                "scriptPubKey": {
                    "asm": vout.get("scriptPubKey", {}).get("asm"),
                    "hex": vout.get("scriptPubKey", {}).get("hex"),
                    "type": vout.get("scriptPubKey", {}).get("type"),
                    "address": vout.get("scriptPubKey", {}).get("address"),
                    "addresses": vout.get("scriptPubKey", {}).get("addresses", []),
                },
            }

        return result

    @staticmethod
    def analyze_legacy_pair(
        decoded_prev_tx: Dict[str, Any],
        decoded_spend_tx: Dict[str, Any],
        prev_output_index: int,
        spend_input_index: int = 0,
    ) -> Dict[str, Any]:
        """
        Analyze a classic P2PKH flow:
        - previous tx output contains locking script (challenge)
        - spending tx input contains scriptSig (response)
        """
        prev_vout = ValidationManager.get_output(decoded_prev_tx, prev_output_index)
        spend_vin = ValidationManager.get_input(decoded_spend_tx, spend_input_index)

        challenge_spk = prev_vout.get("scriptPubKey", {})
        response_sig = spend_vin.get("scriptSig", {})

        return {
            "mode": "legacy",
            "previous_txid": decoded_prev_tx.get("txid"),
            "spending_txid": decoded_spend_tx.get("txid"),
            "challenge_script": {
                "source": "previous transaction output scriptPubKey",
                "asm": challenge_spk.get("asm"),
                "hex": challenge_spk.get("hex"),
                "type": challenge_spk.get("type"),
                "address": challenge_spk.get("address"),
            },
            "response_script": {
                "source": "spending transaction input scriptSig",
                "asm": response_sig.get("asm"),
                "hex": response_sig.get("hex"),
            },
            "witness": [],
            "explanation": (
                "For Legacy P2PKH, the challenge is the previous output's scriptPubKey "
                "(typically OP_DUP OP_HASH160 <pubKeyHash> OP_EQUALVERIFY OP_CHECKSIG). "
                "The response is the spending input's scriptSig, which typically pushes "
                "the signature and public key. Bitcoin validates the spend by executing "
                "scriptSig followed by scriptPubKey; the pubKey hash must match and the "
                "signature must verify."
            ),
        }

    @staticmethod
    def analyze_p2sh_p2wpkh_pair(
        decoded_prev_tx: Dict[str, Any],
        decoded_spend_tx: Dict[str, Any],
        prev_output_index: int,
        spend_input_index: int = 0,
    ) -> Dict[str, Any]:
        """
        Analyze a P2SH-P2WPKH flow:
        - previous output scriptPubKey is outer P2SH challenge
        - spending input scriptSig should contain witness program
        - actual signature/public key live in txinwitness
        """
        prev_vout = ValidationManager.get_output(decoded_prev_tx, prev_output_index)
        spend_vin = ValidationManager.get_input(decoded_spend_tx, spend_input_index)

        challenge_spk = prev_vout.get("scriptPubKey", {})
        response_sig = spend_vin.get("scriptSig", {})
        txinwitness = spend_vin.get("txinwitness", [])

        return {
            "mode": "p2sh-p2wpkh",
            "previous_txid": decoded_prev_tx.get("txid"),
            "spending_txid": decoded_spend_tx.get("txid"),
            "challenge_script": {
                "source": "previous transaction output scriptPubKey",
                "asm": challenge_spk.get("asm"),
                "hex": challenge_spk.get("hex"),
                "type": challenge_spk.get("type"),
                "address": challenge_spk.get("address"),
            },
            "response_script": {
                "source": "spending transaction input scriptSig",
                "asm": response_sig.get("asm"),
                "hex": response_sig.get("hex"),
            },
            "witness": txinwitness,
            "explanation": (
                "For P2SH-P2WPKH, the previous output scriptPubKey is the outer P2SH "
                "locking script (typically OP_HASH160 <scriptHash> OP_EQUAL). The "
                "spending input's scriptSig is much smaller and usually contains the "
                "redeem/witness program such as 0014<pubKeyHash>. The actual signature "
                "and compressed public key are moved to txinwitness. This separation is "
                "the key reason SegWit reduces effective transaction weight and vsize."
            ),
        }

    @staticmethod
    def build_legacy_btcdeb_script(
        spend_tx_decoded: Dict[str, Any],
        prev_tx_decoded: Dict[str, Any],
        prev_output_index: int,
        spend_input_index: int = 0,
    ) -> str:
        """
        Build a simple combined-script btcdeb command for legacy P2PKH.

        Lecture pattern:
        btcdeb '<sig> <pubKey> OP_DUP OP_HASH160 <pubKeyHash> OP_EQUALVERIFY OP_CHECKSIG'
        """
        spend_vin = ValidationManager.get_input(spend_tx_decoded, spend_input_index)
        prev_vout = ValidationManager.get_output(prev_tx_decoded, prev_output_index)

        script_sig_asm = spend_vin.get("scriptSig", {}).get("asm", "")
        script_pubkey_asm = prev_vout.get("scriptPubKey", {}).get("asm", "")

        combined = f"{script_sig_asm} {script_pubkey_asm}".strip()
        return f"btcdeb '{combined}'"

    @staticmethod
    def build_p2sh_p2wpkh_btcdeb_hint(
        spend_tx_decoded: Dict[str, Any],
        prev_tx_decoded: Dict[str, Any],
        prev_output_index: int,
        spend_input_index: int = 0,
    ) -> Dict[str, Any]:
        """
        Provide a practical btcdeb helper payload for P2SH-P2WPKH.

        SegWit validation is more nuanced than plain script concatenation because
        signatures live in txinwitness. For the report, we still want to surface:
        - outer scriptPubKey
        - scriptSig witness program
        - txinwitness elements
        - a suggested combined view for documentation
        """
        spend_vin = ValidationManager.get_input(spend_tx_decoded, spend_input_index)
        prev_vout = ValidationManager.get_output(prev_tx_decoded, prev_output_index)

        script_sig_asm = spend_vin.get("scriptSig", {}).get("asm", "")
        script_pubkey_asm = prev_vout.get("scriptPubKey", {}).get("asm", "")
        txinwitness = spend_vin.get("txinwitness", [])

        witness_items = " ".join(txinwitness)
        documentation_view = f"{script_sig_asm} | witness: [{witness_items}] | {script_pubkey_asm}"

        return {
            "btcdeb_note": (
                "For P2SH-P2WPKH, witness data must be supplied in addition to the "
                "script path. Use the previous output's scriptPubKey, the spending "
                "input's scriptSig (witness program), and txinwitness values when "
                "running btcdeb or documenting the validation flow."
            ),
            "outer_scriptpubkey_asm": script_pubkey_asm,
            "scriptsig_asm": script_sig_asm,
            "txinwitness": txinwitness,
            "documentation_view": documentation_view,
        }

    @staticmethod
    def classify_transaction_type(decoded_tx: Dict[str, Any]) -> str:
        """
        Heuristic classifier based on decoded input/output fields.
        Useful for report automation.
        """
        vin0 = decoded_tx.get("vin", [{}])[0]
        vout0 = decoded_tx.get("vout", [{}])[0]

        has_witness = bool(vin0.get("txinwitness"))
        scriptsig_asm = vin0.get("scriptSig", {}).get("asm", "") or ""
        spk_type = vout0.get("scriptPubKey", {}).get("type")

        if has_witness or "0014" in scriptsig_asm:
            return "p2sh-p2wpkh"
        if spk_type == "pubkeyhash":
            return "legacy"
        return "unknown"

    @staticmethod
    def compute_fee_savings_percent(legacy_vsize: float, segwit_vsize: float) -> float:
        if legacy_vsize <= 0:
            raise ValueError("legacy_vsize must be positive.")
        return (1 - (segwit_vsize / legacy_vsize)) * 100.0

    @staticmethod
    def compute_average_metrics(records: List[Dict[str, Any]]) -> Dict[str, float]:
        if not records:
            return {"avg_size": 0.0, "avg_vsize": 0.0, "avg_weight": 0.0}

        count = len(records)
        total_size = sum(float(r.get("size", 0) or 0) for r in records)
        total_vsize = sum(float(r.get("vsize", 0) or 0) for r in records)
        total_weight = sum(float(r.get("weight", 0) or 0) for r in records)

        return {
            "avg_size": total_size / count,
            "avg_vsize": total_vsize / count,
            "avg_weight": total_weight / count,
        }

    @staticmethod
    def build_size_comparison_row(
        label: str,
        decoded_tx: Dict[str, Any],
        tx_type: str,
        baseline_vsize: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Build one report-ready comparison row.
        """
        summary = extract_tx_summary(decoded_tx)
        row = {
            "label": label,
            "tx_type": tx_type,
            "size": summary.get("size"),
            "vsize": summary.get("vsize"),
            "weight": summary.get("weight"),
        }

        if baseline_vsize and summary.get("vsize") is not None:
            row["fee_savings_percent"] = round(
                ValidationManager.compute_fee_savings_percent(
                    legacy_vsize=float(baseline_vsize),
                    segwit_vsize=float(summary["vsize"]),
                ),
                2,
            )
        else:
            row["fee_savings_percent"] = 0.0

        return row

    @staticmethod
    def explain_witness_discount(decoded_tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return the exact formulas and an interpretation for Part 3.
        """
        size = decoded_tx.get("size")
        vsize = decoded_tx.get("vsize")
        weight = decoded_tx.get("weight")

        return {
            "size": size,
            "vsize": vsize,
            "weight": weight,
            "formula": {
                "weight": "(non-witness bytes × 4) + witness bytes",
                "vsize": "ceil(weight / 4)",
            },
            "explanation": (
                "SegWit moves signatures to txinwitness. Witness bytes are discounted in "
                "weight calculation, so vsize is often significantly smaller than raw size. "
                "Because fees are paid using vsize, SegWit transactions are cheaper."
            ),
        }

    @staticmethod
    def build_report_payload(
        decoded_tx: Dict[str, Any],
        tx_label: str,
        tx_type: str,
        vin_index: int = 0,
        vout_index: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Compact report bundle combining scripts + size metrics.
        """
        return {
            "tx_label": tx_label,
            "tx_type": tx_type,
            "required_fields": ValidationManager.extract_required_fields(
                decoded_tx=decoded_tx,
                vin_index=vin_index,
                vout_index=vout_index,
            ),
            "script_view": extract_full_script_view(decoded_tx),
            "summary": extract_tx_summary(decoded_tx),
        }