import os
from typing import Any, Optional

from dotenv import load_dotenv
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException


load_dotenv()


class RPCClient:

    def __init__(
        self,
        rpc_user: Optional[str] = None,
        rpc_password: Optional[str] = None,
        rpc_host: Optional[str] = None,
        rpc_port: Optional[int] = None,
        wallet_name: Optional[str] = None,
    ) -> None:
        self.rpc_user = rpc_user or os.getenv("RPC_USER")
        self.rpc_password = rpc_password or os.getenv("RPC_PASSWORD")
        self.rpc_host = rpc_host or os.getenv("RPC_HOST", "127.0.0.1")
        self.rpc_port = rpc_port or int(os.getenv("RPC_PORT", "18443"))
        self.wallet_name = wallet_name

        if not self.rpc_user or not self.rpc_password:
            raise ValueError(
                "Missing RPC credentials. Set RPC_USER and RPC_PASSWORD in environment."
            )

        self.base_url = (
            f"http://{self.rpc_user}:{self.rpc_password}@{self.rpc_host}:{self.rpc_port}"
        )

        self.connection = self._create_connection()

    def _create_connection(self) -> AuthServiceProxy:

        if self.wallet_name:
            wallet_url = f"{self.base_url}/wallet/{self.wallet_name}"
            return AuthServiceProxy(wallet_url, timeout=120)

        return AuthServiceProxy(self.base_url, timeout=120)

    def with_wallet(self, wallet_name: str) -> "RPCClient":

        return RPCClient(
            rpc_user=self.rpc_user,
            rpc_password=self.rpc_password,
            rpc_host=self.rpc_host,
            rpc_port=self.rpc_port,
            wallet_name=wallet_name,
        )

    def call(self, method: str, *args: Any) -> Any:

        try:
            rpc_method = getattr(self.connection, method)
            return rpc_method(*args)
        except JSONRPCException as exc:
            raise RuntimeError(
                f"Bitcoin RPC error while calling '{method}': {exc.error}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Unexpected RPC error while calling '{method}': {exc}"
            ) from exc

    def ping(self) -> bool:
        try:
            self.call("getblockchaininfo")
            return True
        except Exception:
            return False

    def assert_regtest(self) -> None:
        info = self.get_blockchain_info()
        chain = info.get("chain")
        if chain != "regtest":
            raise RuntimeError(f"Expected regtest chain, but node reports: {chain!r}")

    def get_blockchain_info(self) -> dict:
        return self.call("getblockchaininfo")

    def get_network_info(self) -> dict:
        return self.call("getnetworkinfo")

    def list_wallets(self) -> list:
        return self.call("listwallets")

    def list_wallet_dir(self) -> dict:
        return self.call("listwalletdir")