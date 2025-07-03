from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List, Dict

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str
    role: Optional[str] = "patient"

class DoctorRegister(UserCreate):
    name: str = Field(..., description="Full name of the doctor.")
    specialty: str = Field(..., description="Specialty of the doctor (e.g., Cardiologist, Pediatrician).")
    role: str = "doctor"

class UserInDB(UserBase):
    hashed_password: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class User(UserBase):
    id: int
    role: str
    is_active: bool

    class Config:
        from_attributes = True

# --- Authentication Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[int] = None

# --- Doctor Schemas ---
class DoctorBase(BaseModel):
    name: str
    specialty: str
    email: EmailStr

class DoctorCreate(DoctorBase):
    pass

class Doctor(DoctorBase):
    id: int
    
    class Config:
        from_attributes = True

# --- Patient Schemas ---
class PatientBase(BaseModel):
    name: str
    email: EmailStr
    phone_number: Optional[str] = None

class PatientCreate(PatientBase):
    user_id: Optional[int] = None

class Patient(PatientBase):
    id: int
    user_id: Optional[int] = None
    user: Optional[User] = None

    class Config:
        from_attributes = True

# --- Appointment Schemas ---
class AppointmentBase(BaseModel):
    doctor_id: int
    patient_id: int
    appointment_date: datetime
    time_slot: str
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class Appointment(AppointmentBase):
    id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    google_calendar_event_id: Optional[str] = None

    doctor: Optional[Doctor] = None
    patient: Optional[Patient] = None

    class Config:
        from_attributes = True

# --- Tool Input Schemas (for LLM Function Calling) ---
class CheckDoctorAvailabilityInput(BaseModel):
    doctor_name: str = Field(..., description="The full name of the doctor (e.g., 'Dr. Ahuja').")
    date: str = Field(..., description="The date to check availability in YYYY-MM-DD format (e.g., '2025-07-02').")

class BookAppointmentInput(BaseModel):
    doctor_name: str = Field(..., description="The full name of the doctor.")
    patient_name: str = Field(..., description="The full name of the patient.")
    patient_email: EmailStr = Field(..., description="The email address of the patient for confirmation.")
    date: str = Field(..., description="The date of the appointment in YYYY-MM-DD format.")
    time_slot: str = Field(..., description="The specific time slot for the appointment in HH:MM format (e.g., '09:30').")
    notes: str = Field(None, description="Any additional notes for the appointment.")

class GetDoctorSummaryReportInput(BaseModel):
    doctor_name: str = Field(..., description="The full name of the doctor.")
    report_type: str = Field("daily", description="The type of report requested (e.g., 'daily', 'monthly', 'total_patients').")
    date: Optional[str] = Field(None, description="Specific date for daily report (YYYY-MM-DD).")
    start_date: Optional[str] = Field(None, description="Start date for range reports (YYYY-MM-DD).")
    end_date: Optional[str] = Field(None, description="End date for range reports (YYYY-MM-DD).")
    user_info: Optional[Dict] = Field(None, description="Current user's information, including 'id', 'email', and 'role'. This field is automatically populated by the system.")

# --- Chat & Conversation History Schemas ---
class ChatRequest(BaseModel):
    user_message: str
    chat_history: List[Dict] = []

class ChatResponse(BaseModel):
    ai_response: str
    updated_chat_history: List[Dict]

class ConversationHistoryBase(BaseModel):
    user_id: int
    role: str
    content: str

class ConversationHistoryCreate(ConversationHistoryBase):
    pass

class ConversationHistory(ConversationHistoryBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True