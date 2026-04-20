from __future__ import annotations

import os
import shutil
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
from .git import *

phycus_owner = "nmdp-bioinformatics"
phycus_repo_name = "phycus"

def submit_hfx_to_phycus(token: str, hfx_file: Path):
  submission_msg = f"HFX submission of \"{os.path.basename(hfx_file)}\""

  print("Starting cleanup of TMP directory (if it exists)")
  shutil.rmtree("TMP", True)
  print("TMP directory removed (or did not exist)")

  print(f"Forking repository: {phycus_owner}/{phycus_repo_name}")
  fork = fork_repo(token, phycus_owner, phycus_repo_name)
  print(f"Fork created at: {fork.full_name} (owner: {fork.owner.login})")

  print(f"Cloning forked repository into TMP directory")
  cloned_repo = clone_repo(token, fork.owner.login, phycus_repo_name, "TMP")
  print("Repository successfully cloned into TMP")

  print(f"Copying HFX file into submission folder: TMP/submission")
  shutil.copy(hfx_file, "TMP/submission")
  print("HFX file copied successfully")

  print("Committing and pushing repository changes")
  pushed = commit_and_push_repo(cloned_repo, submission_msg)
  print(f"Changes committed and pushed successfully")

  print("Creating pull request")
  pr = create_pull_request(
      token,
      phycus_owner,
      phycus_repo_name,
      head_branch=f"{fork.owner.login}:{fork.default_branch}",
      title=submission_msg,
      body=submission_msg
  )
  print(f"Pull request created successfully to: {pr.html_url}")

  print("Cleaning up TMP directory after completion")
  shutil.rmtree("TMP")
  print("TMP directory cleanup complete")