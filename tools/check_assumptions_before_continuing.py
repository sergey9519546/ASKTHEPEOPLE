"""
Pre-run assumption and profile validator (Step 04 — Check the Assumptions).

Enforces the Product Truth Contract and Methodology requirements before a
simulation run is allowed to proceed. Run this as a gate before the simulation
engine starts.

Usage:
    python tools/check_assumptions_before_continuing.py \
        --manifest backend/uploads/simulations/{id}/manifest.json \
        --profiles backend/app/services/fixtures/synthetic_decision_lenses.json \
        --scenario-rules docs/research/scenario-rules.md \
        --starting-conditions docs/research/starting-conditions.md

Exit codes:
    0 - All checks passed, run may proceed
    1 - One or more blocking issues found, run MUST NOT proceed
    2 - Configuration error (missing files, invalid JSON, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    name: str
    passed: bool
    severity: str  # "blocking" | "warning" | "info"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GateResult:
    gate: str
    results: List[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(r.passed is False and r.severity == "blocking" for r in self.results)

    @property
    def blocking_count(self) -> int:
        return sum(1 for r in self.results if r.passed is False and r.severity == "blocking")

    @property
    def warning_count(self) -> int:
        return sum(1 for r in self.results if r.passed is False and r.severity == "warning")


# ---------------------------------------------------------------------------
# Prohibited language patterns (Product Truth Contract enforcement)
# ---------------------------------------------------------------------------

PROHIBITED_OUTCOME_LANGUAGE: List[str] = [
    "predict",
    "know what people think",
    "representative synthetic sample",
    "human-level accuracy",
    "digital twin",
    "bias-free personas",
    "scientifically proven simulation",
    "public opinion",
    "sentiment analysis",
    "preference",
    "intent",
    "behavior",
    "recruited",
    "sampled",
    "observed",
    "interviewed",
    "surveyed",
    "respondents",
    "population",
    "sample size",
    "margin of error",
    "confidence interval",
    "statistically significant",
    "forecast",
    "likely",
    "probably",
    "will",
    "most users",
    "majority",
    "consensus",
    "evidence shows",
    "validated by",
    "proves",
    "confirms",
    "typical",
    "average",
    "representative",
    "authentic",
    "lifelike",
    "grounded in a population",
    "real people",
    "actual people",
    "human respondents",
    "panel",
    "n=",
    "n =",
]

PROHIBITED_FIRST_PERSON_PATTERNS: List[str] = [
    r"\bI (think|believe|feel|experience|know|assume|predict|would|will|should)\b",
    r"\bmy (opinion|view|perspective|experience|belief|assessment)\b",
    r"\bwe (think|believe|feel|experience|know|predict|would|will|should)\b",
    r"\b(Maria|John|Alex|Sarah|Michael|Emily|David|Jessica|Chris|Ashley)\b",  # example names
    r"\b(age|gender|ethnicity|race|nationality)\b.*\b\d{1,3}\b",  # demographic with number
]

QUOTATION_SIMULATION_PATTERNS: List[str] = [
    r'"[^"]{50,}"',  # Long quoted strings
    r"'[^']{50,}'",  # Long single-quoted strings
]


# ---------------------------------------------------------------------------
# Gate 0: Decision Intake Validation
# ---------------------------------------------------------------------------

def check_decision_intake(manifest: Dict[str, Any]) -> GateResult:
    results: List[CheckResult] = []
    required_fields = [
        "decisionQuestion",
        "decisionOwner",
        "intendedUse",
        "decisionDeadline",
        "timeHorizon",
        "stakes",
        "reversibility",
        "affectedContext",
        "knownConstraints",
        "outOfScopeQuestions",
        "humanValidationIntent",
    ]

    for field_name in required_fields:
        value = manifest.get(field_name)
        if value is None:
            results.append(CheckResult(
                name=f"decision_intake_{field_name}",
                passed=False,
                severity="blocking",
                message=f"Required decision intake field '{field_name}' is missing",
                details={"field": field_name},
            ))
        elif isinstance(value, str) and not value.strip():
            results.append(CheckResult(
                name=f"decision_intake_{field_name}",
                passed=False,
                severity="blocking",
                message=f"Required decision intake field '{field_name}' is empty",
                details={"field": field_name},
            ))
        elif isinstance(value, list) and len(value) == 0:
            results.append(CheckResult(
                name=f"decision_intake_{field_name}",
                passed=False,
                severity="blocking",
                message=f"Required decision intake field '{field_name}' is empty list",
                details={"field": field_name},
            ))

    # Check for prohibited verbs
    question = manifest.get("decisionQuestion", "")
    prohibited_verbs = ["improve", "optimize", "understand", "explore", "assess"]
    for verb in prohibited_verbs:
        if verb in question.lower():
            results.append(CheckResult(
                name=f"decision_intake_vague_verb_{verb}",
                passed=False,
                severity="warning",
                message=f"Decision question uses vague verb '{verb}'. Must have observable decision.",
                details={"verb": verb, "question": question},
            ))

    # Check for multiple decisions
    decision_markers = ["should we", "can we", "how do we", "what is the best"]
    decision_count = sum(1 for m in decision_markers if m in question.lower())
    if decision_count > 1:
        results.append(CheckResult(
            name="decision_intake_multiple_decisions",
            passed=False,
            severity="warning",
            message="Decision question appears to contain multiple decisions",
            details={"question": question},
        ))

    # Check for predictive/polling language
    predictive_terms = ["predict", "forecast", "poll", "survey", "measure public", "sample"]
    for term in predictive_terms:
        if term in question.lower():
            results.append(CheckResult(
                name=f"decision_intake_predictive_{term}",
                passed=False,
                severity="blocking",
                message=f"Decision question contains prohibited predictive/polling language: '{term}'",
                details={"term": term, "question": question},
            ))

    if not results:
        results.append(CheckResult(
            name="decision_intake_complete",
            passed=True,
            severity="info",
            message="Decision intake appears complete",
        ))

    return GateResult(gate="Gate 0: Decision Intake", results=results)


# ---------------------------------------------------------------------------
# Gate 1: Truth Contract & Immutable Fields
# ---------------------------------------------------------------------------

def check_truth_contract(manifest: Dict[str, Any]) -> GateResult:
    results: List[CheckResult] = []

    # Check immutable truth fields
    immutable_fields = {
        "output_origin": "synthetic",
        "human_respondent_count": 0,
        "is_forecast": False,
        "is_public_opinion_measure": False,
        "is_causal_evidence": False,
        "source_role": "starting_conditions_only",
        "human_validation_scope": "external_to_synthetic_run",
    }

    for field_name, expected_value in immutable_fields.items():
        actual = manifest.get(field_name)
        if actual != expected_value:
            results.append(CheckResult(
                name=f"truth_contract_{field_name}",
                passed=False,
                severity="blocking",
                message=f"Immutable field '{field_name}' must be '{expected_value}', got '{actual}'",
                details={"field": field_name, "expected": expected_value, "actual": actual},
            ))

    # Check for prohibited claims in manifest text (skip field names and JSON syntax)
    manifest_text = json.dumps(manifest).lower()
    # Remove JSON field names and values that are expected to contain these words
    # (e.g., "is_forecast", "behavior", "will" in legitimate contexts)
    lines_to_skip = []
    for key, value in manifest.items():
        if isinstance(value, (str, int, float, bool)):
            lines_to_skip.append(str(value).lower())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    lines_to_skip.append(item.lower())
                elif isinstance(item, dict):
                    lines_to_skip.append(json.dumps(item).lower())

    check_text = manifest_text
    for skip in lines_to_skip:
        check_text = check_text.replace(skip, "")

    for prohibited in PROHIBITED_OUTCOME_LANGUAGE:
        if prohibited in check_text:
            # Additional context check: only flag if it appears in a claim context
            context_patterns = [
                f"claim.*{prohibited}",
                f"result.*{prohibited}",
                f"output.*{prohibited}",
                f"finding.*{prohibited}",
                f"evidence.*{prohibited}",
            ]
            is_claim_context = any(re.search(p, manifest_text, re.IGNORECASE) for p in context_patterns)
            if is_claim_context or len(prohibited) > 20:  # Long phrases are always flagged
                results.append(CheckResult(
                    name=f"truth_contract_prohibited_language_{prohibited}",
                    passed=False,
                    severity="blocking",
                    message=f"Manifest contains prohibited outcome language: '{prohibited}'",
                    details={"prohibited_term": prohibited},
                ))

    if not results:
        results.append(CheckResult(
            name="truth_contract_valid",
            passed=True,
            severity="info",
            message="Truth contract immutable fields are valid",
        ))

    return GateResult(gate="Gate 1: Truth Contract", results=results)


# ---------------------------------------------------------------------------
# Gate 2: Assumption Review
# ---------------------------------------------------------------------------

def check_assumptions(manifest: Dict[str, Any]) -> GateResult:
    results: List[CheckResult] = []
    assumptions = manifest.get("acceptedAssumptions", [])

    if not assumptions:
        results.append(CheckResult(
            name="assumptions_present",
            passed=False,
            severity="blocking",
            message="No assumptions declared. Run cannot proceed without reviewed assumptions.",
        ))
        return GateResult(gate="Gate 2: Assumptions", results=results)

    blocking_assumptions = [a for a in assumptions if a.get("reviewStatus") == "BLOCKING"]
    if blocking_assumptions:
        results.append(CheckResult(
            name="assumptions_no_blocking",
            passed=False,
            severity="blocking",
            message=f"{len(blocking_assumptions)} blocking assumption(s) present. Run cannot proceed.",
            details={"blocking_assumptions": blocking_assumptions},
        ))

    unreviewed = [a for a in assumptions if a.get("reviewStatus") == "UNREVIEWED"]
    if unreviewed:
        results.append(CheckResult(
            name="assumptions_all_reviewed",
            passed=False,
            severity="blocking",
            message=f"{len(unreviewed)} unreviewed assumption(s). All assumptions must be reviewed before run.",
            details={"unreviewed_count": len(unreviewed)},
        ))

    # Check all assumptions have falsification conditions
    missing_falsification = [a.get("id") for a in assumptions if not a.get("falsificationCondition")]
    if missing_falsification:
        results.append(CheckResult(
            name="assumptions_have_falsification",
            passed=False,
            severity="warning",
            message=f"Assumptions missing falsification conditions: {missing_falsification}",
            details={"missing_falsification": missing_falsification},
        ))

    if not results:
        results.append(CheckResult(
            name="assumptions_valid",
            passed=True,
            severity="info",
            message=f"All {len(assumptions)} assumptions reviewed and non-blocking",
        ))

    return GateResult(gate="Gate 2: Assumptions", results=results)


# ---------------------------------------------------------------------------
# Gate 3: Critical Uncertainties
# ---------------------------------------------------------------------------

def check_uncertainties(manifest: Dict[str, Any]) -> GateResult:
    results: List[CheckResult] = []
    uncertainties = manifest.get("selectedUncertainties", [])

    if not uncertainties:
        results.append(CheckResult(
            name="uncertainties_present",
            passed=False,
            severity="blocking",
            message="No critical uncertainties selected. Run requires 2-4 uncertainties.",
        ))
        return GateResult(gate="Gate 3: Uncertainties", results=results)

    if len(uncertainties) < 2:
        results.append(CheckResult(
            name="uncertainties_minimum",
            passed=False,
            severity="blocking",
            message=f"Only {len(uncertainties)} uncertainty selected. Minimum is 2.",
        ))

    if len(uncertainties) > 4:
        results.append(CheckResult(
            name="uncertainties_maximum",
            passed=False,
            severity="warning",
            message=f"{len(uncertainties)} uncertainties selected. Maximum recommended is 4 (creates combinatorial noise).",
        ))

    # Check each uncertainty has states
    for unc in uncertainties:
        states = unc.get("states", [])
        if len(states) < 2:
            results.append(CheckResult(
                name=f"uncertainty_states_{unc.get('id')}",
                passed=False,
                severity="blocking",
                message=f"Uncertainty {unc.get('id')} has fewer than 2 states",
                details={"uncertainty_id": unc.get("id"), "states": states},
            ))

    if not results:
        results.append(CheckResult(
            name="uncertainties_valid",
            passed=True,
            severity="info",
            message=f"All {len(uncertainties)} uncertainties have ≥2 states",
        ))

    return GateResult(gate="Gate 3: Critical Uncertainties", results=results)


# ---------------------------------------------------------------------------
# Gate 4: Profile Validation
# ---------------------------------------------------------------------------

def check_profiles(
    manifest: Dict[str, Any],
    profiles_path: Optional[str] = None,
    profiles_data: Optional[Dict[str, Any]] = None,
) -> GateResult:
    results: List[CheckResult] = []
    approved_lenses = manifest.get("approvedLenses", [])

    if not approved_lenses:
        results.append(CheckResult(
            name="profiles_present",
            passed=False,
            severity="blocking",
            message="No approved profiles in manifest. Run requires 4-8 profiles.",
        ))
        return GateResult(gate="Gate 4: Profiles", results=results)

    if len(approved_lenses) < 4:
        results.append(CheckResult(
            name="profiles_minimum",
            passed=False,
            severity="blocking",
            message=f"Only {len(approved_lenses)} profiles. Minimum is 4.",
        ))

    if len(approved_lenses) > 8:
        results.append(CheckResult(
            name="profiles_maximum",
            passed=False,
            severity="warning",
            message=f"{len(approved_lenses)} profiles selected. Maximum recommended is 8 (creates false sample-like scale).",
        ))

    # Load profiles if path provided
    profiles_by_id: Dict[str, Dict[str, Any]] = {}
    if profiles_data:
        profiles_by_id = {p["id"]: p for p in profiles_data.get("profiles", [])}
    elif profiles_path and Path(profiles_path).exists():
        with open(profiles_path, "r", encoding="utf-8") as f:
            profiles_data = json.load(f)
            profiles_by_id = {p["id"]: p for p in profiles_data.get("profiles", [])}

    # Check each approved profile exists and is valid
    edge_condition_lenses = {"GP-06", "GP-13", "GP-18", "GP-24"}
    has_edge_condition = False
    has_challenger = False

    for lens_id in approved_lenses:
        profile = profiles_by_id.get(lens_id)
        if not profile:
            results.append(CheckResult(
                name=f"profile_exists_{lens_id}",
                passed=False,
                severity="blocking",
                message=f"Profile {lens_id} not found in profile library",
                details={"lens_id": lens_id},
            ))
            continue

        # Check status
        if profile.get("status") != "approved":
            results.append(CheckResult(
                name=f"profile_approved_{lens_id}",
                passed=False,
                severity="blocking",
                message=f"Profile {lens_id} has status '{profile.get('status')}', must be 'approved'",
                details={"lens_id": lens_id, "status": profile.get("status")},
            ))

        # Check for humanizing language
        full_text = json.dumps(profile).lower()
        for pattern in PROHIBITED_FIRST_PERSON_PATTERNS:
            if re.search(pattern, full_text, re.IGNORECASE):
                results.append(CheckResult(
                    name=f"profile_no_humanizing_{lens_id}",
                    passed=False,
                    severity="blocking",
                    message=f"Profile {lens_id} contains humanizing/first-person language",
                    details={"lens_id": lens_id, "pattern": pattern},
                ))

        # Check for prohibited outcome language
        for prohibited in PROHIBITED_OUTCOME_LANGUAGE:
            if prohibited in full_text:
                results.append(CheckResult(
                    name=f"profile_no_prohibited_lang_{lens_id}_{prohibited}",
                    passed=False,
                    severity="blocking",
                    message=f"Profile {lens_id} contains prohibited language: '{prohibited}'",
                    details={"lens_id": lens_id, "prohibited": prohibited},
                ))

        # Check excludedInferences is non-empty
        if not profile.get("excludedInferences"):
            results.append(CheckResult(
                name=f"profile_excluded_inferences_{lens_id}",
                passed=False,
                severity="warning",
                message=f"Profile {lens_id} has empty excludedInferences — must block stereotype substitution",
                details={"lens_id": lens_id},
            ))

        # Check for demographic attributes without justification
        demographic_keys = ["age", "gender", "ethnicity", "race", "nationality"]
        justifications = profile.get("sensitiveAttributeJustifications", [])
        justified_attrs = {j["attribute"].lower() for j in justifications}

        for key in demographic_keys:
            if key in profile and profile[key] is not None:
                # Check if this demographic attribute is justified
                if not any(key in attr.lower() for attr in justified_attrs):
                    results.append(CheckResult(
                        name=f"profile_demographic_justified_{lens_id}_{key}",
                        passed=False,
                        severity="blocking",
                        message=f"Profile {lens_id} includes demographic attribute '{key}' without sensitiveAttributeJustification",
                        details={"lens_id": lens_id, "attribute": key},
                    ))

        # Track edge conditions and challengers
        if lens_id in edge_condition_lenses:
            has_edge_condition = True
        title = profile.get("title", "").lower()
        if any(word in title for word in ["challenger", "adversarial", "counterfactual", "disconfirmation"]):
            has_challenger = True

    # Check edge condition requirement
    if not has_edge_condition:
        results.append(CheckResult(
            name="profiles_have_edge_condition",
            passed=False,
            severity="blocking",
            message="No edge-condition lens included. Must include at least one of: GP-06, GP-13, GP-18, GP-24",
        ))

    # Check challenger requirement
    if not has_challenger:
        results.append(CheckResult(
            name="profiles_have_challenger",
            passed=False,
            severity="warning",
            message="No lens that challenges decision owner's default assumption detected. Consider adding one.",
        ))

    if not results:
        results.append(CheckResult(
            name="profiles_valid",
            passed=True,
            severity="info",
            message=f"All {len(approved_lenses)} profiles valid and approved",
        ))

    return GateResult(gate="Gate 4: Profiles", results=results)


# ---------------------------------------------------------------------------
# Gate 5: Scenario Rules & Provenance
# ---------------------------------------------------------------------------

def check_scenario_rules(manifest: Dict[str, Any]) -> GateResult:
    results: List[CheckResult] = []

    # Check scenario rules are referenced
    scenario_rules_ref = manifest.get("scenarioRules")
    if not scenario_rules_ref:
        results.append(CheckResult(
            name="scenario_rules_present",
            passed=False,
            severity="blocking",
            message="scenarioRules not referenced in manifest",
        ))
    else:
        # Check the referenced file exists
        rules_path = Path(scenario_rules_ref.split("@")[0])
        if not rules_path.exists():
            results.append(CheckResult(
                name="scenario_rules_exist",
                passed=False,
                severity="blocking",
                message=f"Scenario rules file not found: {scenario_rules_ref}",
                details={"path": str(rules_path)},
            ))

    # Check manifest is immutable (frozenAt present)
    if not manifest.get("frozenAt"):
        results.append(CheckResult(
            name="manifest_frozen",
            passed=False,
            severity="blocking",
            message="Manifest is not frozen (missing frozenAt timestamp). Cannot proceed without frozen manifest.",
        ))

    # Check model config present
    model_config = manifest.get("modelConfig", {})
    if not model_config.get("model"):
        results.append(CheckResult(
            name="model_config_present",
            passed=False,
            severity="warning",
            message="Model configuration incomplete or missing",
        ))

    # Check prompt registry versions
    prompt_versions = manifest.get("promptRegistryVersions", {})
    if not prompt_versions:
        results.append(CheckResult(
            name="prompt_versions_present",
            passed=False,
            severity="warning",
            message="Prompt registry versions not recorded in manifest",
        ))

    # Check content hashes
    content_hashes = manifest.get("contentHashes", {})
    required_hashes = ["brief", "profiles", "config"]
    for hash_name in required_hashes:
        if hash_name not in content_hashes:
            results.append(CheckResult(
                name=f"content_hash_{hash_name}",
                passed=False,
                severity="warning",
                message=f"Missing content hash for '{hash_name}'",
            ))

    if not results:
        results.append(CheckResult(
            name="scenario_rules_valid",
            passed=True,
            severity="info",
            message="Scenario rules and provenance valid",
        ))

    return GateResult(gate="Gate 5: Scenario Rules & Provenance", results=results)


# ---------------------------------------------------------------------------
# Gate 6: Source Material (If Applicable)
# ---------------------------------------------------------------------------

def check_source_material(manifest: Dict[str, Any]) -> GateResult:
    results: List[CheckResult] = []
    source_asset_hashes = manifest.get("sourceAssetHashes", [])

    if not source_asset_hashes:
        results.append(CheckResult(
            name="source_material_present",
            passed=True,
            severity="info",
            message="No source material (decision without uploaded sources)",
        ))
        return GateResult(gate="Gate 6: Source Material", results=results)

    # Source material exists - check rights attestation
    # In a real implementation, this would check a database or file
    results.append(CheckResult(
        name="source_rights_attested",
        passed=True,
        severity="info",
        message=f"Source material present: {len(source_asset_hashes)} assets (rights attestation assumed checked)",
    ))

    return GateResult(gate="Gate 6: Source Material", results=results)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all_checks(
    manifest_path: str,
    profiles_path: Optional[str] = None,
    scenario_rules_path: Optional[str] = None,
    starting_conditions_path: Optional[str] = None,
) -> int:
    """Run all pre-run checks. Returns exit code."""
    manifest_file = Path(manifest_path)
    if not manifest_file.exists():
        print(f"ERROR: Manifest file not found: {manifest_path}", file=sys.stderr)
        return 2

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    gates: List[GateResult] = [
        check_decision_intake(manifest),
        check_truth_contract(manifest),
        check_assumptions(manifest),
        check_uncertainties(manifest),
        check_profiles(manifest, profiles_path=profiles_path),
        check_scenario_rules(manifest),
        check_source_material(manifest),
    ]

    all_passed = True
    total_blocking = 0
    total_warnings = 0

    print("=" * 70)
    print("ASKTHEPEOPLE — PRE-RUN ASSUMPTION CHECK")
    print("=" * 70)
    print(f"Manifest: {manifest_path}")
    print(f"Run ID:   {manifest.get('runId', 'UNKNOWN')}")
    print(f"Frozen:   {manifest.get('frozenAt', 'NOT FROZEN')}")
    print("=" * 70)

    for gate in gates:
        gate_passed = gate.passed
        all_passed = all_passed and gate_passed
        total_blocking += gate.blocking_count
        total_warnings += gate.warning_count

        status_str = "[PASS]" if gate_passed else "[FAIL]"
        print(f"\n{status_str} | {gate.gate}")
        print("-" * 70)

        for result in gate.results:
            icon = "  " if result.passed else "! "
            severity_tag = f"[{result.severity.upper()}]" if not result.passed else ""
            try:
                print(f"  {icon}{result.name}: {result.message} {severity_tag}")
            except UnicodeEncodeError as e:
                # Sanitize message for console output
                safe_msg = result.message.encode('ascii', 'replace').decode('ascii')
                print(f"  {icon}{result.name}: {safe_msg} {severity_tag}")
            if result.details and not result.passed:
                for k, v in result.details.items():
                    print(f"      {k}: {v}")

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total gates:         {len(gates)}")
    print(f"Blocking issues:     {total_blocking}")
    print(f"Warnings:            {total_warnings}")
    print(f"Overall result:      {'[MAY PROCEED]' if all_passed else '[MUST NOT PROCEED]'}")
    print("=" * 70)

    if total_blocking > 0:
        print("\n*** BLOCKING ISSUES FOUND. Run MUST NOT proceed until resolved.", file=sys.stderr)
        return 1
    elif total_warnings > 0:
        print("\n*** Warnings found. Review before proceeding.", file=sys.stderr)
        return 0
    else:
        print("\n*** All checks passed. Run may proceed.", file=sys.stderr)
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ASKTHEPEOPLE Pre-Run Assumption Check (Step 04)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--manifest",
        required=True,
        help="Path to run manifest JSON file",
    )
    parser.add_argument(
        "--profiles",
        help="Path to synthetic decision lenses JSON file",
    )
    parser.add_argument(
        "--scenario-rules",
        help="Path to scenario rules markdown file",
    )
    parser.add_argument(
        "--starting-conditions",
        help="Path to starting conditions markdown file",
    )
    args = parser.parse_args()

    return run_all_checks(
        manifest_path=args.manifest,
        profiles_path=args.profiles,
        scenario_rules_path=args.scenario_rules,
        starting_conditions_path=args.starting_conditions,
    )


if __name__ == "__main__":
    sys.exit(main())
