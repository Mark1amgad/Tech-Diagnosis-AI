class ConfidenceSystem:
    @staticmethod
    def combine(cf1, cf2):
        """
        Combines two confidence scores using the MYCIN probabilistic sum.
        Handles accumulation of evidence when multiple rules fire for the same conclusion.
        """
        return cf1 + cf2 - (cf1 * cf2)

    @staticmethod
    def propagate(rule_cf, conditions_cfs):
        """
        Propagates confidence through a reasoning chain.
        The certainty of the conclusion is bounded by the weakest premise.
        """
        if not conditions_cfs:
            return rule_cf
        return rule_cf * min(conditions_cfs)
