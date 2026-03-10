## CS216 Bitcoin Transaction Lab Assignment
**From Command Line to Programming: A Hands-on Approach**

This repository contains the implementation for the CS216 Bitcoin Transaction Lab assignment. The project demonstrates how to create, sign, broadcast, decode, and analyze Bitcoin transactions in **regtest** mode using both:

- **Part 1:** Legacy **P2PKH**
- **Part 2:** SegWit **P2SH-P2WPKH** using `p2sh-segwit`

The project also includes artifacts for **Part 3 comparative analysis**, where transaction size, virtual size, weight, and script structure are compared between Legacy and SegWit transactions. The assignment requires code for both parts, a clear README, and a single PDF report uploaded in a public GitHub repository.

---

### Team Members

- **Name:** Sreyan Reddy Regatte — **Roll No:** 240051018
- **Name:** Velpula Vikram Varma — **Roll No:** 240001078
- **Name:** Katammagiri Manas Joel — **Roll No:** 240004025
- **Name:** Chinnakondu Hemanth Royal — **Roll No:** 240041010

---

### Objective

The objective of this assignment is to understand the creation and validation of Bitcoin transactions using:

- **Legacy P2PKH**
- **SegWit P2SH-P2WPKH**

The program connects to `bitcoind` over RPC, creates transactions, decodes scripts, validates script execution, and compares transaction efficiency. The assignment also requires explaining why SegWit transactions are smaller and what benefits they provide.

---

### Repository Structure

```text
CS216-MerkleMinds-Bitcoin-Transaction/
│
├── CS216_Blockchain_Assignment2.pdf
│
├── scripts/
│   ├── run_legacy.py
│   └── run_segwit.py
│
├── src/
│   ├── __init__.py
│   ├── rpc_client.py
│   ├── wallet.py
│   ├── transaction.py
│   ├── validation.py
│   └── utils.py
│
├── outputs/
│   ├── legacy/
│   └── segwit/
│
├── tests/
│   └── test_basic.py
│
├── .env
├── .gitignore
├── README.md
└── requirements.txt
```

---

### Tools and Dependencies

#### Required tools

- **Bitcoin Core** (`bitcoind`)
- **Bitcoin CLI** (`bitcoin-cli`)
- **Python 3**
- **btcdeb** (Bitcoin Script Debugger)

#### Python dependencies

Install Python dependencies using:

```bash
pip install -r requirements.txt
```

---

### Bitcoin Core Configuration

Before running the scripts, configure `bitcoin.conf` for **regtest** mode.

Create or edit:

- **Windows:** `%APPDATA%\Bitcoin\bitcoin.conf`

Use the specified config file in config folder.

Regtest RPC uses:

- **Host:** `127.0.0.1`
- **Port:** `18443`

---

### Environment Variables

Create a `.env` file in the project root with the given file in the repo.

---

### Setup and Quick Test

#### 1. Start Bitcoin Core in regtest

```bash
bitcoind -regtest -daemon
```

#### 2. Create a wallet

```bash
bitcoin-cli -regtest createwallet "cs216wallet"
```

#### 3. Generate an address

```bash
bitcoin-cli -regtest -rpcwallet=cs216wallet getnewaddress
```

#### 4. Mine 101 blocks to make funds spendable

```bash
bitcoin-cli -regtest -rpcwallet=cs216wallet generatetoaddress 101 "<ADDRESS>"
```

#### 5. Check wallet balance

```bash
bitcoin-cli -regtest -rpcwallet=cs216wallet getbalance
```

---

### How to Run the Assignment Code

#### Run Part 1: Legacy P2PKH

```bash
python scripts/run_legacy.py
```

This script:

- **connects** to `bitcoind` over RPC,
- **creates or loads** a wallet,
- **generates** three legacy addresses: A, B, C,
- **funds** A,
- **creates** transaction **A → B**,
- **decodes** the transaction and extracts the locking script,
- **uses** the resulting UTXO to create **B → C**,
- **decodes and analyzes** `scriptSig`,
- **prepares** `btcdeb` validation artifacts.

#### Run Part 2: P2SH-P2WPKH (SegWit)

```bash
python scripts/run_segwit.py
```

This script:

- **connects** to `bitcoind` over RPC,
- **creates or loads** a wallet,
- **generates** three `p2sh-segwit` addresses: A’, B’, C’,
- **funds** A’,
- **creates** transaction **A’ → B’**,
- **decodes** the transaction and extracts the challenge script,
- **uses** the resulting UTXO to create **B’ → C’**,
- **extracts** `scriptSig`, `txinwitness`, and size metrics,
- **prepares** witness-aware `btcdeb` validation artifacts.

#### Run tests

```bash
pytest tests/test_basic.py
```

---

### Output Artifacts

Generated transaction artifacts are saved under:

- `outputs/legacy/`
- `outputs/segwit/`

These include:

- decoded transaction JSON,
- script-focused JSON,
- transaction summaries,
- workflow summaries,
- `btcdeb` command or notes files.

---

### Part 1 Deliverables Covered by This Repository

For **Legacy P2PKH**, the lecture and assignment require:

- **two transactions:** A → B and B → C
- **TXIDs** for both transactions
- **`decoderawtransaction` output**
- extracted:
  - `scriptPubKey.asm`
  - `scriptPubKey.type`
  - `scriptSig.asm`
  - `size`, `vsize`, `weight`
- **`btcdeb` validation and screenshots**

This repository automates those steps and stores the corresponding artifacts in `outputs/legacy/`.

---

### Part 2 Deliverables Covered by This Repository

For **SegWit P2SH-P2WPKH**, the lecture and assignment require:

- **two transactions:** A’ → B’ and B’ → C’
- use of **`p2sh-segwit`** address type
- **TXIDs** for both transactions
- **`decoderawtransaction` output**
- extracted:
  - `scriptPubKey.asm`
  - `scriptPubKey.type`
  - `scriptSig.asm`
  - `txinwitness`
  - `size`, `vsize`, `weight`
- **`btcdeb` validation with witness data**

This repository automates those steps and stores the corresponding artifacts in `outputs/segwit/`.

---

### Part 3 Comparative Analysis

Comparison of Legacy P2PKH and SegWit P2SH-P2WPKH in terms of:

- transaction size,
- virtual size,
- weight,
- fee savings,
- script structure,
- witness discount,
- benefits of SegWit.

Example SegWit size intuition:

- witness data is counted at lower weight,
- weight = {non-witness bytes} * 4 + {witness bytes},
- vsize = {weight} / 4.

---

### Script Validation with btcdeb

Using **btcdeb** to validate scripts for both parts and including screenshots in the report.

#### Legacy P2PKH

For Legacy, `btcdeb` is used by combining:

- the spending input’s `scriptSig`
- the referenced output’s `scriptPubKey`

#### SegWit P2SH-P2WPKH

- outer `scriptPubKey`,
- `scriptSig` witness program,
- `txinwitness` contents.

---

### Important Notes

- **Use `legacy` address type for Part 1.**
- **Use `p2sh-segwit` address type for Part 2.**
- **Mine 101 blocks initially** for spendable balance.
- **Mine 1 block after each transaction** to confirm it.
- **Do not manage raw private keys manually**; let `bitcoind` handle key management through wallet RPC commands such as `getnewaddress` and `signrawtransactionwithwallet`.

---

### References

- Bitcoin Core RPC documentation
- BIP 16: Pay to Script Hash (P2SH)
- BIP 141: Segregated Witness (SegWit)
- `btcdeb`
- Descriptor wallet documentation
- Blockchain Commons tutorial referenced in the assignment
