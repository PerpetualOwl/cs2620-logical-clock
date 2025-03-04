#!/usr/bin/env python3
import os
import sys
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

def parse_log_file(log_file):
    """Parse a log file into a pandas DataFrame"""
    data = []
    with open(log_file, 'r') as f:
        for line in f:
            parts = line.strip().split(',', 4)  # Split only on the first 4 commas
            if len(parts) >= 4:
                event_type = parts[0]
                timestamp = float(parts[1])
                queue_size = int(parts[2])
                logical_clock = int(parts[3])
                
                # Extract additional info if available
                additional_info = parts[4] if len(parts) > 4 else ""
                
                data.append({
                    'event_type': event_type,
                    'timestamp': timestamp,
                    'queue_size': queue_size,
                    'logical_clock': logical_clock,
                    'additional_info': additional_info
                })
    
    return pd.DataFrame(data)

def analyze_experiment(experiment_dir):
    """Analyze all log files in an experiment directory"""
    log_files = glob.glob(f"{experiment_dir}/machine_*.log")
    if not log_files:
        print(f"No log files found in {experiment_dir}")
        return
    
    print(f"\nAnalyzing experiment: {os.path.basename(experiment_dir)}")
    print(f"Found {len(log_files)} log files")
    
    # Parse all log files
    machine_data = {}
    for log_file in log_files:
        machine_id = int(os.path.basename(log_file).split('_')[1].split('.')[0])
        df = parse_log_file(log_file)
        machine_data[machine_id] = df
    
    # Extract clock rates
    clock_rates = {}
    internal_probs = {}
    for machine_id, df in machine_data.items():
        start_row = df[df['event_type'] == 'START']
        if not start_row.empty:
            additional_info = start_row.iloc[0]['additional_info']
            # Extract parameters from the additional_info field
            if additional_info:
                # Handle both comma and semicolon separated parameters for backward compatibility
                params = additional_info.replace(',', ';').split(';')
                for param in params:
                    if '=' in param:
                        key, value = param.split('=')
                        if key.strip() == 'clock_rate':
                            clock_rates[machine_id] = int(value)
                        elif key.strip() == 'internal_prob':
                            internal_probs[machine_id] = float(value)
    
    print("\nMachine Clock Rates:")
    for machine_id, rate in clock_rates.items():
        print(f"Machine {machine_id}: {rate} ticks/second")
    
    if internal_probs:
        print("\nInternal Event Probabilities:")
        for machine_id, prob in internal_probs.items():
            print(f"Machine {machine_id}: {prob:.2f}")
    
    # Analyze logical clock jumps
    print("\nLogical Clock Jumps:")
    for machine_id, df in machine_data.items():
        jumps = []
        for i in range(1, len(df)):
            prev_clock = df.iloc[i-1]['logical_clock']
            curr_clock = df.iloc[i]['logical_clock']
            jump = curr_clock - prev_clock
            if jump > 1:
                jumps.append(jump)
        
        if jumps:
            avg_jump = sum(jumps) / len(jumps)
            max_jump = max(jumps)
            print(f"Machine {machine_id}: {len(jumps)} jumps, Avg: {avg_jump:.2f}, Max: {max_jump}")
        else:
            print(f"Machine {machine_id}: No jumps detected")
    
    # Analyze queue sizes
    print("\nMessage Queue Analysis:")
    for machine_id, df in machine_data.items():
        avg_queue = df['queue_size'].mean()
        max_queue = df['queue_size'].max()
        print(f"Machine {machine_id}: Avg queue size: {avg_queue:.2f}, Max: {max_queue}")
    
    # Analyze clock drift
    print("\nLogical Clock Drift Analysis:")
    # Create a common timeline
    min_time = min(df['timestamp'].min() for df in machine_data.values())
    max_time = max(df['timestamp'].max() for df in machine_data.values())
    
    # Sample points for comparison
    sample_points = np.linspace(min_time, max_time, 10)
    
    # Interpolate logical clock values at sample points
    clock_values = defaultdict(list)
    for point in sample_points:
        for machine_id, df in machine_data.items():
            # Find closest timestamp
            closest_idx = (df['timestamp'] - point).abs().idxmin()
            clock_values[machine_id].append(df.loc[closest_idx, 'logical_clock'])
    
    # Calculate drift between machines
    for i in range(len(sample_points)):
        point_time = sample_points[i]
        values = [clock_values[machine_id][i] for machine_id in sorted(machine_data.keys())]
        max_diff = max(values) - min(values)
        print(f"At {point_time:.2f}s: Max drift between machines: {max_diff}")
    
    # Generate plots
    plot_dir = f"{experiment_dir}/plots"
    os.makedirs(plot_dir, exist_ok=True)
    
    # Plot logical clocks over time
    plt.figure(figsize=(12, 6))
    for machine_id, df in machine_data.items():
        plt.plot(df['timestamp'] - min_time, df['logical_clock'], 
                 label=f"Machine {machine_id} (Rate: {clock_rates.get(machine_id, 'Unknown')})")
    
    plt.xlabel('Time (seconds)')
    plt.ylabel('Logical Clock Value')
    plt.title('Logical Clock Progression')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{plot_dir}/logical_clocks.png")
    
    # Plot queue sizes over time
    plt.figure(figsize=(12, 6))
    for machine_id, df in machine_data.items():
        plt.plot(df['timestamp'] - min_time, df['queue_size'], 
                 label=f"Machine {machine_id} (Rate: {clock_rates.get(machine_id, 'Unknown')})")
    
    plt.xlabel('Time (seconds)')
    plt.ylabel('Queue Size')
    plt.title('Message Queue Sizes')
    plt.legend()
    plt.grid(True)
    plt.savefig(f"{plot_dir}/queue_sizes.png")
    
    # Plot event distribution
    plt.figure(figsize=(12, 6))
    for machine_id, df in machine_data.items():
        event_counts = df['event_type'].value_counts()
        plt.bar(
            [f"{event} (M{machine_id})" for event in event_counts.index], 
            event_counts.values,
            alpha=0.7,
            label=f"Machine {machine_id}"
        )
    
    plt.xlabel('Event Type')
    plt.ylabel('Count')
    plt.title('Event Distribution')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{plot_dir}/event_distribution.png")
    
    print(f"\nPlots saved to {plot_dir}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_logs.py <experiment_dir> [experiment_dir2 ...]")
        print("       python analyze_logs.py all")
        sys.exit(1)
    
    if sys.argv[1] == "all":
        # Analyze all experiment directories
        experiment_dirs = glob.glob("logs/*/")
        if not experiment_dirs:
            print("No experiment directories found in logs/")
            sys.exit(1)
    else:
        # Analyze specified experiment directories
        experiment_dirs = sys.argv[1:]
        # Ensure all directories exist
        for exp_dir in experiment_dirs:
            if not os.path.isdir(exp_dir):
                print(f"Directory not found: {exp_dir}")
                sys.exit(1)
    
    for exp_dir in experiment_dirs:
        analyze_experiment(exp_dir)
    
    print("\nAnalysis complete!")

if __name__ == "__main__":
    main() 