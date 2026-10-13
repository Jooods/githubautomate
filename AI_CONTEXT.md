# AI Context Blueprint: githubautomate

> This document is engineered for AI Coding Assistants (Antigravity, Cursor, Copilot, Windsurf, Claude Code).
> It provides high-signal context regarding architecture, tech stack, workflows, and conventions to prevent hallucination.

---

## 1. Project Overview & Architecture
- **Project Name**: `githubautomate`
- **Core Domain**: Desktop GitHub Repository Manager with PySide6, PyGithub, GitPython, and AI Context Generator
- **Primary Language**: `Python`
- **Frameworks & Ecosystem**: PySide / PyQt
- **Architecture Pattern**: Modular separation of concerns (Core Engine / Services / UI / Data Layer).

### Language Breakdown
- **Python**: 22 files

---

## 2. Directory Map & Key Files
```text
githubautomate/
├── core/
│   ├── __init__.py
│   ├── ai_context_generator.py
│   ├── db.py
│   ├── git_manager.py
│   ├── github_client.py
│   ├── semver_manager.py
│   └── workers.py
├── main.py
├── requirements.txt
├── tests/
│   └── test_core.py
└── ui/
    ├── __init__.py
    ├── dialogs/
    │   ├── __init__.py
    │   ├── ai_context_dialog.py
    │   ├── auth_dialog.py
    │   ├── clone_dialog.py
    │   ├── release_dialog.py
    │   ├── settings_dialog.py
    │   └── upload_dialog.py
    ├── log_console.py
    ├── main_window.py
    ├── repo_details.py
    ├── repo_view.py
    └── styles.py
```

### Key Entry Points
- `main.py`

---

## 3. Technology Stack & Manifests
- **Primary Language**: `Python`
- **Frameworks**: `PySide / PyQt`
- **Testing Setup**: Configured (Unit/Integration)
- **CI / Workflows**: Local / Manual workflows
- **Containerization**: Host native execution

---

## 4. Development Workflows & Commands
Run these commands within the project root:

### Environment Setup & Dependencies
```bash
# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Start development runtime
python main.py
```

### Running Tests & Quality Checks
```bash
# Execute test suite
pytest
```

---

## 5. Coding Standards & AI Directives
When generating code or proposing modifications for this project:

1. **Architecture Integrity**: Keep business logic, UI layer, and API integration decoupled.
2. **Clean Code & Typing**:
   - Use explicit type annotations where supported (Python).
   - Prefer descriptive naming conventions for functions, variables, and classes.
3. **Documentation Preservation**:
   - Preserve existing docstrings, comments, and license headers unless explicitly instructed.
4. **Error Handling & Resilience**:
   - Use structured try/except or Result pattern with clear error messages.
   - Never silence exceptions silently; log or bubble them to the UI/console.
5. **Dependency Discipline**:
   - Do not introduce heavy third-party packages if standard library or existing modules suffice.