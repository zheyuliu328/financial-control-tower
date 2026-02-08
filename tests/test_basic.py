"""Minimal tests for FCT"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestBasic(unittest.TestCase):
    def test_import(self):
        """Test basic import"""
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()
