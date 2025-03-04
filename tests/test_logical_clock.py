import unittest
import sys
import os
import time
import threading
import socket
import queue
import logging
from unittest.mock import patch, MagicMock, call, ANY

# Add parent directory to path to import logical_clock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logical_clock import VirtualMachine, start_machine

class TestVirtualMachine(unittest.TestCase):
    def setUp(self):
        # Create a mock logger
        self.mock_logger = MagicMock()
        
        # Patch the socket and threading modules
        self.socket_patcher = patch('logical_clock.socket')
        self.threading_patcher = patch('logical_clock.threading')
        self.time_patcher = patch('logical_clock.time')
        self.random_patcher = patch('logical_clock.random')
        self.datetime_patcher = patch('logical_clock.datetime')
        
        self.mock_socket = self.socket_patcher.start()
        self.mock_threading = self.threading_patcher.start()
        self.mock_time = self.time_patcher.start()
        self.mock_random = self.random_patcher.start()
        self.mock_datetime = self.datetime_patcher.start()
        
        # Set up mock socket server
        self.mock_server_socket = MagicMock()
        self.mock_socket.socket.return_value = self.mock_server_socket
        
        # Mock datetime.now().timestamp()
        self.mock_datetime.now.return_value.timestamp.return_value = 1234567890.0
        
        # Create a virtual machine for testing
        with patch('logical_clock.logging'):
            with patch('logical_clock.os.makedirs'):
                self.vm = VirtualMachine(0, 1, 8000, [8001, 8002])
                self.vm.logger = self.mock_logger
                self.vm.peers = [MagicMock(), MagicMock()]
    
    def tearDown(self):
        self.socket_patcher.stop()
        self.threading_patcher.stop()
        self.time_patcher.stop()
        self.random_patcher.stop()
        self.datetime_patcher.stop()
    
    def test_initialization(self):
        """Test that the virtual machine initializes correctly"""
        self.assertEqual(self.vm.machine_id, 0)
        self.assertEqual(self.vm.clock_rate, 1)
        self.assertEqual(self.vm.port, 8000)
        self.assertEqual(self.vm.peer_ports, [8001, 8002])
        self.assertEqual(self.vm.logical_clock, 0)
        self.assertIsInstance(self.vm.message_queue, queue.Queue)
        self.assertFalse(self.vm.running)
        
        # Test socket initialization
        self.mock_socket.socket.assert_called_once_with(socket.AF_INET, socket.SOCK_STREAM)
        self.mock_server_socket.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.mock_server_socket.bind.assert_called_once_with(('localhost', 8000))
        self.mock_server_socket.listen.assert_called_once_with(5)
    
    def test_process_internal_event(self):
        """Test that internal events increment the logical clock"""
        initial_clock = self.vm.logical_clock
        self.vm.process_internal_event()
        self.assertEqual(self.vm.logical_clock, initial_clock + 1)
        self.mock_logger.info.assert_called_once_with(f"INTERNAL,{self.mock_datetime.now.return_value.timestamp.return_value},{self.vm.message_queue.qsize()},{self.vm.logical_clock}")
    
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
        self.mock_logger.info.assert_called_once_with(f"RECEIVE,{self.mock_datetime.now.return_value.timestamp.return_value},{self.vm.message_queue.qsize()},{self.vm.logical_clock}")
    
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
            peer.sendall.assert_called_once_with(str(self.vm.logical_clock).encode())
        
        self.mock_logger.info.assert_called_once_with(f"SEND,{self.mock_datetime.now.return_value.timestamp.return_value},{self.vm.message_queue.qsize()},{self.vm.logical_clock},all peers")
    
    def test_send_message_to_specific_peer(self):
        """Test that sending a message to a specific peer works"""
        initial_clock = self.vm.logical_clock
        self.vm.send_message([0])  # Send to first peer only
        self.assertEqual(self.vm.logical_clock, initial_clock + 1)
        
        # Check that the message was sent to the first peer only
        self.vm.peers[0].sendall.assert_called_once_with(str(self.vm.logical_clock).encode())
        self.vm.peers[1].sendall.assert_not_called()
        
        self.mock_logger.info.assert_called_once_with(f"SEND,{self.mock_datetime.now.return_value.timestamp.return_value},{self.vm.message_queue.qsize()},{self.vm.logical_clock},peer(s) [0]")
    
    def test_send_message_error_handling(self):
        """Test error handling when sending a message fails"""
        # Make the first peer raise an exception when sendall is called
        self.vm.peers[0].sendall.side_effect = Exception("Connection error")
        
        # Redirect stdout to capture print statements
        with patch('sys.stdout'):
            self.vm.send_message([0])
        
        # The logical clock should still be incremented
        self.assertEqual(self.vm.logical_clock, 1)
        
        # The logger should still record the send event
        self.mock_logger.info.assert_called_once()
    
    def test_internal_event_probability(self):
        """Test that the internal event probability is set correctly"""
        # Test default probability
        self.assertAlmostEqual(self.vm.internal_event_prob, 0.7)
        
        # Test with environment variable
        with patch.dict('os.environ', {'INTERNAL_EVENT_PROB': '0.5'}):
            with patch('logical_clock.logging'):
                with patch('logical_clock.os.makedirs'):
                    vm = VirtualMachine(0, 1, 8000, [8001, 8002])
                    self.assertAlmostEqual(vm.internal_event_prob, 0.5)
        
        # Test with invalid environment variable
        with patch.dict('os.environ', {'INTERNAL_EVENT_PROB': 'invalid'}):
            with patch('logical_clock.logging'):
                with patch('logical_clock.os.makedirs'):
                    vm = VirtualMachine(0, 1, 8000, [8001, 8002])
                    self.assertAlmostEqual(vm.internal_event_prob, 0.7)  # Should use default
    
    def test_connect_to_peers_success(self):
        """Test successful connection to peers"""
        # Mock successful connection
        mock_peer_socket = MagicMock()
        self.mock_socket.socket.return_value = mock_peer_socket
        
        # Redirect stdout to capture print statements
        with patch('sys.stdout'):
            self.vm.connect_to_peers()
        
        # Check that connections were attempted for both peer ports
        self.assertEqual(self.mock_socket.socket.call_count, 2)
        mock_peer_socket.connect.assert_has_calls([
            call(('localhost', 8001)),
            call(('localhost', 8002))
        ])
        
        # Check that peers were added
        self.assertEqual(len(self.vm.peers), 4)  # 2 from setUp + 2 new ones
    
    def test_connect_to_peers_failure(self):
        """Test handling of connection failures to peers"""
        # Mock connection failure
        mock_peer_socket = MagicMock()
        self.mock_socket.socket.return_value = mock_peer_socket
        mock_peer_socket.connect.side_effect = ConnectionRefusedError("Connection refused")
        
        # Redirect stdout to capture print statements
        with patch('sys.stdout'):
            self.vm.connect_to_peers()
        
        # Check that connections were attempted for both peer ports
        self.assertEqual(self.mock_socket.socket.call_count, 20)  # 2 peers * 10 retries
        
        # Check that no new peers were added
        self.assertEqual(len(self.vm.peers), 2)  # Only the 2 from setUp
    
    def test_accept_connections(self):
        """Test accepting connections from peers"""
        # Set up the VM to run
        self.vm.running = True
        
        # Mock accept to return once then raise an exception to exit the loop
        client_socket = MagicMock()
        addr = ('localhost', 9000)
        self.mock_server_socket.accept.side_effect = [
            (client_socket, addr),
            Exception("Test exception")
        ]
        
        # Redirect stdout to capture print statements
        with patch('sys.stdout'):
            self.vm.accept_connections()
        
        # Check that a thread was started to handle the client
        self.mock_threading.Thread.assert_called_once_with(
            target=self.vm.handle_client,
            args=(client_socket,),
            daemon=True
        )
        self.mock_threading.Thread.return_value.start.assert_called_once()
    
    def test_handle_client(self):
        """Test handling messages from a client"""
        # Set up the VM to run
        self.vm.running = True
        
        # Mock client socket
        client_socket = MagicMock()
        client_socket.recv.side_effect = [
            "42".encode(),  # First message
            "".encode(),    # Empty message to break the loop
        ]
        
        # Handle the client
        self.vm.handle_client(client_socket)
        
        # Check that the message was added to the queue
        self.assertEqual(self.vm.message_queue.qsize(), 1)
        self.assertEqual(self.vm.message_queue.get(), 42)
        
        # Check that the socket was closed
        client_socket.close.assert_called_once()
    
    def test_handle_client_error(self):
        """Test error handling in handle_client"""
        # Set up the VM to run
        self.vm.running = True
        
        # Mock client socket with an error
        client_socket = MagicMock()
        client_socket.recv.side_effect = Exception("Test exception")
        
        # Redirect stdout to capture print statements
        with patch('sys.stdout'):
            self.vm.handle_client(client_socket)
        
        # Check that the socket was closed
        client_socket.close.assert_called_once()
    
    def test_run(self):
        """Test the main run loop of the VM"""
        # Mock process_message to return False (no message processed)
        self.vm.process_message = MagicMock(return_value=False)
        
        # Mock connect_to_peers
        self.vm.connect_to_peers = MagicMock()
        
        # Set random values for different events
        self.mock_random.random.return_value = 0.5  # Internal event (< 0.7)
        self.mock_random.randint.return_value = 1  # For communication event type
        
        # Make the VM stop after one iteration
        def stop_vm(*args, **kwargs):
            self.vm.running = False
            return None
        self.mock_time.sleep.side_effect = stop_vm
        
        # Run the VM
        self.vm.run()
        
        # Check that the VM was set to running
        self.assertFalse(self.vm.running)  # Should be False after stopping
        
        # Check that a thread was started to accept connections
        self.mock_threading.Thread.assert_called_once_with(
            target=self.vm.accept_connections,
            daemon=True
        )
        self.mock_threading.Thread.return_value.start.assert_called_once()
        
        # Check that connect_to_peers was called
        self.vm.connect_to_peers.assert_called_once()
        
        # Check that the logger recorded the start event
        self.mock_logger.info.assert_called_with(
            f"START,{self.mock_datetime.now.return_value.timestamp.return_value},0,0,clock_rate=1;internal_prob=0.7"
        )
        
        # Check that process_message was called
        self.vm.process_message.assert_called_once()
        
        # Check that time.sleep was called with the correct value
        self.mock_time.sleep.assert_called_once_with(1.0)  # 1.0 / clock_rate = 1.0
    
    def test_run_with_keyboard_interrupt(self):
        """Test handling of KeyboardInterrupt in the run loop"""
        # Mock process_message to raise KeyboardInterrupt
        self.vm.process_message = MagicMock(side_effect=KeyboardInterrupt)
        
        # Mock connect_to_peers
        self.vm.connect_to_peers = MagicMock()
        
        # Redirect stdout to capture print statements
        with patch('sys.stdout'):
            self.vm.run()
        
        # Check that the VM was stopped
        self.assertFalse(self.vm.running)
        
        # Check that the server socket was closed
        self.mock_server_socket.close.assert_called_once()
    
    def test_run_internal_event(self):
        """Test the run loop with an internal event"""
        # Mock process_message to return False (no message processed)
        self.vm.process_message = MagicMock(return_value=False)
        self.vm.process_internal_event = MagicMock()
        
        # Mock connect_to_peers
        self.vm.connect_to_peers = MagicMock()
        
        # Set random value for internal event
        self.mock_random.random.return_value = 0.5  # < 0.7, so internal event
        
        # Make the VM stop after one iteration
        def stop_vm(*args, **kwargs):
            self.vm.running = False
            return None
        self.mock_time.sleep.side_effect = stop_vm
        
        # Run the VM
        with patch('sys.stdout'):
            self.vm.run()
        
        # Check that process_internal_event was called
        self.vm.process_internal_event.assert_called_once()
    
    def test_run_communication_event_type1(self):
        """Test the run loop with a communication event type 1"""
        # Mock process_message to return False (no message processed)
        self.vm.process_message = MagicMock(return_value=False)
        self.vm.send_message = MagicMock()
        
        # Mock connect_to_peers
        self.vm.connect_to_peers = MagicMock()
        
        # Set random values for communication event
        self.mock_random.random.return_value = 0.8  # > 0.7, so communication event
        self.mock_random.randint.side_effect = [1, 0]  # Type 1, target peer 0
        
        # Make the VM stop after one iteration
        def stop_vm(*args, **kwargs):
            self.vm.running = False
            return None
        self.mock_time.sleep.side_effect = stop_vm
        
        # Run the VM
        with patch('sys.stdout'):
            self.vm.run()
        
        # Check that send_message was called with the correct target
        self.vm.send_message.assert_called_once_with([0])
    
    def test_run_communication_event_type2(self):
        """Test the run loop with a communication event type 2"""
        # Mock process_message to return False (no message processed)
        self.vm.process_message = MagicMock(return_value=False)
        self.vm.send_message = MagicMock()
        
        # Mock connect_to_peers
        self.vm.connect_to_peers = MagicMock()
        
        # Set random values for communication event
        self.mock_random.random.return_value = 0.8  # > 0.7, so communication event
        self.mock_random.randint.side_effect = [2, 1]  # Type 2, target peer 1
        
        # Make the VM stop after one iteration
        def stop_vm(*args, **kwargs):
            self.vm.running = False
            return None
        self.mock_time.sleep.side_effect = stop_vm
        
        # Run the VM
        with patch('sys.stdout'):
            self.vm.run()
        
        # Check that send_message was called with the correct target
        self.vm.send_message.assert_called_once_with([1])
    
    def test_run_communication_event_type3(self):
        """Test the run loop with a communication event type 3"""
        # Mock process_message to return False (no message processed)
        self.vm.process_message = MagicMock(return_value=False)
        self.vm.send_message = MagicMock()
        
        # Mock connect_to_peers
        self.vm.connect_to_peers = MagicMock()
        
        # Set random values for communication event
        self.mock_random.random.return_value = 0.8  # > 0.7, so communication event
        self.mock_random.randint.return_value = 3  # Type 3
        
        # Make the VM stop after one iteration
        def stop_vm(*args, **kwargs):
            self.vm.running = False
            return None
        self.mock_time.sleep.side_effect = stop_vm
        
        # Run the VM
        with patch('sys.stdout'):
            self.vm.run()
        
        # Check that send_message was called with no targets (all peers)
        self.vm.send_message.assert_called_once_with()
    
    def test_run_communication_event_fallback(self):
        """Test the run loop with a communication event that falls back to internal event"""
        # Mock process_message to return False (no message processed)
        self.vm.process_message = MagicMock(return_value=False)
        self.vm.process_internal_event = MagicMock()
        
        # Remove all peers to force fallback
        self.vm.peers = []
        
        # Mock connect_to_peers
        self.vm.connect_to_peers = MagicMock()
        
        # Set random values for communication event
        self.mock_random.random.return_value = 0.8  # > 0.7, so communication event
        self.mock_random.randint.return_value = 1  # Type 1
        
        # Make the VM stop after one iteration
        def stop_vm(*args, **kwargs):
            self.vm.running = False
            return None
        self.mock_time.sleep.side_effect = stop_vm
        
        # Run the VM
        with patch('sys.stdout'):
            self.vm.run()
        
        # Check that process_internal_event was called (fallback)
        self.vm.process_internal_event.assert_called_once()


class TestStartMachine(unittest.TestCase):
    def test_start_machine(self):
        """Test the start_machine function"""
        # Mock VirtualMachine
        with patch('logical_clock.VirtualMachine') as mock_vm_class:
            mock_vm = MagicMock()
            mock_vm_class.return_value = mock_vm
            
            # Call start_machine
            start_machine(0, 1, 8000, [8001, 8002])
            
            # Check that VirtualMachine was created with the correct parameters
            mock_vm_class.assert_called_once_with(0, 1, 8000, [8001, 8002])
            
            # Check that run was called
            mock_vm.run.assert_called_once()


class TestMainFunction(unittest.TestCase):
    def test_main_with_default_num_machines(self):
        """Test the main function with default number of machines"""
        # Mock sys.argv
        with patch('sys.argv', ['logical_clock.py', '0', '8000']):
            # Mock start_machine
            with patch('logical_clock.start_machine') as mock_start_machine:
                # Mock random.randint
                with patch('logical_clock.random.randint', return_value=3):
                    # Redirect stdout to capture print statements
                    with patch('sys.stdout'):
                        # Import __main__ function
                        with patch.dict('os.environ', {'CLOCK_RATE_VARIATION': 'normal'}):
                            # Run the main function
                            import logical_clock
                            if hasattr(logical_clock, '__main__'):
                                logical_clock.__main__
                            
                            # Check that start_machine was called with the correct parameters
                            mock_start_machine.assert_called_once_with(0, 3, 8000, [8001, 8002])
    
    def test_main_with_custom_num_machines(self):
        """Test the main function with custom number of machines"""
        # Mock sys.argv
        with patch('sys.argv', ['logical_clock.py', '1', '8000', '4']):
            # Mock start_machine
            with patch('logical_clock.start_machine') as mock_start_machine:
                # Mock random.randint
                with patch('logical_clock.random.randint', return_value=2):
                    # Redirect stdout to capture print statements
                    with patch('sys.stdout'):
                        # Import __main__ function
                        with patch.dict('os.environ', {'CLOCK_RATE_VARIATION': 'small'}):
                            # Run the main function
                            import logical_clock
                            if hasattr(logical_clock, '__main__'):
                                logical_clock.__main__
                            
                            # Check that start_machine was called with the correct parameters
                            mock_start_machine.assert_called_once_with(1, 2, 8001, [8000, 8002, 8003])
    
    def test_main_with_invalid_args(self):
        """Test the main function with invalid arguments"""
        # Mock sys.argv with insufficient arguments
        with patch('sys.argv', ['logical_clock.py']):
            # Mock sys.exit to prevent actual exit
            with patch('sys.exit') as mock_exit:
                # Redirect stdout to capture print statements
                with patch('sys.stdout'):
                    # Import __main__ function
                    import logical_clock
                    if hasattr(logical_clock, '__main__'):
                        logical_clock.__main__
                    
                    # Check that sys.exit was called
                    mock_exit.assert_called_once_with(1)


if __name__ == '__main__':
    unittest.main() 