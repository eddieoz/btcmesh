import requests
import json
import time

class BitcoinRPCClient:
    class BitcoinRPCException(Exception):
        def __init__(self, error_info):
            self.code = error_info.get('code', 'Unknown code')
            self.message = error_info.get('message', 'Unknown error')
            super().__init__(self.message)

        def __str__(self):
            return '%d: %s' % (self.code, self.message)

        def __repr__(self):
            return '<%s \'%s\'>' % (self.__class__.__name__, self)

    def __init__(self, config: dict):
        user = config['user']
        password = config['password']
        host = config['host']
        port = config['port']
        self.uri = f"http://{user}:{password}@{host}:{port}"
        self.use_tor = host.endswith(".onion")
        self.connect()  # Establish connection on initialization

    def connect(self):
        """Connects to Bitcoin Core RPC using the provided config dictionary."""
        print("Connecting to Bitcoin RPC...")
        
        # Test connection
        try:
            info = self.getblockchaininfo()
            print(f"Connected to Bitcoin Core chain: {info['chain']}")
            if info.get("error"):
                raise self.BitcoinRPCException(info["error"])
        except Exception as e:
                print(f"Error connecting to Bitcoin Core RPC: {e}")

    def rpc_request(self, method, params=None, retries: int = 3, delay: int = 5):
        """Performs a JSON-RPC requests with automatic connection retry logic."""
        if self.use_tor:
            proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
        else:
            proxies = {}

        if params is None:
            params = []
        
        headers = {'Content-Type': 'application/json'}
        payload = {
            "jsonrpc": "1.0",
            "id": "btcmesh",
            "method": method,
            "params": params
        }

        for i in range(retries):
            try:
                print(f"Executing RPC method: {method} (Attempt {i + 1}/{retries})")
                response = requests.post(self.uri, data=json.dumps(payload), headers=headers, proxies=proxies, timeout=30)
                # response.raise_for_status()  # Raise an HTTPError for bad responses
                result = response.json()
                if result.get("error"):
                    raise self.BitcoinRPCException(result["error"])
                return result["result"]
            except (BrokenPipeError, ConnectionError, IOError) as e:
                print(f"Connection error detected: {e}")
                if i < retries - 1:
                    print(f"Retrying connection in {delay} seconds...")
                    time.sleep(delay)
                else:
                    print("Max retries reached. Failing...")
                    raise  # Re-raise the exception after exhausting retries
            # except Exception as e:
            #     if e['message']:
            #         print(f"Bitcoind RPC error: {e['message']}")
            #     else:
            #         print(f"Bitcoind RPC error:: {e}")
            #     raise  # Do not retry on RPC logic errors
                

    def getblockchaininfo(self):
        return self.rpc_request("getblockchaininfo")
        
    def sendrawtransaction(self, raw_tx_hex, max_fee_rate=0.0):
        # Bitcoin Core RPC sendrawtransaction takes an optional maxfeerate.
        # Setting to 0.0 means no limit.
        return self.rpc_request("sendrawtransaction", [raw_tx_hex, max_fee_rate])
    
    def broadcast_transaction(self, raw_tx_hex: str):
        """
        Broadcasts a raw transaction hex via Bitcoin Core RPC sendrawtransaction.
        Returns (txid, None) on success or (None, error_message) on failure.
        """
        print(f"Calling broadcast_transaction_via_rpc: raw_tx_hex: {raw_tx_hex}")
        
        try:
            txid = self.sendrawtransaction(raw_tx_hex, 0.0)  # Pass 0.0 for no fee rate limit
            print(f"Transaction ID received: {txid}")
            return txid, None
        except self.BitcoinRPCException as e:
            message = e.message
            print(f"Caught an RPC error with code {e.code}: {e.message}")
            return None, message
        except requests.exceptions.RequestException as e:
            print(f"RequestException: {str(e)}")
            return None, str(e)
        except Exception as e:
            print(f"General Exception: {str(e)}")
            return None, str(e)
