"""The prompt registry's default construction path (exec-plan T30).

`PromptRegistryService.__init__` defaulted to the **relative** path
``docs/ai/PROMPT_REGISTRY.md``. That resolves against the process working
directory, not the package location, so the outcome depended entirely on where
the app was launched from:

* from ``backend/`` -- the runtime CWD for both the Dockerfile and
  ``npm run dev`` -- it resolved to ``backend/docs/ai/PROMPT_REGISTRY.md``,
  which does not exist;
* ``_parse_registry`` returns ``{}`` for a missing file rather than raising, so
  the failure was silent;
* every subsequent ``get_prompt`` then raised ``Prompt ID ... not found``.

All seven pre-existing tests passed ``registry_path=mock_registry_file``, so the
default was never exercised and the suite stayed green against a default that
cannot work. That is the ``AGENTS.md`` rule 2 hazard in its purest form: a
safety-relevant path that no test reaches.

These tests pin the default. They deliberately do not mock anything, so they
fail if the default regresses to a CWD-relative path.
"""

from pathlib import Path

from app.services.prompt_registry_service import PromptRegistryService

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_default_registry_path_resolves_to_a_real_file():
    """The default must be anchored to the repo, not the working directory."""
    service = PromptRegistryService()
    assert service.registry_path.is_absolute(), (
        "the default registry path is relative, so it resolves against the "
        "process working directory"
    )
    assert service.registry_path.exists(), (
        f"default registry path does not exist: {service.registry_path}"
    )


def test_default_registry_path_is_independent_of_cwd(tmp_path, monkeypatch):
    """Changing the working directory must not change what the registry loads."""
    from_repo_root = PromptRegistryService()
    monkeypatch.chdir(tmp_path)
    from_elsewhere = PromptRegistryService()

    assert from_elsewhere.registry_path == from_repo_root.registry_path
    assert from_elsewhere.prompts == from_repo_root.prompts


def test_default_registry_parses_nothing_because_the_document_format_differs():
    """The default registry loads zero prompts, and that is the real state.

    ``_parse_registry`` looks for ``### Prompt: <ID> (v<version>)`` headings
    followed by a fenced block. ``docs/ai/PROMPT_REGISTRY.md`` is a 658-line
    prose document about prompt governance -- its headings are ``## Purpose``,
    ``## Core rule``, ``### Stage 0 - Use-risk classification`` -- and it
    contains no block in the expected format.

    So this service is not merely unwired: its parser was written against a
    document shape this repository does not contain. Its seven pre-existing
    tests pass because each supplies a synthetic file in the expected format,
    so the mismatch was invisible.

    This test asserts the current behaviour deliberately. It is the honest
    baseline for ADR-0004: adopting this registry requires first deciding
    whether the markdown document or the parser is the thing that is wrong.
    Collapsing the two competing implementations is a design decision, not a
    cleanup.
    """
    service = PromptRegistryService()
    assert service.registry_path.exists()
    assert service.prompts == {}, (
        "the default registry now parses prompts. If that is intended, the "
        "markdown document was reformatted -- record it in ADR-0004 and update "
        "this test."
    )


def test_yaml_registry_is_the_only_implementation_that_loads_real_content():
    """``app/prompts/registry.py`` loads five real YAML definitions.

    This is the implementation with actual content behind it. It still has no
    production consumer, which is the open T30 work.
    """
    from app.prompts.registry import PromptRegistry

    yaml_registry = PromptRegistry()
    assert len(yaml_registry.prompts) == 5, (
        f"expected 5 YAML prompt definitions, found {len(yaml_registry.prompts)}"
    )
    prompt_id, versions = sorted(yaml_registry.prompts.items())[0]
    version = sorted(versions)[0]
    assert yaml_registry.get_sha256(prompt_id, version), (
        "the YAML registry must produce a SHA256 audit fingerprint"
    )


def test_two_competing_registry_implementations_exist():
    """Record the split so it is not forgotten.

    ``app/prompts/registry.py`` reads versioned YAML and computes a SHA256
    audit fingerprint. ``app/services/prompt_registry_service.py`` parses fenced
    blocks out of a markdown governance document. Different storage, different
    id schemes, different capabilities, and neither has a production consumer.
    """
    from app.prompts.registry import PromptRegistry

    markdown_ids = set(PromptRegistryService().prompts)
    yaml_ids = set(PromptRegistry().prompts)
    assert yaml_ids, "the YAML registry must expose ids"
    assert markdown_ids != yaml_ids, (
        "the two registries now expose identical id sets; if that is "
        "intentional, collapse them deliberately and update ADR-0004"
    )
