from typing import Any, Dict, Optional

from rpc_client import RPCClient
from utils import (
    build_single_output,
    build_spending_input,
    extract_full_script_view,
    extract_tx_summary,
    find_vout_for_address,
    require_successful_signing,
    save_json,
    select_utxo_for_address,
    summarize_utxo,
)


class TransactionManager:
    """
    Handles raw transaction creation, signing, broadcasting, decoding,
    and artifact generation for the CS216 Bitcoin assignment.
    """

    def __init__(self, wallet_rpc: RPCClient) -> None:
        self.wallet_rpc = wallet_rpc

    def list_unspent(
        self,
        minconf: int = 1,
        maxconf: int = 9999999,
    ) -> list[Dict[str, Any]]:
        """
        Fetch spendable UTXOs from the wallet.
        """
        return self.wallet_rpc.call("listunspent", minconf, maxconf)

    def find_address_utxo(
        self,
        address: str,
        min_amount: float = 0.0,
        minconf: int = 1,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best UTXO for a specific address.
        """
        utxos = self.list_unspent(minconf=minconf)
        return select_utxo_for_address(utxos, address, min_amount=min_amount)

    def create_raw_transaction(
        self,
        utxo: Dict[str, Any],
        to_address: str,
        amount: float,
    ) -> str:
        """
        Create a simple 1-input, 1-output raw transaction.
        Change and fee handling are intentionally deferred to fundrawtransaction.
        """
        inputs = [build_spending_input(utxo)]
        outputs = build_single_output(to_address, amount)
        return self.wallet_rpc.call("createrawtransaction", inputs, outputs)

    def fund_raw_transaction(self, raw_tx_hex: str) -> Dict[str, Any]:
        """
        Let Bitcoin Core add change output and fee selection.
        """
        return self.wallet_rpc.call("fundrawtransaction", raw_tx_hex)

    def sign_raw_transaction(self, raw_tx_hex: str) -> Dict[str, Any]:
        """
        Sign a raw transaction with wallet-managed keys.
        """
        return self.wallet_rpc.call("signrawtransactionwithwallet", raw_tx_hex)

    def broadcast_transaction(self, signed_tx_hex: str) -> str:
        """
        Broadcast a signed transaction and return txid.
        """
        return self.wallet_rpc.call("sendrawtransaction", signed_tx_hex)

    def get_raw_transaction_hex(self, txid: str) -> str:
        """
        Fetch raw hex for a transaction by txid.
        Requires txindex or wallet visibility / mempool visibility depending on node setup.
        """
        return self.wallet_rpc.call("getrawtransaction", txid)

    def decode_raw_transaction(self, raw_tx_hex: str) -> Dict[str, Any]:
        """
        Decode raw transaction hex into JSON.
        """
        return self.wallet_rpc.call("decoderawtransaction", raw_tx_hex)

    def get_decoded_transaction_by_txid(self, txid: str) -> Dict[str, Any]:
        """
        Get raw transaction hex by txid, then decode it.
        """
        raw_tx_hex = self.get_raw_transaction_hex(txid)
        return self.decode_raw_transaction(raw_tx_hex)

    def create_sign_broadcast(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        min_amount: float = 0.0,
    ) -> Dict[str, Any]:
        """
        End-to-end raw transaction flow:
        1. locate UTXO for from_address
        2. create raw tx
        3. fund raw tx
        4. sign raw tx
        5. broadcast
        6. decode signed tx

        Returns a rich artifact dict useful for logs and report generation.
        """
        utxo = self.find_address_utxo(
            address=from_address,
            min_amount=min_amount,
            minconf=1,
        )
        if not utxo:
            raise RuntimeError(
                f"No suitable confirmed UTXO found for address {from_address} "
                f"with minimum amount {min_amount}."
            )

        raw_tx_hex = self.create_raw_transaction(
            utxo=utxo,
            to_address=to_address,
            amount=amount,
        )

        funded_result = self.fund_raw_transaction(raw_tx_hex)
        funded_tx_hex = funded_result.get("hex")
        if not funded_tx_hex:
            raise RuntimeError("fundrawtransaction did not return funded transaction hex.")

        sign_result = self.sign_raw_transaction(funded_tx_hex)
        signed_tx_hex = require_successful_signing(sign_result)

        txid = self.broadcast_transaction(signed_tx_hex)
        decoded_tx = self.decode_raw_transaction(signed_tx_hex)

        return {
            "from_address": from_address,
            "to_address": to_address,
            "requested_amount": amount,
            "selected_utxo": summarize_utxo(utxo),
            "raw_tx_hex": raw_tx_hex,
            "funded_tx": funded_result,
            "signed_tx_hex": signed_tx_hex,
            "txid": txid,
            "decoded_tx": decoded_tx,
            "tx_summary": extract_tx_summary(decoded_tx),
            "script_view": extract_full_script_view(decoded_tx),
        }

    def save_transaction_artifacts(
        self,
        artifact: Dict[str, Any],
        prefix: str,
        subdir: str,
    ) -> Dict[str, str]:
        """
        Save useful JSON artifacts for the report.
        """
        txid = artifact["txid"]
        decoded_tx = artifact["decoded_tx"]
        script_view = artifact["script_view"]
        tx_summary = artifact["tx_summary"]

        raw_info_path = save_json(
            filename=f"{prefix}_{txid}_full.json",
            data=artifact,
            subdir=subdir,
        )

        decoded_path = save_json(
            filename=f"{prefix}_{txid}_decoded.json",
            data=decoded_tx,
            subdir=subdir,
        )

        scripts_path = save_json(
            filename=f"{prefix}_{txid}_scripts.json",
            data=script_view,
            subdir=subdir,
        )

        summary_path = save_json(
            filename=f"{prefix}_{txid}_summary.json",
            data=tx_summary,
            subdir=subdir,
        )

        return {
            "full_artifact": str(raw_info_path),
            "decoded_tx": str(decoded_path),
            "scripts": str(scripts_path),
            "summary": str(summary_path),
        }

    def extract_output_for_recipient(
        self,
        decoded_tx: Dict[str, Any],
        recipient_address: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Find the output paying to the intended recipient in a decoded tx.
        """
        return find_vout_for_address(decoded_tx, recipient_address)

    def create_chain_step(
        self,
        from_address: str,
        to_address: str,
        amount: float,
        prefix: str,
        subdir: str,
        min_amount: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Higher-level convenience method for one transaction step in a chain
        such as A->B or B->C.

        Also saves artifacts immediately.
        """
        artifact = self.create_sign_broadcast(
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            min_amount=min_amount,
        )

        recipient_vout = self.extract_output_for_recipient(
            decoded_tx=artifact["decoded_tx"],
            recipient_address=to_address,
        )

        artifact["recipient_output"] = recipient_vout
        artifact["saved_paths"] = self.save_transaction_artifacts(
            artifact=artifact,
            prefix=prefix,
            subdir=subdir,
        )
        return artifact

    def get_transaction_metrics(self, txid: str) -> Dict[str, Any]:
        """
        Fetch decoded tx by txid and return only size-related metrics for comparison.
        """
        decoded_tx = self.get_decoded_transaction_by_txid(txid)
        summary = extract_tx_summary(decoded_tx)

        return {
            "txid": summary.get("txid"),
            "size": summary.get("size"),
            "vsize": summary.get("vsize"),
            "weight": summary.get("weight"),
            "vin_count": summary.get("vin_count"),
            "vout_count": summary.get("vout_count"),
        }

    def build_comparison_record(
        self,
        txid: str,
        label: str,
        tx_type: str,
    ) -> Dict[str, Any]:
        """
        Create a compact comparison record for Part 3 report tables.
        tx_type example values:
        - legacy
        - p2sh-segwit
        """
        metrics = self.get_transaction_metrics(txid)
        metrics["label"] = label
        metrics["tx_type"] = tx_type
        return metrics