"""Study 4F-E1-Q1 quota-escalation tests.

Authority: ``studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation_and_conditional_resume_authority.md``

This authority does exactly one irreversible thing -- it opens an Azure Support
case -- and then waits. So the tests concentrate on the properties that would be
expensive or embarrassing to get wrong:

1. the Q1 authority is byte-exact and was published **alone**, first, on top of
   the published E1 head;
2. **at most one** support ticket exists under this authority, the self-service
   quota path was not retried, and the request was never enlarged;
3. the A100 fallback cannot coexist with an unresolved H100 request;
4. no full subscription, tenant or support-ticket identifier is committed;
5. resumption is gated on **visible** quota, not on an approval message;
6. every predecessor byte -- Study 4F, Study 4F-E1, Study 3R, the paper -- is
   untouched.

Nothing here contacts Azure, constructs a model or executes a cell.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess

import pytest

HERE = pathlib.Path(__file__).resolve()
Q1 = HERE.parents[1]
E1 = Q1.parent
STUDY4F = E1.parent
ROOT = STUDY4F.parents[1]

E1_HEAD_COMMIT = "1900aa374bf000353580b042b275a730bbad6b1f"
E1_HEAD_TREE = "a0b5d7304b6d08e55c45f927b048af01ad409126"
E1_AUTHORITY_COMMIT = "58cdcda0ec3848ba2bd3a6c525b3c28ac8955d69"
STUDY4F_COMMIT = "5fd9602df207e95789263d0f8d52428540f48fb8"
STUDY3R_CLOSURE_COMMIT = "ee8a852111d27cb39bf21743e18857485cff1efe"
FAILED_SELF_SERVICE_REQUEST = "a6817961-e0f7-4cbe-a1ef-7ac4104e1089"

AUTHORITY = (STUDY4F / "prompts" /
             "study4f_e1_q1_manual_quota_escalation_and_conditional_resume_"
             "authority.md")
STATUS_JSON = Q1 / "STATUS.json"
STATUS_SCHEMA = Q1 / "STATUS.schema.json"
RECEIPT_JSON = Q1 / "support_ticket_receipt.json"
RECEIPT_SCHEMA = Q1 / "support_ticket_receipt.schema.json"
OPERATOR_RECORD = Q1 / "OPERATOR_RECORD.md"

#: The three registered Q1 lifecycle states.
REGISTERED_Q1_STATES = (
    "STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION",
    "STUDY4F_E1_Q1_MANUAL_PORTAL_SUBMISSION_REQUIRED",
    "STUDY4F_E1_Q1_BLOCKED_ON_STARTING_STATE_INTEGRITY",
)

#: Quota is approved only at or above these visible family limits.
H100_APPROVAL_LIMIT = 40
A100_APPROVAL_LIMIT = 24

GUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
                  r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, check=True).stdout


def _json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def status():
    return _json(STATUS_JSON)


@pytest.fixture(scope="module")
def receipt():
    return _json(RECEIPT_JSON)


@pytest.fixture(scope="module")
def e1_status():
    return _json(E1 / "STATUS.json")


# ---------------------------------------------------------------------------
# 1. Authority identity and alone-first ordering
# ---------------------------------------------------------------------------


def test_the_q1_authority_bytes_match_the_recorded_identity(status, receipt):
    payload = AUTHORITY.read_bytes()
    for recorded in (status["authority"], receipt["authority"]):
        assert len(payload) == recorded["bytes"]
        assert hashlib.sha256(payload).hexdigest() == recorded["sha256"]
        assert _git("hash-object", str(AUTHORITY)).strip() == recorded["git_blob"]


def test_the_q1_authority_was_published_alone_on_top_of_the_e1_head(status):
    commit = status["authority"]["commit"]
    listed = [line.strip() for line
              in _git("show", "--name-only", "--format=", commit).splitlines()
              if line.strip()]
    assert listed == [
        "studies/study4f/prompts/"
        "study4f_e1_q1_manual_quota_escalation_and_conditional_resume_authority.md"]
    assert _git("show", "-s", "--format=%P", commit).split() == [E1_HEAD_COMMIT]
    assert status["authority"]["parent_commit"] == E1_HEAD_COMMIT
    assert status["authority"]["parent_tree"] == E1_HEAD_TREE
    assert status["authority"]["published_alone_as_the_first_commit_after_the_predecessor"] \
        is True


def test_no_q1_artifact_predates_the_q1_authority_commit(status):
    listed = [line.strip() for line
              in _git("ls-tree", "-r", "--name-only", status["authority"]["commit"],
                      "studies/study4f/execution-e1/quota-escalation-q1"
                      ).splitlines() if line.strip()]
    assert listed == []


def test_the_history_is_strictly_linear_and_merge_free():
    merges = [line for line
              in _git("rev-list", "--merges",
                      "%s..HEAD" % E1_HEAD_COMMIT).splitlines() if line.strip()]
    assert merges == []


def test_the_authority_file_is_the_one_this_invocation_executed():
    text = AUTHORITY.read_text(encoding="utf-8")
    assert E1_HEAD_COMMIT in text
    assert FAILED_SELF_SERVICE_REQUEST in text
    assert "QuotaNotAvailableForResource" in text
    for state in REGISTERED_Q1_STATES:
        assert state in text, state
    # It is explicitly not a new study or an amendment.
    lowered = text.lower()
    assert "this is not a new study" in lowered


def test_the_authority_is_recorded_as_published_or_reused_but_not_both(status):
    fresh = status["authority"]["newly_published_in_this_invocation"]
    reused = status["authority"]["reused_existing_published_copy"]
    assert fresh != reused


# ---------------------------------------------------------------------------
# 2. Exactly one ticket, and no retry of the exhausted self-service path
# ---------------------------------------------------------------------------


def test_at_most_one_support_ticket_exists_under_this_authority(status, receipt):
    assert status["support_ticket"]["tickets_created_in_this_invocation"] <= 1
    assert status["support_ticket"]["total_tickets_created_under_this_authority"] <= 1
    assert status["support_ticket"]["duplicate_created"] is False
    assert receipt["submitted_support_ticket"]["count"] == 1
    assert receipt["submitted_support_ticket"]["duplicate_created"] is False


def test_the_self_service_quota_path_was_not_retried(status, receipt):
    assert status["quota"]["additional_self_service_quota_put_submitted"] is False
    assert receipt["self_service_quota_path"]["exhausted"] is True
    assert receipt["self_service_quota_path"][
        "additional_microsoft_quota_put_submitted"] is False
    assert status["zero_operation_counters"][
        "additional_self_service_quota_requests"] == 0


def test_a_pre_existing_ticket_would_have_prevented_a_second_one(receipt):
    """Section 2.2 is the guard; 2.3 was only taken because none existed."""
    pre_existing = receipt["pre_existing_support_ticket"]
    assert pre_existing["searched"] is True
    if pre_existing["matching_non_closed_ticket_found"]:
        assert pre_existing["branch_taken"] == \
            "2.2_an_operator_support_ticket_already_exists"
        assert receipt["submitted_support_ticket"]["created_in_this_invocation"] \
            is False
    else:
        assert pre_existing["branch_taken"] == \
            "2.3_no_operator_support_ticket_exists"
        assert pre_existing["tickets_present_before_this_invocation"] == 0


def test_the_request_is_exactly_the_registered_minimal_one(receipt):
    requested = receipt["requested_quota"]
    assert requested["region"] == "australiaeast"
    assert requested["vm_family"] == "Standard NCadsH100v5 Family vCPUs"
    assert requested["vm_family_api_name"] == "standardNCadsH100v5Family"
    assert requested["requested_new_limit"] == 40
    assert requested["requested_instances"] == 1
    assert requested["target_sku"] == "Standard_NC40ads_H100_v5"
    assert requested["capacity_type"] == "standard on-demand"
    assert requested["spot_requested"] is False
    assert requested["more_than_forty_h100_vcpus_requested"] is False
    assert requested["multiple_instances_requested"] is False
    assert requested["multiple_regions_requested_simultaneously"] is False
    assert requested["another_gpu_family_requested_in_this_ticket"] is False


def test_the_ticket_uses_the_registered_issue_and_quota_type(receipt):
    ticket = receipt["submitted_support_ticket"]
    assert ticket["issue_type"] == "Service and subscription limits (quotas)"
    assert ticket["service_display_name"] == \
        "Service and subscription limits (quotas)"
    assert ticket["problem_classification_display_name"] == \
        "Compute-VM (cores-vCPUs) subscription limit increases"
    assert ticket["title"] == (
        "Manual enablement request: one NC40ads_H100_v5 GPU VM for bounded "
        "non-production research")


def test_the_receipt_binds_the_failed_self_service_request(receipt):
    predecessor = receipt["predecessor"]
    assert predecessor["failed_self_service_request_id"] == \
        FAILED_SELF_SERVICE_REQUEST
    assert predecessor["failed_self_service_error_code"] == \
        "QuotaNotAvailableForResource"
    assert predecessor["commit"] == E1_HEAD_COMMIT


# ---------------------------------------------------------------------------
# 3. The A100 fallback is gated, not merely discouraged
# ---------------------------------------------------------------------------


def test_the_a100_fallback_never_coexists_with_an_unresolved_h100_request(
        status, receipt):
    fallback = status["a100_fallback"]
    assert fallback["coexists_with_an_unresolved_h100_request"] is False
    h100_unresolved = not status["support_ticket"]["azure_decision_recorded"]
    if h100_unresolved:
        assert fallback["authorized"] is False
        assert fallback["submitted"] is False
        assert receipt["a100_fallback"]["authorized"] is False
        assert receipt["a100_fallback"]["submitted"] is False


def test_the_registered_fallback_parameters_are_pinned(receipt):
    fallback = receipt["a100_fallback"]
    assert fallback["registered_sku"] == "Standard_NC24ads_A100_v4"
    assert fallback["registered_family"] == "Standard NCADSA100v4 Family vCPUs"
    assert fallback["registered_region"] == "brazilsouth"
    assert fallback["registered_new_limit"] == 24
    assert fallback["registered_instances"] == 1


# ---------------------------------------------------------------------------
# 4. Resumption is gated on visible quota, never on a message
# ---------------------------------------------------------------------------


def _quota_is_approved(h100_limit: int, a100_limit: int,
                       h100_denied_in_every_region: bool = False) -> bool:
    """The registered section 5 approval rule, as an executable predicate."""
    if h100_limit >= H100_APPROVAL_LIMIT:
        return True
    if h100_denied_in_every_region and a100_limit >= A100_APPROVAL_LIMIT:
        return True
    return False


@pytest.mark.parametrize("h100,a100,denied,expected", [
    (0, 0, False, False),
    (24, 0, False, False),
    (39, 0, False, False),
    (40, 0, False, True),
    (80, 0, False, True),
    (0, 24, False, False),      # A100 alone is not enough without a denial
    (0, 24, True, True),
    (0, 23, True, False),
])
def test_quota_counts_as_approved_only_when_visibly_at_the_registered_limit(
        h100, a100, denied, expected):
    assert _quota_is_approved(h100, a100, denied) is expected


def test_the_current_quota_state_does_not_authorize_resumption(status):
    quota = status["quota"]
    approved = _quota_is_approved(quota["h100_family_limit"],
                                  quota["a100_family_limit"],
                                  status["a100_fallback"]["authorized"])
    assert quota["qualifying_quota_visible"] is approved
    if not approved:
        assert status["execution_reachability"][
            "e1_execution_became_reachable"] is False
        assert status["execution_reachability"][
            "conditional_resumption_entered"] is False
        assert status["authorization_flags"]["provisioning_authorized"] is False
        assert status["authorization_flags"][
            "deployment_attempt_authorized"] is False


def test_an_approval_message_alone_is_never_sufficient():
    """A ticket status of any kind, with zero visible quota, is not approval."""
    for ticket_status in ("Open", "Closed", "Approved", "Resolved"):
        assert _quota_is_approved(0, 0) is False, ticket_status


def test_an_azure_acknowledgement_is_never_recorded_as_an_approval(status,
                                                                   receipt):
    """Microsoft acknowledging receipt is not a decision and grants nothing."""
    ack = receipt["submitted_support_ticket"].get("azure_acknowledgement")
    if ack is None:
        return
    assert ack["is_an_approval"] is False
    assert ack["is_a_denial"] is False
    assert ack["grants_quota"] is False
    assert ack["kind"] == "receipt_acknowledgement_only"
    assert status["support_ticket"]["azure_acknowledgement_is_an_approval"] \
        is False
    assert status["support_ticket"]["azure_decision_recorded"] is False
    # And an acknowledgement never moves the quota gate.
    assert status["quota"]["qualifying_quota_visible"] is False
    assert status["quota"]["h100_family_limit"] < H100_APPROVAL_LIMIT
    assert status["execution_reachability"][
        "e1_execution_became_reachable"] is False
    # The acknowledgement must restate the registered request, unchanged.
    assert ack["restates_the_requested_new_limit"] == 40
    assert ack["restates_the_requested_family"] == "standardNCadsH100v5Family"


def test_no_claim_that_azure_is_reviewing_beyond_the_recorded_status(status,
                                                                     receipt):
    assert status["support_ticket"][
        "azure_is_reviewing_claimed_beyond_the_recorded_status"] is False
    assert receipt["claim_boundary"][
        "claims_azure_is_reviewing_beyond_the_recorded_ticket_status"] is False


# ---------------------------------------------------------------------------
# 5. Redaction
# ---------------------------------------------------------------------------


def test_no_committed_q1_artifact_leaks_a_full_identifier_or_a_secret():
    """No credential, and no bare GUID except the recorded failed request.

    The support ticket ID is not a GUID, so it is checked separately: it must
    appear only as a salted hash and a four-character suffix.
    """
    allowed_guids = {FAILED_SELF_SERVICE_REQUEST}
    # Assembled from fragments so this module never contains a credential
    # marker verbatim. A scanner that trips other scanners is a nuisance, and
    # the E1 successor runs exactly such a scan over this whole namespace.
    forbidden = tuple("BEGIN " + tail for tail in
                      ("OPENSSH PRIVATE" + " KEY", "RSA PRIVATE" + " KEY",
                       "PRIVATE" + " KEY")) + (
        "?" + "sv=", "&" + "sig=", "access" + "_token=",
        "client" + "_secret", "support" + "PlanId")
    scanner = str(HERE.relative_to(ROOT)).replace("\\", "/")
    tracked = [line.strip() for line
               in _git("ls-files",
                       "studies/study4f/execution-e1/quota-escalation-q1"
                       ).splitlines() if line.strip()]
    assert tracked, "the Q1 namespace has no committed file"
    assert scanner in tracked
    for relative in tracked:
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        if relative != scanner:
            for marker in forbidden:
                assert marker not in text, (relative, marker)
        leaked = sorted(set(GUID.findall(text)) - allowed_guids)
        assert leaked == [], (relative, leaked)


def test_the_support_ticket_id_appears_only_as_a_salted_hash(status, receipt):
    ticket = receipt["submitted_support_ticket"]
    assert ticket["ticket_id_committed_in_full"] is False
    assert len(ticket["ticket_id_salted_sha256"]) == 64
    assert len(ticket["ticket_id_last_four"]) == 4
    assert status["support_ticket"]["ticket_id_salted_sha256"] == \
        ticket["ticket_id_salted_sha256"]
    assert status["support_ticket"]["ticket_id_last_four"] == \
        ticket["ticket_id_last_four"]
    # The salt binds the hash to this authority, so it cannot be replayed.
    assert "<q1 authority commit>" in ticket["ticket_id_salt_material"]
    # And a bare sixteen-digit support case number never appears anywhere.
    case_number = re.compile(r"\b\d{16}\b")
    tracked = [line.strip() for line
               in _git("ls-files",
                       "studies/study4f/execution-e1/quota-escalation-q1"
                       ).splitlines() if line.strip()]
    for relative in tracked:
        text = (ROOT / relative).read_text(encoding="utf-8", errors="replace")
        assert case_number.search(text) is None, relative


def test_the_subscription_is_represented_only_by_a_salted_hash(receipt,
                                                               e1_status):
    requested = receipt["requested_quota"]
    assert requested["subscription_id_committed"] is False
    assert requested["tenant_id_committed"] is False
    assert requested["subscription_last_four"] == "d32e"
    assert len(requested["subscription_salted_sha256"]) == 64
    # It reuses the identity the E1 successor already published.
    assert requested["subscription_salted_sha256"] == \
        e1_status["azure"]["subscription_salted_sha256"]
    assert requested["subscription_last_four"] == \
        e1_status["azure"]["subscription_last_four"]


# ---------------------------------------------------------------------------
# 6. Schemas, states and counters
# ---------------------------------------------------------------------------


def test_status_validates_against_its_restrictive_schema(status):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(status, _json(STATUS_SCHEMA))


def test_the_receipt_validates_against_its_restrictive_schema(receipt):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(receipt, _json(RECEIPT_SCHEMA))


def test_the_lifecycle_state_is_exactly_one_registered_q1_state(status,
                                                                receipt):
    assert status["lifecycle_state"] in REGISTERED_Q1_STATES
    assert receipt["state"] in REGISTERED_Q1_STATES
    assert receipt["state"] == status["lifecycle_state"]


def test_the_state_matches_the_ticket_outcome_branch(status, receipt):
    """4.1 succeeded -> awaiting; 4.2 unauthorized -> manual submission."""
    if status["support_ticket"]["manual_portal_submission_required"]:
        assert status["lifecycle_state"] == \
            "STUDY4F_E1_Q1_MANUAL_PORTAL_SUBMISSION_REQUIRED"
        assert status["support_ticket"]["tickets_created_in_this_invocation"] == 0
    else:
        assert status["lifecycle_state"] == \
            "STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION"
        assert status["support_ticket"]["tickets_created_in_this_invocation"] == 1
        assert receipt["authority_section"] == "4.1"


def test_ticket_not_filed_is_distinguishable_from_ticket_pending():
    """The two registered states are different strings for a reason."""
    assert "MANUAL_PORTAL_SUBMISSION_REQUIRED" in REGISTERED_Q1_STATES[1]
    assert "AWAITING_AZURE_SUPPORT_DECISION" in REGISTERED_Q1_STATES[0]
    assert REGISTERED_Q1_STATES[0] != REGISTERED_Q1_STATES[1]


def test_every_authorization_flag_and_counter_is_false_or_zero(status):
    assert not any(status["authorization_flags"].values())
    assert not any(status["claim_boundary"].values())
    assert all(value == 0 for value in status["zero_operation_counters"].values())
    assert all(value == 0
               for value in status["azure_resource_counters"].values()) \
        if "azure_resource_counters" in status else True


def test_the_receipt_reports_zero_azure_resources(receipt):
    assert all(value == 0
               for value in receipt["azure_resource_counters"].values())


def test_the_shakedown_allowance_is_carried_forward_unconsumed(status):
    allowance = status["shakedown_allowance_carried_forward"]
    assert allowance["attempts_remaining"] == 2
    assert allowance["accelerator_hours_remaining"] == 6
    assert allowance["consumed_by_this_invocation"] == 0


def test_q1_is_not_a_study_a_revision_a_review_or_an_amendment(status):
    assert status["is_a_new_study"] is False
    assert status["is_a_protocol_revision"] is False
    assert status["is_a_methods_review"] is False
    assert status["is_a_scientific_amendment"] is False
    assert status["kind"] == "manual_quota_escalation_and_conditional_resume"


def test_q1_routes_only_itself(status, e1_status):
    assert status["routes_only_this_quota_escalation"] is True
    assert status["namespace"] == \
        "studies/study4f/execution-e1/quota-escalation-q1/"
    # The E1 router is untouched and still owns the E1 lifecycle.
    assert e1_status["lifecycle_state"] == \
        "STUDY4F_E1_AWAITING_AZURE_GPU_QUOTA_APPROVAL"
    assert status["predecessor_chain"]["study4f_e1_lifecycle_state"] == \
        e1_status["lifecycle_state"]


# ---------------------------------------------------------------------------
# 7. Every predecessor byte is untouched
# ---------------------------------------------------------------------------


def test_q1_added_paths_only_inside_its_own_namespace_and_the_authority():
    statuses = {}
    for line in _git("diff", "--name-status", E1_HEAD_COMMIT,
                     "HEAD").splitlines():
        if not line.strip():
            continue
        code, path = line.split("\t", 1)
        statuses[path.strip()] = code.strip()
    other = {path for path, code in statuses.items() if code != "A"}
    assert other == set(), sorted(other)
    added = set(statuses)
    allowed_prefix = "studies/study4f/execution-e1/quota-escalation-q1/"
    authority = ("studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation"
                 "_and_conditional_resume_authority.md")
    outside = sorted(path for path in added
                     if not path.startswith(allowed_prefix)
                     and path != authority)
    assert outside == [], outside


@pytest.mark.parametrize("path", [
    "studies/study4f/execution-e1/STATUS.json",
    "studies/study4f/execution-e1/STATUS.schema.json",
    "studies/study4f/execution-e1/STUDY4F_E1_TERMINAL_DISCLOSURE.md",
    "studies/study4f/execution-e1/azure/azure_discovery.json",
    "studies/study4f/execution-e1/azure/quota_disposition.json",
    "studies/study4f/execution-e1/azure/operator_quota_request_packet.md",
    "studies/study4f/execution-e1/analysis/study4f_e1_instrument_binding.py",
    "studies/study4f/execution-e1/analysis/study4f_e1_resource_selection.py",
    "studies/study4f/execution-e1/analysis/study4f_e1_runtime_preflight.py",
    "studies/study4f/execution-e1/analysis/study4f_e1_deployment_plan.py",
    "studies/study4f/execution-e1/analysis/study4f_e1_lifecycle.py",
    "studies/study4f/execution-e1/tests/"
    "test_study4f_e1_qualifying_accelerator_execution.py",
    "studies/study4f/prompts/study4f_e1_qualifying_accelerator_execution_authority.md",
    "studies/study4f/STATUS.json",
    "studies/study4f/protocol/study4f_protocol_v1.json",
    "studies/study4f/analysis/study4f_state_machine.py",
    "studies/study4f/tests/test_study4f_behavioral_feasibility.py",
    "paper/evidence_ledger.csv",
    ".gitattributes",
    "tests/test_study3r_protocol_v1.py",
    "tests/test_study3r_operator_governance.py",
])
def test_no_predecessor_byte_moved(path):
    assert _git("rev-parse", "%s:%s" % (E1_HEAD_COMMIT, path)).strip() == \
        _git("rev-parse", "HEAD:%s" % path).strip(), path


def test_the_one_new_scope_expiry_is_mechanically_scope_only():
    """Section 7. The E1 namespace predicate expires, and cannot be repaired.

    ``studies/study4f/execution-e1/tests/...::test_the_successor_added_paths_
    only_inside_its_own_namespace`` compares ``git diff --name-status`` from the
    Study 4F head to ``HEAD`` and admits only paths under
    ``studies/study4f/execution-e1/`` plus the E1 authority. The Q1 authority
    requires publishing at
    ``studies/study4f/prompts/study4f_e1_q1_..._authority.md``, which is outside
    that set, and section 1 of the Q1 authority fixes that path exactly. The E1
    module is a predecessor byte this authority forbids modifying, so there is
    no publication of Q1 that leaves the assertion passing and no repair that
    does not change a protected byte.

    All five conditions for recording rather than repairing are proved here.
    """
    module = ("studies/study4f/execution-e1/tests/"
              "test_study4f_e1_qualifying_accelerator_execution.py")

    # 1. The expired module is byte-identical to the predecessor head.
    assert _git("rev-parse", "%s:%s" % (E1_HEAD_COMMIT, module)).strip() == \
        _git("rev-parse", "HEAD:%s" % module).strip()

    # 2. It is solely a scope predicate over a git diff to HEAD.
    source = (ROOT / module).read_text(encoding="utf-8")
    name = "test_the_successor_added_paths_only_inside_its_own_namespace"
    assert name in source
    body = source[source.index("def %s" % name):]
    body = body[:body.index("\ndef ")]
    assert '"diff", "--name-status"' in body
    assert '"HEAD"' in body
    assert 'startswith("studies/study4f/execution-e1/")' in body
    # It asserts nothing about bytes, hashes, quotas, counters or claims.
    for substantive in ("sha256", "hashlib", "quota", "lifecycle_state"):
        assert substantive not in body, substantive

    # 3. No substantive protected byte moved: the diff since the E1 head is
    #    purely additive, and every added path is Q1's own.
    statuses = {}
    for line in _git("diff", "--name-status", E1_HEAD_COMMIT,
                     "HEAD").splitlines():
        if not line.strip():
            continue
        code, path = line.split("\t", 1)
        statuses[path.strip()] = code.strip()
    assert all(code == "A" for code in statuses.values()), statuses
    authority = ("studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation"
                 "_and_conditional_resume_authority.md")
    allowed_prefix = "studies/study4f/execution-e1/quota-escalation-q1/"
    assert all(path.startswith(allowed_prefix) or path == authority
               for path in statuses), sorted(statuses)
    # And the sole path outside the E1 namespace is exactly the Q1 authority.
    outside = sorted(path for path in statuses
                     if not path.startswith("studies/study4f/execution-e1/"))
    assert outside == [authority], outside

    # 4. The original guarantee is carried forward by successor invariants.
    for carrier in ("test_q1_added_paths_only_inside_its_own_namespace_and_the_authority",
                    "test_no_predecessor_byte_moved"):
        assert carrier in globals(), carrier

    # 5. The expiry is recorded, not suppressed.
    status = _json(STATUS_JSON)
    expiry = status["test_differential"]["scope_expiries"]
    assert expiry["count"] == 1
    record = expiry["expired_assertions"][0]
    assert record["node_id"] == "%s::%s" % (module, name)
    assert record["repaired"] is False
    assert record["suppressed"] is False
    assert record["editable_under_this_authority"] is False
    assert record["inside_the_registered_repository_baseline"] is False
    assert record["guarantee_carried_forward_by"].startswith(
        "studies/study4f/execution-e1/quota-escalation-q1/tests/")


def test_the_expired_predicate_is_outside_the_registered_repository_baseline():
    """It lives under ``studies/``, which ``testpaths = ["tests"]`` excludes.

    So the expiry cannot change the registered nine-failure baseline, and the
    repository suite at this head must still report exactly those nine.
    """
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'testpaths = ["tests"]' in pyproject
    module = ("studies/study4f/execution-e1/tests/"
              "test_study4f_e1_qualifying_accelerator_execution.py")
    assert not module.startswith("tests/")
    status = _json(STATUS_JSON)
    differential = status["test_differential"]
    assert differential["failure_node_ids_identical_to_the_starting_nine"] is True
    assert differential["new_non_scope_failures"] == 0
    assert differential["historical_failures_edited_or_suppressed"] == 0


def test_every_study3r_byte_is_identical_to_the_closure_head():
    listed = [line.strip() for line
              in _git("ls-tree", "-r", "--name-only", STUDY3R_CLOSURE_COMMIT,
                      "studies/study3r").splitlines() if line.strip()]
    assert len(listed) >= 50
    moved = [path for path in listed
             if _git("rev-parse", "%s:%s" % (STUDY3R_CLOSURE_COMMIT, path)).strip()
             != _git("rev-parse", "HEAD:%s" % path).strip()]
    assert moved == []


def test_the_evidence_ledger_is_untouched_and_ends_at_ev_0016(status):
    ledger = ROOT / "paper" / "evidence_ledger.csv"
    payload = ledger.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == \
        status["evidence_ledger"]["sha256"]
    assert payload.decode("utf-8").splitlines()[-1].startswith("EV-0016,")
    assert status["evidence_ledger"]["rows_added_by_study4f_e1_q1"] == 0


def test_no_bank_seal_or_execution_artifact_is_committed():
    committed = _git("ls-files", "studies/study4f").split()
    assert not any("bank" in path and path.endswith(".json")
                   for path in committed), committed
    assert not any("execution_seal" in path for path in committed), committed


def test_the_q1_namespace_contains_no_model_or_azure_mutating_code():
    """Q1 publishes evidence, not machinery: no runtime and no write calls."""
    import ast
    banned_modules = {"torch", "transformers", "bitsandbytes", "accelerate",
                      "vllm"}
    tracked = [line.strip() for line
               in _git("ls-files",
                       "studies/study4f/execution-e1/quota-escalation-q1"
                       ).splitlines() if line.strip().endswith(".py")]
    assert tracked
    for relative in tracked:
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not (imported & banned_modules), \
            (relative, sorted(imported & banned_modules))


# ---------------------------------------------------------------------------
# 8. Operator record and byte hygiene
# ---------------------------------------------------------------------------


def test_the_disclosure_reports_the_registered_items():
    disclosure = Q1 / "Q1_INVOCATION_DISCLOSURE.md"
    text = disclosure.read_text(encoding="utf-8")
    for required in (E1_HEAD_COMMIT, E1_HEAD_TREE, FAILED_SELF_SERVICE_REQUEST,
                     "STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION",
                     "Standard_NC40ads_H100_v5", "australiaeast",
                     "Standard NCadsH100v5 Family vCPUs",
                     "3115437c07487a4b825eaa7b5017b570db8e38da9cd88824cc88cf8147f84021",
                     "3753", "d32e", "EV-0016",
                     "9 failed, 5,119 passed, 16 skipped"):
        assert required in text, required
    lowered = text.lower()
    assert "no scientific result" in lowered
    assert "acknowledgement, not a decision" in lowered
    assert "unknown" in lowered
    # It must name the recorded expiry and prove it scope-only.
    assert "test_the_successor_added_paths_only_inside_its_own_namespace" in text
    assert "recorded, not repaired" in lowered


def test_the_operator_record_states_the_exact_registered_request():
    text = OPERATOR_RECORD.read_text(encoding="utf-8")
    for required in ("Standard_NC40ads_H100_v5", "australiaeast",
                     "Standard NCadsH100v5 Family vCPUs",
                     "Compute-VM (cores-vCPUs) subscription limit increases",
                     "Service and subscription limits (quotas)",
                     "69,502,926,848", "d32e",
                     "STUDY4F_E1_Q1_AWAITING_AZURE_SUPPORT_DECISION"):
        assert required in text, required
    lowered = text.lower()
    assert "spot" in lowered
    assert "no scientific result" in lowered
    assert "unknown" in lowered


def test_the_operator_record_asserts_no_prohibited_conclusion():
    for path in (OPERATOR_RECORD, STATUS_JSON, RECEIPT_JSON,
                 Q1 / "Q1_INVOCATION_DISCLOSURE.md"):
        text = path.read_text(encoding="utf-8").lower()
        for prohibited in ("j-space exists", "j-space does not exist",
                           "j-space is observable", "j-space is unobservable",
                           "rp-b was confirmed",
                           "capacity is unavailable",
                           "capacity is available"):
            assert prohibited not in text, (path.name, prohibited)


def test_the_status_routes_to_itself_first():
    text = OPERATOR_RECORD.read_text(encoding="utf-8")
    assert "STATUS.json" in text
    assert text.index("STATUS.json") < text.index("Ticket ID")


@pytest.mark.parametrize("relative", sorted(
    str(path.relative_to(ROOT)).replace("\\", "/")
    for path in list(Q1.rglob("*.py")) + list(Q1.rglob("*.json"))
    + list(Q1.rglob("*.md"))) + [
    "studies/study4f/prompts/study4f_e1_q1_manual_quota_escalation"
    "_and_conditional_resume_authority.md"])
def test_every_q1_artifact_is_lf_only(relative):
    payload = (ROOT / relative).read_bytes()
    assert payload
    assert b"\r" not in payload, relative
    assert payload.endswith(b"\n"), relative
    assert not payload.startswith(b"\xef\xbb\xbf"), relative
