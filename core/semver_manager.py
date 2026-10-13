import re
from typing import Optional, Tuple, List, Dict, Any

SEMVER_REGEX = re.compile(
    r'^(?P<prefix>v)?(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)'
    r'(?:-(?P<prerelease>[0-9A-Za-z.-]+))?'
    r'(?:\+(?P<build>[0-9A-Za-z.-]+))?$'
)

class SemVer:
    def __init__(self, major: int, minor: int, patch: int, 
                 prerelease: Optional[str] = None, 
                 build: Optional[str] = None, 
                 has_v_prefix: bool = True):
        self.major = major
        self.minor = minor
        self.patch = patch
        self.prerelease = prerelease
        self.build = build
        self.has_v_prefix = has_v_prefix

    @classmethod
    def parse(cls, version_str: str) -> Optional['SemVer']:
        """Parse a version string into a SemVer object."""
        if not version_str:
            return None
        match = SEMVER_REGEX.match(version_str.strip())
        if not match:
            return None
        
        has_v = bool(match.group('prefix'))
        major = int(match.group('major'))
        minor = int(match.group('minor'))
        patch = int(match.group('patch'))
        prerelease = match.group('prerelease')
        build = match.group('build')
        
        return cls(major, minor, patch, prerelease, build, has_v)

    def format(self) -> str:
        prefix = "v" if self.has_v_prefix else ""
        base = f"{prefix}{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            base += f"-{self.prerelease}"
        if self.build:
            base += f"+{self.build}"
        return base

    def __str__(self) -> str:
        return self.format()

    def bump_patch(self) -> 'SemVer':
        return SemVer(self.major, self.minor, self.patch + 1, has_v_prefix=self.has_v_prefix)

    def bump_minor(self) -> 'SemVer':
        return SemVer(self.major, self.minor + 1, 0, has_v_prefix=self.has_v_prefix)

    def bump_major(self) -> 'SemVer':
        return SemVer(self.major + 1, 0, 0, has_v_prefix=self.has_v_prefix)

    def bump_prerelease(self, label: str = "rc") -> 'SemVer':
        if not self.prerelease:
            return SemVer(self.major, self.minor, self.patch + 1, f"{label}.1", has_v_prefix=self.has_v_prefix)
        # Try to increment numeric suffix in prerelease
        parts = self.prerelease.split(".")
        if parts[-1].isdigit():
            parts[-1] = str(int(parts[-1]) + 1)
            new_pre = ".".join(parts)
        else:
            new_pre = f"{self.prerelease}.1"
        return SemVer(self.major, self.minor, self.patch, new_pre, has_v_prefix=self.has_v_prefix)

    def tuple_key(self) -> Tuple[int, int, int, int, str]:
        # Pre-releases have lower precedence than normal versions
        pre_flag = 0 if self.prerelease else 1
        return (self.major, self.minor, self.patch, pre_flag, self.prerelease or "")


class SemVerManager:
    @staticmethod
    def is_valid_semver(version_str: str) -> bool:
        return SemVer.parse(version_str) is not None

    @staticmethod
    def sort_tags(tags: List[str], reverse: bool = True) -> List[str]:
        """Sort tag strings by SemVer, placing non-semver tags at the end."""
        semvers = []
        non_semvers = []

        for t in tags:
            sv = SemVer.parse(t)
            if sv:
                semvers.append((sv, t))
            else:
                non_semvers.append(t)

        semvers.sort(key=lambda x: x[0].tuple_key(), reverse=reverse)
        non_semvers.sort(reverse=reverse)

        return [t for _, t in semvers] + non_semvers

    @staticmethod
    def get_latest_semver_tag(tags: List[str]) -> Optional[str]:
        """Find the highest SemVer tag from a list of tags."""
        sorted_tags = SemVerManager.sort_tags(tags, reverse=True)
        for t in sorted_tags:
            if SemVer.parse(t):
                return t
        return None

    @staticmethod
    def bump_tag(current_tag: str, bump_type: str = "patch") -> str:
        """Bump a tag string: patch, minor, major, prerelease."""
        sv = SemVer.parse(current_tag)
        if not sv:
            # Default fallback if empty or invalid
            return "v1.0.0"
        
        if bump_type == "major":
            return sv.bump_major().format()
        elif bump_type == "minor":
            return sv.bump_minor().format()
        elif bump_type == "prerelease":
            return sv.bump_prerelease().format()
        else: # patch
            return sv.bump_patch().format()

    @staticmethod
    def generate_release_notes_from_commits(commits: List[Dict[str, Any]], 
                                            version_tag: str = "v1.0.0", 
                                            prev_tag: Optional[str] = None) -> str:
        """Parse git commits into categorized release notes in Markdown."""
        categories = {
            "features": ("🚀 New Features", []),
            "fixes": ("🐛 Bug Fixes", []),
            "perf": ("⚡ Performance Improvements", []),
            "refactor": ("♻️ Code Refactoring", []),
            "docs": ("📝 Documentation", []),
            "maintenance": ("🔧 Maintenance & CI", []),
            "other": ("📦 Other Changes", [])
        }

        conv_regex = re.compile(r'^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^\)]+)\))?(!)?:\s*(?P<desc>.+)$')

        for c in commits:
            summary = c.get("summary", "").strip()
            sha = c.get("sha", "")
            author = c.get("author", "")
            line = f"- {summary} ({sha})" if sha else f"- {summary}"

            match = conv_regex.match(summary)
            if match:
                ctype = match.group("type").lower()
                scope = match.group("scope")
                desc = match.group("desc")
                scope_str = f"**{scope}**: " if scope else ""
                formatted_item = f"- {scope_str}{desc} ({sha})" if sha else f"- {scope_str}{desc}"

                if ctype in ["feat", "feature"]:
                    categories["features"][1].append(formatted_item)
                elif ctype in ["fix", "bugfix", "bug", "patch"]:
                    categories["fixes"][1].append(formatted_item)
                elif ctype in ["perf", "performance"]:
                    categories["perf"][1].append(formatted_item)
                elif ctype in ["refactor"]:
                    categories["refactor"][1].append(formatted_item)
                elif ctype in ["docs", "doc"]:
                    categories["docs"][1].append(formatted_item)
                elif ctype in ["chore", "build", "ci", "style", "test"]:
                    categories["maintenance"][1].append(formatted_item)
                else:
                    categories["other"][1].append(line)
            else:
                # Heuristic categorization based on keywords
                lower = summary.lower()
                if any(w in lower for w in ["add", "new", "feat", "support", "implement"]):
                    categories["features"][1].append(line)
                elif any(w in lower for w in ["fix", "bug", "resolve", "patch", "error", "issue"]):
                    categories["fixes"][1].append(line)
                elif any(w in lower for w in ["doc", "readme", "comment"]):
                    categories["docs"][1].append(line)
                elif any(w in lower for w in ["speed", "optimiz", "perf", "fast"]):
                    categories["perf"][1].append(line)
                elif any(w in lower for w in ["refactor", "cleanup", "clean"]):
                    categories["refactor"][1].append(line)
                elif any(w in lower for w in ["bump", "update", "ci", "build", "config"]):
                    categories["maintenance"][1].append(line)
                else:
                    categories["other"][1].append(line)

        # Build Markdown
        md = []
        md.append(f"## Release {version_tag}")
        if prev_tag:
            md.append(f"_Changes since {prev_tag}_\n")
        else:
            md.append("")

        has_items = False
        for key, (heading, items) in categories.items():
            if items:
                has_items = True
                md.append(f"### {heading}")
                for item in items:
                    md.append(item)
                md.append("")

        if not has_items:
            md.append("- General updates and improvements.")

        return "\n".join(md).strip()
