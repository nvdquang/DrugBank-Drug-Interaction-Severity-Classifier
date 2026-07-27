"""
test_tier1_engine.py

Unit tests for Tier 1 Rule Engine:
- NTI drug detection (Warfarin, Digoxin, etc.)
- High-risk drug class detection
- Rule Engine Score calculation
- Dynamic severity adjustment
"""

import unittest
from classifier import SeverityClassifier
from models import Interaction


class Tier1EngineTest(unittest.TestCase):

    def setUp(self):
        self.classifier = SeverityClassifier()

    def test_nti_warfarin_bleeding_major(self):
        """
        Warfarin + bleeding risk -> NTI flag, High-risk flag, Major severity
        """
        desc = "The risk or severity of bleeding can be increased when Warfarin is combined with Aspirin."
        interaction = Interaction(id=1, description=desc)

        res = self.classifier.classify(interaction)

        self.assertIsNotNone(res)
        self.assertEqual(res.severity, "major")
        self.assertTrue(res.is_nti)
        self.assertTrue(res.is_high_risk)
        self.assertGreaterEqual(res.score, 3.5)

    def test_digoxin_pk_interaction(self):
        """
        Digoxin (NTI) PK interaction -> Moderate base upgraded or scored with NTI warning
        """
        desc = "The metabolism of Digoxin can be decreased by Amiodarone."
        interaction = Interaction(id=2, description=desc)

        res = self.classifier.classify(interaction)

        self.assertIsNotNone(res)
        self.assertTrue(res.is_nti)
        self.assertTrue(res.is_high_risk)
        self.assertEqual(res.pattern, "pharmacokinetic")

    def test_qt_prolongation(self):
        """
        QT prolongation -> Major severity, High-risk event
        """
        desc = "The risk or severity of QT prolongation can be increased when Drug A is combined with Drug B."
        interaction = Interaction(id=3, description=desc)

        res = self.classifier.classify(interaction)

        self.assertIsNotNone(res)
        self.assertEqual(res.severity, "major")
        self.assertTrue(res.is_high_risk)

    def test_minor_interaction(self):
        """
        Minor interaction -> Minor severity, low score
        """
        desc = "The risk or severity of constipation can be increased when Drug A is combined with Drug B."
        interaction = Interaction(id=4, description=desc)

        res = self.classifier.classify(interaction)

        self.assertIsNotNone(res)
        self.assertEqual(res.severity, "minor")
        self.assertFalse(res.is_nti)


if __name__ == "__main__":
    unittest.main()
