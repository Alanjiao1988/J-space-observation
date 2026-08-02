"""Run one read-only public audit of an exact candidate commit.

This program is the auditor harness. It never runs on the laptop: it is executed
inside an Azure runner, it reads only tracked public files from a verified clean
checkout of one exact commit, and it sends them to an Azure OpenAI deployment
that returns a structured finding list.

The harness is deliberately dumb about the audit's content. Everything the
auditor is told lives in committed Markdown under ``docs/audits/`` so that the
instruction is itself auditable, and the property list the auditor must answer
is parsed out of that Markdown rather than restated here.

What the harness does guarantee:

* the checkout is exactly the declared commit and has no local modification;
* every material file is hashed, and the report is bound to the digest of that
  manifest, so a report cannot be quietly re-used against different bytes;
* the returned object is validated against the closed output contract before it
  is accepted, so a malformed or padded answer fails loudly instead of being
  filed as an audit;
* the accepted report is emitted base64-encoded with its own digest, because the
  only channel back out of the runner is the run log and a log must not be
  allowed to silently reflow the bytes.

Usage inside the runner::

    python tools/run_public_audit.py --audit a --commit <sha> \
        --endpoint https://<account>.openai.azure.com/ --deployment <name>

The API key is read from ``AZURE_OPENAI_API_KEY`` and is never logged.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

FRAME = "docs/audits/phase_a_public_audit_frame.md"

# The material each audit may see. These lists are closed: the auditor receives
# exactly these files and nothing else, so a finding can always be traced to
# bytes that were actually in front of it.
MATERIAL = {
    "A": (
        "docs/audits/phase_a_public_audit_scope_a.md",
        (
            "src/jspace_observation/parser_v3_v2_lifecycle.py",
            "src/jspace_observation/parser_v3_v2_construction.py",
            "src/jspace_observation/parser_v3_v2_evaluation.py",
            "tests/test_parser_v3_v2_rehearsal_entrypoints.py",
            "tests/test_parser_v3_v2_rehearsal.py",
            "docs/phase1_parser_v3_v2_stratum_policy.md",
            "docs/phase1_2h_independent_set_repair_protocol.md",
        ),
    ),
    "B": (
        "docs/audits/phase_a_public_audit_scope_b.md",
        (
            "src/jspace_observation/parser_v3_v2_entrypoints.py",
            "src/jspace_observation/parser_v3_v2_schemas.py",
            "tests/test_parser_v3_v2_boundary_iac.py",
            "infra/azure/parser_v3_v2_boundary/main.bicep",
            "infra/azure/parser_v3_v2_boundary/modules/network.bicep",
            "infra/azure/parser_v3_v2_boundary/modules/privatelink.bicep",
            "infra/azure/parser_v3_v2_boundary/modules/storage_access.bicep",
            "infra/azure/parser_v3_v2_boundary/modules/workload.bicep",
            "infra/azure/parser_v3_v2_boundary/modules/assert_no_overlap.bicep",
            "infra/azure/parser_v3_v2_boundary/modules/observability.bicep",
            "infra/azure/parser_v3_v2_boundary/role_matrix.json",
            "infra/azure/parser_v3_v2_boundary/address_plan.json",
            ".dockerignore",
            ".gitattributes",
        ),
    ),
}

SEVERITIES = ("BLOCKER", "MAJOR", "MINOR", "INFO")
DISPOSITIONS = ("REMEDIATE_BEFORE_FREEZE", "ACCEPT_WITH_DISCLOSURE", "NO_ACTION")
VERDICTS = ("HOLDS", "VIOLATED", "UNVERIFIABLE")
OVERALL = ("READY_FOR_FREEZE", "NOT_READY_FOR_FREEZE")

REPORT_KEYS = {
    "audit_id",
    "candidate_commit",
    "material_digest",
    "summary",
    "findings",
    "properties_checked",
    "unverifiable_without_private_material",
    "overall_verdict",
}
FINDING_KEYS = {
    "id",
    "title",
    "area",
    "severity",
    "evidence",
    "reproduction",
    "disposition",
    "residual_limitation",
}
PROPERTY_KEYS = {"property", "verdict", "evidence"}


class AuditError(RuntimeError):
    """The audit could not be carried out, or its answer was not usable."""


def _git(*args: str) -> str:
    done = subprocess.run(
        ("git",) + args, check=True, capture_output=True, text=True
    )
    return done.stdout.strip()


def verify_checkout(commit: str) -> str:
    """Refuse to audit anything but the declared commit, unmodified."""
    head = _git("rev-parse", "HEAD")
    if head != commit:
        raise AuditError(f"checkout is {head}, declared candidate is {commit}")
    dirty = _git("status", "--porcelain")
    if dirty:
        raise AuditError(f"checkout is modified:\n{dirty}")
    return _git("rev-parse", "HEAD^{tree}")


def read_material(paths):
    """Return the material blob and a digest manifest over its exact bytes."""
    entries = []
    chunks = []
    for path in paths:
        with open(path, "rb") as handle:
            raw = handle.read()
        entries.append(
            {
                "path": path,
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        text = raw.decode("utf-8")
        chunks.append(f"===== BEGIN FILE {path} =====\n{text}\n===== END FILE {path} =====\n")
    manifest = json.dumps(entries, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(manifest.encode("utf-8")).hexdigest()
    return "\n".join(chunks), entries, digest


def parse_properties(scope_text: str):
    """Pull the numbered property list out of the committed scope document."""
    marker = "## Properties to check"
    if marker not in scope_text:
        raise AuditError(f"scope document has no {marker!r} section")
    tail = scope_text.split(marker, 1)[1]
    found = re.findall(r"^\d+\.\s+(.*?)\s*$", tail, flags=re.MULTILINE)
    if not found:
        raise AuditError("scope document lists no properties")
    return tuple(found)


def _post(url: str, key: str, payload: dict, attempts: int = 6) -> dict:
    """POST with backoff on throttling; raise on anything else."""
    body = json.dumps(payload).encode("utf-8")
    delay = 20.0
    last = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "api-key": key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=1800) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", "replace")[:600]
            last = f"HTTP {error.code}: {detail}"
            if error.code in (429, 503):
                wait = float(error.headers.get("Retry-After") or delay)
                print(f"  throttled, waiting {wait:.0f}s "
                      f"(attempt {attempt + 1}/{attempts})", flush=True)
                time.sleep(wait)
                delay = min(delay * 2, 180.0)
                continue
            raise AuditError(last) from error
        except urllib.error.URLError as error:
            last = f"transport error: {error}"
            print(f"  {last}, retrying", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 180.0)
    raise AuditError(f"gave up after {attempts} attempts; last was {last}")


def _extract(answer: dict) -> str:
    """Pull the assistant text out of either API shape."""
    if "choices" in answer:
        return answer["choices"][0]["message"]["content"] or ""
    parts = []
    for item in answer.get("output", ()):
        if item.get("type") != "message":
            continue
        for piece in item.get("content", ()):
            if piece.get("type") in ("output_text", "text"):
                parts.append(piece.get("text", ""))
    if not parts and isinstance(answer.get("output_text"), str):
        parts.append(answer["output_text"])
    return "".join(parts)


def ask(endpoint: str, deployment: str, key: str, instruction: str, material: str) -> tuple:
    """Send one audit and return (raw text, which API shape answered)."""
    base = endpoint.rstrip("/")
    user = (
        "MATERIAL BEGINS. Everything between the markers is the complete and only "
        "material for this audit.\n\n" + material + "\nMATERIAL ENDS."
    )
    shapes = (
        (
            "responses",
            f"{base}/openai/v1/responses",
            {
                "model": deployment,
                "instructions": instruction,
                "input": user,
                "max_output_tokens": 32000,
                "text": {"format": {"type": "json_object"}},
            },
        ),
        (
            "responses-plain",
            f"{base}/openai/v1/responses",
            {
                "model": deployment,
                "instructions": instruction,
                "input": user,
                "max_output_tokens": 32000,
            },
        ),
        (
            "chat",
            f"{base}/openai/deployments/{deployment}/chat/completions"
            "?api-version=2025-01-01-preview",
            {
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user},
                ],
                "max_completion_tokens": 32000,
                "response_format": {"type": "json_object"},
            },
        ),
        (
            "chat-plain",
            f"{base}/openai/deployments/{deployment}/chat/completions"
            "?api-version=2025-01-01-preview",
            {
                "messages": [
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": user},
                ],
                "max_completion_tokens": 32000,
            },
        ),
    )
    problems = []
    for name, url, payload in shapes:
        print(f"  trying {name}", flush=True)
        try:
            answer = _post(url, key, payload)
        except AuditError as error:
            problems.append(f"{name}: {error}")
            continue
        text = _extract(answer)
        if not text.strip():
            problems.append(f"{name}: empty completion ({json.dumps(answer)[:400]})")
            continue
        return text, name
    raise AuditError("no API shape produced a completion:\n  " + "\n  ".join(problems))


def coerce_json(text: str) -> dict:
    """Accept the object even if the model wrapped it in a fence."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n", "", stripped)
        stripped = re.sub(r"\n```\s*$", "", stripped)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start, end = stripped.find("{"), stripped.rfind("}")
        if start == -1 or end <= start:
            raise AuditError(f"answer is not JSON:\n{stripped[:800]}")
        return json.loads(stripped[start:end + 1])


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def validate(report, audit_id: str, commit: str, digest: str, properties) -> list:
    """Enforce the closed output contract. Returns non-fatal warnings."""
    if not isinstance(report, dict):
        raise AuditError("report is not an object")
    missing = REPORT_KEYS - set(report)
    extra = set(report) - REPORT_KEYS
    if missing or extra:
        raise AuditError(f"report keys wrong; missing={sorted(missing)} extra={sorted(extra)}")

    warnings = []
    if report["audit_id"] != audit_id:
        warnings.append(f"audit_id was {report['audit_id']!r}; forcing {audit_id!r}")
        report["audit_id"] = audit_id
    if report["candidate_commit"] != commit:
        warnings.append(
            f"candidate_commit was {report['candidate_commit']!r}; forcing the real one"
        )
        report["candidate_commit"] = commit
    if report["material_digest"] != digest:
        warnings.append(
            f"material_digest was {report['material_digest']!r}; forcing the real one"
        )
        report["material_digest"] = digest

    if not isinstance(report["summary"], str):
        raise AuditError("summary is not a string")
    if not isinstance(report["findings"], list):
        raise AuditError("findings is not a list")
    if not isinstance(report["unverifiable_without_private_material"], list):
        raise AuditError("unverifiable_without_private_material is not a list")
    if report["overall_verdict"] not in OVERALL:
        raise AuditError(f"overall_verdict {report['overall_verdict']!r} is not registered")

    seen = set()
    for finding in report["findings"]:
        if not isinstance(finding, dict):
            raise AuditError("a finding is not an object")
        gap = FINDING_KEYS - set(finding)
        over = set(finding) - FINDING_KEYS
        if gap or over:
            raise AuditError(f"finding keys wrong; missing={sorted(gap)} extra={sorted(over)}")
        if finding["severity"] not in SEVERITIES:
            raise AuditError(f"severity {finding['severity']!r} is not registered")
        if finding["disposition"] not in DISPOSITIONS:
            raise AuditError(f"disposition {finding['disposition']!r} is not registered")
        if not re.fullmatch(rf"{audit_id}-\d\d", str(finding["id"])):
            warnings.append(f"finding id {finding['id']!r} is not {audit_id}-NN")
        if finding["id"] in seen:
            raise AuditError(f"duplicate finding id {finding['id']!r}")
        seen.add(finding["id"])
        for field in ("evidence", "reproduction"):
            if not str(finding[field]).strip():
                raise AuditError(f"finding {finding['id']} has empty {field}")
        if finding["severity"] in ("BLOCKER", "MAJOR"):
            if finding["disposition"] != "REMEDIATE_BEFORE_FREEZE":
                raise AuditError(
                    f"finding {finding['id']} is {finding['severity']} but disposed "
                    f"{finding['disposition']}"
                )

    material = any(f["severity"] in ("BLOCKER", "MAJOR") for f in report["findings"])
    expected = "NOT_READY_FOR_FREEZE" if material else "READY_FOR_FREEZE"
    if report["overall_verdict"] != expected:
        raise AuditError(
            f"overall_verdict {report['overall_verdict']!r} contradicts the findings; "
            f"the contract requires {expected!r}"
        )

    checked = report["properties_checked"]
    if not isinstance(checked, list):
        raise AuditError("properties_checked is not a list")
    if len(checked) != len(properties):
        raise AuditError(
            f"properties_checked has {len(checked)} entries; the scope lists {len(properties)}"
        )
    for index, (entry, wanted) in enumerate(zip(checked, properties), start=1):
        if not isinstance(entry, dict) or set(entry) != PROPERTY_KEYS:
            raise AuditError(f"properties_checked[{index}] keys wrong")
        if entry["verdict"] not in VERDICTS:
            raise AuditError(f"properties_checked[{index}] verdict {entry['verdict']!r}")
        if _norm(entry["property"]) != _norm(wanted):
            warnings.append(
                f"properties_checked[{index}] was restated rather than copied; "
                f"restoring the scope text"
            )
            entry["property"] = wanted
    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", required=True, choices=("a", "b", "A", "B"))
    parser.add_argument("--commit", required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--model-label", required=True,
                        help="the model family/name, recorded in the report envelope")
    args = parser.parse_args()

    audit_id = args.audit.upper()
    key = os.environ.get("AZURE_OPENAI_API_KEY", "")
    if not key:
        raise AuditError("AZURE_OPENAI_API_KEY is not set")

    tree = verify_checkout(args.commit)
    scope_path, paths = MATERIAL[audit_id]
    with open(scope_path, encoding="utf-8") as handle:
        scope_text = handle.read()
    with open(FRAME, encoding="utf-8") as handle:
        frame_text = handle.read()
    properties = parse_properties(scope_text)

    material, entries, digest = read_material(paths)
    header = (
        f"CANDIDATE COMMIT: {args.commit}\n"
        f"CANDIDATE TREE:   {tree}\n"
        f"AUDIT ID:         {audit_id}\n"
        f"MATERIAL DIGEST:  {digest}\n"
    )
    instruction = f"{frame_text}\n\n{scope_text}\n\n## This audit\n\n{header}"

    print(f"audit {audit_id}: {len(entries)} files, "
          f"{sum(e['bytes'] for e in entries)} bytes, digest {digest[:16]}", flush=True)
    for entry in entries:
        print(f"  {entry['sha256'][:16]}  {entry['bytes']:>7}  {entry['path']}", flush=True)

    started = time.time()
    text, shape = ask(args.endpoint, args.deployment, key, instruction, material)
    elapsed = time.time() - started
    print(f"  answered via {shape} in {elapsed:.0f}s, {len(text)} characters", flush=True)

    report = coerce_json(text)
    warnings = validate(report, audit_id, args.commit, digest, properties)
    for warning in warnings:
        print(f"  WARNING: {warning}", flush=True)

    envelope = {
        "schema_version": "phase1-parser-v3-v2-public-audit/v1",
        "audit_id": audit_id,
        "candidate_commit": args.commit,
        "candidate_tree": tree,
        "material": entries,
        "material_digest": digest,
        "frame_sha256": hashlib.sha256(frame_text.encode("utf-8")).hexdigest(),
        "scope_path": scope_path,
        "scope_sha256": hashlib.sha256(scope_text.encode("utf-8")).hexdigest(),
        "runner": "azure-container-registry-task",
        "backend": "azure-openai",
        "model": args.model_label,
        "deployment": args.deployment,
        "api_shape": shape,
        "harness_warnings": warnings,
        "report": report,
    }
    serialized = json.dumps(envelope, indent=2, sort_keys=True) + "\n"
    raw = serialized.encode("utf-8")

    counts = {level: 0 for level in SEVERITIES}
    for finding in report["findings"]:
        counts[finding["severity"]] += 1
    print(f"  verdict {report['overall_verdict']}; "
          + ", ".join(f"{k}={v}" for k, v in counts.items()), flush=True)

    encoded = base64.b64encode(raw).decode("ascii")
    print(f"=====AUDIT {audit_id} BEGIN sha256={hashlib.sha256(raw).hexdigest()} "
          f"bytes={len(raw)}=====", flush=True)
    for start in range(0, len(encoded), 100):
        print(encoded[start:start + 100], flush=True)
    print(f"=====AUDIT {audit_id} END=====", flush=True)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except AuditError as error:
        print(f"AUDIT HARNESS REFUSED: {error}", file=sys.stderr, flush=True)
        sys.exit(2)
