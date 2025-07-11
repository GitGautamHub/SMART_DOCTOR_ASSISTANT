# Standard library imports
import asyncio
import os
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager

# Third-party library imports
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr # BaseModel used for local ChatRequest/Response if not imported from schemas
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from typing import List, Dict, Union, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain.tools import StructuredTool

# Local application imports
import models, schemas
from auth import (
    get_password_hash, verify_password, create_access_token,
    get_current_active_user, require_role
)
from database import engine, get_db
from tools import (
    check_doctor_availability_tool,
    book_appointment_tool,
    get_doctor_summary_report_tool,
    list_all_doctors_tool
)
from schemas import ( # Import all necessary Pydantic schemas
    CheckDoctorAvailabilityInput,
    BookAppointmentInput,
    DoctorRegister,
    GetDoctorSummaryReportInput,
    ChatRequest,
    ChatResponse,
    User, UserCreate, Token, TokenData,
    Doctor, DoctorCreate, Patient, PatientCreate, Appointment,
    ConversationHistory # Ensure ConversationHistory is imported
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

ACCESS_TOKEN_EXPIRE_MINUTES = 30


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    Database table creation is performed here on startup.
    """
    logger.info("Application startup: Attempting to create database tables...")
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/checked successfully on startup.")
    except Exception as e:
        logger.error(f"Error creating database tables on startup: {e}")

    # Yield control to the application to start serving requests
    yield

    # This part runs on shutdown (optional for this assignment, but good to know)
    logger.info("Application shutdown: Performing cleanup (if any)...")


app = FastAPI(lifespan=lifespan) 

# Configure CORS middleware
origins = [
    "http://localhost",
    "http://localhost:3000", # Your React local frontend URL
    "https://smart-doctor-assistant.vercel.app", # deploy url
    "https://smart-doctor-backend-api-gautam.onrender.com"
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    """Returns a welcome message for the API root."""
    return {"message": "Welcome to the Smart Doctor Assistant API!"}

# --- User Authentication Endpoints ---

@app.post("/register/", response_model=schemas.User)
def register_user(
    user_data: Union[schemas.UserCreate, schemas.DoctorRegister], # Allow either schema
    db: Session = Depends(get_db)
):
    """Registers a new user (patient or doctor) and creates/links a profile."""
    # Check if email is already registered
    db_user = db.query(models.User).filter(models.User.email == user_data.email).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Hash password and create User entry
    hashed_password = get_password_hash(user_data.password)
    db_user = models.User(email=user_data.email, hashed_password=hashed_password, role=user_data.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    if user_data.role == "patient":
        db_patient = db.query(models.Patient).filter(models.Patient.email == user_data.email).first()
        if not db_patient:
            db_patient = models.Patient(name=user_data.email.split('@')[0], email=user_data.email, user_id=db_user.id)
            db.add(db_patient)
            db.commit()
            db.refresh(db_patient)
        else:
            db_patient.user_id = db_user.id
            db.commit()
            db.refresh(db_patient) 

    elif user_data.role == "doctor":
        if not isinstance(user_data, schemas.DoctorRegister):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Doctor registration requires name and specialty.")

        db_doctor = models.Doctor(user_id=db_user.id,name=user_data.name, specialty=user_data.specialty, email=user_data.email)
        db.add(db_doctor)
        db.commit()
        db.refresh(db_doctor)

    return db_user

@app.post("/token/", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Handles user login and issues a JWT access token."""
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """Retrieves details of the currently authenticated user."""
    return current_user

# --- LLM Agent Setup ---
llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=os.getenv("OPENAI_API_KEY"))

check_availability_tool = StructuredTool.from_function(
    func=check_doctor_availability_tool,
    name="check_doctor_availability",
    description="Useful for finding out available time slots for a doctor on a specific date. Input must include doctor's name and date in YYYY-MM-DD.",
    args_schema=CheckDoctorAvailabilityInput,
    handle_tool_error=True,
    coroutine=check_doctor_availability_tool
)

book_appointment_langchain_tool = StructuredTool.from_function(
    func=book_appointment_tool,
    name="book_appointment",
    description="Useful for booking a new appointment for a patient with a doctor. Input must include doctor's name, patient's name, patient's email, date in YYYY-MM-DD, and time slot in HH:MM. Ensure the time slot is available before booking.",
    args_schema=BookAppointmentInput,
    handle_tool_error=True,
    coroutine=book_appointment_tool
)
list_doctors_tool = StructuredTool.from_function(
    func=list_all_doctors_tool,
    name="list_all_doctors",
    description="Useful for providing a list of all doctors available in the system, along with their specialties. Use this when the user asks to see available doctors or to list all doctors.",
    # This tool takes no specific arguments, so args_schema can be simple/empty
    # args_schema=BaseModel, # Or just omit if the function takes no arguments and description is clear
    handle_tool_error=True,
    coroutine=list_all_doctors_tool
)

get_summary_report_tool = StructuredTool.from_function(
    func=get_doctor_summary_report_tool,
    name="get_doctor_summary_report",
    description="Useful for retrieving various summary reports for a doctor, such as daily appointments or total patients visited. Input must include doctor's name and report type. Optional date/date range can be provided for specific reports. Requires 'doctor' role.",
    args_schema=GetDoctorSummaryReportInput,
    handle_tool_error=True,
    coroutine=get_doctor_summary_report_tool
)

tools = [
    check_availability_tool,
    book_appointment_langchain_tool,
    get_summary_report_tool,
    list_doctors_tool
]
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", f"""You are a helpful AI assistant for managing doctor appointments and generating reports.
        You have access to the following specialized tools to assist users:
        - `list_all_doctors`: Use this to show the user a list of all doctors and their specialties in the system. (Accessible by all users)
        - `check_doctor_availability`: Use this to find out available time slots for any doctor. (Accessible by all users)
        - `book_appointment`: Use this to schedule a new appointment. (Accessible by all users)
        - `get_doctor_summary_report`: Use this to retrieve statistical reports about a doctor's appointments. **Important: This tool is strictly for users with the 'doctor' role only.**

        **Current User's Role: {{current_user_role}}**

        Here are your strict instructions for interacting with users:
        1. Always be polite, professional, and empathetic.
        2. If the user asks "Who are the doctors?", "List all doctors", or similar queries to see available doctors, you MUST use the `list_all_doctors` tool and present the list clearly. After presenting the list, ask the user to choose a doctor for an appointment.
        3. When a user asks to book an appointment, you MUST first use the `check_doctor_availability` tool for the requested date and time.
        4. For booking an appointment, always ask for the patient's full name and their email address for confirmation.
        5. **Regarding reports: If a user asks for a doctor summary report, you MUST first check the 'role' in the `user_info` variable. If `user_info['role']` is NOT 'doctor', you must immediately inform the user that they do not have permission to view reports and DO NOT proceed with calling the `get_doctor_summary_report` tool. For any other role (e.g., 'doctor'), you should proceed with calling the tool.**
        6. Provide clear confirmations for successful actions (like booking).
        7. If any tool returns an error (e.g., doctor not found, slot unavailable, access denied from backend), explain the error clearly to the user and suggest appropriate next steps or alternatives.
        Today's date is {datetime.now().strftime("%Y-%m-%d")}."""
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ]
)

agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- FastAPI Endpoint for LLM Chat ---
@app.post("/chat/", response_model=schemas.ChatResponse)
async def chat_with_assistant(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Interacts with the AI assistant. Handles natural language input, tool invocation,
    conversation continuity, and saves chat history. Requires authentication.
    """
    # Save human message to DB
    user_message_entry = models.ConversationHistory(
        user_id=current_user.id,
        role="human",
        content=request.user_message
    )
    db.add(user_message_entry)
    db.commit()
    db.refresh(user_message_entry)

    formatted_chat_history = []
    # Use chat_history from request directly for LLM context
    for msg in request.chat_history:
        if msg["role"] == "human":
            formatted_chat_history.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            formatted_chat_history.append(AIMessage(content=msg["content"]))

    try:
        agent_input_data = {
            "input": request.user_message,
            "chat_history": formatted_chat_history,
            "current_user_role": current_user.role,   # <--- NEW: Pass role directly for prompt
            "current_user_email": current_user.email, # <--- NEW: Pass email directly for prompt
            "user_info": {"id": current_user.id, "email": current_user.email, "role": current_user.role} # Still pass for tool argument if needed internally by tools
        }

        result = await agent_executor.ainvoke(agent_input_data)
        ai_response_content = result.get("output", "I could not process that request.")

        # Save AI's response to DB
        ai_message_entry = models.ConversationHistory(
            user_id=current_user.id,
            role="ai",
            content=ai_response_content
        )
        db.add(ai_message_entry)
        db.commit()
        db.refresh(ai_message_entry)

        # Return updated history including new messages
        updated_history = request.chat_history + [
            {"role": "human", "content": request.user_message},
            {"role": "ai", "content": ai_response_content}
        ]

        return schemas.ChatResponse(ai_response=ai_response_content, updated_chat_history=updated_history)

    except Exception as e:
        logger.error(f"Error invoking agent for user {current_user.email}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An internal error occurred.")

@app.get("/history/", response_model=List[schemas.ConversationHistory])
def get_conversation_history(
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 100
):
    """Retrieves the conversation history for the current authenticated user."""
    history_records = db.query(models.ConversationHistory).filter(
        models.ConversationHistory.user_id == current_user.id
    ).order_by(models.ConversationHistory.timestamp).limit(limit).all()

    return history_records

# --- Doctor Endpoints ---
@app.post("/doctors/", response_model=schemas.Doctor)
def create_doctor(doctor: schemas.DoctorCreate, db: Session = Depends(get_db)):
    """Creates a new doctor profile."""
    db_doctor = models.Doctor(name=doctor.name, specialty=doctor.specialty, email=doctor.email)
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

@app.get("/doctors/", response_model=list[schemas.Doctor])
def read_doctors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieves a list of all doctors."""
    doctors = db.query(models.Doctor).offset(skip).limit(limit).all()
    return doctors

@app.get("/doctors/{doctor_id}", response_model=schemas.Doctor)
def read_doctor(doctor_id: int, db: Session = Depends(get_db)):
    """Retrieves details for a specific doctor by ID."""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

# --- Patient Endpoints ---
@app.post("/patients/", response_model=schemas.Patient)
def create_patient(patient: schemas.PatientCreate, db: Session = Depends(get_db)):
    """Creates a new patient profile."""
    db_patient = models.Patient(name=patient.name, email=patient.email, phone_number=patient.phone_number)
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

@app.get("/patients/", response_model=list[schemas.Patient])
def read_patients(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieves a list of all patients."""
    patients = db.query(models.Patient).offset(skip).limit(limit).all()
    return patients

# --- Appointment Endpoints (Direct API Access - usually for internal tools or debugging) ---
@app.get("/doctors/{doctor_id}/availability_direct/")
def check_doctor_availability_direct(
    doctor_id: int,
    date: str,
    db: Session = Depends(get_db)
):
    """Checks and returns direct availability for a doctor (without LLM involvement)."""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    try:
        requested_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    booked_appointments = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_date == requested_date
    ).all()
    booked_time_slots = {app.time_slot for app in booked_appointments}

    available_slots = []
    for hour in range(9, 17):
        for minute in [0, 30]:
            time_str = f"{hour:02d}:{minute:02d}"
            if time_str not in booked_time_slots:
                available_slots.append(time_str)

    return {"doctor_name": doctor.name, "date": date, "available_slots": available_slots}

@app.post("/appointments_direct/", response_model=schemas.Appointment)
def book_appointment_direct(appointment: schemas.AppointmentCreate, db: Session = Depends(get_db)):
    """Directly books an appointment (without LLM or external API integrations)."""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == appointment.doctor_id).first()
    patient = db.query(models.Patient).filter(models.Patient.id == appointment.patient_id).first()

    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing_appointment = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == appointment.doctor_id,
        models.Appointment.appointment_date == appointment.appointment_date,
        models.Appointment.time_slot == appointment.time_slot
    ).first()

    if existing_appointment:
        raise HTTPException(status_code=409, detail="Time slot already booked for this doctor.")

    db_appointment = models.Appointment(
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        appointment_date=appointment.appointment_date,
        time_slot=appointment.time_slot,
        status="pending"
    )
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)

    return db_appointment

@app.get("/doctors/{doctor_id}/summary_report_direct/")
def get_doctor_summary_report_direct(doctor_id: int, db: Session = Depends(get_db)):
    """Directly retrieves a summary report for a doctor (without LLM involvement)."""
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    today = datetime.now().date()
    yesterday = today - timedelta(days=1)

    total_patients_visited = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.status == "completed"
    ).count()

    appointments_today = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_date == today,
        models.Appointment.status.in_(["pending", "confirmed"])
    ).count()

    appointments_yesterday = db.query(models.Appointment).filter(
        models.Appointment.doctor_id == doctor_id,
        models.Appointment.appointment_date == yesterday,
        models.Appointment.status.in_(["completed", "pending", "confirmed"])
    ).count()

    summary = {
        "doctor_name": doctor.name,
        "total_patients_visited": total_patients_visited,
        "appointments_today": appointments_today,
        "appointments_yesterday": appointments_yesterday,
        "report_generated_at": datetime.now().isoformat()
    }
    return summary