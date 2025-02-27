import socket
import threading
import time
import random
import queue
import logging
import os
from datetime import datetime

# Configuration
NUM_MACHINES = 3
PORT_BASE = 5000  # Base port, machine i will listen on PORT_BASE + i
LOG_DIR = "logs"

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

class VirtualMachine:
    def __init__(self, machine_id):
        self.machine_id = machine_id
        self.logical_clock = 0
        self.clock_rate = random.randint(1, 6)  # Random clock rate between 1-6 ticks/second
        self.message_queue = queue.Queue()
        self.connections = {}  # Will store connections to other VMs
        self.running = False
        
        # Set up logging
        log_file = os.path.join(LOG_DIR, f"machine_{machine_id}.log")
        self.logger = self._setup_logger(log_file)
        
        # Set up server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.port = PORT_BASE + machine_id
        self.server_socket.bind(('localhost', self.port))
        self.server_socket.listen(5)
        
        self.logger.info(f"Machine {machine_id} initialized with clock rate {self.clock_rate} ticks/second")
    
    def _setup_logger(self, log_file):
        logger = logging.getLogger(f"VM_{self.machine_id}")
        logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter and add to handlers
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def connect_to_others(self, other_machine_ids):
        """Establish connections to other virtual machines."""
        for other_id in other_machine_ids:
            if other_id != self.machine_id:
                self._connect_to_machine(other_id)
    
    def _connect_to_machine(self, other_id):
        """Establish connection to a specific machine."""
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect(('localhost', PORT_BASE + other_id))
                self.connections[other_id] = client_socket
                self.logger.info(f"Connected to Machine {other_id}")
                return
            except ConnectionRefusedError:
                retry_count += 1
                self.logger.info(f"Connection to Machine {other_id} failed. Retrying in 1 second...")
                time.sleep(1)
        
        self.logger.error(f"Failed to connect to Machine {other_id} after {max_retries} attempts")
    
    def start(self):
        """Start the virtual machine."""
        self.running = True
        
        # Start thread to accept connections
        accept_thread = threading.Thread(target=self._accept_connections)
        accept_thread.daemon = True
        accept_thread.start()
        
        # Start thread to receive messages
        receive_thread = threading.Thread(target=self._receive_messages)
        receive_thread.daemon = True
        receive_thread.start()
        
        # Start the main execution loop
        main_thread = threading.Thread(target=self._run)
        main_thread.daemon = True
        main_thread.start()
        
        return main_thread
    
    def stop(self):
        """Stop the virtual machine."""
        self.running = False
        self.server_socket.close()
        for conn in self.connections.values():
            conn.close()
    
    def _accept_connections(self):
        """Accept incoming connections from other machines."""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                # Start a thread to handle this client
                client_thread = threading.Thread(target=self._handle_client, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()
            except OSError:
                # Socket closed or other error
                break
    
    def _handle_client(self, client_socket):
        """Handle messages from a connected client."""
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # Parse the message and add to queue
                sender_id, sender_clock = map(int, data.decode().split(':'))
                self.message_queue.put((sender_id, sender_clock))
            except:
                break
        
        client_socket.close()
    
    def _receive_messages(self):
        """Process all received connections and messages."""
        for conn in self.connections.values():
            conn.setblocking(0)  # Non-blocking mode
    
    def _run(self):
        """Main execution loop for the virtual machine."""
        while self.running:
            # Sleep according to clock rate
            time.sleep(1.0 / self.clock_rate)
            
            # Process one message from queue if available
            if not self.message_queue.empty():
                sender_id, sender_clock = self.message_queue.get()
                # Update logical clock according to Lamport's rules
                self.logical_clock = max(self.logical_clock, sender_clock) + 1
                queue_length = self.message_queue.qsize()
                self.logger.info(f"Received message from Machine {sender_id}, Queue Length: {queue_length}, Logical Clock: {self.logical_clock}")
            else:
                # No message in queue, generate random action
                action = random.randint(1, 10)
                
                if 1 <= action <= 3:
                    # Send message actions
                    if action == 1:
                        # Send to one random machine
                        target_ids = [random.choice([i for i in self.connections.keys()])]
                    elif action == 2:
                        # Send to another random machine
                        target_ids = [random.choice([i for i in self.connections.keys()])]
                    else:  # action == 3
                        # Send to all other machines
                        target_ids = list(self.connections.keys())
                    
                    # Update logical clock before sending
                    self.logical_clock += 1
                    
                    # Send messages
                    for target_id in target_ids:
                        self._send_message(target_id)
                        self.logger.info(f"Sent message to Machine {target_id}, Logical Clock: {self.logical_clock}")
                else:
                    # Internal event
                    self.logical_clock += 1
                    self.logger.info(f"Internal event, Logical Clock: {self.logical_clock}")
    
    def _send_message(self, target_id):
        """Send a message to another virtual machine."""
        try:
            message = f"{self.machine_id}:{self.logical_clock}"
            self.connections[target_id].sendall(message.encode())
        except:
            self.logger.error(f"Failed to send message to Machine {target_id}")

def run_simulation(duration=60):
    """Run the distributed system simulation for the specified duration in seconds."""
    print(f"Starting simulation with {NUM_MACHINES} machines for {duration} seconds...")
    
    # Initialize machines
    machines = []
    for i in range(NUM_MACHINES):
        machines.append(VirtualMachine(i))
        print(f"Machine {i} initialized with clock rate {machines[i].clock_rate} ticks/second")
    
    # Allow time for all servers to start
    time.sleep(1)
    
    # Connect machines to each other
    for i, machine in enumerate(machines):
        other_ids = [j for j in range(NUM_MACHINES) if j != i]
        machine.connect_to_others(other_ids)
    
    # Start all machines
    threads = []
    for machine in machines:
        thread = machine.start()
        threads.append(thread)
    
    # Run for specified duration
    time.sleep(duration)
    
    # Stop all machines
    for machine in machines:
        machine.stop()
    
    print("Simulation completed. Check logs for results.")

def analyze_logs():
    """Analyze log files to extract information about logical clocks."""
    log_files = [os.path.join(LOG_DIR, f) for f in os.listdir(LOG_DIR) if f.startswith("machine_")]
    
    for log_file in log_files:
        machine_id = log_file.split("_")[1].split(".")[0]
        print(f"\nAnalyzing Machine {machine_id} logs:")
        
        clock_values = []
        queue_lengths = []
        
        with open(log_file, 'r') as f:
            for line in f:
                if "Logical Clock:" in line:
                    clock_value = int(line.split("Logical Clock:")[1].strip())
                    clock_values.append(clock_value)
                
                if "Queue Length:" in line:
                    queue_length = int(line.split("Queue Length:")[1].split(",")[0].strip())
                    queue_lengths.append(queue_length)
        
        if clock_values:
            print(f"  Initial logical clock: {clock_values[0]}")
            print(f"  Final logical clock: {clock_values[-1]}")
            print(f"  Total increment: {clock_values[-1] - clock_values[0]}")
            
            # Calculate jumps in logical clock
            jumps = [clock_values[i] - clock_values[i-1] for i in range(1, len(clock_values))]
            if jumps:
                print(f"  Average jump in logical clock: {sum(jumps)/len(jumps):.2f}")
                print(f"  Maximum jump in logical clock: {max(jumps)}")
        
        if queue_lengths:
            print(f"  Average queue length: {sum(queue_lengths)/len(queue_lengths):.2f}")
            print(f"  Maximum queue length: {max(queue_lengths)}")

if __name__ == "__main__":
    # Run simulation multiple times
    for run in range(1, 6):
        print(f"\n=== Run {run} ===")
        run_simulation(duration=60)  # Run for 1 minute
        analyze_logs()
        
        # Rename log files to preserve them for each run
        for i in range(NUM_MACHINES):
            old_file = os.path.join(LOG_DIR, f"machine_{i}.log")
            new_file = os.path.join(LOG_DIR, f"machine_{i}_run_{run}.log")
            if os.path.exists(old_file):
                os.rename(old_file, new_file)
    
    print("\nAll simulation runs completed!")
