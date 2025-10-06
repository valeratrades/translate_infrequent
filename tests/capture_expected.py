#!/usr/bin/env python3
"""
Helper script to capture actual outputs for integration tests.
Run this when dependencies are installed to populate expected outputs.
"""

import subprocess
import sys
import os

def capture_output(input_string, args):
	"""Capture actual output for given input and args."""
	cmd = [sys.executable, "-m", "src"]
	for flag, value in args:
		cmd.extend([flag, str(value)])
	project_root = os.path.join(os.path.dirname(__file__), '..')

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
			return f"ERROR: {stderr}"
		else:
			return stdout.strip()

	except Exception as e:
		return f"EXCEPTION: {e}"

def main():
	"""Capture all expected outputs."""
	test_phrase = "Muss mich rasieren, igitt"

	test_cases = [
		[("-l", "de"), ("-w", "0")],
		[("-l", "de"), ("-w", "1")],
		[("-l", "de"), ("-w", "10")],
		[("-l", "de"), ("-w", "100")],
		[("-l", "de"), ("-w", "1000")],
		[("-l", "de"), ("-w", "100000")],
	]

	print("Capturing expected outputs for integration tests")
	print("=" * 60)
	print(f"Input phrase: '{test_phrase}'")
	print()

	for args in test_cases:
		output = capture_output(test_phrase, args)
		args_str = ' '.join(f"{flag} {value}" for flag, value in args)
		print(f"{args_str}: {repr(output)}")

	print()
	print("Copy these outputs to update the test_cases in __main__.py")

if __name__ == "__main__":
	main()