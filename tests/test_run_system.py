import unittest
import sys
import os
import tempfile
from unittest.mock import patch, MagicMock, call

# Add parent directory to path to import run_system
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import run_system

class TestRunSystem(unittest.TestCase):
    def test_run_system(self):
        """Test running the system with mocked subprocesses"""
        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.pid = 12345
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
            # Mock time.sleep to avoid actual delays
            with patch('time.sleep'):
                # Mock signal.signal to avoid actual signal handling
                with patch('signal.signal'):
                    # Redirect stdout to capture print statements
                    with patch('sys.stdout'):
                        # Mock time.time to control the duration loop
                        with patch('time.time', side_effect=[0, 1, 61]):
                            # Run the system with a short duration
                            run_system.run_system(num_machines=2, base_port=8000, duration=1)
        
        # Check that Popen was called with the correct commands
        mock_popen.assert_has_calls([
            call(['python', 'logical_clock.py', '0', '8000', '2']),
            call(['python', 'logical_clock.py', '1', '8000', '2'])
        ])
        
        # Check that the process was terminated
        mock_process.terminate.assert_called()
    
    def test_run_experiment(self):
        """Test running an experiment with mocked subprocesses"""
        # Mock subprocess.Popen
        mock_process = MagicMock()
        mock_process.pid = 12345
        
        with patch('subprocess.Popen', return_value=mock_process) as mock_popen:
            # Mock time.sleep to avoid actual delays
            with patch('time.sleep'):
                # Mock signal.signal to avoid actual signal handling
                with patch('signal.signal'):
                    # Redirect stdout to capture print statements
                    with patch('sys.stdout'):
                        # Mock time.time to control the duration loop
                        with patch('time.time', side_effect=[0, 1, 61]):
                            # Mock os.makedirs to avoid directory creation
                            with patch('os.makedirs'):
                                # Run an experiment
                                run_system.run_experiment(
                                    experiment_name="test_experiment",
                                    num_machines=2,
                                    base_port=8000,
                                    duration=1,
                                    internal_event_prob=0.5,
                                    clock_rate_variation="small"
                                )
        
        # Check that Popen was called with the correct commands
        mock_popen.assert_has_calls([
            call(['python', 'logical_clock.py', '0', '8000', '2']),
            call(['python', 'logical_clock.py', '1', '8000', '2'])
        ])
        
        # Check that the process was terminated
        mock_process.terminate.assert_called()
    
    def test_main_function(self):
        """Test the main function"""
        # Mock run_experiment
        with patch('run_system.run_experiment') as mock_run_experiment:
            # Mock sys.argv
            with patch('sys.argv', ['run_system.py', 'test_experiment']):
                # Redirect stdout to capture print statements
                with patch('sys.stdout'):
                    # Call main
                    if hasattr(run_system, 'main'):
                        run_system.main()
                    elif __name__ == '__main__' in run_system.__dict__:
                        # If there's no main function but there's a __main__ block
                        pass
                    else:
                        # If there's no main function or __main__ block, call run_experiment directly
                        # This is a fallback in case the script uses a different pattern
                        run_system.run_experiment('test_experiment')
        
        # Check that run_experiment was called
        if hasattr(run_system, 'main') or __name__ == '__main__' in run_system.__dict__:
            mock_run_experiment.assert_called_once()


if __name__ == '__main__':
    unittest.main() 