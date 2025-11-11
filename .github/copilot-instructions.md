# Copilot Instructions for Coucou

## Project Overview

Coucou is a minimalist, cross-platform FOSS (Free and Open Source Software) wordbank application designed for language learning. It's built with PySide6 (Qt for Python) and currently supports French, with plans to add more languages.

### Key Features
- Import vocabulary lists from CSV files with audio
- Auto-generate audio using Google TTS
- Review vocabularies with customizable date filters
- Export and restore review progress
- Search and edit saved vocabularies
- French verb conjugator
- Usage statistics tracking

### Project Status
- Alpha stage: All main functionalities work
- No build version yet; runs from Python source
- Currently French-only, multi-language support planned

## Technology Stack

### Core Dependencies
- **PySide6 (>=6.9.0)**: Qt framework for Python, main UI framework
- **Python 3.12**: Required version (not 3.13 due to dependency constraints)
- **SQLite**: Database via Qt's QSqlDatabase
- **gTTS (>=2.5.4)**: Google Text-to-Speech for audio generation
- **mlconjug3 (>=3.11.0)**: French verb conjugation
- **PyYAML, toml**: Configuration file handling
- **pytest**: Testing framework
- **rich**: Terminal output formatting

### Important Dependency Notes
- **Known Issue**: mlconjug3 requires scikit-learn 1.3.0, which officially requires numpy 1.25
- **Workaround**: We explicitly use numpy 1.26.0 (works despite version mismatch)
- This is necessary because scikit-learn 1.3.0's dependency specs are outdated
- Poetry/pip dependency resolution needs this override

## Project Architecture

### Main Application Structure
- `main.py`: Main application window with navigation buttons
- `retrieval.py`: Review/quiz interface for vocabulary practice
- `record_manager.py`: Manage and edit vocabulary records
- `massImporter.py`: Bulk import from CSV files
- `exporterBulk.py`: Export functionality
- `conjugator.py`: French verb conjugation tool
- `db.py`: Database management layer (SQLite via QSqlDatabase)
- `missing_responses_dialog.py`: Dialog for handling incomplete entries
- `common_methods.py`: Shared utility functions and helper classes
- `usage_statistics.py`: Track and display usage metrics
- `logger.py`: Centralized logging configuration

### Database Structure
- Single SQLite database per language (e.g., `history-fr.db`)
- Main table: `records` with columns:
  - UUID (TEXT PRIMARY KEY)
  - media_file (TEXT): Path to audio file
  - question (TEXT): Vocabulary question/prompt
  - response (TEXT): Answer/translation
  - creation_date (TEXT): ISO format date
  - custom_media (INTEGER): Flag for user-provided audio
  - attribution (TEXT): Source attribution

### Configuration
- `config.toml`: User preferences (font size, username, language, database path, conjugation defaults)
- Configuration loaded at startup in `MainApp.__init__()`

## Code Style and Conventions

### Qt Dialogs and Windows
**CRITICAL**: Always prefer non-blocking methods for dialogs and windows.
- ✅ Use: `dialog.show()` or `dialog.open()`
- ❌ Avoid: `dialog.exec()` (blocking)
- This ensures better user experience and prevents UI freezing

### Python Style
- Use French comments and variable names when contextually appropriate (this is a French learning app)
- Follow PEP 8 conventions
- Use type hints where helpful (see `db.py` for examples: `from __future__ import annotations`)
- Prefer descriptive variable names

### Logging
- Use the centralized logger from `logger.py`
- Import: `from logger import logger`
- Methods: `logger.info()`, `logger.error()`, `logger.warning()`, `logger.debug()`
- Don't use print statements except for debugging during development
- FFmpeg errors go to separate `ffmpeg_errors.log` via `ffmpeg_logger`

### Audio File Management
- Audio files stored in `assets/audio/{database_name}-audio/`
- File naming: `{UUID}.mp3` for generated audio
- Custom audio preserves original filename in `media_file` column
- Use `MediaUtils` class from `common_methods.py` for audio operations

### CSV File Handling
- Template: `template.csv` for vocabulary
- Format: question, response, audio_path (optional), attribution
- Multiple responses separated by semicolons (`;`)
- Use `csv` module with UTF-8 encoding

### Error Handling
- Display user-facing errors with `QMessageBox` (critical, warning, information)
- Use `DialogUtils` from `common_methods.py` for consistent error dialogs
- Log all errors with context using the logger
- Save partial progress where possible (see `MissingResponsesDialog.PROGRESS_FILE`)

## Development Workflow

### Setting Up Development Environment
```bash
# Install Poetry (if not installed)
# Note: Poetry may not be in PATH; the project uses pyproject.toml

# Install dependencies from poetry.lock
poetry install

# Or use pip with pyproject.toml
pip install -e .
```

### Running the Application
```bash
# Activate poetry environment
poetry shell

# Or with poetry run
poetry run python main.py

# Direct Python (if dependencies installed)
python main.py
```

### Testing
```bash
# Run pytest
pytest

# Run specific test file
pytest test_missing_responses_dialog.py

# With verbose output
pytest -v
```

### File Organization
- Test files: `test_*.py` pattern
- Temporary files: Store in `/tmp/` (not tracked by git)
- Data files: CSV files for vocabulary, `.db` files for databases
- Audio: `assets/audio/` directory structure
- Logs: `coucou_main_log.log`, `ffmpeg_errors.log`

### Git Workflow
- Lock files (`.~lock.*`) should be in `.gitignore`
- Database files (`.db`) should be in `.gitignore` (user data)
- Audio files in `assets/audio/` should be in `.gitignore` (generated content)
- Log files should be in `.gitignore`

## Common Patterns and Best Practices

### UI Components
```python
# Non-blocking dialog pattern
dialog = SomeDialog(parent)
dialog.show()  # Non-blocking
# Connect signals if needed
dialog.finished.connect(self.on_dialog_finished)

# MessageBox usage
from common_methods import DialogUtils
DialogUtils.show_error(parent, "Title", "Message")
DialogUtils.show_info(parent, "Title", "Message")
```

### Database Operations
```python
# Always use context manager pattern with queries
from PySide6.QtSql import QSqlQuery

query = QSqlQuery(self.db)
query.prepare("SELECT * FROM records WHERE UUID = ?")
query.addBindValue(uuid)
if query.exec_():
    while query.next():
        # Process results
        uuid = query.value(0)
```

### Audio Playback
```python
# Use QMediaPlayer with QAudioOutput
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl

player = QMediaPlayer()
audio_output = QAudioOutput()
player.setAudioOutput(audio_output)
player.setSource(QUrl.fromLocalFile(audio_path))
player.play()
```

### Text Processing
```python
# Use utilities from common_methods
from common_methods import TextUtils

# Normalize text (remove accents, lowercase)
normalized = TextUtils.normalize_text(text)

# Compare with fuzzy matching
similarity = TextUtils.similarity_ratio(text1, text2)
```

### Progress Saving/Loading
```python
import json

# Save progress
progress_data = {"current_index": self.current_index, "entries": self.entries}
with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
    json.dump(progress_data, f, ensure_ascii=False, indent=2)

# Load progress
with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
    progress = json.load(f)
```

## Testing Guidelines

### Test Structure
- Use pytest fixtures for QApplication setup
- Use `qtbot` fixture from pytest-qt for widget testing
- Test files should be independent and not rely on external state
- Mock database connections when testing UI logic

### Example Test Pattern
```python
import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="module")
def app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app

def test_something(qtbot, app):
    widget = SomeWidget()
    qtbot.addWidget(widget)
    # Test widget behavior
    assert widget.property == expected_value
```

## Common Pitfalls

1. **Qt Dialog Blocking**: Never use `exec()` for dialogs - always use `show()` or `open()`
2. **Database Connections**: Each DatabaseManager instance creates a unique connection - don't share connections across threads
3. **Audio File Paths**: Always use absolute paths for audio files to avoid Qt media player issues
4. **Text Encoding**: Always specify `encoding="utf-8"` when reading/writing files
5. **CSV Parsing**: Handle empty fields and whitespace carefully in CSV imports
6. **Memory Management**: Qt objects need proper parent-child relationships to avoid memory leaks
7. **Signal/Slot Connections**: Disconnect signals when widgets are destroyed to prevent crashes

## Performance Considerations

- Audio generation with gTTS can be slow - show progress indicators
- Database queries should use prepared statements and indexes
- Large CSV imports should show progress bars (use `ProgressBarHelper` from common_methods)
- Cache frequently accessed data (e.g., favorites list)

## Security Considerations

- Sanitize user input before SQL queries (use prepared statements)
- Validate file paths before file operations
- Be cautious with `eval()` or `exec()` - avoid them entirely
- Validate CSV data before importing to database

## Internationalization Notes

- Currently French-only (`language_code = "fr"`)
- Text-to-speech uses language code from config
- UI labels and messages are in French
- Future multi-language support planned
- Use language_code parameter in relevant functions for future i18n