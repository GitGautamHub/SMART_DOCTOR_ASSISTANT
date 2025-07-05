# Standard library imports
from datetime import datetime, timedelta, time
import logging
from typing import Dict,List, Optional # Only import types directly used in this file's function signatures

# Third-party library imports
from fastapi import Depends, HTTPException # Keep if these are used in tool functions (HttpException is used)
from sqlalchemy.orm import Session
from googleapiclient.errors import HttpError
from pydantic import EmailStr # Keep EmailStr as it's used in book_appointment_tool signature

# Local application imports (Corrected relative imports)
import models
import schemas
from database import get_db
from calendar_service import get_calendar_service, create_calendar_event, get_free_busy_slots
from email_service import send_confirmation_email

# Setup logging
logger = logging.getLogger(__name__)

# Initialize Google Calendar service once on startup
gcal_service = get_calendar_service()
if not gcal_service:
    logger.warning("Google Calendar service could not be initialized. Calendar features will be limited.")


# --- Helper Functions ---
def _get_db_session():
    """Provides a SQLAlchemy database session."""
    db_session = get_db()
    try:
        db = next(db_session)
        yield db
    finally:
        if 'db' in locals() and db:
            db.close()

def _get_doctor_by_name(db: Session, doctor_name: str):
    """Retrieves a doctor by name from the database."""
    return db.query(models.Doctor).filter(models.Doctor.name.ilike(doctor_name)).first()

def _get_patient_by_name_or_create(db: Session, patient_name: str, patient_email: str):
    """Retrieves a patient by email or creates a new one if not found."""
    patient = db.query(models.Patient).filter(models.Patient.email == patient_email).first()
    if not patient:
        patient = models.Patient(name=patient_name, email=patient_email)
        db.add(patient)
        db.commit()
        db.refresh(patient)
    return patient

def _get_all_doctors(db: Session) -> List[Dict]:
    """Fetches all doctors from the database."""
    doctors = db.query(models.Doctor).all()
    return [{"name": doc.name, "specialty": doc.specialty, "email": doc.email} for doc in doctors]


# --- Tool Functions (for LLM Agent) ---

async def check_doctor_availability_tool(
    doctor_name: str,
    date: str,
    user_info: Dict = None
) -> Dict:
    """
    Checks available time slots for a doctor on a given date, considering DB and Google Calendar busy times.
    """
    db_gen = _get_db_session()
    db = next(db_gen)

    try:
        doctor = _get_doctor_by_name(db, doctor_name)
        if not doctor:
            return {"error": f"Doctor '{doctor_name}' not found."}

        doctor_calendar_id = doctor.email
        if not doctor_calendar_id:
            return {"error": f"Doctor '{doctor_name}' does not have an email/calendar ID configured."}

        try:
            requested_date = datetime.strptime(date, "%Y-%m-%d").date()
            start_of_day = datetime.combine(requested_date, time(9, 0, 0))
            end_of_day = datetime.combine(requested_date, time(17, 0, 0))
        except ValueError:
            return {"error": "Invalid date format. Please use `YYYY-MM-DD`."}

        all_possible_slots = []
        for hour in range(9, 17):
            for minute in [0, 30]:
                all_possible_slots.append(f"{hour:02d}:{minute:02d}")

        gcal_busy_slots = []
        if gcal_service:
            try:
                busy_periods = get_free_busy_slots(gcal_service, doctor_calendar_id, start_of_day, end_of_day)
                for busy in busy_periods:
                    # Ensure timezone awareness for comparison
                    busy_start = datetime.fromisoformat(busy['start']).astimezone(datetime.timezone.utc).astimezone(start_of_day.tzinfo)
                    busy_end = datetime.fromisoformat(busy['end']).astimezone(datetime.timezone.utc).astimezone(end_of_day.tzinfo)
                    
                    current_time = busy_start
                    while current_time < busy_end:
                        gcal_busy_slots.append(current_time.strftime("%H:%M"))
                        current_time += timedelta(minutes=30)
            except HttpError as error:
                logger.error(f"Error getting free/busy slots from Google Calendar: {error}")
                # Continue without calendar data if API fails, but inform user
                return {"error": f"Could not retrieve Google Calendar availability: {error}. Please try again later."}

        booked_appointments_db = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == doctor.id,
            models.Appointment.appointment_date == requested_date
        ).all()
        db_booked_time_slots = {app.time_slot for app in booked_appointments_db}

        all_occupied_slots = set(gcal_busy_slots) | db_booked_time_slots
        available_slots = [slot for slot in all_possible_slots if slot not in all_occupied_slots]
        available_slots.sort()

        return {"doctor_name": doctor.name, "date": date, "available_slots": available_slots}
    finally:
        db.close()

async def book_appointment_tool(
    doctor_name: str,
    patient_name: str,
    patient_email: EmailStr,
    date: str,
    time_slot: str,
    notes: Optional[str] = None,
    user_info: Dict = None
) -> Dict:
    """
    Books an appointment, creates a Google Calendar event, and sends email confirmation.
    """
    db_gen = _get_db_session()
    db = next(db_gen)

    try:
        doctor = _get_doctor_by_name(db, doctor_name)
        if not doctor:
            return {"error": f"Doctor '{doctor_name}' not found."}
        
        doctor_calendar_id = doctor.email
        if not doctor_calendar_id:
            return {"error": f"Doctor '{doctor_name}' does not have an email/calendar ID configured for Google Calendar."}

        patient = _get_patient_by_name_or_create(db, patient_name, patient_email)

        try:
            appointment_date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            start_hour, start_minute = map(int, time_slot.split(':'))
            start_event_datetime = datetime.combine(appointment_date_obj, time(start_hour, start_minute, 0))
            end_event_datetime = start_event_datetime + timedelta(minutes=30)
        except ValueError:
            return {"error": "Invalid date or time slot format. Use `YYYY-MM-DD` and `HH:MM`."}
        
        # Check for existing appointment in DB before creating calendar event
        existing_appointment_db = db.query(models.Appointment).filter(
            models.Appointment.doctor_id == doctor.id,
            models.Appointment.appointment_date == appointment_date_obj,
            models.Appointment.time_slot == time_slot
        ).first()
        if existing_appointment_db:
            return {"error": f"Time slot '{time_slot}' on {date} already booked for {doctor.name} in our records."}

        # Check Google Calendar busy status one last time for robustness
        if gcal_service:
            try:
                busy_periods = get_free_busy_slots(gcal_service, doctor_calendar_id, start_event_datetime, end_event_datetime)
                if busy_periods:
                    return {"error": f"Doctor '{doctor.name}' is unexpectedly busy at {time_slot} on {date} according to Google Calendar. Please choose another slot."}
            except HttpError as error:
                logger.error(f"Error confirming Google Calendar availability: {error}")
                return {"error": f"Could not confirm Google Calendar availability: {error}. Please try again later."}
        
        # Create Google Calendar Event
        gcal_event_id = None
        if gcal_service:
            event_summary = f"Appointment: Dr. {doctor.name} & {patient.name}"
            event_description = f"Patient: {patient.name}\nEmail: {patient.email}\nNotes: {notes if notes else 'N/A'}"
            
            attendees = [{'email': doctor_calendar_id}]
            if patient.email:
                attendees.append({'email': patient.email})

            gcal_event_id = create_calendar_event(
                gcal_service,
                calendar_id=doctor_calendar_id,
                summary=event_summary,
                description=event_description,
                start_datetime=start_event_datetime,
                end_datetime=end_event_datetime,
                attendees=attendees
            )
            if not gcal_event_id:
                return {"error": "Failed to create Google Calendar event. Appointment not booked."}
        else:
            logger.warning("Google Calendar service not available. Proceeding without calendar event.")

        # Store the appointment in database
        db_appointment = models.Appointment(
            doctor_id=doctor.id,
            patient_id=patient.id,
            appointment_date=appointment_date_obj,
            time_slot=time_slot,
            status="confirmed",
            notes=notes,
            google_calendar_event_id=gcal_event_id
        )
        db.add(db_appointment)
        db.commit()
        db.refresh(db_appointment)
        
        # Send confirmation email
        email_subject = f"Appointment Confirmation: Dr. {doctor.name} - {date} {time_slot}"
        email_body = f"""
Dear {patient.name},

Your appointment with Dr. {doctor.name} on {date} at {time_slot} has been successfully confirmed.

We look forward to seeing you.

Best regards,
Smart Doctor Assistant
"""
        send_confirmation_email(patient.email, email_subject, email_body)

        return {
            "success": True,
            "message": f"Appointment confirmed for {patient.name} with {doctor.name} on {date} at {time_slot}. A confirmation email has been sent to {patient.email}.",
            "appointment_id": db_appointment.id,
            "google_calendar_event_id": gcal_event_id,
            "confirmation_email_to": patient.email
        }
    except HttpError as error: # Catch HttpError from Google Calendar API specifically
        logger.error(f"Google Calendar API error during booking: {error}")
        db.rollback() # Rollback DB changes if calendar creation failed (important!)
        return {"error": f"An external API error occurred during booking: {error}. Please try again."}
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred during booking: {e}")
        db.rollback() # Rollback in case of other errors
        return {"error": f"An unexpected error occurred during booking: {e}. Please try again."}
    finally:
        db.close()

# NEW TOOL: List all Doctors
async def list_all_doctors_tool(user_info: Dict = None) -> Dict: # user_info is optional for consistency
    """
    Lists all available doctors in the system with their names and specialties.
    Useful when a user wants to see who they can book an appointment with.
    """
    db_gen = _get_db_session()
    db = next(db_gen)

    try:
        doctors_data = _get_all_doctors(db)
        if not doctors_data:
            return {"message": "No doctors found in the system at the moment."}

        return {"doctors": doctors_data}
    finally:
        db.close()
    
async def get_doctor_summary_report_tool(
    doctor_name: str,
    report_type: str = "daily",
    date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_info: Dict = None # Debugging for RBAC
) -> Dict:
    """
    Generates a summary report for a specific doctor. Requires 'doctor' role.
    """
    # Debug print: Verify user_info received by the tool
    logger.info(f"Inside get_doctor_summary_report_tool. Received user_info: {user_info}")

    # if not user_info or user_info.get('role') != 'doctor':
    #     logger.warning(f"Access DENIED for report. User info: {user_info}. Role received: {user_info.get('role') if user_info else 'N/A'}")
    #     return {"error": "Access denied. Only users with 'doctor' role can request reports."}

    # logger.info(f"Access GRANTED for report. Role is: {user_info.get('role')}")
    
    db_gen = _get_db_session()
    db = next(db_gen)

    try:
        doctor = _get_doctor_by_name(db, doctor_name)
        if not doctor:
            return {"error": f"Doctor '{doctor_name}' not found."}

        summary_data = {"doctor_name": doctor.name, "report_type": report_type}

        if report_type == "daily":
            report_date_str = date if date else datetime.now().strftime("%Y-%m-%d")
            try:
                report_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
            except ValueError:
                return {"error": "Invalid date format for daily report. Use `YYYY-MM-DD`."}

            appointments_on_date = db.query(models.Appointment).filter(
                models.Appointment.doctor_id == doctor.id,
                models.Appointment.appointment_date == report_date
            ).all()

            summary_data["date"] = report_date_str
            summary_data["appointments_count"] = len(appointments_on_date)
            summary_data["appointments_details"] = [
                {"patient_name": app.patient.name, "time_slot": app.time_slot, "status": app.status}
                for app in appointments_on_date if app.patient # Ensure patient data is loaded
            ]
            summary_data["message"] = f"On {report_date_str}, {doctor.name} has {len(appointments_on_date)} appointments."

        elif report_type == "total_patients":
            total_patients_visited = db.query(models.Appointment).filter(
                models.Appointment.doctor_id == doctor.id,
                models.models.Appointment.status == "completed"
            ).count()
            summary_data["total_patients_visited"] = total_patients_visited
            summary_data["message"] = f"{doctor.name} has had {total_patients_visited} patients completed appointments."

        else:
            summary_data["message"] = "Report type not recognized or implemented yet."
        
        # Doctor Notification (Console print as placeholder for external system)
        if summary_data and "message" in summary_data:
            logger.info(f"\n--- DOCTOR NOTIFICATION ---")
            logger.info(f"Report for Dr. {summary_data.get('doctor_name')}: {summary_data.get('message')}")
            if "appointments_details" in summary_data:
                for app in summary_data["appointments_details"]:
                    logger.info(f"  - {app['time_slot']} with {app['patient_name']} ({app['status']})")
            logger.info(f"---------------------------\n")

        return summary_data
    finally:
        db.close()