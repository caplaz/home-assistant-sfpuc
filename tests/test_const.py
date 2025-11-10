"""Tests for SF Water constants and configuration."""

import json
from pathlib import Path

import pytest

from custom_components.sfpuc.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


class TestConstants:
    """Test the constants defined in const.py."""

    def test_domain_constant(self):
        """Test DOMAIN constant."""
        assert DOMAIN == "sfpuc"
        assert isinstance(DOMAIN, str)
        assert len(DOMAIN) > 0

    def test_config_constants(self):
        """Test configuration key constants."""
        assert CONF_USERNAME == "username"
        assert CONF_PASSWORD == "password"

        # Ensure they are different
        assert CONF_USERNAME != CONF_PASSWORD

    def test_update_interval_constant(self):
        """Test update interval constant."""
        assert DEFAULT_UPDATE_INTERVAL == 720  # 12 hours in minutes
        assert isinstance(DEFAULT_UPDATE_INTERVAL, int)
        assert DEFAULT_UPDATE_INTERVAL > 0

    def test_update_interval_calculation(self):
        """Test that update interval makes sense."""
        # Should be reasonable for daily data (not too frequent, not too infrequent)
        assert 60 <= DEFAULT_UPDATE_INTERVAL <= 1440  # Between 1 hour and 1 day


class TestManifest:
    """Test the manifest.json file."""

    def test_manifest_exists(self):
        """Test that manifest.json exists."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )
        assert manifest_path.exists()

    def test_manifest_is_valid_json(self):
        """Test that manifest.json is valid JSON."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        assert isinstance(manifest_data, dict)

    def test_manifest_required_fields(self):
        """Test that manifest.json has all required fields."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        required_fields = [
            "domain",
            "name",
            "codeowners",
            "config_flow",
            "documentation",
            "integration_type",
            "iot_class",
            "issue_tracker",
            "requirements",
            "version",
        ]

        for field in required_fields:
            assert field in manifest, f"Missing required field: {field}"

    def test_manifest_domain_matches(self):
        """Test that manifest domain matches the DOMAIN constant."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["domain"] == DOMAIN

    def test_manifest_config_flow_enabled(self):
        """Test that config_flow is enabled in manifest."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["config_flow"] is True

    def test_manifest_integration_type(self):
        """Test that integration type is appropriate."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Should be a device or service integration
        assert manifest["integration_type"] in [
            "device",
            "service",
            "hub",
            "integration",
        ]

    def test_manifest_iot_class(self):
        """Test that IoT class is appropriate for this integration."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        # Should be cloud_polling for web scraping integration
        assert manifest["iot_class"] == "cloud_polling"

    def test_manifest_requirements(self):
        """Test that manifest requirements are reasonable."""
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        requirements = manifest["requirements"]
        assert isinstance(requirements, list)
        assert len(requirements) > 0

        # Should include requests and beautifulsoup4
        req_strings = [str(req) for req in requirements]
        assert any("requests" in req for req in req_strings)
        assert any("beautifulsoup4" in req for req in req_strings)


class TestVersionConsistency:
    """Test version consistency across files."""

    def test_pyproject_version_matches_manifest(self):
        """Test that pyproject.toml version matches manifest.json version."""
        # Read manifest version
        manifest_path = (
            Path(__file__).parent.parent
            / "custom_components"
            / "sfpuc"
            / "manifest.json"
        )
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest_version = manifest["version"]

        # Read pyproject version
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Simple version extraction (this could be improved)
            for line in content.split("\n"):
                if line.startswith("version = "):
                    pyproject_version = line.split("=")[1].strip().strip('"')
                    break
            else:
                pytest.skip("Could not find version in pyproject.toml")

        assert manifest_version == pyproject_version
