## PyGetVerse

Lightweight Python utility to package and distribute verse data (currently Tamil verses) and a minimal runtime that reads, processes, and optionally bundles them into a standalone Windows executable via PyInstaller.

### Purpose

- **Centralize verse data** under `public/verses/` as JSON files for easy maintenance and versioning.
- **Provide a simple runtime** (`main.py`) to read and use that content locally or in downstream tools.
- **Ship a portable binary** (`dist/PyGetVerse/PyGetVerse.exe`) for Windows users who don't have Python installed.

### Repository Layout

- `main.py`: Entry point that loads and processes verse JSON files.
- `public/verses/`: Canonical verse data organized by language directory (e.g., `tamil/`).
- `requirements.txt`: Python dependencies used by the runtime and build process.
- `pyinstaller.spec`: Build configuration used by PyInstaller to produce the executable.
- `build/` and `dist/`: PyInstaller build artifacts and final distribution output (generated).

### Data Model

Each verse is represented as a JSON file under `public/verses/<language>/`. File naming and schema are intentionally simple to support offline use and bundling inside the executable. Keep fields consistent across files to simplify processing in `main.py`.

### Workflow

1. **Edit or add verse JSON files**
   - Place new files under `public/verses/<language>/`.
   - Validate JSON structure and naming for consistency.
2. **Run locally (Python)**
   - Use `python main.py` to read/process the verses during development.
3. **Build executable (Windows)**
   - Use PyInstaller (via `pyinstaller.spec`) to bundle the runtime and data for distribution.
4. **Distribute**
   - Share the contents of `dist/PyGetVerse/` with end users. They can run `PyGetVerse.exe` directly without Python.

### Getting Started (Development)

1. Create a virtual environment (optional but recommended):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
pip install -r requirements.txt
```

3. Run the app:

```powershell
python main.py
```

### Building the Windows Executable

The repo includes a ready-to-use `pyinstaller.spec`. Build with:

```powershell
pip install -r requirements.txt
pip install pyinstaller
pyinstaller pyinstaller.spec --noconfirm
```

Outputs:

- `build/pyinstaller/`: Intermediate artifacts and logs.
- `dist/PyGetVerse/`: Final portable app folder with `PyGetVerse.exe` and bundled assets.

If you need a one-off build without the spec file, you can also run:

```powershell
pyinstaller --noconsole --name PyGetVerse --add-data "public;public" main.py
```

Note: Adjust `--add-data` syntax if running on non-Windows shells.

### Contributing

- Keep JSON files small and focused; prefer many small files over one large file.
- Validate JSON before committing.
- Avoid breaking schema changes without updating `main.py` accordingly.

### License

Specify a license for the project (e.g., MIT). If none is specified yet, consider adding one.
