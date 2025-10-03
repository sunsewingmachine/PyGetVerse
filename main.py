import json
import os
import sys
import time
from pathlib import Path

import pyautogui
import tkinter as tk
from tkinter import ttk


APP_TITLE = "PyGetVerse - Quran Paster"
BASE_DIR = Path(__file__).resolve().parent

# Resolve resource directory (data files) for both source and PyInstaller-frozen exe
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    RESOURCES_DIR = Path(sys._MEIPASS)
else:
    RESOURCES_DIR = BASE_DIR

VERSES_DIR = RESOURCES_DIR / "public" / "verses" / "tamil"

# Settings stored in a user config directory (persistent across exe updates)
_default_config_root = Path(os.getenv("APPDATA", str(Path.home())))/"PyGetVerse"
_default_config_root.mkdir(parents=True, exist_ok=True)
SETTINGS_PATH = _default_config_root / "settings.json"


class QuranPasterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        self.root.geometry("380x200")

        # State
        self.paste_pending = False
        self.last_text_copied = ""
        self.include_arabic = tk.BooleanVar(value=True)
        self.include_tamil = tk.BooleanVar(value=True)

        # Load saved settings
        self._load_settings()

        # UI
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill=tk.BOTH, expand=True)

        label = ttk.Label(container, text="Enter chapter:verse (e.g., 1:1)")
        label.pack(anchor=tk.W)

        self.input_var = tk.StringVar()
        self.entry = ttk.Entry(container, textvariable=self.input_var)
        self.entry.pack(fill=tk.X, pady=(4, 6))
        self.entry.focus_set()
        self.entry.bind("<Return>", self._on_submit)

        # Options
        options_row = ttk.Frame(container)
        options_row.pack(fill=tk.X, pady=(2, 2))
        self.arabic_chk = ttk.Checkbutton(options_row, text="Arabic", variable=self.include_arabic)
        self.arabic_chk.pack(side=tk.LEFT)
        self.tamil_chk = ttk.Checkbutton(options_row, text="Tamil", variable=self.include_tamil)
        self.tamil_chk.pack(side=tk.LEFT, padx=(10, 0))

        self.status_var = tk.StringVar()
        self.status = ttk.Label(container, textvariable=self.status_var, foreground="#444")
        self.status.pack(anchor=tk.W, pady=(2, 6))

        buttons = ttk.Frame(container)
        buttons.pack(fill=tk.X)
        self.submit_btn = ttk.Button(buttons, text="Copy & Paste", command=self._on_submit)
        self.submit_btn.pack(side=tk.LEFT)
        # Removed Hide button per request

        # Paste on focus loss only when paste_pending is True
        self.root.bind("<FocusOut>", self._on_focus_out)
        # Exit on Escape
        self.root.bind("<Escape>", lambda _e: self._exit_app())
        # Save settings on exit
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # On startup, prefill input from clipboard if it contains a valid reference
        self._prefill_from_clipboard()

    def _hide(self) -> None:
        try:
            self.root.withdraw()
        except Exception:
            pass

    def _on_focus_out(self, _event=None) -> None:
        if not self.paste_pending:
            return
        # Give a short moment for the other window to receive focus
        time.sleep(0.15)
        try:
            pyautogui.hotkey("ctrl", "v")
            self.status_var.set("Pasted")
            # Exit app after a successful paste
            self.root.after(50, self._exit_app)
        except Exception as exc:
            self.status_var.set(f"Paste failed: {exc}")
        finally:
            self.paste_pending = False

    def _on_submit(self, _event=None) -> None:
        ref = (self.input_var.get() or "").strip()
        try:
            chapter, start_verse, end_verse = self._parse_reference(ref)
        except ValueError as exc:
            self.status_var.set(str(exc))
            return

        # Build text per options
        if not self.include_arabic.get() and not self.include_tamil.get():
            self.status_var.set("Select at least one: Arabic or Tamil")
            return

        try:
            text = self._build_paste_text(
                chapter,
                start_verse,
                end_verse,
                self.include_arabic.get(),
                self.include_tamil.get(),
            )
        except FileNotFoundError:
            self.status_var.set(f"No data for chapter {chapter}")
            return
        except KeyError:
            if start_verse == end_verse:
                self.status_var.set(f"Verse {chapter}:{start_verse} not found")
            else:
                self.status_var.set(f"One or more verses not found for {chapter}:{start_verse}-{end_verse}")
            return
        except Exception as exc:
            self.status_var.set(f"Error: {exc}")
            return

        if not text:
            self.status_var.set("Empty verse text")
            return

        # Copy to clipboard
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()  # ensure clipboard is set
            self.last_text_copied = text
        except Exception as exc:
            self.status_var.set(f"Clipboard error: {exc}")
            return

        # Prepare to paste upon focus loss, then hide window so focus moves away
        self.paste_pending = True
        if start_verse == end_verse:
            self.status_var.set(f"Copied {chapter}:{start_verse}. Switch to target app...")
        else:
            self.status_var.set(f"Copied {chapter}:{start_verse}-{end_verse}. Switch to target app...")
        self._hide()

    def _prefill_from_clipboard(self) -> None:
        try:
            clip = self.root.clipboard_get()
        except Exception:
            return
        s = (clip or "").strip()
        if not s:
            return
        try:
            # Validate without mutating state if invalid
            self._parse_reference(s)
        except Exception:
            return
        # Set the input field once on startup
        self.input_var.set(s)
        self.status_var.set("Loaded reference from clipboard")

    def _get_verse_text(self, chapter: int, verse: int, use_arabic: bool, use_tamil: bool) -> str:
        file_path = VERSES_DIR / f"{chapter}.json"
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        with file_path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

        # Entries use key like "1:1"
        needle = f"{chapter}:{verse}"
        match = None
        for item in data:
            if item.get("verse_key") == needle:
                match = item
                break

        if not match:
            raise KeyError(needle)

        arabic = (match.get("arabic") or "").strip()
        tamil = (match.get("tamil_pj") or "").strip()

        lines = []
        if use_arabic and arabic:
            lines.append(arabic)
        if use_tamil and tamil:
            lines.append(tamil)
        body = "\n".join(lines).strip()

        # Always append suffix reference at the end of pasted data
        suffix = f" (அல்குர்ஆன்: {needle})"
        if body:
            return f"{body}{suffix}"
        # If body is empty for some reason, at least paste the suffix
        return suffix

    def _build_paste_text(self, chapter: int, start_verse: int, end_verse: int, use_arabic: bool, use_tamil: bool) -> str:
        # Single verse path reuses existing logic
        if start_verse == end_verse:
            return self._get_verse_text(chapter, start_verse, use_arabic, use_tamil)

        file_path = VERSES_DIR / f"{chapter}.json"
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        with file_path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

        verse_map = {}
        for item in data:
            if item.get("sura") == chapter and isinstance(item.get("ayah"), int):
                verse_map[item["ayah"]] = item

        segments = []
        for v in range(start_verse, end_verse + 1):
            item = verse_map.get(v)
            if not item:
                raise KeyError(f"{chapter}:{v}")
            arabic = (item.get("arabic") or "").strip()
            tamil = (item.get("tamil_pj") or "").strip()
            lines = []
            if use_arabic and arabic:
                lines.append(arabic)
            if use_tamil and tamil:
                lines.append(tamil)
            body = "\n".join(lines).strip()
            if body:
                segments.append(body)

        content = "\n\n".join(segments).strip()
        suffix = f" (அல்குர்ஆன்: {chapter}:{start_verse}-{end_verse})"
        if content:
            return f"{content}{suffix}"
        return suffix

    def _parse_reference(self, ref: str) -> tuple[int, int, int]:
        # Accept formats:
        #  C:V, C.V, C:V-end, C.V-end, C:V-C:W, C.V-C.W
        s = ref.replace(" ", "")
        if not s:
            raise ValueError("Please enter chapter:verse like 2:255 or 5.6-10")

        # Normalize separators to ':' and '-'
        s = s.replace(".", ":")

        if "-" in s:
            left, right = s.split("-", 1)
            if ":" in right:
                # Right may include chapter too
                r_ch_str, r_vs_str = right.split(":", 1)
                r_ch, r_vs = int(r_ch_str), int(r_vs_str)
            else:
                r_ch = None
                r_vs = int(right)

            l_ch_str, l_vs_str = left.split(":", 1)
            l_ch, l_vs = int(l_ch_str), int(l_vs_str)

            if r_ch is None:
                r_ch = l_ch
            if r_ch != l_ch:
                raise ValueError("Cross-chapter ranges are not supported")

            if r_vs < l_vs:
                raise ValueError("Range end must be greater than or equal to start")

            return l_ch, l_vs, r_vs

        # Single reference
        if ":" not in s:
            raise ValueError("Please enter chapter:verse like 2:255 or 5.6")
        ch_str, vs_str = s.split(":", 1)
        ch, vs = int(ch_str), int(vs_str)
        return ch, vs, vs

    def _on_close(self) -> None:
        self._save_settings()
        self._exit_app()

    def _exit_app(self) -> None:
        # Persist settings before exit
        try:
            self._save_settings()
        except Exception:
            pass
        try:
            self.root.destroy()
        finally:
            # Ensure process exits even if Tk loop lingers
            os._exit(0)

    def _load_settings(self) -> None:
        try:
            if SETTINGS_PATH.exists():
                with SETTINGS_PATH.open("r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.include_arabic.set(bool(cfg.get("include_arabic", True)))
                self.include_tamil.set(bool(cfg.get("include_tamil", True)))
        except Exception:
            # Ignore corrupt settings and keep defaults
            pass

    def _save_settings(self) -> None:
        cfg = {
            "include_arabic": bool(self.include_arabic.get()),
            "include_tamil": bool(self.include_tamil.get()),
        }
        with SETTINGS_PATH.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)


def main() -> None:
    root = tk.Tk()
    # Modernize ttk on Windows if available
    try:
        root.call("source", "azure.tcl")
        root.call("set_theme", "dark")
    except Exception:
        pass
    app = QuranPasterApp(root)
    root.deiconify()
    root.mainloop()


if __name__ == "__main__":
    # Fail fast if data directory missing
    if not VERSES_DIR.exists():
        print(f"Verses directory not found: {VERSES_DIR}")
    main()
