# Voice Maze

**Project title:** Voice Controlled Gaming Tools for Enhanced Learning in the Skill Ecosystem

Voice Maze is a 2D learning game built with Python and Pygame. Choose Python, SQL, or Logical Reasoning and a difficulty, review five topic pages, then navigate a maze and answer three questions at each of its five locked topic doors.

The learning loop is **LEARN → PLAY → ASSESS → REVISE → UNLOCK**. Voice recognition runs outside the game loop. Google speech recognition is the primary mode and has a bounded request timeout. If the connection is unavailable or too slow, the game sends the same captured phrase to the installed Vosk model and continues listening offline while periodically retrying online recognition. If Vosk, speech recognition, or microphone access is unavailable, the game shows a clear status message and mouse controls remain usable.

## Requirements

- Python 3.10 or newer
- A working microphone for voice input
- Internet access for the one-time offline model download, or for Google recognition when no offline model is installed

## Installation

Open a terminal in the project directory (the directory containing `main.py`), then create and activate a virtual environment.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m voice.download_model
```

The model download is about 40 MB and is stored under `assets/models/`. This one-time download requires internet. Google recognition remains the primary mode after installation; Vosk is used as the fallback when the internet connection is slow or unavailable.

Install the requirements and model using the same Python environment that launches the game. In particular, if you use the project virtual environment, activate it before installing and running the commands below. The game tries Google recognition first. When a network request fails or exceeds the configured timeout, it uses Vosk locally if the model is installed, then periodically retries Google recognition in the background. If Vosk is unavailable, the game explains that voice recognition needs internet and keeps mouse controls available.

To check the active environment:

```powershell
python -c "import sys, vosk; print(sys.executable); print(vosk.__file__)"
```

If that reports `ModuleNotFoundError: No module named 'vosk'`, connect to the internet temporarily and install it in that environment to enable offline recognition:

```powershell
python -m pip install -r requirements.txt
```

After the install and model download finish, voice commands work with or without internet. With internet available, Google is tried first; slow or failed requests switch to Vosk, and the listener retries Google periodically. Online requests are limited by the configured timeout, and transient network failures do not stop the microphone listener.

If PowerShell blocks activation, allow it for the current terminal session and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
```

**PyAudio troubleshooting on Windows:** If installing PyAudio reports that it cannot build a wheel, first install the Microsoft C++ Build Tools and retry. Alternatively, install a trusted prebuilt PyAudio wheel that matches your Python version and Windows architecture, then install the remaining packages with `pip install -r requirements.txt`. Avoid installing a wheel for a different Python version or machine architecture.

### macOS

Install PortAudio, create/activate a virtual environment, then install the requirements:

```bash
brew install portaudio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PyAudio still cannot find PortAudio, install the Xcode command-line tools (`xcode-select --install`) and retry. On Apple Silicon, use a Python build matching the architecture of the installed PortAudio libraries.

### Linux (Debian/Ubuntu)

Install the system audio and build dependencies, then install the Python requirements:

```bash
sudo apt update
sudo apt install python3-venv python3-dev build-essential portaudio19-dev
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PyAudio fails to build, confirm that `portaudio19-dev`, the Python development headers, and a C compiler are installed for the active Python version.

After installing the requirements on macOS or Linux, download the offline voice model once:

```bash
python -m voice.download_model
```

## Run the game

Run the entry point from the `voice_maze` project directory:

```bash
python main.py
```

On Windows, if the project is in `C:\Users\Vivek\voice maze miniproject\voice_maze`, use:

```powershell
Set-Location "C:\Users\Vivek\voice maze miniproject\voice_maze"
python main.py
```

## Play

1. Select **Start Learning**, then choose a domain. Only Beginner is initially unlocked. Complete the Beginner maze to unlock Intermediate, then complete Intermediate to unlock Advanced; this progress is saved per domain. An unfinished run does not unlock the next level.
2. Read all five lesson pages. Each page contains key ideas, an example, and its expected output. Use the mouse wheel over the notes panel to scroll longer notes.
3. Start the maze. Each of the nine domain-and-level combinations has a distinct deterministic layout. Every maze is perfect: all walkable tiles are connected, there are no loops or shortcuts, and exactly one path leads from start to finish. Beginner uses a compact 5×5 cell maze (11×11 tiles); Intermediate uses 7×7 cells (15×15 tiles); Advanced uses 9×9 cells (19×19 tiles). Difficulty increases in every domain through larger mazes, longer routes, more turns, and more junctions. A directional command follows the open corridor and stops at the next junction, wall, locked door, or finish.
4. Answer each door's three questions by saying an option or its answer. All three questions must be correct to unlock that topic door.
5. If an answer is wrong, review that door's topic and try again. Each level gives two attempts.
6. Results show completion, score, accuracy, elapsed time, and the saved best completion time. Score history is stored under `data/scores.json`.

The game accepts natural phrasings and short commands. The examples below are suggestions, not the only recognized wording.

| Screen or action | Example voice commands |
|---|---|
| Main menu | “Start”, “start the game”, “start learning”, “how to play”, “quit” |
| Choose a domain | “Python”, “go with SQL”, “I want to learn logical reasoning” |
| Choose a difficulty | “Beginner”, “medium difficulty”, “hardest level” |
| Learning notes | “Next”, “next page”, “back”, “start”, “start the maze”; on the final page, “OK go on”, “go ahead”, or “continue” |
| Move in the maze | “Up”, “go right”, “move down”, “turn left”, “north” |
| Answer a question | “Option A”, “I choose B”, “option C”, or say the answer text |
| Revision and results | “Try again”, “return to maze”, “view results”, “play again”, “main menu” |

Voice captions appear as **You said** at the bottom of the screen. The microphone badge shows whether the application is listening, processing, or has encountered a microphone error. Voice capture adapts its sensitivity to room noise and uses a shorter pause before submitting a phrase. Speak in a normal voice near the microphone, wait briefly for the listening badge before speaking, and pause momentarily between commands. Online Google speech recognition needs a working internet connection; installed offline recognition does not. Mouse controls remain available as an alternative.

The microphone badge identifies online and offline listening/recognition separately. While using Vosk, the local recognizer uses a command-focused grammar for game controls and a separate free-form pass for spoken quiz answers; audio is not sent to Google for those offline phrases. If no model is installed, the game continues trying online recognition and reports when internet is unavailable. You can reinstall or repair the model by running `python -m voice.download_model` after moving or removing an incomplete model directory.

On learning notes, saying **“start”** or **“start the game”** requests the maze; the game still requires all five topics to be reviewed first. On the final notes page, “OK go on”, “go ahead”, and “continue” also start the maze. Explicit refusals such as “don’t start” are not treated as start commands. A temporary Google recognition outage no longer permanently stops the microphone worker; voice recognition can resume when the service becomes available again.

### Mouse and keyboard

The interface supports mouse clicks for all menu, selection, notes, quiz, and results actions. Use the maze's on-screen directional pad to move when voice input is unavailable. Keyboard arrows are disabled during normal play; the hidden testing switch is `DEBUG_KEYBOARD_ENABLED` in `config.py`.

## Run tests

From the project directory, with the project dependencies installed:

```bash
python -m unittest discover -s tests -v
```

The tests cover command parsing, all nine content files, executable Python examples and displayed outputs, maze movement and route validation, scoring, and score persistence.

## Project structure

```text
voice_maze/
├── main.py                  # Application entry point
├── config.py                # Window, palette, timing, paths, and debug switch
├── requirements.txt         # Pygame, SpeechRecognition, and PyAudio
├── core/                    # Game loop, scene stack, and shared state
├── scenes/                  # Menu, selection, notes, maze, quiz, revision, results
├── voice/                   # Background listener, Vosk model setup, parser, mic status
├── maze/                    # Nine layouts, movement engine, BFS validator
├── content/                 # Nine domain/difficulty lesson and quiz JSON files
├── ui/                      # Theme, reusable components, and visual effects
├── utils/                   # Content validation, scoring, and JSON persistence
├── assets/                  # Optional game assets
├── data/
│   └── scores.json          # Persistent course scores and personal bests
└── tests/                   # Command, content, maze, scoring, and storage tests
```
