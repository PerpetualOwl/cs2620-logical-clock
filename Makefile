.PHONY: run run_all analyze clean

# Default port to use
PORT = 8000

# Default number of machines
MACHINES = 3

# Default duration in seconds
DURATION = 60

# Run a single experiment
run:
	python run_system.py run --machines=$(MACHINES) --port=$(PORT) --duration=$(DURATION)

# Run all required experiments
run_all:
	python run_system.py run_all

# Analyze experiment results
analyze:
	python analyze_logs.py all

# Clean logs and plots
clean:
	rm -rf logs/

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	python -m unittest discover -s tests

# Help message
help:
	@echo "Available targets:"
	@echo "  make run         - Run a single experiment"
	@echo "  make run_all     - Run all required experiments"
	@echo "  make analyze     - Analyze all experiment results"
	@echo "  make clean       - Remove all logs and plots"
	@echo "  make install     - Install dependencies"
	@echo "  make test        - Run tests"
	@echo ""
	@echo "Parameters for 'make run':"
	@echo "  MACHINES=N       - Number of machines (default: 3)"
	@echo "  PORT=N           - Base port number (default: 8000)"
	@echo "  DURATION=N       - Duration in seconds (default: 60)"
	@echo ""
	@echo "Example:"
	@echo "  make run MACHINES=4 DURATION=120" 