"""Repository-level locks for the secret-scanning release gate."""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
GITLEAKS_CONFIG = REPO_ROOT / ".gitleaks.toml"
DOCKERIGNORE = REPO_ROOT / ".dockerignore"
HIGH_RISK_ALLOWLIST_FRAGMENTS = (
    "docs/",
    "README",
    ".env.example",
    ".env.production",
    "NEXT_STEPS_ROADMAP",
)
PROVIDER_RULE_IDS = {
    "firecrawl-api-key-assignment",
    "jina-api-key-assignment",
    "nvidia-api-key-assignment",
    "zep-api-key-assignment",
    "brave-search-api-key-assignment",
    "groq-api-key-assignment",
    "openai-compatible-api-key-assignment",
}
DEPLOYMENT_GUIDE_PATTERNS = (
    "*DEPLOY*.md*",
    "RAILWAY*.md*",
    "CELERY_WORKER_SETUP.md",
)
LEGACY_RELEASE_EVIDENCE = {
    "FIXES_COMPLETED.md",
    "SECURITY_GATE0.md",
}
ALWAYS_DEPRECATED_GUIDES = {
    "FRONTEND_UPLOAD_FIX.md",
    "FRONTEND_UPLOAD_FIX_V2.md",
    "PRODUCTION_READY_SUMMARY.md",
}


def _deployment_guides() -> set[str]:
    discovered = {
        path.name
        for pattern in DEPLOYMENT_GUIDE_PATTERNS
        for path in REPO_ROOT.glob(pattern)
        if path.is_file()
    }
    return discovered | ALWAYS_DEPRECATED_GUIDES


def _config() -> dict:
    with GITLEAKS_CONFIG.open("rb") as handle:
        return tomllib.load(handle)


def _rule_map() -> dict[str, dict]:
    return {rule["id"]: rule for rule in _config()["rules"]}


def _tracked_files() -> tuple[Path, ...]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"],
        cwd=REPO_ROOT,
    )
    return tuple(
        REPO_ROOT / relative.decode("utf-8")
        for relative in output.split(b"\0")
        if relative
    )


def test_high_risk_content_is_not_globally_allowlisted() -> None:
    paths = _config().get("allowlist", {}).get("paths", [])

    offenders = sorted(
        path
        for path in paths
        if any(fragment in path for fragment in HIGH_RISK_ALLOWLIST_FRAGMENTS)
    )

    assert offenders == []


def test_global_secret_allowlist_has_no_broad_paths_or_stopwords() -> None:
    allowlist = _config().get("allowlist", {})

    assert allowlist.get("paths", []) == []
    assert allowlist.get("stopwords", []) == []
    assert "txt2graph/lib/vis-9\\.1\\.2/vis-network\\.min\\.js" not in (
        GITLEAKS_CONFIG.read_text(encoding="utf-8")
    )


def test_nvidia_assignment_rule_exists() -> None:
    assert "nvidia-api-key-assignment" in _rule_map()


def test_secret_examples_and_deployment_guides_are_outside_docker_context() -> None:
    entries = {
        line.strip()
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    assert "!.env.example" not in entries
    assert _deployment_guides() <= entries
    assert {
        ".agents",
        ".codex",
        ".pytest*",
        ".superpowers",
        ".transition-backups",
        ".transition-data",
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "scratch",
    } <= entries


def test_legacy_root_deployment_guides_are_explicitly_deprecated() -> None:
    for relative in _deployment_guides():
        opening = (REPO_ROOT / relative).read_text(encoding="utf-8")[:800]
        assert "STATUS: DEPRECATED / DO NOT USE" in opening
        assert "docs/release/RUNBOOK.md" in opening


def test_legacy_release_evidence_is_explicitly_non_authoritative() -> None:
    for relative in LEGACY_RELEASE_EVIDENCE:
        opening = (REPO_ROOT / relative).read_text(encoding="utf-8")[:800]
        assert "STATUS: HISTORICAL / NOT RELEASE EVIDENCE" in opening
        assert "docs/release/RUNBOOK.md" in opening


def test_unsupported_split_platform_manifests_fail_closed() -> None:
    blocker = "block_legacy_railway_deploy.py"
    procfile = (REPO_ROOT / "Procfile").read_text(encoding="utf-8")
    render = (REPO_ROOT / "render.yaml").read_text(encoding="utf-8")
    vercel_manifests = tuple(
        path
        for path in REPO_ROOT.rglob("vercel.json")
        if not any(part.startswith(".") for part in path.relative_to(REPO_ROOT).parts)
    )

    assert all(blocker in line for line in procfile.splitlines() if ":" in line)
    assert "services: []" in render
    assert {path.relative_to(REPO_ROOT).as_posix() for path in vercel_manifests} == {
        "frontend/vercel.json",
        "vercel.json",
    }
    for manifest in vercel_manifests:
        content = manifest.read_text(encoding="utf-8")
        assert blocker in content
        assert "askthepeople-production" not in content


def test_provider_rules_do_not_exempt_test_directories() -> None:
    rules = _rule_map()

    for rule_id in PROVIDER_RULE_IDS:
        assert rules[rule_id].get("allowlists", []) == []


def test_provider_rules_still_detect_realistic_assignments_inside_tests() -> None:
    rules = _rule_map()
    realistic_assignments = {
        "zep-api-key-assignment": f"ZEP_API_KEY=z_{'A1' * 20}",
        "brave-search-api-key-assignment": (
            f"BRAVE_SEARCH_API_KEY=BSA_{'B2' * 12}"
        ),
        "openai-compatible-api-key-assignment": (
            f"LLM_API_KEY=sk-{'C3' * 24}"
        ),
        "groq-api-key-assignment": (
            f"LLM_API_KEY=gsk_{'E5' * 24}"
        ),
        "firecrawl-api-key-assignment": (
            f"FIRECRAWL_API_KEY=fc-{'F6' * 20}"
        ),
        "jina-api-key-assignment": (
            f"JINA_API_KEY=jina_{'A7' * 30}"
        ),
        "nvidia-api-key-assignment": (
            f"LLM_BOOST_API_KEY=nvapi-{'D4' * 24}"
        ),
    }

    for rule_id, assignment in realistic_assignments.items():
        assert re.search(rules[rule_id]["regex"], assignment)


def test_tracked_non_test_files_have_no_provider_credential_assignments() -> None:
    rules = _rule_map()
    patterns = {
        rule_id: re.compile(rules[rule_id]["regex"])
        for rule_id in PROVIDER_RULE_IDS
    }
    offenders: list[str] = []

    for path in _tracked_files():
        relative = path.relative_to(REPO_ROOT).as_posix()
        if relative.startswith(("backend/tests/", "frontend/src/__tests__/")):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for rule_id, pattern in patterns.items():
            if pattern.search(content):
                offenders.append(f"{relative}:{rule_id}")

    assert sorted(offenders) == []


def test_ephemeral_pytest_basetemp_directories_are_ignored() -> None:
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".pytest*/" in gitignore


def test_env_example_does_not_enable_the_unfinished_canonical_path() -> None:
    example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "TRANSITION / NOT RELEASE READY" in example
    assert "production should set this to true" not in example
    assert "canonical Railway deployment" not in example
    assert "For production, set to the Supabase Postgres URI" not in example
