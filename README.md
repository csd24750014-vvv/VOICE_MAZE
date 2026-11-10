# Voice Maze

**Project title:** Voice Controlled Gaming Tools for Enhanced Learning in the Skill Ecosystem

Voice Maze is a 2D learning game built with Python and Pygame. Choose Python, SQL, or Logical Reasoning and a difficulty, review five topic pages, then navigate a maze and answer three questions at each of its five locked topic doors.

The learning loop is **LEARN → PLAY → ASSESS → REVISE → UNLOCK**. Voice recognition runs outside the game loop. If speech recognition or microphone access is unavailable, the game reports the issue and the mouse controls remain usable.

## Requirements

- Python 3.10 or newer
- A working microphone for voice input
- Internet access for Google speech recognition (the game remains playable with mouse input without it)

## Installation

Open a terminal in the project directory (the directory containing `main.py`), then create and activate a virtual environment.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

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
3. Start the maze. Every course uses a deterministic, perfect maze: all walkable tiles are connected, there are no loops or shortcuts, and exactly one path leads from start to finish. Beginner uses a 9×9 cell maze; Intermediate uses 11×11; Advanced uses 13×13. Larger levels have more turns and dead ends. A directional command follows the open corridor and stops at the next junction, wall, locked door, or finish.
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

Voice captions appear as **You said** at the bottom of the screen. The microphone badge shows whether the application is listening, processing, or has encountered a microphone error. Voice capture adapts its sensitivity to room noise and uses a shorter pause before submitting a phrase. Speak in a normal voice near the microphone, wait briefly for the **Listening** badge before speaking, and pause momentarily between commands. Google speech recognition needs a working internet connection; the game does not require speech to continue and provides mouse alternatives.

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
├── voice/                   # Background listener, command parser, mic status
├── maze/                    # Nine layouts, movement engine, BFS validator
├── content/                 # Nine domain/difficulty lesson and quiz JSON files
├── ui/                      # Theme, reusable components, and visual effects
├── utils/                   # Content validation, scoring, and JSON persistence
├── assets/                  # Optional game assets
├── data/
│   └── scores.json          # Persistent course scores and personal bests
└── tests/                   # Command, content, maze, scoring, and storage tests
```
