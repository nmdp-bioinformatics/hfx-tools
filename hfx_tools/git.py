
from __future__ import annotations

import time
import requests
import webbrowser
from github import Github, Auth
from git import Repo
from pathlib import Path

CLIENT_ID = "Ov23linx1WR9QLjRQBNk"
SCOPE = "repo"

# ---------- GitHub API ----------

def get_github_client(token: str) -> Github:
    """Authenticate with GitHub using a personal access token."""
    auth = Auth.Token(token)
    return Github(auth=auth)

def fork_repo(token: str, repo_owner: str, repo_name: str):
    """Fork a repository into the authenticated user's account."""
    gh = get_github_client(token)

    source_repo = gh.get_repo(f"{repo_owner}/{repo_name}")
    user = gh.get_user()
    fork = user.create_fork(source_repo)
    return fork

def create_pull_request(
    token: str,
    repo_owner: str,
    repo_name: str,
    head_branch: str,
    title: str = "Automated PR",
    body: str = ""
):
    """
    Create a pull request via GitHub API.
    head_branch should be in format: 'username:branch'
    """
    gh = get_github_client(token)
    repo = gh.get_repo(f"{repo_owner}/{repo_name}")

    pr = repo.create_pull(
        title=title,
        body=body,
        head=head_branch,
        base=repo.default_branch
    )
    return pr


# ---------- Local Git (GitPython) ----------

def login_into_github():
    # 1. Request device code
    r = requests.post(
        "https://github.com/login/device/code",
        data={
            "client_id": CLIENT_ID,
            "scope": SCOPE,
        },
        headers={"Accept": "application/json"},
    )
    r.raise_for_status()
    flow = r.json()

    # 2. Opem browser to let user login
    webbrowser.open(flow["verification_uri"])

    return flow

def await_token(flow):

    # 3. Poll for token
    device_code = flow["device_code"]
    interval = flow["interval"]

    while True:
        time.sleep(interval)

        r = requests.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": CLIENT_ID,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            headers={"Accept": "application/json"},
        )
        data = r.json()

        if "access_token" in data:
            return data["access_token"]

        if data.get("error") == "authorization_pending":
            continue

        raise RuntimeError(f"OAuth failed: {data}")

def clone_repo(token: str, repo_owner: str, repo_name: str, output_dir: Path) -> Repo:
    """Clone a repository locally."""

    repo_url = f"https://{token}@github.com/{repo_owner}/{repo_name}.git"
    return Repo.clone_from(repo_url, output_dir)

def commit_and_push_repo(repo: Repo, commit_msg: str, branch: str | None = None):
    """Commit changes and push to remote."""
    if not repo.is_dirty(untracked_files=True):
        return False

    repo.git.add(A=True)
    repo.index.commit(commit_msg)

    # Determine branch safely
    if branch is None:
        branch = repo.active_branch.name

    origin = repo.remote(name="origin")
    
    return origin.push(refspec=f"{branch}:{branch}")