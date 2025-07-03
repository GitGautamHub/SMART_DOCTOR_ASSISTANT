import os.path
import datetime
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
TOKEN_FILE = 'token.json'
CREDENTIALS_FILE = 'credentials.json'

calendar_service = None

def get_calendar_service():
    """Initializes and returns the Google Calendar API service, handling authentication."""
    global calendar_service
    if calendar_service:
        return calendar_service

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    try:
        calendar_service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar service initialized successfully.")
        return calendar_service
    except HttpError as error:
        logger.error(f"An error occurred during Google Calendar service initialization: {error}")
        return None

def create_calendar_event(
    service,
    calendar_id: str,
    summary: str,
    description: str,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    attendees: list = None
):
    """Creates an event on the specified Google Calendar."""
    if not service:
        logger.warning("Google Calendar service not available to create event.")
        return None

    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_datetime.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_datetime.isoformat(),
            'timeZone': 'Asia/Kolkata',
        },
        'attendees': attendees if attendees else [],
        'reminders': {
            'useDefault': False,
            'overrides': [
                {'method': 'email', 'minutes': 24 * 60},
                {'method': 'popup', 'minutes': 10},
            ],
        },
        'conferenceData': {'createRequest': {'requestId': 'random-string'}},
    }

    try:
        event = service.events().insert(
            calendarId=calendar_id,
            body=event,
            sendNotifications=True,
            conferenceDataVersion=1
        ).execute()
        logger.info(f"Event created: {event.get('htmlLink')}")
        return event.get('id')
    except HttpError as error:
        logger.error(f"An error occurred creating Google Calendar event: {error}")
        return None

def get_free_busy_slots(service, calendar_id: str, start_time: datetime.datetime, end_time: datetime.datetime):
    """Gets free/busy information for a calendar within a time range."""
    if not service:
        logger.warning("Google Calendar service not available to check free/busy slots.")
        return []

    body = {
        "timeMin": start_time.isoformat() + 'Z',
        "timeMax": end_time.isoformat() + 'Z',
        "timeZone": 'Asia/Kolkata',
        "items": [{"id": calendar_id}]
    }

    try:
        response = service.freebusy().query(body=body).execute()
        calendars_data = response.get('calendars', {})
        if calendar_id in calendars_data:
            return calendars_data[calendar_id].get('busy', [])
        return []
    except HttpError as error:
        logger.error(f"An error occurred checking Google Calendar free/busy: {error}")
        return []

if __name__ == '__main__':
    service = get_calendar_service()
    if service:
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        start_event_time = datetime.datetime.combine(tomorrow, datetime.time(11, 0, 0))
        end_event_time = start_event_time + datetime.timedelta(minutes=30)

        # IMPORTANT: Replace with a real Google Calendar email you have authenticated
        doctor_calendar_id = "your.doctor.email@example.com" 
        