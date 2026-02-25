import unittest
from base_tester import BaseTester  # Assuming BaseTester is defined in base_tester.py

class BackendTest(BaseTester):
    def setUp(self):
        super().setUp()
        # Setup code common to all tests, avoiding duplication

    def test_feature_one(self):
        # Test code for feature one
        self.assertTrue(self.perform_feature_one_check())

    def test_feature_two(self):
        # Test code for feature two
        self.assertTrue(self.perform_feature_two_check())

    def tearDown(self):
        # Cleanup code, if necessary
        super().tearDown()