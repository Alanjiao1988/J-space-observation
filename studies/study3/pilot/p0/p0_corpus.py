"""Deterministic, seed-free frozen corpus for the Study 3-P0 feasibility pilot.

Authority
---------
``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md`` section 5.

P0 uses no random seed and creates no development, confirmation or P3-Q bank.
Every value below is derived by a closed-form registered rule from the pilot
base-item index, so an independent implementation recomputes the whole corpus
without any stored state. The P0 test module recomputes it and compares bytes.

What is registered here
-----------------------
Three semantic base-tuple classes, one each:

* ``K2-none-0``               -- K2 identity/copy, composition depth 0;
* ``K3-affine_mod10-1``       -- K3 affine_mod10, composition depth 1;
* ``K3-permutation_chain-1``  -- K3 permutation_chain, composition depth 1.

Contrast allocation, exactly as the authority fixes it:

* ``S1``: K5-P1, K5-P2, K5-P3, K5-S1, K5-S2, K5-S3, K5-A1, K6-SEP, K6-INSTR;
* ``S2``: K6-INSTR only;
* ``S3``: K6-INSTR only, byte-identical prompts to S2, rescored on CPU;
* ``S4``: the K2 tuple only, K6-SEP and K6-INSTR, distinct base identities.

``K6-SEP`` is never instantiated for S2 or S3. ``not_applicable`` is structural
absence: not a pass, not a zero, not a duplicate and not a denominator row.

Every base-item identity lives in the permanently excluded namespace
``study3-p0-only/<tuple-class>/<contrast-id>`` where ``<contrast-id>`` is the
contrast *cell* identifier ``<profile>-<contrast>``. The cell qualifier is what
makes the identity distinct per contrast cell, which the authority requires; no
identity is shared across two contrast cells.

Standard library only, by design.
"""

import hashlib
import json
import os

from p0_renderer import (
    P0Renderer,
    alphabet_name,
    labels_for_state,
    load_protocol,
    load_registry,
)

P0_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(P0_DIR, "corpus")
CORPUS_PATH = os.path.join(CORPUS_DIR, "p0_corpus.json")
MANIFEST_PATH = os.path.join(CORPUS_DIR, "p0_corpus_manifest.json")
CENSUS_PATH = os.path.join(CORPUS_DIR, "p0_corpus_census.md")

NAMESPACE = "study3-p0-only"

# The three registered pilot tuple classes, in registered order.
TUPLE_CLASSES = (
    {
        "tuple_class_id": "K2-none-0",
        "branch_id": "K2/none/0",
        "task_stratum": "K2",
        "operation_family": None,
        "composition_depth": 0,
        "semantics": "identity/copy of the stated value",
    },
    {
        "tuple_class_id": "K3-affine_mod10-1",
        "branch_id": "K3/affine_mod10/1",
        "task_stratum": "K3",
        "operation_family": "affine_mod10",
        "composition_depth": 1,
        "semantics": "one affine step over the mod-10 residues",
    },
    {
        "tuple_class_id": "K3-permutation_chain-1",
        "branch_id": "K3/permutation_chain/1",
        "task_stratum": "K3",
        "operation_family": "permutation_chain",
        "composition_depth": 1,
        "semantics": "one permutation application over the mod-10 residues",
    },
)

K5_CONTRASTS = ("K5-P1", "K5-P2", "K5-P3", "K5-S1", "K5-S2", "K5-S3", "K5-A1")
K6_CONTRASTS = ("K6-SEP", "K6-INSTR")

# Registered per-profile allocation. S3 mirrors S2 by construction.
PROFILE_ALLOCATION = (
    ("S1", K5_CONTRASTS + K6_CONTRASTS, None),
    ("S2", ("K6-INSTR",), None),
    ("S3", ("K6-INSTR",), None),
    ("S4", K6_CONTRASTS, "K2-none-0"),
)

# The registered operation parameters of each tuple class. They are explicit
# committed bytes; the test recomputes the ground truth from them independently.
TUPLE_PARAMETERS = {
    "K2-none-0": {"x": "3"},
    "K3-affine_mod10-1": {"x": "4", "a1": "3", "b1": "1"},
    "K3-permutation_chain-1": {
        "x": "5",
        "p1": "[1 2 3 4 5 6 7 8 9 0]",
    },
}

# The registered permutation surface grammar: a bracketed, single-space-separated
# one-line image vector of 0..9 in ascending argument order.
PERMUTATION_IMAGE = {
    "K3-permutation_chain-1": [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
}


class CorpusDefect(Exception):
    """Raised when a registered validity predicate fails. P0 stops; it never repairs."""


# ---------------------------------------------------------------------------
# Ground truth. Computed by the harness, never parsed from generated text.
# ---------------------------------------------------------------------------

def ground_truth(tuple_class_id):
    """Return the registered mod-10 ground-truth surface for a tuple class."""
    params = TUPLE_PARAMETERS[tuple_class_id]
    x = int(params["x"])
    if tuple_class_id == "K2-none-0":
        value = x
    elif tuple_class_id == "K3-affine_mod10-1":
        value = (int(params["a1"]) * x + int(params["b1"])) % 10
    elif tuple_class_id == "K3-permutation_chain-1":
        image = PERMUTATION_IMAGE[tuple_class_id]
        if sorted(image) != list(range(10)):
            raise CorpusDefect("the registered permutation is not a permutation")
        if image == list(range(10)):
            raise CorpusDefect("the registered permutation is the identity")
        value = image[x]
    else:
        raise CorpusDefect("unregistered tuple class %r" % tuple_class_id)
    if not 0 <= value <= 9:
        raise CorpusDefect("ground truth outside the registered answer domain")
    return str(value)


def permutation_surface(tuple_class_id):
    """Render the registered permutation image vector in its registered grammar."""
    image = PERMUTATION_IMAGE[tuple_class_id]
    return "[" + " ".join(str(v) for v in image) + "]"


# ---------------------------------------------------------------------------
# Nuisance states and the registered K5 transformations.
# ---------------------------------------------------------------------------

def baseline_state(base_index):
    """Derive the registered baseline nuisance triple from a base-item index.

    The registered derivation is
    ``(k mod 4, (k div 4) mod 4, (k div 16) mod 2)``; the three factors cycle at
    different rates, so every one of the 32 registered nuisance-support states
    occurs exactly once in each complete block of 32 consecutive indices.
    """
    return (base_index % 4, (base_index // 4) % 4, (base_index // 16) % 2)


def variant_state(state, contrast):
    """Apply the one registered factor of ``contrast`` to a baseline triple."""
    position, symbol_index, alphabet_index = state
    if contrast in ("K5-P1", "K5-P2", "K5-P3"):
        offset = int(contrast[-1])
        return ((position + offset) % 4, symbol_index, alphabet_index)
    if contrast in ("K5-S1", "K5-S2", "K5-S3"):
        offset = int(contrast[-1])
        return (position, (symbol_index + offset) % 4, alphabet_index)
    if contrast == "K5-A1":
        return (position, symbol_index, 1 - alphabet_index)
    if contrast in K6_CONTRASTS:
        # A K6 contrast varies a rendering byte, never the nuisance state.
        return (position, symbol_index, alphabet_index)
    raise CorpusDefect("unregistered contrast %r" % contrast)


def renderings_for(contrast):
    """Return the registered (baseline, variant) rendering pair for a contrast."""
    if contrast == "K6-SEP":
        return ("R-base", "R-sep")
    if contrast == "K6-INSTR":
        return ("R-base", "R-instr")
    if contrast in K5_CONTRASTS:
        # K5 varies a nuisance factor; the rendering is held byte-identical.
        return ("R-base", "R-base")
    raise CorpusDefect("unregistered contrast %r" % contrast)


def distractor_triple(base_index, correct):
    """Return the registered ordered distractor triple for one base item.

    P0 draws no seed. The ordered triple is therefore a closed-form rotation of
    the nine mod-10 residues other than the correct answer: it is deterministic,
    distinct by construction and excludes the correct answer, which is exactly
    what the registered validity predicates require. It is a pilot-only
    selection rule and is never a sampling distribution, a weight or a bank rule.
    """
    pool = [str(v) for v in range(10) if str(v) != correct]
    if len(pool) != 9:
        raise CorpusDefect("the distractor pool is not the registered nine residues")
    return [pool[(base_index + j) % 9] for j in range(3)]


def contents_for_state(state, correct, distractors):
    """Lay the correct content and the ordered distractors out over four slots."""
    position = state[0]
    contents = [None, None, None, None]
    contents[position] = correct
    remaining = list(distractors)
    for slot in range(4):
        if contents[slot] is None:
            contents[slot] = remaining.pop(0)
    if remaining:
        raise CorpusDefect("the ordered distractor triple was not fully consumed")
    return contents


def contrast_applicability(registry, protocol, profile, contrast):
    """Resolve applicability of a contrast cell across both binding inputs.

    ``K6`` applicability is registered in the rendering registry's applicability
    table. ``K5`` applicability is registered in the protocol draft's
    ``i3_contrast_registry``. A contrast that neither document registers for the
    profile is a fail-closed rejection, never a default.
    """
    if contrast in K6_CONTRASTS:
        for row in registry["applicability_table"]["rows"]:
            if row["profile"] == profile and row["contrast"] == contrast:
                return row["applicability"]
        raise CorpusDefect(
            "no registered applicability row for %s/%s" % (profile, contrast))
    if contrast in K5_CONTRASTS:
        for entry in protocol["i3_contrast_registry"]["k5"]:
            if entry["contrast_id"] != contrast:
                continue
            if profile in entry["applicable_profiles"]:
                return "applicable"
            if profile in entry["not_applicable_profiles"]:
                return "not_applicable"
            raise CorpusDefect(
                "profile %s is unregistered for %s" % (profile, contrast))
        raise CorpusDefect("unregistered K5 contrast %r" % contrast)
    raise CorpusDefect("unregistered contrast %r" % contrast)


# ---------------------------------------------------------------------------
# Registered validity predicates, all evaluated before any model operation.
# ---------------------------------------------------------------------------

def check_validity(registry, correct, contents, labels, alphabet_index, position):
    """Evaluate the four registered deterministic validity predicates."""
    domain = registry["answer_domain"]["surface_forms"]
    if correct not in domain:
        raise CorpusDefect("correct_answer_in_registered_answer_domain failed")
    if contents[position] != correct:
        raise CorpusDefect("the correct content is not at the registered position")
    distractors = [contents[slot] for slot in range(4) if slot != position]
    if len(set(distractors)) != 3 or correct in distractors:
        raise CorpusDefect(
            "distractors_distinct_and_exclude_the_correct_answer failed")
    for value in distractors:
        if value not in domain:
            raise CorpusDefect("a distractor is outside the registered domain")
    names = list(registry["label_alphabets"]["alphabets"])
    alphabet = registry["label_alphabets"]["alphabets"][names[alphabet_index]]
    if set(alphabet) & set(domain):
        raise CorpusDefect("label_alphabet_disjoint_from_answer_domain failed")
    if sorted(labels) != sorted(alphabet):
        raise CorpusDefect("the displayed labels are not the active alphabet")
    return True


# ---------------------------------------------------------------------------
# Corpus construction.
# ---------------------------------------------------------------------------

def _cell_plan():
    """Enumerate every registered P0 contrast cell in registered order.

    The returned pilot base-item index is the enumeration ordinal. It is the
    only source of nuisance-state variation in P0 and is recomputable from this
    ordering alone.
    """
    plan = []
    base_index = 0
    for tuple_class in TUPLE_CLASSES:
        tuple_class_id = tuple_class["tuple_class_id"]
        for profile, contrasts, restricted_to in PROFILE_ALLOCATION:
            if restricted_to is not None and restricted_to != tuple_class_id:
                continue
            for contrast in contrasts:
                plan.append({
                    "base_index": base_index,
                    "tuple_class": tuple_class,
                    "profile": profile,
                    "contrast": contrast,
                })
                base_index += 1
    return plan


def _values_for(tuple_class_id):
    params = dict(TUPLE_PARAMETERS[tuple_class_id])
    if tuple_class_id in PERMUTATION_IMAGE:
        surface = permutation_surface(tuple_class_id)
        if params["p1"] != surface:
            raise CorpusDefect("the registered p1 surface is inconsistent")
        params["p1"] = surface
    return params


def build_rows(registry=None, protocol=None):
    """Build every frozen P0 corpus row. Deterministic and seed-free."""
    registry = registry if registry is not None else load_registry()
    protocol = protocol if protocol is not None else load_protocol()
    renderer = P0Renderer(registry)
    rows = []
    for cell in _cell_plan():
        tuple_class = cell["tuple_class"]
        tuple_class_id = tuple_class["tuple_class_id"]
        branch_id = tuple_class["branch_id"]
        profile = cell["profile"]
        contrast = cell["contrast"]
        base_index = cell["base_index"]

        applicability = contrast_applicability(
            registry, protocol, profile, contrast)
        if applicability != "applicable":
            raise CorpusDefect(
                "%s/%s is %s and must never be instantiated"
                % (profile, contrast, applicability))

        base_item_id = "%s/%s/%s-%s" % (
            NAMESPACE, tuple_class_id, profile, contrast)
        correct = ground_truth(tuple_class_id)
        values = _values_for(tuple_class_id)
        distractors = distractor_triple(base_index, correct)
        baseline = baseline_state(base_index)
        variant = variant_state(baseline, contrast)
        baseline_rendering, variant_rendering = renderings_for(contrast)

        members = []
        for role_in_pair, state, rendering in (
                ("baseline", baseline, baseline_rendering),
                ("variant", variant, variant_rendering)):
            if profile in ("S1", "S4"):
                labels = labels_for_state(registry, *state)
                contents = contents_for_state(state, correct, distractors)
                check_validity(
                    registry, correct, contents, labels, state[2], state[0])
                active_alphabet = alphabet_name(registry, state[2])
            else:
                labels = None
                contents = None
                active_alphabet = None
            prompt = renderer.render(
                profile, rendering, branch_id, values, labels, contents)
            members.append({
                "role_in_pair": role_in_pair,
                "rendering": rendering,
                "nuisance_state": {
                    "content_position": state[0],
                    "correct_symbol_index": state[1],
                    "label_alphabet_index": state[2],
                    "label_alphabet": active_alphabet,
                },
                "displayed_labels": labels,
                "displayed_contents": contents,
                "prompt": prompt,
                "prompt_bytes": len(prompt.encode("utf-8")),
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            })

        if members[0]["prompt"] == members[1]["prompt"]:
            raise CorpusDefect(
                "byte-identical applicable pair at %s: a self-comparison is a "
                "construction defect, never a pass" % base_item_id)

        rows.append({
            "row_id": "p0-%03d" % base_index,
            "base_index": base_index,
            "base_item_id": base_item_id,
            "namespace": NAMESPACE,
            "tuple_class_id": tuple_class_id,
            "branch_id": branch_id,
            "task_stratum": tuple_class["task_stratum"],
            "operation_family": tuple_class["operation_family"],
            "composition_depth": tuple_class["composition_depth"],
            "profile": profile,
            "contrast": contrast,
            "applicability": "applicable",
            "gate_bearing": False,
            "descriptive_only": True,
            "operation_parameters": values,
            "ground_truth": correct,
            "ordered_distractor_triple": distractors,
            "candidate_surface_class": (
                "label_token" if profile in ("S1",) else
                "content_token" if profile in ("S2", "S3") else
                "generated_text"),
            "members": members,
        })
    return rows


def _s3_mirrors_s2(rows):
    """S3 is a scoring rule, not a new surface: its prompts must mirror S2's."""
    by_key = {}
    for row in rows:
        by_key[(row["tuple_class_id"], row["profile"], row["contrast"])] = row
    pairs = []
    for row in rows:
        if row["profile"] != "S3":
            continue
        source = by_key.get((row["tuple_class_id"], "S2", row["contrast"]))
        if source is None:
            raise CorpusDefect("an S3 row has no S2 source row")
        for s3_member, s2_member in zip(row["members"], source["members"]):
            if s3_member["prompt"] != s2_member["prompt"]:
                raise CorpusDefect(
                    "S3 prompt bytes differ from S2; S3 is a scoring rule, "
                    "not a new surface")
        pairs.append((row["row_id"], source["row_id"]))
    return pairs


def census(rows):
    """Return the machine-readable census of the frozen corpus."""
    counts = {}
    for row in rows:
        for key in (
                ("by_profile", row["profile"]),
                ("by_tuple_class", row["tuple_class_id"]),
                ("by_contrast", row["contrast"]),
        ):
            counts.setdefault(key[0], {})
            counts[key[0]][key[1]] = counts[key[0]].get(key[1], 0) + 1
    counts["rows"] = len(rows)
    counts["members"] = sum(len(row["members"]) for row in rows)
    return counts


def aggregate_sha256(rows):
    """Hash the ordered per-row prompt digests into one aggregate identity."""
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row["row_id"].encode("utf-8"))
        digest.update(b"\n")
        digest.update(row["base_item_id"].encode("utf-8"))
        digest.update(b"\n")
        for member in row["members"]:
            digest.update(member["prompt_sha256"].encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def canonical_bytes(document):
    """The registered canonical serialisation: indent=1, sorted keys, ASCII, LF."""
    text = json.dumps(document, indent=1, sort_keys=True, ensure_ascii=True)
    return (text + "\n").encode("utf-8")


def blob_sha256(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()
