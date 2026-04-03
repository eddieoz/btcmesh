import sys
import os

# Adjust the path to include the project root if
# test_bitcoin_connection.py is in the root
# and core module is in a subdirectory.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from core.config_loader import load_app_config, load_bitcoin_rpc_config
    from core.rpc_client import BitcoinRPCClient

    # # Import Tor management functions and SOCKS port from btcmesh_server
    # from btcmesh_server import TOR_SOCKS_PORT, start_tor, stop_tor
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print(
        "Please ensure that test_bitcoin_connection.py is in the project root "
        "directory, and the 'core' and 'btcmesh_server.py' are accessible."
    )
    sys.exit(1)

# Example raw transaction hex provided by the user
EXAMPLE_RAW_TX = (
    "0200000000010159b52f5572ff75df2b0dfad1fc9a1eae87dd5d0750ba59133a959b934c3b14500100000000fdffffff0200000000000000003d6a3b6261666b726569656a35687178786e326474677663356a66796574616661716472667a34746a7068626177616665786e7a776c746f6a347a366b34a01e0f0000000000160014214f6d2205bf13114220eefaf1721c1b1715453f02473044022038ee60a21dd309cd67445cad011ddad298ddab3171ee44be6fbb10f1d63d4fcd02207d4fa4cb95a91ac601a0d77c56478c4a95faf395835d27755fa0255ccd22e0bd0121027e47a3a758f2d90b2f824cd90d58183711d00b464aa15c821e6613b97e7117c4afa70d00"
)


def main():
    print("Starting Bitcoin node connection test...")
    print("\nStep 1: Loading application configuration (for .env)...")
    try:
        load_app_config()
        print("Application configuration loaded.")
    except Exception as e:
        print(f"Failed to load application configuration: {e}")
        sys.exit(1)

    print("\nStep 2: Loading Bitcoin RPC configuration...")
    rpc_config = None
    try:
        rpc_config = load_bitcoin_rpc_config()
        print(
            f"Bitcoin RPC config loaded: Host={rpc_config['host']}, "
            f"Port={rpc_config['port']}, User={rpc_config['user']}"
        )
    except ValueError as e:
        print(f"Failed to load Bitcoin RPC configuration: {e}")
        print(
            "Please ensure BITCOIN_RPC_HOST, _PORT, _USER, and _PASSWORD "
            "are correctly set in your .env file."
        )
        sys.exit(1)
    except Exception as e:
        print(
            "An unexpected error occurred while loading Bitcoin RPC "
            f"configuration: {e}"
        )
        sys.exit(1)

    # Check for .onion address and start Tor if needed
    if rpc_config["host"].endswith(".onion"):
        print(
            f"Detected .onion address ({rpc_config['host']}). "
            "Attempting to start Tor..."
        )

        print("\nStep 3: Attempting to connect to Bitcoin Core RPC node...")
        rpc = None
        try:
            rpc = BitcoinRPCClient(rpc_config)
            print("Successfully initiated connection object.")
        except Exception as e:
            print(
                "Failed to establish connection with Bitcoin Core RPC node: " f"{e}")
            print(
                "Check your Bitcoin node's status, RPC settings, and network "
                "connectivity."
            )
            if rpc.use_tor:
                print(
                    "Also, verify Tor is working correctly if a .onion "
                    "address is used."
                )
            sys.exit(1)

        print("\nStep 4: Calling getblockchaininfo()...")
        try:
            blockchain_info = rpc.getblockchaininfo()
            print("Successfully called getblockchaininfo(). Response:")
            print(f"  Chain: {blockchain_info.get('chain')}")
            print(f"  Blocks: {blockchain_info.get('blocks')}")
            print(f"  Headers: {blockchain_info.get('headers')}")
            print(
                f"  Verification Progress: "
                f"{blockchain_info.get('verificationprogress')}"
            )
            print(
                f"  Initial Block Download: "
                f"{blockchain_info.get('initialblockdownload')}"
            )
            print("\nBasic connection test successful!")
        except Exception as e:
            print(f"Error calling getblockchaininfo(): {e}")
            print("The connection object was created, but an RPC command failed.")
            print(
                "This could indicate an issue with the RPC interface on the "
                "node, permissions, or network issues preventing the "
                "command execution."
            )
            sys.exit(1)

        print("\nStep 5: Attempting to broadcast an example raw transaction...")
        print(
            f"Using raw transaction hex (first 80 chars): " f"{EXAMPLE_RAW_TX[:80]}..."
        )
        try:
            # The sendrawtransaction method in our rpc object
            # (AuthServiceProxy or RequestsBitcoinRPC) from core.rpc_client
            # was updated to accept max_fee_rate as the second argument.
            # We pass 0.0 for no feerate limit.
            txid = rpc.sendrawtransaction(EXAMPLE_RAW_TX, 0.0)
            print(f"Successfully broadcast example transaction. TXID: {txid}")
            print("\nRaw transaction broadcast test successful!")
        except Exception as e:
            print(f"Error broadcasting example transaction: {e}")
            print(
                "This could indicate an issue with the transaction itself "
                "(e.g., invalid, already broadcast),"
            )
            print(
                "stricter rules on your Bitcoin node for transaction relay, "
                "or the transaction fee rate."
            )
            # We don't sys.exit(1) here as the primary test
            # (getblockchaininfo) passed. This is an additional diagnostic step.

if __name__ == "__main__":
    main()
