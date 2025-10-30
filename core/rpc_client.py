from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import requests
import time

class BitcoinRPCClient:
    def __init__(self, config: dict):
        self.config = config
        self.rpc = self.get_bitcoin_rpc_connection()
    
    def get_bitcoin_rpc_connection(self):
        """Connects to Bitcoin Core RPC using the provided config" dict."""
        print("get_bitcoin_rpc_connection()")
        url = f"http://{self.config['user']}:{self.config['password']}@{self.config['host']}:{int(self.config['port'])}"
        # proxy = self.config.get("proxy")
        
        # if proxy:
        #     # Substitute with an implementation that uses requests with SOCKS
        #     return RequestsBitcoinRPC(url, proxy)  # Define RequestsBitcoinRPC class as needed
        # else:
        rpc = AuthServiceProxy(url)
        # Test connection
        try:
            info = rpc.getblockchaininfo()
            print(f"Connected to Bitcoin Core chain: {info['chain']}")
            return rpc
        except JSONRPCException as e:
            print(f"Error connecting to Bitcoin Core: {e.error['message']}")
            raise

    def safe_rpc_call(self, method_name: str, *args, retries: int = 3, delay: int = 5):
        """Handles RPC calls with automatic connection retry and re-establishment logic."""
        print("safe_rpc_call()")
        for i in range(retries):
            print(f"self.rpc: {self.rpc}")
            try:
                if self.rpc is None:
                    print("self.rpc is None")
                    self.rpc = self.get_bitcoin_rpc_connection()
                    if self.rpc is None:
                        raise ConnectionError("Could not establish connection.")
                
                print(f"Executing RPC method: {method_name} (Attempt {i + 1}/{retries})")
                method_to_call = getattr(self.rpc, method_name)
                return method_to_call(*args)

            except (BrokenPipeError, ConnectionError, IOError) as e:
                print(f"Connection error detected during call: {e}")
                self.rpc = None  # Invalidate the current connection
                if i < retries - 1:
                    print(f"Retrying connection in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Max retries reached for safe_rpc_call. Failing.")
                    raise  # Re-raise the exception after exhausting retries

            except JSONRPCException as e:
                print(f"Bitcoind RPC error: {e.error['message']}")
                raise  # Do not retry on RPC logic errors

    def broadcast_transaction_via_rpc(self, raw_tx_hex: str):
        """
        Broadcasts a raw transaction hex via Bitcoin Core RPC sendrawtransaction.
        Returns (txid, None) on success, (None, error_message) on failure.
        Story 4.3.
        """
        print(f"!!!!!!!call broadcast_transaction_via_rpc: {self.rpc}, raw_tx_hex: {raw_tx_hex}")
        if self.rpc is None:
            return None, "No RPC connection"
        try:
            # For AuthServiceProxy, python-bitcoinrpc supports maxfeerate as a keyword or positional.
            # For RequestsBitcoinRPC, we've modified its sendrawtransaction to accept it.
            # if isinstance(self.rpc, RequestsBitcoinRPC):
            #     print(f"!!isinstance RequestsBitcoinRPC: {self.rpc}")
            #     txid = self.rpc.sendrawtransaction(
            #         raw_tx_hex, 0.0
            #     )  # Pass 0.0 for no feerate limit
            # else:  # AuthServiceProxy
            print(f"!!is AuthServiceProxy: {self.rpc}")
            txid = self.rpc.safe_rpc_call("sendrawtransaction", raw_tx_hex, 0.0 )  # Pass 0.0 for no feerate limit
            print(f"received txid: {txid}")
            return txid, None
        except JSONRPCException as e:
            msg = e.error.get("message", str(e))
            print(f"JSONRPCException: %s", msg)
            return None, msg
        except requests.exceptions.RequestException as e:
            print(f"RequestException: %s", str(e))
            return None, str(e)
        except Exception as e:
            print(f"General Exception: %s", str(e))
            return None, str(e)

# class RequestsBitcoinRPC:
#     def __init__(self, url, proxy):
#         self.url = url
#         self.proxies = {"http": proxy, "https": proxy}
#         self.auth = None
#         # Parse user:pass@host:port from url
#         import re

#         m = re.match(r"http://([^:]+):([^@]+)@([^:]+):(\d+)", url)
#         if m:
#             self.auth = (m.group(1), m.group(2))
#             self.rpc_url = f"http://{m.group(3)}:{m.group(4)}"
#         else:
    #         raise ValueError(f"Invalid RPC URL: {url}")

    # def _call(self, method, params=None):
    #     if params is None:
    #         params = []
    #     payload = {
    #         "jsonrpc": "1.0",
    #         "id": "btcmesh",
    #         "method": method,
    #         "params": params,
    #     }
    #     resp = requests.post(
    #         self.rpc_url, json=payload, auth=self.auth, proxies=self.proxies, timeout=60
    #     )
    #     resp.raise_for_status()
    #     result = resp.json()
    #     if result.get("error"):
    #         raise Exception(result["error"])
    #     return result["result"]

    # def getblockchaininfo(self):
    #     print(f"call getblockchaininfo()")
    #     return self._call("getblockchaininfo")

    # def sendrawtransaction(self, raw_tx_hex, max_fee_rate=0.0):
    #     # Bitcoin Core RPC sendrawtransaction takes an optional maxfeerate.
    #     # Setting to 0.0 means no limit.
    #     print(f"call sendrawtransactiont: {raw_tx_hex}")
    #     return self._call("sendrawtransaction", [raw_tx_hex, max_fee_rate])
