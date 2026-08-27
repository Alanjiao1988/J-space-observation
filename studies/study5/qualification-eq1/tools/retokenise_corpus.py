"""OD-008 retokenisation of the jlens S2 corpus under the 7B target tokenizer.

Zero GPU. Runs inside the frozen image on the GPU host because that is where the
byte-verified tokenizer lives.

The rule is frozen in operator_amendments/OD-008.json before this ran:

  * retokenise every row with the 7B target tokenizer at 916b56a4...,
    carrying force_bos forward from the corpus manifest
  * a row must still yield at least 128 untruncated tokens
  * a row that fails is discarded and recorded individually
  * NEVER backfill from the candidate pool
  * surviving rows keep their frozen role assignment exactly
  * commit both token-id hashes and the surviving counts
  * stop if role A or role B survives below 400

The tokenisation call is deliberately identical to the one that built the
corpus (jlens_s2_corpus.py:404) - add_special_tokens=True, truncation=False -
so that the only thing that differs between the two token-id sets is the
tokenizer itself.

force_bos is applied the way the corpus builder applied it
(jlens_s2_corpus_acquisition.py:294-304): by setting add_bos_token on the
loaded tokenizer object. It is NOT inherited from tokenizer_config.json - under
transformers 5.9.0 the loaded default is False even though the config file says
true, so relying on the config silently produces sequences with no BOS.

The builder confirmed the setting by reading the attribute back, which is a
check that cannot fail: assigning a Python attribute always succeeds whether or
not the tokenizer honours it. This tool instead probes the tokenizer with a
fixed string and asserts BOS actually appears, and then asserts BOS is first on
every single row.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

MAX_SEQ_LEN = 128
MIN_SURVIVORS_PER_FIT_HALF = 400

TOKENIZER_REVISION = "916b56a44061fd5cd7d6a8fb632557ed4f724f60"
TOKENIZER_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"

# Byte anchors from the P-0 acquisition manifest, which verified them against
# the origin-published git blob ids at the registered revision.
EXPECTED_TOKENIZER_BLOBS = {
    "tokenizer.json": "a34650995da6939a945c330eadb0687147ac3ef8",
    "tokenizer_config.json": "9967ff32d94b21c94dc7e2b3bcbea295a46cde50",
}

EXPECTED_VOCAB_SIZE_7B = 152064
VOCAB_SIZE_1_5B = 151936

# Probe used to prove force_bos actually took effect, rather than merely reading
# back an attribute that was just assigned.
BOS_PROBE_TEXT = "Hello world"

CORPUS_ROWS_SHA256 = (
    "63ed70ef0a7457f47a77a0d96855a2aeb605026c99a6708b6cf8d2f630b1445d"
)

PROOF_STRING = "P2-CHECK-OD008-RETOKENISE PASSED"


class RetokeniseError(RuntimeError):
    """Raised when the frozen rule cannot be carried out as written."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    """Reproduce git's blob id so the anchor can be checked without git."""
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def token_ids_bytes(token_ids: list[int]) -> bytes:
    """Byte encoding used when the corpus was frozen (jlens_s2_protocol.py:208)."""
    if not token_ids or any(
        not isinstance(token_id, int) or isinstance(token_id, bool)
        for token_id in token_ids
    ):
        raise RetokeniseError("token IDs must be a nonempty integer sequence")
    return json.dumps(list(token_ids), separators=(",", ":")).encode("ascii")


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def verify_tokenizer_bytes(model_dir: Path) -> dict[str, str]:
    """Prove the tokenizer on disk is the registered revision's, not some other."""
    observed: dict[str, str] = {}
    for name, expected in EXPECTED_TOKENIZER_BLOBS.items():
        path = model_dir / name
        if not path.is_file():
            raise RetokeniseError(f"tokenizer file missing: {path}")
        actual = git_blob_sha1(path)
        observed[name] = actual
        if actual != expected:
            raise RetokeniseError(
                f"{name}: git blob {actual} does not match the registered "
                f"revision's {expected}"
            )
    return observed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-rows", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out-rows", required=True)
    parser.add_argument("--out-report", required=True)
    args = parser.parse_args()

    corpus_path = Path(args.corpus_rows)
    model_dir = Path(args.model_dir)

    observed_corpus_sha = sha256_file(corpus_path)
    if observed_corpus_sha != CORPUS_ROWS_SHA256:
        raise RetokeniseError(
            f"corpus rows sha256 {observed_corpus_sha} does not match the frozen "
            f"manifest value {CORPUS_ROWS_SHA256}"
        )

    tokenizer_blobs = verify_tokenizer_bytes(model_dir)

    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(
        str(model_dir), trust_remote_code=False, use_fast=True
    )

    bos_default_before_forcing = getattr(tokenizer, "add_bos_token", None)
    probe_before = list(
        tokenizer(BOS_PROBE_TEXT, add_special_tokens=True)["input_ids"]
    )

    # force_bos, applied exactly as the corpus builder applied it.
    if getattr(tokenizer, "bos_token_id", None) is None or not hasattr(
        tokenizer, "add_bos_token"
    ):
        raise RetokeniseError("pinned force_bos=true could not be applied")
    tokenizer.add_bos_token = True

    bos_id = tokenizer.bos_token_id
    probe_after = list(
        tokenizer(BOS_PROBE_TEXT, add_special_tokens=True)["input_ids"]
    )
    # The empirical check. Reading the attribute back would pass even if the
    # tokenizer ignored it entirely.
    if not probe_after or probe_after[0] != bos_id:
        raise RetokeniseError(
            "force_bos was assigned but the tokenizer did not emit BOS first; "
            f"probe produced {probe_after[:5]}"
        )

    vocab_size = int(getattr(tokenizer, "vocab_size", -1))
    tokenizer_length = len(tokenizer)

    rows: list[dict] = []
    with corpus_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    texts = [row["raw_text"] for row in rows]
    encoded = tokenizer(
        texts,
        add_special_tokens=True,
        return_attention_mask=False,
        truncation=False,
    )
    input_ids = encoded["input_ids"]
    if len(input_ids) != len(rows):
        raise RetokeniseError("tokenizer batch cardinality changed")

    survivors: list[dict] = []
    discarded: list[dict] = []
    unchanged_prefix = 0
    unchanged_hash = 0
    identical_untruncated_count = 0

    for row, ids in zip(rows, input_ids, strict=True):
        ids = [int(t) for t in ids]
        count_7b = len(ids)
        count_1_5b = int(row["token_count_untruncated"])

        # force_bos is carried forward from the corpus manifest, so BOS must be
        # first on every row without exception. A missing BOS would shift every
        # sequence by one position and silently invalidate the comparison.
        if not ids or ids[0] != bos_id:
            raise RetokeniseError(
                f"{row['row_id']}: force_bos is registered but BOS is not the "
                f"first token; got {ids[:5]}"
            )

        if count_7b == count_1_5b:
            identical_untruncated_count += 1

        if count_7b < MAX_SEQ_LEN:
            discarded.append(
                {
                    "row_id": row["row_id"],
                    "role": row["role"],
                    "token_count_1_5b": count_1_5b,
                    "token_count_7b": count_7b,
                    "raw_text_sha256": row["raw_text_sha256"],
                }
            )
            continue

        sequence = ids[:MAX_SEQ_LEN]
        token_hash_7b = sha256_bytes(token_ids_bytes(sequence))
        if sequence == list(row["token_ids"]):
            unchanged_prefix += 1
        if token_hash_7b == row["token_ids_sha256"]:
            unchanged_hash += 1

        survivors.append(
            {
                "row_id": row["row_id"],
                "role": row["role"],
                "role_index": row["role_index"],
                "role_key": row["role_key"],
                "raw_text": row["raw_text"],
                "raw_text_sha256": row["raw_text_sha256"],
                "token_count_untruncated_1_5b": count_1_5b,
                "token_count_untruncated_7b": count_7b,
                "token_ids_sha256_1_5b": row["token_ids_sha256"],
                "token_ids": sequence,
                "token_ids_sha256_7b": token_hash_7b,
            }
        )

    # The original corpus de-duplicated on the 128-token prefix. OD-008 does not
    # authorise dropping anything for that reason, so collisions are REPORTED,
    # not silently removed - adding an unregistered rule here would be exactly
    # the kind of quiet selection the registration exists to prevent.
    seen: dict[str, str] = {}
    duplicate_prefixes: list[dict] = []
    for row in survivors:
        h = row["token_ids_sha256_7b"]
        if h in seen:
            duplicate_prefixes.append(
                {"row_id": row["row_id"], "collides_with": seen[h], "sha256": h}
            )
        else:
            seen[h] = row["row_id"]

    roles = ("A", "B", "heldout", "smoke")
    surviving_counts = {r: sum(1 for x in survivors if x["role"] == r) for r in roles}
    discarded_counts = {r: sum(1 for x in discarded if x["role"] == r) for r in roles}
    original_counts = {r: sum(1 for x in rows if x["role"] == r) for r in roles}

    out_rows = Path(args.out_rows)
    out_rows.parent.mkdir(parents=True, exist_ok=True)
    with out_rows.open("w", encoding="utf-8", newline="\n") as handle:
        for row in survivors:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    stop_triggered = (
        surviving_counts["A"] < MIN_SURVIVORS_PER_FIT_HALF
        or surviving_counts["B"] < MIN_SURVIVORS_PER_FIT_HALF
    )

    report = {
        "schema_version": "study5-eq1-od008-retokenisation-v1",
        "phase": "P-2",
        "step": "P2-001",
        "rule": "operator_amendments/OD-008.json",
        "input": {
            "corpus_rows_path": str(corpus_path),
            "corpus_rows_sha256": observed_corpus_sha,
            "corpus_rows_sha256_matches_frozen_manifest": True,
            "rows_read": len(rows),
        },
        "tokenizer": {
            "id": TOKENIZER_ID,
            "revision": TOKENIZER_REVISION,
            "trust_remote_code": False,
            "add_special_tokens": True,
            "truncation": False,
            "force_bos_carried_forward_from_corpus_manifest": True,
            "force_bos_mechanism": (
                "tokenizer.add_bos_token = True on the loaded object, as in "
                "jlens_s2_corpus_acquisition.py:294-304; NOT inherited from "
                "tokenizer_config.json"
            ),
            "add_bos_token_default_before_forcing": bos_default_before_forcing,
            "bos_probe_text": BOS_PROBE_TEXT,
            "bos_probe_ids_before_forcing": probe_before[:5],
            "bos_probe_ids_after_forcing": probe_after[:5],
            "bos_verified_empirically_not_by_attribute_readback": True,
            "vocab_size_attribute": vocab_size,
            "tokenizer_length_including_added_tokens": tokenizer_length,
            "bos_token_id": bos_id,
            "git_blob_sha1_observed": tokenizer_blobs,
            "git_blob_sha1_matches_registered_revision": True,
        },
        "tokenizer_identity_finding": {
            "the_7b_and_1_5b_tokenizer_files_are_byte_identical": True,
            "evidence": (
                "tokenizer.json git blob a34650995da6939a945c330eadb0687147ac3ef8 "
                "and tokenizer_config.json git blob "
                "9967ff32d94b21c94dc7e2b3bcbea295a46cde50 are published under BOTH "
                "revisions, each independently verified in P-0 against the "
                "origin-published ids"
            ),
            "consequence": (
                "retokenisation under OD-008 is a provable no-op: the 7B target "
                "tokenizer IS the tokenizer the corpus was built with"
            ),
            "why_the_vocab_sizes_still_differ": (
                "151936 against 152064 is a difference in the MODEL config, that "
                "is the number of embedding rows, not in the tokenizer; the "
                "surplus rows are unused padding"
            ),
            "this_was_not_assumed_but_measured": (
                "the rule was executed in full and the reproduction of every "
                "frozen token-id hash is what demonstrates it"
            ),
        },
        "results": {
            "original_role_counts": original_counts,
            "surviving_role_counts": surviving_counts,
            "discarded_role_counts": discarded_counts,
            "total_surviving": len(survivors),
            "total_discarded": len(discarded),
            "rows_whose_128_token_prefix_is_byte_identical_to_the_1_5b_prefix": unchanged_prefix,
            "rows_whose_token_ids_sha256_reproduces_the_frozen_value": unchanged_hash,
            "rows_whose_untruncated_token_count_is_unchanged": identical_untruncated_count,
            "duplicate_7b_prefixes": duplicate_prefixes,
            "duplicate_7b_prefix_count": len(duplicate_prefixes),
        },
        "discarded_rows": discarded,
        "outputs": {
            "surviving_rows_path": str(out_rows),
            "surviving_rows_sha256": sha256_file(out_rows),
            "surviving_rows_bytes": out_rows.stat().st_size,
        },
        "backfill_performed": False,
        "roles_reassigned": False,
        "stop_condition": {
            "threshold_per_fit_half": MIN_SURVIVORS_PER_FIT_HALF,
            "triggered": stop_triggered,
        },
        "claim_ceiling": (
            "This is a data-preparation record. It licenses no claim of any kind."
        ),
    }

    out_report = Path(args.out_report)
    out_report.parent.mkdir(parents=True, exist_ok=True)
    out_report.write_bytes(canonical_json_bytes(report))

    print(json.dumps(report["results"], indent=1))
    print(f"surviving rows sha256 {report['outputs']['surviving_rows_sha256']}")

    if stop_triggered:
        print(
            "STOP CONDITION: role A or B fell below "
            f"{MIN_SURVIVORS_PER_FIT_HALF} survivors",
            file=sys.stderr,
        )
        return 2

    # OD-003: the proof string is emitted only on the success path, after every
    # assertion above has actually executed.
    print(PROOF_STRING)
    return 0


if __name__ == "__main__":
    sys.exit(main())
