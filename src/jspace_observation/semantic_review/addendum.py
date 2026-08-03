"""The frozen semantic-review execution addendum: contract, requests, parsing.

The base Phase 1.0D protocol froze *what* a semantic review decides.  It never
named an executable reviewer, a label rubric a machine could follow, or a
request body.  This module is the other half: it turns the four presented
fields into an exact request for an exact pinned deployment, and turns exactly
one shape of response back into exactly one registered label.

Two properties matter more than convenience here:

*   nothing in this module may look at a target output before the addendum is
    frozen, so every parameter is read from the committed addendum rather than
    chosen at call time;
*   no failure may become a semantic label.  A transport failure and a
    malformed response each raise a distinct error whose terminal state the
    authority names, because "unresolved" and "no_answer" are *judgments* and
    would silently contaminate the denominator if we reused them for our own
    plumbing faults.

What this establishes: that a recorded judgment came from a specific
deployment, given specific bytes, under a rubric whose hash is committed.  What
it does not establish: that the reviewer is right.  No independent oracle
bounds reviewer accuracy, and inter-model agreement is consistency, not truth.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "phase1-0d-semantic-review-addendum/v1"
ADDENDUM_PATH = "docs/phase1_0d_semantic_review_addendum.json"
RUBRIC_PATH = "docs/phase1_0d_semantic_review_rubric.md"

#: Exactly the fields a reviewer may be shown.  Mirrors the frozen
#: ``REVIEW_FORM_PRESENTED_FIELDS``; asserted equal at load time so the two can
#: never drift apart silently.
PRESENTED_FIELDS: tuple[str, ...] = (
    "record_id",
    "question",
    "registered_answer",
    "output_text",
)

LABELS: tuple[str, ...] = (
    "correct",
    "incorrect",
    "no_answer",
    "invalid",
    "unresolved",
)

ROLES: tuple[str, ...] = ("primary", "secondary", "third")


class AddendumError(RuntimeError):
    """The addendum contract cannot be met."""


class TransportError(RuntimeError):
    """A transport/service failure survived every identical retry.

    Terminal state: ``BLOCKED_ON_SEMANTIC_REVIEW_TRANSPORT``.
    """


class MalformedResponseError(RuntimeError):
    """A successful response was not exactly the required one-key JSON object.

    Terminal state: ``BLOCKED_ON_MALFORMED_SEMANTIC_REVIEW_RESPONSE``.  It is
    deliberately *not* retried semantically and never converted to a label.
    """


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    """Hash a committed text file with line endings normalised to LF."""

    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def request_bytes(body: Mapping[str, Any]) -> bytes:
    """The exact bytes put on the wire.  Hashed into every receipt."""

    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class RoleProfile:
    """One immutable reviewer identity plus the exact request it may send."""

    role: str
    provider: str
    api_kind: str
    endpoint: str
    path_candidates: tuple[str, ...]
    api_version_candidates: tuple[str, ...]
    deployment: str
    model: str
    model_version: str
    sku: str
    region: str
    token_scope: str
    request: Mapping[str, Any]
    max_visible_output_tokens: int
    reasoning_content_fields: tuple[str, ...]

    @property
    def reviewer_id(self) -> str:
        """Stable identity binding role, deployment, model and version."""

        return (
            f"{self.role}:{self.provider}:{self.deployment}"
            f":{self.model}:{self.model_version}"
        )

    def request_profile_sha256(self) -> str:
        return sha256_text(
            canonical_json(
                {
                    "api_kind": self.api_kind,
                    "deployment": self.deployment,
                    "endpoint": self.endpoint,
                    "max_visible_output_tokens": self.max_visible_output_tokens,
                    "model": self.model,
                    "model_version": self.model_version,
                    "path_candidates": list(self.path_candidates),
                    "provider": self.provider,
                    "region": self.region,
                    "request": dict(self.request),
                    "sku": self.sku,
                }
            )
        )


@dataclass(frozen=True)
class Addendum:
    document: Mapping[str, Any]
    sha256: str
    rubric: str
    rubric_sha256: str
    roles: Mapping[str, RoleProfile]

    @property
    def retry(self) -> Mapping[str, Any]:
        return self.document["retry"]  # type: ignore[index]

    @property
    def max_in_flight(self) -> int:
        return int(self.document["concurrency"]["max_in_flight_per_deployment"])

    @property
    def coverage(self) -> Mapping[str, Any]:
        return self.document["coverage"]  # type: ignore[index]

    @property
    def smoke_fixtures(self) -> Sequence[Mapping[str, Any]]:
        return self.document["smoke_fixtures"]  # type: ignore[index]


def _role_profile(role: str, raw: Mapping[str, Any]) -> RoleProfile:
    return RoleProfile(
        role=role,
        provider=str(raw["provider"]),
        api_kind=str(raw["api_kind"]),
        endpoint=str(raw["endpoint"]).rstrip("/"),
        path_candidates=tuple(str(p) for p in raw["path_candidates"]),
        api_version_candidates=tuple(str(v) for v in raw["api_version_candidates"]),
        deployment=str(raw["deployment"]),
        model=str(raw["model"]),
        model_version=str(raw["model_version"]),
        sku=str(raw["sku"]),
        region=str(raw["region"]),
        token_scope=str(raw["token_scope"]),
        request=dict(raw["request"]),
        max_visible_output_tokens=int(raw["max_visible_output_tokens"]),
        reasoning_content_fields=tuple(
            str(name) for name in raw.get("reasoning_content_fields", ())
        ),
    )


def load_addendum(project_root: Path) -> Addendum:
    """Load, hash and validate the frozen addendum and its rubric."""

    path = project_root / ADDENDUM_PATH
    rubric_path = project_root / RUBRIC_PATH
    document = json.loads(path.read_text(encoding="utf-8"))

    if document.get("schema_version") != SCHEMA_VERSION:
        raise AddendumError(
            f"addendum schema is {document.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION!r}"
        )
    if tuple(document["presented_fields"]) != PRESENTED_FIELDS:
        raise AddendumError("the addendum presents fields the frozen form does not")
    if tuple(document["labels"]) != LABELS:
        raise AddendumError("the addendum label set is not the frozen label set")
    if tuple(document["roles"]) != ROLES:
        raise AddendumError("the addendum must declare exactly primary/secondary/third")

    rubric = rubric_path.read_text(encoding="utf-8").replace("\r\n", "\n")
    rubric_sha256 = sha256_file(rubric_path)
    if document["rubric_sha256"] != rubric_sha256:
        raise AddendumError(
            f"rubric hashes to {rubric_sha256}, addendum records "
            f"{document['rubric_sha256']}"
        )

    roles = {role: _role_profile(role, document["roles"][role]) for role in ROLES}

    seen: dict[str, str] = {}
    for role, profile in roles.items():
        key = f"{profile.provider}/{profile.deployment}"
        if key in seen:
            raise AddendumError(
                f"roles {seen[key]} and {role} share deployment {key}; "
                "one reviewer identity may not hold two roles"
            )
        seen[key] = role

    return Addendum(
        document=document,
        sha256=sha256_file(path),
        rubric=rubric,
        rubric_sha256=rubric_sha256,
        roles=roles,
    )


def assert_matches_frozen_form(presented_fields: Sequence[str]) -> None:
    """Guard against the addendum and the protected module drifting apart."""

    if tuple(presented_fields) != PRESENTED_FIELDS:
        raise AddendumError(
            "the frozen review form no longer presents the fields the addendum "
            "was written against"
        )


def user_message(row: Mapping[str, Any]) -> str:
    """The row payload, carrying exactly the four presented fields.

    Serialised as sorted-key JSON so the bytes are a function of the row alone:
    two runs of the same row produce byte-identical requests, which is what the
    retry rule ("byte-identical semantic request content") depends on.
    """

    extra = set(row) - set(PRESENTED_FIELDS)
    if extra:
        raise AddendumError(f"a reviewer row carries prohibited fields: {sorted(extra)}")
    missing = set(PRESENTED_FIELDS) - set(row)
    if missing:
        raise AddendumError(f"a reviewer row is missing fields: {sorted(missing)}")
    return json.dumps(
        {field: row[field] for field in PRESENTED_FIELDS},
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )


def build_request(
    profile: RoleProfile, addendum: Addendum, row: Mapping[str, Any]
) -> dict[str, Any]:
    """Return the exact JSON body for one row against one pinned deployment."""

    body = dict(profile.request)
    body["messages"] = [
        {"role": "system", "content": addendum.rubric},
        {"role": "user", "content": user_message(row)},
    ]
    return body


def request_url(profile: RoleProfile, path: str, api_version: str | None) -> str:
    if path not in profile.path_candidates:
        raise AddendumError(f"{path!r} is not a registered route for {profile.role}")
    if api_version and api_version not in profile.api_version_candidates:
        raise AddendumError(
            f"{api_version!r} is not a registered api-version for {profile.role}"
        )
    url = f"{profile.endpoint}{path}"
    if api_version:
        url = f"{url}?api-version={api_version}"
    return url


def _visible_content(payload: Mapping[str, Any], profile: RoleProfile) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise MalformedResponseError("a reviewer response must carry exactly one choice")
    message = choices[0].get("message")
    if not isinstance(message, Mapping):
        raise MalformedResponseError("a reviewer response carried no message object")

    finish = choices[0].get("finish_reason")
    if finish not in (None, "stop"):
        raise MalformedResponseError(
            f"a reviewer response finished as {finish!r}, not a completed answer"
        )

    content = message.get("content")
    if content is None:
        raise MalformedResponseError("a reviewer response carried no visible content")
    if isinstance(content, list):  # some providers return content parts
        parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, Mapping) and part.get("type") in (None, "text")
        ]
        content = "".join(parts)
    if not isinstance(content, str):
        raise MalformedResponseError("a reviewer response content was not text")
    # Provider-separated reasoning (DeepSeek's reasoning_content) is deliberately
    # never read: only the final one-key JSON object becomes a judgment.
    return content


def parse_label(payload: Mapping[str, Any], profile: RoleProfile) -> str:
    """Extract the one registered label, or refuse.

    Refusal is total.  Prose, a code fence, a second key, a missing key, an
    unknown label value and an empty body are all malformed, and malformed is
    never silently downgraded to ``unresolved`` or ``no_answer``.
    """

    content = _visible_content(payload, profile).strip()
    if not content:
        raise MalformedResponseError("a reviewer returned an empty body")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as error:
        raise MalformedResponseError(f"a reviewer returned non-JSON: {error}") from error
    if not isinstance(parsed, dict):
        raise MalformedResponseError("a reviewer returned JSON that is not an object")
    if set(parsed) != {"label"}:
        raise MalformedResponseError(
            f"a reviewer returned keys {sorted(parsed)}, expected exactly ['label']"
        )
    label = parsed["label"]
    if label not in LABELS:
        raise MalformedResponseError(f"a reviewer returned an unregistered label: {label!r}")
    return str(label)


def visible_token_count(payload: Mapping[str, Any]) -> int | None:
    """Visible (non-reasoning) completion tokens, when the provider reports them."""

    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return None
    completion = usage.get("completion_tokens")
    if not isinstance(completion, int):
        return None
    details = usage.get("completion_tokens_details")
    if isinstance(details, Mapping) and isinstance(details.get("reasoning_tokens"), int):
        return completion - int(details["reasoning_tokens"])
    return completion


def judgment(record_id: str, role: str, label: str, reviewer_id: str) -> dict[str, str]:
    """Form the registered four-field judgment.

    The adapter contributes only ``label``.  ``record_id``, ``role`` and
    ``reviewer_id`` come from the orchestrator, so a provider cannot relabel a
    row it was not given or claim an identity it does not have.
    """

    if role not in ROLES:
        raise AddendumError(f"unregistered review role: {role!r}")
    if label not in LABELS:
        raise AddendumError(f"unregistered label: {label!r}")
    return {
        "record_id": record_id,
        "role": role,
        "label": label,
        "reviewer_id": reviewer_id,
    }
