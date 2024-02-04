from pathlib import Path
import pytest
import yaml

from briefcase.enums import decision_enum
from briefcase.factor import Factor
from briefcase.case import Case

# Define a fixture to load test cases from the YAML file
@pytest.fixture
def test_cases():
    test_data_path = Path(__file__).parent / 'test_data' / 'test_relevant_diffs.yaml'
    with open(test_data_path, 'r') as file:
        return yaml.safe_load(file)


# Define the tests using the loaded test cases
# @pytest.mark.parametrize(
#     "test_case_name",
#     [
#         "small_same_outcome",
#         "small_different_outcome",
#         "big_same_outcome",
#         "big_different_outcome"
#     ],
# )
# def test_relevant_differences(test_cases, test_case_name):
#     cs = test_cases[test_case_name]
#     case1 = Case.from_dict(cs["case1"])
#     factors = {Factor(name, decision_enum[polarity]) for name, polarity in cs["diff"].items()}
#     assert case1.relevant_diff_from(Case.from_dict(cs["case2"])) == frozenset(factors)



