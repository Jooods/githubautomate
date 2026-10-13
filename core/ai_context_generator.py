import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.git_manager import GitManager
from core.semver_manager import SemVerManager

IGNORE_DIRS = {
    '.git', 'node_modules', 'venv', '.venv', 'env', '__pycache__',
    '.pytest_cache', '.idea', '.vscode', 'dist', 'build', 'target',
    'bin', 'obj', '.next', '.nuxt', 'vendor', '.eggs', '*.egg-info'
}

IGNORE_FILES = {
    '.DS_Store', 'Thumbs.db', 'package-lock.json', 'yarn.lock',
    'pnpm-lock.yaml', 'poetry.lock', 'Cargo.lock', '.env'
}

LANGUAGE_EXTS = {
    '.py': 'Python',
    '.js': 'JavaScript',
    '.jsx': 'JavaScript (React)',
    '.ts': 'TypeScript',
    '.tsx': 'TypeScript (React)',
    '.rs': 'Rust',
    '.go': 'Go',
    '.java': 'Java',
    '.kt': 'Kotlin',
    '.c': 'C',
    '.cpp': 'C++',
    '.h': 'C/C++ Header',
    '.cs': 'C#',
    '.php': 'PHP',
    '.rb': 'Ruby',
    '.swift': 'Swift',
    '.html': 'HTML',
    '.css': 'CSS',
    '.scss': 'SCSS',
    '.sql': 'SQL',
    '.sh': 'Shell',
    '.ps1': 'PowerShell'
}

class ProjectAnalyzer:
    def __init__(self, project_path: str):
        self.project_path = os.path.abspath(project_path)
        self.project_name = os.path.basename(self.project_path)

    def analyze(self) -> Dict[str, Any]:
        """Perform deep scan of the project directory."""
        if not os.path.exists(self.project_path):
            raise FileNotFoundError(f"Project path does not exist: {self.project_path}")

        files_by_lang: Dict[str, int] = {}
        total_files = 0
        manifests = {}
        detected_frameworks = set()
        entry_points = []
        has_tests = False
        has_docker = False
        has_ci = False

        # Scan files
        for root, dirs, files in os.walk(self.project_path):
            # Prune ignored directories
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.endswith('.egg-info')]

            rel_root = os.path.relpath(root, self.project_path)
            
            for file in files:
                if file in IGNORE_FILES:
                    continue
                
                total_files += 1
                rel_path = os.path.join(rel_root, file) if rel_root != '.' else file
                ext = os.path.splitext(file)[1].lower()

                if ext in LANGUAGE_EXTS:
                    lang = LANGUAGE_EXTS[ext]
                    files_by_lang[lang] = files_by_lang.get(lang, 0) + 1

                # Check entry points
                if file in ['main.py', 'app.py', 'manage.py', 'index.js', 'index.ts', 'server.js', 'main.go', 'main.rs']:
                    entry_points.append(rel_path)

                # Check tests
                if 'test' in file.lower() or 'test' in rel_root.lower() or 'spec' in file.lower():
                    has_tests = True

                # Check docker
                if file in ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml']:
                    has_docker = True

                # Check CI/CD
                if '.github' in rel_root and ('workflows' in rel_root or file.endswith('.yml') or file.endswith('.yaml')):
                    has_ci = True

                # Inspect manifests
                if file == 'package.json' and rel_root == '.':
                    manifests['package.json'] = self._parse_package_json(os.path.join(root, file))
                    if 'dependencies' in manifests['package.json']:
                        deps = manifests['package.json']['dependencies']
                        if 'react' in deps: detected_frameworks.add('React')
                        if 'vue' in deps: detected_frameworks.add('Vue')
                        if 'next' in deps: detected_frameworks.add('Next.js')
                        if 'express' in deps: detected_frameworks.add('Express')
                        if 'electron' in deps: detected_frameworks.add('Electron')
                
                elif file == 'requirements.txt' and rel_root == '.':
                    reqs = self._parse_requirements(os.path.join(root, file))
                    manifests['requirements.txt'] = reqs
                    req_lower = [r.lower() for r in reqs]
                    if any('pyside' in r or 'pyqt' in r for r in req_lower): detected_frameworks.add('PySide / PyQt')
                    if any('fastapi' in r for r in req_lower): detected_frameworks.add('FastAPI')
                    if any('flask' in r for r in req_lower): detected_frameworks.add('Flask')
                    if any('django' in r for r in req_lower): detected_frameworks.add('Django')
                    if any('torch' in r or 'tensorflow' in r for r in req_lower): detected_frameworks.add('PyTorch / ML')

                elif file == 'pyproject.toml' and rel_root == '.':
                    manifests['pyproject.toml'] = self._read_text_preview(os.path.join(root, file), 20)

                elif file == 'Cargo.toml' and rel_root == '.':
                    manifests['Cargo.toml'] = self._read_text_preview(os.path.join(root, file), 20)
                    detected_frameworks.add('Rust Cargo')

                elif file == 'go.mod' and rel_root == '.':
                    manifests['go.mod'] = self._read_text_preview(os.path.join(root, file), 10)
                    detected_frameworks.add('Go Module')

        # Generate directory tree
        tree_text = self._generate_tree(self.project_path, max_depth=3)

        # Git info
        git_info = {}
        if GitManager.is_git_repo(self.project_path):
            git_info = GitManager.get_repo_details(self.project_path)
            commits = GitManager.get_commits_for_changelog(self.project_path, max_count=30)
            git_info['recent_commits'] = commits

        # Primary language
        primary_lang = "Generic"
        if files_by_lang:
            primary_lang = max(files_by_lang, key=files_by_lang.get)

        return {
            "name": self.project_name,
            "path": self.project_path,
            "total_files": total_files,
            "languages": files_by_lang,
            "primary_language": primary_lang,
            "frameworks": list(detected_frameworks),
            "entry_points": entry_points,
            "has_tests": has_tests,
            "has_docker": has_docker,
            "has_ci": has_ci,
            "manifests": manifests,
            "tree": tree_text,
            "git": git_info
        }

    def _parse_package_json(self, path: str) -> Dict[str, Any]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                "name": data.get("name"),
                "version": data.get("version"),
                "scripts": list(data.get("scripts", {}).keys()),
                "dependencies": list(data.get("dependencies", {}).keys()),
                "devDependencies": list(data.get("devDependencies", {}).keys())
            }
        except Exception:
            return {}

    def _parse_requirements(self, path: str) -> List[str]:
        reqs = []
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        reqs.append(line.split(';')[0].split('==')[0].split('>=')[0].strip())
        except Exception:
            pass
        return reqs[:20]

    def _read_text_preview(self, path: str, max_lines: int = 15) -> str:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = [f.readline() for _ in range(max_lines)]
            return "".join([l for l in lines if l]).strip()
        except Exception:
            return ""

    def _generate_tree(self, root_path: str, max_depth: int = 3) -> str:
        lines = [f"{os.path.basename(root_path)}/"]

        def walk(current_dir, prefix="", depth=1):
            if depth > max_depth:
                return
            try:
                entries = sorted(os.listdir(current_dir))
            except Exception:
                return
            
            filtered = [
                e for e in entries 
                if e not in IGNORE_DIRS and e not in IGNORE_FILES and not e.startswith('.')
            ]
            
            for idx, entry in enumerate(filtered):
                is_last = (idx == len(filtered) - 1)
                connector = "└── " if is_last else "├── "
                entry_path = os.path.join(current_dir, entry)
                is_dir = os.path.isdir(entry_path)
                display_name = f"{entry}/" if is_dir else entry
                lines.append(f"{prefix}{connector}{display_name}")

                if is_dir:
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    walk(entry_path, new_prefix, depth + 1)

        walk(root_path)
        return "\n".join(lines[:60])


class AIContextGenerator:
    @staticmethod
    def generate_all(project_path: str, custom_description: str = "") -> Dict[str, str]:
        """Generate AI_CONTEXT.md, README.md, and CHANGELOG.md files."""
        analyzer = ProjectAnalyzer(project_path)
        info = analyzer.analyze()
        
        ai_context = AIContextGenerator.generate_ai_context(info, custom_description)
        readme = AIContextGenerator.generate_readme(info, custom_description)
        changelog = AIContextGenerator.generate_changelog(info)

        return {
            "AI_CONTEXT.md": ai_context,
            "README.md": readme,
            "CHANGELOG.md": changelog,
            "info": info
        }

    @staticmethod
    def generate_ai_context(info: Dict[str, Any], custom_description: str = "") -> str:
        name = info["name"]
        primary_lang = info["primary_language"]
        frameworks = ", ".join(info["frameworks"]) if info["frameworks"] else primary_lang
        desc = custom_description or f"Modern software project built with {primary_lang} and {frameworks}."
        
        lang_stats = "\n".join([f"- **{k}**: {v} files" for k, v in info["languages"].items()][:5])
        entry_points = "\n".join([f"- `{ep}`" for ep in info["entry_points"]]) if info["entry_points"] else "- (Determined from directory root)"

        md = f"""# AI Context Blueprint: {name}

> This document is engineered for AI Coding Assistants (Antigravity, Cursor, Copilot, Windsurf, Claude Code).
> It provides high-signal context regarding architecture, tech stack, workflows, and conventions to prevent hallucination.

---

## 1. Project Overview & Architecture
- **Project Name**: `{name}`
- **Core Domain**: {desc}
- **Primary Language**: `{primary_lang}`
- **Frameworks & Ecosystem**: {frameworks}
- **Architecture Pattern**: Modular separation of concerns (Core Engine / Services / UI / Data Layer).

### Language Breakdown
{lang_stats}

---

## 2. Directory Map & Key Files
```text
{info["tree"]}
```

### Key Entry Points
{entry_points}

---

## 3. Technology Stack & Manifests
- **Primary Language**: `{primary_lang}`
- **Frameworks**: `{frameworks}`
- **Testing Setup**: {"Configured (Unit/Integration)" if info["has_tests"] else "Standard test runners"}
- **CI / Workflows**: {"GitHub Actions / CI configured" if info["has_ci"] else "Local / Manual workflows"}
- **Containerization**: {"Docker container configured" if info["has_docker"] else "Host native execution"}

---

## 4. Development Workflows & Commands
Run these commands within the project root:

### Environment Setup & Dependencies
```bash
# Install dependencies
{"pip install -r requirements.txt" if primary_lang == "Python" else "npm install" if primary_lang in ["JavaScript", "TypeScript"] else "cargo build" if primary_lang == "Rust" else "go mod download" if primary_lang == "Go" else "./setup.sh"}
```

### Running the Application
```bash
# Start development runtime
{"python main.py" if primary_lang == "Python" else "npm run dev" if primary_lang in ["JavaScript", "TypeScript"] else "cargo run" if primary_lang == "Rust" else "go run ." if primary_lang == "Go" else "./run.sh"}
```

### Running Tests & Quality Checks
```bash
# Execute test suite
{"pytest" if primary_lang == "Python" else "npm test" if primary_lang in ["JavaScript", "TypeScript"] else "cargo test" if primary_lang == "Rust" else "go test ./..." if primary_lang == "Go" else "make test"}
```

---

## 5. Coding Standards & AI Directives
When generating code or proposing modifications for this project:

1. **Architecture Integrity**: Keep business logic, UI layer, and API integration decoupled.
2. **Clean Code & Typing**:
   - Use explicit type annotations where supported ({primary_lang}).
   - Prefer descriptive naming conventions for functions, variables, and classes.
3. **Documentation Preservation**:
   - Preserve existing docstrings, comments, and license headers unless explicitly instructed.
4. **Error Handling & Resilience**:
   - Use structured try/except or Result pattern with clear error messages.
   - Never silence exceptions silently; log or bubble them to the UI/console.
5. **Dependency Discipline**:
   - Do not introduce heavy third-party packages if standard library or existing modules suffice.
"""
        return md.strip()

    @staticmethod
    def generate_readme(info: Dict[str, Any], custom_description: str = "") -> str:
        name = info["name"]
        primary_lang = info["primary_language"]
        frameworks = ", ".join(info["frameworks"]) if info["frameworks"] else primary_lang
        desc = custom_description or f"High-performance {primary_lang} application with modern developer experience and clean modular architecture."
        
        md = f"""# {name}

[![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)](#)
[![Language](https://img.shields.io/badge/Language-{primary_lang}-blue.svg)](#)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](#)

> {desc}

---

## ✨ Features

- ⚡ **High Performance & Modular Design**: Clean architecture tailored for scalability and developer ergonomics.
- 🛠️ **Modern Developer Tooling**: Ready-to-use workflows, dependency manifests, and environment configs.
- 🤖 **AI-Ready Context**: Includes structured `AI_CONTEXT.md` for seamless collaboration with AI coding assistants.
- 📦 **Automated Release Management**: Semantic versioning and changelog tracking built-in.

---

## 🏗️ Tech Stack

- **Core Language**: `{primary_lang}`
- **Frameworks & Libraries**: {frameworks}
- **Packaging / Dependency Manager**: {"Pip / PyProject" if primary_lang == "Python" else "NPM / Yarn" if primary_lang in ["JavaScript", "TypeScript"] else "Cargo" if primary_lang == "Rust" else "Go Modules"}

---

## 🚀 Quickstart Guide

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/{name}.git
cd {name}
```

### 2. Install Dependencies
```bash
{"pip install -r requirements.txt" if primary_lang == "Python" else "npm install" if primary_lang in ["JavaScript", "TypeScript"] else "cargo build" if primary_lang == "Rust" else "go mod download" if primary_lang == "Go" else "./setup.sh"}
```

### 3. Run the Application
```bash
{"python main.py" if primary_lang == "Python" else "npm start" if primary_lang in ["JavaScript", "TypeScript"] else "cargo run" if primary_lang == "Rust" else "go run ." if primary_lang == "Go" else "./run.sh"}
```

---

## 📂 Project Structure

```text
{info["tree"]}
```

---

## 🧪 Testing

Execute test suites with:
```bash
{"pytest" if primary_lang == "Python" else "npm test" if primary_lang in ["JavaScript", "TypeScript"] else "cargo test" if primary_lang == "Rust" else "go test ./..." if primary_lang == "Go" else "make test"}
```

---

## 📝 Semantic Versioning & Releases

This project follows [Semantic Versioning (SemVer)](https://semver.org/).
Consult [CHANGELOG.md](CHANGELOG.md) for version release notes.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
"""
        return md.strip()

    @staticmethod
    def generate_changelog(info: Dict[str, Any]) -> str:
        name = info["name"]
        date_today = datetime.now().strftime("%Y-%m-%d")
        git_info = info.get("git", {})
        recent_commits = git_info.get("recent_commits", [])

        # Categorize commits
        notes = SemVerManager.generate_release_notes_from_commits(
            recent_commits, version_tag="v1.0.0"
        ) if recent_commits else ""

        md = f"""# Changelog

All notable changes to **{name}** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Initial project scaffolding and modular directory structure.
- Comprehensive AI assistant context file (`AI_CONTEXT.md`).
- Developer documentation and configuration.

### Changed
- Refactored core modules for enhanced maintainability.

### Fixed
- General bug fixes and stability improvements.

---

## [1.0.0] - {date_today}

### Added
- Initial release of **{name}**.
- Core features and runtime workflows.
"""
        if notes:
            md += f"\n\n### Commit History Highlights\n{notes}\n"

        return md.strip()

    @staticmethod
    def write_context_files(project_path: str, files: Dict[str, str], 
                             backup_existing: bool = True) -> Dict[str, str]:
        """Write AI_CONTEXT.md, README.md, and CHANGELOG.md to target directory."""
        results = {}
        for filename in ["AI_CONTEXT.md", "README.md", "CHANGELOG.md"]:
            if filename in files:
                target_file = os.path.join(project_path, filename)
                if os.path.exists(target_file) and backup_existing:
                    backup_name = f"{filename}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    backup_path = os.path.join(project_path, backup_name)
                    try:
                        with open(target_file, "r", encoding="utf-8") as rf:
                            content = rf.read()
                        with open(backup_path, "w", encoding="utf-8") as wf:
                            wf.write(content)
                        results[filename + "_backup"] = backup_path
                    except Exception:
                        pass

                with open(target_file, "w", encoding="utf-8") as f:
                    f.write(files[filename])
                results[filename] = target_file

        return results
