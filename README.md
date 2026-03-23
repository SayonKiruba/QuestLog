# QuestLog Prototype


## Running the Program

* Download the program by cloning the repo and adding into the folder of your choice (or creating a new one).
* After cloning the repo to an IDE of your choice, ensure the folder structure matches what was on the repository.
* Open a new terminal in your IDE, `cd` into the `QuestLog` folder, and run: `python app.py`
* The app listens on **port 5050** by default (avoids clashing with another Flask app on 5000). Open **http://127.0.0.1:5050/** — or set `QUESTLOG_PORT=5000` if you need port 5000.
* The console prints **Serving from: …** so you can confirm which folder is running. If the UI looks like an old theme, you were probably hitting a different server; stop other `python` servers or use the URL/port shown in the terminal.
* **Discover** (`/`) is public: browse trending community picks and popular IGDB titles without signing in. **Library** (`/library` or `/dashboard`) is for logged-in users only.
* Sign in or sign up from the top bar when you want to add games to your shelf.

## Added
+ Entire stack changed to:
    + Core Logic: Python
    + Fundamental Logic: JavaScript
    + Styling: CSS
    + Web: HTML
+ Enchanced UI
+ Implemented real database from IGDB which extracts games and displays them here using API calls.
+ Added cover images when searching for games and viewing games on "My Profile".
+ Added profile customization (setting display name, custom avatar, bio).
+ Added ability to add games to profile and set custom notes (status of game, player rating, additional comments).
+ Added ability for user to click on their profiles games and see their set notes.
+ Users can also edit their notes.
+ Users can also remove games from their profile.


## Removed (These features may be implemented in the near future)
- Removed previous tech stack.
- Removed admin checkbox upon signup and all admin exclusive perks (everyone defaults to "User").
- Removed ability to search profiles.
- Local database has been altered slightly*.

## Still Need to Add
- Searching profiles and viewing other users profiles.
- Admin option and features.
- Enhancing more aspects of the UI.
- Logo needs to be completed (best form of logo will appear on login/signup page).
- Viewing game details is avaiable but description of the game is not. Intention to add this has been expressed.


## Additional Notes
* Local database has not been removed but has been altered. Initialization of database included. Issues may arise when cloned from repo. May need fixing.