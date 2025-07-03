# backend/create_db_tables.py
from database import Base, engine
from models import Doctor, Patient, Appointment # Import your models to ensure they are registered with Base

print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")