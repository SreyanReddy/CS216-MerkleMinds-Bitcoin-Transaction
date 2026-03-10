from typing import Any, Dict, List, Optional

from src.rpc_client import RPCClient


DEFAULT_WALLET_NAME = "cs216wallet"


class WalletManager:

    def __init__(self, rpc_client: RPCClient, wallet_name: str = DEFAULT_WALLET_NAME) -> None:
        self.rpc = rpc_client
        self.wallet_name = wallet_name
        self.wallet_rpc: Optional[RPCClient] = None

    def wallet_is_loaded(self) -> bool:
        loaded_wallets = self.rpc.list_wallets()
        return self.wallet_name in loaded_wallets

    def wallet_exists_on_disk(self) -> bool:
        wallet_dir_info = self.rpc.list_wallet_dir()
        existing_wallet_names = [
            wallet_info["name"] for wallet_info in wallet_dir_info.get("wallets", [])
        ]
        return self.wallet_name in existing_wallet_names

    def create_wallet(self) -> Dict[str, Any]:
        return self.rpc.call("createwallet", self.wallet_name)

    def load_wallet(self) -> Dict[str, Any]:
        return self.rpc.call("loadwallet", self.wallet_name)

    def unload_wallet(self) -> Dict[str, Any]:
        return self.rpc.call("unloadwallet", self.wallet_name)

    def create_or_load_wallet(self) -> RPCClient:
        if self.wallet_is_loaded():
            self.wallet_rpc = self.rpc.with_wallet(self.wallet_name)
            return self.wallet_rpc

        if self.wallet_exists_on_disk():
            self.load_wallet()
        else:
            self.create_wallet()

        self.wallet_rpc = self.rpc.with_wallet(self.wallet_name)
        return self.wallet_rpc

    def get_wallet_rpc(self) -> RPCClient:
        if self.wallet_rpc is None:
            self.create_or_load_wallet()
        return self.wallet_rpc

    def get_new_address(self, label: str = "", address_type: str = "legacy") -> str:
        wallet_rpc = self.get_wallet_rpc()
        return wallet_rpc.call("getnewaddress", label, address_type)

    def get_balance(self) -> float:
        wallet_rpc = self.get_wallet_rpc()
        return wallet_rpc.call("getbalance")

    def list_unspent(
        self,
        minconf: int = 1,
        maxconf: int = 9999999,
        addresses: Optional[List[str]] = None,) -> List[Dict[str, Any]]:
        wallet_rpc = self.get_wallet_rpc()
        if addresses:
            return wallet_rpc.call("listunspent", minconf, maxconf, addresses)
        return wallet_rpc.call("listunspent", minconf, maxconf)

    def send_to_address(self, address: str, amount: float) -> str:
        wallet_rpc = self.get_wallet_rpc()
        return wallet_rpc.call("sendtoaddress", address, amount)

    def mine_blocks(self, num_blocks: int, address: Optional[str] = None) -> List[str]:
        wallet_rpc = self.get_wallet_rpc()

        mining_address = address
        if not mining_address:
            mining_address = self.get_new_address(label="mining", address_type="bech32")

        return wallet_rpc.call("generatetoaddress", num_blocks, mining_address)

    def get_wallet_info(self) -> Dict[str, Any]:
        wallet_rpc = self.get_wallet_rpc()
        return wallet_rpc.call("getwalletinfo")

    def get_receive_address(self, address_type: str = "legacy", label: str = "") -> str:
        return self.get_new_address(label=label, address_type=address_type)

    def ensure_spendable_balance(
        self,
        minimum_balance: float = 1.0,
        mining_address_type: str = "bech32",) -> float:
        current_balance = self.get_balance()
        if current_balance >= minimum_balance:
            return current_balance

        mining_address = self.get_new_address(
            label="initial_mining",
            address_type=mining_address_type,
        )
        self.mine_blocks(101, mining_address)

        return self.get_balance()

    def find_utxo_by_address(self, address: str) -> Optional[Dict[str, Any]]:
        utxos = self.list_unspent(addresses=[address])
        return utxos[0] if utxos else None

    def find_utxo_by_txid(self, txid: str) -> Optional[Dict[str, Any]]:
        utxos = self.list_unspent()
        for utxo in utxos:
            if utxo.get("txid") == txid:
                return utxo
        return None

    def fund_address_and_confirm(
        self,
        address: str,
        amount: float,
        blocks: int = 1,
    ) -> Dict[str, Any]:
        txid = self.send_to_address(address, amount)

        self.mine_blocks(blocks)

        utxo = self.find_utxo_by_address(address)
        if utxo is None:
            raise RuntimeError(
                f"No confirmed UTXO found for address {address!r} after mining {blocks} block(s). "
                f"Last funding txid was {txid}."
            )

        utxo["funding_txid"] = txid
        return utxo