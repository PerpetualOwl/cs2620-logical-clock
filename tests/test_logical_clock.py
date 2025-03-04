import unittest
import sys
import os
import time
import threading
import socket
import queue
from unittest.mock import patch, MagicMock

# Add parent directory to path to import logical_clock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logical_clock import VirtualMachine

class TestVirtualMachine(unittest.TestCase):
    def setUp(self):
        # Create a mock logger
        self.mock_logger = MagicMock()
        
        # Patch the socket and threading modules
        self.socket_patcher = patch('logical_clock.socket')
        self.threading_patcher = patch('logical_clock.threading')
        
        self.mock_socket = self.socket_patcher.start()
        self.mock_threading = self.threading_patcher.start()
        
        # Set up mock socket server
        self.mock_server_socket = MagicMock()
        self.mock_socket.socket.return_value = self.mock_server_socket
        
        # Create a virtual machine for testing
        with patch('logical_clock.logging'):
            self.vm = VirtualMachine(0, 1, 8000, [8001, 8002])
            self.vm.logger = self.mock_logger
            self.vm.peers = [MagicMock(), MagicMock()]
    
    def tearDown(self):
        self.socket_patcher.stop()
        self.threading_patcher.stop()
    
    def test_initialization(self):
        """Test that the virtual machine initializes correctly"""
        self.assertEqual(self.vm.machine_id, 0)
        self.assertEqual(self.vm.clock_rate, 1)
        self.assertEqual(self.vm.port, 8000)
        self.assertEqual(self.vm.peer_ports, [8001, 8002])
        self.assertEqual(self.vm.logical_clock, 0)
        self.assertIsInstance(self.vm.message_queue, queue.Queue)
        self.assertFalse(self.vm.running)
    
    def test_process_internal_event(self):
        """Test that internal events increment the logical clock"""
        initial_clock = self.vm.logical_clock
        self.vm.process_internal_event()
        self.assertEqual(self.vm.logical_clock, initial_clock + 1)
        self.mock_logger.info.assert_called_once()
    
    def test_process_message(self):
        """Test that processing a message updates the logical clock correctly"""
        # Add a message to the queue
        self.vm.message_queue.put(5)
        self.vm.logical_clock = 3
        
        # Process the message
        result = self.vm.process_message()
        
        # Check that the logical clock was updated correctly
        self.assertTrue(result)
        self.assertEqual(self.vm.logical_clock, 6)  # max(3, 5) + 1
        self.mock_logger.info.assert_called_once()
    
    def test_process_message_empty_queue(self):
        """Test that processing an empty queue returns False"""
        initial_clock = self.vm.logical_clock
        result = self.vm.process_message()
        self.assertFalse(result)
        self.assertEqual(self.vm.logical_clock, initial_clock)
        self.mock_logger.info.assert_not_called()
    
    def test_send_message(self):
        """Test that sending a message increments the logical clock"""
        initial_clock = self.vm.logical_clock
        self.vm.send_message()
        self.assertEqual(self.vm.logical_clock, initial_clock + 1)
        
        # Check that the message was sent to all peers
        for peer in self.vm.peers:
            peer.sendall.assert_called_once()
        
        self.mock_logger.info.assert_called_once()
    
    def test_send_message_to_specific_peer(self):
        """Test that sending a message to a specific peer works"""
        initial_clock = self.vm.logical_clock
        self.vm.send_message([0])  # Send to first peer only
        self.assertEqual(self.vm.logical_clock, initial_clock + 1)
        
        # Check that the message was sent to the first peer only
        self.vm.peers[0].sendall.assert_called_once()
        self.vm.peers[1].sendall.assert_not_called()
        
        self.mock_logger.info.assert_called_once()
    
    def test_internal_event_probability(self):
        """Test that the internal event probability is set correctly"""
        # Test default probability
        self.assertAlmostEqual(self.vm.internal_event_prob, 0.7)
        
        # Test with environment variable
        with patch.dict('os.environ', {'INTERNAL_EVENT_PROB': '0.5'}):
            vm = VirtualMachine(0, 1, 8000, [8001, 8002])
            self.assertAlmostEqual(vm.internal_event_prob, 0.5)

if __name__ == '__main__':
    unittest.main() 