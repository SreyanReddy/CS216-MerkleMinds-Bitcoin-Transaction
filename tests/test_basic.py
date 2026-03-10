from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils import (
    build_single_output,
    build_spending_input,
    extract_input_script_details,
    extract_output_script_details,
    extract_tx_summary,
    require_successful_signing,
    select_utxo_for_address,
)
from src.validation import ValidationManager


def test_build_single_output() -> None:
    output = build_single_output("mock_address", 0.123)
    assert output == {"mock_address": 0.123}


def test_build_spending_input() -> None:
    utxo = {"txid": "abc123", "vout": 1, "amount": 0.5}
    tx_input = build_spending_input(utxo)

    assert tx_input["txid"] == "abc123"
    assert tx_input["vout"] == 1


def test_build_spending_input_raises_for_missing_fields() -> None:
    try:
        build_spending_input({"txid": "abc123"})
        assert False, "Expected ValueError for missing vout"
    except ValueError:
        assert True


def test_select_utxo_for_address_returns_largest_matching_utxo() -> None:
    utxos = [
        {"txid": "t1", "vout": 0, "address": "A", "amount": 0.001},
        {"txid": "t2", "vout": 1, "address": "A", "amount": 0.01},
        {"txid": "t3", "vout": 0, "address": "B", "amount": 0.5},
    ]

    chosen = select_utxo_for_address(utxos, address="A", min_amount=0.002)

    assert chosen is not None
    assert chosen["txid"] == "t2"
    assert chosen["amount"] == 0.01


def test_select_utxo_for_address_returns_none_when_not_found() -> None:
    utxos = [
        {"txid": "t1", "vout": 0, "address": "A", "amount": 0.001},
    ]

    chosen = select_utxo_for_address(utxos, address="A", min_amount=0.1)
    assert chosen is None


def test_require_successful_signing_returns_hex() -> None:
    sign_result = {
        "complete": True,
        "hex": "deadbeef",
    }

    signed_hex = require_successful_signing(sign_result)
    assert signed_hex == "deadbeef"


def test_require_successful_signing_raises_on_incomplete() -> None:
    sign_result = {
        "complete": False,
        "errors": [{"message": "mock signing error"}],
    }

    try:
        require_successful_signing(sign_result)
        assert False, "Expected RuntimeError for incomplete signing"
    except RuntimeError:
        assert True


def test_extract_tx_summary() -> None:
    decoded_tx = {
        "txid": "tx123",
        "hash": "hash123",
        "version": 2,
        "size": 225,
        "vsize": 144,
        "weight": 573,
        "locktime": 0,
        "vin": [{"txid": "prev1"}],
        "vout": [{"n": 0}, {"n": 1}],
    }

    summary = extract_tx_summary(decoded_tx)

    assert summary["txid"] == "tx123"
    assert summary["size"] == 225
    assert summary["vsize"] == 144
    assert summary["weight"] == 573
    assert summary["vin_count"] == 1
    assert summary["vout_count"] == 2


def test_extract_output_script_details() -> None:
    vout = {
        "value": 0.004,
        "n": 1,
        "scriptPubKey": {
            "asm": "OP_DUP OP_HASH160 abcd OP_EQUALVERIFY OP_CHECKSIG",
            "hex": "76a914abcd88ac",
            "type": "pubkeyhash",
            "address": "mock_address",
        },
    }

    details = extract_output_script_details(vout)

    assert details["n"] == 1
    assert details["value"] == 0.004
    assert details["scriptpubkey_type"] == "pubkeyhash"
    assert details["address"] == "mock_address"


def test_extract_input_script_details_legacy() -> None:
    vin = {
        "txid": "prevtx",
        "vout": 0,
        "sequence": 123,
        "scriptSig": {
            "asm": "3045... 02ab...",
            "hex": "4830450221",
        },
    }

    details = extract_input_script_details(vin)

    assert details["txid"] == "prevtx"
    assert details["scriptsig_asm"] == "3045... 02ab..."
    assert details["scriptsig_hex"] == "4830450221"
    assert details["txinwitness"] == []


def test_extract_input_script_details_segwit() -> None:
    vin = {
        "txid": "prevtx",
        "vout": 1,
        "sequence": 999,
        "scriptSig": {
            "asm": "0014abcd1234",
            "hex": "160014abcd1234",
        },
        "txinwitness": [
            "30440220...",
            "03abcdef...",
        ],
    }

    details = extract_input_script_details(vin)

    assert details["vout"] == 1
    assert details["scriptsig_asm"] == "0014abcd1234"
    assert len(details["txinwitness"]) == 2


def test_validation_extract_required_fields_legacy() -> None:
    decoded_tx = {
        "txid": "legacytx",
        "size": 191,
        "vsize": 191,
        "weight": 764,
        "vin": [
            {
                "txid": "prevtx",
                "vout": 0,
                "scriptSig": {
                    "asm": "3045... 02ab...",
                    "hex": "483045",
                },
            }
        ],
        "vout": [
            {
                "n": 0,
                "value": 0.003,
                "scriptPubKey": {
                    "asm": "OP_DUP OP_HASH160 abcd OP_EQUALVERIFY OP_CHECKSIG",
                    "hex": "76a914abcd88ac",
                    "type": "pubkeyhash",
                    "address": "legacy_addr",
                },
            }
        ],
    }

    extracted = ValidationManager.extract_required_fields(
        decoded_tx=decoded_tx,
        vin_index=0,
        vout_index=0,
    )

    assert extracted["txid"] == "legacytx"
    assert extracted["input"]["scriptSig"]["asm"] == "3045... 02ab..."
    assert extracted["output"]["scriptPubKey"]["type"] == "pubkeyhash"


def test_validation_extract_required_fields_segwit() -> None:
    decoded_tx = {
        "txid": "segwittx",
        "size": 222,
        "vsize": 141,
        "weight": 561,
        "vin": [
            {
                "txid": "prevseg",
                "vout": 1,
                "scriptSig": {
                    "asm": "0014abcd1234",
                    "hex": "160014abcd1234",
                },
                "txinwitness": [
                    "30440220...",
                    "02cafe...",
                ],
            }
        ],
        "vout": [
            {
                "n": 0,
                "value": 0.0025,
                "scriptPubKey": {
                    "asm": "OP_HASH160 deadbeef OP_EQUAL",
                    "hex": "a914deadbeef87",
                    "type": "scripthash",
                    "address": "2NmockAddr",
                },
            }
        ],
    }

    extracted = ValidationManager.extract_required_fields(
        decoded_tx=decoded_tx,
        vin_index=0,
        vout_index=0,
    )

    assert extracted["txid"] == "segwittx"
    assert extracted["input"]["scriptSig"]["asm"] == "0014abcd1234"
    assert len(extracted["input"]["txinwitness"]) == 2
    assert extracted["output"]["scriptPubKey"]["type"] == "scripthash"


def test_analyze_legacy_pair() -> None:
    prev_tx = {
        "txid": "ab",
        "vout": [
            {
                "n": 0,
                "scriptPubKey": {
                    "asm": "OP_DUP OP_HASH160 abcd OP_EQUALVERIFY OP_CHECKSIG",
                    "hex": "76a914abcd88ac",
                    "type": "pubkeyhash",
                    "address": "legacyB",
                },
            }
        ],
    }

    spend_tx = {
        "txid": "bc",
        "vin": [
            {
                "txid": "ab",
                "vout": 0,
                "scriptSig": {
                    "asm": "3045... 02ab...",
                    "hex": "483045",
                },
            }
        ],
    }

    analysis = ValidationManager.analyze_legacy_pair(
        decoded_prev_tx=prev_tx,
        decoded_spend_tx=spend_tx,
        prev_output_index=0,
        spend_input_index=0,
    )

    assert analysis["mode"] == "legacy"
    assert "challenge_script" in analysis
    assert "response_script" in analysis


def test_analyze_p2sh_p2wpkh_pair() -> None:
    prev_tx = {
        "txid": "a'b'",
        "vout": [
            {
                "n": 0,
                "scriptPubKey": {
                    "asm": "OP_HASH160 deadbeef OP_EQUAL",
                    "hex": "a914deadbeef87",
                    "type": "scripthash",
                    "address": "2NsegwitB",
                },
            }
        ],
    }

    spend_tx = {
        "txid": "b'c'",
        "vin": [
            {
                "txid": "a'b'",
                "vout": 0,
                "scriptSig": {
                    "asm": "0014abcd1234",
                    "hex": "160014abcd1234",
                },
                "txinwitness": [
                    "30440220...",
                    "03abcdef...",
                ],
            }
        ],
    }

    analysis = ValidationManager.analyze_p2sh_p2wpkh_pair(
        decoded_prev_tx=prev_tx,
        decoded_spend_tx=spend_tx,
        prev_output_index=0,
        spend_input_index=0,
    )

    assert analysis["mode"] == "p2sh-p2wpkh"
    assert len(analysis["witness"]) == 2
    assert "txinwitness" not in analysis["response_script"]


def test_compute_fee_savings_percent() -> None:
    savings = ValidationManager.compute_fee_savings_percent(
        legacy_vsize=200,
        segwit_vsize=140,
    )
    assert round(savings, 2) == 30.0


def test_classify_transaction_type_legacy() -> None:
    decoded_tx = {
        "vin": [{"scriptSig": {"asm": "3045... 02ab..."}}],
        "vout": [{"scriptPubKey": {"type": "pubkeyhash"}}],
    }

    tx_type = ValidationManager.classify_transaction_type(decoded_tx)
    assert tx_type == "legacy"


def test_classify_transaction_type_segwit() -> None:
    decoded_tx = {
        "vin": [
            {
                "scriptSig": {"asm": "0014abcd1234"},
                "txinwitness": ["3044...", "03ab..."],
            }
        ],
        "vout": [{"scriptPubKey": {"type": "scripthash"}}],
    }

    tx_type = ValidationManager.classify_transaction_type(decoded_tx)
    assert tx_type == "p2sh-p2wpkh"