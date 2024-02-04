import argparse
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A tool to do precedential case reasoning."
    )
    parser.add_argument(
        "-c", "--casebase", type=Path, help="a file containing a case base"
    )
    parser.add_argument(
        "-n", "--newcase", type=Path, help="file containing a case not in the base"
    )
    parser.add_argument(
        "-a",
        "--action",
        type=str,
        default="test",
        help='indicates the preferred action: "check" (default), or "add" (if consistent) or "test" (default) for run tests',
    )

    args = parser.parse_args()

    import doctest

    doctest.testfile("example_tests.txt")
