import os
import unittest
from core.db import init_db, save_profile, get_profiles, set_active_profile, get_active_profile, delete_profile, set_setting, get_setting, save_cached_repos, get_cached_repos
from core.semver_manager import SemVer, SemVerManager
from core.ai_context_generator import AIContextGenerator, ProjectAnalyzer

class TestGitHubManagerCore(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_semver_parsing_and_bumping(self):
        sv = SemVer.parse("v1.2.3")
        self.assertIsNotNone(sv)
        self.assertEqual(sv.major, 1)
        self.assertEqual(sv.minor, 2)
        self.assertEqual(sv.patch, 3)
        self.assertTrue(sv.has_v_prefix)

        # Bumps
        self.assertEqual(sv.bump_patch().format(), "v1.2.4")
        self.assertEqual(sv.bump_minor().format(), "v1.3.0")
        self.assertEqual(sv.bump_major().format(), "v2.0.0")
        self.assertEqual(sv.bump_prerelease("rc").format(), "v1.2.4-rc.1")

        # Static bumps
        self.assertEqual(SemVerManager.bump_tag("v2.10.5", "patch"), "v2.10.6")
        self.assertEqual(SemVerManager.bump_tag("v2.10.5", "minor"), "v2.11.0")
        self.assertEqual(SemVerManager.bump_tag("v2.10.5", "major"), "v3.0.0")

        # Tag sorting
        tags = ["v1.0.0", "v2.0.0", "v1.1.0", "v1.0.1", "v2.1.0-rc.1", "v2.1.0"]
        sorted_tags = SemVerManager.sort_tags(tags, reverse=True)
        self.assertEqual(sorted_tags[0], "v2.1.0")
        self.assertEqual(sorted_tags[1], "v2.1.0-rc.1")
        self.assertEqual(sorted_tags[2], "v2.0.0")

        # Release notes generation
        dummy_commits = [
            {"summary": "feat(auth): add fine-grained PAT support", "sha": "a1b2c3d", "author": "dev"},
            {"summary": "fix(clone): handle ssh remote url with custom port", "sha": "b2c3d4e", "author": "dev"},
            {"summary": "docs: update README with SemVer instructions", "sha": "c3d4e5f", "author": "dev"},
            {"summary": "perf: optimize sqlite cache queries", "sha": "d4e5f6a", "author": "dev"}
        ]
        notes = SemVerManager.generate_release_notes_from_commits(dummy_commits, "v1.1.0")
        self.assertIn("New Features", notes)
        self.assertIn("Bug Fixes", notes)
        self.assertIn("Documentation", notes)
        self.assertIn("Performance Improvements", notes)
        self.assertIn("fine-grained PAT support", notes)

    def test_database_operations(self):
        # Settings
        set_setting("test_key", {"theme": "dark", "zoom": 1.2})
        val = get_setting("test_key")
        self.assertEqual(val.get("theme"), "dark")

        # Profile lifecycle
        pid = save_profile("Test Profile", "ghp_dummytoken123", "testuser", "https://avatar.url", "Test bio")
        set_active_profile(pid)
        active = get_active_profile()
        self.assertEqual(active["username"], "testuser")

        # Cache repos
        sample_repos = [{
            "full_name": "testuser/test-repo",
            "name": "test-repo",
            "owner": "testuser",
            "description": "A sample repository",
            "is_private": True,
            "stars": 42,
            "forks": 5,
            "open_issues": 1,
            "default_branch": "main",
            "language": "Python",
            "html_url": "https://github.com/testuser/test-repo",
            "clone_url": "https://github.com/testuser/test-repo.git",
            "ssh_url": "git@github.com:testuser/test-repo.git",
            "size": 1024,
            "updated_at": "2026-10-13T12:00:00Z"
        }]
        save_cached_repos(pid, sample_repos)
        cached = get_cached_repos(pid)
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0]["name"], "test-repo")
        self.assertEqual(cached[0]["stars"], 42)

        # Cleanup
        delete_profile(pid)
        self.assertEqual(len(get_cached_repos(pid)), 0)

    def test_ai_context_generator_on_current_folder(self):
        curr_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        analyzer = ProjectAnalyzer(curr_dir)
        info = analyzer.analyze()
        self.assertIn("Python", info["languages"])
        self.assertIn("PySide / PyQt", info["frameworks"])

        results = AIContextGenerator.generate_all(curr_dir, "Desktop GitHub Repository Manager")
        self.assertIn("AI_CONTEXT.md", results)
        self.assertIn("README.md", results)
        self.assertIn("CHANGELOG.md", results)

        ai_ctx = results["AI_CONTEXT.md"]
        self.assertIn("AI Context Blueprint", ai_ctx)
        self.assertIn("Directory Map & Key Files", ai_ctx)
        self.assertIn("Development Workflows & Commands", ai_ctx)

if __name__ == "__main__":
    unittest.main()
