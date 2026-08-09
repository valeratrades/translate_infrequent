import subprocess
import sys
import os

# Global test counters
_test_count = 0
_passed_count = 0

def run_integration_test(input_string, args, expected_output):
	"""
	Run an integration test by calling the main module with given args and input.

	Args:
		input_string (str): The input text to pass to stdin
		args (list): List of (flag, value) tuples (e.g., [("-l", "de"), ("-w", "10")])
		expected_output (str): The expected output string

	Returns:
		bool: True if test passes, False otherwise
	"""
	global _test_count, _passed_count
	_test_count += 1

	# Build command line arguments from tuples
	cmd = [sys.executable, "-m", "src"]
	for flag, value in args:
		cmd.extend([flag, str(value)])

	# Get project root (two levels up from this file)
	project_root = os.path.join(os.path.dirname(__file__), '..', '..')

	try:
		process = subprocess.Popen(
			cmd,
			stdin=subprocess.PIPE,
			stdout=subprocess.PIPE,
			stderr=subprocess.PIPE,
			text=True,
			cwd=project_root
		)

		stdout, stderr = process.communicate(input=input_string)

		if process.returncode != 0:
			print(f"FAIL: Command failed with return code {process.returncode}")
			print(f"Command: {' '.join(cmd)}")
			print(f"stderr: {stderr}")
			return False

		actual_output = stdout.strip()

		if actual_output == expected_output:
			_passed_count += 1
			args_str = ' '.join(f"{flag} {value}" for flag, value in args)
			print(f"\n{_test_count}) \033[32mPASS\033[0m: {args_str}\n")
			return True
		else:
			args_str = ' '.join(f"{flag} {value}" for flag, value in args)
			print(f"\n{_test_count}) \033[31mFAIL\033[0m: {args_str}")
			print(f"Input: {repr(input_string)}")
			print(f"Expected: {repr(expected_output)}")
			print(f"Actual:   {repr(actual_output)}\n")
			return False

	except Exception as e:
		args_str = ' '.join(f"{flag} {value}" for flag, value in args)
		print(f"\n{_test_count}) \033[31mFAIL\033[0m: {args_str}")
		print(f"Exception: {e}")
		print(f"Command: {' '.join(cmd)}\n")
		return False

def get_test_stats():
	"""Get current test statistics."""
	return _passed_count, _test_count