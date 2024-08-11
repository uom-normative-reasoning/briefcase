from briefcase.enums import incons_enum


class AdmissibilityConstraints:
    def __init__(self, priority_order):
        self.priority_order = priority_order

    def is_case_admissible(self, new_reason, new_defeated, incons):
        """
        Using an admissibility constraint, checks if a new case can be added into existing
        case base priority order.
        @return: True when admissible, and False when admission should be denied
        """
        method_map = {
            incons_enum.NO: self.no_incons,
            incons_enum.NO_NEW: self.no_new_incons,
            incons_enum.NO_INVOLVEMENT: self.no_involvement_incons,
            incons_enum.HORTY: self.horty_incons,
            incons_enum.NO_CORRUPTION: self.no_corruption_incons,
            incons_enum.ALL: lambda *args: True,
        }

        admissible_method = method_map.get(incons, None)
        if admissible_method:
            return admissible_method(new_reason, new_defeated)
        else:
            raise ValueError("Invalid inconsistency value")

    def no_incons(self, new_reason, new_defeated):
        """A) admissibility constraint
        1. for Γ ∪ {C} there does not exist any cases C′, C′′ ∈ Γ ∪ {C} where C′ ‖ C ′'
        @return: True when case base is already consistent AND when new case is not inconsistent ,
                with any case in the case base, otherwise False"""
        if self.priority_order.is_cb_consistent():
            if self.priority_order.is_consistent(new_reason, new_defeated):
                return True
        return False

    def no_involvement_incons(self, new_reason, new_defeated):
        """B part 1) admissibility constraint
        2. For all cases in the CB, the new case is not inconsistent with any case
        @return: True when new case is not inconsistent with any case in the case base,
                otherwise False"""
        return self.priority_order.is_consistent(new_reason, new_defeated)

    def no_new_incons(self, new_reason, new_defeated):
        """B part 2) admissibility constraint
        3. Priority order remains the same
        @return: True when the new case is an existing claim in the priority order,
                otherwise False"""
        return self.priority_order.is_existing_claim(new_reason, new_defeated)

    def horty_incons(self, new_reason, new_defeated):
        """B admissibility constraint / HORTY admissibility
        @return: True when new case does not alter the priority order, or it is consistent with case base"""
        return self.no_involvement_incons(new_reason, new_defeated) or self.no_new_incons(new_reason, new_defeated)

    def no_corruption_incons(self, new_reason, new_defeated):
        """C admissibility constraint
         4. For all cases in the CB the new case is only inconsistent with cases which are otherwise inconsistent
         @return: True when new case is inconsistent with any case which is otherwise tainted/inconsistent
                  in the case base, otherwise False"""
        incons = self.priority_order.get_incons_pairs_with_case(new_reason, new_defeated)
        if not incons:
            return True

        for case_pairs in incons:
            if self.priority_order.is_consistent(case_pairs[0], case_pairs[1]):
                return False
        return True

    def mrd(self, new_reason, new_defeated):
        """Minimal relevant differences admissibility constraint
         4. For all cases in the CB the new case must be minimally relevant different to
            a case with the same polarity"""
        pass