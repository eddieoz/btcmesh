#!/usr/bin/env python3
"""
BTCMesh Meshtastic Utilities - Shared utilities for working with Meshtastic devices.

This module provides device scanning, node information retrieval, and formatting
functions used by CLI, GUI, and server components.
"""
from typing import Optional, List, Dict


def scan_meshtastic_devices() -> List[str]:
    """Scan for available Meshtastic devices.

    Returns:
        List of device paths (e.g., ['/dev/ttyUSB0', '/dev/ttyACM0']).
        Returns empty list if no devices found or meshtastic not installed.
    """
    try:
        from meshtastic.util import findPorts
        ports = findPorts(True)  # eliminate_duplicates=True
        return ports if ports else []
    except ImportError:
        return []
    except Exception:
        return []


def get_own_node_id(iface) -> Optional[str]:
    """Get the node ID of the connected Meshtastic device.

    Args:
        iface: Meshtastic interface with myInfo attribute

    Returns:
        Node ID string (e.g., '!abcd1234') or None if not connected.
    """
    if not iface or not iface.myInfo:
        return None
    try:
        node_num = iface.myInfo.my_node_num
        return f"!{node_num:08x}"
    except (AttributeError, TypeError):
        return None


def get_own_node_name(iface) -> Optional[str]:
    """Get the name of the connected device's own node.

    Args:
        iface: Meshtastic interface with nodes dictionary and myInfo

    Returns:
        The node's longName or shortName, or None if not available.
    """
    if not iface or not iface.myInfo:
        return None

    try:
        own_node_num = iface.myInfo.my_node_num
        own_node_id = f"!{own_node_num:08x}"

        if not iface.nodes or own_node_id not in iface.nodes:
            return None

        node_data = iface.nodes[own_node_id]
        user = node_data.get('user', {}) if isinstance(node_data, dict) else {}
        long_name = user.get('longName', '') if isinstance(user, dict) else ''
        short_name = user.get('shortName', '') if isinstance(user, dict) else ''

        name = long_name or short_name
        return name if name else None
    except (AttributeError, TypeError, KeyError):
        return None


def get_known_nodes(iface, exclude_own: bool = True) -> List[Dict]:
    """Get list of known nodes from a Meshtastic interface.

    Args:
        iface: Meshtastic interface with nodes dictionary
        exclude_own: Whether to exclude the device's own node (default True)

    Returns:
        List of dicts with keys: id, name, lastHeard, is_recent
        Sorted by lastHeard descending (most recent first).
    """
    import time

    if not iface or not iface.nodes:
        return []

    # Get own node number to filter out
    own_node_num = None
    if exclude_own and iface.myInfo:
        own_node_num = iface.myInfo.my_node_num

    nodes = []
    now = int(time.time())
    hours_24 = 24 * 60 * 60

    for node_id, node_data in iface.nodes.items():
        # Skip own node by comparing node_id hex to own_node_num
        if own_node_num is not None:
            try:
                node_num = int(node_id.lstrip('!'), 16)
                if node_num == own_node_num:
                    continue
            except (ValueError, AttributeError):
                pass

        # Extract user info
        user = node_data.get('user', {}) if isinstance(node_data, dict) else {}
        long_name = user.get('longName', '') if isinstance(user, dict) else ''
        short_name = user.get('shortName', '') if isinstance(user, dict) else ''

        # Use longName, or shortName, or node_id as fallback
        name = long_name or short_name or node_id

        # Get lastHeard timestamp
        last_heard = node_data.get('lastHeard', 0) if isinstance(node_data, dict) else 0

        # Determine if node was seen in last 24 hours
        is_recent = (now - last_heard) < hours_24 if last_heard else False

        nodes.append({
            'id': node_id,
            'name': name,
            'lastHeard': last_heard,
            'is_recent': is_recent,
        })

    # Sort by lastHeard descending (most recent first)
    nodes.sort(key=lambda n: n['lastHeard'], reverse=True)

    return nodes


def format_node_display(node: Dict) -> str:
    """Format a node dict for display in a dropdown or list.

    Args:
        node: Dict with keys: id, name, lastHeard, is_recent

    Returns:
        Formatted string: 'Name (!nodeid)'
    """
    return f"{node['name']} ({node['id']})"


def get_node_by_id(iface, node_id: str) -> Optional[Dict]:
    """Get a specific node's information by its ID.

    Args:
        iface: Meshtastic interface with nodes dictionary
        node_id: The node ID to look up (e.g., '!abcd1234')

    Returns:
        Dict with node information or None if not found.
    """
    if not iface or not iface.nodes:
        return None

    node_data = iface.nodes.get(node_id)
    if not node_data:
        return None

    user = node_data.get('user', {}) if isinstance(node_data, dict) else {}
    long_name = user.get('longName', '') if isinstance(user, dict) else ''
    short_name = user.get('shortName', '') if isinstance(user, dict) else ''

    return {
        'id': node_id,
        'name': long_name or short_name or node_id,
        'longName': long_name,
        'shortName': short_name,
        'lastHeard': node_data.get('lastHeard', 0) if isinstance(node_data, dict) else 0,
    }
