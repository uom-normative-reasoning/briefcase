from pathlib import Path
import pytest
import yaml

from briefcase.case_base import CaseBase
from briefcase.enums import decision_enum
from briefcase.factor import Factor
from briefcase.case import Case


# Define a fixture to load test cases from the YAML file
@pytest.fixture
def test_cases():
    test_data_path = Path(__file__).parent / 'test_data' / 'test_strength.yaml'
    with open(test_data_path, 'r') as file:
        return yaml.safe_load(file)


@pytest.mark.parametrize(
    "test_case_name",
    [
        "test_factor_add",
    ],
)
def test_factorlist_add(test_cases, test_case_name):
    cs = test_cases[test_case_name]
    new_cases = cs['cases']
    cases = [Case.from_dict(c) for c in new_cases]
    cb1 = CaseBase(cases)
    assert frozenset(cb1.order.PD.factor_list[decision_enum.pi]) == frozenset(
        Factor(f, decision_enum.pi) for f in cs['pi'])
    assert frozenset(cb1.order.PD.factor_list[decision_enum.delta]) == frozenset(
        Factor(f, decision_enum.delta) for f in cs['delta'])


@pytest.mark.parametrize(
    "test_case_name",
    [
        "test_strength",
    ],
)
def test_power_case(test_cases, test_case_name):
    cs = test_cases[test_case_name]
    historic_cases = cs['historic_case']
    cases = [Case.from_dict(c) for c in historic_cases]
    cb1 = CaseBase(cases)
    new_cases = cs['cases']
    strengths = cs['strengths']
    for i, case in enumerate(new_cases):
        assert cb1.order.PD.case_power(Case.from_dict(case)) == strengths[i]


@pytest.mark.parametrize(
    "test_case_name",
    [
        "test_cb_strength_small",
    ],
)
def test_power(test_cases, test_case_name):
    cb3 = CaseBase()
    cs = test_cases[test_case_name]
    new_cases = [Case.from_dict(c) for c in cs['cases']]
    strengths = cs['strength_cumulative']
    for i, case in enumerate(new_cases):
        cb3.add_case(case)
        assert cb3.order.PD.cb_power() == strengths[i]


@pytest.mark.parametrize(
    "test_case_name",
    [
        "test_strength",
    ],
)
def test_power_cb_singleton_case(test_cases, test_case_name):
    cs = test_cases[test_case_name]
    new_cases = cs['cases']
    for i, case in enumerate(new_cases):
        new_case = Case.from_dict(case)

        cb2 = CaseBase([])
        empty_powers = cb2.order.PD.case_power(new_case)
        cb2.add_case(new_case)

        assert cb2.order.PD.cb_power() == empty_powers
