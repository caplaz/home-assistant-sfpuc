"""Tests for San Francisco Water Power Sewer integration."""

from datetime import datetime
from unittest.mock import Mock, patch

from custom_components.sfpuc.coordinator import SFPUCScraper


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

    @staticmethod
    def _login_page_mock():
        """Return a mock sign-in page carrying the required form tokens."""
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
        return login_page

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_login_failure_stays_on_login_aspx(self, mock_post, mock_get):
        """A rejected sign-in that lands on LOGIN.aspx must report failure.

        Regression test: the portal serves its sign-in page with the word
        "Account" in the body, so body-keyword scoring reported a false
        success while the session stayed unauthenticated. Every later
        request then hit the portal's error page.
        """
        mock_get.return_value = self._login_page_mock()

        login_response = Mock()
        login_response.status_code = 200
        login_response.url = "https://myaccount-water.sfpuc.org/LOGIN.aspx"
        # The real sign-in page contains "Account" but no session markers.
        login_response.text = "<html>Sign in to My Account</html>"
        mock_post.return_value = login_response

        assert self.scraper.login() is False

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_login_failure_unexpected_landing_page(self, mock_post, mock_get):
        """An unrecognised landing page with no session marker is a failure."""
        mock_get.return_value = self._login_page_mock()

        login_response = Mock()
        login_response.status_code = 200
        login_response.url = "https://myaccount-water.sfpuc.org/MAINTENANCE.aspx"
        login_response.text = "<html>The portal is temporarily unavailable</html>"
        mock_post.return_value = login_response

        assert self.scraper.login() is False

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_login_success_via_session_marker(self, mock_post, mock_get):
        """A different landing page still succeeds when a session marker is present."""
        mock_get.return_value = self._login_page_mock()

        login_response = Mock()
        login_response.status_code = 200
        login_response.url = "https://myaccount-water.sfpuc.org/ACCOUNT_SUMMARY.aspx"
        login_response.text = "<html><a href='/logoff'>Logout</a></html>"
        mock_post.return_value = login_response

        assert self.scraper.login() is True

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
        download_response.content = b"Date\tUsage\n7 AM\t50.5\n8 AM\t45.2\n"
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 10, 1)

        result = self.scraper.get_usage_data(start_date, end_date, "hourly")

        assert result is not None
        assert len(result) == 2
        # Should use the requested end_date for timestamps
        request_date = end_date.date()
        assert result[0]["timestamp"] == datetime.combine(
            request_date, datetime.min.time().replace(hour=7)
        )
        assert result[0]["usage"] == 50.5
        assert result[0]["resolution"] == "hourly"
        assert result[1]["timestamp"] == datetime.combine(
            request_date, datetime.min.time().replace(hour=8)
        )
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
        download_response.content = b"Date\tUsage\n10/01\t150.5\n10/02\t145.2\n"
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 10, 2)

        result = self.scraper.get_usage_data(start_date, end_date, "daily")

        assert result is not None
        assert len(result) == 2
        # Should use the requested year for timestamps
        assert result[0]["timestamp"] == datetime(2023, 10, 1)
        assert result[0]["usage"] == 150.5
        assert result[0]["resolution"] == "daily"
        assert result[1]["timestamp"] == datetime(2023, 10, 2)
        assert result[1]["usage"] == 145.2

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
        download_response.content = b"Date\tUsage\nOct 23\t4500.5\nNov 23\t4200.2\n"
        mock_post.return_value = download_response

        start_date = datetime(2023, 10, 1)
        end_date = datetime(2023, 11, 1)

        result = self.scraper.get_usage_data(start_date, end_date, "monthly")

        assert result is not None
        assert len(result) == 2
        # Should parse "Oct 23" as 2023-10-01 and "Nov 23" as 2023-11-01
        assert result[0]["timestamp"] == datetime(2023, 10, 1)
        assert result[0]["usage"] == 4500.5
        assert result[0]["resolution"] == "monthly"
        assert result[1]["timestamp"] == datetime(2023, 11, 1)
        assert result[1]["usage"] == 4200.2

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

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_daily_sfpuc_format_success(self, mock_post, mock_get):
        """Test successful daily usage data retrieval with real SFPUC format (MM/DD without year)."""
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

        # Mock the download response with SFPUC's actual daily format
        download_response = Mock()
        download_response.url = (
            "https://myaccount-water.sfpuc.org/TRANSACTIONS_EXCEL_DOWNLOAD.aspx"
        )
        download_response.content = b"Date\tUsage\n8/11\t97\n8/12\t112\n"
        mock_post.return_value = download_response

        start_date = datetime(2025, 8, 11)
        end_date = datetime(2025, 8, 12)

        result = self.scraper.get_usage_data(start_date, end_date, "daily")

        assert result is not None
        assert len(result) == 2
        # Should use current year (2025) for the timestamps
        assert result[0]["timestamp"] == datetime(2025, 8, 11)
        assert result[0]["usage"] == 97
        assert result[0]["resolution"] == "daily"
        assert result[1]["timestamp"] == datetime(2025, 8, 12)
        assert result[1]["usage"] == 112

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_hourly_sfpuc_format_success(self, mock_post, mock_get):
        """Test successful hourly usage data retrieval with real SFPUC format (HH AM/PM without date)."""
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

        # Mock the download response with SFPUC's actual hourly format
        download_response = Mock()
        download_response.url = (
            "https://myaccount-water.sfpuc.org/TRANSACTIONS_EXCEL_DOWNLOAD.aspx"
        )
        download_response.content = (
            b"Date\tUsage\n7 AM\t7.48\n8 AM\t14.96\n12 PM\t0\n1 PM\t0\n"
        )
        mock_post.return_value = download_response

        start_date = datetime(2025, 11, 9)
        end_date = datetime(2025, 11, 9)

        result = self.scraper.get_usage_data(start_date, end_date, "hourly")

        assert result is not None
        assert len(result) == 4
        # Should use the requested end_date for the timestamps
        request_date = end_date.date()
        assert result[0]["timestamp"] == datetime.combine(
            request_date, datetime.min.time().replace(hour=7)
        )
        assert result[0]["usage"] == 7.48
        assert result[0]["resolution"] == "hourly"
        assert result[1]["timestamp"] == datetime.combine(
            request_date, datetime.min.time().replace(hour=8)
        )
        assert result[1]["usage"] == 14.96
        assert result[2]["timestamp"] == datetime.combine(
            request_date, datetime.min.time().replace(hour=12)
        )
        assert result[2]["usage"] == 0
        assert result[3]["timestamp"] == datetime.combine(
            request_date, datetime.min.time().replace(hour=13)
        )
        assert result[3]["usage"] == 0

    @patch("requests.Session.get")
    @patch("requests.Session.post")
    def test_get_usage_data_monthly_sfpuc_format_success(self, mock_post, mock_get):
        """Test successful monthly usage data retrieval with real SFPUC format (Mon YY)."""
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

        # Mock the download response with SFPUC's actual monthly format
        download_response = Mock()
        download_response.url = (
            "https://myaccount-water.sfpuc.org/TRANSACTIONS_EXCEL_DOWNLOAD.aspx"
        )
        download_response.content = (
            b"Date\tConsumption in GALLONS\nMay 25\t2812\nJun 25\t2738\n"
        )
        mock_post.return_value = download_response

        start_date = datetime(2025, 5, 1)
        end_date = datetime(2025, 6, 30)

        result = self.scraper.get_usage_data(start_date, end_date, "monthly")

        assert result is not None
        assert len(result) == 2
        # Should parse "May 25" as 2025-05-01 and "Jun 25" as 2025-06-01
        assert result[0]["timestamp"] == datetime(2025, 5, 1)
        assert result[0]["usage"] == 2812
        assert result[0]["resolution"] == "monthly"
        assert result[1]["timestamp"] == datetime(2025, 6, 1)
        assert result[1]["usage"] == 2738
