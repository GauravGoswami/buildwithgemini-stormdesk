"""Tests for claim payout calculations."""

import pytest
from app.tools.payout import calculate_payout


def test_payout_clm_1003():
    result = calculate_payout("CLM-1003")
    assert result["net_payout"] == 5600.0
    assert result["deductible"] == 2800.0
    assert result["depreciation"] == 0.0


def test_payout_clm_1005():
    result = calculate_payout("CLM-1005")
    assert result["net_payout"] == 44300.0
    assert result["deductible"] == 4200.0
    assert result["depreciation"] == 0.0


def test_payout_clm_1015():
    result = calculate_payout("CLM-1015")
    assert result["net_payout"] == 5400.0
    assert result["depreciation"] == 12800.0
    assert result["deductible"] == 2800.0


def test_payout_clm_1023():
    result = calculate_payout("CLM-1023")
    assert result["net_payout"] == 301800.0
    assert result["deductible"] == 3200.0
    assert result["depreciation"] == 0.0


def test_payout_clm_2003():
    result = calculate_payout("CLM-2003")
    assert result["net_payout"] == 5700.0
    assert result["deductible"] == 500.0
    assert result["depreciation"] == 0.0


def test_payout_clm_2009():
    result = calculate_payout("CLM-2009")
    assert result["net_payout"] == 3800.0
    assert result["deductible"] == 1000.0
    assert result["depreciation"] == 0.0
