import argparse

from enum import Enum
from pathlib import Path
from collections import defaultdict

# Decisions are either for side pi, for side delta, or undecided
# Pi = child can have dessert
# Delta = child cannot have dessert
# Undecided = ?
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


class PriorityOrder:
    """
    Orders reasons and factors in a dictionary.
    Key is a frozenset of the stronger factors, value is a frozenset of the weaker factors.
    """

    def __init__(self):
        # default-dict does not error when referencing a key which doesn't exist

        # contains case base ordering with defeated stored as keys,
        # and sets of reasons stored as values
        self.order = defaultdict(set)
        self.defeated_factor_index = defaultdict(set)
        self.incon_counts = defaultdict(int)

    def get_dominated_cases_in_cb(self, new_reason, new_defeated):
        """
        @param new_reason: a frozenset of factors
        @param new_defeated: a frozenset of factors, weaker than the reason
        @return: all defeated factor sets of cases which are dominant to the new case in the existing case base order.
                 Will have the same reason as new_reason, but might have more factors than the new_defeated.
        """
        dominant_cases = []  # tuple of (reason, defeated)

        # retrieve all entries in the priority order for defeats which are stronger than the current defeat
        defeats_supersets = self.get_stronger_defeats(new_defeated)

        # if there is an entry for a reason under the defeated which is the same as current reason,
        # this is a dominating case to the new case
        for superset in defeats_supersets:
            if new_reason in self.order[superset]:
                dominant_cases.append((new_reason, superset))

        return dominant_cases

    def get_dominating_cases_in_cb(self, new_reason, new_defeated):
        """
        @param new_reason: a frozenset of factors
        @param new_defeated: a frozenset of factors, weaker than the reason
        @return: all defeated factor sets of cases which are dominated by the new case in the existing case base order.
                 Will have the same reason as new_reason, but might have more factors than the new_defeated.
        """
        dominating_cases = []  # tuple of (reason, defeated)

        # retrieve all entries in the priority order for defeats which are weaker than the current defeat
        defeats_subsets = self.get_weaker_defeats(new_defeated)

        # if there is an entry for a reason under the defeated which is the same as current reason,
        # this is a dominant case
        for subset in defeats_subsets:
            if new_reason in self.order[subset]:
                dominating_cases.append((new_reason, subset))

        return dominating_cases

    def is_case_tainted(self, reason, defeated):
        """
        @param reason: a frozenset of factors
        @param defeated: a frozenset of factors, weaker than the reason
        @return: if the case is either half of an inconsistency present in the case base return True
        """
        return not self.is_consistent(reason, defeated)

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

    def is_consistent(self, new_reason, new_defeated, inconsistency="STRICT"):
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
        case_sets = [(self.order[superset], superset) for superset in supersets]

        # If for any of the existing reasons sets retrieved, if the new defeated is a superset of one of
        # the sets of old reasons, return True (inconsistent)
        for case in case_sets:
            reasons = case[0]
            defeated = case[1]
            for reason in reasons:
                if reason.issubset(new_defeated):
                    if inconsistency == "STRICT":
                        print("Using STRICT inconsistency")
                        # Strongest inconsistency constraint, don't accept anything
                        return False
                    elif inconsistency == "EQUAL":
                        print("Using EQUAL inconsistency")
                        # Horty inconsistency, weakest constraint
                        # if this inconsistency is already in the cb in a dominant form, continue, we accept this
                        # inconsistency. This occurs when the case already exists in cb in a dominant form
                        if not (new_reason in self.order[new_defeated]):
                            return False
                        return "EQUAL"
                    elif inconsistency == "DOMINATED":
                        print("Using DOMINANT inconsistency")
                        # if this inconsistency is already in the cb in a dominant form, continue, we accept this
                        # inconsistency. This occurs when the case already exists in cb in a dominant form
                        # Also accepts EQUALITY inconsistencies
                        if not self.get_dominated_cases_in_cb(new_reason, new_defeated):
                            return False
                        return "DOMINATED"
                    elif inconsistency == "DOMINATING":
                        print("using DOMINATED inconsistency")
                        # if there is an inconsistency in the cb and the new case dominates this, accept this
                        # If it is dominating of existing tainted case, can conclude we should accept inconsistency
                        # If it is dominating of any case, can conclude we should accept anyway
                        # Keep this here, so we can track how many inconsistencies we accept which are dominating
                        # Also accepts EQUALITY inconsistencies
                        if not self.get_dominating_cases_in_cb(new_reason, new_defeated):
                            return False
                        return "DOMINATING"
                    elif inconsistency == "HORTY":
                        print("using HORTY inconsistency")
                        if self.get_dominated_cases_in_cb(new_reason, new_defeated):
                            return "HORTY"
                        if self.get_dominating_cases_in_cb(new_reason, new_defeated):
                            return "HORTY"
                        return False
                    elif inconsistency == "TAINTED":
                        # if a case is already inconsistent somewhere in the case base, accept this
                        # Accepts DOMINATING, EQUALITY, and DOMINATED inconsistencies
                        print("Using TAINTED inconsistency")
                        if not self.is_case_tainted(reason, defeated):
                            return False
                        return "TAINTED"
                    elif inconsistency == "ALL":
                        # Allows all inconsistencies in the casebase
                        # Keep this here so we can track how many inconsistencies we accept
                        return "ALL"

        return "CONSISTENT-CASE"

    def is_cb_consistent(self):
        """
        @return : True/False if current ordering of the cb order is consistent
        Inconsistency must be strict
        """
        # loop through all cases in order
        for defeated, reason_set in self.order.items():
            for reason in reason_set:
                if not self.is_consistent(reason, defeated, "STRICT"):
                    return False
        return True

    def is_cb_consistent_with(self, case, inconsistency="STRICT"):
        """
        @param case: a new case
        @return: True/False if the current cb order would be consistent with a new case added
        """
        # assert self.is_consistent()  # TODO: is this what we want? Probably not...
        # if any inconsistency other than strict, the cb will have inconsistencies in but case may not be inconsistent

        # New case
        reason = case.reason
        defeated = case.defeated()

        return self.is_consistent(reason, defeated, inconsistency)

    def count_tainted_cases(self):
        """
        @return : number of cases which are associated with an inconsistency in current cb
        """

        # loop through all cases in order
        count = 0
        for reason, defeated_set in self.order.items():
            for defeated in defeated_set:
                if not self.is_consistent(reason, defeated, "STRICT"):
                    count = count + 1
        return count

    def count_new_inconsistency_types(self):
        """
        @return : number of cases which were accepted due to an inconsistency strategy in current cb
        """
        return self.incon_counts

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
        self.incon_counts["IGNORE"] += 1
        # case 1: we know the winning reason is at least as strong as the defeated factors, since it won
        self.add_order_with_subsets(case.reason, case.defeated())
        for r, ds in list(self.order.items()):
            # case 2: check if winning reason is stronger than other winning reasons in the dictionary
            self.add_pair_as_appropriate(case.reason, r)
            # Because we don't do a polarity check, we have to test *all* ds...boo)
            for d in ds:
                # case 3: check if winning reason is stronger than other defeated reasons in the dictionary
                self.add_pair_as_appropriate(case.reason, d)


    def safe_add_case(self, case, inconsistency):
        """
        @param case: the new case to be added to the priority order
        Adds a new case to order dict with no safety checks for inconsistency
        """
        type = self.is_cb_consistent_with(case, inconsistency)
        if type:
            print(type)
            self.incon_counts[type] += 1
            return self.unsafe_add_case(case)


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
        self.add_cases(self.cases)

    def add_cases(self, cases):
        for c in cases:
            self.order.unsafe_add_case(c)

    def add_case(self, case):
        self.order.unsafe_add_case(case)

    def safe_add_cases(self, cases, inconsistency="STRICT"):
        for c in cases:
            self.order.safe_add_case(c, inconsistency)

    def safe_add_case(self, case, inconsistency="STRICT"):
        self.cases.append(case)
        self.order.safe_add_case(case, inconsistency)

    def is_cb_consistent(self):
        return self.order.is_cb_consistent()

    def is_consistent_with(self, case, consistency="STRICT"):
        return self.order.is_cb_consistent_with(case, consistency)

    def metrics(self):
        size = len(self.cases)
        inconsistencies = self.order.count_tainted_cases()
        types = self.order.count_new_inconsistency_types()

        print("Number of cases: ", size)
        print("Number of tainted cases: ", inconsistencies)
        print("Type of newly inconsistent cases: ", types)
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
