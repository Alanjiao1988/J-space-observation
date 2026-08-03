"""Focused tests for the Phase 1.0D semantic-review execution addendum.

Section 5 of the authority names what must be covered before any target
inference. Each test below is one of those obligations, plus the mutation
controls that show the assertions are load-bearing rather than decorative.

No test here talks to a provider. Everything that would cross the network is
injected, so the whole module runs on a CPU host in Azure and can be re-run by
anyone holding the repository.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from jspace_observation.phase1_0d_confirmation import (  # noqa: E402
    REVIEW_FORM_PRESENTED_FIELDS,
    SEMANTIC_LABELS,
)
from jspace_observation.phase1_0d_generation import (  # noqa: E402
    RunConfig,
    run_phase1_0d,
)
from jspace_observation.semantic_review import addendum as contract  # noqa: E402
from jspace_observation.semantic_review import stages  # noqa: E402
from jspace_observation.semantic_review import transport  # noqa: E402


@pytest.fixture(scope="module")
def book() -> contract.Addendum:
    return contract.load_addendum(REPO_ROOT)


# ---------------------------------------------------------------------------
# Addendum, rubric and request-profile snapshot equality
# ---------------------------------------------------------------------------


def test_the_addendum_binds_the_frozen_protocol_and_authority(book):
    assert book.document["base_protocol_sha256"] == stages.FROZEN_PROTOCOL_SHA256
    assert book.document["task_ids_sha256"] == stages.FROZEN_TASK_IDS_SHA256
    assert book.document["generation_image_digest"] == stages.GENERATION_IMAGE_DIGEST
    prompt = REPO_ROOT / book.document["authority_prompt"]
    assert contract.sha256_file(prompt) == book.document["authority_prompt_sha256"]


def test_the_rubric_hash_in_the_addendum_is_the_rubric_on_disk(book):
    rubric = REPO_ROOT / contract.RUBRIC_PATH
    assert contract.sha256_file(rubric) == book.rubric_sha256
    assert book.rubric.startswith("You are an isolated semantic correctness adjudicator.")
    for label in SEMANTIC_LABELS:
        assert f'"{label}"' in book.rubric


def test_the_addendum_presents_exactly_the_frozen_form_fields(book):
    assert tuple(book.document["presented_fields"]) == tuple(REVIEW_FORM_PRESENTED_FIELDS)
    assert tuple(book.document["labels"]) == tuple(SEMANTIC_LABELS)


def test_the_request_profile_hashes_are_stable_and_distinct(book):
    hashes = {role: book.roles[role].request_profile_sha256() for role in contract.ROLES}
    assert len(set(hashes.values())) == 3
    assert hashes == {role: book.roles[role].request_profile_sha256() for role in contract.ROLES}


def test_every_role_pins_an_exact_model_version(book):
    assert book.roles["primary"].model == "gpt-5.6-sol"
    assert book.roles["primary"].model_version == "2026-07-09"
    assert book.roles["secondary"].model == "Mistral-Large-3"
    assert book.roles["secondary"].model_version == "1"
    assert book.roles["third"].model == "DeepSeek-V4-Pro"
    assert book.roles["third"].model_version == "2026-04-23"
    for role in contract.ROLES:
        profile = book.roles[role]
        assert profile.sku == "GlobalStandard"
        assert profile.region == "eastus2"
        assert "latest" not in json.dumps(dict(profile.request)).lower()


def test_the_addendum_carries_no_credential(book):
    """Words like "secret" appear in prose; credential *material* must not."""

    text = json.dumps(book.document)
    for marker in (
        "AccountKey=",
        "SharedAccessSignature",
        "?sig=",
        "&sig=",
        "eyJ0eXAi",
        "BEGIN PRIVATE KEY",
    ):
        assert marker not in text
    for role in contract.ROLES:
        raw = book.document["roles"][role]
        assert set(raw) & {"api_key", "key", "secret", "client_secret", "sas"} == set()
        assert raw["token_scope"].endswith("/.default")
    assert book.document["authentication"]["keys_forbidden"] is True


def test_one_reviewer_identity_cannot_hold_two_roles(book, tmp_path):
    document = json.loads(json.dumps(book.document))
    document["roles"]["third"]["deployment"] = document["roles"]["secondary"]["deployment"]
    root = tmp_path / "repo"
    (root / "docs").mkdir(parents=True)
    (root / contract.ADDENDUM_PATH).write_text(json.dumps(document), encoding="utf-8")
    (root / contract.RUBRIC_PATH).write_text(book.rubric, encoding="utf-8")
    with pytest.raises(contract.AddendumError, match="may not hold two roles"):
        contract.load_addendum(root)


# ---------------------------------------------------------------------------
# Prohibited fields and one-row-per-request
# ---------------------------------------------------------------------------


def _row(**overrides: Any) -> dict[str, Any]:
    row = {
        "record_id": "task-0001|strict_no_cot|0",
        "question": "What is 2 + 2?",
        "registered_answer": "4",
        "output_text": "Final answer: 4",
    }
    row.update(overrides)
    return row


def test_a_request_carries_exactly_one_row_and_the_rubric(book):
    body = contract.build_request(book.roles["primary"], book, _row())
    assert [message["role"] for message in body["messages"]] == ["system", "user"]
    assert body["messages"][0]["content"] == book.rubric
    payload = json.loads(body["messages"][1]["content"])
    assert set(payload) == set(REVIEW_FORM_PRESENTED_FIELDS)


def test_a_prohibited_field_is_refused_before_it_reaches_a_provider(book):
    for prohibited in ("arm_id", "task_family", "primary_label", "triage", "parser_route"):
        with pytest.raises(contract.AddendumError, match="prohibited fields"):
            contract.build_request(book.roles["secondary"], book, _row(**{prohibited: "x"}))


def test_a_missing_presented_field_is_refused(book):
    row = _row()
    del row["registered_answer"]
    with pytest.raises(contract.AddendumError, match="missing fields"):
        contract.build_request(book.roles["primary"], book, row)


def test_no_request_body_carries_conversation_state(book):
    for role in contract.ROLES:
        body = contract.build_request(book.roles[role], book, _row())
        assert "tools" not in body
        assert "tool_choice" not in body
        assert "previous_response_id" not in body
        assert "conversation" not in body
        assert len(body["messages"]) == 2
    assert book.roles["primary"].request["store"] is False


def test_two_rows_produce_two_different_request_bodies(book):
    first = contract.request_bytes(
        contract.build_request(book.roles["primary"], book, _row())
    )
    second = contract.request_bytes(
        contract.build_request(
            book.roles["primary"], book, _row(record_id="task-0002|strict_no_cot|0")
        )
    )
    assert first != second


def test_the_same_row_produces_byte_identical_requests(book):
    """The retry rule depends on this: an identical retry must be identical."""

    profile = book.roles["primary"]
    first = contract.request_bytes(contract.build_request(profile, book, _row()))
    second = contract.request_bytes(contract.build_request(profile, book, _row()))
    assert first == second


# ---------------------------------------------------------------------------
# Response parsing: every label boundary, and refusal of everything else
# ---------------------------------------------------------------------------


def _response(content: str, **extra: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "choices": [{"finish_reason": "stop", "message": {"content": content}}],
    }
    payload.update(extra)
    return payload


@pytest.mark.parametrize("label", SEMANTIC_LABELS)
def test_every_registered_label_parses(book, label):
    payload = _response(json.dumps({"label": label}))
    assert contract.parse_label(payload, book.roles["primary"]) == label


@pytest.mark.parametrize(
    "content",
    [
        "correct",
        "```json\n{\"label\": \"correct\"}\n```",
        "The label is: {\"label\": \"correct\"}",
        "{\"label\": \"correct\", \"confidence\": 0.9}",
        "{\"verdict\": \"correct\"}",
        "{\"label\": \"CORRECT\"}",
        "{\"label\": \"partially_correct\"}",
        "{\"label\": [\"correct\"]}",
        "[{\"label\": \"correct\"}]",
        "",
        "   ",
    ],
)
def test_prose_fences_extra_keys_and_unknown_labels_are_all_malformed(book, content):
    with pytest.raises(contract.MalformedResponseError):
        contract.parse_label(_response(content), book.roles["primary"])


def test_a_truncated_response_is_malformed_not_a_label(book):
    payload = {
        "choices": [{"finish_reason": "length", "message": {"content": "{\"label\": \"cor"}}]
    }
    with pytest.raises(contract.MalformedResponseError, match="not a completed answer"):
        contract.parse_label(payload, book.roles["primary"])


def test_more_than_one_choice_is_malformed(book):
    payload = {
        "choices": [
            {"finish_reason": "stop", "message": {"content": "{\"label\": \"correct\"}"}},
            {"finish_reason": "stop", "message": {"content": "{\"label\": \"incorrect\"}"}},
        ]
    }
    with pytest.raises(contract.MalformedResponseError, match="exactly one choice"):
        contract.parse_label(payload, book.roles["primary"])


def test_provider_separated_reasoning_never_becomes_a_label(book):
    """DeepSeek may return reasoning_content; only the final object counts."""

    payload = _response(
        json.dumps({"label": "incorrect"}),
    )
    payload["choices"][0]["message"]["reasoning_content"] = (
        'I think the answer is right, so {"label": "correct"}'
    )
    assert contract.parse_label(payload, book.roles["third"]) == "incorrect"


def test_a_malformed_response_is_never_downgraded_to_a_semantic_label(book):
    with pytest.raises(contract.MalformedResponseError) as error:
        contract.parse_label(_response("I cannot answer that."), book.roles["primary"])
    assert "unresolved" not in str(error.value)
    assert "no_answer" not in str(error.value)


def test_the_adapter_contributes_only_the_label(book):
    judgment = contract.judgment(
        "task-0001|strict_no_cot|0", "primary", "correct", book.roles["primary"].reviewer_id
    )
    assert set(judgment) == {"record_id", "role", "label", "reviewer_id"}
    assert judgment["reviewer_id"] == book.roles["primary"].reviewer_id
    with pytest.raises(contract.AddendumError):
        contract.judgment("r", "adjudicator", "correct", "x")
    with pytest.raises(contract.AddendumError):
        contract.judgment("r", "primary", "mostly_correct", "x")


def test_a_visible_output_over_the_cap_is_malformed(book):
    payload = _response(
        json.dumps({"label": "correct"}),
        usage={"completion_tokens": 900, "completion_tokens_details": {"reasoning_tokens": 800}},
    )
    assert contract.visible_token_count(payload) == 100
    with pytest.raises(contract.MalformedResponseError) as error:
        stages.review_rows(
            rows=[_row()],
            profile=book.roles["primary"],
            addendum=book,
            caller=lambda profile, body: _FakeResponse(payload),
        )
    assert "visible tokens" in str(error.value)


class _FakeResponse:
    def __init__(self, payload: Mapping[str, Any], retries: int = 0) -> None:
        self.payload = payload
        self.raw_body = json.dumps(payload)
        self.request_sha256 = "0" * 64
        self.response_sha256 = "1" * 64
        self.latency_seconds = 0.01
        self.retries = retries
        self.status = 200
        self.url = "https://example.invalid"
        self.api_version = "2024-05-01-preview"
        self.path = "/models/chat/completions"


# ---------------------------------------------------------------------------
# Transport: failures never become labels
# ---------------------------------------------------------------------------


def _http(status: int, body: str = "{}") -> transport.HttpResult:
    return transport.HttpResult(status=status, body=body)


class _FakeTokens:
    def token(self, resource: str) -> str:  # noqa: D401 - test double
        return "not-a-real-token"


def test_a_retryable_status_is_retried_with_identical_bytes(book):
    seen: list[bytes] = []

    def poster(url, token, payload, timeout):
        seen.append(payload)
        if len(seen) < 3:
            return _http(429)
        return _http(200, json.dumps(_response(json.dumps({"label": "correct"}))))

    response = transport.call_row(
        profile=book.roles["primary"],
        addendum=book,
        body=contract.build_request(book.roles["primary"], book, _row()),
        path="/openai/v1/chat/completions",
        api_version="",
        tokens=_FakeTokens(),
        poster=poster,
        sleeper=lambda _seconds: None,
    )
    assert response.retries == 2
    assert len(set(seen)) == 1, "every retry must send byte-identical content"
    assert contract.parse_label(response.payload, book.roles["primary"]) == "correct"


def test_an_exhausted_retry_budget_stops_rather_than_labelling(book):
    calls = {"n": 0}

    def poster(url, token, payload, timeout):
        calls["n"] += 1
        return _http(503)

    with pytest.raises(contract.TransportError, match="exhausted"):
        transport.call_row(
            profile=book.roles["primary"],
            addendum=book,
            body=contract.build_request(book.roles["primary"], book, _row()),
            path="/openai/v1/chat/completions",
            api_version="",
            tokens=_FakeTokens(),
            poster=poster,
            sleeper=lambda _seconds: None,
        )
    assert calls["n"] == int(book.retry["max_attempts"])


def test_a_non_retryable_status_is_not_retried(book):
    calls = {"n": 0}

    def poster(url, token, payload, timeout):
        calls["n"] += 1
        return _http(403, "forbidden")

    with pytest.raises(contract.TransportError, match="HTTP 403"):
        transport.call_row(
            profile=book.roles["primary"],
            addendum=book,
            body=contract.build_request(book.roles["primary"], book, _row()),
            path="/openai/v1/chat/completions",
            api_version="",
            tokens=_FakeTokens(),
            poster=poster,
            sleeper=lambda _seconds: None,
        )
    assert calls["n"] == 1


def test_a_successful_but_malformed_response_is_not_retried_semantically(book):
    calls = {"n": 0}

    def poster(url, token, payload, timeout):
        calls["n"] += 1
        return _http(200, json.dumps(_response("no idea")))

    response = transport.call_row(
        profile=book.roles["primary"],
        addendum=book,
        body=contract.build_request(book.roles["primary"], book, _row()),
        path="/openai/v1/chat/completions",
        api_version="",
        tokens=_FakeTokens(),
        poster=poster,
        sleeper=lambda _seconds: None,
    )
    assert calls["n"] == 1
    with pytest.raises(contract.MalformedResponseError):
        contract.parse_label(response.payload, book.roles["primary"])


def test_an_unregistered_route_or_api_version_is_refused(book):
    with pytest.raises(contract.AddendumError, match="not a registered route"):
        contract.request_url(book.roles["primary"], "/v1/anything", None)
    with pytest.raises(contract.AddendumError, match="not a registered api-version"):
        contract.request_url(
            book.roles["secondary"], "/models/chat/completions", "1999-01-01"
        )


def test_blob_upload_refuses_to_overwrite(book):
    calls: list[Mapping[str, str]] = []

    def fake_request(method, url, token, *, body=None, extra_headers=None, timeout=120.0):
        calls.append(dict(extra_headers or {}))
        return transport.HttpResult(status=409, body="BlobAlreadyExists")

    original = transport.blob_request
    transport.blob_request = fake_request  # type: ignore[assignment]
    try:
        client = transport.BlobClient("account", "container", _FakeTokens())
        with pytest.raises(contract.TransportError, match="refuses to overwrite"):
            client.put_create_only("prefix/x.json", b"{}")
    finally:
        transport.blob_request = original  # type: ignore[assignment]
    assert calls[0]["If-None-Match"] == "*"


# ---------------------------------------------------------------------------
# Coverage arithmetic over a real 900-row pack
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def pack(tmp_path_factory) -> Path:
    """A real self-test pack: 300 items, 900 rows, no labels."""

    root = tmp_path_factory.mktemp("packs")
    summary = run_phase1_0d(
        RunConfig(
            mode="self-test",
            output_root=root,
            repo_root=REPO_ROOT,
            run_id="20260101T000000Z",
            code_commit="9cde1d95ffda36698a0ddf558a9358f3337dd711",
            image_digest=stages.GENERATION_IMAGE_DIGEST,
            hardware="cpu-test",
        )
    )
    assert summary["records"] == 900
    return Path(summary["output_dir"])


def test_a_clean_pack_verifies_and_reports_the_frozen_binding(pack):
    result = stages.verify_generation_pack(pack)
    assert result["records"] == 900
    assert result["items"] == 300
    assert result["status"] == "AWAITING_SEMANTIC_REVIEW"
    assert result["protocol_sha256"] == stages.FROZEN_PROTOCOL_SHA256
    assert result["task_ids_sha256"] == stages.FROZEN_TASK_IDS_SHA256
    assert len(result["records_sha256"]) == 64
    assert len(result["manifest_sha256"]) == 64


def test_an_edited_record_breaks_the_manifest_binding(pack, tmp_path):
    import shutil

    copy = tmp_path / "tampered"
    shutil.copytree(pack, copy)
    records = (copy / "02_records.jsonl").read_bytes()
    (copy / "02_records.jsonl").write_bytes(records.replace(b"Final answer", b"FINAL"))
    with pytest.raises(stages.StageError, match="hashes to"):
        stages.verify_generation_pack(copy)


def test_a_prelabelled_pack_is_refused(pack, tmp_path):
    import hashlib
    import shutil

    copy = tmp_path / "prelabelled"
    shutil.copytree(pack, copy)
    rows = stages._load_jsonl(copy / "02_records.jsonl")
    rows[0]["evaluation"]["primary_label"] = "correct"
    payload = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode("utf-8")
    (copy / "02_records.jsonl").write_bytes(payload)
    manifest = json.loads((copy / "artifact_manifest.json").read_text("utf-8"))
    for entry in manifest["files"]:
        if entry["name"] == "02_records.jsonl":
            entry["sha256"] = hashlib.sha256(payload).hexdigest()
    (copy / "artifact_manifest.json").write_bytes(
        json.dumps(manifest, indent=2).encode("utf-8")
    )
    with pytest.raises(stages.StageError, match="already carry a label"):
        stages.verify_generation_pack(copy)


def _records(pack: Path) -> list[dict[str, Any]]:
    return stages._load_jsonl(pack / "02_records.jsonl")


def _form(pack: Path) -> list[dict[str, Any]]:
    return stages._load_jsonl(pack / "03_review_form.jsonl")


def _all_primary(pack: Path, book: contract.Addendum) -> list[dict[str, str]]:
    """Primary labels that agree with the frozen parser route on every row.

    The forced component of the secondary set is "parser and reviewer differ",
    so labelling in agreement isolates the *sampled* component and lets the
    fixed 180 be asserted exactly. Nothing here is a claim about correctness:
    it is a fixture that makes the selection arithmetic observable.
    """

    labels = []
    for row in _records(pack):
        triage = row["triage"]
        if triage["surface_matches_registered_answer"]:
            label = "correct"
        elif triage["final_answer_surface_present"]:
            label = "incorrect"
        else:
            label = "no_answer"
        labels.append(
            contract.judgment(
                str(row["record_id"]), "primary", label, book.roles["primary"].reviewer_id
            )
        )
    return labels


def test_primary_coverage_is_exactly_nine_hundred(pack, book):
    judgments = _all_primary(pack, book)
    assert len(judgments) == 900
    assert len({item["record_id"] for item in judgments}) == 900


def test_the_sampled_secondary_component_is_exactly_one_hundred_and_eighty(pack, book):
    selection = stages.select_secondary(_records(pack), _all_primary(pack, book), book)
    assert selection["sampled_count"] == 180
    assert selection["sampled_count"] == int(45 * 20 * 0.2)
    assert selection["required_count"] >= 180


def test_a_parser_agreeing_pass_requires_exactly_the_fixed_sample(pack, book):
    selection = stages.select_secondary(_records(pack), _all_primary(pack, book), book)
    assert selection["forced_count"] == 0
    assert selection["required_ids"] == selection["sampled_ids"]
    assert selection["required_count"] == 180


def test_forced_rows_union_with_the_sample_and_never_shrink_it(pack, book):
    judgments = _all_primary(pack, book)
    forced_ids = {item["record_id"] for item in judgments[:3]}
    judgments = [
        contract.judgment(
            item["record_id"],
            "primary",
            "invalid" if item["record_id"] in forced_ids else item["label"],
            item["reviewer_id"],
        )
        for item in judgments
    ]
    selection = stages.select_secondary(_records(pack), judgments, book)
    required = set(selection["required_ids"])
    assert set(selection["sampled_ids"]) <= required
    assert set(selection["forced_ids"]) == forced_ids
    assert required == set(selection["sampled_ids"]) | forced_ids
    assert selection["sampled_count"] == 180
    assert selection["required_count"] >= 180


def _agreeing_secondary(
    primary: Sequence[Mapping[str, str]],
    required: Sequence[str],
    book: contract.Addendum,
    disagree_on: int = 0,
) -> list[dict[str, str]]:
    """Secondary labels over exactly the required set, disagreeing on N rows."""

    by_id = {item["record_id"]: item["label"] for item in primary}
    judgments: list[dict[str, str]] = []
    for index, record_id in enumerate(required):
        label = by_id[record_id]
        if index < disagree_on:
            label = "invalid" if label != "invalid" else "correct"
        judgments.append(
            contract.judgment(
                record_id, "secondary", label, book.roles["secondary"].reviewer_id
            )
        )
    return judgments


def test_an_unresolved_primary_forces_a_secondary_review(pack, book):
    records = _records(pack)
    judgments = _all_primary(pack, book)
    target = judgments[0]["record_id"]
    judgments[0] = contract.judgment(
        target, "primary", "unresolved", book.roles["primary"].reviewer_id
    )
    selection = stages.select_secondary(records, judgments, book)
    assert target in selection["forced_ids"]
    assert target in selection["required_ids"]


def test_a_missing_primary_judgment_stops_secondary_selection(pack, book):
    with pytest.raises(stages.StageError, match="exactly one primary judgment"):
        stages.select_secondary(_records(pack), _all_primary(pack, book)[:-1], book)


def test_third_review_is_selected_only_on_disagreement(pack, book):
    primary = _all_primary(pack, book)
    selection = stages.select_secondary(_records(pack), primary, book)
    required = selection["required_ids"]
    secondary = _agreeing_secondary(primary, required, book, disagree_on=5)
    third = stages.select_third(primary, secondary)
    assert third["required_count"] == 5
    assert third["required_ids"] == sorted(required[:5])
    assert third["agreement_count"] == len(required) - 5


def test_no_third_review_where_the_first_two_agreed(pack, book):
    primary = _all_primary(pack, book)
    selection = stages.select_secondary(_records(pack), primary, book)
    secondary = _agreeing_secondary(primary, selection["required_ids"], book)
    assert stages.select_third(primary, secondary)["required_ids"] == []


def test_a_secondary_judgment_for_a_row_with_no_primary_is_refused(book):
    primary = [contract.judgment("a", "primary", "correct", "p")]
    secondary = [contract.judgment("b", "secondary", "correct", "s")]
    with pytest.raises(stages.StageError, match="no primary"):
        stages.select_third(primary, secondary)


def test_rows_for_selects_original_four_field_rows_only(pack, book):
    form = _form(pack)
    ids = [str(row["record_id"]) for row in form[:7]]
    rows = stages.rows_for(form, ids)
    assert len(rows) == 7
    for row in rows:
        assert set(row) == set(REVIEW_FORM_PRESENTED_FIELDS)
    with pytest.raises(stages.StageError, match="no row for"):
        stages.rows_for(form, ["not-a-record"])


# ---------------------------------------------------------------------------
# Judgment-set verification
# ---------------------------------------------------------------------------


def _coverage_args(pack: Path, book: contract.Addendum) -> dict[str, Any]:
    primary = _all_primary(pack, book)
    selection = stages.select_secondary(_records(pack), primary, book)
    secondary = _agreeing_secondary(primary, selection["required_ids"], book)
    third_selection = stages.select_third(primary, secondary)
    third: list[dict[str, str]] = []
    receipts = {
        role: [
            {
                "record_id": item["record_id"],
                "deployment": book.roles[role].deployment,
                "model_version": book.roles[role].model_version,
            }
            for item in judgments
        ]
        for role, judgments in (("primary", primary), ("secondary", secondary), ("third", third))
    }
    return {
        "record_ids": [str(row["record_id"]) for row in _records(pack)],
        "primary": primary,
        "secondary": secondary,
        "third": third,
        "required_secondary": selection["required_ids"],
        "required_third": third_selection["required_ids"],
        "addendum": book,
        "receipts_by_role": receipts,
    }


def test_an_exact_judgment_set_verifies(pack, book):
    result = stages.verify_judgments(**_coverage_args(pack, book))
    assert result["primary_count"] == 900
    assert result["third_count"] == 0
    assert set(result["request_profile_sha256"]) == set(contract.ROLES)


def test_a_secondary_judgment_for_an_unrequired_row_is_a_hard_failure(pack, book):
    args = _coverage_args(pack, book)
    intruder = sorted(set(args["record_ids"]) - set(args["required_secondary"]))[0]
    args["secondary"] = [
        *args["secondary"],
        contract.judgment(intruder, "secondary", "correct", book.roles["secondary"].reviewer_id),
    ]
    args["receipts_by_role"]["secondary"] = [
        *args["receipts_by_role"]["secondary"],
        {
            "record_id": intruder,
            "deployment": book.roles["secondary"].deployment,
            "model_version": book.roles["secondary"].model_version,
        },
    ]
    with pytest.raises(stages.StageError, match="secondary coverage is wrong"):
        stages.verify_judgments(**args)


def test_a_missing_required_secondary_judgment_is_a_hard_failure(pack, book):
    args = _coverage_args(pack, book)
    args["secondary"] = args["secondary"][:-1]
    args["receipts_by_role"]["secondary"] = args["receipts_by_role"]["secondary"][:-1]
    with pytest.raises(stages.StageError, match="secondary coverage is wrong"):
        stages.verify_judgments(**args)


def test_an_incomplete_primary_set_is_refused_before_finalization(pack, book):
    args = _coverage_args(pack, book)
    args["primary"] = args["primary"][:-1]
    args["receipts_by_role"]["primary"] = args["receipts_by_role"]["primary"][:-1]
    with pytest.raises(stages.StageError, match="primary coverage is wrong"):
        stages.verify_judgments(**args)


def test_a_substituted_deployment_is_caught(pack, book):
    args = _coverage_args(pack, book)
    args["receipts_by_role"]["primary"][0]["deployment"] = "some-other-deployment"
    with pytest.raises(stages.StageError, match="response came from"):
        stages.verify_judgments(**args)


def test_a_reviewer_holding_two_roles_is_caught(pack, book):
    args = _coverage_args(pack, book)
    shared = book.roles["primary"].reviewer_id
    args["secondary"] = [
        {**item, "reviewer_id": shared} for item in args["secondary"]
    ]
    with pytest.raises(stages.StageError, match="reviewer id is"):
        stages.verify_judgments(**args)


def test_a_judgment_without_a_raw_response_is_caught(pack, book):
    args = _coverage_args(pack, book)
    args["receipts_by_role"]["primary"] = args["receipts_by_role"]["primary"][:-1]
    with pytest.raises(stages.StageError, match="raw responses"):
        stages.verify_judgments(**args)


def test_the_combined_set_is_sorted_and_closed(pack, book):
    args = _coverage_args(pack, book)
    combined = stages.combine_judgments(args["primary"], args["secondary"], args["third"])
    assert combined == sorted(combined, key=lambda item: (item["record_id"], item["role"]))
    for item in combined:
        assert set(item) == {"record_id", "role", "label", "reviewer_id"}


# ---------------------------------------------------------------------------
# Review pass mechanics
# ---------------------------------------------------------------------------


def test_review_rows_sends_one_request_per_row_and_records_a_receipt(book):
    rows = [_row(record_id=f"task-{index:04d}|strict_no_cot|0") for index in range(6)]
    seen: list[str] = []

    def caller(profile, body):
        payload = json.loads(body["messages"][1]["content"])
        seen.append(payload["record_id"])
        return _FakeResponse(_response(json.dumps({"label": "correct"})), retries=1)

    outcome = stages.review_rows(
        rows=rows, profile=book.roles["primary"], addendum=book, caller=caller
    )
    assert sorted(seen) == sorted(row["record_id"] for row in rows)
    assert len(outcome.judgments) == 6
    assert len(outcome.receipts) == 6
    assert outcome.label_counts == {"correct": 6}
    assert outcome.retries == 6
    assert outcome.requests == 12
    assert all(receipt["role"] == "primary" for receipt in outcome.receipts)


def test_review_rows_refuses_to_label_a_malformed_response(book):
    with pytest.raises(contract.MalformedResponseError):
        stages.review_rows(
            rows=[_row()],
            profile=book.roles["primary"],
            addendum=book,
            caller=lambda profile, body: _FakeResponse(_response("sure, correct")),
        )


# ---------------------------------------------------------------------------
# Outer bundle: manifest last, create-only
# ---------------------------------------------------------------------------


def test_the_outer_manifest_hashes_every_other_file(book):
    files = {"a.json": b"{}\n", "b/c.json": b"[]\n"}
    manifest = stages.bundle_manifest(files, "20260101T000000Z")
    assert manifest["file_count"] == 2
    assert [entry["name"] for entry in manifest["files"]] == ["a.json", "b/c.json"]
    assert manifest["manifest_written_last"] is True
    assert "create-only" in manifest["upload_semantics"]


def test_the_outer_receipt_states_what_it_does_not_establish():
    receipt = stages.outer_receipt(generation_run_id="x")
    assert "nothing about reviewer accuracy" in receipt["claim_boundary"]
    assert "J-space" in receipt["claim_boundary"]


def test_the_independent_check_refuses_an_incomplete_pack(book):
    records = [
        {"record_id": "a", "evaluation": {"final_label": "correct"}},
        {"record_id": "b", "evaluation": {"final_label": None}},
    ]
    combined = [
        contract.judgment("a", "primary", "correct", "x"),
        contract.judgment("b", "primary", "correct", "x"),
    ]
    with pytest.raises(stages.IntegrityError, match="no final label"):
        stages.independent_check(
            records=records,
            decision={"result": "HEADROOM_NOT_ESTABLISHED", "rq2_pilot_candidates": []},
            combined=combined,
            required_secondary=[],
            required_third=[],
        )


def test_the_independent_check_recomputes_without_changing_anything():
    records = [
        {"record_id": "a", "evaluation": {"final_label": "correct"}},
        {"record_id": "b", "evaluation": {"final_label": "incorrect"}},
    ]
    combined = [
        contract.judgment("a", "primary", "correct", "x"),
        contract.judgment("b", "primary", "incorrect", "x"),
    ]
    decision = {"result": "HEADROOM_NOT_ESTABLISHED", "rq2_pilot_candidates": []}
    result = stages.independent_check(
        records=records,
        decision=decision,
        combined=combined,
        required_secondary=[],
        required_third=[],
    )
    assert result["final_label_counts"] == {"correct": 1, "incorrect": 1}
    assert result["changed_nothing"] is True
    assert len(result["decision_sha256"]) == 64
    assert decision == {"result": "HEADROOM_NOT_ESTABLISHED", "rq2_pilot_candidates": []}


# ---------------------------------------------------------------------------
# The wrapper does not reimplement the frozen science
# ---------------------------------------------------------------------------


def test_the_wrapper_calls_the_frozen_selector_rather_than_its_own(monkeypatch, pack, book):
    calls = {"n": 0}
    original = stages.annotate_review_selection

    def spy(records):
        calls["n"] += 1
        return original(records)

    monkeypatch.setattr(stages, "annotate_review_selection", spy)
    stages.select_secondary(_records(pack), _all_primary(pack, book), book)
    assert calls["n"] == 1


def test_the_review_package_defines_no_arbitration_or_gate_of_its_own():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPO_ROOT / "src" / "jspace_observation" / "semantic_review").glob("*.py")
    )
    for forbidden in ("def arbitrate", "def compute_cell_outcomes", "def build_decision",
                      "def stratified_secondary_sample", "def forces_secondary_review"):
        assert forbidden not in sources


def test_the_entrypoint_imports_and_exposes_exactly_three_modes():
    import importlib.util

    path = REPO_ROOT / "scripts" / "run_phase1_0d_semantic_review.py"
    spec = importlib.util.spec_from_file_location("p10d_review_cli", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with pytest.raises(SystemExit):
        module.main(["not-a-mode"])
    assert hasattr(module, "LiveCaller")
    assert callable(module._qualify)
    assert callable(module._smoke)
    assert callable(module._review)


def test_the_entrypoint_never_reviews_before_a_route_is_qualified(book):
    import importlib.util

    path = REPO_ROOT / "scripts" / "run_phase1_0d_semantic_review.py"
    spec = importlib.util.spec_from_file_location("p10d_review_cli2", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    caller = module.LiveCaller(book, _FakeTokens())
    with pytest.raises(contract.AddendumError, match="before its route was qualified"):
        caller(book.roles["primary"], {})
