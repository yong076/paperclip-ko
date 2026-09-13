#!/usr/bin/env python3
"""Prepare an upstream merge in a disposable clone; publish only a draft PR."""

import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import tempfile


def command(args, cwd=None, check=True):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    env.setdefault("GIT_SSH_COMMAND", "ssh -oBatchMode=yes")
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, timeout=300)
    if check and result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result


def sync(args):
    with tempfile.TemporaryDirectory(prefix="paperclip-upstream-") as directory:
        command(["git", "clone", "--no-tags", "--single-branch", "--branch", "master", args.fork_url, directory])

        def git(*argv, check=True):
            return command(["git", "-c", "core.hooksPath=/dev/null", *argv], directory, check)

        git("fetch", "--no-tags", "--", args.upstream_url, args.upstream_ref)
        upstream = git("rev-parse", "FETCH_HEAD").stdout.strip()
        base = git("rev-parse", "HEAD").stdout.strip()
        behind = int(git("rev-list", "--count", f"HEAD..{upstream}").stdout)
        result = {"base": base, "upstream": upstream, "behind": behind}
        if behind == 0:
            return {**result, "status": "up_to_date"}

        branch = f"upstream-sync/{upstream[:12]}"
        existing = git("ls-remote", "origin", f"refs/heads/{branch}").stdout.strip()
        if existing and args.publish:
            prs = json.loads(command([
                "gh", "pr", "list", "--repo", args.fork_repo, "--head", branch,
                "--state", "all", "--json", "url,state",
            ], directory).stdout)
            if prs:
                return {**result, "status": "already_proposed", "branch": branch, "prs": prs}

        git("config", "user.name", "paperclip-ko-sync")
        git("config", "user.email", "paperclip-ko-sync@users.noreply.github.com")
        git("switch", "-c", branch)
        merge = git("merge", "--no-commit", "--no-ff", upstream, check=False)
        if merge.returncode:
            conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
            if conflicts:
                return {**result, "status": "conflicts", "conflicts": conflicts}
            raise RuntimeError(merge.stderr.strip() or merge.stdout.strip())
        if not args.publish:
            return {**result, "status": "ready", "branch": branch}

        git("commit", "-m", f"chore(sync): merge upstream {upstream[:12]}")
        # Push only this new branch. Never force, update master, or merge a PR.
        if not existing:
            git("push", "origin", f"HEAD:refs/heads/{branch}")
        body = Path(directory) / "sync-pr-body.md"
        body.write_text(f"""## Thinking Path

> - Paperclip manages AI agents and their work.
> - This fork retains Korean localization.
> - The fork is missing {behind} upstream commits.
> - A normal merge retains both histories and the fork's changes.
> - This draft proposes upstream `{upstream}` for review and CI.

## Linked Issues or Issue Description

The fork's master does not contain the upstream master snapshot above.
Expected behavior: retain Korean functionality while including upstream fixes.
Reproduction: compare the fork and upstream master commit histories.

## What Changed

- Merge {behind} upstream commits into fork master at `{base}`.

## Verification

- Git merged without conflicts in a disposable clone.
- CI and human review are required before merging. No application tests ran in the scheduler.

## Risks

- Upstream may change runtime requirements, APIs, localization, and database migrations.
- Back up the instance and verify upgrades before deployment.

## Model Used

None at execution time — deterministic Git synchronization script.

## Checklist

- [x] Problem, change, and risks are described above.
- [ ] Typecheck, tests, and build pass.
- [ ] Korean UI and migration compatibility reviewed.
- [ ] All required CI and reviewer feedback addressed.
""")
        pr = command([
            "gh", "pr", "create", "--repo", args.fork_repo, "--draft", "--base", "master",
            "--head", branch, "--title", f"chore(sync): upstream {upstream[:12]}",
            "--body-file", str(body),
        ], directory)
        return {**result, "status": "draft_created", "branch": branch, "pr_url": pr.stdout.strip()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publish", action="store_true", help="Push a clean merge and create a draft PR")
    parser.add_argument("--fork-repo", default="yong076/paperclip-ko")
    parser.add_argument("--fork-url", default="git@github.com:yong076/paperclip-ko.git")
    parser.add_argument("--upstream-url", default="https://github.com/paperclipai/paperclip.git")
    parser.add_argument("--upstream-ref", default="master")
    parser.add_argument("--status-file", type=Path)
    args = parser.parse_args()
    lock = None
    if args.status_file:
        args.status_file.parent.mkdir(parents=True, exist_ok=True)
        lock = args.status_file.with_suffix(".lock").open("w")
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "already_running"}))
            return 0
    try:
        result = sync(args)
    except Exception as error:
        result = {"status": "error", "error": str(error)}
    result["checked_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    print(text, end="")
    if args.status_file:
        temporary = args.status_file.with_suffix(".tmp")
        temporary.write_text(text)
        temporary.replace(args.status_file)
    if lock:
        lock.close()
    return int(result["status"] in {"error", "conflicts"})


if __name__ == "__main__":
    raise SystemExit(main())
