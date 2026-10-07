"""Executable measurement of the two competing prompt registries.

This repository contains two implementations of "the prompt registry", and
neither the divergence nor the absence of a consumer was enforced anywhere.

1. ``app/prompts/registry.py`` (``PromptRegistry``) loads versioned YAML from
   ``app/prompts/definitions/*.yaml`` and computes a SHA256 audit fingerprint.
2. ``app/services/prompt_registry_service.py`` (``PromptRegistryService``)
   parses ``### Prompt: <ID> (v<version>)`` headings, plus a fenced code block,
   out of a markdown document.

The second one cannot work against the document it is pointed at. Its default
path resolves to ``docs/ai/PROMPT_REGISTRY.md``, a 658-line prose governance
document whose headings are ``## Purpose``, ``## Core rule``, ``### Stage 0 -
Use-risk classification`` and so on. That file contains **zero** occurrences of
the token ``Prompt:``, so the parser's required shape is absent by construction
rather than by accident.

The prior module ``test_prompt_registry_default_path.py`` records the same
facts, but in ways that cannot detect the failures that matter most:

* it asserts ``prompts == {}`` without proving the parser can ever return
  non-empty, so a parser that is broken for reasons *other* than format
  mismatch would pass just as quietly;
* it asserts the two id sets merely ``!=`` without printing them, so a reader
  debugging the split has to re-derive both sets by hand;
* it asserts the YAML count is exactly 5, which measures a snapshot rather than
  a property. It has already been broken that way: the four ``zep_*``
  definitions make the count 9, so that assertion is now a false statement
  about the repository;
* it measures no consumers at all, so the "one consumer" and "zero consumers"
  facts live only in prose that nothing checks.

This module derives the consumer sets by walking the ASTs of every module under
``backend/app`` -- relative imports resolved, because all three real importers
use relative form and a scanner that skips them would report zero consumers for
both registries and pass vacuously.

Scope. This module only measures. It edits neither registry, and it does not
decide which of the two should survive. That decision belongs to ADR-0004.
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import pytest

from app.prompts.registry import PromptRegistry
from app.services.prompt_registry_service import PromptRegistryService

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
APP_PACKAGE = BACKEND_ROOT / "app"

# The two implementations, as dotted module names and their defining files.
YAML_REGISTRY_MODULE = "app.prompts.registry"
YAML_REGISTRY_FILE = APP_PACKAGE / "prompts" / "registry.py"

MARKDOWN_REGISTRY_MODULE = "app.services.prompt_registry_service"
MARKDOWN_REGISTRY_FILE = APP_PACKAGE / "services" / "prompt_registry_service.py"

# Measured by AST-walking every module under backend/app. All three importers
# use relative form, which is why this scan resolves relative imports rather
# than skipping them.
#
# The YAML registry's importer set:
#
# * ``backend/app/prompts/__init__.py`` -- package re-export. Not a consumer;
#   it makes the class reachable as ``app.prompts.PromptRegistry``.
# * ``backend/app/services/zep_tools.py`` -- runtime consumer. Imports the
#   class, holds a module-level ``Optional[PromptRegistry]``, and calls
#   ``get_prompt`` through a private accessor.
# * ``backend/app/utils/llm_client.py`` -- runtime consumer. Imports the class,
#   instantiates it lazily as a class attribute, and reads it in
#   ``chat_with_registry_prompt``.
#
# The surprise worth naming: neither runtime consumer reaches the registry the
# obvious way. ``LLMClient`` only touches it inside
# ``chat_with_registry_prompt``, so an importer count of three understates the
# blast radius; EXPECTED_INDIRECT_CONSUMERS below pins those four call sites.
# And
# ``zep_tools`` appears in this list at all only because prompt-registry
# adoption work landed here: ADR-0004 lines 62-66 still records the repository
# as having "no prompt registry", which is now false. Treat this constant as a
# changelog of adoption, not as trivia.
EXPECTED_YAML_IMPORTERS = frozenset(
    {
        "backend/app/prompts/__init__.py",
        "backend/app/services/zep_tools.py",
        "backend/app/utils/llm_client.py",
    }
)

EXPECTED_MARKDOWN_IMPORTERS = frozenset()

# Call sites of LLMClient.chat_with_registry_prompt -- the only path by which
# the YAML registry is actually read at runtime.
EXPECTED_INDIRECT_CONSUMERS = frozenset(
    {
        "backend/app/services/archetype_engine.py",
        "backend/app/services/decision_lens_generator.py",
        "backend/app/services/oasis_profile_generator.py",
        "backend/app/services/ontology_generator.py",
    }
)

# Mirrors the shape _parse_registry requires. Kept test-local rather than
# imported because the parser builds the pattern as a local variable and
# exposes no constant; if _parse_registry's pattern changes, this mirror must be
# updated in the same commit so the mismatch diagnostic stays honest.
_PROMPT_HEADING_SHAPE = re.compile(
    r"###\s+Prompt:\s+[A-Z0-9_]+\s*\(v[0-9.]+\)", re.IGNORECASE
)


def _app_modules() -> list[Path]:
    return sorted(
        path
        for path in APP_PACKAGE.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _package_of(path: Path) -> str:
    return ".".join(path.relative_to(BACKEND_ROOT).parent.parts)


def _resolve_import_from(node: ast.ImportFrom, path: Path) -> str | None:
    """Absolute dotted module for an ImportFrom, or None if unresolvable."""
    if not node.level:
        return node.module
    package = _package_of(path).split(".")
    trimmed = package[: len(package) - (node.level - 1)] if node.level > 1 else package
    if not trimmed:
        return None
    if node.module:
        return ".".join(trimmed + [node.module])
    return ".".join(trimmed)


def _direct_importers(
    target_module: str, target_file: Path
) -> dict[str, list[tuple[int, str]]]:
    """Every module under backend/app importing `target_module`, by repo-relative path."""
    resolved_target = target_file.resolve()
    found: dict[str, list[tuple[int, str]]] = {}
    for path in _app_modules():
        if path.resolve() == resolved_target:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover
            pytest.fail(f"{path} could not be parsed: {exc}")
        hits: list[tuple[int, str]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                resolved = _resolve_import_from(node, path)
                if resolved == target_module or (
                    resolved and resolved.startswith(target_module + ".")
                ):
                    spec = ("." * node.level) + (node.module or "")
                    names = ",".join(alias.name for alias in node.names)
                    hits.append((node.lineno, f"from {spec} import {names}"))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if (
                        alias.name == target_module
                        or alias.name.startswith(target_module + ".")
                    ):
                        hits.append((node.lineno, f"import {alias.name}"))
        if hits:
            found[path.relative_to(REPO_ROOT).as_posix()] = sorted(hits)
    return found


def _classify_importer(rel_path: str) -> str:
    """`re-export` for a package __init__, `runtime` otherwise."""
    return "re-export" if Path(rel_path).name == "__init__.py" else "runtime"


def _render_importers(importers: dict[str, list[tuple[int, str]]]) -> str:
    if not importers:
        return "    <none>"
    lines = []
    for rel_path, hits in sorted(importers.items()):
        lines.append(
            f"    {rel_path}  [{_classify_importer(rel_path)}]"
        )
        lines.extend(f"      :{line}  {spec}" for line, spec in hits)
    return "\n".join(lines)


def _call_sites(method_name: str) -> dict[str, list[int]]:
    """Every call of `.<method_name>()` under backend/app, by repo-relative path."""
    found: dict[str, list[int]] = {}
    for path in _app_modules():
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError) as exc:  # pragma: no cover
            pytest.fail(f"{path} could not be parsed: {exc}")
        lines = sorted(
            node.lineno
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == method_name
        )
        if lines:
            found[path.relative_to(REPO_ROOT).as_posix()] = lines
    return found


def _heading_inventory(document: str) -> list[str]:
    return [
        line
        for line in document.splitlines()
        if line.lstrip().startswith("#")
    ]


class _VirtualRegistryDocument:
    """Minimal stand-in for a path, so the parser can read a synthetic string.

    ``PromptRegistryService`` accepts only a filesystem path, so exercising it
    against an in-memory document needs an object that answers ``exists()`` and
    ``read_text()``. This is preferable to committing a fixture file, because a
    fixture in the repository would itself become a second document the parser
    "works against", and the divergence would stop being visible.
    """

    def __init__(self, text: str) -> None:
        self._text = text

    def exists(self) -> bool:
        return True

    def read_text(self, encoding: str = "utf-8") -> str:
        return self._text


def _parse_synthetic_document(document: str) -> dict[str, dict[str, str]]:
    """Run ``PromptRegistryService._parse_registry`` over an in-memory string."""
    service = PromptRegistryService.__new__(PromptRegistryService)
    service.registry_path = _VirtualRegistryDocument(document)
    return service._parse_registry()


def test_consumer_scan_is_not_vacuous():
    """The scanner must see files and relative imports before its results mean anything.

    Both real importers of the YAML registry use relative form
    (`from .registry import ...`, `from ..prompts.registry import ...`). A
    scanner that skipped relative imports -- as
    ``test_no_phantom_imports.py`` deliberately does, because it only handles
    absolute `app.*` imports -- would report zero consumers for *both*
    registries and every consumer assertion below would pass while measuring
    nothing.

    If this now fails, the scan stopped covering backend/app, or the app package
    moved. Re-point `APP_PACKAGE` before trusting any other test in this file.
    """
    modules = _app_modules()
    assert len(modules) > 100, (
        f"only scanned {len(modules)} modules under {APP_PACKAGE}; the consumer "
        "measurement below would be meaningless"
    )
    assert (APP_PACKAGE / "__init__.py").is_file(), (
        f"{APP_PACKAGE} is not a package; the scan anchor moved"
    )
    yaml_importers = _direct_importers(YAML_REGISTRY_MODULE, YAML_REGISTRY_FILE)
    assert yaml_importers, (
        "the scanner found no importer of the YAML registry at all, including "
        "the known importer backend/app/utils/llm_client.py. The relative-import "
        "resolution in _resolve_import_from has regressed."
    )


def test_yaml_registry_consumer_set_is_exactly_what_was_measured():
    """Pin the live consumer set of the YAML registry.

    The surprise this records: the consumer count is a poor proxy for blast
    radius. Of the three importers only one is the obvious kind --
    ``LLMClient``, which instantiates the registry at :57 and reads it in
    ``chat_with_registry_prompt`` at :194 and :210. ``app/prompts/__init__.py``
    is a package re-export and calls nothing. ``services/zep_tools.py`` holds a
    module-level registry and reads it through a private accessor. Deleting the
    registry would break three modules directly and four more indirectly, so an
    importer count alone would mislead whoever did it.

    If this now fails, a consumer was added or removed. Do not just update the
    constant: a new runtime consumer is a material change to how prompts are
    sourced and belongs in ADR-0004, whose "Project-specific implication" still
    states the repository has no prompt registry. A *removed* consumer means
    prompt templates are inlined in service code again, which is the exact
    condition ADR-0004 says must not persist.
    """
    importers = _direct_importers(YAML_REGISTRY_MODULE, YAML_REGISTRY_FILE)
    measured = frozenset(importers)
    added = sorted(measured - EXPECTED_YAML_IMPORTERS)
    removed = sorted(EXPECTED_YAML_IMPORTERS - measured)
    assert measured == EXPECTED_YAML_IMPORTERS, (
        "the live consumer set of the YAML registry changed.\n"
        f"  added:   {added}\n"
        f"  removed: {removed}\n"
        "current importers:\n"
        + _render_importers(importers)
        + "\nexpected importers:\n"
        + _render_importers(
            {
                rel: []
                for rel in sorted(EXPECTED_YAML_IMPORTERS)
            }
        )
        + "\nIf a new runtime consumer is correct, record it in ADR-0004 first, "
        "then update EXPECTED_YAML_IMPORTERS here."
    )


def test_markdown_registry_has_no_live_consumer():
    """Pin the absence of any consumer of the markdown registry.

    ``app/services/prompt_registry_service.py`` is imported by nothing under
    ``backend/app``. ``PromptRegistryService`` is not even named outside its own
    defining module in that tree. Its only importers anywhere in the repository
    are three test modules, and two of those pass an explicit
    ``registry_path=<synthetic file>``.

    If this now fails, a consumer was added. That is a larger change than the
    set of importers suggests, because that consumer would be reading prompts
    out of a prose governance document that currently contains none. Require
    that the document format question be settled in ADR-0004 first, then update
    EXPECTED_MARKDOWN_IMPORTERS here.
    """
    importers = _direct_importers(
        MARKDOWN_REGISTRY_MODULE, MARKDOWN_REGISTRY_FILE
    )
    measured = frozenset(importers)
    assert measured == EXPECTED_MARKDOWN_IMPORTERS, (
        "the markdown registry is no longer consumerless.\n"
        f"  added:   {sorted(measured - EXPECTED_MARKDOWN_IMPORTERS)}\n"
        f"  removed: {sorted(EXPECTED_MARKDOWN_IMPORTERS - measured)}\n"
        "current importers:\n" + _render_importers(importers)
    )


def test_yaml_registry_reachability_is_measured_indirectly_too():
    """The one direct importer is not the whole story; measure the call sites.

    ``LLMClient`` is the only module that touches ``PromptRegistry``, but it
    only does so inside ``chat_with_registry_prompt``. That method is called
    from four services, all of which are themselves reachable from live code
    (``prep_routes.py`` for profile generation, ``graph_tasks.py`` for ontology,
    ``simulation_manager.py`` for the decision lens).

    So "one consumer" is not a load-bearing description of this registry, and a
    reader who saw only the importer count could delete it and break four
    services. This test makes the indirect set explicit and exact.

    If this now fails, a service started or stopped sourcing prompts through the
    registry. Additions are the ADR-0004 work landing and should be recorded
    there; removals mean prompts are being inlined again. Update
    EXPECTED_INDIRECT_CONSUMERS in the same commit either way.
    """
    call_sites = _call_sites("chat_with_registry_prompt")
    measured = frozenset(call_sites)
    assert measured == EXPECTED_INDIRECT_CONSUMERS, (
        "the set of call sites reading prompts from the YAML registry changed.\n"
        f"  added:   {sorted(measured - EXPECTED_INDIRECT_CONSUMERS)}\n"
        f"  removed: {sorted(EXPECTED_INDIRECT_CONSUMERS - measured)}\n"
        "current call sites:\n"
        + "\n".join(
            f"    {rel}: {lines}"
            for rel, lines in sorted(call_sites.items())
        )
        + "\nAn addition means a new service now sources its prompt from the "
        "registry; record it in ADR-0004. A removal means prompts are inlined "
        "in service code again, which ADR-0004 requires to end."
    )


def test_markdown_registry_parses_zero_prompts_and_the_reason_is_recorded():
    """The measured fact, with the mechanism, so the failure explains itself.

    ``_parse_registry`` matches
    ``###\\s+Prompt:\\s+([A-Z0-9_]+)\\s*\\(v([0-9.]+)\\)``. The default document,
    ``docs/ai/PROMPT_REGISTRY.md``, contains zero occurrences of the token
    ``Prompt:`` anywhere in its 658 lines, so the match is structurally
    impossible rather than nearly-successful. Its 47 headings are all prose:
    ``## Purpose``, ``### Stage 0 - Use-risk classification``, ``### Prompt
    definition``, ``### Prompt release``. The last two are near misses -- they
    begin ``### Prompt`` but carry no colon, so no relaxation of the pattern to
    an optional colon would turn them into prompts either, because the version
    group is still required.

    If this now fails, the document was reformatted, or a second document was
    pointed at, or the parser changed. Any of those means
    ``prompt_registry_service`` may be able to retire or may be about to become
    live. Decide that in ADR-0004 and update the count expectation here; do not
    simply relax this test to whatever the new number happens to be.
    """
    service = PromptRegistryService()
    document = service.registry_path.read_text(encoding="utf-8")
    headings = _heading_inventory(document)
    shaped = [
        line for line in headings if _PROMPT_HEADING_SHAPE.search(line)
    ]
    assert not shaped, (
        f"{service.registry_path} now contains "
        f"{len(shaped)} heading(s) of the shape the parser requires: {shaped}"
    )
    assert "Prompt:" not in document, (
        f"{service.registry_path} now contains the token 'Prompt:' even though "
        "no heading matched the required shape. The parser's pattern is the "
        "thing that changed; re-derive it from _parse_registry before trusting "
        "this test."
    )
    assert service.prompts == {}, (
        "the markdown registry now parses prompts from its default document "
        f"(count={len(service.prompts)}, ids={sorted(service.prompts)}).\n"
        f"  document: {service.registry_path}\n"
        f"  lines:    {len(document.splitlines())}\n"
        f"  headings: {len(headings)}\n"
        f"  'Prompt:' occurrences: {document.count('Prompt:')}\n"
        "  reason it used to parse nothing: the parser requires a heading of "
        "the shape '### Prompt: <ID> (v<version>)' and this prose governance "
        "document contains no such heading, so the match count is zero by "
        "construction.\n"
        "If the reformatting was intentional, record it in ADR-0004 -- that is "
        "the point at which prompt_registry_service stops being a dead parser "
        "and starts competing with app/prompts/registry.py for real use."
    )


def test_markdown_parser_can_parse_a_correctly_formatted_document():
    """Non-vacuity guard. The parser must work; the document is what is wrong.

    The test above proves the default parse is empty. On its own that is
    unfalsifiable: a parser broken in every other way would produce the same
    empty dict and the suite would stay green. This test hands the parser a
    synthetic document in exactly the shape its own docstring describes and
    requires it to extract the ids, versions, and template text.

    It is the input that settles the recommendation. Because the parser does
    parse a correctly shaped document, the divergence is a format mismatch and
    not a defect in the parser's matching logic, which is what makes "reformat
    the document or retire the parser" a decision about intent rather than a
    bug hunt.

    If this now fails, the parser regressed beyond the format question -- the
    regex, the fenced-block extraction, or version ordering. Fix the parser and
    re-examine whether the zero-parse expectation above still describes the
    honest state; do not delete this test, because without it the empty-parse
    assertion measures nothing.
    """
    synthetic = (
        "# Prompt Registry\n"
        "\n"
        "Prose before the blocks, which the parser must ignore.\n"
        "\n"
        "### Prompt: S00_ONTOLOGY (v1.0)\n"
        "```text\n"
        "You are a helpful assistant. Hello {name}!\n"
        "```\n"
        "\n"
        "Prose between blocks, which belongs to the preceding block.\n"
        "\n"
        "### Prompt: S01_SCENARIO (v1.1)\n"
        "```\n"
        "Second template for {topic}.\n"
        "```\n"
        "\n"
        "### Prompt: S00_ONTOLOGY (v2.0)\n"
        "```\n"
        "V2 of the ontology template.\n"
        "```\n"
    )
    parsed = _parse_synthetic_document(synthetic)
    if not parsed:
        pytest.fail(
            "the markdown parser extracts nothing even from a document in the "
            "exact format its own docstring specifies:\n"
            + synthetic
            + "\nThis is worse than a format mismatch: it means the parser "
            "cannot do the only thing it was written to do, so reformatting "
            "docs/ai/PROMPT_REGISTRY.md would NOT make it work. The remedy is "
            "to fix or retire the parser, and the empty-parse assertion above "
            "must stop being read as evidence that the parser is merely "
            "unmatched."
        )
    assert sorted(parsed) == ["S00_ONTOLOGY", "S01_SCENARIO"], (
        f"expected both synthetic ids, got {sorted(parsed)}"
    )
    assert parsed["S00_ONTOLOGY"] == {
        "1.0": "You are a helpful assistant. Hello {name}!",
        "2.0": "V2 of the ontology template.",
    }, f"S00_ONTOLOGY parsed wrong: {parsed['S00_ONTOLOGY']}"
    assert parsed["S01_SCENARIO"] == {
        "1.1": "Second template for {topic}."
    }, f"S01_SCENARIO parsed wrong: {parsed['S01_SCENARIO']}"


def test_the_two_registries_expose_different_id_sets():
    """The divergence itself, with both id sets printed.

    The YAML registry exposes snake_case domain ids, one version each, loaded
    from disk. The markdown registry exposes nothing, because its document has
    no prompt blocks. A previous assertion in
    ``test_prompt_registry_default_path.py`` checked only that the sets differ;
    a reader who then asked "which ids, actually?" had to re-derive both.

    The case convention is part of the divergence and is what makes the two
    schemes hard to merge: ``_parse_registry`` captures ``[A-Z0-9_]+`` and then
    calls ``.upper()``, so every id it can ever produce is upper case, while the
    YAML ids are lower snake_case. Reformatting the document would therefore
    produce ``ONTOLOGY_GENERATION`` where the live path reads
    ``ontology_generation`` -- the same prompt under two names, which is the
    condition the second assertion guards.

    If this now fails, the two registries have converged -- either the markdown
    document acquired real prompt blocks, or the YAML registry lost its
    definitions. Either way the duplicate implementation should be collapsed
    deliberately, in ADR-0004, and this test removed in that same commit rather
    than left to fail.
    """
    markdown_ids = set(PromptRegistryService().prompts)
    yaml_ids = set(PromptRegistry().prompts)
    assert yaml_ids, "the YAML registry exposes no ids; it cannot be compared"
    assert markdown_ids != yaml_ids, (
        "the two registries now expose the same id set.\n"
        f"  yaml ids ({len(yaml_ids)}): {sorted(yaml_ids)}\n"
        f"  markdown ids ({len(markdown_ids)}): {sorted(markdown_ids)}\n"
        "Two implementations reading two formats from two sources are now "
        "agreeing on identity. Collapse them deliberately in ADR-0004 and "
        "delete this test in the same commit."
    )
    assert markdown_ids.isdisjoint(yaml_ids) or not markdown_ids, (
        "the id schemes overlapped.\n"
        f"  yaml ids:     {sorted(yaml_ids)}\n"
        f"  markdown ids: {sorted(markdown_ids)}\n"
        f"  overlap:      {sorted(markdown_ids & yaml_ids)}\n"
        "An overlap means the same prompt id resolves to two different "
        "templates depending on which registry a caller happens to hold. "
        "That is a correctness defect, not a bookkeeping detail; settle it in "
        "ADR-0004."
    )


def test_the_two_registries_differ_in_storage_source_and_capability():
    """The id-set assertion above cannot fire on a case difference alone.

    This test exists because falsification proved the id-set test is currently
    unfalsifiable: the markdown parser upper-cases every id it captures and the
    YAML ids are lower case, so the sets can only converge if one side is
    rewritten. A test that cannot fail measures nothing.

    What is asserted here holds in the present state and is falsifiable now: the
    two classes read different sources, expose different capabilities, and
    ``get_sha256`` -- the audit fingerprint ADR-0004 asks for -- exists on
    exactly one of them.

    If this now fails, the two implementations have grown together: either one
    acquired the other's source format, or the capabilities were unified behind
    a shared base. Both are the preconditions for collapsing them, and both
    belong in ADR-0004 rather than being discovered later as a surprise.
    """
    yaml_registry = PromptRegistry()
    markdown_service = PromptRegistryService()

    yaml_dir = YAML_REGISTRY_FILE.parent / "definitions"
    assert yaml_registry.definitions_path.resolve() == yaml_dir.resolve(), (
        "the YAML registry no longer reads app/prompts/definitions; it read "
        f"{yaml_registry.definitions_path}"
    )
    assert markdown_service.registry_path.suffix == ".md", (
        "the markdown registry no longer reads a markdown document; it read "
        f"{markdown_service.registry_path}"
    )

    yaml_surface = {name for name in dir(PromptRegistry) if not name.startswith("_")}
    markdown_surface = {
        name for name in dir(PromptRegistryService) if not name.startswith("_")
    }
    yaml_only = yaml_surface - markdown_surface
    markdown_only = markdown_surface - yaml_surface
    shared = yaml_surface & markdown_surface
    report = (
        f"\n  shared:       {sorted(shared)}\n"
        f"  yaml-only:    {sorted(yaml_only)}\n"
        f"  markdown-only:{sorted(markdown_only)}"
    )
    assert shared == {"get_prompt"}, (
        "the two registries share a public surface beyond get_prompt; they are "
        f"growing toward one implementation.{report}"
    )
    assert "get_sha256" in yaml_only, (
        "get_sha256 is no longer exclusive to the YAML registry; the audit "
        f"fingerprint ADR-0004 requires has been implemented twice.{report}"
    )
    assert "list_prompts" in yaml_only, (
        f"list_prompts is no longer exclusive to the YAML registry.{report}"
    )
    assert "format_user_prompt" in yaml_only, (
        f"format_user_prompt is no longer exclusive to the YAML registry.{report}"
    )
    assert "strip_chain_of_thought" in markdown_only, (
        "strip_chain_of_thought moved onto the YAML registry. ADR-0010 places "
        "chain-of-thought retention inside the AI-eval domain, so a move here "
        f"is a cross-domain change that needs its own decision.{report}"
    )
    assert "format_prompt" in markdown_only, (
        f"format_prompt is no longer exclusive to the markdown registry.{report}"
    )


# Expected when both system_prompt and user_prompt_template are empty:
# get_sha256 hashes f"{system}\n---\n{user}", so a fully empty definition
# fingerprints to this constant and two different empty definitions would
# collide on the same audit record.
_DEGENERATE_FINGERPRINT = hashlib.sha256("\n---\n".encode("utf-8")).hexdigest()

_TEMPLATE_VARIABLE = re.compile(r"(?<!\{)\{([a-zA-Z0-9_]+)(?:![rsa])?(?::[^{}]*)?\}")


def _missing_template_variables(
    registry: PromptRegistry, prompt_id: str, version: str
) -> dict[str, str]:
    """Placeholder values for every variable the template declares.

    ``PromptRegistry.format_user_prompt`` deliberately raises on an unsupplied
    variable, so exercising a real template means supplying the variables the
    template itself names. Derived from the template rather than hardcoded, so
    this stays correct as definitions change.
    """
    template = registry.get_prompt(prompt_id, version).get(
        "user_prompt_template", ""
    )
    return {
        name: "x"
        for name in _TEMPLATE_VARIABLE.findall(template or "")
    }


def test_yaml_registry_definitions_all_resolve_and_fingerprint():
    """Prove the live path is healthy, not merely present.

    Counts and file listings only prove something was loaded. This walks every
    id and version the YAML registry exposes and requires that each one resolves
    through the public accessors, carries the fields the role contract depends
    on, and produces a stable 64-character SHA256 audit fingerprint that is not
    the degenerate hash of an empty definition.

    This is deliberately a property of whatever is loaded, not a count. A count
    pins a snapshot and is broken by every future adoption; the properties here
    hold for any number of definitions. That matters because the set is already
    growing: the five original domain prompts were joined by four
    ``zep_*`` definitions, so any test asserting "5" was measuring a moment
    rather than a property.

    An empty ``user_prompt_template`` is allowed and is not a defect. A
    system-prompt-only definition is a legitimate shape -- the paired user
    prompt may be an f-string whose interpolations cannot be expressed as a
    ``str.format()`` template -- and the ``zep_*`` definitions declare exactly
    that inline. What is not allowed is a definition with *neither* half, which
    would fingerprint to a constant shared with every other empty definition.

    If this now fails, a definition file is malformed, a prompt lost its system
    prompt, or a prompt became fully empty. A non-empty ``tools`` list is a
    security finding rather than a data-quality one, because
    ``chat_with_role_contract`` binds zero tools by contract and records the
    SHA256 per call; a tools list in the registry would be a declaration the
    runtime does not honour. Fix the definition file and re-run. If a whole
    prompt id was removed, that removal belongs in ADR-0004 and in the caller
    that referenced it.
    """
    registry = PromptRegistry()
    assert registry.prompts, "the YAML registry loaded no prompts at all"

    on_disk = sorted(
        path.name
        for path in YAML_REGISTRY_FILE.parent.joinpath("definitions").glob("*.yaml")
    )
    loaded_versions = sum(len(versions) for versions in registry.prompts.values())
    assert loaded_versions == len(on_disk), (
        f"{len(on_disk)} definition file(s) on disk produced {loaded_versions} "
        f"loaded id/version pair(s). Files: {on_disk}. A file is either being "
        "skipped silently or two files claim the same id and version."
    )

    problems: list[str] = []
    hex_digits = re.compile(r"^[0-9a-f]{64}$")
    system_only: list[str] = []
    for prompt_id, versions in sorted(registry.prompts.items()):
        for version, record in sorted(versions.items()):
            where = f"{prompt_id} v{version}"
            if record.get("id") != prompt_id:
                problems.append(f"{where}: record id is {record.get('id')!r}")
            if record.get("version") != version:
                problems.append(
                    f"{where}: record version is {record.get('version')!r}"
                )
            system_prompt = (record.get("system_prompt") or "").strip()
            user_template = (record.get("user_prompt_template") or "").strip()
            if not system_prompt:
                problems.append(f"{where}: system_prompt is empty")
            if not user_template:
                system_only.append(where)
            if not system_prompt and not user_template:
                problems.append(
                    f"{where}: system_prompt and user_prompt_template are both "
                    "empty, so its fingerprint is the degenerate hash shared by "
                    "every empty definition"
                )
            tools = record.get("tools")
            if tools:
                problems.append(
                    f"{where}: tools is {tools!r}; the role contract binds zero "
                    "tools and chat_with_role_contract never passes them"
                )
            if "validators" not in record:
                problems.append(f"{where}: no validators key")
            if not record.get("created_at"):
                problems.append(
                    f"{where}: no created_at; ADR-0004 requires a release date"
                )
            try:
                digest = registry.get_sha256(prompt_id, version)
            except Exception as exc:  # pragma: no cover
                problems.append(f"{where}: get_sha256 raised {exc!r}")
                continue
            if not hex_digits.match(digest):
                problems.append(
                    f"{where}: fingerprint {digest!r} is not a 64-char sha256 "
                    "hex digest"
                )
            if digest == _DEGENERATE_FINGERPRINT:
                problems.append(
                    f"{where}: fingerprint is the degenerate empty-definition hash"
                )
            if digest != registry.get_sha256(prompt_id, version):
                problems.append(f"{where}: fingerprint is not stable across calls")
            try:
                registry.format_user_prompt(prompt_id, version)
            except ValueError as exc:
                missing = _missing_template_variables(
                    registry, prompt_id, version
                )
                if not missing:
                    problems.append(
                        f"{where}: format_user_prompt raised {exc!r} but the "
                        "template declares no variables"
                    )
                else:
                    try:
                        rendered = registry.format_user_prompt(
                            prompt_id, version, **missing
                        )
                    except Exception as inner:
                        problems.append(
                            f"{where}: format_user_prompt still raised "
                            f"{inner!r} with its own declared variables "
                            f"{sorted(missing)} supplied"
                        )
                    else:
                        if not rendered.strip():
                            problems.append(
                                f"{where}: format_user_prompt rendered nothing "
                                f"from a template declaring {sorted(missing)}"
                            )
            except Exception as exc:
                problems.append(
                    f"{where}: format_user_prompt raised an unexpected "
                    f"{type(exc).__name__}: {exc}"
                )
            latest = registry.get_prompt(prompt_id).get("version")
            if latest not in versions:
                problems.append(
                    f"{where}: unversioned get_prompt returned version "
                    f"{latest!r}, which is not among {sorted(versions)}"
                )
            elif latest != max(
                versions, key=lambda v: tuple(int(p) for p in v.split("."))
            ):
                problems.append(
                    f"{where}: unversioned get_prompt resolved to {latest!r}, "
                    "which is not the semantic maximum"
                )

    assert not problems, (
        "the YAML registry is present but unhealthy, which is worse than "
        "absent because the role contract records its fingerprints:\n"
        + "\n".join(f"  {problem}" for problem in problems)
        + f"\n  ({len(registry.prompts)} id(s) checked; system-prompt-only "
        f"definitions, which are allowed: {system_only})"
    )
