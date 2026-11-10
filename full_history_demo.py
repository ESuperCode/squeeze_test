
#!/usr/bin/env python3
"""
Full synthetic Git history demonstration.

Preserves:
- Commit graph and parent relationships
- Merge commits
- File trees and changes
- Commit messages
- Branches and tags

Rewrites:
- Author and committer dates
- Author and committer identities (optional demo identities)

Publishes source branches under demo/<branch> and tags under demo/<tag>.
The destination main branch is not overwritten.
"""

import os
import sys
import argparse
import subprocess
import tempfile
import random
from pathlib import Path
from datetime import datetime, timezone


DEFAULT_SOURCE = (
    "https://github.com/epsretriever/spherex-planet-x.git"
)

DEFAULT_DESTINATION = (
    "https://github.com/ESuperCode/squeeze_test.git"
)


def run(command, cwd=None, env=None):
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed:\n{' '.join(map(str, command))}\n"
            f"{result.stderr}"
        )

    return result.stdout.strip()


def parse_start(value):
    if not value:
        return datetime.now(timezone.utc).replace(
            microsecond=0
        )

    date = datetime.fromisoformat(
        value.replace("Z", "+00:00")
    )

    if date.tzinfo is None:
        raise ValueError(
            "start_utc must include Z or a UTC offset"
        )

    return date.astimezone(timezone.utc)


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        default=os.getenv("SOURCE_REPO", DEFAULT_SOURCE)
    )

    parser.add_argument(
        "--destination",
        default=os.getenv(
            "DESTINATION_REPO",
            DEFAULT_DESTINATION
        )
    )

    parser.add_argument(
        "--window-hours",
        type=float,
        default=float(
            os.getenv("WINDOW_HOURS", "24")
        )
    )

    parser.add_argument(
        "--start-utc",
        default=os.getenv("START_UTC", "")
    )

    parser.add_argument(
        "--identity-mode",
        choices=["bot", "one", "two"],
        default=os.getenv("IDENTITY_MODE", "bot")
    )

    parser.add_argument(
        "--name1",
        default=os.getenv(
            "NAME1", "Demo Contributor A"
        )
    )

    parser.add_argument(
        "--email1",
        default=os.getenv(
            "EMAIL1", "demo-a@example.invalid"
        )
    )

    parser.add_argument(
        "--name2",
        default=os.getenv(
            "NAME2", "Demo Contributor B"
        )
    )

    parser.add_argument(
        "--email2",
        default=os.getenv(
            "EMAIL2", "demo-b@example.invalid"
        )
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=int(
            os.getenv("ASSIGNMENT_SEED", "42")
        )
    )

    parser.add_argument(
        "--push",
        action="store_true"
    )

    args = parser.parse_args()

    if not 0 < args.window_hours <= 87600:
        parser.error("Invalid timeframe")

    if args.identity_mode == "two":
        if (
            args.name1,
            args.email1.lower()
        ) == (
            args.name2,
            args.email2.lower()
        ):
            parser.error(
                "The two demo identities must be different"
            )

    start = parse_start(args.start_utc)

    destination = args.destination

    token = (
        os.getenv("GITHUB_TOKEN")
        or os.getenv("DESTINATION_TOKEN")
    )

    if (
        args.push
        and token
        and destination.startswith(
            "https://github.com/"
        )
    ):
        destination = destination.replace(
            "https://github.com/",
            f"https://x-access-token:{token}@github.com/",
            1
        )

    with tempfile.TemporaryDirectory() as temp:

        mirror = Path(temp) / "source.git"

        print("Fetching source repository...")

        run([
            "git",
            "clone",
            "--mirror",
            args.source,
            str(mirror)
        ])

        commits = run([
            "git",
            "-C",
            str(mirror),
            "rev-list",
            "--all",
            "--reverse"
        ]).splitlines()

        if not commits:
            raise RuntimeError(
                "No commits found."
            )

        print(
            f"Found {len(commits)} commits."
        )

        # Read original author timestamps.

        original_dates = {}

        for commit in commits:

            timestamp = int(run([
                "git",
                "-C",
                str(mirror),
                "show",
                "-s",
                "--format=%at",
                commit
            ]))

            original_dates[commit] = timestamp

        earliest = min(original_dates.values())
        latest = max(original_dates.values())

        original_span = latest - earliest

        duration = args.window_hours * 3600

        # Calculate compressed dates.

        compressed_dates = {}

        for commit, original_time in original_dates.items():

            if original_span == 0:
                offset = 0
            else:
                offset = (
                    (original_time - earliest)
                    / original_span
                ) * duration

            compressed_dates[commit] = int(
                start.timestamp() + offset
            )

        # Create balanced randomized demo identities.

        rng = random.Random(args.seed)

        shuffled = commits.copy()
        rng.shuffle(shuffled)

        if args.identity_mode == "two":

            split = (len(shuffled) + 1) // 2

            assignments = {
                commit: (
                    1 if index < split else 2
                )
                for index, commit in enumerate(shuffled)
            }

        elif args.identity_mode == "one":

            assignments = {
                commit: 1 for commit in commits
            }

        else:

            assignments = {
                commit: 0 for commit in commits
            }

        identities = {
            0: (
                "Synthetic Demo Bot",
                "synthetic-demo@users.noreply.github.com"
            ),
            1: (args.name1, args.email1),
            2: (args.name2, args.email2)
        }

        if args.identity_mode == "two":

            a = sum(
                value == 1
                for value in assignments.values()
            )

            b = sum(
                value == 2
                for value in assignments.values()
            )

            print(
                f"Contributor A: {a} commits"
            )

            print(
                f"Contributor B: {b} commits"
            )

        # Build git-filter-repo callback.
        #
        # original_id refers to the original commit SHA.
        # Both author and committer timestamps are rewritten.

        date_map = repr(compressed_dates)
        assignment_map = repr(assignments)
        identity_map = repr(identities)

        callback = f'''
sha = commit.original_id.decode("ascii")

epoch = {date_map}[sha]

identity_id = {assignment_map}[sha]

name, email = {identity_map}[identity_id]

date = (
    str(epoch) + " +0000"
).encode("ascii")

commit.author_date = date
commit.committer_date = date

commit.author_name = name.encode("utf-8")
commit.author_email = email.encode("utf-8")

commit.committer_name = name.encode("utf-8")
commit.committer_email = email.encode("utf-8")
'''

        print(
            "Rewriting Git commit metadata..."
        )

        run([
            sys.executable,
            "-m",
            "git_filter_repo",
            "--force",
            "--commit-callback",
            callback
        ], cwd=mirror)

        if not args.push:

            print(
                "Preview completed. Nothing was pushed."
            )

            return

        

print("Publishing reconstructed branches...", flush=True)

run([
    "git", "-C", str(source),
    "push", "--force", "destination",
    "+refs/heads/*:refs/heads/demo/*"
])

print("Publishing reconstructed tags...", flush=True)

run([
    "git", "-C", str(source),
    "push", "--force", "destination",
    "+refs/tags/*:refs/tags/demo/*"
])




if __name__ == "__main__":

    try:
        main()

    except Exception as error:

        print(
            f"ERROR: {error}",
            file=sys.stderr
        )

        sys.exit(1)
