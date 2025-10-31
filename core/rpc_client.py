from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import requests
import time

class BitcoinRPCClient:
    def __init__(self, config: dict):
        self.config = config
        self.rpc = None
        self.connect()  # Establish connection on initialization

    def connect(self):
        """Connects to Bitcoin Core RPC using the provided config dictionary."""
        print("Connecting to Bitcoin RPC...")
        url = f"http://{self.config['user']}:{self.config['password']}@{self.config['host']}:{int(self.config['port'])}"
        
        self.rpc = AuthServiceProxy(url)
        
        # Test connection
        try:
            info = self.rpc.getblockchaininfo()
            print(f"Connected to Bitcoin Core chain: {info['chain']}")
        except JSONRPCException as e:
            print(f"Error connecting to Bitcoin Core: {e.error['message']}")
            self.rpc = None  # Invalidate the connection on failure
            raise

    def safe_rpc_call(self, method_name: str, *args, retries: int = 3, delay: int = 5):
        """Handles RPC calls with automatic connection retry and re-establishment logic."""
        print("Attempting RPC call...")
        for i in range(retries):
            print(f"RPC connection status: {self.rpc}")
            try:
                if self.rpc is None:
                    print("Reconnecting to RPC...")
                    self.connect()  # Re-establish connection if it's lost
                
                print(f"Executing RPC method: {method_name} (Attempt {i + 1}/{retries})")
                method_to_call = getattr(self.rpc, method_name)
                return method_to_call(*args)

            except (BrokenPipeError, ConnectionError, IOError) as e:
                print(f"Connection error detected: {e}")
                self.rpc = None  # Invalidate the current connection
                if i < retries - 1:
                    print(f"Retrying connection in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Max retries reached. Failing...")
                    raise  # Re-raise the exception after exhausting retries

            except JSONRPCException as e:
                print(f"Bitcoind RPC error: {e.error['message']}")
                raise  # Do not retry on RPC logic errors

    def broadcast_transaction_via_rpc(self, raw_tx_hex: str):
        """
        Broadcasts a raw transaction hex via Bitcoin Core RPC sendrawtransaction.
        Returns (txid, None) on success or (None, error_message) on failure.
        """
        print(f"Calling broadcast_transaction_via_rpc: raw_tx_hex: {raw_tx_hex}")
        if self.rpc is None:
            return None, "No RPC connection"
        
        try:
            txid = self.safe_rpc_call("sendrawtransaction", raw_tx_hex, 0.0)  # Pass 0.0 for no fee rate limit
            print(f"Transaction ID received: {txid}")
            return txid, None
        except JSONRPCException as e:
            msg = e.error.get("message", str(e))
            print(f"JSONRPCException: {msg}")
            return None, msg
        except requests.exceptions.RequestException as e:
            print(f"RequestException: {str(e)}")
            return None, str(e)
        except Exception as e:
            print(f"General Exception: {str(e)}")
            return None, str(e)
