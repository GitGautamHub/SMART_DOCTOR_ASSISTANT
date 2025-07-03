from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base # Corrected to use relative import

class User(Base):
    """SQLAlchemy model for storing user authentication details."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="patient", nullable=False) # 'patient' or 'doctor'
    is_active = Column(Boolean, default=True)

    patients = relationship("Patient", back_populates="user", uselist=False)

class Patient(Base):
    """SQLAlchemy model for patient profiles, linked to a user account."""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)
    name = Column(String, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone_number = Column(String, nullable=True)

    user = relationship("User", back_populates="patients")
    appointments = relationship("Appointment", back_populates="patient")

class Doctor(Base):
    """SQLAlchemy model for doctor profiles."""
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    specialty = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)

    appointments = relationship("Appointment", back_populates="doctor")

class Appointment(Base):
    """SQLAlchemy model for appointment details."""
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    appointment_date = Column(DateTime, nullable=False)
    time_slot = Column(String, nullable=False)
    status = Column(String, default="pending", nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    google_calendar_event_id = Column(String, nullable=True)

    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")

class ConversationHistory(Base):
    """SQLAlchemy model for storing user-AI conversation history."""
    __tablename__ = "conversation_history"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String, nullable=False) # 'human' or 'ai'
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    user = relationship("User")