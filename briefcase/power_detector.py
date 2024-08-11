from collections import defaultdict
from itertools import combinations

from briefcase.enums import decision_enum
from briefcase.case import Case


class PowerDetector:
    def __init__(self, priority_order):
        self.priority_order = priority_order
        self.factor_list = {decision_enum.pi: set(),
                            decision_enum.delta: set()}

    def add_factor_list(self, case):
        reason_pol = case.decision
        if case.decision == decision_enum.pi:
            defeated_pol = decision_enum.delta
        else:
            defeated_pol = decision_enum.pi

        for factor in case.reason:
            self.factor_list[reason_pol].add(factor)

        for factor in case.defeated():
            self.factor_list[defeated_pol].add(factor)

    def max_edges(self):
        max_p = len(self.factor_list[decision_enum.pi])
        max_d = len(self.factor_list[decision_enum.delta])
        maximum_edges_pi = (2 ** (max_p-1)) * ((2 ** max_d) - 1)
        maximum_edges_delta = (2 ** (max_d-1)) * ((2 ** max_p) - 1)
        return maximum_edges_pi, maximum_edges_delta

    def count_winning_edges_case(self, case):
        if case.reason:
            return 2 ** (len(self.factor_list[case.decision]) - len(case.reason))
        else:
            return 0 # no empty sides allowed

    @staticmethod
    def count_losing_edges_case(case):
        return (2 ** (len(case.defeated()))) - 1

    def case_power(self, case):
        copy_factor_list = self.factor_list
        self.add_factor_list(case)
        edges_count = self.count_winning_edges_case(case) * self.count_losing_edges_case(case)
        self.factor_list = copy_factor_list
        return edges_count

    def get_non_proper_supersets(self, reason_set):
        """
        Returns a set of frozen sets of factors representing all non-proper supersets of the given set of reason_sets.
        """
        union_set = set()
        for reason in reason_set:
            current_polarity = list(reason)[0].polarity
            all_combinations = []
            for r in range(1, len(self.factor_list[current_polarity]) + 1):
                all_combinations.extend(combinations(self.factor_list[current_polarity], r))
            for combination in all_combinations:
                union_set.add(frozenset(reason | frozenset(combination)))

        return union_set

    def get_non_proper_subsets(self, defeated_set):
        """
        Returns a list of frozen sets of factors representing all non-proper subsets of the given defeated_set.
        """
        non_proper_subsets = []
        for r in range(1, len(defeated_set)+1):
            for subset in combinations(defeated_set, r):
                non_proper_subsets.append(frozenset(subset))
        return non_proper_subsets

    def cb_power(self):
        """
        Returns the sum of the number of elements in the priority order.
        """
        edges = defaultdict(set)
        for defeated, reason_set in self.priority_order.order.items():
            non_proper_subsets_defeated = self.get_non_proper_subsets(defeated)
            non_proper_supersets_reasons = self.get_non_proper_supersets(reason_set)
            for subset_defeated in non_proper_subsets_defeated:
                edges[subset_defeated].update(non_proper_supersets_reasons)

        return sum(len(reason_set) for defeated, reason_set in edges.items())
