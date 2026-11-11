
import argparse
import json
import os
import random
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


def run(command, capture=True):
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(map(str, command))
            + "\n"
            + (result.stdout or "")
            + "\n"
            + (result.stderr or "")
        )

    return result.stdout.strip() if capture else ""


def parse_start(value, window_hours):
    if not value:
        return int(
            (
                datetime.now(timezone.utc)
                - timedelta(hours=window_hours)
            ).timestamp()
        )

    value = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        raise ValueError(
            "START_UTC must include a timezone, "
            "for example 2026-11-10T12:00:00Z"
        )

    return int(parsed.timestamp())


def validate_identity(name, email):
    if not name or not email:
        raise ValueError("Identity name and email are required.")

    if not any(
        word in name.casefold()
        for word in ("demo", "synthetic")
    ):
        raise ValueError(
            "Synthetic identity names must include "
            "'Demo' or 'Synthetic'."
        )

    if not email.casefold().endswith(".invalid"):
        raise ValueError(
            "Synthetic identity emails must end in .invalid."
        )


def get_identities(args):
    bot = {
        "name": "Synthetic Demo Bot",
        "email": "demo-bot@example.invalid"
    }

    identity_a = {
        "name": args.name1,
        "email": args.email1
    }

    identity_b = {
        "name": args.name2,
        "email": args.email2
    }

    if args.identity_mode == "bot":
        return [bot]

    validate_identity(
        identity_a["name"],
        identity_a["email"]
    )

    if args.identity_mode == "one":
        return [identity_a]

    validate_identity(
        identity_b["name"],
        identity_b["email"]
    )

    return [identity_a, identity_b]


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        default=os.getenv("SOURCE_REPO")
    )

    parser.add_argument(
        "--destination",
        default=os.getenv("DESTINATION_REPO")
    )

    parser.add_argument(
        "--window-hours",
        type=float,
        default=float(os.getenv("WINDOW_HOURS", "24"))
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
        "--assignment-seed",
        type=int,
        default=int(os.getenv("ASSIGNMENT_SEED", "42"))
    )

    parser.add_argument(
        "--push",
        action="store_true"
    )

    args = parser.parse_args()

    if not args.source or not args.destination:
        parser.error(
            "Source and destination repositories are required."
        )

    if args.window_hours <= 0:
        parser.error("--window-hours must be greater than zero.")

    identities = get_identities(args)

    token = os.getenv("GITHUB_TOKEN", "")

    destination_url = args.destination

    if args.push and not token:
        raise RuntimeError(
            "GITHUB_TOKEN is required when --push is used."
        )

    if args.push and destination_url.startswith(
        "https://github.com/"
    ):
        destination_url = destination_url.replace(
            "https://github.com/",
            "https://x-access-token:"
            + token
            + "@github.com/",
            1
        )

    window_seconds = int(args.window_hours * 3600)
    start_epoch = parse_start(
        args.start_utc,
        args.window_hours
    )

    print("Fetching source repository...", flush=True)

    with tempfile.TemporaryDirectory() as temp:
        mirror = Path(temp) / "source.git"

        run([
            "git",
            "clone",
            "--mirror",
            args.source,
            str(mirror)
        ])

        print("Reading commit history...", flush=True)

        log_output = run([
            "git",
            "-C", str(mirror),
            "log",
            "--all",
            "--format=%H%x09%at%x09%ct"
        ])

        records = []

        for line in log_output.splitlines():
            parts = line.split("\t")

            if len(parts) != 3:
                continue

            sha, author_time, committer_time = parts

            records.append({
                "sha": sha,
                "author_time": int(author_time),
                "committer_time": int(committer_time)
            })

        if not records:
            raise RuntimeError("No commits found.")

        print(
            f"Found {len(records)} commits.",
            flush=True
        )

        all_times = []

        for record in records:
            all_times.append(record["author_time"])
            all_times.append(record["committer_time"])

        earliest = min(all_times)
        latest = max(all_times)

        def map_time(original_time):
            if latest == earliest:
                return start_epoch

            fraction = (
                (original_time - earliest)
                / (latest - earliest)
            )

            return start_epoch + round(
                fraction * window_seconds
            )

        rng = random.Random(args.assignment_seed)

        shuffled = [
            record["sha"] for record in records
        ]

        rng.shuffle(shuffled)

        assignments = {}

        if len(identities) == 1:
            for sha in shuffled:
                assignments[sha] = identities[0]

        else:
            split = (len(shuffled) + 1) // 2

            for sha in shuffled[:split]:
                assignments[sha] = identities[0]

            for sha in shuffled[split:]:
                assignments[sha] = identities[1]

        counts = {}

        for identity in identities:
            counts[identity["name"]] = 0

        mapping = {}

        for record in records:
            sha = record["sha"]
            identity = assignments[sha]

            counts[identity["name"]] += 1

            mapping[sha] = {
                "name": identity["name"],
                "email": identity["email"],
                "author_time": map_time(
                    record["author_time"]
                ),
                "committer_time": map_time(
                    record["committer_time"]
                )
            }

        for name, count in counts.items():
            print(
                f"{name}: {count} commits",
                flush=True
            )

        print(
            "Rewriting Git commit metadata...",
            flush=True
        )

        mapping_json = json.dumps(
            mapping,
            ensure_ascii=False
        )

        callback = (
            "import json\n"
            "mapping = json.loads("
            + repr(mapping_json)
            + ")\n"
            "item = mapping[commit.original_id.decode('ascii')]\n"
            "commit.author_name = item['name'].encode('utf-8')\n"
            "commit.author_email = item['email'].encode('utf-8')\n"
            "commit.committer_name = item['name'].encode('utf-8')\n"
            "commit.committer_email = item['email'].encode('utf-8')\n"
            "commit.author_date = "
            "str(item['author_time']).encode('ascii') + b' +0000'\n"
            "commit.committer_date = "
            "str(item['committer_time']).encode('ascii') + b' +0000'\n"
        )

        run([
            "git-filter-repo",
            "--force",
            "--commit-callback",
            callback
        ], capture=True) if False else None

        # Run git-filter-repo from inside the mirror repository.
        result = subprocess.run(
            [
                "git-filter-repo",
                "--force",
                "--commit-callback",
                callback
            ],
            cwd=str(mirror),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if result.returncode != 0:
            raise RuntimeError(
                "git-filter-repo failed:\n"
                + result.stdout
                + "\n"
                + result.stderr
            )

        if not args.push:
            print(
                "Reconstruction completed locally. "
                "No push requested."
            )
            return

        print(
            "Preparing destination remote...",
            flush=True
        )

        run([
            "git",
            "-C", str(mirror),
            "remote",
            "add",
            "destination",
            destination_url
        ])

        # Reserve this branch for the workflow itself.
        control_branch = "history-demo-control"

        source_branches = run([
            "git",
            "-C", str(mirror),
            "for-each-ref",
            "--format=%(refname)",
            "refs/heads"
        ]).splitlines()

        if f"refs/heads/{control_branch}" in source_branches:
            raise RuntimeError(
                f"The source already has a branch named "
                f"{control_branch}. Choose another control branch."
            )

        print(
            "Publishing reconstructed branches...",
            flush=True
        )

        if source_branches:
            run([
                "git",
                "-C", str(mirror),
                "push",
                "--force",
                "--prune",
                "destination",
                "+refs/heads/*:refs/heads/*"
            ])

        print(
            "Publishing reconstructed tags...",
            flush=True
        )

        source_tags = run([
            "git",
            "-C", str(mirror),
            "for-each-ref",
            "--format=%(refname)",
            "refs/tags"
        ]).splitlines()

        if source_tags:
            run([
                "git",
                "-C", str(mirror),
                "push",
                "--force",
                "--prune",
                "destination",
                "+refs/tags/*:refs/tags/*"
            ])

        print(
            "Publishing completed successfully.",
            flush=True
        )


if __name__ == "__main__":
    main()
