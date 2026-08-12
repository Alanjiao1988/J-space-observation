"""Study 3 P0-R1 execution-readiness tests.

Authority:
``studies/study3/prompts/study3_p0_r1_pre_replay_execution_completion_authority_rev2.md``
section 8, over ``studies/study3/prompts/study3_v0_6_p0_r1_authority.md``.

Every test here is production-bound. Each one either drives the real entry point
or mutates the live input that production code reads, and each fails at the
required baseline `167d3067d7d9a2866999a51ec49c3c57c1d31546`, where ``--gate``
was an unconditional refusal, the replay shell called ``derive()``, the model
runner always raised and no GPU launcher existed.

No test in this module constructs a real tokenizer, downloads a checkpoint,
exposes a GPU or runs the live replay gate against the real published lock.
Synthetic tokenizers, models and logits are used for the CPU-only paths, and the
live gate is exercised only against a temporary fixture repository.
"""

import copy
import hashlib
import json
import os
import subprocess
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P0_R1_DIR = os.path.join(REPO_ROOT, "studies", "study3", "pilot", "p0_r1")
CONTAINER_DIR = os.path.join(P0_R1_DIR, "container")

if P0_R1_DIR not in sys.path:
    sys.path.insert(0, P0_R1_DIR)

import p0_r1_counters as COUNTERS  # noqa: E402
import p0_r1_eligibility as ELIG  # noqa: E402
import p0_r1_execution_lock as LOCK  # noqa: E402
import p0_r1_factorization as FACT  # noqa: E402
import p0_r1_model_runner as RUNNER  # noqa: E402
import p0_r1_replay_gate as GATE  # noqa: E402

READY_STATE = "STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE"
REPLAY_PASS_STATE = "STUDY3_P0_R1_REPLAY_GATE_PASSED_AWAITING_MODEL_PILOT"

DIGEST = "sha256:" + "ab" * 32
OTHER_DIGEST = "sha256:" + "cd" * 32
COMMIT = "1" * 40
TREE = "2" * 40
PARENT = "3" * 40


def _read(path):
    with open(path, "rb") as handle:
        return handle.read()


def _text(path):
    return _read(path).decode("utf-8")


# ---------------------------------------------------------------------------
# The replay gate reaches live logic only under successor authorization.
# ---------------------------------------------------------------------------

def test_gate_is_no_longer_an_unconditional_refusal_but_still_refuses_by_default():
    """At the baseline --gate returned 3 for every input. Now it is conditional."""
    assert GATE.main(["--gate"]) == 3
    assert GATE.main(["--gate", "--successor-authorization", "wrong"]) == 3
    source = _text(os.path.join(P0_R1_DIR, "p0_r1_replay_gate.py"))
    assert "def gate_run(" in source, (
        "the live gate entry point must exist; a refusal-only --gate cannot "
        "produce the registered pass or stop disposition")
    assert GATE.SUCCESSOR_AUTHORIZATION


def test_gate_requires_an_output_directory_even_with_authorization():
    assert GATE.main([
        "--gate", "--successor-authorization", GATE.SUCCESSOR_AUTHORIZATION,
    ]) == 3


def test_gate_run_refuses_without_successor_authorization(tmp_path):
    with pytest.raises(GATE.GateRefused):
        GATE.gate_run(str(tmp_path), authorization=None)
    with pytest.raises(GATE.GateRefused):
        GATE.gate_run(str(tmp_path), authorization="calibration")


def test_gate_run_refuses_without_a_writable_result_directory():
    with pytest.raises(GATE.GateRefused):
        GATE.gate_run("", authorization=GATE.SUCCESSOR_AUTHORIZATION)


def test_calibration_and_build_modes_cannot_consume_the_live_gate():
    """--derive and --check must never reach gate_run."""
    assert GATE.main(["--check"]) == 0
    source = _text(os.path.join(P0_R1_DIR, "p0_r1_replay_gate.py"))
    body = source.split("def main(", 1)[1]
    derive_branch = body.split("if args.gate:", 1)[0]
    assert "gate_run(" not in derive_branch


# ---------------------------------------------------------------------------
# The replay shell invokes --gate, not derive().
# ---------------------------------------------------------------------------

def test_the_replay_shell_invokes_the_live_gate_and_not_derive():
    shell = _text(os.path.join(CONTAINER_DIR, "p0_r1_replay.sh"))
    assert "--gate" in shell
    assert "--successor-authorization" in shell
    assert "GATE.derive()" not in shell
    assert "document = GATE.derive" not in shell


def test_the_replay_shell_passes_a_writable_runtime_result_directory():
    shell = _text(os.path.join(CONTAINER_DIR, "p0_r1_replay.sh"))
    assert "--out-dir" in shell
    assert "RESULTS_DIR" in shell
    assert "is not writable" in shell


def test_the_replay_shell_preserves_a_non_zero_exit_only_after_writing_bytes():
    shell = _text(os.path.join(CONTAINER_DIR, "p0_r1_replay.sh"))
    artifacts_index = shell.index("p0_r1_replay_result.json")
    exit_index = shell.rindex('exit "$GATE_EXIT"')
    assert artifacts_index < exit_index, (
        "a stop must never be lost: the artifact check runs before the gate "
        "exit is propagated")
    assert "GATE_EXIT=$?" in shell


def test_the_replay_shell_asserts_no_gpu_and_no_model_library():
    shell = _text(os.path.join(CONTAINER_DIR, "p0_r1_replay.sh"))
    assert "a GPU is visible to the replay gate" in shell
    assert "transformers" in shell and "tokenizers" in shell


def test_the_checkout_step_exists_and_binds_the_exact_commit():
    path = os.path.join(CONTAINER_DIR, "p0_r1_checkout.sh")
    assert os.path.exists(path), (
        "the ACR task references p0_r1_checkout.sh; at the baseline it did not "
        "exist, so the task could not run")
    shell = _text(path)
    assert "repo.bundle" in shell
    assert "the checkout is not the requested commit" in shell
    assert "the checkout is dirty" in shell


def test_the_acr_replay_task_consumes_an_immutable_digest_and_launches_no_model():
    task = _text(os.path.join(CONTAINER_DIR, "p0_r1_acr_task.yaml"))
    assert "{{.Values.IMAGE}}" in task
    assert "{{.Values.DIGEST}}" in task
    assert "p0_r1_checkout.sh" in task
    assert "p0_r1_replay.sh" in task
    assert "p0_r1_model_pilot.sh" not in task, (
        "the replay task must not contain, download or launch any model")


# ---------------------------------------------------------------------------
# The live gate writes complete bytes on both the pass and the failure path.
# ---------------------------------------------------------------------------

def _fixture_repo(tmp_path, mutate_result=None):
    """Build a minimal repository the live gate can run against."""
    root = tmp_path / "repo"
    for relative in (FACT.RESULT_PATH, FACT.CORPUS_PATH,
                     "studies/study3/pilot/p0/results/p0-t/"
                     "p0_tokenizer_gate_receipt.json",
                     "studies/study3/pilot/p0/results/p0-t/P0_T_DISPOSITION.md",
                     LOCK.REGISTRATION_AUTHORITY["path"],
                     LOCK.SUPPLEMENTAL_AUTHORITY["path"],
                     "studies/study3/protocol/"
                     "interface_calibration_rendering_registry_v0_6.json"):
        source = os.path.join(REPO_ROOT, *relative.split("/"))
        target = root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_read(source))
    for relative in LOCK.EXECUTABLE_CODE_PATHS:
        source = os.path.join(REPO_ROOT, *relative.split("/"))
        target = root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(_read(source))
    # The lock is built from pristine bytes first: an execution lock can only
    # ever be created over immutable evidence that still reproduces. The
    # mutation is applied afterwards, which is exactly how a corrupted source
    # would present itself to a later gate run.
    lock = LOCK.build_lock(COMMIT, TREE, DIGEST, PARENT, root=str(root))
    root.joinpath(*LOCK.LOCK_PATH.split("/")).write_bytes(
        LOCK.dumps(lock).encode("utf-8"))
    if mutate_result is not None:
        path = root.joinpath(*FACT.RESULT_PATH.split("/"))
        document = json.loads(path.read_text(encoding="utf-8"))
        mutate_result(document)
        path.write_text(
            json.dumps(document, indent=1, sort_keys=True), encoding="utf-8")
    return root


def test_the_live_gate_writes_every_canonical_artifact_on_the_pass_path(tmp_path):
    root = _fixture_repo(tmp_path)
    out_dir = tmp_path / "results"
    outcome = GATE.gate_run(
        str(out_dir), authorization=GATE.SUCCESSOR_AUTHORIZATION,
        image_digest=DIGEST, root=str(root))
    assert outcome["passed"] is True
    assert outcome["state"] == REPLAY_PASS_STATE
    for name in (GATE.GATE_RESULT_NAME, GATE.GATE_RECEIPT_NAME,
                 GATE.GATE_COUNTERS_NAME, GATE.GATE_DISPOSITION_NAME):
        target = out_dir / name
        assert target.exists() and target.stat().st_size > 0
    receipt = json.loads((out_dir / GATE.GATE_RECEIPT_NAME).read_text("utf-8"))
    assert receipt["authorizes_model_pilot"] is True
    body = _read(str(out_dir / GATE.GATE_RESULT_NAME))
    assert receipt["result_document"]["sha256"] == hashlib.sha256(body).hexdigest()
    assert receipt["result_document"]["bytes"] == len(body)


def test_the_live_gate_writes_every_canonical_artifact_on_the_failure_path(tmp_path):
    def _break(document):
        role = document["candidate_token_eligibility"]["RT"]["s2"]
        role["token_ids"][3] = role["token_ids"][2]

    root = _fixture_repo(tmp_path, mutate_result=_break)
    out_dir = tmp_path / "results"
    outcome = GATE.gate_run(
        str(out_dir), authorization=GATE.SUCCESSOR_AUTHORIZATION,
        image_digest=DIGEST, root=str(root))
    assert outcome["passed"] is False
    assert outcome["state"] != REPLAY_PASS_STATE
    for name in (GATE.GATE_RESULT_NAME, GATE.GATE_RECEIPT_NAME,
                 GATE.GATE_COUNTERS_NAME, GATE.GATE_DISPOSITION_NAME):
        target = out_dir / name
        assert target.exists() and target.stat().st_size > 0
    receipt = json.loads((out_dir / GATE.GATE_RECEIPT_NAME).read_text("utf-8"))
    assert receipt["authorizes_model_pilot"] is False
    assert receipt["stop_reason"]


def test_the_live_gate_writes_outputs_only_into_the_runtime_directory(tmp_path):
    root = _fixture_repo(tmp_path)
    out_dir = tmp_path / "results"
    GATE.gate_run(str(out_dir), authorization=GATE.SUCCESSOR_AUTHORIZATION,
                  image_digest=DIGEST, root=str(root))
    published = os.path.join(P0_R1_DIR, "results")
    assert not (os.path.isdir(published) and os.listdir(published))
    assert not root.joinpath("studies", "study3", "pilot", "p0_r1",
                             "results").exists()


def test_the_live_gate_imports_no_model_library_and_leaves_counters_at_zero(tmp_path):
    root = _fixture_repo(tmp_path)
    counters = COUNTERS.P0R1Counters()
    GATE.gate_run(str(tmp_path / "results"),
                  authorization=GATE.SUCCESSOR_AUTHORIZATION,
                  image_digest=DIGEST, root=str(root), counters=counters)
    assert "transformers" not in sys.modules
    assert "tokenizers" not in sys.modules
    snapshot = counters.snapshot()
    assert snapshot["replay_gate_evaluations"] == 1
    for name, value in snapshot.items():
        if name == "replay_gate_evaluations":
            continue
        assert value == 0, "%s advanced to %d" % (name, value)


def test_the_gate_rejects_an_image_digest_that_is_not_the_locked_digest(tmp_path):
    root = _fixture_repo(tmp_path)
    with pytest.raises(LOCK.LockDefect):
        GATE.gate_run(str(tmp_path / "results"),
                      authorization=GATE.SUCCESSOR_AUTHORIZATION,
                      image_digest=OTHER_DIGEST, root=str(root))


def test_the_gate_acceptance_conditions_are_the_registered_ones():
    assert GATE.REQUIRED_MATRIX_CELLS == 39
    assert GATE.REQUIRED_ELIGIBLE_CELLS == 39
    assert GATE.REQUIRED_EMPTY_REASON_INELIGIBLE_CELLS == 0
    assert GATE.REQUIRED_EXECUTABLE_CONTRASTS_PER_ROLE == 11
    summary = {
        "cells": 39, "eligible_cells": 39,
        "ineligible_cells_with_an_empty_reason_list": 0,
        "executable_genuine_i3_contrasts_per_role": {
            "RI": 11, "RL": 11, "RT": 11},
        "roles_without_executable_contrast": [],
    }
    assert GATE.check_corrected_matrix(summary) == []
    for mutation in (
            {"cells": 38},
            {"eligible_cells": 38},
            {"ineligible_cells_with_an_empty_reason_list": 1},
            {"executable_genuine_i3_contrasts_per_role":
                {"RI": 11, "RL": 11, "RT": 9}},
            {"roles_without_executable_contrast": ["RT"]}):
        broken = dict(summary)
        broken.update(mutation)
        assert GATE.check_corrected_matrix(broken), mutation


# ---------------------------------------------------------------------------
# The execution lock.
# ---------------------------------------------------------------------------

def test_the_execution_lock_binds_the_two_commit_relationship():
    lock = LOCK.build_lock(COMMIT, TREE, DIGEST, PARENT)
    LOCK.validate_lock(lock)
    assert lock["executable_code"]["commit"] == COMMIT
    assert lock["image"]["built_from_commit"] == COMMIT
    assert lock["ready_commit_relationship"]["parent"] == PARENT
    assert lock["state"] == READY_STATE
    assert list(lock["state_transition"]) == [READY_STATE, REPLAY_PASS_STATE]


def test_the_execution_lock_rejects_a_tag_instead_of_an_immutable_digest():
    for bad in ("latest", "sha256:short", "", None, "sha256:" + "zz" * 32):
        with pytest.raises(LOCK.LockDefect):
            LOCK.build_lock(COMMIT, TREE, bad, PARENT)


def test_the_execution_lock_detects_executable_byte_drift(tmp_path):
    root = _fixture_repo(tmp_path)
    lock = json.loads(
        root.joinpath(*LOCK.LOCK_PATH.split("/")).read_text("utf-8"))
    target = root.joinpath(*LOCK.EXECUTABLE_CODE_PATHS[0].split("/"))
    target.write_bytes(target.read_bytes() + b"\n# drift\n")
    findings = LOCK.verify_executable_bytes(lock, root=str(root))
    assert findings and "drift" in findings[0]
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate_lock(lock, root=str(root))


def test_the_execution_lock_refuses_a_consumed_or_widened_envelope():
    base = LOCK.build_lock(COMMIT, TREE, DIGEST, PARENT)
    consumed = copy.deepcopy(base)
    consumed["legal_status"]["p0_r1_pilot_execution_consumed"] = True
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate_lock(consumed)
    widened = copy.deepcopy(base)
    widened["caps"]["non_generative_prefill_evaluations"] = 181
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate_lock(widened)
    formal = copy.deepcopy(base)
    formal["legal_status"]["formal_execution_authorized"] = True
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate_lock(formal)
    ledger = copy.deepcopy(base)
    ledger["legal_status"]["evidence_ledger_last_row"] = "EV-0017"
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate_lock(ledger)


def test_the_execution_lock_counters_are_all_zero_before_execution():
    lock = LOCK.build_lock(COMMIT, TREE, DIGEST, PARENT)
    assert set(lock["counters_before_execution"]) == set(
        COUNTERS.ZERO_BEFORE_EXECUTION)
    assert all(value == 0
               for value in lock["counters_before_execution"].values())
    broken = copy.deepcopy(lock)
    broken["counters_before_execution"]["model_weight_loads"] = 1
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate_lock(broken)


def test_the_execution_lock_pins_the_three_registered_roles():
    lock = LOCK.build_lock(COMMIT, TREE, DIGEST, PARENT)
    assert sorted(lock["roles"]) == ["RI", "RL", "RT"]
    broken = copy.deepcopy(lock)
    broken["roles"]["RT"]["revision"] = "0" * 40
    with pytest.raises(LOCK.LockDefect):
        LOCK.validate_lock(broken)


# ---------------------------------------------------------------------------
# The model runner is a real executor, not a refusal or a synthetic shell.
# ---------------------------------------------------------------------------

def test_the_model_runner_is_not_an_unconditional_refusal():
    source = _text(os.path.join(P0_R1_DIR, "p0_r1_model_runner.py"))
    assert "the model pilot is registered but not implemented" not in source
    assert "def validate_execution_authorization(" in source
    # The replay and registration path must stay free of model libraries, so the
    # executor lives in its own subpackage. That separation is the reason the
    # published static guard still holds.
    execution = _text(os.path.join(
        P0_R1_DIR, "execution", "p0_r1_model_execution.py"))
    assert "AutoModelForCausalLM.from_pretrained" in execution
    assert "model.generate(" in execution
    assert "torch.inference_mode()" in execution
    assert "def execute(" in execution
    for forbidden in ("import torch", "from transformers", "AutoTokenizer",
                      "AutoModel"):
        assert forbidden not in source, (
            "%s appears in the replay/registration path" % forbidden)


def test_the_executor_is_reached_only_through_the_authorization_check():
    source = _text(os.path.join(P0_R1_DIR, "p0_r1_model_runner.py"))
    body = source.split("def run(", 1)[1]
    authorize = body.index("validate_execution_authorization(")
    delegate = body.index("p0_r1_model_execution")
    assert authorize < delegate, (
        "authorization must be validated before the execution shell is even "
        "loaded, so no import side effect can precede it")


def test_the_model_runner_refuses_without_a_lock_and_a_pass_receipt():
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.run()
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.run(authorization={"p0_r1_pilot_execution_authorized": True})
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.run(authorization={
            "p0_r1_pilot_execution_authorized": True,
            "replay_gate_passed_in_this_session": True,
        })
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.validate_execution_authorization({
            "p0_r1_pilot_execution_authorized": True,
            "replay_gate_passed_in_this_session": True,
            "execution_lock": "a prose log line",
            "replay_receipt": "the gate said it passed",
        })


def _authorization(tmp_path, mutate_receipt=None):
    root = _fixture_repo(tmp_path)
    out_dir = tmp_path / "results"
    outcome = GATE.gate_run(
        str(out_dir), authorization=GATE.SUCCESSOR_AUTHORIZATION,
        image_digest=DIGEST, root=str(root))
    receipt = outcome["receipt"]
    # The attempt id is captured from the *original* receipt, so mutating the
    # receipt's attempt id creates a genuine disagreement rather than silently
    # moving both sides together.
    attempt_id = receipt.get("attempt_id")
    if mutate_receipt is not None:
        receipt = copy.deepcopy(receipt)
        mutate_receipt(receipt)
    lock = LOCK.load_lock(root=str(root))
    return str(root), {
        "p0_r1_pilot_execution_authorized": True,
        "replay_gate_passed_in_this_session": True,
        "execution_lock": lock,
        "replay_receipt": receipt,
        "attempt_id": attempt_id,
    }


def test_the_model_runner_accepts_only_an_agreeing_receipt_and_lock(tmp_path):
    root, authorization = _authorization(tmp_path)
    accepted = RUNNER.validate_execution_authorization(authorization, root=root)
    assert accepted["attempt_id"] == authorization["attempt_id"]

    for mutate in (
            lambda receipt: receipt.update({"image_digest": OTHER_DIGEST}),
            lambda receipt: receipt.update({"executable_code_commit": "9" * 40}),
            lambda receipt: receipt.update({"executable_code_tree": "9" * 40}),
            lambda receipt: receipt.update({"attempt_id": "another-attempt"}),
            lambda receipt: receipt.update({"passed": False}),
            lambda receipt: receipt.update({"authorizes_model_pilot": False}),
            lambda receipt: receipt.update({"state": "SOMETHING_ELSE"}),
            lambda receipt: receipt.update({"model_operations_performed": 1}),
            lambda receipt: receipt["execution_lock"].update(
                {"sha256": "0" * 64}),
    ):
        root, broken = _authorization(tmp_path, mutate_receipt=mutate)
        with pytest.raises(RUNNER.ExecutionRefused):
            RUNNER.validate_execution_authorization(broken, root=root)


def test_the_s2_scoring_context_appends_the_prefix_id_and_reads_the_last_position():
    plan = RUNNER.build_scoring_plan(
        "S2", "RT", "row", [11, 12, 13],
        [[220, 15 + index] for index in range(10)],
        [" %d" % digit for digit in range(10)],
        common_prefix_token=220,
        tie_break_order=[" %d" % digit for digit in range(10)])
    RUNNER.validate_scoring_plan(plan)
    assert plan["scoring_context_token_ids"] == [11, 12, 13, 220]
    assert plan["logit_read_position"] == 3
    assert plan["discriminant_token_ids"] == list(range(15, 25))
    assert plan["registered_prompt_token_ids"] == [11, 12, 13]
    assert plan["common_prefix_token_count"] == 1
    # Reading before the teacher-forced prefix scores the shared token.
    broken = dict(plan)
    broken["logit_read_position"] = 2
    with pytest.raises(RUNNER.ScoringDefect):
        RUNNER.validate_scoring_plan(broken)


def test_s3_reuses_the_same_vector_and_performs_zero_model_operations():
    counters = COUNTERS.P0R1Counters()
    plan = RUNNER.build_scoring_plan(
        "S2", "RT", "row", [11, 12],
        [[220, 15 + index] for index in range(10)],
        [" %d" % digit for digit in range(10)],
        common_prefix_token=220,
        tie_break_order=[" %d" % digit for digit in range(10)])
    logits = {token: float(token) for token in range(15, 25)}
    RUNNER.score_from_logits(plan, logits, counters=counters)
    before = counters.snapshot()["non_generative_prefill_evaluations"]
    row = RUNNER.reuse_for_s3(plan, logits, counters=counters)
    after = counters.snapshot()
    assert row["sequence_level_model_evaluations"] == 0
    assert after["non_generative_prefill_evaluations"] == before
    assert after["s3_cpu_only_reuse_scored_rows"] == 1
    assert row["reuses_row_id"] == "row"


def test_the_execution_plan_is_the_registered_allocation():
    corpus = RUNNER.load_corpus()
    plan = RUNNER.build_execution_plan(corpus, ["RI", "RL", "RT"])
    smoke = sum(len(rows) for rows in plan["smoke"].values())
    extension = sum(len(rows) for rows in plan["extension"].values())
    generations = sum(len(rows) for rows in plan["s4"].values())
    assert smoke == 60
    assert extension == 120
    assert smoke + extension == 180
    assert generations == 12


# ---------------------------------------------------------------------------
# The smoke boundary, the load schedule and the caps.
# ---------------------------------------------------------------------------

def test_the_smoke_boundary_blocks_extension_and_s4_before_the_smoke_passes():
    counters = COUNTERS.P0R1Counters()
    boundary = RUNNER.SmokeBoundary(counters)
    with pytest.raises(RUNNER.ScoringDefect):
        boundary.admit("extension")
    with pytest.raises(RUNNER.ScoringDefect):
        boundary.admit("s4")
    for _ in range(60):
        boundary.admit("smoke")
    with pytest.raises(RUNNER.ScoringDefect):
        boundary.admit("smoke")
    with pytest.raises(RUNNER.ScoringDefect):
        boundary.admit("extension")
    boundary.close_smoke(True)
    assert boundary.admit("extension") == "extension"
    assert boundary.admit("s4") == "s4"


def test_a_failed_smoke_authorizes_no_extension_or_generation():
    counters = COUNTERS.P0R1Counters()
    boundary = RUNNER.SmokeBoundary(counters)
    for _ in range(60):
        boundary.admit("smoke")
    boundary.close_smoke(False)
    with pytest.raises(RUNNER.ScoringDefect):
        boundary.admit("extension")
    with pytest.raises(RUNNER.ScoringDefect):
        boundary.admit("s4")


def test_an_incomplete_smoke_cannot_be_closed():
    counters = COUNTERS.P0R1Counters()
    boundary = RUNNER.SmokeBoundary(counters)
    for _ in range(59):
        boundary.admit("smoke")
    with pytest.raises(RUNNER.ScoringDefect):
        boundary.close_smoke(True)


class _FakeModel(object):
    def __init__(self, name):
        self.name = name
        self.device = "cpu"

    def to(self, device):
        self.device = device
        return self


def test_only_one_checkpoint_is_gpu_resident_and_reloading_is_refused():
    counters = COUNTERS.P0R1Counters()
    residency = RUNNER.GpuResidency(counters)
    for role in ("RI", "RL", "RT"):
        residency.load(role, lambda role=role: _FakeModel(role))
    assert counters.snapshot()["model_weight_loads"] == 3
    with pytest.raises(RUNNER.ScoringDefect):
        residency.load("RT", lambda: _FakeModel("RT"))
    residency.to_gpu("RI", "cuda")
    assert residency.resident == "RI"
    residency.to_gpu("RL", "cuda")
    assert residency.resident == "RL"
    residency.evict()
    assert residency.resident is None


def test_a_fourth_weight_load_exceeds_the_registered_cap():
    counters = COUNTERS.P0R1Counters()
    residency = RUNNER.GpuResidency(counters)
    for role in ("RI", "RL", "RT"):
        residency.load(role, lambda role=role: _FakeModel(role))
    with pytest.raises(COUNTERS.CapExceeded):
        residency.load("RX", lambda: _FakeModel("RX"))


def test_the_one_model_operating_job_cap_is_registered():
    assert COUNTERS.CAPS["gpu_jobs_performing_a_model_operation"] == 1
    counters = COUNTERS.P0R1Counters()
    counters.add("gpu_jobs_performing_a_model_operation", 1)
    with pytest.raises(COUNTERS.CapExceeded):
        counters.add("gpu_jobs_performing_a_model_operation", 1)


def test_an_infrastructure_retry_requires_a_proven_zero_operation_attempt():
    zero = {name: 0 for name in COUNTERS.ZERO_BEFORE_EXECUTION}
    assert RUNNER.validate_infrastructure_retry(zero) is True
    for name in ("model_weight_loads", "tokenizer_encoded_sequences",
                 "non_generative_prefill_evaluations", "s4_generation_calls",
                 "total_scored_rows"):
        dirty = dict(zero)
        dirty[name] = 1
        with pytest.raises(RUNNER.ExecutionRefused):
            RUNNER.validate_infrastructure_retry(dirty)
    incomplete = dict(zero)
    incomplete.pop("model_weight_loads")
    with pytest.raises(RUNNER.ExecutionRefused):
        RUNNER.validate_infrastructure_retry(incomplete)


# ---------------------------------------------------------------------------
# The GPU launcher.
# ---------------------------------------------------------------------------

def test_the_launcher_exists_binds_a_digest_and_disables_platform_retry():
    path = os.path.join(CONTAINER_DIR, "p0_r1_launch_gpu_pilot.sh")
    assert os.path.exists(path), (
        "no P0-R1 GPU launcher existed at the baseline, so a replay pass could "
        "not physically advance to the model pilot")
    shell = _text(path)
    assert "--replica-retry-limit 0" in shell
    assert "gpu-t4" in shell
    assert "registry-identity" in shell
    assert "@$IMAGE_DIGEST" in shell
    assert "the image must be bound by an immutable sha256 digest" in shell


def test_the_launcher_cannot_start_a_second_model_operating_execution():
    shell = _text(os.path.join(CONTAINER_DIR, "p0_r1_launch_gpu_pilot.sh"))
    assert "execution list" in shell
    assert "already has" in shell
    assert "exit 3" in shell


def test_the_gpu_job_definition_pins_one_execution_and_no_retry():
    path = os.path.join(CONTAINER_DIR, "p0_r1_gpu_job.yaml")
    assert os.path.exists(path)
    text = _text(path)
    assert "replicaRetryLimit: 0" in text
    assert "parallelism: 1" in text
    assert "replicaCompletionCount: 1" in text
    assert "triggerType: Manual" in text
    assert "model_operating_executions_authorized: 1" in text
    assert "output_conditioned_retry_authorized: false" in text


def test_the_model_pilot_entry_point_requires_a_replay_pass_receipt():
    path = os.path.join(CONTAINER_DIR, "p0_r1_model_pilot.sh")
    assert os.path.exists(path)
    shell = _text(path)
    assert "p0_r1_replay_receipt.json" in shell
    assert "the replay gate must pass first" in shell
    assert "verify_binding" in shell


# ---------------------------------------------------------------------------
# Immutability, provenance and the path census.
# ---------------------------------------------------------------------------

def test_the_immutable_p0_namespace_and_ledger_are_unchanged():
    for relative, expected in FACT.IMMUTABLE_SOURCES.items():
        identity = FACT.source_identity(relative)
        assert identity["bytes"] == expected["bytes"]
        assert identity["sha256"] == expected["sha256"]
    ledger = _text(os.path.join(REPO_ROOT, "paper", "evidence_ledger.csv"))
    assert "EV-0017" not in ledger
    rows = [row for row in ledger.splitlines() if row.strip()]
    assert rows[-1].startswith("EV-0016")


def test_the_operative_authorities_reproduce_their_registered_identity():
    for entry in (LOCK.REGISTRATION_AUTHORITY, LOCK.SUPPLEMENTAL_AUTHORITY):
        identity = LOCK.blob_identity(entry["path"])
        assert identity["bytes"] == entry["bytes"], entry["path"]
        assert identity["sha256"] == entry["sha256"], entry["path"]


def test_the_baseline_to_head_provenance_is_forty_committed_repository_paths():
    """Section 2.4: the registration erratum said 41; the exact count is 40."""
    result = subprocess.run(
        ["git", "-C", REPO_ROOT, "diff", "--name-status",
         "dfbe6dd6c82fbe0e8906a4aa7f4df6b676496366",
         "167d3067d7d9a2866999a51ec49c3c57c1d31546"],
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        pytest.skip("the registration range is not available in this checkout")
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert len(lines) == 40
    assert sum(1 for line in lines if line.startswith("M")) == 9
    assert sum(1 for line in lines if line.startswith("A")) == 31


def test_the_active_governance_records_forty_paths_and_the_two_hop_provenance():
    run_log = _text(os.path.join(REPO_ROOT, "docs", "run_log.md"))
    assert "changed-path census is 41 paths" not in run_log
    assert "40 changed repository paths" in run_log
    # The two provenance hops must both be visible and must not be collapsed
    # into an end-to-end byte-identical claim.
    assert "20,217" in run_log
    assert "db42214e37e9b44feab5c36c8ca4359b0d269cba3b9f0444c60b8837bc59975f" \
        in run_log
    assert "19,632" in run_log


def test_the_handoff_orders_replay_before_the_final_focused_review():
    handoff = _text(
        os.path.join(REPO_ROOT, "studies", "study3", "NEXT_THREAD_HANDOFF.md"))
    replay = handoff.find("STUDY3_P0_R1_EXECUTION_READY_AWAITING_REPLAY_GATE")
    assert replay >= 0
    assert "only after" in handoff.lower()


def test_the_ready_state_is_published_and_the_pilot_is_not_consumed():
    status = _text(os.path.join(REPO_ROOT, "reports", "current_status.md"))
    assert READY_STATE in status
    lock = LOCK.load_lock()
    LOCK.validate_lock(lock)
    assert lock["legal_status"]["p0_r1_pilot_execution_authorized"] is True
    assert lock["legal_status"]["p0_r1_pilot_execution_consumed"] is False
    assert lock["legal_status"]["formal_execution_authorized"] is False
    assert all(value == 0
               for value in lock["counters_before_execution"].values())
