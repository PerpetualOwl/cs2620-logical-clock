#!/usr/bin/env python3
import socket
import threading
import time
import random
import os
import sys
import queue
import logging
from datetime import datetime

class VirtualMachine:
    def __init__(self, machine_id, clock_rate, port, peer_ports):
        """
        Initialize a virtual machine with a specific ID, clock rate, and communication ports.
        
        Args:
            machine_id (int): Unique identifier for this machine
            clock_rate (int): Number of clock ticks per second (1-6)
            port (int): Port this machine listens on
            peer_ports (list): Ports of other machines to connect to
        """
        self.machine_id = machine_id
        self.clock_rate = clock_rate
        self.port = port
        self.peer_ports = peer_ports
        self.logical_clock = 0
        self.message_queue = queue.Queue()
        self.running = False
        self.peers = []
        
        # Get experiment parameters from environment variables
        self.internal_event_prob = self._get_internal_event_prob()
        
        # Set up logging
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = f"{log_dir}/machine_{machine_id}.log"
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(message)s'
        )
        self.logger = logging.getLogger(f"Machine_{machine_id}")
        
        # Set up socket server
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.port))
        self.server_socket.listen(5)
        
    def _get_internal_event_prob(self):
        """Get the probability of internal events from environment variables"""
        if "INTERNAL_EVENT_PROB" in os.environ:
            try:
                prob = float(os.environ["INTERNAL_EVENT_PROB"])
                return prob
            except ValueError:
                pass
        # Default probability (7/10 for internal events in the original spec)
        return 0.7
        
    def connect_to_peers(self):
        """Connect to all peer machines"""
        for peer_port in self.peer_ports:
            max_retries = 10
            retry_count = 0
            while retry_count < max_retries:
                try:
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    peer_socket.connect(('localhost', peer_port))
                    self.peers.append(peer_socket)
                    print(f"Machine {self.machine_id} connected to peer on port {peer_port}")
                    break
                except ConnectionRefusedError:
                    retry_count += 1
                    print(f"Connection to port {peer_port} refused, retrying ({retry_count}/{max_retries})...")
                    time.sleep(1)
            if retry_count == max_retries:
                print(f"Failed to connect to peer on port {peer_port} after {max_retries} attempts")
    
    def accept_connections(self):
        """Accept incoming connections from peers"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    print(f"Error accepting connection: {e}")
    
    def handle_client(self, client_socket):
        """Handle messages from a connected peer"""
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # Parse the received logical clock time
                received_time = int(data.decode().strip())
                
                # Add to message queue
                self.message_queue.put(received_time)
            except Exception as e:
                if self.running:  # Only log if we're still supposed to be running
                    print(f"Error handling client: {e}")
                break
        
        try:
            client_socket.close()
        except:
            pass
    
    def send_message(self, target_indices=None):
        """
        Send the current logical clock value to specified peers
        
        Args:
            target_indices: List of indices of peers to send to, or None for all peers
        """
        # Increment logical clock for send event
        self.logical_clock += 1
        
        # Determine which peers to send to
        if target_indices is None:
            targets = self.peers
        else:
            targets = [self.peers[i] for i in target_indices if i < len(self.peers)]
        
        # Send message to each target
        for peer_socket in targets:
            try:
                message = str(self.logical_clock)
                peer_socket.sendall(message.encode())
            except Exception as e:
                print(f"Error sending message: {e}")
        
        # Log the send event
        target_str = "all peers" if target_indices is None else f"peer(s) {target_indices}"
        self.logger.info(f"SEND,{datetime.now().timestamp()},{self.message_queue.qsize()},{self.logical_clock},{target_str}")
    
    def process_internal_event(self):
        """Process an internal event, updating the logical clock"""
        self.logical_clock += 1
        self.logger.info(f"INTERNAL,{datetime.now().timestamp()},{self.message_queue.qsize()},{self.logical_clock}")
    
    def process_message(self):
        """Process a message from the queue, updating the logical clock"""
        if not self.message_queue.empty():
            received_time = self.message_queue.get()
            # Update logical clock according to Lamport's rule
            self.logical_clock = max(self.logical_clock, received_time) + 1
            self.logger.info(f"RECEIVE,{datetime.now().timestamp()},{self.message_queue.qsize()},{self.logical_clock}")
            return True
        return False
    
    def run(self):
        """Run the virtual machine's main loop"""
        self.running = True
        
        # Start thread to accept connections
        accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
        accept_thread.start()
        
        # Connect to peers
        self.connect_to_peers()
        
        # Log initial state with experiment parameters
        params = f"clock_rate={self.clock_rate};internal_prob={self.internal_event_prob}"
        self.logger.info(f"START,{datetime.now().timestamp()},0,{self.logical_clock},{params}")
        
        try:
            while self.running:
                # Calculate sleep time based on clock rate
                sleep_time = 1.0 / self.clock_rate
                
                # Process a message if available
                if not self.process_message():
                    # If no message, generate random event
                    rand_val = random.random()
                    
                    # Determine if this is an internal event based on probability
                    if rand_val < self.internal_event_prob:
                        # Internal event
                        self.process_internal_event()
                    else:
                        # Communication event - determine type (1, 2, or 3)
                        # Scale the remaining probability space (1 - internal_prob) into 3 equal parts
                        comm_type = random.randint(1, 3)
                        
                        if comm_type == 1 and self.peers:
                            # Send to one random peer
                            target_idx = random.randint(0, len(self.peers) - 1)
                            self.send_message([target_idx])
                        elif comm_type == 2 and len(self.peers) >= 2:
                            # Send to another random peer (different from first if possible)
                            target_idx = random.randint(0, len(self.peers) - 1)
                            self.send_message([target_idx])
                        elif comm_type == 3 and self.peers:
                            # Send to all peers
                            self.send_message()
                        else:
                            # Fallback to internal event if no peers available
                            self.process_internal_event()
                
                # Sleep according to clock rate
                time.sleep(sleep_time)
        
        except KeyboardInterrupt:
            print(f"Machine {self.machine_id} shutting down...")
        finally:
            self.running = False
            self.server_socket.close()
            for peer in self.peers:
                try:
                    peer.close()
                except:
                    pass
            print(f"Machine {self.machine_id} shutdown complete")

def start_machine(machine_id, clock_rate, port, peer_ports):
    """Start a virtual machine with the given parameters"""
    vm = VirtualMachine(machine_id, clock_rate, port, peer_ports)
    vm.run()

def main(machine_id, base_port, num_machines):
    # Calculate ports for all machines
    all_ports = [base_port + i for i in range(num_machines)]
    
    # Get port for this machine and ports for peers
    port = all_ports[machine_id]
    peer_ports = [p for i, p in enumerate(all_ports) if i != machine_id]
    
    # Generate random clock rate based on experiment settings
    clock_rate_variation = os.environ.get("CLOCK_RATE_VARIATION", "normal")
    
    if clock_rate_variation == "small":
        # Smaller variation: 3-4 ticks per second
        clock_rate = random.randint(3, 4)
    else:
        # Normal variation: 1-6 ticks per second
        clock_rate = random.randint(1, 6)
    
    print(f"Starting machine {machine_id} with clock rate {clock_rate} on port {port}")
    print(f"Peer ports: {peer_ports}")
    
    # Start the machine
    start_machine(machine_id, clock_rate, port, peer_ports) 

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python logical_clock.py <machine_id> <base_port> [num_machines=3]")
        sys.exit(1)
    
    machine_id = int(sys.argv[1])
    base_port = int(sys.argv[2])
    num_machines = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    main(machine_id, base_port, num_machines)