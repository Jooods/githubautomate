import os
import requests
from typing import List, Dict, Any, Optional, Callable
from github import Github, Auth, GithubException

class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self._gh: Optional[Github] = None
        if token:
            self.connect(token)

    def connect(self, token: str):
        self.token = token
        try:
            # PyGithub 2.0+ uses Auth.Token
            auth = Auth.Token(token)
            self._gh = Github(auth=auth)
        except Exception:
            # Fallback for older PyGithub
            self._gh = Github(token)

    @property
    def client(self) -> Github:
        if not self._gh:
            raise ValueError("GitHub client is not initialized with a token.")
        return self._gh

    def get_authenticated_user(self) -> Dict[str, Any]:
        """Verify token and return authenticated user details."""
        u = self.client.get_user()

        # Safely extract rate limit — PyGithub 2.10 uses rate.resources.core
        rate_remaining = 0
        rate_limit = 0
        rate_reset = None
        try:
            rate = self.client.get_rate_limit()
            # PyGithub 2.10: RateLimitOverview has .resources.core (not .core directly)
            resources = getattr(rate, 'resources', None)
            core = getattr(resources, 'core', None) if resources else None
            # Fallback: older builds may expose .rate directly
            if core is None:
                core = getattr(rate, 'rate', None)
            if core:
                rate_remaining = getattr(core, 'remaining', 0)
                rate_limit = getattr(core, 'limit', 0)
                reset_dt = getattr(core, 'reset', None)
                rate_reset = reset_dt.isoformat() if reset_dt else None
        except Exception:
            pass

        return {
            "login": u.login,
            "name": u.name or u.login,
            "avatar_url": u.avatar_url,
            "bio": u.bio or "",
            "html_url": u.html_url,
            "public_repos": u.public_repos,
            "total_private_repos": getattr(u, 'total_private_repos', 0) or 0,
            "followers": u.followers,
            "following": u.following,
            "rate_limit_remaining": rate_remaining,
            "rate_limit_limit": rate_limit,
            "rate_limit_reset": rate_reset
        }

    def list_repositories(self, repo_type: str = "all", sort: str = "updated", 
                          direction: str = "desc") -> List[Dict[str, Any]]:
        """List repositories for authenticated user."""
        user = self.client.get_user()
        # repo_type can be 'all', 'owner', 'public', 'private', 'member'
        repos = user.get_repos(type=repo_type, sort=sort, direction=direction)
        
        repo_list = []
        for r in repos:
            repo_list.append({
                "id": r.id,
                "name": r.name,
                "full_name": r.full_name,
                "owner": r.owner.login if r.owner else "",
                "description": r.description or "",
                "is_private": r.private,
                "is_fork": r.fork,
                "stars": r.stargazers_count,
                "forks": r.forks_count,
                "open_issues": r.open_issues_count,
                "default_branch": r.default_branch or "main",
                "language": r.language or "Unknown",
                "html_url": r.html_url,
                "clone_url": r.clone_url,
                "ssh_url": r.ssh_url,
                "size": r.size,
                "pushed_at": r.pushed_at.isoformat() if r.pushed_at else "",
                "updated_at": r.updated_at.isoformat() if r.updated_at else "",
                "archived": r.archived,
                "has_wiki": r.has_wiki,
                "license": r.license.name if r.license else None
            })
        return repo_list

    def get_repository(self, full_name: str):
        """Get PyGithub Repository object."""
        return self.client.get_repo(full_name)

    def create_repository(self, name: str, description: str = "", private: bool = True,
                          auto_init: bool = False, org_name: Optional[str] = None) -> Dict[str, Any]:
        """Create a new repository under user account or organization."""
        if org_name:
            target = self.client.get_organization(org_name)
        else:
            target = self.client.get_user()

        repo = target.create_repo(
            name=name,
            description=description,
            private=private,
            auto_init=auto_init
        )
        return {
            "id": repo.id,
            "name": repo.name,
            "full_name": repo.full_name,
            "html_url": repo.html_url,
            "clone_url": repo.clone_url,
            "ssh_url": repo.ssh_url,
            "default_branch": repo.default_branch or "main"
        }

    def list_releases(self, full_name: str) -> List[Dict[str, Any]]:
        """List releases of a repository."""
        repo = self.get_repository(full_name)
        releases = repo.get_releases()
        results = []
        for rel in releases:
            assets = []
            for a in rel.get_assets():
                assets.append({
                    "id": a.id,
                    "name": a.name,
                    "size": a.size,
                    "download_count": a.download_count,
                    "browser_download_url": a.browser_download_url,
                    "content_type": a.content_type
                })
            results.append({
                "id": rel.id,
                "tag_name": rel.tag_name,
                "title": rel.title or rel.tag_name,
                "body": rel.body or "",
                "draft": rel.draft,
                "prerelease": rel.prerelease,
                "created_at": rel.created_at.isoformat() if rel.created_at else "",
                "published_at": rel.published_at.isoformat() if rel.published_at else "",
                "html_url": rel.html_url,
                "tarball_url": rel.tarball_url,
                "zipball_url": rel.zipball_url,
                "assets": assets
            })
        return results

    def create_release(self, full_name: str, tag_name: str, name: str, body: str,
                       draft: bool = False, prerelease: bool = False,
                       target_commitish: str = "main",
                       asset_paths: Optional[List[str]] = None,
                       progress_callback: Optional[Callable[[str], None]] = None) -> Dict[str, Any]:
        """Create a new release and optionally upload assets."""
        repo = self.get_repository(full_name)
        
        if progress_callback:
            progress_callback(f"Creating release {tag_name}...")
            
        release = repo.create_git_release(
            tag=tag_name,
            name=name,
            message=body,
            draft=draft,
            prerelease=prerelease,
            target_commitish=target_commitish
        )

        if asset_paths:
            for path in asset_paths:
                if os.path.exists(path):
                    filename = os.path.basename(path)
                    if progress_callback:
                        progress_callback(f"Uploading asset: {filename}...")
                    release.upload_asset(path=path, name=filename)

        return {
            "id": release.id,
            "tag_name": release.tag_name,
            "title": release.title,
            "html_url": release.html_url
        }

    def delete_release(self, full_name: str, release_id: int):
        """Delete a release."""
        repo = self.get_repository(full_name)
        release = repo.get_release(release_id)
        release.delete_release()

    def list_tags(self, full_name: str) -> List[Dict[str, Any]]:
        """List git tags for a repository."""
        repo = self.get_repository(full_name)
        tags = repo.get_tags()
        results = []
        for t in tags:
            results.append({
                "name": t.name,
                "commit_sha": t.commit.sha,
                "zipball_url": t.zipball_url,
                "tarball_url": t.tarball_url
            })
        return results

    def download_archive(self, full_name: str, ref: str, dest_path: str,
                         archive_format: str = "zipball",
                         progress_callback: Optional[Callable[[int, str], None]] = None):
        """Download zipball/tarball archive of a ref (tag, branch, commit)."""
        repo = self.get_repository(full_name)
        url = repo.get_archive_link(archive_format, ref)
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        response = requests.get(url, headers=headers, stream=True)
        response.raise_for_status()

        total_length = response.headers.get('content-length')
        total_bytes = int(total_length) if total_length else 0
        downloaded = 0

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes > 0 and progress_callback:
                        percent = int((downloaded / total_bytes) * 100)
                        progress_callback(percent, f"Downloaded {downloaded // 1024} KB / {total_bytes // 1024} KB")
                    elif progress_callback:
                        progress_callback(50, f"Downloaded {downloaded // 1024} KB...")

        if progress_callback:
            progress_callback(100, "Download completed!")

    def download_asset(self, asset_download_url: str, dest_path: str,
                       progress_callback: Optional[Callable[[int, str], None]] = None):
        """Download a release asset with streaming progress."""
        headers = {
            "Accept": "application/octet-stream"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        response = requests.get(asset_download_url, headers=headers, stream=True, allow_redirects=True)
        response.raise_for_status()

        total_length = response.headers.get('content-length')
        total_bytes = int(total_length) if total_length else 0
        downloaded = 0

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes > 0 and progress_callback:
                        percent = int((downloaded / total_bytes) * 100)
                        progress_callback(percent, f"Downloaded {downloaded // 1024} KB / {total_bytes // 1024} KB")
                    elif progress_callback:
                        progress_callback(50, f"Downloaded {downloaded // 1024} KB...")

        if progress_callback:
            progress_callback(100, "Asset download completed!")

    def star_repository(self, full_name: str, star: bool = True):
        """Star or unstar repository."""
        repo = self.get_repository(full_name)
        user = self.client.get_user()
        if star:
            user.add_to_starred(repo)
        else:
            user.remove_from_starred(repo)

    def is_starred(self, full_name: str) -> bool:
        """Check if repository is starred by authenticated user."""
        repo = self.get_repository(full_name)
        user = self.client.get_user()
        return user.has_in_starred(repo)
