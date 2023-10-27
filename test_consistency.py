import pytest
import yaml
from pathlib import Path
from briefcase import Case, CaseBase, PriorityOrder


# Define a fixture to load test cases from the YAML file
@pytest.fixture
def test_cases():
    test_cases_file = Path("test_case_base.yaml")
    with test_cases_file.open("r") as f:
        return yaml.safe_load(f)


@pytest.mark.parametrize(
    "test_name, error_type",
    [("error_case_bad_decision", KeyError), ("error_case_bad_reason", ValueError)],
)
def test_errors_case_from_dict(test_cases, test_name, error_type):
    with pytest.raises(error_type):
        Case.from_dict(test_cases[test_name])


def test_base_case_consistency(test_cases):
    cb1 = CaseBase([])  # no cases
    assert cb1.is_cb_consistent()
    case = Case.from_dict(test_cases["one_case"])  # one case
    cb1.add_case(case)
    assert cb1.is_cb_consistent()


# Define the tests using the loaded test cases
@pytest.mark.parametrize(
    "test_case_name",
    [
        "simple_small",
        "simple_big",
        "distractor_small",
        "subset_small",
        "subset_big",
        "multi_defeated_small",
        "multi_defeated_big",
        "mega_case_10",
        "combined_factors"
    ],
)
def test_consistency(test_cases, test_case_name):
    cs = test_cases[test_case_name]
    cases = [Case.from_dict(c) for c in cs[:-1]]  # don't include last case
    cb1 = CaseBase(cases)
    assert cb1.is_cb_consistent()

    inconsistent_case = Case.from_dict(cs[-1])

    assert not cb1.is_consistent_with(inconsistent_case)
    cb1.add_case(inconsistent_case)

    assert not cb1.is_cb_consistent()


# test add order with subsets references the same object to the order
@pytest.mark.parametrize(
    "test_case_name",
    [
        "simple_small",
        "simple_big"
    ],
)
def test_add_order_with_subsets_id(test_cases, test_case_name):
    cs = test_cases[test_case_name]
    case = Case.from_dict(cs[0])  # get first case
    order = PriorityOrder()  # blank priority order
    order.add_order_with_subsets(case.reason, case.defeated())  # add one element
    # check if items added, and that the id is the same id
    assert any(case.defeated() is obj for obj in order.order.keys())
    assert any(case.defeated() is obj for subset in order.defeated_factor_index.values() for obj in subset)



