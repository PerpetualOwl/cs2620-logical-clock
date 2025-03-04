import unittest
import sys
import os
import time
import threading
import socket
import queue
import logging
from unittest.mock import patch, MagicMock, call

# Add parent directory to path to import logical_clock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logical_clock import VirtualMachine

class TestVirtualMachineIntegration(unittest.TestCase):
    def setUp(self):
        # Patch logging to prevent actual file writes
        self.logging_patcher = patch('logical_clock.logging')
        self.mock_logging = self.logging_patcher.start()
        
        # Patch os.makedirs to prevent directory creation
        self.makedirs_patcher = patch('logical_clock.os.makedirs')
        self.mock_makedirs = self.makedirs_patcher.start()
        
        # Create mock loggers
        self.mock_loggers = [MagicMock() for _ in range(3)]
        
        # Create virtual machines for testing
        self.vms = []
        self.ports = [8000, 8001, 8002]
        
        # Create VMs with real sockets but mock loggers
        for i in range(3):
            vm = VirtualMachine(
                machine_id=i,
                clock_rate=1,
                port=self.ports[i],
                peer_ports=[p for p in self.ports if p != self.ports[i]]
            )
            vm.logger = self.mock_loggers[i]
            self.vms.append(vm)
    
    def tearDown(self):
        # Stop all VMs
        for vm in self.vms:
            vm.running = False
            vm.server_socket.close()
            for peer in vm.peers:
                try:
                    peer.close()
                except:
                    pass
        
        # Stop patchers
        self.logging_patcher.stop()
        self.makedirs_patcher.stop()
    
    def test_vm_connections(self):
        """Test that VMs can connect to each other"""
        # Start server threads for each VM
        server_threads = []
        for vm in self.vms:
            vm.running = True
            thread = threading.Thread(target=vm.accept_connections, daemon=True)
            thread.start()
            server_threads.append(thread)
        
        # Give servers time to start
        time.sleep(0.5)
        
        # Connect VMs to each other
        for vm in self.vms:
            vm.connect_to_peers()
        
        # Give connections time to establish
        time.sleep(0.5)
        
        # Check that each VM has connected to the other two
        for vm in self.vms:
            self.assertEqual(len(vm.peers), 2)
    
    def test_message_sending_and_receiving(self):
        """Test that VMs can send and receive messages"""
        # Start server threads for each VM
        server_threads = []
        for vm in self.vms:
            vm.running = True
            thread = threading.Thread(target=vm.accept_connections, daemon=True)
            thread.start()
            server_threads.append(thread)
        
        # Give servers time to start
        time.sleep(0.5)
        
        # Connect VMs to each other
        for vm in self.vms:
            vm.connect_to_peers()
        
        # Give connections time to establish
        time.sleep(0.5)
        
        # Send a message from VM 0 to all peers
        self.vms[0].send_message()
        
        # Give message time to be received
        time.sleep(0.5)
        
        # Check that VM 1 and VM 2 received the message
        self.assertEqual(self.vms[1].message_queue.qsize(), 1)
        self.assertEqual(self.vms[2].message_queue.qsize(), 1)
        
        # Process the messages
        self.vms[1].process_message()
        self.vms[2].process_message()
        
        # Check that the logical clocks were updated correctly
        self.assertEqual(self.vms[0].logical_clock, 1)  # Incremented for send
        self.assertEqual(self.vms[1].logical_clock, 2)  # max(0, 1) + 1
        self.assertEqual(self.vms[2].logical_clock, 2)  # max(0, 1) + 1
    
    def test_targeted_message_sending(self):
        """Test that VMs can send messages to specific peers"""
        # Start server threads for each VM
        server_threads = []
        for vm in self.vms:
            vm.running = True
            thread = threading.Thread(target=vm.accept_connections, daemon=True)
            thread.start()
            server_threads.append(thread)
        
        # Give servers time to start
        time.sleep(0.5)
        
        # Connect VMs to each other
        for vm in self.vms:
            vm.connect_to_peers()
        
        # Give connections time to establish
        time.sleep(0.5)
        
        # Send a message from VM 0 to VM 1 only
        self.vms[0].send_message([0])  # First peer is VM 1
        
        # Give message time to be received
        time.sleep(0.5)
        
        # Check that VM 1 received the message but VM 2 did not
        self.assertEqual(self.vms[1].message_queue.qsize(), 1)
        self.assertEqual(self.vms[2].message_queue.qsize(), 0)
    
    def test_multiple_message_exchange(self):
        """Test a sequence of message exchanges between VMs"""
        # Start server threads for each VM
        server_threads = []
        for vm in self.vms:
            vm.running = True
            thread = threading.Thread(target=vm.accept_connections, daemon=True)
            thread.start()
            server_threads.append(thread)
        
        # Give servers time to start
        time.sleep(0.5)
        
        # Connect VMs to each other
        for vm in self.vms:
            vm.connect_to_peers()
        
        # Give connections time to establish
        time.sleep(0.5)
        
        # VM 0 sends to all
        self.vms[0].send_message()
        time.sleep(0.1)
        
        # VM 1 processes message and sends to VM 2
        self.vms[1].process_message()
        self.vms[1].send_message([1])  # Second peer is VM 2
        time.sleep(0.1)
        
        # VM 2 processes both messages
        self.vms[2].process_message()  # From VM 0
        self.vms[2].process_message()  # From VM 1
        
        # Check final logical clock values
        self.assertEqual(self.vms[0].logical_clock, 1)  # Initial send
        self.assertEqual(self.vms[1].logical_clock, 3)  # Received 1, then sent (2+1)
        self.assertEqual(self.vms[2].logical_clock, 4)  # max(0, 1) + 1, then max(2, 3) + 1


if __name__ == '__main__':
    unittest.main() 