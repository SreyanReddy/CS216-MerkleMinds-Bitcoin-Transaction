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

FUND_A_AMOUNT = 0.01
AMOUNT_A_TO_B = 0.004
AMOUNT_B_TO_C = 0.0025


def main() -> None:
    print("\n=== CS216 Part 1: Legacy P2PKH Transaction Chain ===")

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

    address_a = wallet.get_new_address(label="legacy_A", address_type="legacy")
    address_b = wallet.get_new_address(label="legacy_B", address_type="legacy")
    address_c = wallet.get_new_address(label="legacy_C", address_type="legacy")

    addresses = {
        "A": address_a,
        "B": address_b,
        "C": address_c,
        "address_type": "legacy",
    }
    pretty_print("Legacy Addresses", addresses)
    save_json("legacy_addresses.json", addresses, subdir="legacy")

    funding_txid = wallet.send_to_address(address_a, FUND_A_AMOUNT)
    mining_address = wallet.get_new_address(label="legacy_mining", address_type="bech32")
    wallet.mine_blocks(1, mining_address)

    funding_info = {
        "funding_txid": funding_txid,
        "funded_address": address_a,
        "fund_amount": FUND_A_AMOUNT,
        "confirmation_blocks_mined": 1,
        "mining_address": mining_address,
    }
    pretty_print("Funding A", funding_info)
    save_json("legacy_funding_A.json", funding_info, subdir="legacy")

    utxos_after_funding = wallet.list_unspent(addresses=[address_a])
    pretty_print("UTXOs for A after funding", utxos_after_funding)
    save_json("legacy_A_utxos.json", utxos_after_funding, subdir="legacy")

    step_ab = tx_manager.create_chain_step(
        from_address=address_a,
        to_address=address_b,
        amount=AMOUNT_A_TO_B,
        prefix="A_to_B",
        subdir="legacy",
        min_amount=AMOUNT_A_TO_B,
    )
    wallet.mine_blocks(1, mining_address)

    pretty_print("Legacy A -> B Artifact", step_ab)

    b_utxos = wallet.list_unspent(addresses=[address_b])
    pretty_print("UTXOs for B after A -> B", b_utxos)
    save_json("legacy_B_utxos_after_A_to_B.json", b_utxos, subdir="legacy")

    step_bc = tx_manager.create_chain_step(
        from_address=address_b,
        to_address=address_c,
        amount=AMOUNT_B_TO_C,
        prefix="B_to_C",
        subdir="legacy",
        min_amount=AMOUNT_B_TO_C,
    )
    wallet.mine_blocks(1, mining_address)

    pretty_print("Legacy B -> C Artifact", step_bc)

    recipient_output_ab = step_ab.get("recipient_output")
    if recipient_output_ab is None:
        raise RuntimeError(
            "Could not find recipient output for B in decoded A -> B transaction."
        )

    prev_output_index_for_b = recipient_output_ab["n"]

    legacy_analysis = validator.analyze_legacy_pair(
        decoded_prev_tx=step_ab["decoded_tx"],
        decoded_spend_tx=step_bc["decoded_tx"],
        prev_output_index=prev_output_index_for_b,
        spend_input_index=0,
    )
    pretty_print("Legacy Challenge / Response Analysis", legacy_analysis)
    save_json("legacy_challenge_response_analysis.json", legacy_analysis, subdir="legacy")

    ab_required = validator.extract_required_fields(
        decoded_tx=step_ab["decoded_tx"],
        vin_index=0,
        vout_index=prev_output_index_for_b,
    )
    bc_required = validator.extract_required_fields(
        decoded_tx=step_bc["decoded_tx"],
        vin_index=0,
        vout_index=0,
    )

    save_json("legacy_A_to_B_required_fields.json", ab_required, subdir="legacy")
    save_json("legacy_B_to_C_required_fields.json", bc_required, subdir="legacy")

    btcdeb_command = validator.build_legacy_btcdeb_script(
        spend_tx_decoded=step_bc["decoded_tx"],
        prev_tx_decoded=step_ab["decoded_tx"],
        prev_output_index=prev_output_index_for_b,
        spend_input_index=0,
    )

    btcdeb_notes = (
        "Run this command in your terminal after installing btcdeb.\n\n"
        f"{btcdeb_command}\n"
    )

    write_text("legacy_btcdeb_command.txt", btcdeb_notes, subdir="legacy")
    print("\n=== btcdeb command for Legacy validation ===")
    print(btcdeb_command)

    workflow_summary = {
        "part": "Part 1 - Legacy P2PKH",
        "wallet_name": WALLET_NAME,
        "addresses": addresses,
        "funding": funding_info,
        "tx_chain": {
            "A_to_B": {
                "txid": step_ab["txid"],
                "recipient_output_index_for_B": prev_output_index_for_b,
                "saved_paths": step_ab["saved_paths"],
            },
            "B_to_C": {
                "txid": step_bc["txid"],
                "saved_paths": step_bc["saved_paths"],
            },
        },
        "analysis_files": {
            "challenge_response": "outputs/legacy/legacy_challenge_response_analysis.json",
            "required_fields_A_to_B": "outputs/legacy/legacy_A_to_B_required_fields.json",
            "required_fields_B_to_C": "outputs/legacy/legacy_B_to_C_required_fields.json",
            "btcdeb_command": "outputs/legacy/legacy_btcdeb_command.txt",
        },
    }

    save_json("legacy_workflow_summary.json", workflow_summary, subdir="legacy")
    pretty_print("Legacy Workflow Summary", workflow_summary)

    print("\n=== Legacy run completed successfully ===")
    print(f"A -> B txid: {step_ab['txid']}")
    print(f"B -> C txid: {step_bc['txid']}")
    print("Artifacts saved under outputs/legacy/")


if __name__ == "__main__":
    main()