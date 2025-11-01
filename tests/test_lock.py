"""Tests for locking mechanisms."""

import os
from unittest.mock import patch, Mock, MagicMock
import pytest
import sys
sys.path.insert(0, 'src')  # Ensure import

from routine_workflow.lock import acquire_lock, release_lock, lock_context, cleanup_and_exit


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
def test_acquire_lock_success(mock_pid: Mock, mock_rmtree: Mock, mock_runner: Mock):
    """Test lock acquire creates dir/pid."""
    # Use mutable mock config
    mock_config = Mock()
    mock_lock_dir = Mock()
    mock_lock_dir.mkdir = Mock()
    mock_pid_path = Mock()
    mock_pid_path.write_text = Mock()
    mock_lock_dir.__truediv__ = lambda self, name: mock_pid_path if name == 'pid' else None
    mock_config.lock_dir = mock_lock_dir
    mock_runner.config = mock_config

    acquire_lock(mock_runner)

    mock_lock_dir.mkdir.assert_called_once_with(parents=True, exist_ok=False)
    mock_pid_path.write_text.assert_called_once_with('1234')
    assert mock_runner._lock_acquired is True
    mock_runner.logger.info.assert_called_once()


@patch('routine_workflow.lock.shutil.rmtree')
def test_acquire_lock_exists(mock_rmtree: Mock, mock_runner: Mock):
    """Test concurrent lock fails."""
    mock_config = Mock()
    mock_lock_dir = Mock()
    mock_lock_dir.mkdir.side_effect = FileExistsError("Lock exists")
    mock_config.lock_dir = mock_lock_dir
    mock_runner.config = mock_config

    with pytest.raises(SystemExit) as exc:
        acquire_lock(mock_runner)

    assert exc.value.code == 3
    mock_runner.logger.error.assert_called_once()


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
def test_release_lock_success(mock_pid: Mock, mock_rmtree: Mock, mock_runner: Mock):
    """Test release removes lock dir."""
    mock_runner._lock_acquired = True
    mock_pid_path = Mock()
    mock_pid_path.read_text.return_value = '1234'
    mock_pid_path.exists.return_value = True
    mock_runner._pid_path = mock_pid_path
    mock_config = Mock()
    mock_runner.config = mock_config

    release_lock(mock_runner)

    mock_pid_path.read_text.assert_called_once()
    mock_rmtree.assert_called_once_with(mock_runner.config.lock_dir)
    assert mock_runner._lock_acquired is False
    mock_runner.logger.info.assert_called_once_with("Lock directory removed")


@patch('routine_workflow.lock.shutil.rmtree')
def test_release_lock_stale_pid(mock_rmtree: Mock, mock_runner: Mock):
    """Test leaves stale lock (different PID)."""
    mock_runner._lock_acquired = True
    mock_pid_path = Mock()
    mock_pid_path.read_text.return_value = '9999'  # Different PID
    mock_pid_path.exists.return_value = True
    mock_runner._pid_path = mock_pid_path
    mock_runner.config = Mock()

    release_lock(mock_runner)

    mock_rmtree.assert_not_called()
    mock_runner.logger.warning.assert_called_once_with("Lock owned by different PID — leaving it in place")


def test_lock_context(mock_runner: Mock):
    """Test context manager acquires/releases."""
    with patch('routine_workflow.lock.acquire_lock') as mock_acquire, \
         patch('routine_workflow.lock.release_lock') as mock_release:

        with lock_context(mock_runner):
            pass  # Yield block

    mock_acquire.assert_called_once_with(mock_runner)
    mock_release.assert_called_once_with(mock_runner)


def test_cleanup_and_exit(mock_runner: Mock):
    """Test cleanup calls release."""
    with patch('routine_workflow.lock.release_lock') as mock_release:

        with pytest.raises(SystemExit) as exc:
            cleanup_and_exit(mock_runner, 1)

    assert exc.value.code == 1
    mock_runner.logger.info.assert_called_once_with("Exiting with code 1")
    mock_release.assert_called_once_with(mock_runner)


@patch('routine_workflow.lock.shutil.rmtree')
def test_release_lock_no_pid_best_effort(mock_rmtree: Mock, mock_runner: Mock):
    """Test best-effort removal if no PID file."""
    mock_runner._lock_acquired = True
    mock_pid_path = Mock()
    mock_pid_path.exists.return_value = False
    mock_runner._pid_path = mock_pid_path
    mock_lock_dir = Mock()
    mock_lock_dir.exists.return_value = True
    mock_runner.config.lock_dir = mock_lock_dir
    mock_runner.config = Mock(lock_dir=mock_lock_dir)

    release_lock(mock_runner)

    mock_rmtree.assert_called_once_with(mock_runner.config.lock_dir)
    mock_runner.logger.info.assert_called_once_with("Stale lock dir removed")


def test_acquire_lock_exception(mock_runner: Mock):
    """Test general exception in acquire_lock."""
    mock_config = Mock()
    mock_lock_dir = Mock()
    mock_lock_dir.mkdir.side_effect = Exception("IOError")
    mock_config.lock_dir = mock_lock_dir
    mock_runner.config = mock_config

    with patch.object(mock_runner.logger, 'exception') as mock_exc:
        with pytest.raises(SystemExit) as exc:
            acquire_lock(mock_runner)

    assert exc.value.code == 3
    mock_exc.assert_called_once_with('Failed to acquire lock: IOError')