"""Common test utilities for San Francisco Water Power Sewer integration."""

from typing import Any
from unittest.mock import Mock

from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.sfpuc.const import DOMAIN


class MockConfigEntry:
    """Mock ConfigEntry for testing."""

    def __init__(
        self,
        entry_id: str = "test_entry",
        data: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        title: str = "San Francisco Water Power Sewer",
        version: int = 1,
        domain: str = DOMAIN,
    ):
        """Initialize mock config entry."""
        self.entry_id = entry_id
        self.data = data or {
            CONF_USERNAME: "test@example.com",
            CONF_PASSWORD: "testpass",
        }
        self.options = options or {}
        self.title = title
        self.version = version
        self.domain = domain
        self.runtime_data = None
        self.state = None
        self.reason = None

    def add_to_hass(self, hass):
        """Add entry to hass."""
        hass.config_entries._entries[self.entry_id] = self
        return self

    def async_start_reauth(self, hass, context=None):
        """Mock reauth start."""
        pass

    def async_update_entry(self, **kwargs):
        """Mock update entry."""
        for key, value in kwargs.items():
            setattr(self, key, value)
        return True

    def async_set_unique_id(self, unique_id):
        """Mock set unique id."""
        self.unique_id = unique_id
        return True


def mock_session_response(content: str = "", url: str = "", status_code: int = 200):
    """Create a mock requests response."""
    response = Mock()
    response.content = content.encode() if isinstance(content, str) else content
    response.text = content
    response.url = url
    response.status_code = status_code
    return response
