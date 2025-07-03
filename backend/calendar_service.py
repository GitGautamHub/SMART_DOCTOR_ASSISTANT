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

    # --- MODIFIED: Check for credentials.json before proceeding ---
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error(f"{CREDENTIALS_FILE} not found. Google Calendar service cannot be initialized in this environment.")
        # Optionally, you could try to read client_id/secret from environment variables here
        # or just return None and disable functionality.
        return None # Fail gracefully if file is missing

    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try: # Wrap this part in try-except in case file is malformed
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0) # This will not work on a headless server like Render
            except Exception as e:
                logger.error(f"Error during Google Calendar authentication flow: {e}. Cannot obtain new credentials.")
                return None # Cannot authenticate, so return None

        # On Render, writing to token.json is ephemeral or requires special setup
        # For this assignment, we will skip saving token.json on Render.
        # Just use the 'creds' object directly for the 'build' step.
        # with open(TOKEN_FILE, 'w') as token:
        #     token.write(creds.to_json())

    try:
        calendar_service = build('calendar', 'v3', credentials=creds)
        logger.info("Google Calendar service initialized successfully.")
        return calendar_service
    except HttpError as error:
        logger.error(f"An error occurred during Google Calendar service initialization: {error}")
        return None
    except Exception as e: # Catch other potential errors during build
        logger.error(f"Unexpected error during Google Calendar service build: {e}")
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
    # Remove or comment out this block when deploying to Render
    # as it attempts local server authentication which will fail.
    pass # Keep this for local testing only