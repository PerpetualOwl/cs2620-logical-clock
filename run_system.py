#!/usr/bin/env python3
import subprocess
import sys
import time
import signal
import os

def run_system(num_machines=3, base_port=8000, duration=60):
    """
    Run a distributed system with multiple virtual machines.
    
    Args:
        num_machines (int): Number of virtual machines to run
        base_port (int): Base port number for communication
        duration (int): Duration to run the system in seconds
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Start each machine as a separate process
    processes = []
    for i in range(num_machines):
        cmd = ["python", "logical_clock.py", str(i), str(base_port), str(num_machines)]
        process = subprocess.Popen(cmd)
        processes.append(process)
        print(f"Started machine {i} (PID: {process.pid})")
        # Small delay to allow each machine to start listening before the next one tries to connect
        time.sleep(0.5)
    
    print(f"\nRunning system with {num_machines} machines for {duration} seconds...")
    try:
        # Wait for the specified duration
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
    
    # Terminate all processes
    print("\nShutting down all machines...")
    for i, process in enumerate(processes):
        try:
            process.terminate()
            print(f"Terminated machine {i} (PID: {process.pid})")
        except:
            print(f"Failed to terminate machine {i} (PID: {process.pid})")
    
    # Wait for all processes to terminate
    for process in processes:
        process.wait()
    
    print("\nAll machines shut down. Experiment complete.")
    print(f"Log files are available in the 'logs' directory.")

def run_experiment(experiment_name, num_machines=3, base_port=8000, duration=60, 
                  internal_event_prob=None, clock_rate_variation=None):
    """
    Run an experiment with specific parameters and save logs to a dedicated directory.
    
    Args:
        experiment_name (str): Name of the experiment
        num_machines (int): Number of virtual machines to run
        base_port (int): Base port number for communication
        duration (int): Duration to run the system in seconds
        internal_event_prob (float, optional): Probability of internal events (0-1)
        clock_rate_variation (str, optional): Type of clock rate variation ("small" or "normal")
    """
    # Create experiment directory
    experiment_dir = f"logs/{experiment_name}"
    os.makedirs(experiment_dir, exist_ok=True)
    
    # Prepare environment variables for experiment parameters
    env = os.environ.copy()
    if internal_event_prob is not None:
        env["INTERNAL_EVENT_PROB"] = str(internal_event_prob)
    if clock_rate_variation is not None:
        env["CLOCK_RATE_VARIATION"] = clock_rate_variation
    
    # Start each machine as a separate process
    processes = []
    for i in range(num_machines):
        cmd = ["python", "logical_clock.py", str(i), str(base_port), str(num_machines)]
        process = subprocess.Popen(cmd, env=env)
        processes.append(process)
        print(f"Started machine {i} (PID: {process.pid})")
        # Small delay to allow each machine to start listening before the next one tries to connect
        time.sleep(0.5)
    
    print(f"\nRunning experiment '{experiment_name}' with {num_machines} machines for {duration} seconds...")
    try:
        # Wait for the specified duration
        time.sleep(duration)
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
    
    # Terminate all processes
    print("\nShutting down all machines...")
    for i, process in enumerate(processes):
        try:
            process.terminate()
            print(f"Terminated machine {i} (PID: {process.pid})")
        except:
            print(f"Failed to terminate machine {i} (PID: {process.pid})")
    
    # Wait for all processes to terminate
    for process in processes:
        process.wait()
    
    # Move log files to experiment directory
    for i in range(num_machines):
        src_file = f"logs/machine_{i}.log"
        dst_file = f"{experiment_dir}/machine_{i}.log"
        if os.path.exists(src_file):
            os.rename(src_file, dst_file)
    
    print(f"\nExperiment '{experiment_name}' complete.")
    print(f"Log files are available in the '{experiment_dir}' directory.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_system.py <command> [options]")
        print("\nCommands:")
        print("  run              Run a single experiment")
        print("  run_all          Run all required experiments")
        print("\nOptions for 'run':")
        print("  --machines=N     Number of machines (default: 3)")
        print("  --port=N         Base port number (default: 8000)")
        print("  --duration=N     Duration in seconds (default: 60)")
        print("  --internal=0.X   Probability of internal events (0-1)")
        print("  --variation=TYPE Clock rate variation ('small' or 'normal')")
        print("\nExample:")
        print("  python run_system.py run --machines=3 --duration=60")
        print("  python run_system.py run_all")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "run":
        # Parse options
        num_machines = 3
        base_port = 8000
        duration = 60
        internal_event_prob = None
        clock_rate_variation = None
        
        for arg in sys.argv[2:]:
            if arg.startswith("--machines="):
                num_machines = int(arg.split("=")[1])
            elif arg.startswith("--port="):
                base_port = int(arg.split("=")[1])
            elif arg.startswith("--duration="):
                duration = int(arg.split("=")[1])
            elif arg.startswith("--internal="):
                internal_event_prob = float(arg.split("=")[1])
            elif arg.startswith("--variation="):
                clock_rate_variation = arg.split("=")[1]
        
        # Generate experiment name
        experiment_name = f"custom_m{num_machines}_d{duration}"
        if internal_event_prob is not None:
            experiment_name += f"_i{internal_event_prob}"
        if clock_rate_variation is not None:
            experiment_name += f"_v{clock_rate_variation}"
        
        run_experiment(experiment_name, num_machines, base_port, duration, 
                      internal_event_prob, clock_rate_variation)
    
    elif command == "run_all":
        # Run all required experiments
        
        # 1. Run 5 trials of the original model for 60 seconds each
        for trial in range(1, 6):
            run_experiment(f"original_trial{trial}", 3, 8000, 60)
            print("\nWaiting 5 seconds before starting next trial...\n")
            time.sleep(5)
        
        # 2. Run experiment with smaller clock rate variation
        run_experiment("small_variation", 3, 8000, 60, None, "small")
        print("\nWaiting 5 seconds before starting next experiment...\n")
        time.sleep(5)
        
        # 3. Run experiment with smaller probability of internal events
        run_experiment("small_internal_prob", 3, 8000, 60, 0.4, None)
        
        print("\nAll experiments completed successfully!")
    
    else:
        print(f"Unknown command: {command}")
        print("Use 'python run_system.py run' or 'python run_system.py run_all'")
        sys.exit(1) 