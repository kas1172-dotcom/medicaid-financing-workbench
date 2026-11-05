import unittest
import pandas as pd
from mfw.analysis import duals, work_requirements

class AnalysisEdgeCases(unittest.TestCase):
    def row(self, **changes):
        row=dict(state="Example",abbr="XX",enrollment=100,duals=0,total_medicaid_spend=1000,data_provenance="Test fixture")
        row.update(changes)
        return pd.DataFrame([row])
    def test_zero_duals_has_zero_spending_but_undefined_concentration(self):
        result=duals.run(self.row(),{})
        self.assertEqual(result["rows"][0]["dual_spend_share_pct"],0)
        self.assertIsNone(result["rows"][0]["concentration_ratio"])
    def test_zero_spending_has_no_national_percentage(self):
        self.assertIsNone(duals.run(self.row(total_medicaid_spend=0),{})["national_dual_spend_share_pct"])
    def test_invalid_counts_rejected(self):
        for value in [-1,101,float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                duals.run(self.row(duals=value),{})
    def test_empty_input(self):
        result=duals.run(pd.DataFrame(),{})
        self.assertEqual(result["rows"],[])
        self.assertIsNone(result["national_dual_spend_share_pct"])
    def test_scenario_proportions_are_bounded(self):
        for value in [-.1,1.1,float("nan"),True]:
            params={"work_requirements":{"already_working_or_exempt_share":.9,"administrative_churn_rate":value}}
            with self.subTest(value=value), self.assertRaises(ValueError):
                work_requirements.run(pd.DataFrame(),params)
