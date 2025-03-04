import unittest
import sys
import os
import time
import threading
import socket
import queue
import logging
import random
from unittest.mock import patch, MagicMock, call

# Add parent directory to path to import logical_clock
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logical_clock import VirtualMachine

class TestVirtualMachineRegression(unittest.TestCase):
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
    
    def test_logical_clock_monotonicity(self):
        """Test that logical clocks only increase over time"""
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
        
        # Track logical clock values over time
        clock_history = [[] for _ in range(3)]
        
        # Run a series of random events
        for _ in range(10):
            # Choose a random VM to perform an action
            vm_idx = random.randint(0, 2)
            vm = self.vms[vm_idx]
            
            # Randomly choose between internal event and send message
            if random.random() < 0.5:
                # Internal event
                vm.process_internal_event()
            else:
                # Send message to random peer
                target_idx = random.randint(0, 1)  # 0 or 1
                vm.send_message([target_idx])
            
            # Record new clock value
            clock_history[vm_idx].append(vm.logical_clock)
            
            # Give time for messages to be received
            time.sleep(0.1)
            
            # Process any received messages
            for i, vm in enumerate(self.vms):
                if not vm.message_queue.empty():
                    vm.process_message()
                    # Record updated clock value
                    clock_history[i].append(vm.logical_clock)
        
        # Check that clock values are monotonically increasing for each VM
        for i, history in enumerate(clock_history):
            for j in range(1, len(history)):
                self.assertGreater(history[j], history[j-1], 
                                  f"VM {i} clock decreased from {history[j-1]} to {history[j]}")
    
    def test_lamport_clock_property(self):
        """Test that Lamport's clock property holds: if event a happens before event b, then C(a) < C(b)"""
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
        
        # Reset all logical clocks to ensure a clean state
        for vm in self.vms:
            vm.logical_clock = 0
        
        # Create a causal chain of events:
        # 1. VM0 internal event
        # 2. VM0 sends to VM1
        # 3. VM1 processes message
        # 4. VM1 internal event
        # 5. VM1 sends to VM2
        # 6. VM2 processes message
        
        # Record clock values at each step
        clock_values = []
        
        # 1. VM0 internal event
        self.vms[0].process_internal_event()
        clock_values.append(("VM0 internal", self.vms[0].logical_clock))
        
        # 2. VM0 sends to VM1
        self.vms[0].send_message([0])  # First peer is VM1
        clock_values.append(("VM0 send", self.vms[0].logical_clock))
        time.sleep(0.1)
        
        # 3. VM1 processes message
        self.vms[1].process_message()
        clock_values.append(("VM1 receive", self.vms[1].logical_clock))
        
        # 4. VM1 internal event
        self.vms[1].process_internal_event()
        clock_values.append(("VM1 internal", self.vms[1].logical_clock))
        
        # 5. VM1 sends to VM2
        self.vms[1].send_message([1])  # Second peer is VM2
        clock_values.append(("VM1 send", self.vms[1].logical_clock))
        time.sleep(0.1)
        
        # 6. VM2 processes message
        self.vms[2].process_message()
        clock_values.append(("VM2 receive", self.vms[2].logical_clock))
        
        # Check that clock values are strictly increasing along the causal chain
        for i in range(1, len(clock_values)):
            self.assertGreater(
                clock_values[i][1], 
                clock_values[i-1][1],
                f"Clock did not increase from {clock_values[i-1][0]} ({clock_values[i-1][1]}) to {clock_values[i][0]} ({clock_values[i][1]})"
            )
    
    def test_system_stability_under_load(self):
        """Test that the system remains stable under load"""
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
        
        # Create worker threads to simulate load
        def worker(vm_idx):
            vm = self.vms[vm_idx]
            for _ in range(20):
                # Randomly choose between internal event and send message
                if random.random() < 0.3:
                    # Internal event
                    vm.process_internal_event()
                else:
                    # Send message to random peer or all peers
                    if random.random() < 0.7:
                        target_idx = random.randint(0, 1)  # 0 or 1
                        vm.send_message([target_idx])
                    else:
                        vm.send_message()  # All peers
                
                # Process any received messages
                while not vm.message_queue.empty():
                    vm.process_message()
                
                # Small delay
                time.sleep(0.01)
            time.sleep(1)
            while not vm.message_queue.empty():
                vm.process_message()
        
        # Start worker threads
        worker_threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            thread.start()
            worker_threads.append(thread)
        
        # Wait for all workers to finish
        for thread in worker_threads:
            thread.join()
        
        # Check that all VMs are still in a valid state
        for i, vm in enumerate(self.vms):
            # Logical clock should be positive
            self.assertGreater(vm.logical_clock, 0, f"VM {i} has invalid logical clock: {vm.logical_clock}")
            
            # All message queues should eventually be processed
            self.assertEqual(vm.message_queue.qsize(), 0, f"VM {i} still has {vm.message_queue.qsize()} unprocessed messages")
    
    def test_connection_recovery(self):
        """Test that VMs can recover from connection failures"""
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
        
        # Verify initial connections
        for vm in self.vms:
            self.assertEqual(len(vm.peers), 2)
        
        # Simulate a connection failure by closing VM1's peers
        for peer in self.vms[1].peers:
            peer.close()
        self.vms[1].peers = []
        
        # Reconnect VM1 to its peers
        self.vms[1].connect_to_peers()
        
        # Give connections time to establish
        time.sleep(0.5)
        
        # Verify that VM1 has reconnected
        self.assertEqual(len(self.vms[1].peers), 2)
        
        # Test that communication still works
        # VM1 sends to all peers
        self.vms[1].send_message()
        
        # Give time for messages to be received
        time.sleep(0.5)
        
        # Check that VM0 and VM2 received the message
        self.assertEqual(self.vms[0].message_queue.qsize(), 1)
        self.assertEqual(self.vms[2].message_queue.qsize(), 1)


if __name__ == '__main__':
    unittest.main() 