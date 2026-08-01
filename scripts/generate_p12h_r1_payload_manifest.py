#!/usr/bin/env python3
"""Generate and verify the Phase 1.2H-R1 access-image payload manifest.

The access image carries exactly five files. Each is pinned by LF-normalized
SHA-256 so that a build cannot quietly ship a probe, a schema or a frozen
binding that differs from the reviewed commit.

Keeping the digests in one generated manifest rather than inline in the
Dockerfile means there is a single place to regenerate and a single place to
check, and ``--check`` makes drift a test failure rather than a review
oversight.

    python scripts/generate_p12h_r1_payload_manifest.py            # write
    python scripts/generate_p12h_r1_payload_manifest.py --check    # verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "infra" / "azure" / "phase1_2h_r1_image_payload.json"

# The complete payload. Nothing else may enter the image, and in particular no
# parser module, no evaluator source and no private material.
PAYLOAD = (
    "scripts/phase1_2h_r1_private_source_probe.py",
    "scripts/phase1_2h_r1_receipt_validator.py",
    "docs/phase1_2h_r1_access_decision_record.json",
    "docs/phase1_2h_r1_access_receipt.schema.json",
    # Added after independent Audit A (A-09) and Audit B (B-08): the probe now
    # validates its refusal receipts too, so the refusal schema is read at
    # runtime. Without it in the image, every refusal path would crash instead
    # of emitting the content-free document the refusal contract promises.
    "docs/phase1_2h_r1_access_refusal_receipt.schema.json",
    "artifacts/phase1-evaluator-validation/track-d1/"
    "20260725T160340Z-track-d1-parser-v3-seal/02_records.jsonl",
)


def lf_sha256(path: Path) -> str:
    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(lf).hexdigest()


def build() -> dict:
    return {
        "schema_version": "phase1-2h-r1-image-payload/v1",
        "phase": "1.2H-R1",
        "purpose": (
            "LF-normalized SHA-256 of every file baked into the Phase 1.2H-R1 "
            "byte-only access image. The image build fails if any file differs."
        ),
        "digest_algorithm": "sha256",
        "line_ending_normalization": "CRLF and CR are normalized to LF before digesting",
        "payload": [
            {"path": rel, "sha256": lf_sha256(ROOT / rel)} for rel in PAYLOAD
        ],
        "excluded_by_construction": [
            "any parser module (eval_parsing.py, eval_parsing_v2.py, eval_parsing_v3.py)",
            "the jspace_observation package, whose __init__ eagerly imports the legacy parser",
            "any sealed input, label, prediction or curator artifact",
            "any credential, secret, connection string or SAS token",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    current = build()
    rendered = json.dumps(current, indent=2, ensure_ascii=False) + "\n"

    if args.check:
        if not MANIFEST.exists():
            print("payload manifest: FAIL: manifest does not exist")
            return 1
        committed = MANIFEST.read_text(encoding="utf-8").replace("\r\n", "\n")
        if committed != rendered:
            print(
                "payload manifest: FAIL: manifest is stale. Re-run "
                "scripts/generate_p12h_r1_payload_manifest.py"
            )
            return 1
        print("payload manifest: OK")
        return 0

    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"payload manifest: wrote {MANIFEST.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
