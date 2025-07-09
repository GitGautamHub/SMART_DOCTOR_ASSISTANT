# backend/calendar_service.py
import os.path
import datetime
import logging
import json # NEW: To parse JSON string from environment variable

# google.auth modules for Service Account
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials as ServiceAccountCredentials # MODIFIED IMPORT: Use this for service account auth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar.events']
GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON")

calendar_service = None

def get_calendar_service():
    """Initializes and returns the Google Calendar API service, handling authentication using a Service Account."""
    global calendar_service
    if calendar_service:
        return calendar_service

    # --- MODIFIED LOGIC: Use Service Account credentials from environment variable ---
    creds_info = None

    # Priority 1: Try to load credentials from environment variable (for deployment)
    if GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON:
        try:
            creds_info = json.loads(GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON)
            logger.info("Attempting to initialize Google Calendar service from environment variable.")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON (from env var): {e}. Check JSON format in environment variable.")
            creds_info = None # Reset to None if decoding fails
    
    # Priority 2: If not from env var, try to load credentials from local file (for local development/testing)
    # This block is added for local flexibility; Render will use the env var
    local_service_account_key_file_path = 'service_account_key.json' # Make sure this file is in backend/ and in .gitignore
    if not creds_info:
        if os.path.exists(local_service_account_key_file_path):
            try:
                with open(local_service_account_key_file_path, "r") as f:
                    creds_info = json.load(f)
                logger.info(f"Attempting to initialize Google Calendar service from local file: {local_service_account_key_file_path}.")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                logger.error(f"Error loading local service account key file '{local_service_account_key_file_path}': {e}. Check file path/JSON format.")
                creds_info = None
        else:
            logger.warning(f"Neither GOOGLE_SERVICE_ACCOUNT_CREDENTIALS_JSON env var nor local file '{local_service_account_key_file_path}' found. Google Calendar service cannot be initialized.")
            return None # Fail gracefully if no credentials source found

    # If credentials info is successfully obtained, try to build the service
    if creds_info:
        try:
            # Use the imported ServiceAccountCredentials class
            creds = ServiceAccountCredentials.from_service_account_info(
                creds_info, scopes=SCOPES
            )
            calendar_service = build('calendar', 'v3', credentials=creds)
            logger.info("Google Calendar service initialized successfully using Service Account credentials.")
            return calendar_service
        except Exception as e:
            logger.error(f"An error occurred during Google Calendar service build with Service Account: {e}")
            return None
    else:
        logger.warning("No valid Google Calendar credentials found or loaded. Calendar features will be limited.")
        return None


def create_calendar_event(
    service,
    calendar_id: str,
    summary: str,
    description: str,
    start_datetime: datetime.datetime,
    end_datetime: datetime.datetime,
    attendees: list = None # This parameter will still be accepted by the function
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
        # 'attendees': attendees if attendees else [], # <--- CRITICAL CHANGE: COMMENT OUT OR REMOVE THIS LINE
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
            sendNotifications=False, # <--- MODIFIED: Set to False, since we are not inviting attendees via Google. Your app will send the email.
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
    # This block is for local testing with Service Account, not browser flow
    logger.info("Running calendar_service.py for local Service Account testing...")
    service = get_calendar_service()
    if service:
        logger.info("Service account test: Calendar service acquired.")
        # Example usage for local testing (uncomment to test after setting up service_account_key.json)
        # from datetime import timedelta, time
        # tomorrow = datetime.date.today() + timedelta(days=1)
        # test_doctor_calendar_id = "smart-doctor-svc@smart-doctor-assistant-api.iam.gserviceaccount.com" # Service Account itself
        # This should be the doctor's email, whose calendar is shared with the Service Account
        # test_doctor_calendar_id = "dr.gautamkumar@gmail.com" # Replace with an actual doctor's shared calendar email

        # start_event_time = datetime.datetime.combine(tomorrow, time(10, 0, 0))
        # end_event_time = start_event_time + timedelta(minutes=30)
        # event_id = create_calendar_event(
        #     service,
        #     test_doctor_calendar_id,
        #     "Test Appointment",
        #     "Testing Service Account",
        #     start_event_time,
        #     end_event_time,
        #     attendees=[{'email': test_doctor_calendar_id}]
        # )
        # if event_id:
        #     logger.info(f"Test event created with ID: {event_id}")
        # else:
        #     logger.warning("Failed to create test event locally.")

        # busy_slots = get_free_busy_slots(service, test_doctor_calendar_id, start_event_time, end_event_time)
        # logger.info(f"Test busy slots for {test_doctor_calendar_id}: {busy_slots}")

    else:
        logger.warning("Service account test: Failed to acquire calendar service.")