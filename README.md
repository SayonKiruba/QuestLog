# 🎮 QuestLog

![QuestLog Overview](https://img.shields.io/badge/Status-Prototype-orange.svg) 
![Python](https://img.shields.io/badge/Backend-Python_|_Flask-blue.svg) 
![JavaScript](https://img.shields.io/badge/Frontend-Vanilla_JS_|_HTML_|_CSS-yellow.svg)
![IGDB API](https://img.shields.io/badge/API-IGDB-purple.svg)

**QuestLog** is a video game tracking and discovery web application. It allows users to browse trending games, manage their personal game libraries, and keep custom notes, ratings, and statuses for their favorite titles. 

**Developed by:** Shajjan, Sayon, Faraz, Haseeb, and Abdoul.

---

## ✨ Features

- **Discover New Games:** Browse trending community picks and popular IGDB titles right from the home page (`/`) without needing an account.
- **Personal Game Library:** Sign up/log in to access your personal dashboard (`/library` or `/dashboard`).
- **Real-Time Game Search:** Powered by the IGDB API, search for real-world games and pull cover images directly into the app.
- **Custom Notes & Tracking:** Add games to your personal shelf and document:
  - Game Status (e.g., Playing, Completed, Dropped)
  - Player Rating
  - Additional Comments & Reviews
- **Library Management:** Edit your notes or remove games from your profile at any time.
- **Profile Customization:** Personalize your presence by setting a custom display name, uploading an avatar, and writing a bio.

---

## 🛠️ Tech Stack

- **Core Backend:** Python (Flask)
- **Frontend:** Vanilla JavaScript, HTML5, CSS3
- **Database:** Local SQLite database
- **External API:** [IGDB API](https://www.igdb.com/api) for fetching game data and cover images.

---

## 🚀 Getting Started

Follow these instructions to get a copy of the project up and running on your local machine.

### Prerequisites
- [Python 3.x](https://www.python.org/downloads/) installed on your machine.
- IDE/Text Editor (e.g., VS Code).

### Installation & Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/SayonKiruba/QuestLog.git
   ```

2. **Navigate to the project directory:**
   Ensure your folder structure matches the repository exactly.
   ```bash
   cd QuestLog
   ```

3. **Install dependencies (if applicable):**
   *(Note: Ensure you have Flask and the required packages installed.)*
   ```bash
   pip install flask requests
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

5. **Access the application:**
   - The app listens on **port 5050** by default (to avoid clashing with other standard Flask apps running on port 5000).
   - Open your web browser and navigate to: **[http://127.0.0.1:5050/](http://127.0.0.1:5050/)**
   - *Note: If you need to run it on port 5000, set your environment variable: `QUESTLOG_PORT=5000`.*

> **Troubleshooting Tip:** The console will print **Serving from: …** so you can confirm which folder is running. If the UI looks like an old theme, you might be hitting a different server. Stop other Python servers or use the exact URL/port shown in your terminal. There are also known edge cases regarding the local database initialization upon cloning; if issues arise, resetting the database may be required.

---

## 🗺️ Roadmap / Future Implementations

The team is actively working on enhancing QuestLog. Planned features include:

- [ ] **Game Descriptions:** Adding detailed game summaries and lore when viewing game details.
- [ ] **Admin Roles:** Implementing an admin dashboard with exclusive moderation perks.

---
