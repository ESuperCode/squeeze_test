#!/usr/bin/env python3
"""
Create a clearly labeled synthetic Git timeline for educational demonstrations.

This does NOT rewrite or copy the source repository's Git history. It creates a
new branch containing one synthetic commit per source commit, plus a CSV
manifest mapping source commit IDs and original dates to compressed demo dates.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_SOURCE = "https://github.com/epsretriever/spherex-planet-x.git"
DEFAULT_BRANCH = "synthetic-history"
DEMO_NAME = "Synthetic History Demonstration"


def run(args, cwd=None, env=None, capture=True):
    p = subprocess.run(
        args, cwd=cwd, env=env, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if p.returncode:
        detail = (p.stderr or p.stdout or "").strip()
        raise RuntimeError(f"Command failed: {' '.join(map(str, args))}\n{detail}")
    return (p.stdout or "").strip()


def parse_start(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(microsecond=0)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "start-utc must look like 2026-01-01T00:00:00Z"
        ) from exc
    if dt.tzinfo is None:
        raise argparse.ArgumentTypeError("start-utc must include Z or a UTC offset")
    return dt.astimezone(timezone.utc).replace(microsecond=0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=os.getenv("SOURCE_REPO", DEFAULT_SOURCE))
    ap.add_argument("--destination", default=os.getenv("DESTINATION_REPO"))
    ap.add_argument("--branch", default=os.getenv("DESTINATION_BRANCH", DEFAULT_BRANCH))
    ap.add_argument("--window-hours", type=float, default=float(os.getenv("WINDOW_HOURS", "24")))
    ap.add_argument("--start-utc", default=os.getenv("START_UTC", ""),
                    help="Timeline start, e.g. 2026-01-01T00:00:00Z; default is current UTC time")
    ap.add_argument("--push", action="store_true",
                    help="Push the generated branch to destination (required in CI)")
    args = ap.parse_args()

    if not args.destination:
        ap.error("--destination or DESTINATION_REPO is required")
    if not (0 < args.window_hours <= 87600):
        ap.error("--window-hours must be > 0 and <= 87600")

    start = parse_start(args.start_utc)
    duration = args.window_hours * 3600

    with tempfile.TemporaryDirectory(prefix="synthetic-history-") as td:
        td = Path(td)
        source_dir = td / "source"
        demo_dir = td / "demo"

        print("Cloning public source repository...")
        run(["git", "clone", "--quiet", "--no-tags", args.source, str(source_dir)])
        raw = run([
            "git", "-C", str(source_dir), "log", "--all", "--reverse",
            "--format=%H%x09%ct%x09%an%x09%s"
        ])
        commits = []
        for line in raw.splitlines():
            parts = line.split("\t", 3)
            if len(parts) == 4:
                sha, epoch, author, subject = parts
                commits.append((sha, int(epoch), author, subject))
        if not commits:
            raise RuntimeError("No source commits were found.")

        # Use timestamp order rather than Git's graph traversal order. This is
        # a synthetic linear teaching timeline, not a reconstruction of merges.
        commits.sort(key=lambda item: (item[1], item[0]))

        min_epoch = min(c[1] for c in commits)
        max_epoch = max(c[1] for c in commits)
        span = max_epoch - min_epoch

        mapped = []
        for i, (sha, epoch, author, subject) in enumerate(commits):
            offset = 0 if span == 0 else ((epoch - min_epoch) / span) * duration
            synthetic_dt = start + timedelta(seconds=offset)
            mapped.append((sha, epoch, author, subject, synthetic_dt))

        print(f"Found {len(commits)} source commits.")
        print(f"Mapping source date range into {args.window_hours:g} hours.")

        run(["git", "init", "--quiet", str(demo_dir)])
        run(["git", "-C", str(demo_dir), "checkout", "--quiet", "-b", args.branch])
        run(["git", "-C", str(demo_dir), "config", "user.name", "Synthetic Demo Bot"])
        run(["git", "-C", str(demo_dir), "config", "user.email", "synthetic-demo@users.noreply.github.com"])

        readme = f"""# {DEMO_NAME}

**This branch is synthetic educational data. It is not the source repository's
actual Git history and does not represent when original contributors worked.**

Source repository: {args.source}

This branch contains one generated commit per source commit. The generated
commit messages and author identity are synthetic. `timeline.csv` records the
source commit ID and original source date alongside its mapped demonstration
date. No source files or original contributor identities are copied into this
branch.

Compression window: {args.window_hours:g} hours
Timeline start (UTC): {start.isoformat().replace("+00:00", "Z")}

GitHub's push, event, and audit timestamps remain the actual times at which
these synthetic commits were published.
"""
        (demo_dir / "README.md").write_text(readme, encoding="utf-8")
        (demo_dir / "timeline.csv").write_text(
            "source_commit,source_timestamp_utc,source_author_label,source_subject,"
            "synthetic_timestamp_utc\n", encoding="utf-8"
        )
        run(["git", "-C", str(demo_dir), "add", "README.md", "timeline.csv"])
        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"]
        run(["git", "-C", str(demo_dir), "commit", "--quiet", "-m",
             "[SYNTHETIC DEMO] Initialize labeled timeline"], env=env)

        csv_path = demo_dir / "timeline.csv"
        for index, (sha, epoch, author, subject, mapped_dt) in enumerate(mapped, 1):
            source_dt = datetime.fromtimestamp(epoch, timezone.utc)
            with csv_path.open("a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    sha,
                    source_dt.isoformat().replace("+00:00", "Z"),
                    "Source author omitted",
                    subject.replace("\r", " ").replace("\n", " "),
                    mapped_dt.isoformat().replace("+00:00", "Z"),
                ])
            run(["git", "-C", str(demo_dir), "add", "timeline.csv"])
            date_str = mapped_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            env = os.environ.copy()
            env["GIT_AUTHOR_DATE"] = date_str
            env["GIT_COMMITTER_DATE"] = date_str
            short = sha[:12]
            message = f"[SYNTHETIC DEMO {index}/{len(mapped)}] Timeline entry for source {short}"
            run(["git", "-C", str(demo_dir), "commit", "--quiet", "-m", message], env=env)

        print(f"Created {len(mapped) + 1} clearly labeled synthetic commits.")
        if args.push:
            token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
            destination = args.destination
            if token and destination.startswith("https://github.com/"):
                destination = destination.replace(
                    "https://github.com/",
                    f"https://x-access-token:{token}@github.com/", 1
                )
            run(["git", "-C", str(demo_dir), "remote", "add", "destination", destination])
            run(["git", "-C", str(demo_dir), "push", "--force", "destination",
                 f"HEAD:refs/heads/{args.branch}"])
            print(f"Pushed branch: {args.branch}")
        else:
            print("Preview only. Add --push to publish the branch.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
