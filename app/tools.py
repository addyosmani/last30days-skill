"""ADK tool functions wrapping the last30days research engine.

Each tool invokes scripts/last30days.py via subprocess so the existing
codebase works unchanged.
"""

import os
import subprocess
import sys
from pathlib import Path

# Resolve paths relative to the repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "last30days.py"


def _run_research(
    topic: str,
    *,
    days: int = 30,
    depth: str = "default",
    sources: str | None = None,
) -> str:
    """Run the last30days research script and return its output."""
    cmd = [
        sys.executable,
        str(_SCRIPT),
        topic,
        f"--days={days}",
        "--emit=compact",
    ]

    if depth == "quick":
        cmd.append("--quick")
    elif depth == "deep":
        cmd.append("--deep")

    if sources:
        cmd.append(f"--search={sources}")

    env = {**os.environ}
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(_REPO_ROOT / "scripts"),
            env=env,
        )
        output = result.stdout.strip()
        if result.returncode != 0 and result.stderr:
            output += f"\n\n[stderr]: {result.stderr.strip()[:500]}"
        return output or "(no results)"
    except subprocess.TimeoutExpired:
        return "(research timed out after 5 minutes)"
    except Exception as e:
        return f"(error running research: {e})"


# ---------------------------------------------------------------------------
# ADK Tools — plain functions with docstrings (auto-exposed by ADK)
# ---------------------------------------------------------------------------


def research_topic(
    topic: str,
    days: int = 30,
    depth: str = "default",
    sources: str = "auto",
) -> str:
    """Search for a topic across all available sources (Reddit, X, YouTube,
    Hacker News, web, etc.) and return a comprehensive summary.

    Args:
        topic: The topic or query to research.
        days: Number of days to look back (default 30).
        depth: Search depth — "quick" (fast, fewer results), "default",
               or "deep" (comprehensive, slower).
        sources: Comma-separated source list or "auto" for all available.
                 Options: reddit, x, youtube, hackernews, web, tiktok,
                 instagram, bluesky, truthsocial, polymarket.

    Returns:
        Formatted research results with scores, engagement metrics,
        and source attribution.
    """
    src = None if sources == "auto" else sources
    return _run_research(topic, days=days, depth=depth, sources=src)


def search_reddit(topic: str, days: int = 30) -> str:
    """Search Reddit for discussions about a topic.

    Args:
        topic: The topic or query to search for on Reddit.
        days: Number of days to look back (default 30).

    Returns:
        Reddit posts with scores, subreddits, top comments, and engagement.
    """
    return _run_research(topic, days=days, sources="reddit")


def search_x(topic: str, days: int = 30) -> str:
    """Search X (Twitter) for posts about a topic.

    Args:
        topic: The topic or query to search for on X/Twitter.
        days: Number of days to look back (default 30).

    Returns:
        X posts with engagement metrics (likes, reposts, views).
    """
    return _run_research(topic, days=days, sources="x")


def search_youtube(topic: str, days: int = 30) -> str:
    """Search YouTube for videos about a topic, including transcript highlights.

    Args:
        topic: The topic or query to search for on YouTube.
        days: Number of days to look back (default 30).

    Returns:
        YouTube videos with view counts, channel info, and transcript excerpts.
    """
    return _run_research(topic, days=days, sources="youtube")


def search_web(topic: str, days: int = 30) -> str:
    """Search the web for articles, blog posts, and news about a topic.

    Args:
        topic: The topic or query to search for on the web.
        days: Number of days to look back (default 30).

    Returns:
        Web articles with source domains, snippets, and links.
    """
    return _run_research(topic, days=days, sources="web")


def search_hackernews(topic: str, days: int = 30) -> str:
    """Search Hacker News for discussions about a topic.

    Args:
        topic: The topic or query to search for on Hacker News.
        days: Number of days to look back (default 30).

    Returns:
        Hacker News posts with points, comment counts, and links.
    """
    return _run_research(topic, days=days, sources="hackernews")
