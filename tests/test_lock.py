# tests/test_lock.py

"""Tests for locking mechanisms."""

import os
from unittest.mock import patch, Mock, MagicMock, ANY
import pytest
import sys
sys.path.insert(0, 'src')  # Ensure import

from routine_workflow.lock import acquire_lock, release_lock, lock_context, cleanup_and_exit
from routine_workflow.config import WorkflowConfig
from pathlib import Path


@pytest.fixture
def mock_runner():
    """Mock runner with config and logger."""
    runner = Mock()
    runner.logger = Mock()
    config = Mock(spec=WorkflowConfig)
    config.lock_ttl = 3600  # Default
    runner.config = config
    runner._lock_acquired = False
    runner._pid_path = None
    return runner


@pytest.fixture
def mock_lock_dir():
    """Mocked lock_dir Path with sub-path mocks for pid/timestamp."""
    lock_dir = Mock(spec=Path)
    lock_dir.__str__ = Mock(return_value="/tmp/mock_lock")  # Override dunder as new Mock
    pid_path = Mock(spec=Path)
    ts_path = Mock(spec=Path)
    def truediv(self, other):
        if other == 'pid':
            return pid_path
        elif other == 'timestamp':
            return ts_path
        raise ValueError(f"Unexpected subpath: {other}")
    lock_dir.__truediv__ = truediv
    lock_dir.mkdir = Mock()
    lock_dir.exists.return_value = False  # Default for fresh
    return lock_dir, pid_path, ts_path


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
@patch('routine_workflow.lock.time.time', return_value=1720000000.0)
def test_acquire_lock_success(mock_time, mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test lock acquire creates dir/pid/timestamp."""
    lock_dir, pid_path, ts_path = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    mock_runner.config.lock_ttl = 3600

    acquire_lock(mock_runner)

    lock_dir.mkdir.assert_called_once_with(parents=True, exist_ok=False)
    pid_path.write_text.assert_called_once_with('1234')
    ts_path.write_text.assert_called_once_with('1720000000.0')
    assert mock_runner._lock_acquired is True
    mock_runner.logger.info.assert_called_once_with("Lock acquired: /tmp/mock_lock (PID 1234)")


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
@patch('routine_workflow.lock.time.time', return_value=1720000000.0)
def test_acquire_lock_ttl_disabled(mock_time, mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test no eviction if lock_ttl=0; fail on exists."""
    lock_dir, _, _ = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.mkdir.side_effect = FileExistsError("Exists")
    mock_runner.config.lock_ttl = 0

    with pytest.raises(SystemExit) as exc:
        acquire_lock(mock_runner)

    assert exc.value.code == 3
    mock_rmtree.assert_not_called()
    mock_runner.logger.error.assert_called_once_with("Lock exists: /tmp/mock_lock — concurrent run detected")


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
@patch('routine_workflow.lock.time.time', return_value=1720000000.0)
def test_acquire_lock_eviction_by_ttl(mock_time, mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test eviction if timestamp > TTL; then retry acquire."""
    lock_dir, pid_path, ts_path = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.exists.return_value = True
    ts_path.exists.return_value = True
    ts_path.read_text.return_value = str(mock_time.return_value - 7200)  # 2h old > 1h TTL
    lock_dir.mkdir.side_effect = [FileExistsError("Stale"), None]  # First fails, retry succeeds
    mock_runner.config.lock_ttl = 3600

    acquire_lock(mock_runner)

    mock_rmtree.assert_called_once_with(lock_dir)
    mock_runner.logger.info.assert_any_call("Evicted stale lock by TTL (3600s): /tmp/mock_lock")
    assert lock_dir.mkdir.call_count == 2
    pid_path.write_text.assert_called_once_with('1234')
    ts_path.write_text.assert_called_once_with('1720000000.0')
    mock_runner.logger.info.assert_called_with("Lock acquired post-eviction: /tmp/mock_lock (PID 1234)")


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
@patch('routine_workflow.lock.time.time', return_value=1720000000.0)
def test_acquire_lock_no_eviction_live_pid(mock_time, mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test no eviction if PID alive (os.kill succeeds); fail acquire."""
    lock_dir, pid_path, ts_path = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.exists.return_value = True
    ts_path.exists.return_value = True
    ts_path.read_text.return_value = str(mock_time.return_value - 1800)  # Fresh < TTL
    pid_path.exists.return_value = True
    lock_dir.mkdir.side_effect = FileExistsError("Active")
    mock_runner.config.lock_ttl = 3600
    with patch('routine_workflow.lock.os.kill', return_value=None):  # Alive

        with pytest.raises(SystemExit) as exc:
            acquire_lock(mock_runner)

    assert exc.value.code == 3
    mock_rmtree.assert_not_called()
    mock_runner.logger.error.assert_called_once_with("Lock exists: /tmp/mock_lock — concurrent run detected")


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
@patch('routine_workflow.lock.time.time', return_value=1720000000.0)
def test_acquire_lock_eviction_no_timestamp(mock_time, mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test eviction if no timestamp file; then retry."""
    lock_dir, pid_path, ts_path = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.exists.return_value = True
    ts_path.exists.return_value = False  # No TS
    lock_dir.mkdir.side_effect = [FileExistsError("No TS"), None]
    mock_runner.config.lock_ttl = 3600

    acquire_lock(mock_runner)

    mock_rmtree.assert_called_once_with(lock_dir)
    mock_runner.logger.info.assert_any_call("Evicted stale lock (no timestamp): /tmp/mock_lock")
    assert lock_dir.mkdir.call_count == 2


@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
@patch('routine_workflow.lock.time.time', return_value=1720000000.0)
def test_acquire_lock_eviction_no_pid(mock_time, mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test eviction if no PID file; then retry."""
    lock_dir, pid_path, ts_path = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.exists.return_value = True
    ts_path.exists.return_value = True  # Assume TS exists for this path
    ts_path.read_text.return_value = str(mock_time.return_value - 1800)  # Fresh
    pid_path.exists.return_value = False  # No PID
    lock_dir.mkdir.side_effect = [FileExistsError("No PID"), None]
    mock_runner.config.lock_ttl = 3600

    acquire_lock(mock_runner)

    mock_rmtree.assert_called_once_with(lock_dir)
    mock_runner.logger.info.assert_any_call("Evicted stale lock (no PID): /tmp/mock_lock")
    assert lock_dir.mkdir.call_count == 2


@patch('routine_workflow.lock.shutil.rmtree')
def test_release_lock_success(mock_rmtree, mock_lock_dir, mock_runner):
    """Test release removes lock dir."""
    lock_dir, pid_path, _ = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    mock_runner._lock_acquired = True
    pid_path.read_text.return_value = str(os.getpid())
    pid_path.exists.return_value = True
    mock_runner._pid_path = pid_path
    lock_dir.exists.return_value = True

    release_lock(mock_runner)

    pid_path.read_text.assert_called_once()
    mock_rmtree.assert_called_once_with(lock_dir)
    assert mock_runner._lock_acquired is False
    mock_runner.logger.info.assert_called_once_with("Lock directory removed")


@patch('routine_workflow.lock.shutil.rmtree')
def test_release_lock_stale_pid(mock_rmtree, mock_lock_dir, mock_runner):
    """Test leaves stale lock (different PID)."""
    lock_dir, pid_path, _ = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    mock_runner._lock_acquired = True
    pid_path.read_text.return_value = '9999'  # Different PID
    pid_path.exists.return_value = True
    mock_runner._pid_path = pid_path

    release_lock(mock_runner)

    mock_rmtree.assert_not_called()
    mock_runner.logger.warning.assert_called_once_with("Lock owned by different PID — leaving it in place")


def test_lock_context(mock_runner):
    """Test context manager acquires/releases."""
    with patch('routine_workflow.lock.acquire_lock') as mock_acquire, \
         patch('routine_workflow.lock.release_lock') as mock_release:

        with lock_context(mock_runner):
            pass  # Yield block

    mock_acquire.assert_called_once_with(mock_runner)
    mock_release.assert_called_once_with(mock_runner)


def test_cleanup_and_exit(mock_runner):
    """Test cleanup calls release."""
    with patch('routine_workflow.lock.release_lock') as mock_release:

        with pytest.raises(SystemExit) as exc:
            cleanup_and_exit(mock_runner, 1)

    assert exc.value.code == 1
    mock_runner.logger.info.assert_called_once_with("Exiting with code 1")
    mock_release.assert_called_once_with(mock_runner)


@patch('routine_workflow.lock.shutil.rmtree')
def test_release_lock_no_pid_best_effort(mock_rmtree, mock_lock_dir, mock_runner):
    """Test best-effort removal if no PID file."""
    lock_dir, pid_path, _ = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    mock_runner._lock_acquired = True
    pid_path.exists.return_value = False
    mock_runner._pid_path = pid_path
    lock_dir.exists.return_value = True

    release_lock(mock_runner)

    mock_rmtree.assert_called_once_with(lock_dir)
    mock_runner.logger.info.assert_called_once_with("Stale lock dir removed")


@patch('routine_workflow.lock.shutil.rmtree')
def test_acquire_lock_exception(mock_rmtree, mock_lock_dir, mock_runner):
    """Test general exception in acquire_lock."""
    lock_dir, _, _ = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.mkdir.side_effect = Exception("IOError")

    with patch.object(mock_runner.logger, 'exception') as mock_exc:
        with pytest.raises(SystemExit) as exc:
            acquire_lock(mock_runner)

    assert exc.value.code == 3
    mock_exc.assert_called_once_with('Failed to acquire lock: IOError')
    
    
@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
def test_acquire_lock_eviction_error(mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test warn on eviction error; fail acquire."""
    lock_dir, pid_path, ts_path = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.exists.return_value = True
    ts_path.exists.return_value = True
    ts_path.read_text.return_value = str(1720000000.0 - 1800)  # Fresh, to reach rmtree
    pid_path.exists.return_value = True
    pid_path.read_text.return_value = "1234"  # Valid PID
    lock_dir.mkdir.side_effect = FileExistsError("Evict fail")
    mock_rmtree.side_effect = PermissionError("Evict fail")
    mock_runner.config.lock_ttl = 3600

    with pytest.raises(SystemExit) as exc:
        acquire_lock(mock_runner)

    assert exc.value.code == 3
    mock_runner.logger.warning.assert_called_once_with("Failed to evict stale lock: Evict fail — treating as active")
    mock_runner.logger.error.assert_called_once_with("Lock exists: /tmp/mock_lock — concurrent run detected")

@patch('routine_workflow.lock.shutil.rmtree')
@patch('routine_workflow.lock.os.getpid', return_value=1234)
@patch('routine_workflow.lock.time.time', return_value=1720000000.0)
def test_acquire_lock_eviction_by_dead_pid(mock_time, mock_pid, mock_rmtree, mock_lock_dir, mock_runner):
    """Test eviction if PID dead (os.kill raises OSError); then retry."""
    lock_dir, pid_path, ts_path = mock_lock_dir
    mock_runner.config.lock_dir = lock_dir
    lock_dir.exists.return_value = True
    ts_path.exists.return_value = True
    ts_path.read_text.return_value = str(mock_time.return_value - 1800)  # Fresh < TTL
    pid_path.exists.return_value = True
    pid_path.read_text.return_value = "invalid"  # Triggers ValueError in int(pid_str)
    lock_dir.mkdir.side_effect = [FileExistsError("Stale"), None]  # First fails, retry succeeds
    mock_runner.config.lock_ttl = 3600
    with patch('routine_workflow.lock.os.kill', side_effect=OSError("Dead")):  # Simulates dead PID

        acquire_lock(mock_runner)

    mock_rmtree.assert_called_once_with(lock_dir)
    mock_runner.logger.info.assert_any_call("Evicted stale lock (dead PID): /tmp/mock_lock")
    assert lock_dir.mkdir.call_count == 2
