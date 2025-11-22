"""Run manifest and reproducibility metadata.

This module provides data structures and utilities for capturing full run manifests
including code versions, model revisions, and configuration digests for auditability
and reproducibility.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class ComponentVersion:
    """Version information for a pipeline component."""
    
    name: str
    version: str
    type: str  # e.g., "ocr_engine", "llm_provider", "detector"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RunManifest:
    """Complete manifest for a pipeline run capturing all reproducibility metadata."""
    
    # Run identification
    run_id: str
    timestamp: str
    
    # Code version
    git_commit: Optional[str] = None
    git_branch: Optional[str] = None
    git_dirty: bool = False
    version_string: Optional[str] = None
    
    # Configuration
    config_digest: str = ""
    config_snapshot: Dict[str, Any] = field(default_factory=dict)
    
    # Environment
    python_version: str = ""
    platform_system: str = ""
    platform_release: str = ""
    
    # Component versions
    components: list[ComponentVersion] = field(default_factory=list)
    
    # Dependencies
    package_versions: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary for serialization."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert manifest to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


def get_git_info() -> tuple[Optional[str], Optional[str], bool]:
    """Get git commit, branch, and dirty status.
    
    Returns:
        Tuple of (commit_hash, branch_name, is_dirty)
    """
    try:
        # Get commit hash
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        
        # Get branch name
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        
        # Check if dirty (uncommitted changes)
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        is_dirty = len(status) > 0
        
        return commit, branch, is_dirty
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Git not available or not a git repo
        return None, None, False


def get_package_versions() -> Dict[str, str]:
    """Get versions of key installed packages.
    
    Returns:
        Dictionary mapping package names to versions
    """
    packages = {}
    
    # Key packages to track
    package_names = [
        "pdfplumber",
        "pillow",
        "numpy",
        "opencv-python",
        "pydantic",
        "google-generativeai",
        "openai",
    ]
    
    for pkg_name in package_names:
        try:
            import importlib.metadata
            version = importlib.metadata.version(pkg_name)
            packages[pkg_name] = version
        except importlib.metadata.PackageNotFoundError:
            packages[pkg_name] = "not_installed"
    
    return packages


def compute_config_digest(config: Any) -> str:
    """Compute a deterministic hash of the pipeline configuration.
    
    Args:
        config: PipelineConfig instance or dict
        
    Returns:
        SHA256 hex digest of the configuration
    """
    # Convert config to dict if needed
    if hasattr(config, "__dict__"):
        config_dict = {k: v for k, v in config.__dict__.items() if not k.startswith("_")}
    else:
        config_dict = dict(config)
    
    # Remove sensitive fields
    sensitive_fields = ["llm_api_key", "api_key"]
    for field in sensitive_fields:
        config_dict.pop(field, None)
    
    # Convert to JSON string (sorted keys for determinism)
    config_json = json.dumps(config_dict, sort_keys=True, default=str)
    
    # Compute SHA256
    return hashlib.sha256(config_json.encode()).hexdigest()


def create_run_manifest(
    run_id: str,
    config: Any,
    components: Optional[list[ComponentVersion]] = None,
) -> RunManifest:
    """Create a complete run manifest.
    
    Args:
        run_id: Unique identifier for this run
        config: PipelineConfig instance
        components: Optional list of component versions
        
    Returns:
        RunManifest instance
    """
    # Get git info
    git_commit, git_branch, git_dirty = get_git_info()
    
    # Get version string (from package or env var)
    version_string = os.getenv("PDF_READER_VERSION", "dev")
    
    # Compute config digest
    config_digest = compute_config_digest(config)
    
    # Get config snapshot (sanitized)
    if hasattr(config, "__dict__"):
        config_snapshot = {k: v for k, v in config.__dict__.items() if not k.startswith("_")}
    else:
        config_snapshot = dict(config)
    
    # Remove sensitive fields from snapshot
    sensitive_fields = ["llm_api_key", "api_key"]
    for field in sensitive_fields:
        config_snapshot.pop(field, None)
    
    # Convert Path objects to strings for serialization
    for key, value in config_snapshot.items():
        if isinstance(value, Path):
            config_snapshot[key] = str(value)
    
    # Get package versions
    package_versions = get_package_versions()
    
    # Create manifest
    manifest = RunManifest(
        run_id=run_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        git_commit=git_commit,
        git_branch=git_branch,
        git_dirty=git_dirty,
        version_string=version_string,
        config_digest=config_digest,
        config_snapshot=config_snapshot,
        python_version=sys.version,
        platform_system=platform.system(),
        platform_release=platform.release(),
        components=components or [],
        package_versions=package_versions,
    )
    
    return manifest


def save_manifest(manifest: RunManifest, output_path: Path) -> None:
    """Save manifest to a JSON file.
    
    Args:
        manifest: RunManifest to save
        output_path: Path to output file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w") as f:
        f.write(manifest.to_json())


def load_manifest(manifest_path: Path) -> RunManifest:
    """Load manifest from a JSON file.
    
    Args:
        manifest_path: Path to manifest file
        
    Returns:
        RunManifest instance
    """
    with open(manifest_path, "r") as f:
        data = json.load(f)
    
    # Convert components list to ComponentVersion objects
    if "components" in data:
        data["components"] = [
            ComponentVersion(**comp) for comp in data["components"]
        ]
    
    return RunManifest(**data)


def compare_manifests(manifest1: RunManifest, manifest2: RunManifest) -> Dict[str, Any]:
    """Compare two manifests and return differences.
    
    Args:
        manifest1: First manifest
        manifest2: Second manifest
        
    Returns:
        Dictionary describing differences
    """
    differences = {}
    
    # Compare git info
    if manifest1.git_commit != manifest2.git_commit:
        differences["git_commit"] = {
            "manifest1": manifest1.git_commit,
            "manifest2": manifest2.git_commit,
        }
    
    # Compare config digests
    if manifest1.config_digest != manifest2.config_digest:
        differences["config_digest"] = {
            "manifest1": manifest1.config_digest,
            "manifest2": manifest2.config_digest,
        }
    
    # Compare package versions
    pkg_diffs = {}
    all_packages = set(manifest1.package_versions.keys()) | set(manifest2.package_versions.keys())
    for pkg in all_packages:
        v1 = manifest1.package_versions.get(pkg)
        v2 = manifest2.package_versions.get(pkg)
        if v1 != v2:
            pkg_diffs[pkg] = {"manifest1": v1, "manifest2": v2}
    
    if pkg_diffs:
        differences["package_versions"] = pkg_diffs
    
    # Compare component versions
    comp_diffs = {}
    comp1_by_name = {c.name: c.version for c in manifest1.components}
    comp2_by_name = {c.name: c.version for c in manifest2.components}
    all_components = set(comp1_by_name.keys()) | set(comp2_by_name.keys())
    
    for comp in all_components:
        v1 = comp1_by_name.get(comp)
        v2 = comp2_by_name.get(comp)
        if v1 != v2:
            comp_diffs[comp] = {"manifest1": v1, "manifest2": v2}
    
    if comp_diffs:
        differences["components"] = comp_diffs
    
    return differences


