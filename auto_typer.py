"""
auto_typer.py
----------------------------------------
A simple keyboard "control system" built with PyAutoGUI.

Press a hotkey at any time, in any application, and this script types
predefined text wherever your cursor / text field currently has focus
(browser, chat app, notepad, code editor, terminal, etc). It works with
ANY app because PyAutoGUI just simulates real keystrokes at the OS level
— whatever window is focused when the hotkey fires is where it types.

SETUP
-----
    pip install pyautogui keyboard

    Windows: run as-is (may need to run as Administrator for hotkeys
             to work inside some elevated apps/games).
    macOS:   grant your terminal (or python) "Accessibility" AND
             "Input Monitoring" permission in
             System Settings > Privacy & Security.
    Linux:   the 'keyboard' library needs raw input access, so you'll
             usually need to run this with sudo:
                 sudo python3 auto_typer.py

USAGE
-----
    1. Edit the SNIPPETS dictionary below with the hotkeys/text you want.
    2. Run:  python auto_typer.py
    3. Click into whatever app/text field you want to type into.
    4. Press the hotkey. It types the matching snippet there.
    5. Press QUIT_HOTKEY (default ctrl+alt+q) to stop the script.

SAFETY
------
    PyAutoGUI's fail-safe is ON: if typing starts going somewhere you
    don't want, slam your mouse into any screen corner to immediately
    abort mid-type.
"""

import time
import pyautogui
import keyboard

# ------------------- CONFIG -------------------

# hotkey -> text that gets typed when that hotkey is pressed
SNIPPETS = {
    "f8": "Hello, this text was typed automatically.",
    "f9": "Thanks for your message - I'll get back to you shortly.",
}

QUIT_HOTKEY = "ctrl+alt+q"

TYPING_INTERVAL = 0.03   # seconds between keystrokes (lower = faster, less human-like)
PRE_TYPE_DELAY = 0.3     # short pause after hotkey press, lets modifier keys release first

# ------------------------------------------------

pyautogui.FAILSAFE = True   # move mouse to any screen corner to abort mid-type
pyautogui.PAUSE = 0.0       # pacing is handled by TYPING_INTERVAL instead


def type_snippet(text: str, hotkey: str):
    print(f"[{hotkey}] pressed -> typing in {PRE_TYPE_DELAY}s...")
    time.sleep(PRE_TYPE_DELAY)
    try:
        pyautogui.write(text, interval=TYPING_INTERVAL)
        print("done.\n")
    except pyautogui.FailSafeException:
        print("Aborted (mouse hit a screen corner - fail-safe triggered).\n")


def main():
    print("Auto-typer running. Click into the app/field you want to type into, then:\n")
    for hotkey, text in SNIPPETS.items():
        preview = text if len(text) <= 40 else text[:37] + "..."
        print(f"  press '{hotkey}'  -> types: {preview!r}")
    print(f"  press '{QUIT_HOTKEY}' -> quit\n")

    for hotkey, text in SNIPPETS.items():
        keyboard.add_hotkey(hotkey, type_snippet, args=(text, hotkey))

    keyboard.wait(QUIT_HOTKEY)
    print("Quitting.")


if __name__ == "__main__":
    main()
