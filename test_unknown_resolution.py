"""
test_unknown_resolution.py

Unit test to verify that previously unknown interaction events
are now resolved successfully by Tier 1/2 Rule Engine enhancements.
"""

import unittest
from classifier import SeverityClassifier
from models import Interaction


class UnknownResolutionTest(unittest.TestCase):

    def setUp(self):
        self.classifier = SeverityClassifier()

    def test_resolve_increased_transaminases(self):
        desc = "The risk or severity of increased transaminases can be increased when Drug A is combined with Drug B."
        res = self.classifier.classify(Interaction(id=1, description=desc))
        self.assertIsNotNone(res)
        self.assertNotEqual(res.severity, "unknown")
        self.assertEqual(res.severity, "major")

    def test_resolve_osteomalacia(self):
        desc = "The risk or severity of osteomalacia can be increased when Drug A is combined with Drug B."
        res = self.classifier.classify(Interaction(id=2, description=desc))
        self.assertIsNotNone(res)
        self.assertNotEqual(res.severity, "unknown")

    def test_resolve_increased_glucose(self):
        desc = "The risk or severity of increased glucose can be increased when Drug A is combined with Drug B."
        res = self.classifier.classify(Interaction(id=3, description=desc))
        self.assertIsNotNone(res)
        self.assertNotEqual(res.severity, "unknown")

    def test_resolve_water_intoxication(self):
        desc = "The risk or severity of water intoxication can be increased when Drug A is combined with Drug B."
        res = self.classifier.classify(Interaction(id=4, description=desc))
        self.assertIsNotNone(res)
        self.assertNotEqual(res.severity, "unknown")
        self.assertEqual(res.severity, "major")

    def test_fuzzy_token_overlap(self):
        """
        Test fuzzy token overlap matching for unmapped phrasing variant
        """
        desc = "The risk or severity of severe hypokalemic condition can be increased when Drug A is combined with Drug B."
        res = self.classifier.classify(Interaction(id=5, description=desc))
        self.assertIsNotNone(res)
        self.assertNotEqual(res.severity, "unknown")


if __name__ == "__main__":
    unittest.main()
