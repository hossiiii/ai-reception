from unittest.mock import MagicMock, patch

import pytest

from app.services.calendar_service import CalendarService


class TestCalendarService:
    """Test cases for CalendarService"""

    @pytest.fixture
    def calendar_service(self):
        return CalendarService()

    @pytest.fixture
    def mock_calendar_client(self):
        """Mock Google Calendar API client"""
        mock_client = MagicMock()
        mock_events = MagicMock()
        mock_events.list.return_value.execute.return_value = {
            'items': [
                {
                    'id': 'event1',
                    'summary': '山田太郎様との会議',
                    'description': 'プロジェクトについて',
                    'start': {'dateTime': '2024-01-01T10:00:00Z'},
                    'end': {'dateTime': '2024-01-01T11:00:00Z'},
                    'attendees': [
                        {
                            'email': 'yamada@test.com',
                            'displayName': '山田太郎',
                            'responseStatus': 'accepted'
                        }
                    ],
                    'creator': {
                        'email': 'creator@test.com',
                        'displayName': '作成者'
                    },
                    'organizer': {
                        'email': 'organizer@test.com',
                        'displayName': '主催者'
                    }
                }
            ]
        }
        mock_client.events.return_value = mock_events
        return mock_client

    @pytest.fixture
    def mock_empty_calendar_client(self):
        """Mock Google Calendar API client with no events"""
        mock_client = MagicMock()
        mock_events = MagicMock()
        mock_events.list.return_value.execute.return_value = {'items': []}
        mock_client.events.return_value = mock_events
        return mock_client

    @patch('app.services.calendar_service.CalendarService._get_calendar_client')
    @patch('app.services.calendar_service.CalendarService._get_meeting_room_calendars')
    @pytest.mark.asyncio
    async def test_check_todays_reservations_found(
        self,
        mock_get_calendars,
        mock_get_client,
        calendar_service,
        mock_calendar_client
    ):
        """Test reservation checking when reservation is found"""
        mock_get_client.return_value = mock_calendar_client
        # Only return one calendar to avoid duplicate events
        mock_get_calendars.return_value = {
            'A': 'calendar-a@group.calendar.google.com'
        }

        result = await calendar_service.check_todays_reservations('山田太郎')

        assert result['found'] is True
        assert result['identifier'] == '山田太郎'
        assert '山田太郎' in result['message']
        assert result['error'] is None
        assert result['roomName'] == '会議室A'
        assert len(result['events']) == 1

    @patch('app.services.calendar_service.CalendarService._get_calendar_client')
    @patch('app.services.calendar_service.CalendarService._get_meeting_room_calendars')
    @pytest.mark.asyncio
    async def test_check_todays_reservations_not_found(
        self,
        mock_get_calendars,
        mock_get_client,
        calendar_service,
        mock_empty_calendar_client
    ):
        """Test reservation checking when no reservation is found"""
        mock_get_client.return_value = mock_empty_calendar_client
        mock_get_calendars.return_value = {
            'A': 'calendar-a@group.calendar.google.com'
        }

        result = await calendar_service.check_todays_reservations('存在しない人')

        assert result['found'] is False
        assert result['identifier'] == '存在しない人'
        assert '予約が確認できませんでした' in result['message']
        assert result['error'] is None
        assert result['roomName'] is None
        assert result['events'] is None

    @patch('app.services.calendar_service.CalendarService._get_calendar_client')
    @patch('app.services.calendar_service.CalendarService._get_meeting_room_calendars')
    @pytest.mark.asyncio
    async def test_check_todays_reservations_api_error(
        self,
        mock_get_calendars,
        mock_get_client,
        calendar_service
    ):
        """Test reservation checking when API error occurs"""
        mock_get_client.side_effect = Exception("Google API Error")
        mock_get_calendars.return_value = {'A': 'calendar-a@group.calendar.google.com'}

        result = await calendar_service.check_todays_reservations('山田太郎')

        assert result['found'] is False
        assert result['identifier'] == '山田太郎'
        assert 'システムエラー' in result['message']
        assert result['error'] is True
        assert result['roomName'] is None

    @patch('app.services.calendar_service.settings')
    def test_get_meeting_room_calendars(self, mock_settings, calendar_service):
        """Test meeting room calendar ID parsing"""
        mock_settings.meeting_room_calendar_ids = 'cal1@group.calendar.google.com,cal2@group.calendar.google.com,cal3@group.calendar.google.com'

        calendars = calendar_service._get_meeting_room_calendars()

        assert len(calendars) == 3
        assert calendars['A'] == 'cal1@group.calendar.google.com'
        assert calendars['B'] == 'cal2@group.calendar.google.com'
        assert calendars['C'] == 'cal3@group.calendar.google.com'

    @patch('app.services.calendar_service.settings')
    def test_get_meeting_room_calendars_empty(self, mock_settings, calendar_service):
        """Test meeting room calendar ID parsing with empty config"""
        mock_settings.meeting_room_calendar_ids = ''

        with pytest.raises(ValueError, match='MEETING_ROOM_CALENDAR_IDS'):
            calendar_service._get_meeting_room_calendars()

    @patch('app.services.calendar_service.settings')
    @patch('app.services.calendar_service.service_account')
    def test_get_google_auth_success(self, mock_service_account, mock_settings, calendar_service):
        """Test successful Google authentication"""
        mock_settings.google_service_account_key = '{"type":"service_account","project_id":"test"}'
        mock_credentials = MagicMock()
        mock_service_account.Credentials.from_service_account_info.return_value = mock_credentials

        credentials = calendar_service._get_google_auth()

        assert credentials == mock_credentials
        mock_service_account.Credentials.from_service_account_info.assert_called_once()

    @patch('app.services.calendar_service.settings')
    def test_get_google_auth_missing_key(self, mock_settings, calendar_service):
        """Test Google authentication with missing key"""
        mock_settings.google_service_account_key = ''

        with pytest.raises(Exception, match='GOOGLE_SERVICE_ACCOUNT_KEY'):
            calendar_service._get_google_auth()

    @patch('app.services.calendar_service.settings')
    def test_get_google_auth_invalid_json(self, mock_settings, calendar_service):
        """Test Google authentication with invalid JSON"""
        mock_settings.google_service_account_key = 'invalid json'

        with pytest.raises(Exception, match='Google Service Account authentication failed'):
            calendar_service._get_google_auth()

    def test_check_todays_reservations_sync_event_matching(self, calendar_service):
        """Test event matching logic in synchronous method"""
        # Mock dependencies
        with patch.object(calendar_service, '_get_calendar_client') as mock_client, \
             patch.object(calendar_service, '_get_meeting_room_calendars') as mock_calendars:

            # Setup mocks
            mock_calendars.return_value = {'A': 'test-calendar@group.calendar.google.com'}

            mock_events = MagicMock()
            mock_events.list.return_value.execute.return_value = {
                'items': [
                    {
                        'id': 'event1',
                        'summary': '山田太郎様との会議',
                        'description': '',
                        'start': {'dateTime': '2024-01-01T10:00:00Z'},
                        'end': {'dateTime': '2024-01-01T11:00:00Z'},
                        'attendees': [
                            {
                                'email': 'yamada@test.com',
                                'displayName': '山田太郎',
                                'responseStatus': 'accepted'
                            }
                        ]
                    },
                    {
                        'id': 'event2',
                        'summary': '別の会議',
                        'description': '山田太郎さん参加予定',
                        'start': {'dateTime': '2024-01-01T14:00:00Z'},
                        'end': {'dateTime': '2024-01-01T15:00:00Z'},
                    },
                    {
                        'id': 'event3',
                        'summary': '関係ない会議',
                        'description': '',
                        'start': {'dateTime': '2024-01-01T16:00:00Z'},
                        'end': {'dateTime': '2024-01-01T17:00:00Z'},
                    }
                ]
            }

            mock_client.return_value.events.return_value = mock_events

            # Test matching by attendee
            result = calendar_service._check_todays_reservations_sync('山田太郎')
            assert result['found'] is True
            assert len(result['events']) == 2  # Should find both events

            # Test matching by description
            result = calendar_service._check_todays_reservations_sync('山田太郎')
            assert result['found'] is True

            # Test no match
            result = calendar_service._check_todays_reservations_sync('存在しない人')
            assert result['found'] is False

    def test_event_time_parsing(self, calendar_service):
        """Test event time parsing for different formats"""
        with patch.object(calendar_service, '_get_calendar_client') as mock_client, \
             patch.object(calendar_service, '_get_meeting_room_calendars') as mock_calendars:

            mock_calendars.return_value = {'A': 'test-calendar@group.calendar.google.com'}

            # Test with dateTime
            mock_events = MagicMock()
            mock_events.list.return_value.execute.return_value = {
                'items': [
                    {
                        'id': 'event1',
                        'summary': '山田太郎様との会議',
                        'start': {'dateTime': '2024-01-01T10:30:00Z'},
                        'end': {'dateTime': '2024-01-01T11:00:00Z'},
                    }
                ]
            }
            mock_client.return_value.events.return_value = mock_events

            result = calendar_service._check_todays_reservations_sync('山田太郎')
            assert '10:30' in result['message']

            # Test with date (all-day event)
            mock_events.list.return_value.execute.return_value = {
                'items': [
                    {
                        'id': 'event1',
                        'summary': '山田太郎様との会議',
                        'start': {'date': '2024-01-01'},
                        'end': {'date': '2024-01-01'},
                    }
                ]
            }

            result = calendar_service._check_todays_reservations_sync('山田太郎')
            assert '終日' in result['message']

    def test_case_insensitive_matching(self, calendar_service):
        """Test that name matching is case insensitive"""
        with patch.object(calendar_service, '_get_calendar_client') as mock_client, \
             patch.object(calendar_service, '_get_meeting_room_calendars') as mock_calendars:

            mock_calendars.return_value = {'A': 'test-calendar@group.calendar.google.com'}

            mock_events = MagicMock()
            mock_events.list.return_value.execute.return_value = {
                'items': [
                    {
                        'id': 'event1',
                        'summary': 'YAMADA TARO様との会議',
                        'start': {'dateTime': '2024-01-01T10:00:00Z'},
                        'end': {'dateTime': '2024-01-01T11:00:00Z'},
                    }
                ]
            }
            mock_client.return_value.events.return_value = mock_events

            # Search with lowercase should find uppercase event
            result = calendar_service._check_todays_reservations_sync('yamada taro')
            assert result['found'] is True

    @patch('app.services.calendar_service.CalendarService._get_calendar_client')
    @patch('app.services.calendar_service.CalendarService._get_meeting_room_calendars')
    @pytest.mark.asyncio
    async def test_multiple_calendar_search(
        self,
        mock_get_calendars,
        mock_get_client,
        calendar_service
    ):
        """Test searching across multiple calendars"""
        mock_get_calendars.return_value = {
            'A': 'calendar-a@group.calendar.google.com',
            'B': 'calendar-b@group.calendar.google.com'
        }

        # Mock client that returns different results for different calendars
        def mock_events_list(**kwargs):
            mock_result = MagicMock()
            if 'calendar-a' in kwargs['calendarId']:
                mock_result.execute.return_value = {'items': []}
            else:  # calendar-b
                mock_result.execute.return_value = {
                    'items': [
                        {
                            'id': 'event1',
                            'summary': '山田太郎様との会議',
                            'start': {'dateTime': '2024-01-01T10:00:00Z'},
                            'end': {'dateTime': '2024-01-01T11:00:00Z'},
                        }
                    ]
                }
            return mock_result

        mock_client = MagicMock()
        mock_client.events.return_value.list.side_effect = mock_events_list
        mock_get_client.return_value = mock_client

        result = await calendar_service.check_todays_reservations('山田太郎')

        assert result['found'] is True
        assert result['roomName'] == '会議室B'  # Should find in second calendar
