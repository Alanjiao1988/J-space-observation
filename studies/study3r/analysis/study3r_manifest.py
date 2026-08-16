"""Study 3R candidate reproducibility manifest generator.

Authority: ``studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md``

The sealing design is **explicitly acyclic**. The manifest binds every
decision-bearing Study 3R artifact by exact repository-relative path, byte
length, SHA-256 content digest and Git blob identity. It never claims to
contain its own hash: the manifest document is the one and only self-exclusion,
and the outer recursive identity is supplied by the Git commit and tree that
contain the manifest.

This manifest is a **candidate reproducibility manifest**. It is not an
execution seal: the protocol remains ``frozen = false`` and
``execution_authorized = false``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess

DEFAULT_ROOT = pathlib.Path(__file__).resolve().parents[3]

MANIFEST_PATH = "studies/study3r/study3r_candidate_manifest_v1.json"
MANIFEST_SCHEMA_PATH = "studies/study3r/study3r_candidate_manifest_v1.schema.json"

#: Deterministic inclusion rules. Every rule maps one inclusion category to one
#: concrete repository-relative path. Nothing is included by wildcard, so the
#: mapping from category to file is total and auditable.
INCLUSION_RULES = (
    ("authoring_authority",
     "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md"),
    ("protocol", "studies/study3r/protocol/study3r_protocol_v1.json"),
    ("protocol_schema",
     "studies/study3r/protocol/study3r_protocol_v1.schema.json"),
    ("protocol_markdown", "studies/study3r/protocol/study3r_protocol_v1.md"),
    ("current_pointer",
     "studies/study3r/protocol/study3r_protocol_current.json"),
    ("current_pointer_schema",
     "studies/study3r/protocol/study3r_protocol_current.schema.json"),
    ("rendering_registry",
     "studies/study3r/protocol/study3r_rendering_registry_v1.json"),
    ("rendering_registry_schema",
     "studies/study3r/protocol/study3r_rendering_registry_v1.schema.json"),
    ("state_machine",
     "studies/study3r/protocol/study3r_state_machine_v1.json"),
    ("state_machine_schema",
     "studies/study3r/protocol/study3r_state_machine_v1.schema.json"),
    ("task_generator_specification",
     "studies/study3r/tasks/study3r_task_generators_v1.py"),
    ("statistical_code",
     "studies/study3r/analysis/study3r_design_statistics.py"),
    ("statistical_tables",
     "studies/study3r/analysis/study3r_design_statistics_tables.json"),
    ("atomic_cell_census",
     "studies/study3r/analysis/study3r_atomic_cell_census_v1.json"),
    ("independent_recalculation_code",
     "studies/study3r/analysis/study3r_independent_recalculation.py"),
    ("independent_recalculation_tables",
     "studies/study3r/analysis/study3r_independent_recalculation_tables.json"),
    ("protocol_builder",
     "studies/study3r/analysis/study3r_protocol_build.py"),
    ("tokenizer_probe",
     "studies/study3r/analysis/study3r_tokenizer_probe.py"),
    ("tokenizer_acquisition_record",
     "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json"),
    ("tokenizer_acquisition_schema",
     "studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.schema.json"),
    ("wrapper_bytes_and_token_surfaces",
     "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json"),
    ("wrapper_bytes_and_token_surfaces_schema",
     "studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.schema.json"),
    ("tokenizer_equivalence_record",
     "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.json"),
    ("tokenizer_equivalence_schema",
     "studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.schema.json"),
    ("manifest_generator", "studies/study3r/analysis/study3r_manifest.py"),
    ("manifest_schema", MANIFEST_SCHEMA_PATH),
    ("semantic_and_mutation_tests", "tests/test_study3r_protocol_v1.py"),
)

#: The single self-exclusion, with its explanation. A document cannot contain
#: its own content digest, so the manifest excludes itself and defers to the
#: Git commit and tree for the outer recursive identity.
SELF_EXCLUSIONS = (
    {
        "path": MANIFEST_PATH,
        "reason": (
            "A content manifest cannot contain its own SHA-256: including it "
            "would require a fixed point of SHA-256 over a document that "
            "embeds that same digest. The manifest is therefore excluded from "
            "its own entry list, and the Git blob, tree and commit that carry "
            "the manifest supply the outer recursive identity instead."),
    },
)

#: Artifacts that are published *after* this manifest in the registered linear
#: publication order and are therefore bound by the Git commit and tree rather
#: than by the content manifest. These are not decision-bearing: they describe
#: the authoring session and route readers to it.
DEFERRED_EXCLUSIONS = (
    {
        "path": "studies/study3r/study3r_authoring_disclosure_v1.json",
        "reason": (
            "The authoring disclosure records this manifest's own aggregate "
            "digest and the commit that publishes it, so it is necessarily "
            "written in the following commit of the registered linear "
            "publication order. It is bound by the Git commit and tree, and it "
            "is decision-reporting rather than decision-bearing."),
    },
    {
        "path": "studies/study3r/study3r_authoring_disclosure_v1.schema.json",
        "reason": (
            "The disclosure schema is published with the disclosure it "
            "constrains, in the same later commit, for the same reason."),
    },
    {
        "path": "studies/study3r/AUTHORING_DISCLOSURE.md",
        "reason": (
            "The human-readable disclosure is the Markdown rendering of the "
            "machine-readable disclosure and is published with it."),
    },
    {
        "path": "studies/study3r/README.md",
        "reason": (
            "The Study 3R routing update points readers at the disclosure and "
            "is published in the same later commit. It carries no protocol "
            "decision."),
    },
)


def sha256_of(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_id(root: pathlib.Path, relative: str):
    try:
        result = subprocess.run(
            ["git", "--no-pager", "hash-object", "--", relative],
            cwd=str(root), capture_output=True, text=True, check=True)
    except Exception:  # pragma: no cover - git absent
        return None
    return result.stdout.strip() or None


def git_identity(root: pathlib.Path):
    def run(*args):
        try:
            result = subprocess.run(["git", "--no-pager", *args],
                                    cwd=str(root), capture_output=True,
                                    text=True, check=True)
        except Exception:  # pragma: no cover - git absent
            return None
        return result.stdout.strip() or None

    return {
        "commit": run("rev-parse", "HEAD"),
        "tree": run("rev-parse", "HEAD^{tree}"),
        "branch": run("rev-parse", "--abbrev-ref", "HEAD"),
        "is_outer_recursive_identity": True,
    }


def build_manifest(root: pathlib.Path):
    entries = []
    missing = []
    for category, relative in INCLUSION_RULES:
        path = root / pathlib.PurePosixPath(relative)
        if not path.exists():
            missing.append(relative)
            continue
        payload = path.read_bytes()
        entries.append({
            "category": category,
            "path": relative,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "git_blob": git_blob_id(root, relative),
            "lf_only": b"\r" not in payload,
            "utf8_bom": payload.startswith(b"\xef\xbb\xbf"),
        })
    entries.sort(key=lambda entry: entry["path"])
    aggregate = hashlib.sha256()
    for entry in entries:
        aggregate.update(("%s\0%s\0%d\n" % (entry["path"], entry["sha256"],
                                            entry["bytes"])).encode("utf-8"))
    return {
        "schema_version": "study3r-candidate-manifest-v1",
        "authority":
            "studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md",
        "protocol_id": "STUDY3R_PROTOCOL_V1",
        "manifest_kind": "candidate_reproducibility_manifest",
        "is_an_execution_seal": False,
        "protocol_frozen": False,
        "execution_authorized": False,
        "sealing_design": {
            "acyclic": True,
            "claims_to_contain_its_own_hash": False,
            "outer_recursive_identity": "git_commit_and_tree",
            "inner_identity": "deterministic path/blob/sha256 content manifest",
            "aggregate_rule": (
                "SHA-256 over the path-sorted concatenation of "
                "'<path>\\0<sha256>\\0<bytes>\\n' for every included entry"),
        },
        "inclusion_categories": sorted({category
                                        for category, _ in INCLUSION_RULES}),
        "inclusion_rule_count": len(INCLUSION_RULES),
        "entries": entries,
        "entry_count": len(entries),
        "missing_paths": sorted(missing),
        "self_exclusions": [dict(entry) for entry in SELF_EXCLUSIONS],
        "deferred_exclusions": [dict(entry) for entry in DEFERRED_EXCLUSIONS],
        "aggregate_sha256": aggregate.hexdigest(),
        "git": git_identity(root),
        "every_entry_is_lf_only": all(entry["lf_only"] for entry in entries),
        "no_entry_has_a_utf8_bom": not any(entry["utf8_bom"]
                                           for entry in entries),
    }


def build_manifest_schema():
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://study3r.invalid/study3r_candidate_manifest_v1.schema.json",
        "title": "Study 3R candidate reproducibility manifest",
        "type": "object",
        "additionalProperties": False,
        "required": ["aggregate_sha256", "authority", "deferred_exclusions",
                     "entries", "entry_count",
                     "every_entry_is_lf_only", "execution_authorized", "git",
                     "inclusion_categories", "inclusion_rule_count",
                     "is_an_execution_seal", "manifest_kind", "missing_paths",
                     "no_entry_has_a_utf8_bom", "protocol_frozen",
                     "protocol_id", "schema_version", "sealing_design",
                     "self_exclusions"],
        "properties": {
            "schema_version": {"const": "study3r-candidate-manifest-v1"},
            "authority": {
                "const": "studies/study3r/prompts/"
                         "study3r_protocol_v1_authoring_authority.md"},
            "protocol_id": {"const": "STUDY3R_PROTOCOL_V1"},
            "manifest_kind": {"const": "candidate_reproducibility_manifest"},
            "is_an_execution_seal": {"const": False},
            "protocol_frozen": {"const": False},
            "execution_authorized": {"const": False},
            "sealing_design": {
                "type": "object",
                "additionalProperties": False,
                "required": ["acyclic", "aggregate_rule",
                             "claims_to_contain_its_own_hash", "inner_identity",
                             "outer_recursive_identity"],
                "properties": {
                    "acyclic": {"const": True},
                    "claims_to_contain_its_own_hash": {"const": False},
                    "outer_recursive_identity": {"const": "git_commit_and_tree"},
                    "inner_identity": {"type": "string", "minLength": 1},
                    "aggregate_rule": {"type": "string", "minLength": 1},
                },
            },
            "inclusion_categories": {"type": "array", "minItems": 1,
                                     "items": {"type": "string",
                                               "minLength": 1}},
            "inclusion_rule_count": {"type": "integer", "minimum": 1},
            "entries": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["bytes", "category", "git_blob", "lf_only",
                                 "path", "sha256", "utf8_bom"],
                    "properties": {
                        "category": {"type": "string", "minLength": 1},
                        "path": {"type": "string",
                                 "pattern": r"^(studies/study3r/|tests/)"},
                        "bytes": {"type": "integer", "minimum": 1},
                        "sha256": {"type": "string",
                                   "pattern": r"^[0-9a-f]{64}$"},
                        "git_blob": {"type": ["string", "null"],
                                     "pattern": r"^[0-9a-f]{40}$"},
                        "lf_only": {"const": True},
                        "utf8_bom": {"const": False},
                    },
                },
            },
            "entry_count": {"type": "integer", "minimum": 1},
            "missing_paths": {"type": "array", "maxItems": 0,
                              "items": {"type": "string"}},
            "self_exclusions": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "reason"],
                    "properties": {
                        "path": {"const": MANIFEST_PATH},
                        "reason": {"type": "string", "minLength": 40},
                    },
                },
            },
            "deferred_exclusions": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "reason"],
                    "properties": {
                        "path": {"type": "string",
                                 "pattern": r"^studies/study3r/"},
                        "reason": {"type": "string", "minLength": 40},
                    },
                },
            },
            "aggregate_sha256": {"type": "string",
                                 "pattern": r"^[0-9a-f]{64}$"},
            "git": {
                "type": "object",
                "additionalProperties": False,
                "required": ["branch", "commit", "is_outer_recursive_identity",
                             "tree"],
                "properties": {
                    "commit": {"type": ["string", "null"]},
                    "tree": {"type": ["string", "null"]},
                    "branch": {"type": ["string", "null"]},
                    "is_outer_recursive_identity": {"const": True},
                },
            },
            "every_entry_is_lf_only": {"const": True},
            "no_entry_has_a_utf8_bom": {"const": True},
        },
    }


def write_json(path: pathlib.Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=1, sort_keys=True,
                          ensure_ascii=True) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    args = parser.parse_args(argv)
    root = pathlib.Path(args.root)
    write_json(root / pathlib.PurePosixPath(MANIFEST_SCHEMA_PATH),
               build_manifest_schema())
    manifest = build_manifest(root)
    write_json(root / pathlib.PurePosixPath(MANIFEST_PATH), manifest)
    print("manifest: %d entries; aggregate=%s; missing=%d"
          % (manifest["entry_count"], manifest["aggregate_sha256"][:16],
             len(manifest["missing_paths"])))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
