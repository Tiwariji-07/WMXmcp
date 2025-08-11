"""Tests for the Git manager."""
import os
import shutil
import pytest
from pathlib import Path
from wavemaker_wmx_mcp.git_manager import GitManager

@pytest.fixture
def test_repo_path(tmp_path):
    """Create a temporary directory for testing Git operations."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    return repo_path

def test_git_manager_init(test_repo_path):
    """Test GitManager initialization."""
    git_manager = GitManager(str(test_repo_path))
    assert git_manager.repo_path == Path(test_repo_path).resolve()
    assert git_manager.repo is None

# Note: Tests for clone, pull, and checkout_branch would require mocking Git operations
# or setting up a test Git repository, which is more complex and beyond this example.
