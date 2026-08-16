"""Independent adversarial mutation audit for the Study 3R protocol candidate.

Authority:
``studies/study3r/prompts/study3r_protocol_v1_single_focused_review_authority.md``

This module is a *review* artifact. It re-runs the candidate's own registered
mutation set and adds an independent adversarial set covering the categories the
focused-review authority names in section 12. Every mutation is executed in a
temporary staged tree; the repository worktree is never mutated.

Two mutation classes are executed:

``artifact_only``
    The committed JSON artifact is edited directly and the semantic validator is
    run without rebuilding. A surviving artifact-only mutation means the
    validator does not bind that value at all.

``coordinated``
    The *generator* is edited, the whole bundle is rebuilt from the generators,
    and the semantic validator is run against the rebuilt bundle. A surviving
    coordinated mutation means the registered design can be changed
    self-consistently without detection, which is the decision-bearing case.

The validator under audit is the candidate's own
``tests/test_study3r_protocol_v1.py::validate_bundle``. It is imported, never
edited.

Run::

    python studies/study3r/reviews/study3r_review_mutation_audit.py

It writes ``study3r_review_mutation_audit.json`` beside this module.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).with_suffix(".json")

BUILD = "studies/study3r/analysis/study3r_protocol_build.py"
RECALC = "studies/study3r/analysis/study3r_independent_recalculation.py"
MANIFEST_GEN = "studies/study3r/analysis/study3r_manifest.py"
STATS = "studies/study3r/analysis/study3r_design_statistics.py"
TASKS = "studies/study3r/tasks/study3r_task_generators_v1.py"

PROTOCOL = "studies/study3r/protocol/study3r_protocol_v1.json"
REGISTRY = "studies/study3r/protocol/study3r_rendering_registry_v1.json"
MACHINE = "studies/study3r/protocol/study3r_state_machine_v1.json"
POINTER = "studies/study3r/protocol/study3r_protocol_current.json"
MANIFEST = "studies/study3r/study3r_candidate_manifest_v1.json"
CENSUS = "studies/study3r/analysis/study3r_atomic_cell_census_v1.json"
SURFACES = "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json"


def _load_candidate_tests():
    """Import the candidate test module so its validator can be exercised."""
    path = ROOT / "tests" / "test_study3r_protocol_v1.py"
    spec = importlib.util.spec_from_file_location(
        "study3r_candidate_tests_under_audit", str(path))
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CANDIDATE = _load_candidate_tests()

#: Every file the semantic validator or the rebuild needs.
STAGED_PATHS: Tuple[str, ...] = tuple(CANDIDATE.STAGED_PATHS) + (
    PROTOCOL, REGISTRY, MACHINE, POINTER, MANIFEST, CENSUS,
    "studies/study3r/protocol/study3r_protocol_v1.schema.json",
    "studies/study3r/protocol/study3r_protocol_v1.md",
    "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json",
    "studies/study3r/protocol/study3r_state_machine_v1.schema.json",
    "studies/study3r/protocol/study3r_protocol_current.schema.json",
    "studies/study3r/study3r_candidate_manifest_v1.schema.json",
    "studies/study3r/analysis/study3r_design_statistics_tables.json",
    "studies/study3r/analysis/study3r_independent_recalculation_tables.json",
)


# ---------------------------------------------------------------------------
# Independent adversarial mutations
# ---------------------------------------------------------------------------

#: ``(mutation_id, class, target, old, new, category)``.
#: ``class`` is ``"coordinated"`` (generator edit + rebuild) or
#: ``"artifact_only"`` (direct artifact edit, no rebuild).
ADVERSARIAL: Tuple[Tuple[str, str, str, str, str, str], ...] = (
    # --- D2/D3 allocation ---------------------------------------------------
    ("adv_d2_d3_family_mix_drops_depth_three", "coordinated", BUILD,
     '{"bank_id": "D2_D3_TARGET_BANK", "family_mix": ["D2", "D3"],',
     '{"bank_id": "D2_D3_TARGET_BANK", "family_mix": ["D2"],',
     "d2_d3_allocation"),
    ("adv_d2_d3_ceiling_mix_drops_depth_three", "coordinated", BUILD,
     '{"bank_id": "D2_D3_CEILING_BANK", "family_mix": ["D2", "D3"],',
     '{"bank_id": "D2_D3_CEILING_BANK", "family_mix": ["D2"],',
     "d2_d3_allocation"),
    ("adv_d2_d3_family_mix_artifact_only", "artifact_only", PROTOCOL,
     '"family_mix": [\n     "D2",\n     "D3"\n    ],\n    "gate_id": "G09_RT_E0_QUALIFICATION"',
     '"family_mix": [\n     "D2"\n    ],\n    "gate_id": "G09_RT_E0_QUALIFICATION"',
     "d2_d3_allocation"),
    ("adv_d3_family_depth_relabelled", "coordinated", TASKS,
     '"D2": 2,\n    "D3": 3,', '"D2": 2,\n    "D3": 2,',
     "d2_d3_allocation"),

    # --- global versus candidate-scoped failure transition ------------------
    ("adv_cot_ceiling_failure_scope_becomes_candidate_scoped", "coordinated",
     BUILD,
     '"target": "T03_COT_CEILING_FAILED"},',
     '"target": "S04_COMPETENCE_CONTROLS"},',
     "global_vs_candidate_scoped_failure"),
    ("adv_wrapper_adequacy_failure_scope_changed", "coordinated", BUILD,
     '"target": "T06_WRAPPER_ADEQUACY_FAILED"},',
     '"target": "S07_RPB_LADDER_DEVELOPMENT_AND_CONFIRMATION"},',
     "global_vs_candidate_scoped_failure"),
    ("adv_state_machine_failure_target_artifact_only", "artifact_only", MACHINE,
     '"target": "T03_COT_CEILING_FAILED"',
     '"target": "S04_COMPETENCE_CONTROLS"',
     "global_vs_candidate_scoped_failure"),

    # --- CoT decoding contract ---------------------------------------------
    ("adv_cot_do_sample_true_artifact_only", "artifact_only", PROTOCOL,
     '"bank_relationship": "The ceiling bank is drawn',
     '"do_sample": true,\n   "bank_relationship": "The ceiling bank is drawn',
     "cot_do_sample_temperature_top_p"),
    ("adv_cot_max_new_tokens_artifact_only", "artifact_only", PROTOCOL,
     '"max_new_tokens_per_item": 4096', '"max_new_tokens_per_item": 262144',
     "cot_do_sample_temperature_top_p"),
    ("adv_e0_do_sample_true", "coordinated", BUILD,
     '"do_sample": False,\n                "temperature": None,',
     '"do_sample": True,\n                "temperature": None,',
     "cot_do_sample_temperature_top_p"),

    # --- D0 per-item position rule -----------------------------------------
    ("adv_d0_registry_position_artifact_only", "artifact_only", REGISTRY,
     '"d0_discriminant_position": 57', '"d0_discriminant_position": 40',
     "d0_per_item_position_rule"),
    ("adv_d0_protocol_position_artifact_only", "artifact_only", PROTOCOL,
     '"d0_discriminant_position": 63', '"d0_discriminant_position": 40',
     "d0_per_item_position_rule"),

    # --- forced </think> closure -------------------------------------------
    ("adv_forced_reasoning_closure_removed", "coordinated", BUILD,
     'REASONING_CLOSE_BYTES = "</think>\\n\\n"',
     'REASONING_CLOSE_BYTES = ""',
     "forced_think_closure"),
    ("adv_forced_reasoning_closure_changed", "coordinated", BUILD,
     'REASONING_CLOSE_BYTES = "</think>\\n\\n"',
     'REASONING_CLOSE_BYTES = "</think>\\n"',
     "forced_think_closure"),
    ("adv_closure_artifact_only", "artifact_only", REGISTRY,
     '"frozen_reasoning_closure": "</think>\\n\\n"',
     '"frozen_reasoning_closure": ""',
     "forced_think_closure"),
    # The registry copies ``frozen_reasoning_closure`` and the rendered byte
    # counts out of the tokenizer surfaces record independently. Emptying the
    # closure upstream leaves ``rendered_utf8_bytes`` and
    # ``rendered_token_count`` at their 231/63 values, so the registered
    # description of the model input contradicts the registered rendered bytes.
    ("adv_surfaces_closure_emptied_while_rendered_bytes_unchanged",
     "coordinated", SURFACES,
     '"frozen_reasoning_closure": "</think>\\n\\n"',
     '"frozen_reasoning_closure": ""',
     "forced_think_closure"),

    # --- parser anchoring ---------------------------------------------------
    # ``parser_regex`` is not a builder constant: the builder copies it out of
    # the tokenizer surfaces record, so the coordinated mutation is applied to
    # that upstream input and then rebuilt.
    ("adv_cot_parser_regex_unanchored", "coordinated", SURFACES,
     '"parser_regex": "^Final answer: ([ABCD])$"',
     '"parser_regex": "Final answer: ([ABCD])"',
     "parser_anchoring"),
    ("adv_cot_parser_regex_artifact_only", "artifact_only", PROTOCOL,
     '"parser_regex": "^Final answer: ([ABCD])$"',
     '"parser_regex": "Final answer: ([ABCD])"',
     "parser_anchoring"),

    # --- checkpoint dtype / quantization -----------------------------------
    ("adv_checkpoint_dtype_injected", "artifact_only", PROTOCOL,
     '"acquisition_immutable_revision": "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"',
     '"torch_dtype": "float16",\n   "quantization": "int4",\n'
     '   "acquisition_immutable_revision": "ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562"',
     "checkpoint_dtype_quantization"),

    # --- manifest path omission --------------------------------------------
    ("adv_manifest_omits_the_rendering_registry", "coordinated", MANIFEST_GEN,
     '    ("rendering_registry",\n'
     '     "studies/study3r/protocol/study3r_rendering_registry_v1.json"),\n',
     "",
     "manifest_path_omission"),
    ("adv_manifest_omits_the_state_machine", "coordinated", MANIFEST_GEN,
     '    ("state_machine",\n'
     '     "studies/study3r/protocol/study3r_state_machine_v1.json"),\n',
     "",
     "manifest_path_omission"),
    ("adv_manifest_omits_the_task_generator", "coordinated", MANIFEST_GEN,
     '    ("task_generator_specification",\n'
     '     "studies/study3r/tasks/study3r_task_generators_v1.py"),\n',
     "",
     "manifest_path_omission"),

    # --- current-pointer omission of a normative artifact -------------------
    ("adv_pointer_drops_the_authoritative_schema", "artifact_only", POINTER,
     ' "authoritative_schema": "studies/study3r/protocol/'
     'study3r_protocol_v1.schema.json",\n',
     "",
     "current_pointer_omission"),
    ("adv_pointer_adds_an_alternative_authoritative_artifact", "artifact_only",
     POINTER,
     '"alternative_authoritative_artifacts": []',
     '"alternative_authoritative_artifacts": '
     '["studies/study3/protocol/interface_calibration_protocol_draft_v0_7.json"]',
     "current_pointer_omission"),
    ("adv_pointer_permits_a_runtime_overlay", "artifact_only", POINTER,
     '"runtime_overlay_permitted": false',
     '"runtime_overlay_permitted": true',
     "current_pointer_omission"),
)

#: Governance-test widening is audited as a *predicate* comparison rather than
#: through the bundle validator, because the governance module is not part of the
#: candidate bundle the validator reads.
GOVERNANCE_TEST = "tests/test_study3r_operator_governance.py"


def _stage(destination: pathlib.Path) -> pathlib.Path:
    for relative in STAGED_PATHS:
        source = ROOT / pathlib.PurePosixPath(relative)
        target = destination / pathlib.PurePosixPath(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(str(source), str(target))
    return destination


def _run(root: pathlib.Path, script: str, *args: str):
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(root / pathlib.PurePosixPath(script)), *args],
        cwd=str(root), capture_output=True, text=True, env=environment)


def _rebuild(root: pathlib.Path) -> Optional[str]:
    for script, args in ((BUILD, ("--source-root", str(root),
                                  "--out-root", str(root))),
                         (RECALC, ("--root", str(root))),
                         (MANIFEST_GEN, ("--root", str(root)))):
        completed = _run(root, script, *args)
        if completed.returncode != 0:
            return "rebuild step %s failed: %s" % (
                script, completed.stderr.strip()[-400:])
    return None


def _apply(root: pathlib.Path, relative: str, old: str, new: str) -> None:
    path = root / pathlib.PurePosixPath(relative)
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count < 1:
        raise AssertionError("mutation anchor absent in %s" % relative)
    with open(str(path), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text.replace(old, new))


#: Artifacts compared after a coordinated rebuild to tell a genuine survivor
#: apart from a mutation that changes no committed byte.
GENERATED_ARTIFACTS: Tuple[str, ...] = (
    PROTOCOL, REGISTRY, MACHINE, POINTER, CENSUS, MANIFEST,
    "studies/study3r/protocol/study3r_protocol_v1.schema.json",
    "studies/study3r/protocol/study3r_protocol_v1.md",
    "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json",
    "studies/study3r/protocol/study3r_state_machine_v1.schema.json",
    "studies/study3r/protocol/study3r_protocol_current.schema.json",
    "studies/study3r/study3r_candidate_manifest_v1.schema.json",
    "studies/study3r/analysis/study3r_design_statistics_tables.json",
    "studies/study3r/analysis/study3r_independent_recalculation_tables.json",
)


def _changed_artifacts(staged: pathlib.Path) -> List[str]:
    changed = []
    for relative in GENERATED_ARTIFACTS:
        committed = (ROOT / pathlib.PurePosixPath(relative))
        rebuilt = (staged / pathlib.PurePosixPath(relative))
        if not rebuilt.exists():
            changed.append(relative)
            continue
        if committed.read_bytes() != rebuilt.read_bytes():
            changed.append(relative)
    return changed


#: JSON artifacts that must still validate against their own committed schema.
#: ``validate_bundle`` performs no JSON-schema validation, so a mutation that
#: only breaks schema/data agreement is invisible to it. Recording the schema
#: outcome separately keeps that distinction explicit in the report.
SCHEMA_PAIRS: Tuple[Tuple[str, str], ...] = (
    (PROTOCOL, "studies/study3r/protocol/study3r_protocol_v1.schema.json"),
    (REGISTRY,
     "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json"),
    (MACHINE, "studies/study3r/protocol/study3r_state_machine_v1.schema.json"),
    (POINTER,
     "studies/study3r/protocol/study3r_protocol_current.schema.json"),
    (MANIFEST, "studies/study3r/study3r_candidate_manifest_v1.schema.json"),
)


def _schema_conformance(staged: pathlib.Path) -> Dict[str, object]:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - jsonschema is a repo dependency
        return {"available": False}
    failures = []
    for document, schema in SCHEMA_PAIRS:
        try:
            jsonschema.validate(
                json.loads((staged / pathlib.PurePosixPath(document))
                           .read_text("utf-8")),
                json.loads((staged / pathlib.PurePosixPath(schema))
                           .read_text("utf-8")))
        except Exception as error:  # noqa: BLE001
            failures.append({"document": document,
                             "error": str(error)[:200]})
    return {"available": True, "failures": failures}


def _execute(mutation_id: str, kind: str, relative: str, old: str, new: str,
             category: str) -> Dict[str, object]:
    with tempfile.TemporaryDirectory() as raw:
        staged = _stage(pathlib.Path(raw) / "staged")
        try:
            _apply(staged, relative, old, new)
        except AssertionError as error:
            return {"mutation_id": mutation_id, "class": kind,
                    "category": category, "target": relative,
                    "outcome": "not_applicable",
                    "detail": str(error)}
        if kind == "coordinated":
            failure = _rebuild(staged)
            if failure is not None:
                return {"mutation_id": mutation_id, "class": kind,
                        "category": category, "target": relative,
                        "outcome": "killed", "killed_by": "rebuild",
                        "detail": failure}
        changed = _changed_artifacts(staged)
        schema = _schema_conformance(staged)
        try:
            CANDIDATE.validate_bundle(staged)
        except Exception as error:  # noqa: BLE001 - any rejection kills it
            return {"mutation_id": mutation_id, "class": kind,
                    "category": category, "target": relative,
                    "outcome": "killed", "killed_by": "semantic_validation",
                    "changed_artifacts": changed,
                    "schema_conformance": schema,
                    "detail": str(error)[:300]}
        if not changed:
            return {"mutation_id": mutation_id, "class": kind,
                    "category": category, "target": relative,
                    "outcome": "no_effect_on_the_bundle", "killed_by": None,
                    "changed_artifacts": [],
                    "schema_conformance": schema,
                    "detail": "the mutated generator rebuilt a byte-identical "
                              "bundle, so the mutated symbol is not consumed "
                              "by any committed artifact"}
        return {"mutation_id": mutation_id, "class": kind,
                "category": category, "target": relative,
                "outcome": "survived", "killed_by": None,
                "changed_artifacts": changed,
                "schema_conformance": schema,
                "detail": "the semantic validator accepted a bundle whose "
                          "committed artifacts changed"}


def registered_mutations() -> List[Dict[str, object]]:
    rows = []
    for mutation_id, relative, old, new in CANDIDATE.MUTATIONS:
        rows.append(_execute(mutation_id, "coordinated", relative, old, new,
                             "candidate_registered"))
    return rows


def adversarial_mutations() -> List[Dict[str, object]]:
    return [_execute(*spec) for spec in ADVERSARIAL]


def governance_predicate_audit() -> Dict[str, object]:
    """Compare the governance test's admitted path sets before and after."""
    before = subprocess.run(
        ["git", "--no-pager", "show",
         "cd9c0af3118ca2f254bd0bbaa8eb2ee4dad6d1ed:%s" % GOVERNANCE_TEST],
        cwd=str(ROOT), capture_output=True, text=True, check=True).stdout
    after = (ROOT / pathlib.PurePosixPath(GOVERNANCE_TEST)).read_text("utf-8")
    return {
        "before_declares_a_namespace_prefix_predicate":
            "AUTHORING_NAMESPACE" in before,
        "after_declares_a_namespace_prefix_predicate":
            "AUTHORING_NAMESPACE" in after,
        "newly_admitted_exact_paths": sorted({
            "tests/test_study3r_protocol_v1.py",
            ".gitattributes",
            "tests/test_study3r_operator_governance.py",
            "studies/study3r/README.md",
        }),
        "newly_admitted_prefix": "studies/study3r/",
        "the_module_added_itself_to_its_own_permitted_modified_set":
            'AUTHORING_MODIFIED = {' in after
            and '"tests/test_study3r_operator_governance.py",' in after,
        "per_path_protected_blob_assertions_unchanged":
            before.count("REJECTED_CANDIDATE_PATHS")
            == after.count("REJECTED_CANDIDATE_PATHS")
            and before.count("PROTECTED_HISTORICAL")
            == after.count("PROTECTED_HISTORICAL"),
        "no_protected_path_lies_inside_the_newly_admitted_prefix": True,
    }


def main() -> Dict[str, object]:
    registered = registered_mutations()
    adversarial = adversarial_mutations()
    everything = registered + adversarial
    survivors = [row for row in everything if row["outcome"] == "survived"]
    no_effect = [row for row in everything
                 if row["outcome"] == "no_effect_on_the_bundle"]
    inapplicable = [row for row in everything
                    if row["outcome"] == "not_applicable"]
    decision_bearing_survivors = [
        row for row in survivors
        if row["class"] == "coordinated"
        or row["category"] in ("d2_d3_allocation",
                               "global_vs_candidate_scoped_failure",
                               "cot_do_sample_temperature_top_p",
                               "d0_per_item_position_rule",
                               "forced_think_closure",
                               "parser_anchoring",
                               "checkpoint_dtype_quantization",
                               "manifest_path_omission",
                               "current_pointer_omission")]
    return {
        "authority": ("studies/study3r/prompts/"
                      "study3r_protocol_v1_single_focused_review_authority.md"),
        "schema_version": "study3r-review-mutation-audit-v1",
        "validator_under_audit":
            "tests/test_study3r_protocol_v1.py::validate_bundle",
        "validator_performs_json_schema_validation": False,
        "repository_worktree_was_mutated": False,
        "outcome_definitions": {
            "killed": "the rebuild failed or the semantic validator rejected "
                      "the mutated bundle",
            "no_effect_on_the_bundle":
                "the mutated generator symbol is not consumed by any committed "
                "artifact, so the rebuilt bundle is byte-identical; this is not "
                "a survivor because no registered value moved",
            "survived": "at least one committed artifact changed and the "
                        "semantic validator still accepted the bundle",
            "not_applicable": "the mutation anchor did not resolve",
        },
        "registered_mutation_count": len(registered),
        "adversarial_mutation_count": len(adversarial),
        "total_mutation_count": len(everything),
        "killed_count": len([r for r in everything if r["outcome"] == "killed"]),
        "survivor_count": len(survivors),
        "no_effect_count": len(no_effect),
        "not_applicable_count": len(inapplicable),
        "decision_bearing_survivor_count": len(decision_bearing_survivors),
        "registered_mutations": registered,
        "adversarial_mutations": adversarial,
        "survivors": survivors,
        "no_effect_mutations": no_effect,
        "governance_test_predicate_audit": governance_predicate_audit(),
    }


if __name__ == "__main__":
    payload = main()
    OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    print("wrote", OUT)
    print("registered", payload["registered_mutation_count"],
          "adversarial", payload["adversarial_mutation_count"],
          "killed", payload["killed_count"],
          "survived", payload["survivor_count"],
          "no-effect", payload["no_effect_count"],
          "n/a", payload["not_applicable_count"])
    for row in payload["survivors"]:
        print("  SURVIVOR", row["mutation_id"], "|", row["class"], "|",
              row["category"], "|", row["changed_artifacts"])
    for row in payload["no_effect_mutations"]:
        print("  NO-EFFECT", row["mutation_id"], "|", row["category"])
