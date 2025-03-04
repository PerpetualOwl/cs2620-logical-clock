# Logical Clock System

This project implements a model of a small, asynchronous distributed system with logical clocks. The system consists of multiple virtual machines running at different clock rates, communicating with each other via sockets.

## Overview

Each virtual machine in the system:
- Runs at a random clock rate (1-6 ticks per second by default)
- Maintains a logical clock that follows Lamport's logical clock rules
- Communicates with other machines via sockets
- Logs all events (internal events, message sends, and message receives)

The system allows for experimentation with different parameters:
- Clock rate variation (normal: 1-6 ticks/second or small: 3-4 ticks/second)
- Probability of internal events vs. communication events
- Number of machines in the system
- Duration of experiments

## Requirements

- Python 3.6 or higher
- Required Python packages (install with `pip install -r requirements.txt`):
  - pandas
  - matplotlib
  - numpy

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/PerpetualOwl/cs2620-logical-clock.git
   cd cs2620-logical-clock
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the System

### Using the Makefile

The project includes a Makefile to simplify running experiments:

```
# Run a single experiment with default parameters
make run

# Run a single experiment with custom parameters
make run MACHINES=4 DURATION=120

# Run all required experiments (5 trials of original model, small variation, small internal probability)
make run_all

# Analyze experiment results
make analyze

# Clean logs and plots
make clean

# Show help
make help
```

### Using Python Directly

You can also run the system directly using Python:

```
# Run a single experiment
python run_system.py run --machines=3 --duration=60

# Run all required experiments
python run_system.py run_all

# Analyze experiment results
python analyze_logs.py all
```

## Experiment Types

The system supports several types of experiments:

1. **Original Model**: The default configuration with clock rates between 1-6 ticks/second and 70% probability of internal events.

2. **Small Clock Rate Variation**: Reduces the variation in clock rates to 3-4 ticks/second, which should result in less drift between machines.

3. **Small Internal Event Probability**: Reduces the probability of internal events to 40%, which should result in more communication between machines.

## Required Experiments

The assignment requires running the following experiments:

1. Run 5 trials of the original model for at least 1 minute each
2. Run an experiment with smaller variation in clock cycles
3. Run an experiment with smaller probability of internal events

You can run all these experiments with:
```
make run_all
```

## Analyzing Results

After running experiments, you can analyze the results using:
```
make analyze
```

This will:
- Parse all log files
- Calculate statistics on logical clock jumps, queue sizes, and clock drift
- Generate plots for each experiment
- Print a summary of the results

The analysis focuses on:
- **Jumps**: When a logical clock increases by more than 1 in a single step
- **Drift**: Differences in logical clock values between machines
- **Queue Sizes**: How many messages are waiting to be processed

## Log Files

Log files are stored in the `logs/` directory, organized by experiment. Each log file contains comma-separated values with the following format:

```
EVENT_TYPE,TIMESTAMP,QUEUE_SIZE,LOGICAL_CLOCK,ADDITIONAL_INFO
```

Where:
- `EVENT_TYPE` is one of: START, INTERNAL, SEND, RECEIVE
- `TIMESTAMP` is the system time in seconds
- `QUEUE_SIZE` is the current size of the message queue
- `LOGICAL_CLOCK` is the current logical clock value
- `ADDITIONAL_INFO` contains extra information about the event

## Engineering Notebook

When analyzing the results, pay attention to:

1. **Clock Jumps**: How often and by how much do logical clocks jump? What causes these jumps?

2. **Clock Drift**: How much do the logical clocks drift apart? Does the drift increase over time?

3. **Queue Sizes**: Do message queues grow over time? Which machines tend to have larger queues?

4. **Impact of Parameters**: How do different parameters (clock rate variation, internal event probability) affect the system?

Document your observations in your engineering notebook, including:
- Quantitative analysis of jumps, drift, and queue sizes
- Qualitative observations about system behavior
- Comparisons between different experiment types
- Interesting patterns or anomalies you discover

## Running Tests

To run the unit tests:
```
make test
```

Or directly:
```
python -m unittest discover -s tests
```

## Project Structure

- `logical_clock.py`: Main implementation of the virtual machine and logical clock
- `run_system.py`: Script to run experiments with multiple machines
- `analyze_logs.py`: Script to analyze experiment results
- `tests/`: Unit tests
- `logs/`: Experiment logs and plots
- `Makefile`: Simplifies running experiments and analysis
- `requirements.txt`: Python dependencies