from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.rpc_client import RPCClient
from src.wallet import WalletManager
from src.transaction import TransactionManager
from src.validation import ValidationManager
from src.utils import (
    assert_regtest,
    pretty_print,
    save_json,
    write_text,
)

WALLET_NAME = "cs216wallet"
INITIAL_MIN_BALANCE = 1.0

FUND_A_PRIME_AMOUNT = 0.01
AMOUNT_A_PRIME_TO_B_PRIME = 0.004
AMOUNT_B_PRIME_TO_C_PRIME = 0.0025


def main() -> None:
    print("\n=== CS216 Part 2: P2SH-P2WPKH (p2sh-segwit) Transaction Chain ===")

    rpc = RPCClient()
    blockchain_info = rpc.get_blockchain_info()
    assert_regtest(blockchain_info)
    pretty_print("Blockchain Info", blockchain_info)

    wallet = WalletManager(rpc, WALLET_NAME)
    wallet_rpc = wallet.create_or_load_wallet()

    wallet.ensure_spendable_balance(minimum_balance=INITIAL_MIN_BALANCE)
    pretty_print("Wallet Info", wallet.get_wallet_info())
    pretty_print("Wallet Balance", wallet.get_balance())

    tx_manager = TransactionManager(wallet_rpc)
    validator = ValidationManager()

    address_a_prime = wallet.get_new_address(label="segwit_A_prime", address_type="p2sh-segwit")
    address_b_prime = wallet.get_new_address(label="segwit_B_prime", address_type="p2sh-segwit")
    address_c_prime = wallet.get_new_address(label="segwit_C_prime", address_type="p2sh-segwit")

    addresses = {
        "A_prime": address_a_prime,
        "B_prime": address_b_prime,
        "C_prime": address_c_prime,
        "address_type": "p2sh-segwit",
    }
    pretty_print("P2SH-SegWit Addresses", addresses)
    save_json("segwit_addresses.json", addresses, subdir="segwit")

    funding_txid = wallet.send_to_address(address_a_prime, FUND_A_PRIME_AMOUNT)
    mining_address = wallet.get_new_address(label="segwit_mining", address_type="bech32")
    wallet.mine_blocks(1, mining_address)

    funding_info = {
        "funding_txid": funding_txid,
        "funded_address": address_a_prime,
        "fund_amount": FUND_A_PRIME_AMOUNT,
        "confirmation_blocks_mined": 1,
        "mining_address": mining_address,
    }
    pretty_print("Funding A'", funding_info)
    save_json("segwit_funding_A_prime.json", funding_info, subdir="segwit")

    utxos_after_funding = wallet.list_unspent(addresses=[address_a_prime])
    pretty_print("UTXOs for A' after funding", utxos_after_funding)
    save_json("segwit_A_prime_utxos.json", utxos_after_funding, subdir="segwit")

    step_ab_prime = tx_manager.create_chain_step(
        from_address=address_a_prime,
        to_address=address_b_prime,
        amount=AMOUNT_A_PRIME_TO_B_PRIME,
        prefix="A_prime_to_B_prime",
        subdir="segwit",
        min_amount=AMOUNT_A_PRIME_TO_B_PRIME,
    )
    wallet.mine_blocks(1, mining_address)

    pretty_print("SegWit A' -> B' Artifact", step_ab_prime)

    b_prime_utxos = wallet.list_unspent(addresses=[address_b_prime])
    pretty_print("UTXOs for B' after A' -> B'", b_prime_utxos)
    save_json("segwit_B_prime_utxos_after_A_prime_to_B_prime.json", b_prime_utxos, subdir="segwit")

    step_bc_prime = tx_manager.create_chain_step(
        from_address=address_b_prime,
        to_address=address_c_prime,
        amount=AMOUNT_B_PRIME_TO_C_PRIME,
        prefix="B_prime_to_C_prime",
        subdir="segwit",
        min_amount=AMOUNT_B_PRIME_TO_C_PRIME,
    )
    wallet.mine_blocks(1, mining_address)

    pretty_print("SegWit B' -> C' Artifact", step_bc_prime)

    recipient_output_ab_prime = step_ab_prime.get("recipient_output")
    if recipient_output_ab_prime is None:
        raise RuntimeError(
            "Could not find recipient output for B' in decoded A' -> B' transaction."
        )

    prev_output_index_for_b_prime = recipient_output_ab_prime["n"]

    segwit_analysis = validator.analyze_p2sh_p2wpkh_pair(
        decoded_prev_tx=step_ab_prime["decoded_tx"],
        decoded_spend_tx=step_bc_prime["decoded_tx"],
        prev_output_index=prev_output_index_for_b_prime,
        spend_input_index=0,
    )
    pretty_print("P2SH-P2WPKH Challenge / Response Analysis", segwit_analysis)
    save_json("segwit_challenge_response_analysis.json", segwit_analysis, subdir="segwit")

    ab_prime_required = validator.extract_required_fields(
        decoded_tx=step_ab_prime["decoded_tx"],
        vin_index=0,
        vout_index=prev_output_index_for_b_prime,
    )
    bc_prime_required = validator.extract_required_fields(
        decoded_tx=step_bc_prime["decoded_tx"],
        vin_index=0,
        vout_index=0,
    )

    save_json("segwit_A_prime_to_B_prime_required_fields.json", ab_prime_required, subdir="segwit")
    save_json("segwit_B_prime_to_C_prime_required_fields.json", bc_prime_required, subdir="segwit")

    btcdeb_hint = validator.build_p2sh_p2wpkh_btcdeb_hint(
        spend_tx_decoded=step_bc_prime["decoded_tx"],
        prev_tx_decoded=step_ab_prime["decoded_tx"],
        prev_output_index=prev_output_index_for_b_prime,
        spend_input_index=0,
    )

    btcdeb_notes = (
        "P2SH-P2WPKH btcdeb validation notes\n"
        "-----------------------------------\n"
        "For SegWit, document all three pieces:\n"
        "1. Outer scriptPubKey from previous output\n"
        "2. scriptSig from the spending input (witness program)\n"
        "3. txinwitness values (signature + compressed pubkey)\n\n"
        "Use these values when running btcdeb and take screenshots showing\n"
        "witness-aware validation steps.\n\n"
        f"Outer scriptPubKey ASM:\n{btcdeb_hint['outer_scriptpubkey_asm']}\n\n"
        f"scriptSig ASM:\n{btcdeb_hint['scriptsig_asm']}\n\n"
        f"txinwitness:\n{btcdeb_hint['txinwitness']}\n\n"
        f"Documentation view:\n{btcdeb_hint['documentation_view']}\n"
    )

    write_text("segwit_btcdeb_notes.txt", btcdeb_notes, subdir="segwit")
    pretty_print("SegWit btcdeb Hint", btcdeb_hint)

    comparison_rows = [
        validator.build_size_comparison_row(
            label="A_prime_to_B_prime",
            decoded_tx=step_ab_prime["decoded_tx"],
            tx_type="p2sh-p2wpkh",
        ),
        validator.build_size_comparison_row(
            label="B_prime_to_C_prime",
            decoded_tx=step_bc_prime["decoded_tx"],
            tx_type="p2sh-p2wpkh",
        ),
    ]

    average_metrics = validator.compute_average_metrics(comparison_rows)
    witness_discount_ab_prime = validator.explain_witness_discount(step_ab_prime["decoded_tx"])
    witness_discount_bc_prime = validator.explain_witness_discount(step_bc_prime["decoded_tx"])

    part3_payload = {
        "comparison_rows": comparison_rows,
        "average_metrics": average_metrics,
        "witness_discount_examples": {
            "A_prime_to_B_prime": witness_discount_ab_prime,
            "B_prime_to_C_prime": witness_discount_bc_prime,
        },
    }

    save_json("segwit_part3_metrics.json", part3_payload, subdir="segwit")
    pretty_print("SegWit Part 3 Metrics", part3_payload)

    workflow_summary = {
        "part": "Part 2 - P2SH-P2WPKH",
        "wallet_name": WALLET_NAME,
        "addresses": addresses,
        "funding": funding_info,
        "tx_chain": {
            "A_prime_to_B_prime": {
                "txid": step_ab_prime["txid"],
                "recipient_output_index_for_B_prime": prev_output_index_for_b_prime,
                "saved_paths": step_ab_prime["saved_paths"],
            },
            "B_prime_to_C_prime": {
                "txid": step_bc_prime["txid"],
                "saved_paths": step_bc_prime["saved_paths"],
            },
        },
        "analysis_files": {
            "challenge_response": "outputs/segwit/segwit_challenge_response_analysis.json",
            "required_fields_A_prime_to_B_prime": "outputs/segwit/segwit_A_prime_to_B_prime_required_fields.json",
            "required_fields_B_prime_to_C_prime": "outputs/segwit/segwit_B_prime_to_C_prime_required_fields.json",
            "btcdeb_notes": "outputs/segwit/segwit_btcdeb_notes.txt",
            "part3_metrics": "outputs/segwit/segwit_part3_metrics.json",
        },
        "report_notes": [
            "Mention the txid for A' -> B' and explain how that output became B' as a UTXO.",
            "Show that B' -> C' spends the earlier output created for B'.",
            "Explain the outer P2SH locking script in scriptPubKey.",
            "Explain that scriptSig contains the witness program, not the signature/pubkey pair.",
            "Document txinwitness and show how it carries the signature and compressed public key.",
            "Include screenshots of decoderawtransaction outputs and btcdeb execution.",
            "Record size, vsize, and weight for both transactions and compare them with Legacy.",
        ],
    }

    save_json("segwit_workflow_summary.json", workflow_summary, subdir="segwit")
    pretty_print("SegWit Workflow Summary", workflow_summary)

    print("\n=== SegWit run completed successfully ===")
    print(f"A' -> B' txid: {step_ab_prime['txid']}")
    print(f"B' -> C' txid: {step_bc_prime['txid']}")
    print("Artifacts saved under outputs/segwit/")


if __name__ == "__main__":
    main()