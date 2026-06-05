#!/usr/bin/env python3
import json
import os
import queue
import select
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path

from pynput import keyboard
from Xlib import X, XK, display


CONFIG = Path(
    os.environ.get(
        "TEXT_EXPANDER_CONFIG",
        Path.home() / ".config" / "linux-tab-text-expander" / "replacements.json",
    )
)
MAX_BUFFER = 80
TERMINAL_EXTRA_BACKSPACES = int(os.environ.get("TEXT_EXPANDER_TERMINAL_EXTRA_BACKSPACES", "1"))

buffer = ""
expanding = False
active_shortcut = None
active_typed = ""
target_window = None
lock = threading.Lock()
ui_events = queue.Queue()


def load_replacements():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    return {item["shortcut"]: item["expansion"] for item in data}


replacements = load_replacements()


def run(args, *, input_text=None):
    return subprocess.run(
        args,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def active_window_id():
    result = run(["xdotool", "getactivewindow"])
    window_id = result.stdout.strip()
    return window_id if result.returncode == 0 and window_id else None


def activate_window(window_id):
    if window_id:
        run(["xdotool", "windowactivate", window_id])


def window_properties(window_id):
    if not window_id:
        return "", ""
    result = run(["xprop", "-id", window_id, "WM_CLASS", "WM_NAME"])
    if result.returncode != 0:
        return "", ""
    wm_class = ""
    wm_name = ""
    for line in result.stdout.lower().splitlines():
        if line.startswith("wm_class"):
            wm_class = line
        elif line.startswith("wm_name"):
            wm_name = line
    return wm_class, wm_name


def is_terminal_window(window_id):
    wm_class, wm_name = window_properties(window_id)
    terminal_markers = [
        "terminal",
        "xterm",
        "ghostty",
        "kitty",
        "alacritty",
        "terminator",
        "tilix",
        "wezterm",
        "console",
    ]
    return "lmux" in wm_class or "lmux" in wm_name or any(marker in wm_class for marker in terminal_markers)


def insert_expansion(text, window_id, typed):
    if is_terminal_window(window_id):
        activate_window(window_id)
        time.sleep(0.03)
        # In lmux/Codex the important UX bug is Tab reaching the TUI. Once Tab is
        # consumed by the X11 grab, direct typing is more reliable than trying to
        # drive each terminal widget's paste shortcut.
        for _ in range(len(typed) + TERMINAL_EXTRA_BACKSPACES):
            run(["xdotool", "key", "--clearmodifiers", "BackSpace"])
            time.sleep(0.015)
        run(["xdotool", "type", "--clearmodifiers", "--delay", "0", text])
        return

    activate_window(window_id)
    time.sleep(0.03)
    run(["xdotool", "type", "--clearmodifiers", "--delay", "0", text])


def expand(shortcut, typed, window_id):
    global expanding
    with lock:
        expanding = True

    try:
        activate_window(window_id)
        time.sleep(0.03)
        if not is_terminal_window(window_id):
            for _ in range(len(typed)):
                run(["xdotool", "key", "BackSpace"])
                time.sleep(0.01)

        insert_expansion(replacements[shortcut], window_id, typed)
        time.sleep(0.08)
    finally:
        with lock:
            expanding = False


def reset_buffer():
    global buffer
    buffer = ""


def match_shortcut():
    for candidate in sorted(replacements, key=len, reverse=True):
        if buffer.endswith(candidate):
            return candidate, candidate

    for typed_len in range(min(len(buffer), MAX_BUFFER), 2, -1):
        typed = buffer[-typed_len:]
        matches = [
            candidate for candidate in sorted(replacements, key=len, reverse=True)
            if candidate.startswith(typed)
        ]
        if matches:
            return matches[0], typed

    return None, ""


def request_hint(shortcut):
    ui_events.put(("show", shortcut))


def request_hide_hint():
    ui_events.put(("hide", None))


def accept_active_shortcut():
    global active_shortcut, active_typed, target_window

    with lock:
        shortcut = active_shortcut
        typed = active_typed
        window_id = target_window
        if not shortcut:
            return False
        reset_buffer()
        active_shortcut = None
        active_typed = ""
        target_window = None

    request_hide_hint()
    threading.Thread(target=expand, args=(shortcut, typed, window_id), daemon=True).start()
    return True


def on_press(key):
    global active_shortcut, active_typed, buffer, target_window

    with lock:
        if expanding:
            return

    if key == keyboard.Key.backspace:
        buffer = buffer[:-1]
        shortcut, typed = match_shortcut()
        active_shortcut = shortcut
        active_typed = typed
        if shortcut:
            target_window = active_window_id()
            request_hint(shortcut)
        else:
            active_typed = ""
            target_window = None
            request_hide_hint()
        return

    if key == keyboard.Key.tab:
        if active_shortcut:
            return
        reset_buffer()
        active_shortcut = None
        active_typed = ""
        target_window = None
        request_hide_hint()
        return

    if key == keyboard.Key.space:
        reset_buffer()
        active_shortcut = None
        active_typed = ""
        target_window = None
        request_hide_hint()
        return

    if key in (keyboard.Key.enter, keyboard.Key.esc):
        reset_buffer()
        active_shortcut = None
        active_typed = ""
        target_window = None
        request_hide_hint()
        return

    if isinstance(key, keyboard.KeyCode) and key.char:
        char = key.char
        if char.isspace():
            reset_buffer()
            active_shortcut = None
            active_typed = ""
            target_window = None
            request_hide_hint()
            return
        buffer = (buffer + char)[-MAX_BUFFER:]
        shortcut, typed = match_shortcut()
        active_shortcut = shortcut
        active_typed = typed
        if shortcut:
            target_window = active_window_id()
            request_hint(shortcut)
        else:
            active_typed = ""
            target_window = None
            request_hide_hint()
        return

    reset_buffer()
    active_shortcut = None
    active_typed = ""
    target_window = None
    request_hide_hint()


class HintWindow:
    def __init__(self, root):
        self.root = root
        self.window = tk.Toplevel(root)
        self.window.withdraw()
        self.window.overrideredirect(True)
        try:
            self.window.attributes("-type", "tooltip")
        except tk.TclError:
            pass
        self.window.attributes("-topmost", True)
        self.window.configure(bg="#1f2937", padx=8, pady=5)
        self.label = tk.Label(
            self.window,
            bg="#1f2937",
            fg="#f9fafb",
            font=("Sans", 10),
            justify="left",
            padx=4,
            pady=2,
        )
        self.label.pack()

    def show(self, shortcut):
        expansion = replacements[shortcut].replace("\n", " ")
        preview = expansion[:88] + ("..." if len(expansion) > 88 else "")
        self.label.configure(text=f"{shortcut}  ->  Tab: {preview}")
        x = self.root.winfo_pointerx() + 16
        y = self.root.winfo_pointery() + 18
        self.window.geometry(f"+{x}+{y}")
        self.window.deiconify()
        self.window.lift()
        activate_window(target_window)

    def hide(self):
        self.window.withdraw()


def pump_ui(root, hint):
    while True:
        try:
            action, shortcut = ui_events.get_nowait()
        except queue.Empty:
            break
        if action == "show":
            hint.show(shortcut)
        else:
            hint.hide()
    root.after(25, pump_ui, root, hint)


def tab_grabber_loop():
    d = display.Display()
    root = d.screen().root
    tab_keycode = d.keysym_to_keycode(XK.string_to_keysym("Tab"))

    def grab_tab():
        root.grab_key(tab_keycode, X.AnyModifier, False, X.GrabModeAsync, X.GrabModeAsync)
        d.flush()

    def ungrab_tab():
        root.ungrab_key(tab_keycode, X.AnyModifier)
        d.flush()

    def replay_tab():
        ungrab_tab()
        run(["xdotool", "key", "--clearmodifiers", "Tab"])
        grab_tab()

    grab_tab()

    while True:
        readable, _, _ = select.select([d.fileno()], [], [], 0.05)
        if not readable:
            continue

        while d.pending_events():
            event = d.next_event()
            if event.type != X.KeyPress or event.detail != tab_keycode:
                continue
            if not accept_active_shortcut():
                replay_tab()


def main():
    root = tk.Tk()
    root.withdraw()
    hint = HintWindow(root)
    listener = keyboard.Listener(on_press=on_press)
    listener.daemon = True
    listener.start()
    threading.Thread(target=tab_grabber_loop, daemon=True).start()
    pump_ui(root, hint)
    root.mainloop()


if __name__ == "__main__":
    main()
