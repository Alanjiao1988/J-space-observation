#!/usr/bin/env python3
"""Study 3 P0-R2 generation-2 in-VNet prefix proof and its single validator.

Authority:
``studies/study3/prompts/study3_p0_r2_generation2_successor_and_conditional_execution_authority.md``
sections 4, 6.2 and 6.3.

Generation 1 died on one fact. An ACR Tasks agent has neither the registered
managed identity nor a route into ``cae-jspace-observation-sea-vnet2``, so the
live container could not list a private Storage account. Its prefix preflight
refused, correctly, with ``P0_R2_PREFIX_PREFLIGHT_REFUSED=1``: a Bad Gateway is
an ambiguity and an ambiguity is never an absence.

Generation 2 does not weaken that proof, it relocates it:

1. a CPU-only Container Apps execution inside the registered environment, using
   the registered user-assigned identity, performs the exact prefix listing and
   emits an **observation** between two unambiguous markers;
2. the host correlates that observation with the Azure control plane and with
   the captured execution log, producing a **receipt**;
3. the host embeds the exact receipt bytes and their SHA-256 in the two-file ACR
   context admission;
4. the ACR container validates the bound receipt with the function below and
   prints ``P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1``.

There is exactly one validator, :func:`validate_receipt`, and both the canary
and the live path call it with the same arguments. The mode argument selects a
marker, never a rule: generation 1's real defect was that its canary branch and
its live branch did different work, so the canary could not rehearse the step
that stopped the live run.

There is deliberately no ``--allow-path``, no ``--skip-proof``, no ``--force``,
no caller-supplied truth value and no fallback that converts an error into an
absence.

Model-free. Constructs no tokenizer, downloads no checkpoint, loads no weight,
allocates no GPU, and writes no object into the results container.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys


P0_R2_DIR = Path(__file__).resolve().parent
if str(P0_R2_DIR) not in sys.path:
    sys.path.insert(0, str(P0_R2_DIR))

import p0_r2_blob_transport as BLOB  # noqa: E402


SCHEMA_VERSION = "study3-p0-r2-prefix-proof-g2"
OBSERVATION_SCHEMA_VERSION = "study3-p0-r2-prefix-observation-g2"
STAGE = "STUDY3-P0-R2"
GENERATION = 2

#: Generation-2 storage namespace. Disjoint from generation 1's
#: ``study3/p0_r2/g1`` by construction, and asserted in the tests.
PREFIX_ROOT = "study3/p0_r2/g2"
ATTEMPT_ID_PREFIX = "p0r2-g2-"
LIVE_ATTEMPT_PREFIX = "p0r2-g2-live-"
PILOT_ATTEMPT_PREFIX = "p0r2-g2-pilot-"
CANARY_ATTEMPT_PREFIX = "p0r2-g2-canary-"

#: The generation-1 namespace, kept here only so the disjointness is checked
#: rather than assumed.
GENERATION1_PREFIX_ROOT = "study3/p0_r2/g1"
GENERATION1_ATTEMPT_ID_PREFIX = "p0r2-g1-"

SUBSCRIPTION = "943bacdf-8b6e-4e3a-8126-a149f623d32e"
RESOURCE_GROUP = "rg-jspace-observation-sea"
ACCOUNT = "stjspacefiles0709085305"
CONTAINER = "jspace-results"
ACA_ENVIRONMENT = "cae-jspace-observation-sea-vnet2"
MANAGED_IDENTITY = "id-jspace-aca-acrpull-sea"
IDENTITY_CLIENT_ID = "479d9229-632e-4490-ad92-854a34dfddf8"

PREFIX_JOB = "job-jspace-s3-p0r2-prefix-g2"

#: The host must start the Azure CLI live process within this window of the
#: in-VNet observation. Azure queue time afterwards is not the host's fact, so
#: the container checks identity and byte binding but never re-checks age.
MAX_HOST_OBSERVATION_AGE_SECONDS = 900

OBSERVATION_BEGIN = "P0_R2_G2_PREFIX_OBSERVATION_BEGIN"
OBSERVATION_END = "P0_R2_G2_PREFIX_OBSERVATION_END"
DEFERRED_MARKER = "P0_R2_PREFIX_PROOF_DEFERRED_TO_HOST=1"

#: The exact label under which the correlated receipt is embedded in the
#: two-file ACR context manifest.
CONTEXT_LABEL = "prefix_receipt"

_TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

VALID_MODES = ("canary", "live")


class PrefixProofDefect(Exception):
    """The generation-2 prefix could not be proved unused."""


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_bytes(document) -> bytes:
    """The one serialisation every hash in this generation is taken over."""
    return json.dumps(document, indent=2, sort_keys=True).encode("utf-8") + b"\n"


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value, field):
    if not isinstance(value, str) or not _TIMESTAMP.match(value):
        raise PrefixProofDefect(
            "%s is not an exact UTC timestamp: %r" % (field, value))
    return datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc)


def attempt_prefix(attempt_id: str) -> str:
    """The one unique, attempt-bound generation-2 prefix."""
    if not attempt_id or not isinstance(attempt_id, str):
        raise PrefixProofDefect("a prefix requires an attempt id")
    if not attempt_id.startswith(ATTEMPT_ID_PREFIX):
        raise PrefixProofDefect(
            "attempt id %r does not begin with the registered generation-2 "
            "prefix %r" % (attempt_id, ATTEMPT_ID_PREFIX))
    if attempt_id.startswith(GENERATION1_ATTEMPT_ID_PREFIX):
        raise PrefixProofDefect(
            "attempt id %r belongs to the closed generation 1" % attempt_id)
    if len(attempt_id) > 128:
        raise PrefixProofDefect("attempt id %r is too long" % attempt_id)
    for character in attempt_id:
        if not (character.isalnum() or character in "-_."):
            raise PrefixProofDefect(
                "attempt id %r is not a safe prefix component" % attempt_id)
    if ".." in attempt_id:
        raise PrefixProofDefect("attempt id %r traverses" % attempt_id)
    return "%s/%s/" % (PREFIX_ROOT, attempt_id)


def _network_observation(client):
    """Best-effort public-network facts. Absence is recorded, never inferred."""
    observed = {
        "public_network_access": None,
        "default_action": None,
        "observed": False,
    }
    try:
        properties = client.get_account_information()
    except Exception:  # noqa: BLE001 - an unavailable fact stays unavailable
        return observed
    if isinstance(properties, dict):
        observed["public_network_access"] = properties.get(
            "public_network_access")
        observed["default_action"] = properties.get("default_action")
        observed["observed"] = True
    return observed


def observe(attempt_id: str, *, backend=None, environ=None) -> dict:
    """List the exact complete prefix from inside the VNet.

    Every failure is an ambiguity and refuses. Nothing here writes an object,
    and nothing here accepts a caller-supplied outcome.
    """
    environ = os.environ if environ is None else environ
    prefix = attempt_prefix(attempt_id)
    started = utc_now()

    sink = backend if backend is not None else BLOB.AzureManagedIdentityBackend()
    if getattr(sink, "credential_kind", None) != "managed-identity":
        raise PrefixProofDefect(
            "the generation-2 prefix proof accepts a managed-identity backend "
            "only; %r is not one" % getattr(sink, "credential_kind", None))

    try:
        names = sorted(sink.list_names(prefix))
    except Exception as exc:  # noqa: BLE001 - any failure is an ambiguity
        raise PrefixProofDefect(
            "the private listing failed (%s); a query error is never an "
            "absence" % exc)
    observed_at = utc_now()

    network = _network_observation(sink)
    completed = utc_now()

    return {
        "schema_version": OBSERVATION_SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "attempt_id": attempt_id,
        "prefix": prefix,
        "prefix_root": PREFIX_ROOT,
        "subscription": SUBSCRIPTION,
        "resource_group": RESOURCE_GROUP,
        "account": ACCOUNT,
        "container": CONTAINER,
        "container_apps_environment": ACA_ENVIRONMENT,
        "managed_identity": MANAGED_IDENTITY,
        "identity_client_id": IDENTITY_CLIENT_ID,
        "prefix_proof_job": environ.get("P0_R2_G2_PREFIX_JOB") or PREFIX_JOB,
        "execution_name": environ.get("CONTAINER_APP_JOB_EXECUTION_NAME")
        or environ.get("P0_R2_G2_EXECUTION_NAME"),
        "replica_name": environ.get("CONTAINER_APP_REPLICA_NAME"),
        "image_digest": environ.get("P0_R2_IMAGE_DIGEST"),
        "started_at_utc": started,
        "observed_at_utc": observed_at,
        "completed_at_utc": completed,
        "listing_succeeded": True,
        "listing_error": None,
        "object_count": len(names),
        "objects": names[:16],
        "wrote_any_object": False,
        "outcome": "PROVED_UNUSED" if not names else "PROVED_IN_USE",
        "network": network,
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "checkpoint_loads": 0,
        "model_weight_loads": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "gpu_allocations": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }


def require_unused(observation: dict) -> dict:
    if not isinstance(observation, dict):
        raise PrefixProofDefect("the observation is not a document")
    if observation.get("listing_succeeded") is not True:
        raise PrefixProofDefect(
            "the listing did not succeed; a query error is never an absence")
    if observation.get("outcome") != "PROVED_UNUSED":
        raise PrefixProofDefect(
            "the prefix is not proved unused: %r" % observation.get("outcome"))
    if observation.get("object_count") != 0:
        raise PrefixProofDefect(
            "the prefix already carries %r object(s)"
            % observation.get("object_count"))
    if observation.get("wrote_any_object") is not False:
        raise PrefixProofDefect("the probe claims to have written an object")
    return observation


def extract_observation(log_text: str) -> dict:
    """Recover the observation from the captured execution log alone."""
    if not isinstance(log_text, str):
        raise PrefixProofDefect("the captured log is not text")
    begins = [index for index, line in enumerate(log_text.splitlines())
              if line.strip() == OBSERVATION_BEGIN]
    ends = [index for index, line in enumerate(log_text.splitlines())
            if line.strip() == OBSERVATION_END]
    if len(begins) != 1 or len(ends) != 1:
        raise PrefixProofDefect(
            "the captured log carries %d begin and %d end markers; exactly one "
            "of each is required" % (len(begins), len(ends)))
    if ends[0] <= begins[0]:
        raise PrefixProofDefect("the observation markers are out of order")
    lines = log_text.splitlines()[begins[0] + 1:ends[0]]
    encoded = "".join(line.strip() for line in lines)
    try:
        payload = base64.b64decode(encoded, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise PrefixProofDefect(
            "the observation block is not valid base64: %s" % exc)
    try:
        document = json.loads(payload.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise PrefixProofDefect(
            "the observation block is not a JSON document: %s" % exc)
    if not isinstance(document, dict):
        raise PrefixProofDefect("the observation block is not a document")
    return document


def correlate(*, observation: dict, execution: dict, stdout: bytes,
              stderr: bytes, log_text=None) -> dict:
    """Bind an in-VNet observation to its Azure execution and captured log.

    The observation is re-derived from the captured log rather than trusted, so
    a receipt cannot be built from a document the log does not contain.
    """
    require_unused(observation)

    if log_text is not None:
        recovered = extract_observation(log_text)
        if canonical_bytes(recovered) != canonical_bytes(observation):
            raise PrefixProofDefect(
                "the supplied observation is not the one the captured log "
                "carries")

    if not isinstance(execution, dict):
        raise PrefixProofDefect("the execution record is not a document")
    for field in ("job", "name", "status", "start_time"):
        if not execution.get(field):
            raise PrefixProofDefect(
                "the execution record is missing %r" % field)
    if execution.get("status") != "Succeeded":
        raise PrefixProofDefect(
            "the prefix-proof execution is %r; only a succeeded execution can "
            "correlate a receipt" % execution.get("status"))
    if execution.get("job") != observation.get("prefix_proof_job"):
        raise PrefixProofDefect(
            "the execution job %r is not the job the observation names (%r)"
            % (execution.get("job"), observation.get("prefix_proof_job")))
    if observation.get("execution_name") and \
            observation.get("execution_name") != execution.get("name"):
        raise PrefixProofDefect(
            "the observation names execution %r but the control plane names %r"
            % (observation.get("execution_name"), execution.get("name")))

    receipt = {
        "schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generation": GENERATION,
        "attempt_id": observation["attempt_id"],
        "prefix": observation["prefix"],
        "prefix_root": PREFIX_ROOT,
        "subscription": SUBSCRIPTION,
        "resource_group": RESOURCE_GROUP,
        "account": ACCOUNT,
        "container": CONTAINER,
        "container_apps_environment": ACA_ENVIRONMENT,
        "prefix_proof_job": observation["prefix_proof_job"],
        "execution": {
            "job": execution["job"],
            "name": execution["name"],
            "status": execution["status"],
            "start_time": execution["start_time"],
            "end_time": execution.get("end_time"),
        },
        "image_digest": observation.get("image_digest"),
        "started_at_utc": observation["started_at_utc"],
        "observed_at_utc": observation["observed_at_utc"],
        "completed_at_utc": observation["completed_at_utc"],
        "listing_succeeded": True,
        "object_count": 0,
        "objects": [],
        "wrote_any_object": False,
        "outcome": "PROVED_UNUSED",
        "network": observation.get("network"),
        "log": {
            "stdout_bytes": len(stdout),
            "stdout_sha256": _sha256(stdout),
            "stderr_bytes": len(stderr),
            "stderr_sha256": _sha256(stderr),
        },
        "observation_sha256": _sha256(canonical_bytes(observation)),
        "correlated_at_utc": utc_now(),
        "tokenizer_constructions": 0,
        "tokenizer_encodes": 0,
        "checkpoint_downloads": 0,
        "checkpoint_loads": 0,
        "model_weight_loads": 0,
        "prefills": 0,
        "generations": 0,
        "scored_rows": 0,
        "gpu_allocations": 0,
        "gpu_operations": 0,
        "model_operations_performed": 0,
    }
    return receipt


def validate_receipt(receipt, *, attempt_id, mode, expected_sha256=None,
                     receipt_bytes=None, now=None,
                     require_host_freshness=False,
                     max_age_seconds=MAX_HOST_OBSERVATION_AGE_SECONDS) -> dict:
    """The one prefix-receipt validator. Canary and live both call this.

    ``mode`` selects the marker a caller may print. It changes no rule here:
    every check below runs identically for ``canary`` and ``live``.
    """
    if mode not in VALID_MODES:
        raise PrefixProofDefect(
            "mode %r is not one of %s" % (mode, ", ".join(VALID_MODES)))
    if not isinstance(receipt, dict):
        raise PrefixProofDefect("the prefix receipt is missing or malformed")
    if receipt.get("schema_version") != SCHEMA_VERSION:
        raise PrefixProofDefect(
            "the prefix receipt declares schema %r; %r is required"
            % (receipt.get("schema_version"), SCHEMA_VERSION))
    if receipt.get("stage") != STAGE:
        raise PrefixProofDefect(
            "the prefix receipt is for stage %r" % receipt.get("stage"))
    if receipt.get("generation") != GENERATION:
        raise PrefixProofDefect(
            "the prefix receipt is for generation %r; this is generation %d"
            % (receipt.get("generation"), GENERATION))
    if not attempt_id:
        raise PrefixProofDefect("an attempt id is required to validate")
    if receipt.get("attempt_id") != attempt_id:
        raise PrefixProofDefect(
            "the prefix receipt is for attempt %r, not %r"
            % (receipt.get("attempt_id"), attempt_id))

    expected_prefix = attempt_prefix(attempt_id)
    if receipt.get("prefix") != expected_prefix:
        raise PrefixProofDefect(
            "the prefix receipt names prefix %r; %r is the exact complete "
            "prefix for this attempt"
            % (receipt.get("prefix"), expected_prefix))
    if receipt.get("prefix_root") != PREFIX_ROOT:
        raise PrefixProofDefect(
            "the prefix receipt names root %r" % receipt.get("prefix_root"))

    for field, expected in (
            ("subscription", SUBSCRIPTION),
            ("resource_group", RESOURCE_GROUP),
            ("account", ACCOUNT),
            ("container", CONTAINER),
            ("container_apps_environment", ACA_ENVIRONMENT)):
        if receipt.get(field) != expected:
            raise PrefixProofDefect(
                "the prefix receipt names %s %r; %r is registered"
                % (field, receipt.get(field), expected))

    if receipt.get("prefix_proof_job") != PREFIX_JOB:
        raise PrefixProofDefect(
            "the prefix receipt names job %r; %r is the registered "
            "generation-2 prefix-proof job"
            % (receipt.get("prefix_proof_job"), PREFIX_JOB))

    execution = receipt.get("execution")
    if not isinstance(execution, dict):
        raise PrefixProofDefect(
            "the prefix receipt carries no execution correlation")
    if execution.get("job") != PREFIX_JOB:
        raise PrefixProofDefect(
            "the correlated execution belongs to job %r" % execution.get("job"))
    if not execution.get("name"):
        raise PrefixProofDefect("the correlated execution has no name")
    if execution.get("status") != "Succeeded":
        raise PrefixProofDefect(
            "the correlated execution is %r, not Succeeded"
            % execution.get("status"))

    digest = receipt.get("image_digest")
    if not isinstance(digest, str) or not _DIGEST.match(digest):
        raise PrefixProofDefect(
            "the prefix receipt does not name a digest-pinned proof image: %r"
            % digest)

    if receipt.get("listing_succeeded") is not True:
        raise PrefixProofDefect(
            "the prefix receipt does not report a successful listing")
    if receipt.get("outcome") != "PROVED_UNUSED":
        raise PrefixProofDefect(
            "the prefix receipt reports %r" % receipt.get("outcome"))
    if receipt.get("object_count") != 0:
        raise PrefixProofDefect(
            "the prefix receipt reports %r object(s)"
            % receipt.get("object_count"))
    if receipt.get("objects"):
        raise PrefixProofDefect(
            "the prefix receipt enumerates objects under a prefix it calls "
            "unused")
    if receipt.get("wrote_any_object") is not False:
        raise PrefixProofDefect("the prefix receipt admits writing an object")

    log = receipt.get("log")
    if not isinstance(log, dict):
        raise PrefixProofDefect("the prefix receipt carries no log binding")
    for field in ("stdout_bytes", "stderr_bytes"):
        if not isinstance(log.get(field), int) or log.get(field) < 0:
            raise PrefixProofDefect(
                "the prefix receipt log field %r is not a byte length" % field)
    for field in ("stdout_sha256", "stderr_sha256"):
        value = log.get(field)
        if not isinstance(value, str) or not _SHA256.match(value):
            raise PrefixProofDefect(
                "the prefix receipt log field %r is not a SHA-256" % field)
    if log.get("stdout_bytes") == 0:
        raise PrefixProofDefect(
            "the prefix receipt binds an empty stdout; an execution that "
            "printed nothing cannot have carried an observation")

    observation_hash = receipt.get("observation_sha256")
    if not isinstance(observation_hash, str) \
            or not _SHA256.match(observation_hash):
        raise PrefixProofDefect(
            "the prefix receipt does not bind its observation by SHA-256")

    for field in ("tokenizer_constructions", "tokenizer_encodes",
                  "checkpoint_downloads", "checkpoint_loads",
                  "model_weight_loads", "prefills", "generations",
                  "scored_rows", "gpu_allocations", "gpu_operations",
                  "model_operations_performed"):
        if receipt.get(field) != 0:
            raise PrefixProofDefect(
                "the prefix receipt reports a nonzero %s: %r"
                % (field, receipt.get(field)))

    started = _parse_timestamp(receipt.get("started_at_utc"), "started_at_utc")
    observed = _parse_timestamp(receipt.get("observed_at_utc"),
                                "observed_at_utc")
    completed = _parse_timestamp(receipt.get("completed_at_utc"),
                                 "completed_at_utc")
    if not (started <= observed <= completed):
        raise PrefixProofDefect(
            "the prefix receipt timestamps are not ordered")

    if expected_sha256 is not None:
        if not isinstance(expected_sha256, str) \
                or not _SHA256.match(expected_sha256):
            raise PrefixProofDefect(
                "the expected receipt SHA-256 is malformed: %r"
                % expected_sha256)
        actual = _sha256(receipt_bytes if receipt_bytes is not None
                         else canonical_bytes(receipt))
        if actual != expected_sha256:
            raise PrefixProofDefect(
                "the bound receipt SHA-256 %s does not equal the admitted %s"
                % (actual, expected_sha256))

    age_seconds = None
    if require_host_freshness:
        reference = _parse_timestamp(now, "now") if isinstance(now, str) \
            else (now or datetime.datetime.now(datetime.timezone.utc))
        age_seconds = int((reference - observed).total_seconds())
        if age_seconds < 0:
            raise PrefixProofDefect(
                "the prefix observation is dated in the future")
        if age_seconds > max_age_seconds:
            raise PrefixProofDefect(
                "the prefix observation is %d seconds old; the host may not "
                "start the live process more than %d seconds after it"
                % (age_seconds, max_age_seconds))

    return {
        "schema_version": "study3-p0-r2-prefix-validation-g2",
        "stage": STAGE,
        "generation": GENERATION,
        "mode": mode,
        "validator": "p0_r2_prefix_proof_g2.validate_receipt",
        "shared_by_canary_and_live": True,
        "attempt_id": attempt_id,
        "prefix": expected_prefix,
        "receipt_sha256": _sha256(receipt_bytes if receipt_bytes is not None
                                  else canonical_bytes(receipt)),
        "host_freshness_checked": bool(require_host_freshness),
        "observation_age_seconds": age_seconds,
        "outcome": "PREFIX_RECEIPT_VALID",
        "model_operations_performed": 0,
    }


def validate_bound_receipt(manifest: dict, *, attempt_id, mode) -> dict:
    """Validate the receipt a two-file ACR context admitted, by its bytes.

    This is the only path the container uses. It re-derives the receipt from the
    embedded bytes and calls the single validator above, so the container can
    neither read a receipt the manifest did not admit nor accept one whose bytes
    disagree with the admitted SHA-256.
    """
    if not isinstance(manifest, dict):
        raise PrefixProofDefect("the context manifest is not a document")
    entries = [entry for entry
               in (manifest.get("embedded_governance_objects") or [])
               if isinstance(entry, dict)
               and entry.get("label") == CONTEXT_LABEL]
    if len(entries) != 1:
        raise PrefixProofDefect(
            "the context embeds %d %r objects; exactly one is required"
            % (len(entries), CONTEXT_LABEL))
    entry = entries[0]
    try:
        payload = base64.b64decode(entry.get("payload") or "", validate=True)
    except Exception as exc:  # noqa: BLE001
        raise PrefixProofDefect(
            "the embedded prefix receipt is not valid base64: %s" % exc)
    if len(payload) != entry.get("bytes"):
        raise PrefixProofDefect(
            "the embedded prefix receipt length disagrees with its admission")
    declared = entry.get("sha256")
    actual = _sha256(payload)
    if actual != declared:
        raise PrefixProofDefect(
            "the embedded prefix receipt SHA-256 %s disagrees with the "
            "admitted %s" % (actual, declared))
    try:
        receipt = json.loads(payload.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise PrefixProofDefect(
            "the embedded prefix receipt is not a JSON document: %s" % exc)
    return validate_receipt(receipt, attempt_id=attempt_id, mode=mode,
                            expected_sha256=declared, receipt_bytes=payload,
                            require_host_freshness=False)


def implementation_identity() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "module": "p0_r2_prefix_proof_g2.py",
        "stage": STAGE,
        "generation": GENERATION,
        "prefix_root": PREFIX_ROOT,
        "attempt_id_prefix": ATTEMPT_ID_PREFIX,
        "prefix_proof_job": PREFIX_JOB,
        "container_apps_environment": ACA_ENVIRONMENT,
        "validator": "validate_receipt",
        "shared_by_canary_and_live": True,
        "separate_canary_and_live_validators": False,
        "query_error_is_absence": False,
        "writes_objects": False,
        "accepts_allow_path": False,
        "accepts_skip_proof": False,
        "accepts_force": False,
        "accepts_caller_supplied_outcome": False,
        "max_host_observation_age_seconds": MAX_HOST_OBSERVATION_AGE_SECONDS,
        # The literal marker is deliberately not reproduced here. It must occur
        # exactly once in an execution log, and an identity dump that quoted it
        # would make a truthful log look like a repeated claim.
        "defers_prefix_proof_to_host": True,
        "model_operations_performed": 0,
    }


def _read_json(path, what):
    try:
        payload = Path(path).read_bytes()
    except OSError as exc:
        raise PrefixProofDefect("%s is unreadable: %s" % (what, exc))
    try:
        return json.loads(payload.decode("utf-8")), payload
    except Exception as exc:  # noqa: BLE001
        raise PrefixProofDefect("%s is not a JSON document: %s" % (what, exc))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--identity", action="store_true")
    mode.add_argument("--observe", metavar="ATTEMPT")
    mode.add_argument("--correlate", action="store_true")
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--validate-bound", action="store_true")
    parser.add_argument("--attempt")
    parser.add_argument("--receipt")
    parser.add_argument("--observation")
    parser.add_argument("--execution")
    parser.add_argument("--raw-log")
    parser.add_argument("--stderr-file")
    parser.add_argument("--context-manifest")
    parser.add_argument("--expect-sha256")
    parser.add_argument("--replay-mode", choices=list(VALID_MODES))
    parser.add_argument("--require-host-freshness", action="store_true")
    parser.add_argument("--out")
    args = parser.parse_args(argv)

    if args.identity:
        print(json.dumps(implementation_identity(), indent=2, sort_keys=True))
        return 0

    try:
        if args.observe:
            observation = require_unused(observe(args.observe))
            payload = canonical_bytes(observation)
            if args.out:
                Path(args.out).write_bytes(payload)
            encoded = base64.b64encode(payload).decode("ascii")
            print(OBSERVATION_BEGIN)
            for index in range(0, len(encoded), 76):
                print(encoded[index:index + 76])
            print(OBSERVATION_END)
            print("P0_R2_G2_PREFIX_OBSERVATION_SHA256=%s" % _sha256(payload))
            print("P0_R2_G2_PREFIX_PROVED_UNUSED=%s" % observation["prefix"])
            print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
            return 0

        if args.correlate:
            raw = Path(args.raw_log).read_bytes() if args.raw_log else b""
            err = Path(args.stderr_file).read_bytes() \
                if args.stderr_file else b""
            observation = extract_observation(raw.decode("utf-8", "replace"))
            execution, _ = _read_json(args.execution, "the execution record")
            receipt = correlate(observation=observation, execution=execution,
                                stdout=raw, stderr=err,
                                log_text=raw.decode("utf-8", "replace"))
            payload = canonical_bytes(receipt)
            if args.out:
                Path(args.out).write_bytes(payload)
            print(payload.decode("utf-8"), end="")
            print("P0_R2_G2_PREFIX_RECEIPT_SHA256=%s" % _sha256(payload))
            print("P0_R2_G2_PREFIX_RECEIPT_CORRELATED=1")
            return 0

        if args.validate:
            receipt, payload = _read_json(args.receipt, "the prefix receipt")
            report = validate_receipt(
                receipt, attempt_id=args.attempt,
                mode=args.replay_mode or "canary",
                expected_sha256=args.expect_sha256, receipt_bytes=payload,
                require_host_freshness=args.require_host_freshness)
        else:
            manifest, _ = _read_json(args.context_manifest,
                                     "the context manifest")
            report = validate_bound_receipt(
                manifest, attempt_id=args.attempt,
                mode=args.replay_mode or "canary")
    except PrefixProofDefect as exc:
        print("P0_R2_G2_PREFIX_PROOF_REFUSED=1 %s" % exc, file=sys.stderr)
        return 3

    payload = canonical_bytes(report)
    if args.out:
        Path(args.out).write_bytes(payload)
    print(payload.decode("utf-8"), end="")
    print(DEFERRED_MARKER)
    print("P0_R2_MODEL_OPERATIONS_PERFORMED=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
