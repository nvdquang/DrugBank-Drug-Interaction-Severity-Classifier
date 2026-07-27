"""
test_tier2_kb.py

Unit tests for Tier 2 Knowledge Base loader and Classifier integration:
- Verifies DBRuleLoader initialization & fallback mechanism
- Verifies rules loading into memory cache
- Verifies classification accuracy using Knowledge Base
"""

import unittest
from db_rule_loader import DBRuleLoader
from classifier import SeverityClassifier
from models import Interaction


class Tier2KnowledgeBaseTest(unittest.TestCase):

    def test_db_rule_loader_fallback_or_db(self):
        """
        Verify DBRuleLoader loads rules without errors
        """
        loader = DBRuleLoader()
        loader.load()

        self.assertGreater(len(loader.event_lookup), 0, "event_lookup should not be empty")
        self.assertIn("bleeding", loader.event_lookup)
        self.assertEqual(loader.event_lookup["bleeding"], "major")
        self.assertIn("warfarin", loader.nti_drugs)

    def test_classifier_with_tier2_kb(self):
        """
        Verify SeverityClassifier loads and classifies using Tier 2 Knowledge Base
        """
        classifier = SeverityClassifier(use_db_kb=True)

        interaction = Interaction(
            id=1,
            description="The risk or severity of bleeding can be increased when Warfarin is combined with Aspirin."
        )

        result = classifier.classify(interaction)
        self.assertIsNotNone(result)
        self.assertEqual(result.severity, "major")
        self.assertTrue(result.is_nti)
        self.assertTrue(result.is_high_risk)


if __name__ == "__main__":
    unittest.main()
