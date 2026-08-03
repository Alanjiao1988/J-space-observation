#!/usr/bin/env python
"""Container entrypoint for the Phase 1.0D semantic review.

Three modes, in the order the authority requires them:

``qualify``
    Prove, against the live pinned deployments and before any target output
    exists, which registered route and api-version answer.  Synthetic only.
``smoke``
    Run the six committed conformance fixtures through all three deployments
    and require the committed expected label for every one.  Synthetic only.
``review``
    The nine deterministic stages over one verified generation pack.

Modes are separate processes on purpose: a qualification or smoke call must not
be able to touch a target output, and the review stages must not be able to
start before both have passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation.phase1_0d_confirmation import (  # noqa: E402
    REVIEW_FORM_PRESENTED_FIELDS,
)
from jspace_observation.semantic_review import addendum as contract  # noqa: E402
from jspace_observation.semantic_review import stages  # noqa: E402
from jspace_observation.semantic_review import transport  # noqa: E402


def _write(path: Path, payload: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.encode("utf-8")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def download_pack(client: Any, prefix: str, destination: Path) -> dict[str, Any]:
    """Copy one generation pack out of Blob, refusing to merge two runs.

    The pack is read, never written back. Downloading into a directory that
    already holds files would let a second source contribute bytes to something
    that is about to be verified as a single run, so a non-empty destination is
    refused outright.
    """

    if destination.exists() and any(destination.iterdir()):
        raise stages.StageError(f"{destination} is not empty; refusing to merge packs")
    names = [name for name in client.list_prefix(prefix) if not name.endswith("/")]
    if not names:
        raise stages.StageError(f"no generation pack under {prefix}")
    destination.mkdir(parents=True, exist_ok=True)
    written: list[dict[str, Any]] = []
    for name in sorted(names):
        relative = name[len(prefix) :].lstrip("/")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = client.get(name)
        target.write_bytes(payload)
        written.append(
            {
                "name": relative,
                "sha256": hashlib.sha256(payload.replace(b"\r\n", b"\n")).hexdigest(),
                "bytes": len(payload),
            }
        )
    return {
        "source_prefix": prefix,
        "file_count": len(written),
        "files": written,
        "destination": str(destination),
    }


def publish_bundle(client: Any, prefix: str, files: Mapping[str, bytes], run_id: str) -> dict[str, Any]:
    """Upload every file, then the manifest that hashes them, create-only.

    Manifest last is the whole point: a reader that finds the manifest knows the
    bytes it names were already written, so a partial upload can never be
    mistaken for a complete result.
    """

    manifest = stages.bundle_manifest(files, run_id)
    uploaded: list[str] = []
    for name in sorted(files):
        client.put_create_only(f"{prefix}/{name}", files[name])
        uploaded.append(name)
    manifest_bytes = contract.canonical_json(manifest).encode("utf-8")
    client.put_create_only(f"{prefix}/artifact_manifest.json", manifest_bytes)
    return {
        "prefix": prefix,
        "uploaded": uploaded,
        "uploaded_count": len(uploaded),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "manifest_written_last": True,
        "manifest": manifest,
    }


class LiveCaller:
    """Calls one pinned deployment, remembering the route that answered."""

    def __init__(self, book: contract.Addendum, tokens: transport.TokenProvider) -> None:
        self._addendum = book
        self._tokens = tokens
        self.resolved: dict[str, tuple[str, str]] = {}

    def resolve(self, profile: contract.RoleProfile, body: Mapping[str, Any]) -> tuple[str, str]:
        """Find the first registered (route, api-version) that answers 200."""

        errors: list[str] = []
        for path in profile.path_candidates:
            for api_version in profile.api_version_candidates:
                try:
                    transport.call_row(
                        profile=profile,
                        addendum=self._addendum,
                        body=body,
                        path=path,
                        api_version=api_version,
                        tokens=self._tokens,
                    )
                except contract.TransportError as error:
                    errors.append(f"{path}?{api_version or '-'}: {error}")
                    continue
                except contract.MalformedResponseError:
                    return path, api_version  # it answered; shape is a later concern
                return path, api_version
        raise contract.TransportError(
            f"no registered route answered for {profile.role}: " + " | ".join(errors[:6])
        )

    def __call__(self, profile: contract.RoleProfile, body: Mapping[str, Any]):
        route = self.resolved.get(profile.role)
        if route is None:
            raise contract.AddendumError(
                f"{profile.role} was called before its route was qualified"
            )
        path, api_version = route
        return transport.call_row(
            profile=profile,
            addendum=self._addendum,
            body=body,
            path=path,
            api_version=api_version,
            tokens=self._tokens,
        )


def _qualify(book: contract.Addendum, caller: LiveCaller) -> dict[str, Any]:
    probe = dict(book.smoke_fixtures[0]["row"])
    receipts: dict[str, Any] = {}
    for role in contract.ROLES:
        profile = book.roles[role]
        body = contract.build_request(profile, book, probe)
        started = time.monotonic()
        path, api_version = caller.resolve(profile, body)
        caller.resolved[role] = (path, api_version)
        receipts[role] = {
            "provider": profile.provider,
            "deployment": profile.deployment,
            "model": profile.model,
            "model_version": profile.model_version,
            "sku": profile.sku,
            "region": profile.region,
            "proven_path": path,
            "proven_api_version": api_version,
            "reviewer_id": profile.reviewer_id,
            "request_profile_sha256": profile.request_profile_sha256(),
            "seconds": round(time.monotonic() - started, 2),
        }
    return receipts


def _smoke(book: contract.Addendum, caller: LiveCaller) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    mismatches: list[str] = []
    for fixture in book.smoke_fixtures:
        for role in contract.ROLES:
            profile = book.roles[role]
            body = contract.build_request(profile, book, fixture["row"])
            response = caller(profile, body)
            label = contract.parse_label(response.payload, profile)
            expected = str(fixture["expected_label"])
            results.append(
                {
                    "fixture_id": fixture["fixture_id"],
                    "role": role,
                    "deployment": profile.deployment,
                    "expected_label": expected,
                    "observed_label": label,
                    "match": label == expected,
                    "request_sha256": response.request_sha256,
                    "response_sha256": response.response_sha256,
                    "visible_completion_tokens": contract.visible_token_count(
                        response.payload
                    ),
                    "usage": response.payload.get("usage"),
                    "retries": response.retries,
                }
            )
            if label != expected:
                mismatches.append(f"{fixture['fixture_id']}/{role}: {label} != {expected}")
    return {
        "fixtures": results,
        "fixture_count": len(book.smoke_fixtures),
        "call_count": len(results),
        "mismatches": mismatches,
        "passed": not mismatches,
        "counts_towards_scientific_totals": False,
    }


def _review(
    book: contract.Addendum,
    caller: LiveCaller,
    pack_dir: Path,
    out_dir: Path,
    run_id: str,
) -> dict[str, Any]:
    verification = stages.verify_generation_pack(pack_dir)
    records = stages._load_jsonl(pack_dir / "02_records.jsonl")
    form = stages._load_jsonl(pack_dir / "03_review_form.jsonl")
    record_ids = [str(row["record_id"]) for row in records]

    primary = stages.review_rows(
        rows=stages.rows_for(form, record_ids),
        profile=book.roles["primary"],
        addendum=book,
        caller=caller,
    )
    secondary_selection = stages.select_secondary(records, primary.judgments, book)
    secondary = stages.review_rows(
        rows=stages.rows_for(form, secondary_selection["required_ids"]),
        profile=book.roles["secondary"],
        addendum=book,
        caller=caller,
    )
    third_selection = stages.select_third(primary.judgments, secondary.judgments)
    third = stages.review_rows(
        rows=stages.rows_for(form, third_selection["required_ids"]),
        profile=book.roles["third"],
        addendum=book,
        caller=caller,
    )

    coverage = stages.verify_judgments(
        record_ids=record_ids,
        primary=primary.judgments,
        secondary=secondary.judgments,
        third=third.judgments,
        required_secondary=secondary_selection["required_ids"],
        required_third=third_selection["required_ids"],
        addendum=book,
        receipts_by_role={
            "primary": primary.receipts,
            "secondary": secondary.receipts,
            "third": third.receipts,
        },
    )
    combined = stages.combine_judgments(
        primary.judgments, secondary.judgments, third.judgments
    )

    review_dir = out_dir / "review"
    for role, outcome in (
        ("primary", primary),
        ("secondary", secondary),
        ("third", third),
    ):
        _write(
            review_dir / role / "judgments.json",
            contract.canonical_json(outcome.judgments),
        )
        _write(
            review_dir / role / "raw_response_manifest.json",
            contract.canonical_json(
                {
                    "role": role,
                    "responses": outcome.receipts,
                    "response_count": len(outcome.receipts),
                    "label_counts": outcome.label_counts,
                    "transport_retries": outcome.retries,
                    "requests_including_retries": outcome.requests,
                }
            ),
        )
    _write(
        review_dir / "secondary" / "selection_receipt.json",
        contract.canonical_json(secondary_selection),
    )
    _write(
        review_dir / "third" / "disagreement_receipt.json",
        contract.canonical_json(third_selection),
    )
    judgments_path = review_dir / "all_judgments.json"
    judgments_sha = _write(judgments_path, contract.canonical_json(combined))

    return {
        "verification": verification,
        "coverage": coverage,
        "secondary_selection": secondary_selection,
        "third_selection": third_selection,
        "judgments_path": str(judgments_path),
        "all_judgments_sha256": judgments_sha,
        "label_counts": {
            "primary": primary.label_counts,
            "secondary": secondary.label_counts,
            "third": third.label_counts,
        },
        "transport": {
            "retries": primary.retries + secondary.retries + third.retries,
            "requests": primary.requests + secondary.requests + third.requests,
        },
        "run_id": run_id,
    }


def finalize_pack(
    project_root: Path,
    pack_dir: Path,
    judgments_path: Path,
    out_root: Path,
    run_id: str,
    code_commit: str,
    image_digest: str,
) -> dict[str, Any]:
    """Stage 8: the frozen finalizer, called rather than reimplemented."""

    from jspace_observation.phase1_0d_generation import (  # noqa: PLC0415
        RunConfig,
        run_phase1_0d,
    )

    summary = run_phase1_0d(
        RunConfig(
            mode="finalize",
            output_root=out_root,
            repo_root=project_root,
            run_id=run_id,
            code_commit=code_commit,
            image_digest=image_digest,
            hardware="Azure Container Apps Consumption workload profile, CPU only",
            records_path=pack_dir / "02_records.jsonl",
            judgments_path=judgments_path,
        )
    )
    return summary


def _read_tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }



def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("qualify", "smoke", "review"))
    parser.add_argument("--project-root", default=str(REPO_ROOT))
    parser.add_argument("--pack-dir", default="")
    parser.add_argument("--pack-blob-prefix", default="")
    parser.add_argument("--blob-account", default="")
    parser.add_argument("--blob-container", default="")
    parser.add_argument("--out-blob-prefix", default="")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--client-id", default="")
    parser.add_argument("--code-commit", default="")
    parser.add_argument("--image-digest", default="")
    args = parser.parse_args(argv)

    root = Path(args.project_root).resolve()
    book = contract.load_addendum(root)
    contract.assert_matches_frozen_form(REVIEW_FORM_PRESENTED_FIELDS)
    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "_review_out"
    run_id = args.run_id or time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())

    print(f"ADDENDUM_SHA256={book.sha256}")
    print(f"RUBRIC_SHA256={book.rubric_sha256}")
    print(f"BASE_PROTOCOL_SHA256={book.document['base_protocol_sha256']}")

    tokens = transport.TokenProvider(args.client_id or None)
    caller = LiveCaller(book, tokens)

    qualification = _qualify(book, caller)
    for role, receipt in qualification.items():
        print(
            f"QUALIFIED role={role} deployment={receipt['deployment']} "
            f"model={receipt['model']}:{receipt['model_version']} "
            f"path={receipt['proven_path']} api_version={receipt['proven_api_version'] or '-'}"
        )

    if args.mode == "qualify":
        receipt = {
            "artifact": "phase1_0d_provider_qualification_receipt",
            "run_id": run_id,
            "addendum_sha256": book.sha256,
            "rubric_sha256": book.rubric_sha256,
            "roles": qualification,
            "scientific": False,
            "claim_boundary": (
                "proves only that the exact pinned deployments answer over a "
                "registered route with managed-identity authentication"
            ),
        }
        path = out_dir / f"provider_qualification_{run_id}.json"
        print(f"RECEIPT_SHA256={_write(path, contract.canonical_json(receipt))}")
        print(f"RECEIPT_PATH={path}")
        print("QUALIFY_COMPLETE=1")
        return 0

    if args.mode == "smoke":
        result = _smoke(book, caller)
        receipt = {
            "artifact": "phase1_0d_provider_smoke_receipt",
            "run_id": run_id,
            "addendum_sha256": book.sha256,
            "rubric_sha256": book.rubric_sha256,
            "roles": qualification,
            "expected_labels_committed_before_calls": True,
            "scientific": False,
            **result,
        }
        path = out_dir / f"provider_smoke_{run_id}.json"
        print(f"RECEIPT_SHA256={_write(path, contract.canonical_json(receipt))}")
        print(f"RECEIPT_PATH={path}")
        for row in result["fixtures"]:
            print(
                f"SMOKE fixture={row['fixture_id']} role={row['role']} "
                f"expected={row['expected_label']} observed={row['observed_label']} "
                f"match={row['match']}"
            )
        if not result["passed"]:
            print("BLOCKED_ON_SEMANTIC_REVIEW_PROVIDER_BEFORE_GENERATION")
            return 1
        print("SMOKE_COMPLETE=1")
        return 0

    blob = None
    if args.blob_account and args.blob_container:
        blob = transport.BlobClient(args.blob_account, args.blob_container, tokens)

    pack_dir = Path(args.pack_dir).resolve() if args.pack_dir else out_dir / "generation"
    download: dict[str, Any] | None = None
    if args.pack_blob_prefix:
        if blob is None:
            raise SystemExit("a blob pack prefix needs --blob-account and --blob-container")
        download = download_pack(blob, args.pack_blob_prefix.rstrip("/"), pack_dir)
        print(f"PACK_FILES={download['file_count']}")
    elif not args.pack_dir:
        raise SystemExit("review mode requires --pack-dir or --pack-blob-prefix")

    summary = _review(book, caller, pack_dir, out_dir, run_id)
    summary["provider_qualification"] = qualification
    summary["pack_download"] = download

    # Stage 8: the frozen finalizer decides; this wrapper only supplies bytes.
    final_dir = out_dir / "final"
    finalization = finalize_pack(
        project_root=root,
        pack_dir=pack_dir,
        judgments_path=Path(summary["judgments_path"]),
        out_root=final_dir,
        run_id=run_id,
        code_commit=args.code_commit or "not_recorded",
        image_digest=args.image_digest or "not_recorded",
    )
    final_pack = Path(finalization["output_dir"])
    summary["finalization"] = finalization
    print(f"FINAL_RESULT={finalization['result']}")

    # Stage 9: recompute; never choose.
    finalized_records = stages.load_records(final_pack / "02_records.jsonl")
    decision = json.loads((final_pack / "05_decision.json").read_text(encoding="utf-8"))
    combined = json.loads(Path(summary["judgments_path"]).read_text(encoding="utf-8"))
    check = stages.independent_check(
        records=finalized_records,
        decision=decision,
        combined=combined,
        required_secondary=summary["secondary_selection"]["required_ids"],
        required_third=summary["third_selection"]["required_ids"],
    )
    summary["independent_check"] = check
    print(f"INDEPENDENT_CHECK_DECISION_SHA256={check['decision_sha256']}")

    summary["execution_receipt"] = stages.outer_receipt(
        artifact="phase1_0d_semantic_review_execution_receipt",
        run_id=run_id,
        addendum_sha256=book.sha256,
        rubric_sha256=book.rubric_sha256,
        base_protocol_sha256=book.document["base_protocol_sha256"],
        generation_pack_manifest_sha256=summary["verification"]["manifest_sha256"],
        generation_records_sha256=summary["verification"]["records_sha256"],
        all_judgments_sha256=summary["all_judgments_sha256"],
        review_image_digest=args.image_digest or "not_recorded",
        review_code_commit=args.code_commit or "not_recorded",
        reviewer_authority="registered under DR-01; LLM operational consensus, not human ground truth",
    )
    path = out_dir / "review_stage_summary.json"
    print(f"SUMMARY_SHA256={_write(path, contract.canonical_json(summary))}")
    _write(
        out_dir / "00_execution_receipt.json",
        contract.canonical_json(summary["execution_receipt"]),
    )

    # Stage 10: outer bundle, manifest last, create-only.
    if args.out_blob_prefix:
        if blob is None:
            raise SystemExit("an output prefix needs --blob-account and --blob-container")
        files: dict[str, bytes] = {}
        files.update(
            {f"generation/{name}": payload for name, payload in _read_tree(pack_dir).items()}
        )
        files.update(
            {f"final/{name}": payload for name, payload in _read_tree(final_pack).items()}
        )
        for name, payload in _read_tree(out_dir).items():
            if name.startswith("generation/") or name.startswith("final/"):
                continue
            files[name] = payload
        published = publish_bundle(blob, args.out_blob_prefix.rstrip("/"), files, run_id)
        print(f"BUNDLE_FILES={published['uploaded_count']}")
        print(f"BUNDLE_MANIFEST_SHA256={published['manifest_sha256']}")

    print(f"ALL_JUDGMENTS={summary['judgments_path']}")
    print(f"ALL_JUDGMENTS_SHA256={summary['all_judgments_sha256']}")
    print(f"SECONDARY_REQUIRED={summary['secondary_selection']['required_count']}")
    print(f"THIRD_REQUIRED={summary['third_selection']['required_count']}")
    print("REVIEW_STAGES_COMPLETE=1")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI
    raise SystemExit(main())
