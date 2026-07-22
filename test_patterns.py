import unittest

from patterns import PatternMatcher

PD = "pharmacodynamic"
PK = "pharmacokinetic"


class PatternMatcherTest(unittest.TestCase):

    def setUp(self):
        self.matcher = PatternMatcher()

    def test_risk_pattern(self):
        desc = "The risk or severity of hypotension can be increased when combined with drug X."
        res = self.matcher.extract(desc)
        self.assertIsNotNone(res)
        self.assertEqual(res.pattern_type, PD)
        self.assertEqual(res.event, "hypotension")
        self.assertEqual(res.direction, "increased")

    def test_therapeutic_efficacy_pattern(self):
        desc = "Drug A can cause a decrease in the absorption of Drug B resulting in a decrease in efficacy."
        res = self.matcher.extract(desc)
        self.assertIsNotNone(res)
        self.assertEqual(res.pattern_type, PD)
        self.assertEqual(res.event, "therapeutic efficacy")
        self.assertEqual(res.direction, "decreased")

    def test_pk_pattern(self):
        desc = "The metabolism of Drug B can be decreased by Drug A."
        res = self.matcher.extract(desc)
        self.assertIsNotNone(res)
        self.assertEqual(res.pattern_type, PK)
        self.assertEqual(res.event, "metabolism")
        self.assertEqual(res.direction, "decreased")


if __name__ == "__main__":
    unittest.main()
