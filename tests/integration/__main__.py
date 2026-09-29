from . import run_integration_test, get_test_stats

def main():
	"""Run all integration tests for the translate_infrequent module."""

  # Test cases: (input_string, args, expected_output)
	test_phrase = "Muss mein Yak rasieren"
	test_cases = [
		(
			test_phrase,
			[("-l", "de"), ("-w", "1")],
			"Muss mein {my} Yak rasieren {shave}" # note that "Muss" and "Yak" don't have translations noted, because of high degree of similarity
		),
		(
			test_phrase,
			[("-l", "de"), ("-w", "10_000")],
			"Muss mein Yak rasieren {shave}"
		),
		(
			test_phrase,
			[("-l", "de"), ("-w", "100_000")],
			"Muss mein Yak rasieren"
		),
		(
			test_phrase,
			[("-l", "de"), ("-w", "1"), ("-b", "ask_llm")],
			"Muss mein {my} Yak rasieren {shave}"
		),
		(
			test_phrase,
			[("-l", "de"), ("-w", "10_000"), ("-b", "ask_llm")],
			"Muss mein Yak rasieren {to shave}"
		),
	]

	print("Running integration tests for translate_infrequent")
	print("=" * 60)

	for input_string, args, expected_output in test_cases:
		run_integration_test(input_string, args, expected_output)

	passed, total = get_test_stats()
	print("=" * 60)
	print(f"Results: {passed}/{total} tests passed")

	if passed == total:
		print("All tests passed!")
		return 0
	else:
		print("Some tests failed!")
		return 1

if __name__ == "__main__":
	exit(main())
