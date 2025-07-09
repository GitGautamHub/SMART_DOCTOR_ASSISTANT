// frontend/smart-doctor-ui/src/App.js
import React, { useState, useEffect, useRef } from 'react';
import './App.css';

function App() {
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Authentication states
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userRole, setUserRole] = useState(null);
  const [userEmail, setUserEmail] = useState('');
  const [token, setToken] = useState(null);

  // Auth form states
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [isRegistering, setIsRegistering] = useState(false);
  const [authError, setAuthError] = useState('');
  const [selectedRole, setSelectedRole] = useState('patient'); // Default to 'patient'

  // NEW: Doctor registration specific fields
  const [doctorName, setDoctorName] = useState('');
  const [doctorSpecialty, setDoctorSpecialty] = useState('');

  // NEW: Instruction box state
  const [showInstructions, setShowInstructions] = useState(true);

  const BACKEND_BASE_URL = 'https://smart-doctor-backend-api-gautam.onrender.com'; // change for local deployment as 'http://127.0.0.1:8000' 'https://smart-doctor-backend-api-gautam.onrender.com'
  const CHAT_URL = `${BACKEND_BASE_URL}/chat/`; 
  const HISTORY_URL = `${BACKEND_BASE_URL}/history/`;

  // Pre-registered Doctor for instructions
  const PRE_REGISTERED_DOCTOR = {
    name: "Dr. Gautam Kumar",
    email: "gautamk8760@gmail.com",
    specialty: "AI Specialist" // Assuming this is your specialty for the demo doctor
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Initial load: check for stored token, fetch user info and history
  useEffect(() => {
    const storedToken = localStorage.getItem('accessToken');
    if (storedToken) {
      setToken(storedToken);
      setIsLoggedIn(true);
      fetchUserInfoAndHistory(storedToken);
    } else {
      setMessages([{ role: 'ai', content: "Please log in or register to use the Smart Doctor Assistant." }]);
    }
  }, []);

  const fetchUserInfoAndHistory = async (current_token) => {
    try {
      const userResponse = await fetch(`${BACKEND_BASE_URL}/users/me/`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${current_token}` },
      });
      if (!userResponse.ok) throw new Error('Failed to fetch user info');
      const userData = await userResponse.json();
      setUserRole(userData.role);
      setUserEmail(userData.email);

      const historyResponse = await fetch(HISTORY_URL, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${current_token}` },
      });
      if (!historyResponse.ok) throw new Error('Failed to fetch conversation history');
      const historyData = await historyResponse.json();

      const formattedHistory = historyData.map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      if (formattedHistory.length === 0) {
        setMessages([{ role: 'ai', content: "Welcome back! How can I help you today?" }]);
      } else {
        setMessages(formattedHistory);
      }

    } catch (error) {
      console.error('Error fetching user info or history:', error);
      handleLogout();
    }
  };

  const handleLoginRegister = async () => {
    setAuthError('');
    setIsLoading(true);
    const url = isRegistering ? `${BACKEND_BASE_URL}/register/` : `${BACKEND_BASE_URL}/token/`;
    const method = 'POST';

    let body;
    let headers;

    if (isRegistering) {
      if (selectedRole === 'doctor') {
        body = JSON.stringify({
          email: authEmail,
          password: authPassword,
          role: selectedRole,
          name: doctorName, // NEW
          specialty: doctorSpecialty // NEW
        });
      } else { // Patient registration
        body = JSON.stringify({ email: authEmail, password: authPassword, role: selectedRole });
      }
      headers = { 'Content-Type': 'application/json' };
    } else { // Login
      body = new URLSearchParams({ username: authEmail, password: authPassword });
      headers = { 'Content-Type': 'application/x-www-form-urlencoded' };
    }

    try {
      const response = await fetch(url, { method, headers, body });
      const data = await response.json();

      if (!response.ok) {
        setAuthError(data.detail || 'Authentication failed');
        return;
      }

      if (isRegistering) {
        alert('Registration successful! Please log in.');
        setIsRegistering(false); // Switch to login form
        // Reset all auth form fields
        setAuthEmail('');
        setAuthPassword('');
        setSelectedRole('patient');
        setDoctorName('');
        setDoctorSpecialty('');
      } else { // Login successful
        const accessToken = data.access_token;
        localStorage.setItem('accessToken', accessToken);
        setToken(accessToken);
        setIsLoggedIn(true);
        setAuthError('');
        setAuthEmail('');
        setAuthPassword('');
        setSelectedRole('patient'); // Reset role for safety
        fetchUserInfoAndHistory(accessToken);
      }
    } catch (error) {
      console.error('Auth error:', error);
      setAuthError('Network error or server unavailable');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    setToken(null);
    setIsLoggedIn(false);
    setUserRole(null);
    setUserEmail('');
    setMessages([{ role: 'ai', content: "You have been logged out. Please log in or register." }]);
  };

  const sendMessage = async () => {
    if (inputMessage.trim() === '' || isLoading || !isLoggedIn) return;

    const newMessage = { role: 'human', content: inputMessage };
    setMessages((prevMessages) => [...prevMessages, newMessage]);
    setInputMessage('');

    setIsLoading(true);

    try {
      const chatHistoryForBackend = messages
        .filter(msg => msg.role === 'human' || msg.role === 'ai')
        .map(msg => ({ role: msg.role, content: msg.content }));

      const response = await fetch(CHAT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_message: newMessage.content,
          chat_history: chatHistoryForBackend
        }),
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          handleLogout();
          throw new Error('Session expired or unauthorized. Please log in again.');
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      setMessages(data.updated_chat_history);

    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prevMessages) => [
        ...prevMessages,
        { role: 'ai', content: `Sorry, something went wrong: ${error.message}. Please try again.` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const requestDoctorReport = async () => {
    if (isLoading || !isLoggedIn || userRole !== 'doctor') return;

    const reportMessage = "Get my daily report for today.";
    const newMessage = { role: 'human', content: reportMessage };
    setMessages((prevMessages) => [...prevMessages, newMessage]);

    setIsLoading(true);

    try {
      const chatHistoryForBackend = messages
        .filter(msg => msg.role === 'human' || msg.role === 'ai')
        .map(msg => ({ role: msg.role, content: msg.content }));

      const response = await fetch(CHAT_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          user_message: reportMessage,
          chat_history: chatHistoryForBackend
        }),
      });

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          handleLogout();
          throw new Error('Session expired or unauthorized. Please log in again.');
        }
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      setMessages(data.updated_chat_history);
      
    } catch (error) {
      console.error('Error requesting doctor report:', error);
      setMessages((prevMessages) => [
        ...prevMessages,
        { role: 'ai', content: `Sorry, something went wrong with the report: ${error.message}.` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>🩺 Smart Doctor Assistant</h1>
        {isLoggedIn && (
          <div className="user-info-bar">
            <span>Logged in as: {userEmail} ({userRole})</span>
            <button onClick={handleLogout}>Logout</button>
          </div>
        )}
      </header>

      {!isLoggedIn ? (
        <div className="auth-form-container">
          <h2>{isRegistering ? 'Register' : 'Login'}</h2>
          <input
            type="email"
            placeholder="Email"
            value={authEmail}
            onChange={(e) => setAuthEmail(e.target.value)}
            disabled={isLoading}
          />
          <input
            type="password"
            placeholder="Password"
            value={authPassword}
            onChange={(e) => setAuthPassword(e.target.value)}
            disabled={isLoading}
          />

          {isRegistering && (
            <>
              <select
                value={selectedRole}
                onChange={(e) => {
                  setSelectedRole(e.target.value);
                  if (e.target.value === 'patient') {
                    setDoctorName('');
                    setDoctorSpecialty('');
                  }
                }}
                disabled={isLoading}
                className="role-select"
              >
                <option value="patient">Patient</option>
                <option value="doctor">Doctor</option>
              </select>
              {selectedRole === 'doctor' && (
                <>
                  <input
                    type="text"
                    placeholder="Doctor's Full Name"
                    value={doctorName}
                    onChange={(e) => setDoctorName(e.target.value)}
                    disabled={isLoading}
                  />
                  <input
                    type="text"
                    placeholder="Specialty (e.g., Cardiologist)"
                    value={doctorSpecialty}
                    onChange={(e) => setDoctorSpecialty(e.target.value)}
                    disabled={isLoading}
                  />
                </>
              )}
            </>
          )}

          {authError && <p className="error-message">{authError}</p>}
          <button onClick={handleLoginRegister} disabled={isLoading}>
            {isLoading ? (isRegistering ? 'Registering...' : 'Logging In...') : (isRegistering ? 'Register' : 'Login')}
          </button>
          <p onClick={() => {
            setIsRegistering(!isRegistering);
            setAuthError('');
            setAuthEmail('');
            setAuthPassword('');
            setSelectedRole('patient'); // Reset role when toggling
            setDoctorName(''); // Clear doctor specific fields
            setDoctorSpecialty(''); // Clear doctor specific fields
          }} className="toggle-auth-mode">
            {isRegistering ? 'Already have an account? Login' : "Don't have an account? Register"}
          </p>
        </div>
      ) : (
        // Chat interface
        <div className="chat-container">
          {showInstructions && (
            <div className="instructions-box">
              <button className="close-instructions" onClick={() => setShowInstructions(false)}>✖</button>
              <h3>How to Use This Prototype</h3>
              <p>
                This is a demo of a Smart Doctor Assistant. Follow these steps to explore its features:
              </p>
              <ol>
                <li>
                  <strong>Register a Doctor:</strong> You can register any new doctor with their full name and specialty.
                  <br />
                  <strong>Pre-registered Doctors for Demo:</strong>
                  <ul>
                    <li>
                      Dr. Gautam Kumar (General Medicine) - <code>gautamk8760@gmail.com</code>
                    </li>
                    <li>
                      Dr. Gulshan (Dentist) - <code>terceletbag@gmail.com</code>
                    </li>
                    <li>
                      Dr. Anjali (Dentist) - <code>anjali089ak@gmail.com</code>
                    </li>
                  </ul>
                  Password for all doctors: <code>docpass123</code>
                  <br />
                  <strong>Only Dr. Gautam and Dr. Gulshan have Google Calendar linked</strong>. Appointments can only be booked with them unless other doctors link their Google Calendar.
                </li>
                <li>
                  <strong>Login as Patient:</strong> Register as a "Patient" or login with an existing patient account.
                  <br />
                  Example:
                  <ul>
                    <li>Rahul Verma - <code>rahul.verma93@gmail.com</code></li>
                    <li>Riya Kapoor - <code>riya.kapoor12@gmail.com</code></li>
                  </ul>
                  Password for all patients: <code>patientpass123</code>
                </li>
                <li>
                  <strong>Book an Appointment (as Patient):</strong>
                  <br />
                  Type:
                  <br />
                  <code>
                    Book me an appointment with Dr. Gautam Kumar tomorrow at 10:00 AM. My name is [Your Name] and my email is [your_email@example.com].
                  </code>
                  <br />
                  (Replace `[Your Name]` and `[your_email@example.com]` with your actual details.)
                </li>
                <li>
                  <strong>Check Email & Calendar:</strong> You'll receive confirmation in your email and the event will appear in the doctor’s Google Calendar (only for linked accounts).
                </li>
                <li>
                  <strong>Login as Doctor:</strong> Logout and then login as doctor (e.g., <code>gautamk8760@gmail.com</code>) to manage appointments.
                </li>
                <li>
                  <strong>Get Daily Report:</strong>
                  <br />
                  Type: <code>Get my daily report for today</code> OR click the "Generate Daily Report" button.
                </li>
              </ol>
              <p>
                <strong>Note:</strong> To allow a doctor to receive calendar bookings, their Google Calendar must be integrated via the Google Auth link during setup.
              </p>
            </div>
          )}


          <div className="messages-display">
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`}>
                <p dangerouslySetInnerHTML={{ __html: msg.content.replace(/\\n/g, '<br/>') }}></p>
              </div>
            ))}
            {isLoading && (
              <div className="message ai">
                <p>Thinking...</p>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <div className="input-area">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              rows="3"
              disabled={isLoading}
            />
            <button onClick={sendMessage} disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
          {userRole === 'doctor' && (
            <div className="doctor-actions">
              <button onClick={requestDoctorReport} disabled={isLoading}>
                {isLoading ? 'Generating Report...' : 'Generate Daily Report'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default App;