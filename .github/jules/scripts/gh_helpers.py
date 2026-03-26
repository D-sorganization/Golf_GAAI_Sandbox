#!/usr/bin/env python3
"""Small helper CLI for Jules GitHub workflow operations.

This script is intentionally lightweight so GitHub Actions workflows can reuse
the same JSON parsing and step-summary rendering logic without duplicating large
inline Python blocks across multiple workflow files.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def _run_json(command: list[str]) -> object:
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def issue_context(repo: str, issue_number: str, task_classes_path: str) -> int:
    issue = _run_json(
        [
            "gh",
            "issue",
            "view",
            issue_number,
            "--repo",
            repo,
            "--json",
            "number,title,body,labels,url",
        ]
    )

    import re  # noqa: I001
    import yaml

    labels = [label["name"] for label in issue.get("labels", [])]
    with open(task_classes_path, "r", encoding="utf-8") as handle:  # noqa: UP015
        task_classes = yaml.safe_load(handle)["task_classes"]

    task_class = "triage"
    validation_profile = "docs"
    task_label = "jules:triage"
    for name, config in task_classes.items():
        label = config.get("label")
        if label in labels:
            task_class = name
            task_label = label
            validation_profile = config.get("validation_profile", "docs")
            break

    slug = re.sub(r"[^a-z0-9]+", "-", issue["title"].lower()).strip("-")[:40] or "task"
    branch_prefix = f"jules/issue-{issue['number']}-"
    payload = {
        "title": issue["title"],
        "task_class": task_class,
        "task_label": task_label,
        "validation_profile": validation_profile,
        "slug": slug,
        "branch_prefix": branch_prefix,
    }
    print(json.dumps(payload))  # noqa: T201
    return 0


def pr_lookup(repo: str, issue_number: str, branch_prefix: str) -> int:
    prs = _run_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--json",
            "number,headRefName,title,body",
        ]
    )
    issue_ref = f"#{issue_number}"
    issue_title_ref = f"issue #{issue_number}"
    match = None
    for pr in prs:
        body = pr.get("body") or ""
        title = pr.get("title") or ""
        head = pr.get("headRefName") or ""
        if (
            head.startswith(branch_prefix)
            or issue_ref in body
            or issue_title_ref in title.lower()
        ):
            match = pr
            break
    print(json.dumps(match or {}))  # noqa: T201
    return 0


def collect_pr_comments(repo: str, pr_number: str) -> int:
    review_comments = _run_json(
        [
            "gh",
            "api",
            f"repos/{repo}/pulls/{pr_number}/comments?per_page=100",
        ]
    )
    issue_comments = _run_json(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{pr_number}/comments?per_page=100",
        ]
    )

    actionable_terms = [
        "please",
        "should",
        "could you",
        "can you",
        "fix",
        "change",
        "update",
        "add",
        "remove",
        "consider",
        "suggest",
        "recommend",
    ]
    ignored_authors = {
        "copilot-pull-request-reviewer[bot]",
        "cursor[bot]",
        "dependabot[bot]",
        "github-actions[bot]",
        "renovate[bot]",
        "codecov[bot]",
        "sonarcloud[bot]",
    }

    def is_actionable(body: str) -> bool:
        text = (body or "").lower()
        return any(term in text for term in actionable_terms) or "?" in text

    comments = []
    for source, items in [("review", review_comments), ("pr", issue_comments)]:
        for item in items:
            author = item.get("user", {}).get("login", "")
            body = item.get("body", "")
            if author in ignored_authors or not is_actionable(body):
                continue
            comments.append(
                {
                    "comment_id": item.get("id"),
                    "author": author,
                    "body": body,
                    "type": source,
                    "path": item.get("path"),
                    "line": item.get("line"),
                    "created_at": item.get("created_at"),
                }
            )

    seen = set()
    deduped = []
    for comment in comments:
        snippet = (comment["body"] or "")[:120]
        key = (comment["author"], comment["path"], comment["line"], snippet)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(comment)

    grouped = defaultdict(list)
    for comment in deduped:
        grouped[comment.get("path") or "general"].append(comment)

    payload = {
        "pr_number": pr_number,
        "comment_count": len(deduped),
        "comments": deduped,
        "grouped_by_path": grouped,
    }
    print(json.dumps(payload, indent=2, default=list))  # noqa: T201
    return 0


def write_summary(output: str, title: str, items: list[str]) -> int:
    path = Path(output)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"## {title}\n\n")
        for item in items:
            handle.write(f"- {item}\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Jules GitHub workflow helpers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    issue_parser = subparsers.add_parser("issue-context")
    issue_parser.add_argument("--repo", required=True)
    issue_parser.add_argument("--issue-number", required=True)
    issue_parser.add_argument("--task-classes", required=True)

    pr_lookup_parser = subparsers.add_parser("pr-lookup")
    pr_lookup_parser.add_argument("--repo", required=True)
    pr_lookup_parser.add_argument("--issue-number", required=True)
    pr_lookup_parser.add_argument("--branch-prefix", required=True)

    comment_parser = subparsers.add_parser("collect-pr-comments")
    comment_parser.add_argument("--repo", required=True)
    comment_parser.add_argument("--pr-number", required=True)

    summary_parser = subparsers.add_parser("write-summary")
    summary_parser.add_argument("--output", required=True)
    summary_parser.add_argument("--title", required=True)
    summary_parser.add_argument("items", nargs="*")

    args = parser.parse_args()

    if args.command == "issue-context":
        return issue_context(args.repo, args.issue_number, args.task_classes)
    if args.command == "pr-lookup":
        return pr_lookup(args.repo, args.issue_number, args.branch_prefix)
    if args.command == "collect-pr-comments":
        return collect_pr_comments(args.repo, args.pr_number)
    if args.command == "write-summary":
        return write_summary(args.output, args.title, args.items)
    return 1


if __name__ == "__main__":
    sys.exit(main())
