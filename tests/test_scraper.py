"""Tests for SF Water integration."""

from datetime import datetime
from unittest.mock import Mock, patch

from custom_components.sf_water.coordinator import SFPUCScraper


class TestSFPUCScraper:
    """Test the SFPUC scraper functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.username = "test@example.com"
        self.password = "testpass"
        self.scraper = SFPUCScraper(self.username, self.password)

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_login_success(self, mock_post, mock_get):
        """Test successful login."""
        # Mock the login page response
        login_page = Mock()
        login_page.status_code = 200
        login_page.content = b"""
        <html>
            <form>
                <input name="__VIEWSTATE" value="test_viewstate" />
                <input name="__EVENTVALIDATION" value="test_validation" />
            </form>
        </html>
        """
        mock_get.return_value = login_page

        # Mock the login POST response
        login_response = Mock()
        login_response.status_code = 200
        login_response.url = "https://myaccount-water.sfpuc.org/MY_ACCOUNT_RSF.aspx"
        login_response.text = "Welcome to your account"
        mock_post.return_value = login_response

        result = self.scraper.login()
        assert result is True

        # Verify login was called with correct data
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["data"]["tb_USER_ID"] == self.username
        assert call_args[1]["data"]["tb_USER_PSWD"] == self.password

    @patch("requests.Session.get")
    def test_login_failure_no_form(self, mock_get):
        """Test login failure when form is not found."""
        login_page = Mock()
        login_page.content = b"<html><body>No form here</body></html>"
        mock_get.return_value = login_page

        result = self.scraper.login()
        assert result is False

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_login_failure_invalid_credentials(self, mock_post, mock_get):
        """Test login failure with invalid credentials."""
        # Mock the login page response
        login_page = Mock()
        login_page.content = b"""
        <html>
            <form>
                <input name="__VIEWSTATE" value="test_viewstate" />
                <input name="__EVENTVALIDATION" value="test_validation" />
            </form>
        </html>
        """
        mock_get.return_value = login_page

        # Mock the login POST response (redirected back to login)
        login_response = Mock()
        login_response.url = "https://myaccount-water.sfpuc.org/"
        login_response.text = "Invalid credentials"
        mock_post.return_value = login_response

        result = self.scraper.login()
        assert result is False

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_hourly_success(self, mock_post, mock_get):
        """Test successful hourly usage data retrieval."""
        # Mock the usage page response
        usage_page = Mock()
        usage_page.content = b"""
        <html>
            <form>
                <input name="token1" value="value1" />
                <input name="token2" value="value2" />
            </form>
        </html>
        """
        mock_get.return_value = usage_page

        # Mock the download response with Excel data
        download_response = Mock()
        download_response.url = (
            "https://myaccount-water.sfpuc.org/TRANSACTIONS_EXCEL_DOWNLOAD.aspx"
        )
        download_response.content = (
            b"Date\tUsage\n10/01/2023 10:00:00\t50.5\n10/01/2023 11:00:00\t45.2\n"
        )
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 10, 1)

        result = self.scraper.get_usage_data(start_date, end_date, "hourly")

        assert result is not None
        assert len(result) == 2
        assert result[0]["timestamp"] == datetime(2023, 10, 1, 10, 0, 0)
        assert result[0]["usage"] == 50.5
        assert result[0]["resolution"] == "hourly"
        assert result[1]["timestamp"] == datetime(2023, 10, 1, 11, 0, 0)
        assert result[1]["usage"] == 45.2

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_daily_success(self, mock_post, mock_get):
        """Test successful daily usage data retrieval."""
        # Mock the usage page response
        usage_page = Mock()
        usage_page.content = b"""
        <html>
            <form>
                <input name="token1" value="value1" />
            </form>
        </html>
        """
        mock_get.return_value = usage_page

        # Mock the download response
        download_response = Mock()
        download_response.url = (
            "https://myaccount-water.sfpuc.org/TRANSACTIONS_EXCEL_DOWNLOAD.aspx"
        )
        download_response.content = (
            b"Date\tUsage\n10/01/2023\t150.5\n10/02/2023\t145.2\n"
        )
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 10, 2)

        result = self.scraper.get_usage_data(start_date, end_date, "daily")

        assert result is not None
        assert len(result) == 2
        assert result[0]["timestamp"] == datetime(2023, 10, 1)
        assert result[0]["usage"] == 150.5
        assert result[0]["resolution"] == "daily"

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_monthly_success(self, mock_post, mock_get):
        """Test successful monthly usage data retrieval."""
        # Mock the usage page response
        usage_page = Mock()
        usage_page.content = b"""
        <html>
            <form>
                <input name="token1" value="value1" />
            </form>
        </html>
        """
        mock_get.return_value = usage_page

        # Mock the download response
        download_response = Mock()
        download_response.url = (
            "https://myaccount-water.sfpuc.org/TRANSACTIONS_EXCEL_DOWNLOAD.aspx"
        )
        download_response.content = b"Date\tUsage\n10/2023\t4500.5\n11/2023\t4200.2\n"
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 11, 1)

        result = self.scraper.get_usage_data(start_date, end_date, "monthly")

        assert result is not None
        assert len(result) == 2
        assert result[0]["timestamp"] == datetime(2023, 10, 1)
        assert result[0]["usage"] == 4500.5
        assert result[0]["resolution"] == "monthly"

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_wrong_url(self, mock_post, mock_get):
        """Test usage data retrieval when redirected to wrong URL."""
        # Mock the usage page response
        usage_page = Mock()
        usage_page.content = b"""
        <html>
            <form>
                <input name="token1" value="value1" />
            </form>
        </html>
        """
        mock_get.return_value = usage_page

        # Mock the download response (wrong URL)
        download_response = Mock()
        download_response.url = "https://myaccount-water.sfpuc.org/some_other_page.aspx"
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        result = self.scraper.get_usage_data(start_date, None, "daily")

        assert result is None

    def test_get_usage_data_invalid_resolution(self):
        """Test usage data retrieval with invalid resolution."""
        start_date = datetime(2023, 10, 1)
        result = self.scraper.get_usage_data(start_date, None, "invalid")

        assert result is None

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_parse_error(self, mock_post, mock_get):
        """Test usage data retrieval with parsing errors."""
        # Mock the usage page response
        usage_page = Mock()
        usage_page.content = b"""
        <html>
            <form>
                <input name="token1" value="value1" />
            </form>
        </html>
        """
        mock_get.return_value = usage_page

        # Mock the download response with malformed data
        download_response = Mock()
        download_response.url = (
            "https://myaccount-water.sfpuc.org/TRANSACTIONS_EXCEL_DOWNLOAD.aspx"
        )
        download_response.content = b"Date\tUsage\ninvalid_date\tinvalid_usage\n"
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        result = self.scraper.get_usage_data(start_date, None, "daily")

        # Should return empty list since parsing failed
        assert result == []

    def test_get_daily_usage_legacy(self):
        """Test the legacy get_daily_usage method."""
        with patch.object(self.scraper, "get_usage_data") as mock_get_data:
            mock_get_data.return_value = [
                {"timestamp": datetime(2023, 10, 1, 10, 0), "usage": 50.0},
                {"timestamp": datetime(2023, 10, 1, 11, 0), "usage": 45.0},
            ]

            result = self.scraper.get_daily_usage()
            assert result == 95.0  # Sum of hourly usage
            mock_get_data.assert_called_once()

    def test_get_daily_usage_no_data(self):
        """Test the legacy get_daily_usage method with no data."""
        with patch.object(self.scraper, "get_usage_data") as mock_get_data:
            mock_get_data.return_value = None

            result = self.scraper.get_daily_usage()
            assert result is None
