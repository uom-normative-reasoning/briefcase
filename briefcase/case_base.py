from briefcase.admissibility_constraints import AdmissibilityConstraints
from briefcase.enums import incons_enum
from briefcase.priority_order import PriorityOrder


class CaseBase:
    def __init__(self, caselist=[]):
        self.cases = caselist
        self.order = PriorityOrder(self)
        self.add_unsafe_cases(self.cases)

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

    def add_unsafe_cases(self, cases):
        for case in cases:
            self.order.unsafe_add_case(case)

    def add_cases(self, cases, incons="ALL"):
        for case in cases:
            self.add_case(case, incons)

    def add_case(self, case, incons="ALL"):
        if self.order.safe_add_case(case, self.check_incons_value(incons)):
            self.cases.append(case)
            return True
        else:
            return False

    def is_cb_consistent(self):
        return self.order.is_cb_consistent()

    def is_consistent_with(self, case):
        return self.order.is_cb_consistent_with(case)

    def count_tainted_cases(self):
        """
        @return : number of cases which are associated with an inconsistency in current cb
        """

        # loop through all cases in order
        count = 0
        for case in self.cases:
            if self.is_consistent_with(case):
                count = count + 1

        return count

    def metrics(self):
        size = len(self.cases)
        inconsistencies = self.count_tainted_cases()

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
