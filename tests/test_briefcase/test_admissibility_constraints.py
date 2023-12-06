from pathlib import Path
import pytest
import yaml
from briefcase import Case, CaseBase, PriorityOrder
from collections import Counter


# Define a fixture to load test cases from the YAML file
@pytest.fixture
def test_cases():
    test_data_path = Path(__file__).parent / 'test_data' / 'test_admissibility_constraints.yaml'
    with open(test_data_path, 'r') as file:
        return yaml.safe_load(file)


@pytest.mark.parametrize(
    "test_case_name",
    [
        "all",
        "no_new",
        "no_involvement",
        "no_corruption"
    ],
)
def test_is_case_admissible(test_cases, test_case_name):
    cs = test_cases[test_case_name]['cases']
    ads = test_cases[test_case_name]['adds']
    fs = test_cases[test_case_name]['fails']
    constraint = test_cases[test_case_name]['name']

    cases = [Case.from_dict(c) for c in cs]
    adds = [Case.from_dict(c) for c in ads]
    fails = [Case.from_dict(c) for c in fs]

    cb1 = CaseBase(cases)
    fails_results = []
    i = 0
    for case in adds:
        if not cb1.add_case(case, constraint):
            fails_results.append(case)
            print(case)
            print()
            print(fails[i])
            i = i + 1

    assert fails == fails_results