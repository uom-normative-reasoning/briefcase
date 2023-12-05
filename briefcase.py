import argparse

from enum import Enum
from pathlib import Path
from collections import defaultdict

# Decisions are either for side pi, for side delta, or undecided
# Pi = child can have dessert
# Delta = child cannot have dessert
# Undecided = ?
decision_enum = Enum("Decision", ["pi", "delta", "un"])
incons_enum = Enum("Inconsistency", ["NO", "NO_NEW", "NO_INVOLVEMENT", "NO_CORRUPTION", "ALL"])


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
    pi_factors = frozenset{name="The child ate their dinner", polarity=pi}
    delta_factors = frozenset{name="The child didn't do their homework", polarity=delta}
    the decision = pi
    reason = name="The child ate their dinner", polarity=pi
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
                frozenset()
            )  # TODO: Throw error? ... Already happens further up, ths code would never be reached

    def relevant_diff_from(self, other_case):
        """
        @param: other_case
        @return: Set of factors which are relevant differences from the other_case to this case
        This returns a set of relevant differences for factors of binary dimensions
        """
        # outcome is the same
        if self.decision == other_case.decision:
            # get all reasons for the other_case which are not in this case
            return other_case.reason - self.reason
        else:  # outcome is different
            # get all defeated for the other_case which are not in this case
            return other_case.reason - self.defeated()

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

    def __eq__(self, other):
        if isinstance(other, Case):
            return (
                self.pi_factors == other.pi_factors and
                self.delta_factors == other.delta_factors and
                self.decision == other.decision and
                self.reason == other.reason
            )
        return False


class PriorityOrder:
    """
    Orders reasons and factors in a dictionary.
    Key is a frozenset of the stronger factors, value is a frozenset of the weaker factors.
    """

    def __init__(self):
        # default-dict does not error when referencing a key which doesn't exist

        # contains case base ordering with defeated stored as keys, and sets of reasons stored as values
        self.order = defaultdict(set)
        # defeated factor as key and a set of frozensets as values
        self.defeated_factor_index = defaultdict(set)


    def is_case_admissible(self, new_reason, new_defeated, incons):
        method_map = {
            incons_enum.NO: self.no_incons,
            incons_enum.NO_NEW: self.no_new_incons,
            incons_enum.NO_INVOLVEMENT: self.no_involvement_incons,
            incons_enum.NO_CORRUPTION: self.no_corruption_incons,
            incons_enum.ALL: lambda *args: True,
        }

        admissible_method = method_map.get(incons, None)
        if admissible_method:
            return admissible_method(new_reason, new_defeated)
        else:
            raise ValueError("Invalid inconsistency value")

    def no_incons(self, new_reason, new_defeated):
        """for Γ ∪ {C} there does not exist any cases C′, C′′ ∈ Γ ∪ {C} where C′ ‖ C ′′"""
        # create new case base, and check whether inconsistent (using STRICT inconsistency)
        # using existing functionality, 1) check whether CB is inconsistent
        if self.is_cb_consistent():
            # 2) check whether CB is consistent with the new case using STRICT inconsistency
            if self.is_consistent(new_reason, new_defeated):
                return True
        return False

    def no_new_incons(self, new_reason, new_defeated):
        """Priority order remains the same"""
        return self.is_existing_claim(new_reason, new_defeated)

    def no_involvement_incons(self, new_reason, new_defeated):
        """For all cases in the CB, the new case is not inconsistent with any case"""
        return self.is_consistent(new_reason, new_defeated)

    def no_corruption_incons(self,  new_reason, new_defeated):
        """For all cases in the CB the new case is only inconsistent with cases which are otherwise inconsistent"""

        for case_pairs in self.get_incons_pairs_with_case(new_reason, new_defeated):
            # check each of these cases is already inconsistent
            if self.is_consistent(case_pairs[0], case_pairs[1]):
                return False
        return True

    def is_existing_claim(self, new_reason, new_defeated):
        """Checks priority order remains the same"""
        # if there exists a case with a weaker than or equal to defeated
        for weaker_defeat in self.get_weaker_defeats(new_defeated):
            # and with a stronger or equal to reason
            if any(reason.issubset(new_reason) for reason in self.order[weaker_defeat]):
                return True
        return False

    def get_stronger_defeats(self, factor_set):
        # Retrieve all entries in defeated_factor_index for all factors within factor_set (defeats_that_intersect)
        # Cast existing set of references to a frozenset within a set
        defeats_that_intersect = {frozenset(self.defeated_factor_index[factor]) for factor in factor_set}

        # Find the intersection of all sets retrieved above, exploiting the references property
        # This gives us all sets of factors which are stronger than our factor_set - supersets
        # To optimise this, we order by size so that initially smaller sets are compared for intersections
        sorted_defeats_that_intersect = sorted(defeats_that_intersect, key=lambda x: len(x))
        supersets = frozenset.intersection(*sorted_defeats_that_intersect)

        return supersets

    def get_weaker_defeats(self, factor_set):
        # Retrieve all entries in defeated_factor_index which are weaker than a given factor set
        # This any factor sets containing any number of the factors in the factor set

        """
        How do I find all subsets of a factorset e.g. {d1, d2, d3},
        d1 ={{d1, d3}, {d1, d2}}
        d2 = {{d1, d2}, {d2, d5}}
        d3 = {{d1, d3}, {d4}}
        d4 = {{d4}}

        I don't think you can efficiently. Let's just loop through
        """

        # Initialize an empty set to store the union of all sets
        weaker_defeats = set()

        # Iterate through each factor in factor_set and update the union
        for factor in factor_set:
            candidate_weaker_defeats = self.defeated_factor_index[factor]
            for candidate in candidate_weaker_defeats:
                if candidate.issubset(factor_set):
                    weaker_defeats.add(candidate)

        return weaker_defeats

    def add_order_with_subsets(self, reason, defeated):
        """
        @param reason: a frozenset of factors
        @param defeated: a frozenset of factors, weaker than the reason
        Adds defeated: reason to the cb order.
        Adds all factors within the defeated set to the defeated_subsets dictionary with the
        defeated frozenset as key and a set of frozensets as values
        """
        self.order[defeated].add(reason)

        for factor in defeated:
            self.defeated_factor_index[factor].add(defeated)

    def is_consistent(self, new_reason, new_defeated):
        """
        @param new_reason: a frozenset of factors
        @param new_defeated: a frozenset of factors, weaker than the reason
        @return: True/False if for the new_reason being stronger than the new_defeated,
                this causes inconsistency with the existing Case Base order
        """
        supersets = self.get_stronger_defeats(new_reason)

        # Looking at each (defeated) superset within the set of supersets,
        # Retrieve the (reason) entry in the existing order dictionary - this will be a set of reasons for each
        # Intersecting case
        reasons_sets = [self.order[superset] for superset in supersets]

        # If for any of the existing reasons sets retrieved, if the new defeated is a superset of one of
        # the sets of old reasons, return True (inconsistent)
        return not any(any(reason.issubset(new_defeated) for reason in reasons) for reasons in reasons_sets)

    def get_incons_pairs_with_case(self, new_reason, new_defeated):
        """
        @param new_reason: a frozenset of factors
        @param new_defeated: a frozenset of factors, weaker than the reason
        @return: list of pairs of reasons, defeated which are inconsistent with a new case
        """

        supersets = self.get_stronger_defeats(new_reason)
        case_sets = [(self.order[superset], superset) for superset in supersets]

        incons_pairs = []
        for case in case_sets:
            reasons = case[0]
            defeated = case[1]
            for reason in reasons:
                if reason.issubset(new_defeated):
                    incons_pairs.append((reason, defeated))

        return incons_pairs

    def is_cb_consistent(self):
        """
        @return : True/False if current ordering of the cb order is consistent
        Inconsistency must be strict
        """
        # loop through all cases in order
        for defeated, reason_set in self.order.items():
            for reason in reason_set:
                if not self.is_consistent(reason, defeated):
                    return False
        return True

    def is_cb_consistent_with(self, case):
        """
        @param case: a new case
        @return: True/False if the current cb order would be consistent with a new case added
        """
        return self.is_consistent(case.reason, case.defeated())

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
        elif r2.issubset(r1):
            self.add_order_with_subsets(r1, r2)

    def unsafe_add_case(self, case):
        """
        @param case: the new case to be added to the priority order
        Adds a new case to order dict with no safety checks for inconsistency
        """
        # case 1: we know the winning reason is at least as strong as the defeated factors, since it won
        self.add_order_with_subsets(case.reason, case.defeated())
        for r, ds in list(self.order.items()):
            # case 2: check if winning reason is stronger than other winning reasons in the dictionary
            self.add_pair_as_appropriate(case.reason, r)
            # Because we don't do a polarity check, we have to test *all* ds...boo)
            for d in ds:
                # case 3: check if winning reason is stronger than other defeated reasons in the dictionary
                self.add_pair_as_appropriate(case.reason, d)

    def safe_add_case(self, case, incons):
        """
        @param case: the new case to be added to the priority order
        @param incons: the constraint to be used when adding the new case to the priority order
        """
        if self.is_case_admissible(case.reason, case.defeated(), incons):
            self.unsafe_add_case(case)
            return True
        return False

    def count_tainted_cases(self):
        """
        @return : number of cases which are associated with an inconsistency in current cb
        """

        # loop through all cases in order
        count = 0
        for reason, defeated_set in self.order.items():
            for defeated in defeated_set:
                if not self.is_consistent(reason, defeated):
                    count = count + 1
        return count

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
        self.add_cases(self.cases)

    def check_incons_value(self, incons):
        # Check inconsistency is valid
        try:
            incons_value = incons_enum[incons]
        except KeyError as e:
            raise KeyError(
                f"""The key 'Inconsistency' with value '{incons}' is not found in the incons_enum (NO, NO_NEW, 
                NO_INVOLVEMENT, NO_CORRUPTION, ALL)."""
            ) from e
        return incons_value

    def add_cases(self, cases, incons="ALL"):
        for case in cases:
            self.add_case(case, incons)

    def add_case(self, case, incons="ALL"):
        return self.order.safe_add_case(case, self.check_incons_value(incons))

    def is_cb_consistent(self):
        return self.order.is_cb_consistent()

    def is_consistent_with(self, case):
        return self.order.is_cb_consistent_with(case)

    def metrics(self):
        size = len(self.cases)
        inconsistencies = self.order.count_tainted_cases()

        print("Number of cases: ", size)
        print("Number of tainted cases: ", inconsistencies)
        return size, inconsistencies

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
