import argparse
import copy

import yaml
import networkx as nx

from enum import Enum
from pathlib import Path
from collections import defaultdict

# Decisions are either for side pi, for side delta, or undecided
# Pi = child can have dessert
# Delta = child cannot have dessert# Undecided = ?
decision_enum = Enum("Decision", ["pi", "delta", "un"])


class Factor:
    """Class describing a factor which contributes to a decision
    e.g. factor 1, name = "child ate their dinner", polarity = pi (child can have dessert)
    """

    def __init__(self, name, polarity="un"):
        """
        @param name: name of the given factor
        @param polarity: the result of the decision (pi/delta/undecided)
        """
        self.name = name
        self.polarity = polarity

    def __eq__(self, other):
        """
        @param other: second factor, to compare instance factor to
        @return: override equality return based on factor name and factor polarity
        """
        if type(other) is type(self):
            return self.name == other.name and self.polarity == other.polarity
        else:
            return False

    def __hash__(self):
        """
        @return: override hash of factor based on factor name and factor polarity
        """
        return hash(self.name + str(self.polarity))

    def __str__(self):
        """
        @return: String representation of the Factor for human-readable output
        """

        return f"Factor: {self.name}, Polarity: {self.polarity}"

    def __repr__(self):
        """
        @return: String representation of the Factor for recreation
        """

        return f"Factor('{self.name}', '{self.polarity}')"


class Case:
    """
    Class describing a case
    e.g. case 1
    pi_factors = [name="The child ate their dinner", polarity=pi]
    delta_factors = [name="The child didn't do their homework", polarity=delta]
    the decision = pi
    reason = [name="The child ate their dinner", polarity=pi]
    """

    @classmethod
    def from_dict(cls, dic):
        """
        @param dic: a dictionary of 'pi', 'delta' and 'reason' factor lists, and a 'decision'
        @return: An instance of the Case class based on the dic.
        Converts pi, delta, and reason factor lists to frozensets (immutable sets) of tuples of each
        factor name and the polarity.
        """
        pi_factors = frozenset((Factor(f, decision_enum.pi) for f in dic["pi"]))
        delta_factors = frozenset(
            (Factor(f, decision_enum.delta) for f in dic["delta"])
        )

        # Check decision is valid
        try:
            decision_value = decision_enum[dic["decision"]]
        except KeyError as e:
            raise KeyError(
                f"The key 'decision' with value '{dic['decision']}' is not found in the decision_enum (pi/delta)."
            ) from e

        reason_factors = frozenset((Factor(f, decision_value) for f in dic["reason"]))

        # Check reason is valid
        winning_factors = (
            pi_factors if decision_value == decision_enum.pi else delta_factors
        )
        if not reason_factors.issubset(winning_factors):
            raise ValueError(
                f"reason_factors is not a subset of the winning_factors with the polarity {decision_value}"
            )

        return cls(pi_factors, delta_factors, decision_value, reason_factors)

    def __init__(
        self,
        pi_factors=frozenset(),
        delta_factors=frozenset(),
        decision=decision_enum.un,
        reason=frozenset(),
    ):
        """I think we can have as a degenerate case a pure decision, that is, one with no factors
        and thus no reasons. Alternatively, we could force all such to be undecided.

        If we allow nominal typing, then degenerate cases can be meaningfully different. We might use
        a general rule to express burden of proof, e.g., that we default for the defense.

        We might want to have an additional typology of cases to allow different burden of proofs for
        different sorts of cases, e.g., civil vs. criminal."""

        self.pi_factors = pi_factors
        self.delta_factors = delta_factors
        self.decision = decision
        self.reason = reason

    def defeated(self):  # TODO: make property
        """
        @return: the factors which were defeated by the decision e.g. for a decision of polarity pi, the delta factors
        """
        if self.decision == decision_enum.pi:
            return self.delta_factors
        elif self.decision == decision_enum.delta:
            return self.pi_factors
        else:
            return (
                set()
            )  # TODO: Throw error? ... Already happens further up, ths code would never be reached

    def relevant_diff_from(self, other_case):
        """All factors have a singleton dimension and thus
        any individual factor"""
        # TODO: Look up what relevant differences are again
        if self.decision == other_case.decision:
            pass

    def __str__(self):
        """
        @return: String representation of the Case for human-readable output
        """

        pi_factors_str = [str(factor) for factor in self.pi_factors]
        delta_factors_str = [str(factor) for factor in self.delta_factors]
        decision_str = f"Decision: {self.decision.name}"
        reason_str = [str(factor) for factor in self.reason]
        return (
            f"Case:\n  Pi Factors: {', '.join(pi_factors_str)}\n  Delta Factors: {', '.join(delta_factors_str)}\n  "
            f"{decision_str}\n  Reasons: {', '.join(reason_str)}"
        )

    def __repr__(self):
        """
        @return: String representation of the Case for recreation
        """
        pi_factors_repr = [repr(factor) for factor in self.pi_factors]
        delta_factors_repr = [repr(factor) for factor in self.delta_factors]
        decision_repr = (
            f"Decision.{self.decision.name}"  # Assuming 'decision' is an enum
        )
        reason_repr = [repr(factor) for factor in self.reason]
        return f"""Case(Pi Factors: {pi_factors_repr}, Delta Factors: {delta_factors_repr}, {
        decision_repr}, Reasons: {reason_repr})"""


class PriorityOrder:
    """
    Orders reasons and factors in a dictionary.
    Key is a frozenset of the stronger factors, value is a frozenset of the weaker factors.
    """

    def __init__(self):
        # default-dict does not error when referencing a key which doesn't exist
        self.order = defaultdict(set)
        self.subsets = defaultdict(set)

    def is_consistent(self, reason, defeated):
        """
        @param reason: a frozenset of factors
        @param defeated: a frozenset of factors, weaker than the reason
        @return: True/False if this reason being stronger than this defeated is consistent with
                the cb order
        """
        # Focus on the new defeated, is this a superset of any existing case's reason?
        # Get these cases using the subset dict
        for factor in defeated:
            d_supersets = {r for r in self.subsets[factor] if r.issubset(defeated)}
            # loop through these supersets, looking for the case in the keys of the casebase (reasons)
            # then check if the new reason is a subset of the existing defeated... inconsistent
            for d in d_supersets:
                old_defeated = self.order[d]
                if any(reason.issubset(d) for d in old_defeated):
                    return False

        return True

    def is_cb_consistent(self):
        """
        @return : True/False if current ordering of the cb order is consistent
        """
        # loop through all cases in order
        for reason, defeated_set in self.order.items():
            for defeated in defeated_set:
                if not self.is_consistent(reason, defeated):
                    return False
        return True

    def is_case_consistent_with(self, case):
        """
        @param case: a new case
        @return: True/False if the current cb order would be consistent with a new case added
        """
        # assert self.is_consistent()  # TODO: is this what we want?

        # New case
        reason = case.reason
        defeated = case.defeated()

        return self.is_consistent(reason, defeated)

    def add_pair_as_appropriate(self, r1, r2):
        """
        @param r1: first reason
        @param r2: second reason
        Adds pairs of reasons to the priority order dictionary, where stronger reason : weaker reason
        within the dictionary 'order'
        """
        if r1 == r2:
            return
        if r1.issubset(r2):  # then r2 is at least as strong as r1
            # Potentially a bit slow for large reasons? could check for polarity first.
            self.add_order_with_subsets(r2, r1)
            # self.order[r2].add(r1)
            # ds has to be of opposite polarity thus disjoint from the reason
        elif r2.issubset(r1):
            self.add_order_with_subsets(r1, r2)
            # self.order[r1].add(r2)

    def unsafe_add_cases(self, cases):
        """
        @param cases: multiple cases to add to the order
        """
        for c in cases:
            self.unsafe_add_case(c)

    def unsafe_add_case(self, case):
        """
        @param case: the new case to be added to the priority order
        Adds a new case to order dict with no safety checks.
        """
        # case 1: we know the winning reason is at least as strong as the defeated factors, since it won
        # self.order[case.reason].add(case.defeated())
        self.add_order_with_subsets(case.reason, case.defeated())
        for r, ds in list(self.order.items()):
            # case 2: check if winning reason is stronger than other winning reasons in the dictionary
            self.add_pair_as_appropriate(case.reason, r)
            # Because we don't do a polarity check, we have to test *all* ds...boo)
            for d in ds:
                # case 3: check if winning reason is stronger than other defeated reasons in the dictionary
                self.add_pair_as_appropriate(case.reason, d)

    def add_order_with_subsets(self, reason, defeated):
        """
        @param reason: a frozenset of factors
        @param defeated: a frozenset of factors, weaker than the reason
        Adds reason: defeated to the cb order.
        Adds for all factors within the reason as keys to subsets
        """
        self.order[reason].add(defeated)

        for factor in reason:
            self.subsets[factor].add(reason)

    def newly_inconsistent_with(self, case):
        pass

    def inconsistent_pairs(self):
        pass

    def str_order(self):
        """
        @return: String representation of the PriorityOrder for human-readable output
        """
        cases_str = []
        for winning, defeated in self.order.items():
            cases_str.append("Reason: " + str(winning) + ", Defeated: " + str(defeated))
        cases_formatted = "\n".join(cases_str)
        return f"\nPriority Order:\n{cases_formatted}"


class CaseBase:
    def __init__(self, caselist=[]):
        self.cases = caselist
        self.order = PriorityOrder()
        self.order.unsafe_add_cases(self.cases)

    def add_case(self, case):
        self.cases.append(case)
        self.order.unsafe_add_case(case)

    def is_consistent(self):
        return self.order.is_cb_consistent()

    def is_consistent_with(self, case):
        return self.order.is_case_consistent_with(case)

    def __str__(self):
        """
        @return: String representation of the CaseBase for human-readable output
        """
        cases_str = [str(case) for case in self.cases]
        cases_formatted = "\n\n".join(cases_str)
        return f"CaseBase:\n{cases_formatted}"

    def __repr__(self):
        """
        @return: String representation of the CaseBase for recreation
        """
        cases_repr = [repr(case) for case in self.cases]
        return f"CaseBase({cases_repr})"


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
