#!/usr/bin/env python3
"""Shared GitHub stats fetcher for profile analytics SVGs."""

from __future__ import annotations

import json
import os
import urllib.request

USERNAME = os.environ.get("USERNAME", "Timeless-Dave")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

QUERY = """
query($login: String!) {
  user(login: $login) {
    repositoriesContributedTo(contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) {
      totalCount
    }
    repositories(ownerAffiliations: OWNER, first: 100) {
      totalCount
      nodes {
        stargazerCount
      }
    }
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      contributionCalendar {
        totalContributions
      }
    }
  }
}
"""


def fetch_stats(username: str | None = None, token: str | None = None) -> dict[str, int]:
    login = username or USERNAME
    auth = token or TOKEN
    if not auth:
        raise RuntimeError("GITHUB_TOKEN is required")

    payload = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {auth}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read())

    if body.get("errors"):
        raise RuntimeError(json.dumps(body["errors"]))

    user = body["data"]["user"]
    contrib = user["contributionsCollection"]
    repos = user["repositories"]["nodes"]
    stars = sum(repo["stargazerCount"] for repo in repos)

    # Paginate stars if user has more than 100 repos
    if user["repositories"]["totalCount"] > len(repos):
        page = 2
        while True:
            rest = urllib.request.Request(
                f"https://api.github.com/users/{login}/repos?per_page=100&page={page}&type=owner",
                headers={"Authorization": f"Bearer {auth}", "Accept": "application/vnd.github+json"},
            )
            with urllib.request.urlopen(rest, timeout=60) as response:
                batch = json.loads(response.read())
            if not batch:
                break
            stars += sum(repo.get("stargazers_count", 0) for repo in batch)
            if len(batch) < 100:
                break
            page += 1

    return {
        "commits": contrib["totalCommitContributions"],
        "total_contributions": contrib["contributionCalendar"]["totalContributions"],
        "repos": user["repositories"]["totalCount"],
        "stars": stars,
        "prs": contrib["totalPullRequestContributions"],
        "issues": contrib["totalIssueContributions"],
        "followers": user["followers"]["totalCount"],
        "contributed_to": user["repositoriesContributedTo"]["totalCount"],
    }
