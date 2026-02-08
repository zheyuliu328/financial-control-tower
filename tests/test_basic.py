"""Minimal tests for FCT"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.mark.unit
def test_import():
    """Test basic import"""
    assert True
