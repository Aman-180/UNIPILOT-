# UniPilot

UniPilot is an AI-powered productivity platform built for students. It combines task management, streak tracking, and analytics with a Gemini-powered AI coach that helps users stay consistent with their goals — all wrapped in a glassmorphism dark-theme UI.

Built as the Group 29 capstone project at IIT Patna.

## Features

- 🤖 **Gemini AI Coach** — personalized guidance and check-ins to keep users on track
- 🔥 **Streak Tracking** — visualize and maintain daily productivity streaks
- 📊 **Analytics Dashboard** — insights into productivity trends over time
- 🎯 **Productivity Score** — a computed score reflecting overall user activity and consistency
- 🎨 **Glassmorphism UI** — a modern, dark-themed interface built with vanilla HTML/CSS/JS

## Tech Stack

- **Backend:** Flask (Python), REST API (20+ endpoints)
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript (vanilla)
- **AI Integration:** Gemini API

## Getting Started

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/unipilot.git
cd unipilot

# Create a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Add your Gemini API key and other config to .env

# Run the app
python app.py
```

The app should now be running at `http://localhost:5000`.

## Environment Variables

Create a `.env` file in the project root with the following:

```
GEMINI_API_KEY=your_api_key_here
SECRET_KEY=your_secret_key_here
DATABASE_URL=sqlite:///unipilot.db
```

## Project Structure

```
unipilot/
├── app.py                 # Flask application entry point
├── models/                 # Database models / schema
├── routes/                 # API route definitions
├── static/                 # CSS, JS, images
├── templates/               # HTML templates
├── requirements.txt
└── .env.example
```

## Contributors

- Backend development, API design, SQLite schema, productivity score logic, and app integration by [Aman Gupta](mailto:amanguptadkmg@gmail.com)

## License

This project was built for academic purposes as part of a capstone at IIT Patna.
