"""Independent, registry-driven renderer for the Study 3-P0 feasibility pilot.

Scope and authority
-------------------
This module belongs to the one-shot P0 feasibility pilot authorized by
``studies/study3/prompts/study3_p0_feasibility_pilot_authority.md``. It is a
methods-feasibility instrument, not Study 3 evidence.

``formal_execution_authorized`` is false throughout. This module draws no seed,
builds no bank, selects no interface, resolves no operator decision, and touches
no positive-reference object.

Why an independent implementation
---------------------------------
Section 2 of the authority asks whether *an independent implementation* can
instantiate the binding draft-v0.5 rendering registry without making an
unregistered wording, punctuation, whitespace, ordering, escaping, placeholder
or wrapper choice. A renderer that imported the existing committed fixture
renderer could not answer that question, because it would inherit that
renderer's choices.

This renderer is therefore written from the registry alone. It reads only
``interface_calibration_rendering_registry_v0_5.json``. Every normative string
it emits is checked against its registered SHA-256 asset identity before use, so
a string that merely *looks* plausible is rejected. Where the registry does not
determine a byte, the renderer raises :class:`UnregisteredSurface` rather than
choosing.

The P0 test module cross-checks this renderer against the committed fixture
renderer in ``tests/test_study3_rendering_registry_v0_5.py``. Byte agreement
between two independent implementations is the feasibility observation; it is
not a claim that draft-v0.5 is correct.

Standard library only, by design.
"""

import hashlib
import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
REGISTRY_PATH = os.path.join(
    REPO_ROOT, "studies", "study3", "protocol",
    "interface_calibration_rendering_registry_v0_5.json")
PROTOCOL_PATH = os.path.join(
    REPO_ROOT, "studies", "study3", "protocol",
    "interface_calibration_protocol_draft.json")

LABEL_BEARING = ("S1", "S4")
OPTION_LESS = ("S2", "S3")
PROFILES = ("S1", "S2", "S3", "S4")
RENDERINGS = ("R-base", "R-sep", "R-instr")

PLACEHOLDER = re.compile(r"\{([a-z][a-z0-9_]*)\}")


class UnregisteredSurface(Exception):
    """Raised when the registry does not determine a required byte."""


def load_json(path):
    """Read a committed JSON document as bytes and decode it as UTF-8."""
    with open(path, "rb") as handle:
        return json.loads(handle.read().decode("utf-8"))


def load_registry():
    return load_json(REGISTRY_PATH)


def load_protocol():
    return load_json(PROTOCOL_PATH)


class P0Renderer(object):
    """A byte-exact renderer driven entirely by the registered v0.5 surface."""

    def __init__(self, registry):
        self.registry = registry
        self.assets = {
            asset["asset_id"]: asset
            for asset in registry["registry_identity"]["normative_template_assets"]
        }
        self.stems = {
            branch["branch_id"]: branch
            for branch in registry["question_stem_templates"]["branches"]
        }
        self.instructions = {}
        for entry in registry["instructions"]["entries"]:
            if entry["applicable"]:
                key = (entry["profile"], entry["rendering"])
                self.instructions[key] = entry["instruction"]
        self.separators = {rid: registry["separators"][rid] for rid in RENDERINGS}
        self.cue = registry["answer_cue"]["literal"]
        self.alphabet_names = list(registry["label_alphabets"]["alphabets"])
        self.alphabets = registry["label_alphabets"]["alphabets"]
        self.answer_domain = list(registry["answer_domain"]["surface_forms"])
        self.profiles = {entry["profile"]: entry for entry in registry["profiles"]}
        self.registered_placeholders = set(registry["placeholders"]["names"])

    # -- registered-identity enforcement ----------------------------------
    def registered_asset(self, asset_id, text):
        """Return ``text`` only if it reproduces its registered asset identity."""
        asset = self.assets.get(asset_id)
        if asset is None:
            raise UnregisteredSurface("no registered asset %r" % asset_id)
        encoded = text.encode("utf-8")
        if hashlib.sha256(encoded).hexdigest() != asset["sha256"]:
            raise UnregisteredSurface(
                "asset %r does not reproduce its registered digest" % asset_id)
        if len(encoded) != asset["bytes"]:
            raise UnregisteredSurface(
                "asset %r has an unregistered byte length" % asset_id)
        return text

    # -- applicability ----------------------------------------------------
    def rendering_applicable(self, profile, rendering):
        for entry in self.registry["renderings"]["entries"]:
            if entry["rendering_id"] == rendering:
                return profile in entry["applicable_profiles"]
        raise UnregisteredSurface("unregistered rendering %r" % rendering)

    def contrast_applicable(self, profile, contrast):
        for row in self.registry["applicability_table"]["rows"]:
            if row["profile"] == profile and row["contrast"] == contrast:
                return row["applicability"] == "applicable"
        raise UnregisteredSurface(
            "no registered applicability row for %s/%s" % (profile, contrast))

    def stem_applicable(self, profile, branch_id):
        branch = self.stems.get(branch_id)
        if branch is None:
            raise UnregisteredSurface("no registered stem branch %r" % branch_id)
        return profile in branch["applicable_profiles"]

    # -- parts ------------------------------------------------------------
    def stem(self, branch_id, values):
        branch = self.stems.get(branch_id)
        if branch is None:
            raise UnregisteredSurface("no registered stem branch %r" % branch_id)
        template = self.registered_asset("stem/" + branch_id, branch["template"])
        needed = set(PLACEHOLDER.findall(template))
        unknown = needed - self.registered_placeholders
        if unknown:
            raise UnregisteredSurface(
                "unregistered placeholder(s) %s" % sorted(unknown))
        missing = needed - set(values)
        if missing:
            raise UnregisteredSurface("missing substitution(s) %s" % sorted(missing))
        rendered = template
        for name in sorted(needed):
            rendered = rendered.replace("{%s}" % name, values[name])
        if PLACEHOLDER.search(rendered):
            raise UnregisteredSurface("residual placeholder after substitution")
        return rendered

    def option_block(self, profile, rendering, labels, contents):
        if profile in OPTION_LESS:
            return ""
        if profile not in LABEL_BEARING:
            raise UnregisteredSurface("unregistered profile %r" % profile)
        if not self.rendering_applicable(profile, rendering):
            raise UnregisteredSurface(
                "%s has no registered %s rendering" % (profile, rendering))
        separator = self.registered_asset(
            "separator/" + rendering, self.separators[rendering])
        spec = self.profiles[profile]["option_block_by_rendering"][rendering]
        if spec["separator"] != separator:
            raise UnregisteredSurface(
                "profile %s disagrees with the registered %s separator"
                % (profile, rendering))
        if len(labels) != spec["line_count"] or len(contents) != spec["line_count"]:
            raise UnregisteredSurface(
                "exactly %d option lines are registered" % spec["line_count"])
        return "".join(
            "%s%s%s\n" % (labels[i], separator, contents[i])
            for i in range(spec["line_count"]))

    def instruction(self, profile, rendering):
        key = (profile, rendering)
        if key not in self.instructions:
            raise UnregisteredSurface(
                "no registered instruction for %s/%s" % (profile, rendering))
        return self.registered_asset(
            "instruction/%s/%s" % (profile, rendering), self.instructions[key])

    # -- assembly ---------------------------------------------------------
    def render(self, profile, rendering, branch_id, values,
               labels=None, contents=None):
        """Return the complete registered prompt bytes for one cell member."""
        if profile not in PROFILES:
            raise UnregisteredSurface("unregistered profile %r" % profile)
        if not self.rendering_applicable(profile, rendering):
            raise UnregisteredSurface(
                "%s does not render %s" % (profile, rendering))
        if not self.stem_applicable(profile, branch_id):
            raise UnregisteredSurface(
                "%s does not register stem branch %r" % (profile, branch_id))
        order = self.profiles[profile]["prompt_assembly"]["concatenation_order"]
        parts = []
        for part in order:
            if part == "question_stem":
                parts.append(self.stem(branch_id, values))
            elif part == "option_block":
                parts.append(self.option_block(profile, rendering, labels, contents))
            elif part == "instruction":
                parts.append(self.instruction(profile, rendering))
            elif part == "answer_cue":
                parts.append(self.registered_asset("answer_cue", self.cue))
            else:
                raise UnregisteredSurface("unregistered prompt part %r" % part)
        prompt = "".join(parts)
        self.validate_bytes(prompt)
        self.validate_surface_class(profile, prompt, parts[0])
        return prompt

    def validate_surface_class(self, profile, prompt, stem):
        """Reject a chat wrapper applied to a raw-completion profile.

        S1, S2 and S3 are registered ``raw_completion`` surfaces whose registered
        bytes are the complete prompt: the registry records ``chat_wrapper: null``
        for each of them. A role tag, system turn or any other prefix or suffix is
        an unregistered substitution, even when every one of its bytes is inside
        the permitted printable range.
        """
        spec = self.profiles[profile]
        if spec["surface_class"] != "raw_completion":
            return True
        if spec.get("chat_wrapper") is not None:
            raise UnregisteredSurface(
                "%s registers no chat wrapper, but one is present" % profile)
        if not prompt.startswith(stem):
            raise UnregisteredSurface(
                "a chat wrapper or unregistered prefix precedes the registered "
                "question stem of raw-completion profile %s" % profile)
        return True

    def validate_bytes(self, prompt):
        """Enforce the registered encoding policy on assembled prompt bytes."""
        policy = self.registry["encoding_policy"]
        if policy["character_encoding"] != "UTF-8":
            raise UnregisteredSurface("unregistered character encoding")
        if "\r" in prompt:
            raise UnregisteredSurface("CR is prohibited")
        if "\t" in prompt:
            raise UnregisteredSurface("TAB is prohibited")
        if "\u00a0" in prompt:
            raise UnregisteredSurface("non-breaking space is prohibited")
        if prompt.startswith("\ufeff"):
            raise UnregisteredSurface("a byte order mark is prohibited")
        for line in prompt.split("\n"):
            if line != line.rstrip(" "):
                raise UnregisteredSurface("trailing whitespace is prohibited")
        for char in prompt:
            if char in ("\n", " "):
                continue
            if not 0x21 <= ord(char) <= 0x7E:
                raise UnregisteredSurface(
                    "codepoint %r is outside the registered set" % char)
        if not prompt.endswith(self.cue):
            raise UnregisteredSurface("the prompt must end with the registered cue")

    # -- S4 role-native wrapper boundary ----------------------------------
    def s4_message_content(self, rendering, branch_id, values, labels, contents):
        """Return the registered S4 message content: the wrapper's inner bytes.

        The role-native chat wrapper is applied outside this registry. Its bytes
        are wrapper bytes; they are never registered message bytes and are never
        compared across roles.
        """
        content = self.render("S4", rendering, branch_id, values, labels, contents)
        boundary = self.profiles["S4"]["wrapper_boundary"]
        registered = boundary[
            "boundary_is_the_first_and_last_byte_of_the_registered_message_content"]
        if not registered:
            raise UnregisteredSurface("the S4 wrapper boundary is not registered")
        return content


def labels_for_state(registry, position, symbol_index, alphabet_index):
    """Return the four displayed label symbols for one nuisance state.

    The registered ordering rule says the label displayed at physical position
    ``i`` is the registered nuisance-state symbol assignment for that base-item
    index, and that the symbol carrying the correct content is the symbol at
    ``correct_symbol_index``. Both hold exactly when the alphabet is rotated by
    ``(symbol_index - position) mod 4``.
    """
    names = list(registry["label_alphabets"]["alphabets"])
    alphabet = registry["label_alphabets"]["alphabets"][names[alphabet_index]]
    shift = (symbol_index - position) % 4
    return [alphabet[(slot + shift) % 4] for slot in range(4)]


def alphabet_name(registry, alphabet_index):
    return list(registry["label_alphabets"]["alphabets"])[alphabet_index]
