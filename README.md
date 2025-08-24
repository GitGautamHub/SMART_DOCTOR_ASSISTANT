# Niyukti: A New Approach to Appointments

## Project Overview

This project develops a full-stack smart doctor appointment and reporting assistant, demonstrating agentic AI behavior by leveraging Large Language Models (LLMs) to dynamically interact with various APIs and backend services. The system aims to streamline patient scheduling and provide doctors with quick access to vital reports through natural language interactions.

---

![Login/Registration Screen](images/smart-doctor-assistant.png)
_User authentication portal._

![Patient - Doctor Availability Check](images/doctor-app-1-patient.png)
_A patient querying for a doctor's availability._

![Patient - Appointment Booking Confirmation](images/doctor-app-patient-2.png)
_Successful appointment booking via natural language._

![Email Confirmation Received](images/email.png)
_Automated email sent to the patient for booking confirmation._

![Google Calendar Event Created](images/google-calendar.png)
_The appointment automatically scheduled on the doctor's Google Calendar._

![Doctor - Daily Report Access](images/doctor-app-1-doctor.png)
_A doctor successfully requesting and receiving a summary report._


## Project Folder Structure
```bash
SMART_DOCTOR_ASSISTANT/
├── .git/                      (Hidden Git folder)
├── .gitignore                 (Single, comprehensive gitignore file)
├── README.md                  (Your main project documentation)
├── images/                    (NEW: Folder for your screenshots/demo images)
│   ├── doctor-app-1-doctor.png
│   ├── doctor-app-patient.png
│   └── ... (and so on)
│
├── backend/
│   ├── .env                   (Environment variables - NOT committed to Git)
│   ├── __pycache__/           (Python bytecode cache - ignored by Git)
│   ├── venv/                  (Python virtual environment - ignored by Git)
│   ├── auth.py                (Authentication utilities)
│   ├── calendar_service.py    (Google Calendar integration)
│   ├── create_db_tables.py    (Script to create database tables)
│   ├── database.py            (SQLAlchemy database setup)
│   ├── email_service.py       (Email sending utility)
│   ├── main.py                (FastAPI application entry point, API routes)
│   ├── models.py              (SQLAlchemy database models)
│   ├── requirements.txt       (Python dependencies)
│   ├── schemas.py             (Pydantic data schemas)
│   └── tools.py               (LLM agent tools/functions)
│
└── frontend/
    └── smart-doctor-ui/
        ├── node_modules/      (Node.js packages - ignored by Git)
        ├── public/
        │   ├── index.html     (Main HTML file - modified)
        │   └── robots.txt
        ├── src/
        │   ├── App.css        (Main CSS styling)
        │   ├── App.js         (Main React application component)
        │   ├── index.css      (Basic index CSS)
        │   └── index.js       (React app entry point - modified)
        ├── package.json       (Frontend dependencies)
        └── package-lock.json  (npm lock file)
```

## Features

### Core Functionalities
-   **Patient Appointment Scheduling:** Patients can easily check doctor availability and book appointments using natural language queries.
-   **Doctor Summary Reports:** Doctors can retrieve various types of reports (e.g., daily appointments, total patients) by simply asking in natural language.
-   **Natural Language Understanding (NLU):** Powered by OpenAI's GPT-4o, the assistant interprets complex user intents and maintains context across multi-turn conversations.
-   **AI Agentic Behavior:** The LLM acts as an intelligent agent, dynamically selecting and invoking the appropriate backend tools (APIs) based on the user's request.
-   **Database Management:** Securely stores all doctor, patient, user, appointment, and conversation history data in a PostgreSQL database.
-   **Email Confirmations:** Automated email confirmations are sent to patients upon successful appointment bookings using Gmail (via Yagmail).
-   **Google Calendar Integration:** Appointments are scheduled directly onto doctors' Google Calendars, ensuring real-time availability management and preventing double bookings.

### Bonus Features Implemented
-   **Simple Role-Based Login (Patient vs. Doctor):** Users can register and log in with distinct roles. Frontend UI adapts based on the logged-in user's role (e.g., "Generate Daily Report" button visible only for doctors). User authentication is handled securely using JWTs.
-   **Prompt History Tracking:** All user and AI messages are persisted in the PostgreSQL database, allowing users to view their past conversation history upon logging back in.

---

## Technologies Used

### Backend (Python - FastAPI)
-   **Python 3.10**: The primary programming language.
-   **FastAPI**: A modern, fast (high-performance) web framework for building APIs.
-   **SQLAlchemy**: Python SQL Toolkit and Object Relational Mapper (ORM) for efficient database interaction.
-   **PostgreSQL**: A powerful, open-source relational database used for data storage. (Managed via Docker for easy setup).
-   **LangChain**: A framework designed to build applications with Large Language Models, enabling agentic workflows and tool integration.
-   **OpenAI API (GPT-4o)**: Provides the core LLM capabilities for natural language understanding and tool-calling.
-   **Google Calendar API**: Integrated for managing doctors' schedules and creating appointment events.
-   **Yagmail**: A robust library for sending emails, used for appointment confirmations via Gmail.
-   **`passlib[bcrypt]` & `python-jose[cryptography]`**: For secure password hashing and JSON Web Token (JWT) based authentication.
-   **`python-dotenv`**: Manages environment variables securely.
-   **`uvicorn`**: An ASGI server to run the FastAPI application.
-   **`psycopg2-binary`**: PostgreSQL adapter for Python.

### Frontend (React JS)
-   **React JS**: A popular JavaScript library for building interactive user interfaces.
-   **HTML/CSS**: For structuring and styling the web application.
-   **`fetch` API**: Used for asynchronous communication with the FastAPI backend.
-   **`npm` (Node Package Manager)**: Used for managing frontend dependencies.

---

## Setup and Installation Guide

Follow these steps to get the project running on your local machine.

### Prerequisites

* **Python 3.10**: [Download and Install Python 3.10 (LTS)](https://www.python.org/downloads/windows/). Ensure it's added to PATH or remember its installation location.
* **Node.js & npm**: [Download and Install Node.js (LTS)](https://nodejs.org/). npm is included with Node.js.
* **Docker Desktop**: [Download and Install Docker Desktop](https://www.docker.com/products/docker-desktop/). Essential for running PostgreSQL.
* **Git**: [Install Git](https://git-scm.com/downloads).

### 1. Clone the Repository

Open your terminal or command prompt and clone the project:
```bash
git clone YOUR_GITHUB_REPO_URL_HERE
cd SMART_DOCTOR_ASSISTANT
```

**(Important: Replace YOUR\_GITHUB\_REPO\_URL\_HERE with the actual URL of your private GitHub repository.)**

### 2\. Backend Setup (Python)

a. **Navigate to the Backend Directory:**

```bash

cd backend
```
b. **Create and Activate a Python Virtual Environment:**

(Ensure you use your Python 3.10 executable. Adjust the path if necessary.)
```bash
-m venv venv
.\venv\Scripts\activate # On Windows
# source venv/bin/activate # On macOS/Linux
```

c. **Install Python Dependencies:**

Install all required Python packages. A requirements.txt file is provided.
```bash
pip install -r requirements.txt
```

d. **Set Up PostgreSQL Database using Docker:**

Ensure Docker Desktop is running before executing this command. This will start a PostgreSQL container.
```bash
docker run --name smart_doctor_pg -e POSTGRES_USER=doctor_user -e POSTGRES_PASSWORD=secure_password -e POSTGRES_DB=smart_doctor_db -p 5432:5432 -d postgres
```

Verify the container is running: docker ps

e. **Configure Environment Variables (.env file):**

Create a file named .env in the backend/ directory. Replace all placeholder values with your actual keys and credentials.
```bash
# backend/.env
DATABASE_URL=postgresql://doctor_user:secure_password@localhost:5432/smart_doctor_db
OPENAI_API_KEY=sk-YOUR_OPENAI_API_KEY_HERE
EMAIL_USERNAME=your_gmail_address@gmail.com # The Gmail address you will send emails from
EMAIL_APP_PASSWORD=your_16_character_gmail_app_password # Generate from Google Account Security (requires 2FA)
SECRET_KEY=your-random-long-secret-key-for-jwt-DONT-SHARE # Generate a strong, random string (e.g., using 'secrets.token_hex(32)' in Python)
```
**OpenAI API Key:** Obtain from platform.openai.com/account/api-keys.

**Gmail App Password:** If your Gmail account has 2-Step Verification enabled, you'll need to generate an App password. Otherwise, use your regular password (though App Password is more secure).

f. **Create Database Tables:**

From your backend/ directory (with venv activated):

```bash

python create_db_tables.py
```

g. **Start the FastAPI Backend Server:**

From your backend/ directory (with venv activated):

```bash
uvicorn main:app --reload
```
The backend will run on http://127.0.0.1:8000. Keep this terminal open.


### 3. Frontend Setup (React JS)
a. **Navigate to the Frontend Application Directory:**

```bash
cd ../frontend/smart-doctor-ui # If you are in backend/
```

b. **Install Frontend Dependencies:**

The dependencies are listed in package.json.

```bash
npm install
```

c. **Start the React Development Server:**

```bash
npm start
```
The frontend will run on http://localhost:3000. Keep this terminal open.

How to Use the Application (Testing Flow)
-----------------------------------------

Access the frontend in your browser: http://localhost:3000

### 1\. Register Users and Create Doctor/Patient Profiles

Use the Swagger UI for initial data setup: http://127.0.0.1:8000/docs

a. **Register Users (POST /register/):**

*   Register at least one **patient** user (e.g., email: rina.devi@example.com, password: patientpass123, role: patient). Note the id from the response.
    
*   Register at least one **doctor** user (e.g., email: dr.amit.kumar@example.com, password: docpass123, role: doctor). Note the id from the response.
    

b. **Create Doctor Profiles (POST /doctors/):**

*   For each doctor user registered, create a corresponding Doctor profile.(e.g., name: "Dr. Amit Kumar", specialty: "Cardiologist", email: "dr.amit.kumar@example.com"). **Ensure the email matches the registered doctor user's email.**
    

c. **Create Patient Profiles (POST /patients/):**

*   For each patient user registered, create a corresponding Patient profile, **linking their user\_id**.(e.g., name: "Rina Devi", email: "rina.devi@example.com", phone\_number: "9876543210", user\_id: \[ID from patient registration\]).
    

_(You can use the provided realistic Indian names from our previous conversation to populate your database.)_

### 2\. Log In and Interact via the Frontend

Access the application in your browser: http://localhost:3000

#### a. Patient Interactions (Login as a Patient)

1.  **Login:** Use a registered patient's email and password (e.g., rina.devi@example.com, patientpass123).
    
2.  **Check Doctor Availability:**
    
    *   Type a prompt like: "Is Dr. Amit Kumar available tomorrow?"
        
    *   **Expected:** The AI should respond with available time slots.
        
3.  **Book an Appointment:**
    
    *   Type a prompt like: "Book me an appointment with Dr. Amit Kumar for tomorrow at 10:00 AM. My name is Rina Devi and my email is rina.devi@example.com."
        
    *   **Expected:** The AI confirms the booking.
        
    *   **Verify:**
        
        *   Check rina.devi@example.com's (your own Gmail if you used it) inbox for the confirmation email.
            
        *   Check dr.amit.kumar@example.com's (your authenticated Google Calendar) calendar for the new appointment event.
            
4.  **Attempt Doctor Report (Access Denied):**
    
    *   Type a prompt like: "Get Dr. Amit Kumar's daily report for today."
        
    *   **Expected (IMPORTANT):** The AI should respond with: "Sorry, something went wrong: An error occurred: Access denied. Only users with 'doctor' role can request reports." (This message originates from the backend tool's logic.)
        

#### b. Doctor Interactions (Logout, then Login as a Doctor)

1.  **Logout:** Click the "Logout" button in the frontend.
    
2.  **Login:** Use a registered doctor's email and password (e.g., dr.amit.kumar@example.com, docpass123).
    
3.  **Get Doctor Report:**
    
    *   The "Generate Daily Report" button should now be visible. You can click it, or type a prompt like: "Get my daily report for today."
        
    *   **Expected:** The AI should respond with a summary report based on appointments.
        
    *   **Verify:** Check your **backend terminal** where FastAPI is running for the detailed report printout.
        
