import asyncio
import json
from datetime import datetime, time

# Import types from examples/calendar_sample.py
from typing import TypedDict

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config import settings


class Attendee(TypedDict, total=False):
    email: str
    displayName: str | None
    responseStatus: str | None
    organizer: bool | None


class Person(TypedDict, total=False):
    email: str
    displayName: str | None


class EventTime(TypedDict, total=False):
    dateTime: str | None
    date: str | None


class CalendarEvent(TypedDict):
    id: str
    summary: str
    description: str | None
    start: EventTime
    end: EventTime
    attendees: list[Attendee] | None
    location: str | None
    creator: Person | None
    organizer: Person | None


class ReservationCheckResult(TypedDict):
    found: bool
    events: list[CalendarEvent] | None
    identifier: str
    message: str
    error: bool | None
    roomName: str | None


class CalendarService:
    """Google Calendar integration service"""

    def __init__(self):
        self._credentials = None
        self._service = None

        # Check if we should use real API or mock
        if (settings.google_service_account_key and
            settings.google_service_account_key.strip() and
            settings.meeting_room_calendar_ids):
            self.use_mock = False
            print("✅ CalendarService initialized with Google Calendar API")
        else:
            self.use_mock = True
            print("⚠️ CalendarService initialized with mock mode (missing Google credentials)")

    def _get_google_auth(self):
        """Initialize Google authentication"""
        if self._credentials:
            return self._credentials

        try:
            # Get service account key from environment
            key_string = settings.google_service_account_key
            if not key_string:
                raise ValueError('GOOGLE_SERVICE_ACCOUNT_KEY environment variable not set')

            # Parse JSON credentials
            credentials_info = json.loads(key_string)

            # Create service account credentials
            self._credentials = service_account.Credentials.from_service_account_info(
                credentials_info,
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )

            return self._credentials
        except Exception as e:
            raise Exception(f'Google Service Account authentication failed: {str(e)}')

    def _get_calendar_client(self):
        """Get calendar client"""
        if self._service:
            return self._service

        credentials = self._get_google_auth()
        self._service = build('calendar', 'v3', credentials=credentials)
        return self._service

    def _get_meeting_room_calendars(self) -> dict[str, str]:
        """Get meeting room calendar IDs"""
        calendar_ids = settings.meeting_room_calendar_ids

        if not calendar_ids:
            raise ValueError('MEETING_ROOM_CALENDAR_IDS environment variable not set')

        # Map comma-separated calendar IDs to room names
        calendars = {}
        for index, calendar_id in enumerate(calendar_ids.split(',')):
            room_name = chr(65 + index)  # A, B, C...
            calendars[room_name] = calendar_id.strip()

        return calendars

    async def check_todays_reservations(self, visitor_identifier: str) -> ReservationCheckResult:
        """Check today's reservations for a visitor"""

        # Use mock response if credentials not available
        if self.use_mock:
            return await self._mock_check_reservations(visitor_identifier)

        try:
            print(f"🔍 Checking calendar for: {visitor_identifier}")

            # Run the synchronous Google API calls in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._check_todays_reservations_sync,
                visitor_identifier
            )

            print(f"✅ Calendar check completed. Found: {result['found']}")
            return result

        except Exception as error:
            print(f'❌ Calendar API async error: {error}')

            return {
                'found': False,
                'events': None,
                'identifier': visitor_identifier,
                'message': 'システムエラーが発生しました。スタッフをお呼びします。',
                'error': True,
                'roomName': None
            }

    def _check_todays_reservations_sync(self, visitor_identifier: str) -> ReservationCheckResult:
        """Synchronous version of reservation checking"""
        try:
            calendar = self._get_calendar_client()
            room_calendars = self._get_meeting_room_calendars()

            # Set today's time range
            now = datetime.now()
            time_min = datetime.combine(now.date(), time.min)
            time_max = datetime.combine(now.date(), time.max)

            # Search all meeting room calendars
            all_events: list[CalendarEvent] = []

            for room_name, calendar_id in room_calendars.items():
                try:
                    # Get calendar events
                    events_result = calendar.events().list(
                        calendarId=calendar_id,
                        timeMin=time_min.isoformat() + 'Z',
                        timeMax=time_max.isoformat() + 'Z',
                        singleEvents=True,
                        orderBy='startTime'
                    ).execute()

                    events = events_result.get('items', [])

                    # Convert events to CalendarEvent format
                    for event in events:
                        calendar_event: CalendarEvent = {
                            'id': event.get('id', ''),
                            'summary': event.get('summary', ''),
                            'description': event.get('description'),
                            'start': {
                                'dateTime': event.get('start', {}).get('dateTime'),
                                'date': event.get('start', {}).get('date')
                            },
                            'end': {
                                'dateTime': event.get('end', {}).get('dateTime'),
                                'date': event.get('end', {}).get('date')
                            },
                            'attendees': None,
                            'location': f'会議室{room_name}',
                            'creator': None,
                            'organizer': None
                        }

                        # Add attendee information
                        if 'attendees' in event:
                            calendar_event['attendees'] = [
                                {
                                    'email': attendee.get('email', ''),
                                    'displayName': attendee.get('displayName'),
                                    'responseStatus': attendee.get('responseStatus'),
                                    'organizer': attendee.get('organizer', False)
                                }
                                for attendee in event['attendees']
                            ]

                        # Add creator information
                        if 'creator' in event:
                            calendar_event['creator'] = {
                                'email': event['creator'].get('email', ''),
                                'displayName': event['creator'].get('displayName')
                            }

                        # Add organizer information
                        if 'organizer' in event:
                            calendar_event['organizer'] = {
                                'email': event['organizer'].get('email', ''),
                                'displayName': event['organizer'].get('displayName')
                            }

                        all_events.append(calendar_event)

                except HttpError as error:
                    print(f'Calendar {room_name} search error: {error}')
                    # Continue with other calendars
                    continue

            # Filter events by visitor name with stricter matching
            identifier_lower = visitor_identifier.lower()
            matching_events = []

            for event in all_events:
                # Check if visitor name is in title or description with stricter matching
                summary = (event.get('summary', '') or '').lower()
                description = (event.get('description', '') or '').lower()

                # More strict matching - require word boundaries or exact matches
                import re
                # Create pattern that matches the identifier as a whole word or part of compound words
                identifier_pattern = re.escape(identifier_lower)
                title_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', summary))
                description_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', description))

                # Check if visitor name is in attendees with stricter matching
                attendee_match = False
                if event.get('attendees'):
                    for attendee in event['attendees']:
                        display_name = (attendee.get('displayName', '') or '').lower()
                        email = (attendee.get('email', '') or '').lower()

                        # Strict matching for attendee names and emails
                        name_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', display_name))
                        email_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', email))

                        if name_match or email_match:
                            attendee_match = True
                            break

                # Check if visitor name is in creator or organizer with stricter matching
                organizer_match = False

                if event.get('creator'):
                    creator_email = (event['creator'].get('email', '') or '').lower()
                    creator_name = (event['creator'].get('displayName', '') or '').lower()

                    creator_email_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', creator_email))
                    creator_name_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', creator_name))

                    if creator_email_match or creator_name_match:
                        organizer_match = True

                if event.get('organizer'):
                    organizer_email = (event['organizer'].get('email', '') or '').lower()
                    organizer_name = (event['organizer'].get('displayName', '') or '').lower()

                    org_email_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', organizer_email))
                    org_name_match = bool(re.search(rf'\b{identifier_pattern}\b|{identifier_pattern}', organizer_name))

                    if org_email_match or org_name_match:
                        organizer_match = True

                # Match if any condition is met
                if title_match or description_match or attendee_match or organizer_match:
                    matching_events.append(event)

            if matching_events:
                # Reservation found
                event = matching_events[0]  # Use first matching event

                # Get start time
                start_time = '終日'
                if event['start'].get('dateTime'):
                    start_dt = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    start_time = start_dt.strftime('%H:%M')

                return {
                    'found': True,
                    'events': matching_events,
                    'identifier': visitor_identifier,
                    'roomName': event.get('location'),
                    'message': f'{visitor_identifier}様の本日{start_time}からの会議室予約を確認いたしました。奥の呼び鈴を押してお待ちください。',
                    'error': None
                }
            else:
                # No reservation found
                return {
                    'found': False,
                    'events': None,
                    'identifier': visitor_identifier,
                    'message': f'申し訳ございません。{visitor_identifier}様の本日の予約が確認できませんでした。事前予約制となっておりますので、お引き取りをお願いいたします。',
                    'error': None,
                    'roomName': None
                }

        except Exception as error:
            print(f'Calendar API full error: {error}')

            return {
                'found': False,
                'events': None,
                'identifier': visitor_identifier,
                'message': 'システムエラーが発生しました。スタッフをお呼びします。',
                'error': True,
                'roomName': None
            }

    async def _mock_check_reservations(self, visitor_identifier: str) -> ReservationCheckResult:
        """Mock calendar checking for development"""
        import asyncio

        print(f"🧪 Mock calendar check for: {visitor_identifier}")

        # Add realistic delay
        await asyncio.sleep(0.8)

        # Mock some realistic test data
        test_reservations = ["田中", "佐藤", "山田", "test", "yamada", "tanaka"]

        # Check if visitor identifier matches any test reservation
        identifier_lower = visitor_identifier.lower()
        found = any(test_name in identifier_lower for test_name in test_reservations)

        if found:
            return {
                'found': True,
                'events': [{
                    'id': 'mock-event-123',
                    'summary': f'{visitor_identifier}様との会議',
                    'start': {'dateTime': '2025-08-02T10:00:00+09:00'},
                    'end': {'dateTime': '2025-08-02T11:00:00+09:00'},
                    'location': '入って右手の会議室',
                    'attendees': [{'email': 'example@company.com'}]
                }],
                'identifier': visitor_identifier,
                'roomName': '入って右手の会議室',
                'message': f'{visitor_identifier}様の本日10:00からの会議室予約を確認いたしました。奥の呼び鈴を押してお待ちください。',
                'error': None
            }
        else:
            return {
                'found': False,
                'events': None,
                'identifier': visitor_identifier,
                'message': f'申し訳ございません。{visitor_identifier}様の本日の予約が確認できませんでした。事前予約制となっておりますので、お引き取りをお願いいたします。',
                'error': None,
                'roomName': None
            }
