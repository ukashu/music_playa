## Functionality list
- play music
- pause playback
- skip song
- go to previous song (one back)
- list all songs in working directory (including subdirectories)
- get song cover art
- get current song info
- get current song progress
- change playback volume
- jump to specific position in song playback (or maybe rewind buttons)
- in order, shuffle, repeat playback modes

## Architecture
Main logic is exposed via REST API. User Interface applications call endpoints.

## Proposed folder structure

``` python
music-playa/
│
├── backend/
│   ├── core/
│   │   ├── audio_engine.py #get MPV working
│   │   ├── player.py #playback controls
│   │   ├── library.py 
│   │   └── queue.py
│   │
│   ├── services/
│   │   ├── scanner.py #scan for music in current directory
│   │   ├── metadata.py #get song metadata
│   │   ├── cover_art.py #get song cover art
│   │   └── visualizer.py #extract visualizer data from song
│   │
│   └── api/
│       ├── routes/
│       │   ├── player.py
│       │   └── library.py
│       └── websocket.py
│
├── tui/
│   └── main.py
│
├── gui/
│   └── ...
│
├── script to run both backend and TUI/GUI
└── requirements.txt
```