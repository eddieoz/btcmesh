# BTC Mesh Relay

## Description

BTC Mesh Relay is a project designed to enable the broadcasting of Bitcoin raw transactions by sending them as chunked hexadecimal strings via LoRa Meshtastic direct messages. A dedicated client script (`btcmesh_cli.py`) will be used for sending, and a relay device running `btcmesh_server.py` will reassemble these chunks, decode, validate, and then relay the complete transaction to a configured Bitcoin RPC node. This system is intended for scenarios with limited or censored internet access but where LoRa Meshtastic network availability exists.

This project is currently under development.

## Features (Planned & In-Progress)

*   **Meshtastic Communication**: Initializes and manages communication with a Meshtastic device.
*   **Transaction Chunking & Reassembly**: Allows large Bitcoin transactions to be sent in smaller chunks over LoRa by `btcmesh_cli.py` and reassembled by `btcmesh_server.py`.
*   **Payload Handling**: Relay server reassembles hexadecimal chunks. The connected Bitcoin Core node performs full transaction validation upon broadcast attempt. (Advanced pre-broadcast decoding and validation capabilities on the relay server via `core/transaction_parser.py` are planned for future enhancements).
*   **Basic Transaction Validation**: Currently, the relay server relies on the connected Bitcoin Core node for most transaction validation. (More extensive pre-broadcast sanity checks on the relay are planned).
*   **Bitcoin RPC Integration**: Connects to a Bitcoin Core RPC node to broadcast the validated raw transaction.
*   **Logging**: Comprehensive logging for both server and client operations.
*   **Client Script (`btcmesh_cli.py`)**: Implemented command-line tool (`btcmesh_cli.py`) for users to send raw transactions.
*   **TOR**: Optionally relay the transaction to a node running inside Tor network. (onion server)

## Project Structure

```
btcmesh/
├── btcmesh_cli.py         # Client script
├── btcmesh_server.py      # Server/Relay script
├── core/                  # Core logic for the server/relay
│   ├── __init__.py
│   ├── config_loader.py   # For loading .env and other configurations
│   ├── logger_setup.py    # For setting up consistent logging
│   ├── transaction_parser.py # For decoding raw Bitcoin transactions (Planned)
│   ├── rpc_client.py      # For interacting with Bitcoin RPC
│   └── reassembler.py     # For reassembling chunked messages
├── project/               # Project planning documents
│   ├── tasks.txt
│   └── reference_materials.md
├── logs/                  # Directory for log files (created at runtime)
├── tests/                 # Unit and integration tests
├── .env.example           # Example environment variable configuration file
├── requirements.txt       # Python dependencies
└── README.md              # This file
```
(Refer to `project/tasks.txt` for detailed ongoing tasks and user stories.)

## Setup Instructions

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/eddieoz/btcmesh.git
    cd btcmesh
    ```

2.  **Create and Activate Conda Environment**:
    It's recommended to use a Conda environment. If you don't have Conda, please [install it first](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html).
    ```bash
    conda create -n btcmesh python=3.11
    conda activate btcmesh
    ```
    Or use venv
    ```bash
    python -m venv env
    source env/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment (.env)**:
    The application is configured using a `.env` file in the project root.
    Copy the example file to create your own configuration:
    ```bash
    cp .env-example .env
    ```
    Then, edit the `.env` file to set your specific configurations. For example:

    *   **`MESHTASTIC_SERIAL_PORT`**: Specifies the serial port for your Meshtastic device (e.g., `/dev/ttyUSB0`, `/dev/ttyACM0` on Linux, or `COM3` on Windows). If this is not set or is commented out, the application will attempt to auto-detect the Meshtastic device.
        ```env
        # MESHTASTIC_SERIAL_PORT=/dev/your/meshtastic_port
        ```
    *   **Bitcoin RPC Node Details**: Required for the relay server (`btcmesh_server.py`).
        ```env
        BITCOIN_RPC_HOST=your_bitcoin_node_host
        BITCOIN_RPC_PORT=your_bitcoin_node_port # e.g., 8332 for mainnet
        BITCOIN_RPC_USER=your_rpc_username
        BITCOIN_RPC_PASSWORD=your_rpc_password
        # Optional: For transaction reassembly timeout
        # REASSEMBLY_TIMEOUT_SECONDS=120
        ```
    *   **Connecting via Tor**: If you wish to connect to your Bitcoin RPC node via Tor, simply set the `BITCOIN_RPC_HOST` to your node's `.onion` address. The application will automatically detect this and manage the Tor connection using the Tor binary provided in the `tor/` directory of this project. You do not need to have Tor installed or running separately on your system. 
        ```env
        # Example for Tor connection:
        # BITCOIN_RPC_HOST=yourbitcoinrpcnode.onion
    
    **OBS** The TOR binary supplied is part of the Debian package. REPLACE it to make it compatible with your distribution. [DOWNLOAD TOR](https://www.torproject.org/download/)
        ```

5.  **Meshtastic Device Setup**:
    *   Ensure you have a Meshtastic device connected to the machine where `btcmesh_server.py` will run (and another for the client when `btcmesh_cli.py` is used).
    *   The Meshtastic Python library, by default, attempts to auto-detect your device. You can specify the serial port explicitly by setting `MESHTASTIC_SERIAL_PORT` in your `.env` file.
    *   Ensure your Bitcoin Core node is configured to accept RPC connections.
    *   Configure the RPC host, port, user, and password in your `.env` file (see step 4).
    *   **Tor Connectivity**: If `BITCOIN_RPC_HOST` is a `.onion` address, the script will automatically attempt to establish a connection through Tor using the bundled Tor executable (`./tor/tor`). No separate Tor installation or configuration is required by the user.

## Configuration

The primary method for configuration is via a `.env` file in the project root (see "Configure Environment (.env)" in Setup Instructions).

Key settings configurable in `.env`:

*   Meshtastic device serial port (`MESHTASTIC_SERIAL_PORT`).
*   Bitcoin RPC connection details (`BITCOIN_RPC_HOST`, `BITCOIN_RPC_PORT`, `BITCOIN_RPC_USER`, `BITCOIN_RPC_PASSWORD`). This includes the ability to use a `.onion` address for `BITCOIN_RPC_HOST` to automatically route traffic through Tor using the project's bundled Tor executable.
*   Transaction reassembly timeout (`REASSEMBLY_TIMEOUT_SECONDS`).

## Running the Server (`btcmesh_server.py`)

Once set up and configured, you can run the BTC Mesh Relay server:

```bash
python btcmesh_server.py
```

The server will initialize the Meshtastic interface, connect to the Bitcoin RPC node (if configured), and start listening for incoming messages.

## Running the Client (`btcmesh_cli.py`)

The client script is used to send a raw Bitcoin transaction to a relay server.

```bash
python btcmesh_cli.py --destination <SERVER_NODE_ID> --tx <RAW_TRANSACTION_HEX>
```
Replace `<SERVER_NODE_ID>` with the Meshtastic node ID of the machine running `btcmesh_server.py` (e.g., `!abcdef12`) and `<RAW_TRANSACTION_HEX>` with the full raw transaction hex string you intend to broadcast.

Use `python btcmesh_cli.py --help` for more options, such as `--dry-run` to simulate sending without actually transmitting over LoRa.

## Running Tests

To run the automated tests:

```bash
python -m unittest discover -s tests -p 'test_*.py'
```

## Contributing

Contributions are welcome! Please refer to the project's issue tracker and development plan in `project/tasks.txt`. Follow TDD/BDD principles when adding new features or fixing bugs. 

## License

This project is licensed under the MIT License.

## Buy me a coffee
Did you like it? [Buy me a coffee](https://www.buymeacoffee.com/eddieoz)

[![Buy me a coffee](https://ipfs.io/ipfs/QmR6W4L3XiozMQc3EjfFeqSkcbu3cWnhZBn38z2W2FuTMZ?filename=buymeacoffee.webp)](https://www.buymeacoffee.com/eddieoz)

Or drop me a tip through Lightning Network: ⚡ [getalby.com/p/eddieoz](https://getalby.com/p/eddieoz)
