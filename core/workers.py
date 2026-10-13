import os
import traceback
from typing import Optional, List, Dict, Any
from PySide6.QtCore import QThread, Signal
from core.github_client import GitHubClient
from core.git_manager import GitManager
from core.ai_context_generator import AIContextGenerator
from core.db import save_cached_repos, log_activity

class BaseWorker(QThread):
    progress = Signal(int, str)    # percent (0-100), message
    log = Signal(str, str)          # message, level (INFO, SUCCESS, WARNING, ERROR)
    failed = Signal(str)           # error message
    succeeded = Signal(object)     # result payload

    def __init__(self, parent=None):
        super().__init__(parent)

    def emit_log(self, msg: str, level: str = "INFO"):
        self.log.emit(msg, level)
        log_activity(self.__class__.__name__, msg, level)


class FetchReposWorker(BaseWorker):
    def __init__(self, client: GitHubClient, profile_id: int, 
                 repo_type: str = "all", sort: str = "updated", parent=None):
        super().__init__(parent)
        self.client = client
        self.profile_id = profile_id
        self.repo_type = repo_type
        self.sort = sort

    def run(self):
        try:
            self.emit_log(f"Fetching repositories ({self.repo_type}, sorted by {self.sort})...", "INFO")
            repos = self.client.list_repositories(repo_type=self.repo_type, sort=self.sort)
            
            # Cache in SQLite
            save_cached_repos(self.profile_id, repos)
            self.emit_log(f"Successfully retrieved and cached {len(repos)} repositories.", "SUCCESS")
            self.succeeded.emit(repos)
        except Exception as e:
            err = f"Failed to fetch repositories: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)


class CloneRepoWorker(BaseWorker):
    def __init__(self, clone_url: str, target_dir: str, token: Optional[str] = None,
                 branch: Optional[str] = None, depth: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.clone_url = clone_url
        self.target_dir = target_dir
        self.token = token
        self.branch = branch
        self.depth = depth

    def run(self):
        try:
            self.emit_log(f"Initiating clone of {self.clone_url} into {self.target_dir}...", "INFO")
            self.progress.emit(10, "Connecting to remote...")

            def progress_cb(pct, status):
                self.progress.emit(pct, status)
                if pct % 25 == 0:
                    self.emit_log(f"Git: {status}", "INFO")

            repo = GitManager.clone_repository(
                clone_url=self.clone_url,
                target_dir=self.target_dir,
                token=self.token,
                branch=self.branch,
                depth=self.depth,
                progress_callback=progress_cb
            )

            self.progress.emit(100, "Clone completed!")
            self.emit_log(f"Repository successfully cloned to {self.target_dir}", "SUCCESS")
            self.succeeded.emit(self.target_dir)
        except Exception as e:
            err = f"Clone failed: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)


class UploadProjectWorker(BaseWorker):
    def __init__(self, local_path: str, repo_name: str, description: str,
                 is_private: bool, client: GitHubClient, token: str,
                 commit_message: str = "Initial commit via GitHub Manager",
                 branch: str = "main", parent=None):
        super().__init__(parent)
        self.local_path = local_path
        self.repo_name = repo_name
        self.description = description
        self.is_private = is_private
        self.client = client
        self.token = token
        self.commit_message = commit_message
        self.branch = branch

    def run(self):
        try:
            self.emit_log(f"Creating GitHub repository '{self.repo_name}'...", "INFO")
            self.progress.emit(20, "Creating remote repository on GitHub...")

            # 1. Create repo on GitHub
            remote_repo = self.client.create_repository(
                name=self.repo_name,
                description=self.description,
                private=self.is_private,
                auto_init=False
            )
            clone_url = remote_repo["clone_url"]
            self.emit_log(f"GitHub repository created at {remote_repo['html_url']}", "SUCCESS")

            # 2. Get user info for git author
            user = self.client.get_authenticated_user()
            user_name = user.get("name") or user.get("login")
            user_email = f"{user.get('login')}@users.noreply.github.com"

            # 3. Local Git Init & Push
            self.progress.emit(50, "Staging and committing files...")

            def progress_cb(status):
                self.emit_log(status, "INFO")

            GitManager.init_and_push(
                local_path=self.local_path,
                remote_url=clone_url,
                commit_message=self.commit_message,
                branch=self.branch,
                token=self.token,
                user_name=user_name,
                user_email=user_email,
                progress_callback=progress_cb
            )

            self.progress.emit(100, "Project successfully pushed!")
            self.emit_log(f"Project '{self.repo_name}' uploaded successfully!", "SUCCESS")
            self.succeeded.emit(remote_repo)
        except Exception as e:
            err = f"Failed to upload project: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)


class FetchReleasesWorker(BaseWorker):
    def __init__(self, client: GitHubClient, full_name: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.full_name = full_name

    def run(self):
        try:
            self.emit_log(f"Fetching releases and tags for {self.full_name}...", "INFO")
            releases = self.client.list_releases(self.full_name)
            tags = self.client.list_tags(self.full_name)
            self.emit_log(f"Found {len(releases)} releases and {len(tags)} tags.", "SUCCESS")
            self.succeeded.emit({"releases": releases, "tags": tags})
        except Exception as e:
            err = f"Failed to fetch releases: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)


class CreateReleaseWorker(BaseWorker):
    def __init__(self, client: GitHubClient, full_name: str, tag_name: str,
                 title: str, body: str, draft: bool = False, prerelease: bool = False,
                 target_commitish: str = "main", asset_paths: Optional[List[str]] = None,
                 parent=None):
        super().__init__(parent)
        self.client = client
        self.full_name = full_name
        self.tag_name = tag_name
        self.title = title
        self.body = body
        self.draft = draft
        self.prerelease = prerelease
        self.target_commitish = target_commitish
        self.asset_paths = asset_paths or []

    def run(self):
        try:
            self.emit_log(f"Creating release '{self.tag_name}' for {self.full_name}...", "INFO")
            self.progress.emit(25, "Creating GitHub Release...")

            def progress_cb(msg):
                self.emit_log(msg, "INFO")

            rel = self.client.create_release(
                full_name=self.full_name,
                tag_name=self.tag_name,
                name=self.title,
                body=self.body,
                draft=self.draft,
                prerelease=self.prerelease,
                target_commitish=self.target_commitish,
                asset_paths=self.asset_paths,
                progress_callback=progress_cb
            )

            self.progress.emit(100, "Release created successfully!")
            self.emit_log(f"Release {self.tag_name} created: {rel.get('html_url')}", "SUCCESS")
            self.succeeded.emit(rel)
        except Exception as e:
            err = f"Failed to create release: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)


class DownloadArchiveWorker(BaseWorker):
    def __init__(self, client: GitHubClient, full_name: str, ref: str,
                 dest_path: str, archive_format: str = "zipball", parent=None):
        super().__init__(parent)
        self.client = client
        self.full_name = full_name
        self.ref = ref
        self.dest_path = dest_path
        self.archive_format = archive_format

    def run(self):
        try:
            self.emit_log(f"Downloading {self.archive_format} for {self.full_name}@{self.ref}...", "INFO")

            def progress_cb(pct, msg):
                self.progress.emit(pct, msg)

            self.client.download_archive(
                full_name=self.full_name,
                ref=self.ref,
                dest_path=self.dest_path,
                archive_format=self.archive_format,
                progress_callback=progress_cb
            )

            self.emit_log(f"Archive saved to {self.dest_path}", "SUCCESS")
            self.succeeded.emit(self.dest_path)
        except Exception as e:
            err = f"Archive download failed: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)


class DownloadAssetWorker(BaseWorker):
    def __init__(self, client: GitHubClient, asset_url: str, dest_path: str, parent=None):
        super().__init__(parent)
        self.client = client
        self.asset_url = asset_url
        self.dest_path = dest_path

    def run(self):
        try:
            self.emit_log(f"Downloading asset to {self.dest_path}...", "INFO")

            def progress_cb(pct, msg):
                self.progress.emit(pct, msg)

            self.client.download_asset(
                asset_download_url=self.asset_url,
                dest_path=self.dest_path,
                progress_callback=progress_cb
            )

            self.emit_log(f"Asset downloaded to {self.dest_path}", "SUCCESS")
            self.succeeded.emit(self.dest_path)
        except Exception as e:
            err = f"Asset download failed: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)


class GenerateAIContextWorker(BaseWorker):
    def __init__(self, project_path: str, custom_description: str = "", parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.custom_description = custom_description

    def run(self):
        try:
            self.emit_log(f"Analyzing project directory {self.project_path}...", "INFO")
            self.progress.emit(25, "Scanning file system & dependencies...")

            result = AIContextGenerator.generate_all(self.project_path, self.custom_description)

            self.progress.emit(100, "Context files generated!")
            self.emit_log(f"Successfully generated AI context files for {result['info']['name']}", "SUCCESS")
            self.succeeded.emit(result)
        except Exception as e:
            err = f"Context generation failed: {str(e)}"
            self.emit_log(err, "ERROR")
            self.failed.emit(err)
