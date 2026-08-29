import hashlib
import json
import pathlib
import subprocess

ROOT = pathlib.Path(
    r"C:\Users\alanjiao\.copilot\repos\copilot-worktrees"
    r"\J-space-observation\alanjiao1988-upgraded-sniffle"
)

# Every predecessor namespace, and the commit at which each was sealed.
SEALED = [
    ("studies/study5/qualification-eq1", "a28ae6a"),
    ("studies/study5/qualification-eq2", "a28ae6a"),
    ("studies/study5/prompts", "f88b2a6"),
    ("studies/study5/validation-p0", "9556c40"),
    ("studies/study5/validation-p0-prime", "e948134"),
    ("studies/study5/validation-p0c", "f88b2a6"),
]


def run(args):
    return subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def tree_digest(namespace, ref=None):
    """A content digest over every file in a namespace, path-ordered.

    Comparing a digest of the whole tree is stronger than a diff summary: it
    fails on a byte anywhere, including in a file git might report as merely
    renamed.
    """
    if ref:
        listing = run(["git", "ls-tree", "-r", "--name-only", ref, "--", namespace])
    else:
        listing = run(["git", "ls-tree", "-r", "--name-only", "HEAD", "--", namespace])
    paths = sorted(p for p in listing.splitlines() if p.strip())
    digest = hashlib.sha256()
    for path in paths:
        blob = run(["git", "show", f"{ref or 'HEAD'}:{path}"])
        digest.update(path.encode("utf-8"))
        digest.update(hashlib.sha256(blob.encode("utf-8")).hexdigest().encode())
    return digest.hexdigest(), len(paths)


results = []
all_ok = True
for namespace, sealed_at in SEALED:
    then, n_then = tree_digest(namespace, sealed_at)
    now, n_now = tree_digest(namespace, None)
    identical = then == now and n_then == n_now
    all_ok = all_ok and identical
    results.append(
        {
            "namespace": namespace,
            "sealed_at_commit": sealed_at,
            "files_then": n_then,
            "files_now": n_now,
            "tree_digest_then": then,
            "tree_digest_now": now,
            "byte_identical": identical,
        }
    )
    print(
        f"  {'IDENTICAL' if identical else 'CHANGED':10} {namespace:44} "
        f"{n_now:4} files  {now[:16]}..."
    )

report = {
    "schema_version": "study5-closure-integrity-v1",
    "recorded_at_utc": "2026-08-29T05:55:00Z",
    "method": (
        "for each sealed namespace, a sha256 over every file's path and content "
        "digest in path order, computed at the sealing commit and at HEAD, and "
        "compared. A whole-tree digest fails on a byte anywhere, which a diff "
        "summary alone would not guarantee"
    ),
    "namespaces": results,
    "all_byte_identical": all_ok,
    "claim_ceiling": "An integrity record. It licenses no claim of any kind.",
}
out = ROOT / "studies/study5/closure/PREDECESSOR_INTEGRITY.json"
out.write_bytes(
    json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
)
print()
print(f"all byte-identical: {all_ok}")
print(f"namespaces verified: {len(results)}")
print(f"files verified: {sum(r['files_now'] for r in results)}")
