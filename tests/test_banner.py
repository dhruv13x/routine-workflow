# tests/test_banner.py

"""Tests for the rich banner and color palette generation."""

import os
from unittest.mock import patch, MagicMock
import pytest
from routine_workflow import banner

def test_lerp():
    """Test linear interpolation."""
    assert banner.lerp(0, 10, 0.5) == 5
    assert banner.lerp(-10, 10, 0.5) == 0
    assert banner.lerp(10, 20, 0) == 10
    assert banner.lerp(10, 20, 1) == 20

@patch('random.SystemRandom')
def test_print_logo_procedural_palette(mock_sysrand):
    """Test logo prints with a procedurally-generated palette."""
    # Ensure random calls are deterministic
    mock_sysrand.return_value.random.return_value = 0.5
    mock_sysrand.return_value.shuffle.return_value = None

    with patch('rich.console.Console') as mock_console:
        banner.print_logo()
        # Check that console.print was called multiple times for the logo + tagline
        assert mock_console.return_value.print.call_count > 10

@patch.dict(os.environ, {"CREATE_DUMP_PALETTE": "0"})
def test_print_logo_fixed_palette_env():
    """Test logo prints with a fixed palette from env var."""
    with patch('rich.console.Console') as mock_console:
        banner.print_logo()
        assert mock_console.return_value.print.call_count > 10

@patch('random.SystemRandom')
def test_print_logo_procedural_palette_with_color_shift(mock_sysrand):
    """Test logo prints with a procedurally-generated palette."""
    # Ensure random calls are deterministic by providing a long list of return values
    mock_sysrand.return_value.random.side_effect = [0.1] * 50
    mock_sysrand.return_value.shuffle.return_value = None

    with patch('rich.console.Console') as mock_console:
        banner.print_logo()
        # Check that console.print was called multiple times for the logo + tagline
        assert mock_console.return_value.print.call_count > 10

@patch.dict(os.environ, {"CREATE_DUMP_PALETTE": "99"}) # Invalid index
def test_print_logo_fixed_palette_bad_env_fallback():
    """Test fallback to procedural on bad env var index."""
    with patch('rich.console.Console') as mock_console:
        banner.print_logo()
        assert mock_console.return_value.print.call_count > 10

@patch.dict(os.environ, {"CREATE_DUMP_PALETTE": "not-a-number"})
def test_print_logo_fixed_palette_nan_env_fallback():
    """Test fallback to procedural on non-numeric env var."""
    with patch('rich.console.Console') as mock_console:
        banner.print_logo()
        assert mock_console.return_value.print.call_count > 10
