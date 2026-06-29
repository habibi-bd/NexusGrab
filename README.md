# NexusGrab

A lightweight, zero-config media downloader built with FastAPI, WebSockets, and `yt-dlp`. It streams video and audio assets directly to your browser without leaving permanent files on your server.

## Features

* **Paste & Click UI:** No complex settings or quality dropdowns.
* **Auto-Stream Detection:** Automatically converts audio links (like SoundCloud) into MP3s and video links into high-res MP4s.
* **Live UI Previews:** Displays active progress bars, speeds, and ETAs via WebSockets, then embeds a native player when finished.
* **Clipboard & Analytics:** Includes a one-click paste button and a clean dashboard tracking domain stats.

## Project Structure

```text
NexusGrab/
├── app/
│   ├── main.py               # FastAPI server & WebSocket handlers
│   ├── database.py & models.py # SQLite analytics tracking
│   ├── services/downloader.py # Core yt-dlp processing logic
│   └── templates/index.html   # Tailwind CSS frontend
├── requirements.txt
└── .gitignore



# Clone and enter the project
git clone [https://github.com/habibi-bd/NexusGrab.git](https://github.com/habibi-bd/NexusGrab.git)
cd NexusGrab

# Set up virtual environment
python -m venv ng
.\ng\Scripts\activate  # Windows
source ng/bin/activate # Linux/macOS

# Install dependencies and run
pip install -r requirements.txt
uvicorn app.main:app --reload
