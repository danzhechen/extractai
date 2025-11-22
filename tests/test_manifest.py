"""Tests for run manifest and reproducibility metadata."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from pdf_reader.manifest import (
    ComponentVersion,
    RunManifest,
    compute_config_digest,
    create_run_manifest,
    save_manifest,
    load_manifest,
    compare_manifests,
    get_git_info,
    get_package_versions,
)
from pdf_reader.pipeline import PipelineConfig


def test_component_version_creation():
    """Test ComponentVersion dataclass creation."""
    component = ComponentVersion(
        name="TestComponent",
        version="1.0.0",
        type="detector",
        metadata={"key": "value"},
    )
    
    assert component.name == "TestComponent"
    assert component.version == "1.0.0"
    assert component.type == "detector"
    assert component.metadata == {"key": "value"}


def test_run_manifest_creation():
    """Test RunManifest dataclass creation."""
    manifest = RunManifest(
        run_id="test-run-123",
        timestamp="2025-11-21T12:00:00Z",
        git_commit="abc123",
        git_branch="main",
        git_dirty=False,
        version_string="1.0.0",
        config_digest="digest123",
        python_version="3.10.0",
        platform_system="Linux",
        platform_release="5.15.0",
    )
    
    assert manifest.run_id == "test-run-123"
    assert manifest.git_commit == "abc123"
    assert manifest.config_digest == "digest123"


def test_run_manifest_to_dict():
    """Test RunManifest serialization to dict."""
    manifest = RunManifest(
        run_id="test-run",
        timestamp="2025-11-21T12:00:00Z",
    )
    
    data = manifest.to_dict()
    assert isinstance(data, dict)
    assert data["run_id"] == "test-run"
    assert data["timestamp"] == "2025-11-21T12:00:00Z"


def test_run_manifest_to_json():
    """Test RunManifest serialization to JSON."""
    manifest = RunManifest(
        run_id="test-run",
        timestamp="2025-11-21T12:00:00Z",
    )
    
    json_str = manifest.to_json()
    assert isinstance(json_str, str)
    
    # Verify it's valid JSON
    data = json.loads(json_str)
    assert data["run_id"] == "test-run"


def test_compute_config_digest():
    """Test config digest computation."""
    config1 = PipelineConfig(dpi=200, default_rows=2, default_cols=3)
    config2 = PipelineConfig(dpi=200, default_rows=2, default_cols=3)
    config3 = PipelineConfig(dpi=300, default_rows=2, default_cols=3)
    
    digest1 = compute_config_digest(config1)
    digest2 = compute_config_digest(config2)
    digest3 = compute_config_digest(config3)
    
    # Same config should produce same digest
    assert digest1 == digest2
    
    # Different config should produce different digest
    assert digest1 != digest3
    
    # Digest should be a hex string
    assert isinstance(digest1, str)
    assert len(digest1) == 64  # SHA256 hex digest


def test_compute_config_digest_excludes_sensitive_fields():
    """Test that sensitive fields are excluded from digest."""
    config1 = PipelineConfig(dpi=200, llm_api_key="secret-key-1")
    config2 = PipelineConfig(dpi=200, llm_api_key="secret-key-2")
    
    digest1 = compute_config_digest(config1)
    digest2 = compute_config_digest(config2)
    
    # Digests should be the same despite different API keys
    assert digest1 == digest2


def test_get_package_versions():
    """Test package version collection."""
    versions = get_package_versions()
    
    assert isinstance(versions, dict)
    # Should include key packages
    assert "pdfplumber" in versions
    assert "pillow" in versions
    assert "numpy" in versions


@patch("pdf_reader.manifest.subprocess.check_output")
def test_get_git_info_success(mock_check_output):
    """Test git info collection when git is available."""
    mock_check_output.side_effect = [
        "abc123def456\n",  # commit hash
        "main\n",  # branch name
        "",  # status (clean)
    ]
    
    commit, branch, is_dirty = get_git_info()
    
    assert commit == "abc123def456"
    assert branch == "main"
    assert is_dirty is False


@patch("pdf_reader.manifest.subprocess.check_output")
def test_get_git_info_dirty(mock_check_output):
    """Test git info collection with uncommitted changes."""
    mock_check_output.side_effect = [
        "abc123def456\n",
        "main\n",
        "M file.py\n",  # Modified file
    ]
    
    commit, branch, is_dirty = get_git_info()
    
    assert is_dirty is True


@patch("pdf_reader.manifest.subprocess.check_output")
def test_get_git_info_not_available(mock_check_output):
    """Test git info collection when git is not available."""
    mock_check_output.side_effect = FileNotFoundError()
    
    commit, branch, is_dirty = get_git_info()
    
    assert commit is None
    assert branch is None
    assert is_dirty is False


def test_create_run_manifest():
    """Test full run manifest creation."""
    config = PipelineConfig(dpi=200, default_rows=2)
    components = [
        ComponentVersion(name="Detector", version="1.0", type="detector"),
    ]
    
    manifest = create_run_manifest(
        run_id="test-run-123",
        config=config,
        components=components,
    )
    
    assert manifest.run_id == "test-run-123"
    assert manifest.timestamp is not None
    assert manifest.config_digest != ""
    assert manifest.python_version != ""
    assert len(manifest.components) == 1
    assert manifest.components[0].name == "Detector"
    
    # Config snapshot should not contain sensitive fields
    assert "llm_api_key" not in manifest.config_snapshot


def test_save_and_load_manifest():
    """Test saving and loading manifest from file."""
    manifest = RunManifest(
        run_id="test-run",
        timestamp="2025-11-21T12:00:00Z",
        git_commit="abc123",
        config_digest="digest123",
        components=[
            ComponentVersion(name="Test", version="1.0", type="test"),
        ],
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        manifest_path = Path(tmpdir) / "manifest.json"
        
        # Save
        save_manifest(manifest, manifest_path)
        assert manifest_path.exists()
        
        # Load
        loaded_manifest = load_manifest(manifest_path)
        assert loaded_manifest.run_id == manifest.run_id
        assert loaded_manifest.git_commit == manifest.git_commit
        assert len(loaded_manifest.components) == 1
        assert loaded_manifest.components[0].name == "Test"


def test_compare_manifests_identical():
    """Test comparing identical manifests."""
    manifest1 = RunManifest(
        run_id="run1",
        timestamp="2025-11-21T12:00:00Z",
        git_commit="abc123",
        config_digest="digest123",
    )
    
    manifest2 = RunManifest(
        run_id="run2",
        timestamp="2025-11-21T12:01:00Z",
        git_commit="abc123",
        config_digest="digest123",
    )
    
    differences = compare_manifests(manifest1, manifest2)
    
    # Should have no differences (run_id and timestamp are not compared)
    assert len(differences) == 0


def test_compare_manifests_different_git():
    """Test comparing manifests with different git commits."""
    manifest1 = RunManifest(
        run_id="run1",
        timestamp="2025-11-21T12:00:00Z",
        git_commit="abc123",
        config_digest="digest123",
    )
    
    manifest2 = RunManifest(
        run_id="run2",
        timestamp="2025-11-21T12:01:00Z",
        git_commit="def456",
        config_digest="digest123",
    )
    
    differences = compare_manifests(manifest1, manifest2)
    
    assert "git_commit" in differences
    assert differences["git_commit"]["manifest1"] == "abc123"
    assert differences["git_commit"]["manifest2"] == "def456"


def test_compare_manifests_different_config():
    """Test comparing manifests with different config digests."""
    manifest1 = RunManifest(
        run_id="run1",
        timestamp="2025-11-21T12:00:00Z",
        config_digest="digest123",
    )
    
    manifest2 = RunManifest(
        run_id="run2",
        timestamp="2025-11-21T12:01:00Z",
        config_digest="digest456",
    )
    
    differences = compare_manifests(manifest1, manifest2)
    
    assert "config_digest" in differences


def test_compare_manifests_different_packages():
    """Test comparing manifests with different package versions."""
    manifest1 = RunManifest(
        run_id="run1",
        timestamp="2025-11-21T12:00:00Z",
        package_versions={"numpy": "1.24.0", "pillow": "10.0.0"},
    )
    
    manifest2 = RunManifest(
        run_id="run2",
        timestamp="2025-11-21T12:01:00Z",
        package_versions={"numpy": "1.25.0", "pillow": "10.0.0"},
    )
    
    differences = compare_manifests(manifest1, manifest2)
    
    assert "package_versions" in differences
    assert "numpy" in differences["package_versions"]
    assert differences["package_versions"]["numpy"]["manifest1"] == "1.24.0"
    assert differences["package_versions"]["numpy"]["manifest2"] == "1.25.0"


def test_compare_manifests_different_components():
    """Test comparing manifests with different component versions."""
    manifest1 = RunManifest(
        run_id="run1",
        timestamp="2025-11-21T12:00:00Z",
        components=[
            ComponentVersion(name="Detector", version="1.0", type="detector"),
        ],
    )
    
    manifest2 = RunManifest(
        run_id="run2",
        timestamp="2025-11-21T12:01:00Z",
        components=[
            ComponentVersion(name="Detector", version="2.0", type="detector"),
        ],
    )
    
    differences = compare_manifests(manifest1, manifest2)
    
    assert "components" in differences
    assert "Detector" in differences["components"]
    assert differences["components"]["Detector"]["manifest1"] == "1.0"
    assert differences["components"]["Detector"]["manifest2"] == "2.0"


