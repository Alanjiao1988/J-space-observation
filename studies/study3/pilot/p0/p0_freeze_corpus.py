"""Freeze the Study 3-P0 pilot corpus into committed, immutable bytes.

Authority: ``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``
section 5 and section 6.

This tool is run once, before the pre-execution publication gate and therefore
before any tokenizer or model operation. After the pre-execution commit is
published these bytes are immutable: no item, prompt, expected answer,
distractor, nuisance state, variant, wrapper or allocation may be changed in
response to tokenizer or model output.

Usage::

    python p0_freeze_corpus.py --write     # emit the frozen corpus artifacts
    python p0_freeze_corpus.py --check     # recompute and compare, byte-exact

``--check`` is what the P0 test module and the ACR validation run.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from p0_corpus import (  # noqa: E402
    CENSUS_PATH,
    CORPUS_PATH,
    MANIFEST_PATH,
    NAMESPACE,
    PROFILE_ALLOCATION,
    TUPLE_CLASSES,
    _s3_mirrors_s2,
    aggregate_sha256,
    build_rows,
    canonical_bytes,
    census,
)
from p0_renderer import (  # noqa: E402
    PROTOCOL_PATH,
    REGISTRY_PATH,
    REPO_ROOT,
    load_registry,
)

FIXTURE_RENDERER_PATH = os.path.join(
    REPO_ROOT, "tests", "test_study3_rendering_registry_v0_5.py")

CORPUS_SCHEMA_VERSION = "study3-p0-frozen-corpus-v1"
MANIFEST_SCHEMA_VERSION = "study3-p0-frozen-corpus-manifest-v1"


def _file_sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _file_bytes(path):
    return os.path.getsize(path)


def build_corpus_document(rows):
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "document_class": "study3_p0_frozen_pilot_corpus",
        "authority": (
            "studies/study3/prompts/study3_p0_feasibility_pilot_authority.md"),
        "binding_inputs": {
            "rendering_registry": (
                "studies/study3/protocol/"
                "interface_calibration_rendering_registry_v0_5.json"),
            "protocol_draft": (
                "studies/study3/protocol/interface_calibration_protocol_draft.json"),
        },
        "namespace": NAMESPACE,
        "permanently_excluded_from": [
            "development_bank",
            "confirmation_bank",
            "p3q_bank",
            "external_validity_bank",
        ],
        "exclusion_rule": (
            "the complete study3-p0-only/ namespace and every semantic tuple used "
            "by P0 are permanently excluded from every later development, "
            "confirmation, P3-Q and external-validity bank. P0 data may not be "
            "relabelled or promoted later."),
        "seed_policy": "P0 uses no random seed and creates no bank row",
        "evidence_status": (
            "methods-feasibility observations only; never Study 3 evidence and "
            "never an entry in paper/evidence_ledger.csv"),
        "tuple_classes": list(TUPLE_CLASSES),
        "profile_allocation": [
            {
                "profile": profile,
                "contrasts": list(contrasts),
                "restricted_to_tuple_class": restricted,
            }
            for profile, contrasts, restricted in PROFILE_ALLOCATION
        ],
        "not_applicable_semantics": (
            "structural absence; not a pass, not a zero, not a duplicate and "
            "never a denominator row. K6-SEP is never instantiated for S2 or S3."),
        "row_count": len(rows),
        "rows": rows,
    }


def build_manifest_document(rows, corpus_bytes):
    pairs = _s3_mirrors_s2(rows)
    return {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "document_class": "study3_p0_frozen_pilot_corpus_manifest",
        "authority": (
            "studies/study3/prompts/study3_p0_feasibility_pilot_authority.md"),
        "canonical_serialisation": (
            "json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True) "
            "followed by one LF"),
        "hash_algorithm": "sha256",
        "corpus_document": {
            "path": "studies/study3/pilot/p0/corpus/p0_corpus.json",
            "bytes": len(corpus_bytes),
            "sha256": hashlib.sha256(corpus_bytes).hexdigest(),
        },
        "aggregate_prompt_sha256": aggregate_sha256(rows),
        "row_count": len(rows),
        "member_count": sum(len(row["members"]) for row in rows),
        "census": census(rows),
        "s3_mirrors_s2": [
            {"s3_row_id": s3, "s2_row_id": s2} for s3, s2 in pairs
        ],
        "per_row": [
            {
                "row_id": row["row_id"],
                "base_item_id": row["base_item_id"],
                "profile": row["profile"],
                "contrast": row["contrast"],
                "tuple_class_id": row["tuple_class_id"],
                "ground_truth": row["ground_truth"],
                "members": [
                    {
                        "role_in_pair": member["role_in_pair"],
                        "rendering": member["rendering"],
                        "prompt_bytes": member["prompt_bytes"],
                        "prompt_sha256": member["prompt_sha256"],
                    }
                    for member in row["members"]
                ],
            }
            for row in rows
        ],
        "generator_and_renderer_identities": {
            "p0_renderer": {
                "path": "studies/study3/pilot/p0/p0_renderer.py",
                "bytes": _file_bytes(
                    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "p0_renderer.py")),
                "sha256": _file_sha256(
                    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "p0_renderer.py")),
            },
            "p0_corpus": {
                "path": "studies/study3/pilot/p0/p0_corpus.py",
                "bytes": _file_bytes(
                    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "p0_corpus.py")),
                "sha256": _file_sha256(
                    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "p0_corpus.py")),
            },
            "binding_rendering_registry": {
                "path": ("studies/study3/protocol/"
                         "interface_calibration_rendering_registry_v0_5.json"),
                "bytes": _file_bytes(REGISTRY_PATH),
                "sha256": _file_sha256(REGISTRY_PATH),
            },
            "binding_protocol_draft": {
                "path": ("studies/study3/protocol/"
                         "interface_calibration_protocol_draft.json"),
                "bytes": _file_bytes(PROTOCOL_PATH),
                "sha256": _file_sha256(PROTOCOL_PATH),
            },
            "committed_fixture_renderer": {
                "path": "tests/test_study3_rendering_registry_v0_5.py",
                "bytes": _file_bytes(FIXTURE_RENDERER_PATH),
                "sha256": _file_sha256(FIXTURE_RENDERER_PATH),
                "role": (
                    "byte-protected cross-check target; P0 reimplements the "
                    "registry independently and compares bytes against it"),
            },
        },
    }


def build_census_markdown(rows, manifest):
    lines = []
    lines.append("# Study 3-P0 frozen pilot corpus - census")
    lines.append("")
    lines.append("> Methods-feasibility input only. Not Study 3 evidence, not a")
    lines.append("> bank, not a seed draw and never an evidence-ledger row.")
    lines.append("")
    lines.append("Authority: `studies/study3/prompts/"
                 "study3_p0_feasibility_pilot_authority.md`")
    lines.append("")
    lines.append("Aggregate prompt SHA-256: `%s`"
                 % manifest["aggregate_prompt_sha256"])
    lines.append("")
    lines.append("Rows: **%d**. Rendered pair members: **%d**."
                 % (manifest["row_count"], manifest["member_count"]))
    lines.append("")
    lines.append("Every base-item identity lives in the permanently excluded")
    lines.append("`study3-p0-only/` namespace and may never be relabelled,")
    lines.append("promoted or reused by a later bank.")
    lines.append("")
    lines.append("## Rows by profile")
    lines.append("")
    lines.append("| profile | rows |")
    lines.append("| --- | --- |")
    for profile in sorted(manifest["census"]["by_profile"]):
        lines.append("| %s | %d |"
                     % (profile, manifest["census"]["by_profile"][profile]))
    lines.append("")
    lines.append("## Rows by tuple class")
    lines.append("")
    lines.append("| tuple class | rows |")
    lines.append("| --- | --- |")
    for name in sorted(manifest["census"]["by_tuple_class"]):
        lines.append("| `%s` | %d |"
                     % (name, manifest["census"]["by_tuple_class"][name]))
    lines.append("")
    lines.append("## Rows by contrast")
    lines.append("")
    lines.append("| contrast | rows |")
    lines.append("| --- | --- |")
    for name in sorted(manifest["census"]["by_contrast"]):
        lines.append("| %s | %d |"
                     % (name, manifest["census"]["by_contrast"][name]))
    lines.append("")
    lines.append("## Complete row census")
    lines.append("")
    lines.append("| row | base item identity | profile | contrast | rendering pair "
                 "| ground truth | baseline prompt sha256 | variant prompt sha256 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        baseline, variant = row["members"]
        lines.append("| `%s` | `%s` | %s | %s | %s -> %s | `%s` | `%s` | `%s` |" % (
            row["row_id"], row["base_item_id"], row["profile"], row["contrast"],
            baseline["rendering"], variant["rendering"], row["ground_truth"],
            baseline["prompt_sha256"], variant["prompt_sha256"]))
    lines.append("")
    lines.append("## Structural absence")
    lines.append("")
    lines.append("`K6-SEP` is **not** instantiated for `S2` or `S3`: the")
    lines.append("label-to-content separator has no referent for an option-less")
    lines.append("profile. `not_applicable` is a third value. It is not a pass, not")
    lines.append("a zero effect, not robustness evidence and never a denominator")
    lines.append("member.")
    lines.append("")
    lines.append("`S3` registers no new surface. Its prompts are byte-identical to")
    lines.append("the matching `S2` prompts because `S3` is a CPU-only rescoring")
    lines.append("rule over the already captured `S2` logit vector.")
    lines.append("")
    return "\n".join(lines).encode("utf-8")


def emit():
    registry = load_registry()
    rows = build_rows(registry)
    _s3_mirrors_s2(rows)
    corpus_bytes = canonical_bytes(build_corpus_document(rows))
    manifest = build_manifest_document(rows, corpus_bytes)
    manifest_bytes = canonical_bytes(manifest)
    census_bytes = build_census_markdown(rows, manifest)
    return corpus_bytes, manifest_bytes, census_bytes


def write():
    corpus_bytes, manifest_bytes, census_bytes = emit()
    for path, payload in (
            (CORPUS_PATH, corpus_bytes),
            (MANIFEST_PATH, manifest_bytes),
            (CENSUS_PATH, census_bytes)):
        with open(path, "wb") as handle:
            handle.write(payload)
        print("WROTE %s (%d bytes, sha256 %s)"
              % (os.path.relpath(path, REPO_ROOT).replace(os.sep, "/"),
                 len(payload), hashlib.sha256(payload).hexdigest()))
    return 0


def check():
    corpus_bytes, manifest_bytes, census_bytes = emit()
    failures = []
    for path, payload in (
            (CORPUS_PATH, corpus_bytes),
            (MANIFEST_PATH, manifest_bytes),
            (CENSUS_PATH, census_bytes)):
        rel = os.path.relpath(path, REPO_ROOT).replace(os.sep, "/")
        if not os.path.exists(path):
            failures.append("MISSING %s" % rel)
            continue
        with open(path, "rb") as handle:
            committed = handle.read()
        if committed != payload:
            failures.append(
                "DIFFERS %s (committed %d bytes sha256 %s; recomputed %d bytes "
                "sha256 %s)" % (rel, len(committed),
                                hashlib.sha256(committed).hexdigest(),
                                len(payload),
                                hashlib.sha256(payload).hexdigest()))
    if failures:
        for line in failures:
            print("FAIL " + line)
        return 1
    print("OK the committed frozen P0 corpus reproduces byte-exactly")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.write:
        return write()
    return check()


if __name__ == "__main__":
    sys.exit(main())
