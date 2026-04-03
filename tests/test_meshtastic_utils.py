#!/usr/bin/env python3
"""
Tests for BTCMesh Meshtastic Utilities (core/meshtastic_utils.py).

Tests device scanning, node information retrieval, and formatting functions.
"""
import sys
import unittest
import unittest.mock
import time


class TestScanMeshtasticDevices(unittest.TestCase):
    """Tests for scan_meshtastic_devices function."""

    def test_scan_meshtastic_devices_exists(self):
        """Given meshtastic_utils module, Then scan_meshtastic_devices should be defined."""
        from core.meshtastic_utils import scan_meshtastic_devices
        self.assertTrue(callable(scan_meshtastic_devices))

    def test_scan_returns_list(self):
        """Given scan_meshtastic_devices call, Then it returns a list."""
        from core.meshtastic_utils import scan_meshtastic_devices
        result = scan_meshtastic_devices()
        self.assertIsInstance(result, list)

    def test_scan_returns_empty_when_meshtastic_not_installed(self):
        """Given meshtastic not installed, Then returns empty list."""
        from core.meshtastic_utils import scan_meshtastic_devices

        with unittest.mock.patch.dict(sys.modules, {'meshtastic': None, 'meshtastic.util': None}):
            # Force reimport
            import importlib
            import core.meshtastic_utils
            importlib.reload(core.meshtastic_utils)
            result = core.meshtastic_utils.scan_meshtastic_devices()
            self.assertEqual(result, [])

    def test_scan_returns_ports_when_found(self):
        """Given meshtastic finds ports, Then returns port list."""
        from core import meshtastic_utils

        mock_util = unittest.mock.MagicMock()
        mock_util.findPorts.return_value = ['/dev/ttyUSB0', '/dev/ttyACM0']

        with unittest.mock.patch.dict(sys.modules, {'meshtastic.util': mock_util}):
            result = meshtastic_utils.scan_meshtastic_devices()
            self.assertEqual(result, ['/dev/ttyUSB0', '/dev/ttyACM0'])


class TestGetOwnNodeId(unittest.TestCase):
    """Tests for get_own_node_id function."""

    def test_get_own_node_id_exists(self):
        """Given meshtastic_utils module, Then get_own_node_id should be defined."""
        from core.meshtastic_utils import get_own_node_id
        self.assertTrue(callable(get_own_node_id))

    def test_returns_none_for_none_iface(self):
        """Given None interface, Then returns None."""
        from core.meshtastic_utils import get_own_node_id
        result = get_own_node_id(None)
        self.assertIsNone(result)

    def test_returns_none_when_no_myinfo(self):
        """Given interface with no myInfo, Then returns None."""
        from core.meshtastic_utils import get_own_node_id

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo = None

        result = get_own_node_id(mock_iface)
        self.assertIsNone(result)

    def test_returns_formatted_node_id(self):
        """Given valid interface, Then returns formatted node ID."""
        from core.meshtastic_utils import get_own_node_id

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo.my_node_num = 0xABCD1234

        result = get_own_node_id(mock_iface)
        self.assertEqual(result, '!abcd1234')

    def test_returns_zero_padded_node_id(self):
        """Given small node number, Then returns zero-padded 8-char hex."""
        from core.meshtastic_utils import get_own_node_id

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo.my_node_num = 0x1234

        result = get_own_node_id(mock_iface)
        self.assertEqual(result, '!00001234')


class TestGetOwnNodeName(unittest.TestCase):
    """Tests for get_own_node_name function."""

    def test_get_own_node_name_exists(self):
        """Given meshtastic_utils module, Then get_own_node_name should be defined."""
        from core.meshtastic_utils import get_own_node_name
        self.assertTrue(callable(get_own_node_name))

    def test_returns_none_for_none_iface(self):
        """Given None interface, Then returns None."""
        from core.meshtastic_utils import get_own_node_name
        result = get_own_node_name(None)
        self.assertIsNone(result)

    def test_returns_none_when_no_myinfo(self):
        """Given interface with no myInfo, Then returns None."""
        from core.meshtastic_utils import get_own_node_name

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo = None

        result = get_own_node_name(mock_iface)
        self.assertIsNone(result)

    def test_returns_long_name(self):
        """Given node with longName, Then returns longName."""
        from core.meshtastic_utils import get_own_node_name

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo.my_node_num = 0xABCD1234
        mock_iface.nodes = {
            '!abcd1234': {
                'user': {
                    'longName': 'My Device',
                    'shortName': 'MD'
                }
            }
        }

        result = get_own_node_name(mock_iface)
        self.assertEqual(result, 'My Device')

    def test_returns_short_name_as_fallback(self):
        """Given node with only shortName, Then returns shortName."""
        from core.meshtastic_utils import get_own_node_name

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo.my_node_num = 0xABCD1234
        mock_iface.nodes = {
            '!abcd1234': {
                'user': {
                    'longName': '',
                    'shortName': 'MD'
                }
            }
        }

        result = get_own_node_name(mock_iface)
        self.assertEqual(result, 'MD')

    def test_returns_none_when_no_name(self):
        """Given node with no name, Then returns None."""
        from core.meshtastic_utils import get_own_node_name

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo.my_node_num = 0xABCD1234
        mock_iface.nodes = {
            '!abcd1234': {
                'user': {
                    'longName': '',
                    'shortName': ''
                }
            }
        }

        result = get_own_node_name(mock_iface)
        self.assertIsNone(result)


class TestGetKnownNodes(unittest.TestCase):
    """Tests for get_known_nodes function."""

    def test_get_known_nodes_exists(self):
        """Given meshtastic_utils module, Then get_known_nodes should be defined."""
        from core.meshtastic_utils import get_known_nodes
        self.assertTrue(callable(get_known_nodes))

    def test_returns_empty_for_none_iface(self):
        """Given None interface, Then returns empty list."""
        from core.meshtastic_utils import get_known_nodes
        result = get_known_nodes(None)
        self.assertEqual(result, [])

    def test_returns_empty_when_no_nodes(self):
        """Given interface with no nodes, Then returns empty list."""
        from core.meshtastic_utils import get_known_nodes

        mock_iface = unittest.mock.MagicMock()
        mock_iface.nodes = None

        result = get_known_nodes(mock_iface)
        self.assertEqual(result, [])

    def test_excludes_own_node_by_default(self):
        """Given nodes including own, Then excludes own node."""
        from core.meshtastic_utils import get_known_nodes

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo.my_node_num = 0xABCD1234
        mock_iface.nodes = {
            '!abcd1234': {'user': {'longName': 'Own Node'}},
            '!11111111': {'user': {'longName': 'Other Node'}},
        }

        result = get_known_nodes(mock_iface)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '!11111111')

    def test_includes_own_node_when_exclude_false(self):
        """Given exclude_own=False, Then includes own node."""
        from core.meshtastic_utils import get_known_nodes

        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo.my_node_num = 0xABCD1234
        mock_iface.nodes = {
            '!abcd1234': {'user': {'longName': 'Own Node'}},
            '!11111111': {'user': {'longName': 'Other Node'}},
        }

        result = get_known_nodes(mock_iface, exclude_own=False)
        self.assertEqual(len(result), 2)

    def test_sorts_by_last_heard_descending(self):
        """Given nodes with different lastHeard, Then sorts descending."""
        from core.meshtastic_utils import get_known_nodes

        now = int(time.time())
        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo = None
        mock_iface.nodes = {
            '!11111111': {'user': {'longName': 'Old Node'}, 'lastHeard': now - 1000},
            '!22222222': {'user': {'longName': 'New Node'}, 'lastHeard': now - 10},
            '!33333333': {'user': {'longName': 'Middle Node'}, 'lastHeard': now - 500},
        }

        result = get_known_nodes(mock_iface)
        self.assertEqual(result[0]['id'], '!22222222')  # Most recent
        self.assertEqual(result[1]['id'], '!33333333')  # Middle
        self.assertEqual(result[2]['id'], '!11111111')  # Oldest

    def test_returns_node_info(self):
        """Given nodes, Then returns node info dict."""
        from core.meshtastic_utils import get_known_nodes

        now = int(time.time())
        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo = None
        mock_iface.nodes = {
            '!11111111': {
                'user': {'longName': 'Test Node', 'shortName': 'TN'},
                'lastHeard': now - 100
            },
        }

        result = get_known_nodes(mock_iface)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], '!11111111')
        self.assertEqual(result[0]['name'], 'Test Node')
        self.assertEqual(result[0]['lastHeard'], now - 100)
        self.assertTrue(result[0]['is_recent'])  # Within 24 hours

    def test_is_recent_false_for_old_nodes(self):
        """Given node not heard in 24+ hours, Then is_recent is False."""
        from core.meshtastic_utils import get_known_nodes

        now = int(time.time())
        mock_iface = unittest.mock.MagicMock()
        mock_iface.myInfo = None
        mock_iface.nodes = {
            '!11111111': {
                'user': {'longName': 'Old Node'},
                'lastHeard': now - (25 * 60 * 60)  # 25 hours ago
            },
        }

        result = get_known_nodes(mock_iface)
        self.assertFalse(result[0]['is_recent'])


class TestFormatNodeDisplay(unittest.TestCase):
    """Tests for format_node_display function."""

    def test_format_node_display_exists(self):
        """Given meshtastic_utils module, Then format_node_display should be defined."""
        from core.meshtastic_utils import format_node_display
        self.assertTrue(callable(format_node_display))

    def test_formats_correctly(self):
        """Given node dict, Then returns 'Name (!nodeid)'."""
        from core.meshtastic_utils import format_node_display

        node = {'id': '!abcd1234', 'name': 'TestNode', 'lastHeard': 0, 'is_recent': False}
        result = format_node_display(node)
        self.assertEqual(result, 'TestNode (!abcd1234)')

    def test_handles_spaces_in_name(self):
        """Given node with spaces in name, Then formats correctly."""
        from core.meshtastic_utils import format_node_display

        node = {'id': '!12345678', 'name': 'My Test Node', 'lastHeard': 0, 'is_recent': False}
        result = format_node_display(node)
        self.assertEqual(result, 'My Test Node (!12345678)')


class TestGetNodeById(unittest.TestCase):
    """Tests for get_node_by_id function."""

    def test_get_node_by_id_exists(self):
        """Given meshtastic_utils module, Then get_node_by_id should be defined."""
        from core.meshtastic_utils import get_node_by_id
        self.assertTrue(callable(get_node_by_id))

    def test_returns_none_for_none_iface(self):
        """Given None interface, Then returns None."""
        from core.meshtastic_utils import get_node_by_id
        result = get_node_by_id(None, '!abcd1234')
        self.assertIsNone(result)

    def test_returns_none_when_node_not_found(self):
        """Given node ID not in nodes, Then returns None."""
        from core.meshtastic_utils import get_node_by_id

        mock_iface = unittest.mock.MagicMock()
        mock_iface.nodes = {'!11111111': {'user': {'longName': 'Other'}}}

        result = get_node_by_id(mock_iface, '!abcd1234')
        self.assertIsNone(result)

    def test_returns_node_info(self):
        """Given valid node ID, Then returns node info dict."""
        from core.meshtastic_utils import get_node_by_id

        mock_iface = unittest.mock.MagicMock()
        mock_iface.nodes = {
            '!abcd1234': {
                'user': {'longName': 'Test Node', 'shortName': 'TN'},
                'lastHeard': 12345
            }
        }

        result = get_node_by_id(mock_iface, '!abcd1234')
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], '!abcd1234')
        self.assertEqual(result['name'], 'Test Node')
        self.assertEqual(result['longName'], 'Test Node')
        self.assertEqual(result['shortName'], 'TN')
        self.assertEqual(result['lastHeard'], 12345)


if __name__ == '__main__':
    unittest.main()
