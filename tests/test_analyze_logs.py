import unittest
import sys
import os
import pandas as pd
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path to import analyze_logs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analyze_logs

class TestAnalyzeLogs(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test log files
        self.test_dir = tempfile.TemporaryDirectory()
        
        # Create sample log files
        self.create_sample_log_files()
    
    def tearDown(self):
        # Clean up the temporary directory
        self.test_dir.cleanup()
    
    def create_sample_log_files(self):
        """Create sample log files for testing"""
        # Machine 0 log
        with open(os.path.join(self.test_dir.name, "machine_0.log"), "w") as f:
            f.write("START,1234567890.0,0,0,clock_rate=1;internal_prob=0.7\n")
            f.write("INTERNAL,1234567890.1,0,1\n")
            f.write("SEND,1234567890.2,0,2,all peers\n")
            f.write("INTERNAL,1234567890.3,0,3\n")
        
        # Machine 1 log
        with open(os.path.join(self.test_dir.name, "machine_1.log"), "w") as f:
            f.write("START,1234567890.0,0,0,clock_rate=2;internal_prob=0.7\n")
            f.write("INTERNAL,1234567890.1,0,1\n")
            f.write("RECEIVE,1234567890.2,0,3\n")
            f.write("SEND,1234567890.3,0,4,peer(s) [0]\n")
        
        # Machine 2 log
        with open(os.path.join(self.test_dir.name, "machine_2.log"), "w") as f:
            f.write("START,1234567890.0,0,0,clock_rate=3;internal_prob=0.7\n")
            f.write("RECEIVE,1234567890.2,0,3\n")
            f.write("INTERNAL,1234567890.3,0,4\n")
            f.write("INTERNAL,1234567890.4,0,5\n")
    
    def test_parse_log_file(self):
        """Test parsing a log file into a DataFrame"""
        log_file = os.path.join(self.test_dir.name, "machine_0.log")
        df = analyze_logs.parse_log_file(log_file)
        
        # Check that the DataFrame has the correct structure
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 4)  # 4 log entries
        
        # Check that the columns are correct
        expected_columns = ['event_type', 'timestamp', 'queue_size', 'logical_clock', 'additional_info']
        self.assertListEqual(list(df.columns), expected_columns)
        
        # Check the values of the first row
        first_row = df.iloc[0]
        self.assertEqual(first_row['event_type'], 'START')
        self.assertEqual(first_row['timestamp'], 1234567890.0)
        self.assertEqual(first_row['queue_size'], 0)
        self.assertEqual(first_row['logical_clock'], 0)
        self.assertEqual(first_row['additional_info'], 'clock_rate=1;internal_prob=0.7')
    
    def test_analyze_experiment(self):
        """Test analyzing an experiment directory"""
        # Patch plt.show to prevent plots from being displayed
        with patch('matplotlib.pyplot.show'):
            # Patch plt.savefig to prevent files from being saved
            with patch('matplotlib.pyplot.savefig'):
                # Call analyze_experiment
                analyze_logs.analyze_experiment(self.test_dir.name)
    
    def test_analyze_experiment_no_logs(self):
        """Test analyzing an experiment directory with no log files"""
        # Create an empty directory
        empty_dir = tempfile.TemporaryDirectory()
        
        # Redirect stdout to capture print statements
        with patch('sys.stdout'):
            # Call analyze_experiment
            analyze_logs.analyze_experiment(empty_dir.name)
        
        # Clean up
        empty_dir.cleanup()
    
    def test_main_function(self):
        """Test the main function"""
        # Mock sys.argv
        with patch('sys.argv', ['analyze_logs.py', self.test_dir.name]):
            # Patch plt.show to prevent plots from being displayed
            with patch('matplotlib.pyplot.show'):
                # Patch plt.savefig to prevent files from being saved
                with patch('matplotlib.pyplot.savefig'):
                    # Call main
                    analyze_logs.main()


if __name__ == '__main__':
    unittest.main() 