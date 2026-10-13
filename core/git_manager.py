import os
import git
from typing import Optional, Callable, List, Dict, Any

class CloneProgress(git.RemoteProgress):
    def __init__(self, callback: Optional[Callable[[int, str], None]] = None):
        super().__init__()
        self.callback = callback

    def update(self, op_code, cur_count, max_count=None, message=""):
        if self.callback:
            percent = int((cur_count / max_count) * 100) if max_count else 0
            op_name = self._op_name(op_code)
            status_text = f"{op_name}: {cur_count}/{max_count or '?'} {message}".strip()
            self.callback(percent, status_text)

    def _op_name(self, op_code):
        if op_code & git.RemoteProgress.COUNTING:
            return "Counting objects"
        elif op_code & git.RemoteProgress.COMPRESSING:
            return "Compressing objects"
        elif op_code & git.RemoteProgress.WRITING:
            return "Writing objects"
        elif op_code & git.RemoteProgress.RECEIVING:
            return "Receiving objects"
        elif op_code & git.RemoteProgress.RESOLVING:
            return "Resolving deltas"
        elif op_code & git.RemoteProgress.FINDING_SOURCES:
            return "Finding sources"
        elif op_code & git.RemoteProgress.CHECKING_OUT:
            return "Checking out files"
        return "Processing"


class GitManager:
    @staticmethod
    def is_git_repo(path: str) -> bool:
        """Check if directory is a valid git repository."""
        try:
            _ = git.Repo(path)
            return True
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return False

    @staticmethod
    def clone_repository(clone_url: str, target_dir: str, token: Optional[str] = None,
                         branch: Optional[str] = None, depth: Optional[int] = None,
                         progress_callback: Optional[Callable[[int, str], None]] = None) -> git.Repo:
        """Clone a remote repository to target directory with progress reporting."""
        auth_url = clone_url
        if token and clone_url.startswith("https://"):
            # Embed token for authenticated cloning of private repos
            auth_url = clone_url.replace("https://", f"https://x-access-token:{token}@")

        kwargs = {}
        if branch:
            kwargs['branch'] = branch
        if depth and depth > 0:
            kwargs['depth'] = depth
        if progress_callback:
            kwargs['progress'] = CloneProgress(progress_callback)

        os.makedirs(target_dir, exist_ok=True)
        repo = git.Repo.clone_from(auth_url, target_dir, **kwargs)
        
        # Reset origin url to clean clone_url so personal access token isn't stored in plain text remote config
        if token and clone_url.startswith("https://"):
            try:
                origin = repo.remote("origin")
                origin.set_url(clone_url)
            except Exception:
                pass

        return repo

    @staticmethod
    def init_and_push(local_path: str, remote_url: str, commit_message: str = "Initial commit",
                      branch: str = "main", token: Optional[str] = None,
                      user_name: Optional[str] = None, user_email: Optional[str] = None,
                      progress_callback: Optional[Callable[[str], None]] = None) -> git.Repo:
        """Initialize a local directory as a Git repository, commit files, and push to remote."""
        if progress_callback:
            progress_callback(f"Checking repository at {local_path}...")

        if GitManager.is_git_repo(local_path):
            repo = git.Repo(local_path)
            if progress_callback:
                progress_callback("Found existing Git repository.")
        else:
            if progress_callback:
                progress_callback("Initializing new Git repository...")
            repo = git.Repo.init(local_path)

        # Configure user if provided and missing
        with repo.config_writer() as config:
            if user_name and not config.has_option("user", "name"):
                config.set_value("user", "name", user_name)
            if user_email and not config.has_option("user", "email"):
                config.set_value("user", "email", user_email)

        # Ensure default .gitignore if none exists
        gitignore_path = os.path.join(local_path, ".gitignore")
        if not os.path.exists(gitignore_path):
            if progress_callback:
                progress_callback("Generating sensible default .gitignore...")
            with open(gitignore_path, "w", encoding="utf-8") as f:
                f.write("# Common ignore patterns\n__pycache__/\n*.py[cod]\nnode_modules/\n.env\n.DS_Store\nThumbs.db\n.venv/\nvenv/\nbuild/\ndist/\n*.egg-info/\n*.log\n")

        # Stage all changes
        if progress_callback:
            progress_callback("Staging all files...")
        repo.git.add(A=True)

        # Commit if there are changes
        if repo.is_dirty(untracked_files=True) or len(repo.index.diff("HEAD")) > 0 if repo.heads else True:
            try:
                if progress_callback:
                    progress_callback(f"Committing changes: '{commit_message}'...")
                repo.index.commit(commit_message)
            except Exception as e:
                # Might have already committed
                if progress_callback:
                    progress_callback(f"Note on commit: {e}")

        # Set or rename current branch to desired branch
        try:
            if repo.active_branch.name != branch:
                if progress_callback:
                    progress_callback(f"Setting branch to '{branch}'...")
                repo.git.branch("-M", branch)
        except Exception:
            try:
                repo.git.checkout("-b", branch)
            except Exception:
                pass

        # Remote setup
        auth_remote_url = remote_url
        if token and remote_url.startswith("https://"):
            auth_remote_url = remote_url.replace("https://", f"https://x-access-token:{token}@")

        if "origin" in [r.name for r in repo.remotes]:
            origin = repo.remote("origin")
            origin.set_url(auth_remote_url)
        else:
            origin = repo.create_remote("origin", auth_remote_url)

        if progress_callback:
            progress_callback(f"Pushing to remote origin/{branch}...")

        # Push to remote
        origin.push(refspec=f"{branch}:{branch}", set_upstream=True, force=True)

        # Clean token from stored remote URL
        if token and remote_url.startswith("https://"):
            try:
                origin.set_url(remote_url)
            except Exception:
                pass

        if progress_callback:
            progress_callback("Push completed successfully!")

        return repo

    @staticmethod
    def get_repo_details(local_path: str) -> Dict[str, Any]:
        """Get summary info about a local repository."""
        if not GitManager.is_git_repo(local_path):
            return {"is_git": False}

        repo = git.Repo(local_path)
        active_branch = repo.active_branch.name if not repo.head.is_detached else "DETACHED"
        remotes = {r.name: r.url for r in repo.remotes}
        is_dirty = repo.is_dirty(untracked_files=True)
        
        last_commit = None
        if repo.heads:
            try:
                c = repo.head.commit
                last_commit = {
                    "hexsha": c.hexsha[:7],
                    "message": c.message.strip(),
                    "author": c.author.name,
                    "date": c.committed_datetime.isoformat()
                }
            except Exception:
                pass

        tags = [t.name for t in repo.tags]

        return {
            "is_git": True,
            "branch": active_branch,
            "remotes": remotes,
            "is_dirty": is_dirty,
            "last_commit": last_commit,
            "tags": tags,
            "untracked_count": len(repo.untracked_files)
        }

    @staticmethod
    def get_commits_for_changelog(local_path: str, max_count: int = 100, 
                                  since_tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve commit history for changelog/release notes generation."""
        if not GitManager.is_git_repo(local_path):
            return []

        repo = git.Repo(local_path)
        commits_data = []

        rev = "HEAD"
        if since_tag:
            try:
                rev = f"{since_tag}..HEAD"
            except Exception:
                rev = "HEAD"

        try:
            commits = list(repo.iter_commits(rev=rev, max_count=max_count))
            for c in commits:
                commits_data.append({
                    "sha": c.hexsha[:8],
                    "full_sha": c.hexsha,
                    "summary": c.summary,
                    "message": c.message.strip(),
                    "author": c.author.name,
                    "email": c.author.email,
                    "date": c.committed_datetime.strftime("%Y-%m-%d")
                })
        except Exception:
            pass

        return commits_data

    @staticmethod
    def create_and_push_tag(local_path: str, tag_name: str, message: str = "",
                            push_remote: bool = True, token: Optional[str] = None) -> bool:
        """Create a local Git tag and optionally push to remote origin."""
        if not GitManager.is_git_repo(local_path):
            raise ValueError(f"{local_path} is not a valid Git repository.")

        repo = git.Repo(local_path)
        tag = repo.create_tag(tag_name, message=message or f"Release {tag_name}")

        if push_remote and "origin" in [r.name for r in repo.remotes]:
            origin = repo.remote("origin")
            orig_url = origin.url
            if token and orig_url.startswith("https://"):
                auth_url = orig_url.replace("https://", f"https://x-access-token:{token}@")
                origin.set_url(auth_url)
            
            try:
                origin.push(tag_name)
            finally:
                if token and orig_url.startswith("https://"):
                    origin.set_url(orig_url)

        return True
