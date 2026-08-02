"""Controls for the per-role production entrypoints.

Section 5.2 is explicit about what these tests have to establish: "Tests must
mutate the configured command, module binding, role, identity, and lane to prove
that the deployed path---not merely a similarly named function---is
constrained." Every mutation named there has a control below, and each one is
paired with the positive case, because a refusal test that would also pass
against a function that refuses everything proves nothing.

Two structural controls carry more weight than the rest.

``TestDeployedPathIsTheTestedPath`` proves the container command resolves to the
same callable the tests exercise. Without it, every other test in this file
could pass while the deployment ran something else.

``TestTheEntrypointsAreParserFree`` proves the module reaches its dependencies
without executing ``jspace_observation/__init__.py``, which eagerly imports
``model_loader`` and ``eval_parsing``. If it did not, a parser-free role would
hold parser code before its first statement ran, and its own isolation check
could never pass on a real container.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from jspace_observation import parser_v3_v2_entrypoints as entrypoints  # noqa: E402
from jspace_observation import parser_v3_v2_lifecycle as package_lifecycle  # noqa: E402
from jspace_observation import parser_v3_v2_schemas as package_schemas  # noqa: E402

EntrypointError = entrypoints.EntrypointError
LifecycleError = entrypoints.lifecycle.LifecycleError
ConstructionError = entrypoints.construction.ConstructionError
SchemaValidationError = entrypoints.schemas.SchemaValidationError

CLIENT_ID = "11111111-2222-3333-4444-555555555555"
IMAGE_DIGEST = "sha256:" + "ab" * 32
CONFIG_DIGEST = "cd" * 32
PRIVATE_ENDPOINT = "stjspacefiles0709085305.privatelink.blob.core.windows.net"


def _config(role: str, **overrides: object) -> entrypoints.RoleConfig:
    """A configuration that is valid for ``role`` unless a field is overridden.

    The configuration digest is *derived* from the finished configuration
    rather than typed as a constant. A constant would have been a digest that
    described nothing, which is precisely what public audit finding B-02
    refused. An explicit ``config_digest=`` override is honoured verbatim, so
    the controls that supply a wrong digest still get a wrong digest.
    """
    fields = {
        "role": role,
        "uami_name": entrypoints.ROLE_IDENTITY_NAMES[role],
        "uami_client_id": CLIENT_ID,
        "private_endpoint": PRIVATE_ENDPOINT,
        "container": entrypoints.REGISTERED_CONTAINERS[role],
        "prefix": entrypoints.REGISTERED_PREFIXES[role],
        "schema_ids": entrypoints.ROLE_SCHEMAS[role],
        "schema_registry_digest": entrypoints.schemas.REGISTRY_DIGEST,
        "image_digest": IMAGE_DIGEST,
        "config_digest": CONFIG_DIGEST,
    }
    fields.update(overrides)
    config = entrypoints.RoleConfig(**fields)  # type: ignore[arg-type]
    if "config_digest" not in overrides:
        fields["config_digest"] = entrypoints.compute_config_digest(config)
        config = entrypoints.RoleConfig(**fields)  # type: ignore[arg-type]
    return config


def _env() -> dict[str, str]:
    return {"AZURE_CLIENT_ID": CLIENT_ID, "PYTHONHASHSEED": "0"}


def _preflight_env(name: str) -> dict[str, str]:
    """The environment the deployed container is given for ``name``.

    Built from the same registries the Bicep is generated from, and with the
    configuration digest derived rather than typed, so this helper cannot make
    a container look configured when it is not.
    """
    role = entrypoints.ENTRYPOINTS[name].role
    config = _config(role)
    return {
        "JSPACE_ROLE": role,
        "AZURE_CLIENT_ID": config.uami_client_id,
        "JSPACE_UAMI_NAME": config.uami_name,
        "JSPACE_ENDPOINT": config.private_endpoint,
        "JSPACE_CONTAINER": config.container,
        "JSPACE_PREFIX": config.prefix,
        "JSPACE_SCHEMA_IDS": ",".join(config.schema_ids),
        "JSPACE_SCHEMA_REGISTRY_DIGEST": config.schema_registry_digest,
        "JSPACE_IMAGE_DIGEST": config.image_digest,
        "JSPACE_CONFIG_DIGEST": config.config_digest,
    }


def _run_preflight(
    name: str, environment: dict[str, str] | None = None
) -> entrypoints.AccessLog:
    return entrypoints.preflight(
        name,
        _preflight_env(name) if environment is None else environment,
        loaded_module_names=["json", "hashlib", "pathlib"],
    )


def _lanes(role: str) -> dict[str, list[str]]:
    lane = entrypoints.lifecycle.ROLE_LANES[role]
    return {"reads": list(lane["reads"]), "writes": list(lane["writes"])}


ALL_ROLES = tuple(sorted(entrypoints.ROLE_IDENTITY_NAMES))


# ---------------------------------------------------------------------------
# the registry itself
# ---------------------------------------------------------------------------


class TestRegistryShape:
    def test_there_is_one_entrypoint_for_each_of_the_fifteen_roles(self) -> None:
        assert len(entrypoints.ENTRYPOINTS) == 15
        roles = sorted(spec.role for spec in entrypoints.ENTRYPOINTS.values())
        assert roles == list(ALL_ROLES)

    def test_every_entrypoint_role_is_a_registered_lane(self) -> None:
        for spec in entrypoints.ENTRYPOINTS.values():
            assert spec.role in entrypoints.lifecycle.ROLE_LANES

    def test_each_role_appears_exactly_once(self) -> None:
        roles = [spec.role for spec in entrypoints.ENTRYPOINTS.values()]
        assert len(roles) == len(set(roles)), "a role with two entrypoints has two lanes"

    def test_each_role_has_its_own_prefix(self) -> None:
        prefixes = list(entrypoints.REGISTERED_PREFIXES.values())
        assert len(prefixes) == len(set(prefixes)), "a shared prefix is a shared lane"

    def test_every_role_has_an_identity_a_container_and_a_prefix(self) -> None:
        for role in ALL_ROLES:
            assert role in entrypoints.REGISTERED_CONTAINERS
            assert role in entrypoints.REGISTERED_PREFIXES
            assert role in entrypoints.ROLE_SCHEMAS

    def test_every_declared_schema_id_is_registered(self) -> None:
        for role, ids in entrypoints.ROLE_SCHEMAS.items():
            assert ids, f"{role} declares no schema and so binds nothing"
            entrypoints.schemas.assert_all_ids_reachable(ids)

    def test_role_schema_ids_are_a_subset_of_the_lifecycle_binding(self) -> None:
        bound = set(package_lifecycle.BOUND_SCHEMA_IDS)
        for role, ids in entrypoints.ROLE_SCHEMAS.items():
            assert set(ids) <= bound, f"{role} names a schema the lifecycle does not bind"


# ---------------------------------------------------------------------------
# the deployed path
# ---------------------------------------------------------------------------


class TestDeployedPathIsTheTestedPath:
    def test_resolving_the_registered_command_returns_the_real_callable(self) -> None:
        for name, spec in entrypoints.ENTRYPOINTS.items():
            resolved = entrypoints.resolve_entrypoint(spec.command)
            assert resolved is spec
            assert resolved.function is spec.function
            assert resolved.name == name

    def test_the_command_names_the_file_and_not_the_package_module(self) -> None:
        """The ``-m`` form would run the package ``__init__`` and load the parser."""
        for spec in entrypoints.ENTRYPOINTS.values():
            assert "-m" not in spec.command
            assert spec.command[1] == entrypoints.CONTAINER_ENTRYPOINT_PATH
            assert spec.command[1].endswith("parser_v3_v2_entrypoints.py")

    def test_the_registered_path_matches_this_module_s_filename(self) -> None:
        assert Path(entrypoints.CONTAINER_ENTRYPOINT_PATH).name == Path(
            entrypoints.__file__
        ).name

    @pytest.mark.parametrize(
        "command",
        [
            ("python", "-m", "jspace_observation.parser_v3_v2_entrypoints", "stage-p"),
            ("python", "/app/src/jspace_observation/other_module.py", "stage-p"),
            ("python", entrypoints.CONTAINER_ENTRYPOINT_PATH, "stage-p", "--allow-labels"),
            ("python", entrypoints.CONTAINER_ENTRYPOINT_PATH),
            ("bash", "-c", "python /app/src/jspace_observation/parser_v3_v2_entrypoints.py stage-p"),
            ("python", entrypoints.CONTAINER_ENTRYPOINT_PATH, "stage-x"),
        ],
    )
    def test_a_mutated_command_is_refused(self, command) -> None:
        """Command mutation: extra arguments, a shell wrapper, a different module."""
        with pytest.raises(EntrypointError, match="not a registered entrypoint"):
            entrypoints.resolve_entrypoint(command)

    def test_a_command_for_the_wrong_role_is_refused(self) -> None:
        """Module-binding mutation: the container runs someone else's entrypoint."""
        stage_p_command = entrypoints.ENTRYPOINTS["stage-p"].command
        with pytest.raises(EntrypointError, match="configured for role"):
            entrypoints.assert_container_command_is_registered("stage_e", stage_p_command)

    def test_the_matching_command_and_role_are_accepted(self) -> None:
        for spec in entrypoints.ENTRYPOINTS.values():
            entrypoints.assert_container_command_is_registered(spec.role, spec.command)

    def test_main_dispatches_only_registered_names(self) -> None:
        with pytest.raises(EntrypointError, match="unregistered entrypoint"):
            entrypoints.main(["not-a-role"])
        with pytest.raises(EntrypointError, match="exactly one entrypoint name"):
            entrypoints.main([])

    def test_main_refuses_to_invent_a_payload(self, monkeypatch, capsys) -> None:
        """A role that could synthesise its own input could run without the boundary.

        The property is unchanged; what changed is that it is now demonstrated
        by a command that runs. Public audit finding B-01 established that
        ``main`` previously refused *everything*, so the command bound by the
        role matrix, the Bicep and the freeze could not have done its job even
        if the boundary had been perfect. It now performs the whole preflight
        and stops, and this control proves it stopped without a payload.
        """
        monkeypatch.setattr(entrypoints.os, "environ", _preflight_env("stage-e"))
        monkeypatch.setattr(
            entrypoints, "_runtime_module_names", lambda: ("json", "hashlib", "pathlib")
        )
        code = entrypoints.main(["stage-e"])
        assert code == entrypoints.PREFLIGHT_WITHOUT_PAYLOAD
        assert code != 0, "a container that did no work must not report success"
        emitted = json.loads(capsys.readouterr().out)
        assert emitted["outcome"] == "PREFLIGHT_PASSED_PAYLOAD_NOT_SUPPLIED"
        assert emitted["role"] == "stage_e"
        assert "result" not in emitted
        assert "members" not in emitted

    def test_the_preflight_actually_reaches_the_guarded_prologue(self) -> None:
        """Otherwise it would be a command that runs and checks nothing, which
        is the same untruthful binding the audit refused, wearing a new name."""
        graph = tuple(sorted(set(entrypoints.preflight.__code__.co_names)))
        assert "_PREFLIGHT_ACTIVE" in graph
        assert "_preflight_payload" in graph
        assert "function" in graph
        assert "assert_container_command_is_registered" in graph
        assert "RoleConfig" in graph

    def test_preflight_calls_the_callable_in_the_registry(self, monkeypatch) -> None:
        """B-01. The command binding is proved by execution, not resemblance."""

        class Sentinel(Exception):
            pass

        called: list[str] = []
        original = entrypoints.ENTRYPOINTS["stage-e"]

        def replacement(*, config, environment, loaded_module_names):
            called.append(config.role)
            raise Sentinel

        monkeypatch.setitem(
            entrypoints.ENTRYPOINTS,
            "stage-e",
            entrypoints.EntrypointSpec(
                name=original.name,
                role=original.role,
                function=replacement,
                command=original.command,
            ),
        )
        with pytest.raises(Sentinel):
            _run_preflight("stage-e")
        assert called == ["stage_e"]

    def test_the_preflight_refuses_an_incomplete_environment(self) -> None:
        for name in entrypoints.PREFLIGHT_ENVIRONMENT_NAMES:
            environment = _preflight_env("stage-e")
            del environment[name]
            with pytest.raises(EntrypointError, match="missing"):
                _run_preflight("stage-e", environment)

    def test_the_preflight_refuses_a_role_that_is_not_its_entrypoint(self) -> None:
        environment = _preflight_env("stage-e")
        environment["JSPACE_ROLE"] = "stage_p"
        with pytest.raises(EntrypointError, match="started with the"):
            _run_preflight("stage-e", environment)

    def test_the_preflight_refuses_an_unregistered_name(self) -> None:
        with pytest.raises(EntrypointError, match="unregistered entrypoint"):
            _run_preflight("not-a-role", _preflight_env("stage-e"))

    def test_the_preflight_refuses_a_forged_configuration_digest(self) -> None:
        environment = _preflight_env("stage-e")
        environment["JSPACE_CONFIG_DIGEST"] = "ab" * 32
        with pytest.raises(EntrypointError, match="does not match the configuration"):
            _run_preflight("stage-e", environment)

    def test_the_preflight_refuses_a_credential_the_deployment_added(self) -> None:
        environment = _preflight_env("stage-e")
        environment["JSPACE_STORAGE_TOKEN"] = "irrelevant"
        with pytest.raises(EntrypointError, match="unregistered environment"):
            _run_preflight("stage-e", environment)

    def test_every_registered_entrypoint_has_a_runnable_preflight(self) -> None:
        """The finding was about one command; the property is about all of them."""
        for name in entrypoints.ENTRYPOINT_NAMES:
            log = _run_preflight(name)
            assert log.role == entrypoints.ENTRYPOINTS[name].role
            assert "entrypoint_completed" in log.event_ids()
            assert all(event["object_count"] == 0 for event in log.events)


class TestCallGraphIsInspectable:
    def test_every_entrypoint_reaches_the_guarded_prologue(self) -> None:
        for name in entrypoints.ENTRYPOINT_NAMES:
            entrypoints.assert_entrypoint_is_guarded(name)

    def test_the_call_graph_is_read_from_bytecode_not_from_a_list(self) -> None:
        graph = entrypoints.entrypoint_call_graph("stage-e")
        assert "_guarded" in graph
        assert "evaluation" in graph, "Stage E must reach the real evaluation module"

    def test_the_guard_control_would_notice_an_unguarded_entrypoint(self) -> None:
        """Mutation control: an entrypoint that skips the prologue must be flagged."""

        def unguarded(**kwargs):  # pragma: no cover - never executed
            return dict(kwargs)

        spec = entrypoints.EntrypointSpec(
            name="unguarded", role="stage_e", function=unguarded, command=("python", "x")
        )
        original = dict(entrypoints.ENTRYPOINTS)
        try:
            entrypoints.ENTRYPOINTS["unguarded"] = spec  # type: ignore[index]
            with pytest.raises(EntrypointError, match="guarded prologue"):
                entrypoints.assert_entrypoint_is_guarded("unguarded")
        finally:
            entrypoints.ENTRYPOINTS.clear()  # type: ignore[attr-defined]
            entrypoints.ENTRYPOINTS.update(original)  # type: ignore[attr-defined]

    def test_an_unregistered_entrypoint_has_no_call_graph(self) -> None:
        with pytest.raises(EntrypointError, match="unregistered entrypoint"):
            entrypoints.entrypoint_call_graph("no-such-entrypoint")


class TestTheEntrypointsAreParserFree:
    def test_the_module_never_imports_the_package(self) -> None:
        """AST control, not a substring scan: the string is data, the import is not."""
        tree = ast.parse(Path(entrypoints.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert node.level == 0, "a relative import would run the package __init__"
                if node.module:
                    imported.add(node.module)
        assert imported, "the AST walk found no imports at all, so it proves nothing"
        for name in imported:
            assert name.split(".")[0] != "jspace_observation", f"{name} runs the package init"
            for marker in ("eval_parsing", "parser_v3_repair", "model_loader", "torch"):
                assert marker not in name, f"{name} reaches parser-bearing code"

    def test_the_evaluation_module_can_be_loaded_without_the_package(self) -> None:
        """The dependency Stage E needs must itself be reachable parser-free."""
        assert entrypoints.evaluation.__name__ == "parser_v3_v2_evaluation"
        assert entrypoints.evaluation.lifecycle is entrypoints.lifecycle

    def test_the_standalone_copies_agree_with_the_package_copies(self) -> None:
        """A standalone module that had drifted would be a second, silent protocol."""
        assert entrypoints.lifecycle.ROLE_LANES == package_lifecycle.ROLE_LANES
        assert entrypoints.lifecycle.BOUND_SCHEMA_IDS == package_lifecycle.BOUND_SCHEMA_IDS
        assert entrypoints.schemas.REGISTRY_DIGEST == package_schemas.REGISTRY_DIGEST

    def test_a_parser_bearing_process_is_refused_for_every_parser_free_role(self) -> None:
        for role in sorted(entrypoints.PARSER_FREE_ROLES):
            with pytest.raises(LifecycleError, match="parser-bearing"):
                entrypoints.assert_import_isolation(
                    role, ["json", "jspace_observation.eval_parsing"]
                )

    def test_stage_p_is_refused_a_scoring_capable_process(self) -> None:
        with pytest.raises(entrypoints.evaluation.EvaluationError, match="scoring-bearing"):
            entrypoints.assert_import_isolation("stage_p", ["json", "my_scorer"])

    def test_a_clean_process_is_accepted(self) -> None:
        for role in ALL_ROLES:
            entrypoints.assert_import_isolation(role, ["json", "hashlib", "pathlib"])


# ---------------------------------------------------------------------------
# configuration, identity and credentials
# ---------------------------------------------------------------------------


class TestConfigurationIsClosed:
    def test_the_predeployment_digest_map_matches_every_runtime_recomputation(
        self,
    ) -> None:
        image_digests = {role: IMAGE_DIGEST for role in ALL_ROLES}
        generated = entrypoints.compute_role_config_digests(
            role_image_digests=image_digests,
            private_endpoint=PRIVATE_ENDPOINT,
        )
        assert set(generated) == set(ALL_ROLES)
        for role in ALL_ROLES:
            assert generated[role] == _config(role).config_digest

    def test_an_incomplete_predeployment_digest_input_is_refused(self) -> None:
        image_digests = {role: IMAGE_DIGEST for role in ALL_ROLES}
        image_digests.pop("stage_e")
        with pytest.raises(EntrypointError, match="missing=.*stage_e"):
            entrypoints.compute_role_config_digests(
                role_image_digests=image_digests,
                private_endpoint=PRIVATE_ENDPOINT,
            )
    def test_a_valid_configuration_is_accepted_for_every_role(self) -> None:
        for role in ALL_ROLES:
            entrypoints.assert_config_registered(_config(role))

    def test_an_unregistered_role_is_refused(self) -> None:
        with pytest.raises(EntrypointError, match="not a registered role"):
            entrypoints.assert_config_registered(
                entrypoints.RoleConfig(
                    role="shadow_reviewer",
                    uami_name="uami-jspace-shadow",
                    uami_client_id=CLIENT_ID,
                    private_endpoint="stjspacefiles0709085305.privatelink.blob.core.windows.net",
                    container="v2-review",
                    prefix="review/shadow/",
                    schema_ids=("phase1-parser-v3-v2-admission-record/v1",),
                    schema_registry_digest=entrypoints.schemas.REGISTRY_DIGEST,
                    image_digest=IMAGE_DIGEST,
                    config_digest=CONFIG_DIGEST,
                )
            )

    def test_a_role_may_not_borrow_another_role_s_identity(self) -> None:
        """Identity mutation."""
        with pytest.raises(EntrypointError, match="must run as"):
            entrypoints.assert_config_registered(
                _config("stage_p", uami_name=entrypoints.ROLE_IDENTITY_NAMES["stage_e"])
            )

    @pytest.mark.parametrize("client_id", ["", "not-a-guid", "1111", CLIENT_ID[:-1]])
    def test_a_client_id_that_is_not_a_guid_is_refused(self, client_id: str) -> None:
        with pytest.raises(EntrypointError, match="explicit GUID"):
            entrypoints.assert_config_registered(_config("arbiter", uami_client_id=client_id))

    @pytest.mark.parametrize(
        "endpoint",
        [
            "stjspacefiles0709085305.blob.core.windows.net",
            "10.0.0.4",
            "evil.privatelink.blob.core.windows.net",
            "",
        ],
    )
    def test_an_unregistered_endpoint_is_refused(self, endpoint: str) -> None:
        with pytest.raises(EntrypointError, match="registered private endpoints"):
            entrypoints.assert_config_registered(_config("arbiter", private_endpoint=endpoint))

    def test_a_role_may_not_use_another_role_s_container(self) -> None:
        with pytest.raises(EntrypointError, match="may not use container"):
            entrypoints.assert_config_registered(
                _config("reviewer_a", container=entrypoints.REGISTERED_CONTAINERS["stage_e"])
            )

    def test_a_role_may_not_use_another_role_s_prefix(self) -> None:
        with pytest.raises(EntrypointError, match="may not use prefix"):
            entrypoints.assert_config_registered(
                _config("reviewer_a", prefix=entrypoints.REGISTERED_PREFIXES["reviewer_b"])
            )

    def test_a_role_may_not_widen_its_schema_binding(self) -> None:
        widened = entrypoints.ROLE_SCHEMAS["reviewer_a"] + (
            "phase1-parser-v3-v2-stage-e-result/v1",
        )
        with pytest.raises(EntrypointError, match="may only bind"):
            entrypoints.assert_config_registered(_config("reviewer_a", schema_ids=widened))

    def test_an_unregistered_schema_id_is_refused(self) -> None:
        with pytest.raises(EntrypointError, match="may only bind"):
            entrypoints.assert_config_registered(
                _config("reviewer_a", schema_ids=("phase1-parser-v3-v2-invented/v1",))
            )

    @pytest.mark.parametrize("digest", ["latest", "v2", "sha256:short", "", "ab" * 32])
    def test_an_image_tag_is_refused_where_a_digest_is_required(self, digest: str) -> None:
        with pytest.raises(EntrypointError, match="sha256: digest"):
            entrypoints.assert_config_registered(_config("stage_e", image_digest=digest))

    @pytest.mark.parametrize("digest", ["", "not-hex", "AB" * 32, "ab" * 31])
    def test_a_malformed_config_digest_is_refused(self, digest: str) -> None:
        with pytest.raises(EntrypointError, match="SHA-256 hex digest"):
            entrypoints.assert_config_registered(_config("stage_e", config_digest=digest))

    def test_a_well_formed_but_wrong_config_digest_is_refused(self) -> None:
        """B-02. Syntax is not a binding.

        Before this control, ``config_digest`` only had to look like a
        SHA-256 hex string, so sixty-four arbitrary hex characters satisfied
        every check the deployment made about its own configuration.
        """
        with pytest.raises(EntrypointError, match="does not match the configuration"):
            entrypoints.assert_config_registered(_config("stage_e", config_digest="ab" * 32))

    @pytest.mark.parametrize(
        "field,value",
        [
            ("image_digest", "sha256:" + "cd" * 32),
        ],
    )
    def test_changing_a_bound_field_invalidates_the_digest(
        self, field: str, value: str
    ) -> None:
        """B-02. The digest must actually cover the fields it claims to cover.

        Each of these substitutions leaves a configuration that passes every
        other check, so if the digest did not cover it the substitution would
        be invisible.
        """
        original = _config("stage_e")
        forged = _config("stage_e", **{field: value, "config_digest": original.config_digest})
        assert entrypoints.compute_config_digest(forged) != original.config_digest
        with pytest.raises(EntrypointError, match="does not match the configuration"):
            entrypoints.assert_config_registered(forged)

    def test_the_registered_identity_name_is_in_the_configuration_digest(self) -> None:
        registered = _config("stage_e")
        borrowed = _config(
            "stage_e",
            uami_name="id-jspace-parser-v3-v2-stage-p",
            config_digest=registered.config_digest,
        )
        assert (
            entrypoints.compute_config_digest(borrowed) != registered.config_digest
        )
        with pytest.raises(EntrypointError, match="must run as"):
            entrypoints.assert_config_registered(borrowed)

    def test_the_digest_is_bound_to_the_schema_registry(self) -> None:
        """A configuration validated against a different schema set is a
        different configuration, even when every visible field agrees."""
        config = _config("stage_e")
        original = entrypoints.compute_config_digest(config)
        assert len(original) == 64
        assert original != entrypoints.compute_config_digest(_config("stage_p"))
        changed = _config(
            "stage_e",
            schema_registry_digest="ff" * 32,
            config_digest=config.config_digest,
        )
        assert entrypoints.compute_config_digest(changed) != original

    def test_the_runtime_schema_digest_must_name_the_loaded_registry(self) -> None:
        config = _config("stage_e")
        with pytest.raises(EntrypointError, match="registry loaded by this role"):
            entrypoints.assert_config_registered(
                _config(
                    "stage_e",
                    schema_registry_digest="ff" * 32,
                    config_digest=config.config_digest,
                )
            )

    @pytest.mark.parametrize("digest", ["", "not-hex", "AB" * 32, "ab" * 31])
    def test_a_malformed_schema_registry_digest_is_refused(self, digest: str) -> None:
        with pytest.raises(EntrypointError, match="schema_registry_digest"):
            entrypoints.assert_config_registered(
                _config("stage_e", schema_registry_digest=digest)
            )

    def test_the_registration_check_verifies_the_schema_binding(self) -> None:
        """B-02. ``assert_schema_binding`` was defined and never called.

        A verification routine that no production path reaches is a comment.
        The call graph is read from bytecode so that removing the call fails
        here rather than being noticed by a reader.
        """
        graph = set(entrypoints.assert_config_registered.__code__.co_names)
        assert "assert_schema_binding" in graph
        assert "compute_config_digest" in graph

    def test_a_drifted_schema_registry_stops_every_configuration(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(entrypoints.schemas, "REGISTRY_DIGEST", "ff" * 32)
        with pytest.raises(entrypoints.lifecycle.LifecycleError):
            entrypoints.assert_config_registered(_config("stage_e"))

    def test_a_non_config_object_is_refused(self) -> None:
        with pytest.raises(EntrypointError, match="must be a RoleConfig"):
            entrypoints.assert_config_registered({"role": "stage_e"})  # type: ignore[arg-type]


class TestIdentityAndCredentials:
    def test_the_registered_identity_is_accepted(self) -> None:
        entrypoints.assert_identity(_config("stage_e"), _env())

    def test_a_missing_client_id_is_refused(self) -> None:
        with pytest.raises(EntrypointError, match="ambient identity is refused"):
            entrypoints.assert_identity(_config("stage_e"), {})

    def test_a_different_identity_is_refused(self) -> None:
        env = _env() | {"AZURE_CLIENT_ID": "99999999-9999-9999-9999-999999999999"}
        with pytest.raises(EntrypointError, match="not the role's registered identity"):
            entrypoints.assert_identity(_config("stage_e"), env)

    @pytest.mark.parametrize(
        "key",
        [
            "AZURE_CLIENT_SECRET",
            "AZURE_STORAGE_ACCOUNT_KEY",
            "AZURE_STORAGE_CONNECTION_STRING",
            "BLOB_SAS_TOKEN",
            "STORAGE_SHARED_KEY",
            "SOME_PASSWORD",
            "azure_client_certificate_path",
            "AZURE_FEDERATED_TOKEN_FILE",
        ],
    )
    def test_ambient_credential_material_is_refused(self, key: str) -> None:
        with pytest.raises(EntrypointError, match="ambient credential material"):
            entrypoints.assert_no_ambient_credentials(_env() | {key: "x"})

    @pytest.mark.parametrize("value", ["1", "true", "TRUE", "yes"])
    def test_an_explicit_ambient_fallback_is_refused(self, value: str) -> None:
        with pytest.raises(EntrypointError, match="ambient credential fallback"):
            entrypoints.assert_no_ambient_credentials(
                _env() | {"AZURE_USE_AMBIENT_CREDENTIAL": value}
            )

    @pytest.mark.parametrize(
        "key",
        [
            "FOO_TOKEN",
            "MY_STORAGE_AUTH",
            "REVIEWER_SIGNATURE",
            "APP_CREDENTIALS",
            "svc_pwd",
            "DATABRICKS_SECRET_SCOPE",
            "SSH_AUTH_SOCK",
            "TLS_CERT_PATH",
            "HMAC_KEY_B64",
            "SASL_PASSWD",
        ],
    )
    def test_a_credential_shaped_name_nobody_anticipated_is_refused(
        self, key: str
    ) -> None:
        """B-04. The denylist was a list of the mechanisms we thought of.

        Every one of these passed every marker in
        ``FORBIDDEN_CREDENTIAL_MARKERS`` and reached the payload. They are
        refused now because the rule is closure, not enumeration.
        """
        assert not any(
            marker in key.casefold() for marker in entrypoints.FORBIDDEN_CREDENTIAL_MARKERS
        ), "this name is already caught by the denylist, so it proves nothing about closure"
        with pytest.raises(EntrypointError, match="unregistered environment"):
            entrypoints.assert_no_ambient_credentials(_env() | {key: "x"})

    def test_the_registered_environment_names_are_the_only_exemptions(self) -> None:
        """Every admitted name is explicit; a prefix or regex would be a denylist."""
        assert set(entrypoints.PREFLIGHT_ENVIRONMENT_NAMES) <= set(
            entrypoints.REGISTERED_ENVIRONMENT_NAMES
        )
        assert {"IDENTITY_ENDPOINT", "IDENTITY_HEADER"} <= set(
            entrypoints.REGISTERED_ENVIRONMENT_NAMES
        )
        assert "FOO_TOKEN" not in entrypoints.REGISTERED_ENVIRONMENT_NAMES

    def test_an_unknown_name_with_no_credential_marker_is_still_refused(self) -> None:
        """This distinguishes closure from a broader marker denylist."""
        key = "UNCLASSIFIED_CHANNEL"
        assert not any(
            marker in key.casefold()
            for marker in entrypoints.FORBIDDEN_CREDENTIAL_MARKERS
        )
        with pytest.raises(EntrypointError, match="unregistered environment"):
            entrypoints.assert_no_ambient_credentials(_env() | {key: "x"})

    def test_the_ambient_flag_is_refused_by_closure_even_when_switched_off(
        self,
    ) -> None:
        """``AZURE_USE_AMBIENT_CREDENTIAL=0`` used to be accepted silently.

        A role has no reason to carry the variable at all, and a value-based
        check is one typo away from being read the other way round.
        """
        with pytest.raises(EntrypointError, match="unregistered environment"):
            entrypoints.assert_no_ambient_credentials(
                _env() | {"AZURE_USE_AMBIENT_CREDENTIAL": "0"}
            )

    def test_the_broad_markers_do_not_swallow_the_named_ones(self) -> None:
        """The precise message has to survive, or an operator loses the one
        piece of information that says which mechanism arrived."""
        with pytest.raises(EntrypointError, match="ambient credential material"):
            entrypoints.assert_no_ambient_credentials(_env() | {"AZURE_CLIENT_SECRET": "x"})

    def test_the_deployed_environment_passes_the_closure_rule(self) -> None:
        """The rule must refuse credentials without refusing the deployment.

        A closure rule that also rejected the variables every role legitimately
        needs would be repaired by widening the exemption list, and the
        exemption list is the denylist coming back.
        """
        for name in entrypoints.ENTRYPOINT_NAMES:
            entrypoints.assert_no_ambient_credentials(_preflight_env(name))

    def test_a_clean_environment_is_accepted(self) -> None:
        entrypoints.assert_no_ambient_credentials(_env())


# ---------------------------------------------------------------------------
# lanes
# ---------------------------------------------------------------------------


class TestLanes:
    def test_each_role_s_own_lane_is_accepted(self) -> None:
        for role in ALL_ROLES:
            entrypoints.assert_lanes(role, **_lanes(role))

    def test_a_read_outside_the_lane_is_refused(self) -> None:
        """Lane mutation."""
        lanes = _lanes("reviewer_a")
        lanes["reads"].append("scoring_labels")
        with pytest.raises(EntrypointError, match="outside its lane"):
            entrypoints.assert_lanes("reviewer_a", **lanes)

    def test_a_write_outside_the_lane_is_refused(self) -> None:
        lanes = _lanes("reviewer_a")
        lanes["writes"].append("v2_sealed_namespace")
        with pytest.raises(EntrypointError, match="outside its lane"):
            entrypoints.assert_lanes("reviewer_a", **lanes)

    def test_only_stage_e_may_read_labels(self) -> None:
        assert entrypoints.lifecycle.LABEL_READING_ROLE == "stage_e"
        for role in ALL_ROLES:
            if role == "stage_e":
                continue
            with pytest.raises(EntrypointError):
                entrypoints.assert_lanes(role, reads=["scoring_labels"], writes=[])

    def test_stage_p_is_refused_a_forbidden_class_even_inside_a_widened_lane(
        self, monkeypatch
    ) -> None:
        """The stage scope check must not be reachable only through the lane table.

        If a future edit widened Stage P's lane, the lane check alone would let
        a label through. ``assert_stage_p_scope`` is called unconditionally for
        exactly that reason, and this control proves it.
        """
        widened = dict(entrypoints.lifecycle.ROLE_LANES)
        widened["stage_p"] = {
            "reads": ("sealed_v2_inputs", "frozen_parser_assets", "scoring_labels"),
            "writes": ("prediction_namespace",),
        }
        monkeypatch.setattr(entrypoints.lifecycle, "ROLE_LANES", widened)
        with pytest.raises((EntrypointError, LifecycleError)):
            entrypoints.assert_lanes(
                "stage_p",
                reads=["sealed_v2_inputs", "scoring_labels"],
                writes=["prediction_namespace"],
            )

    def test_an_unregistered_role_has_no_lane(self) -> None:
        with pytest.raises(EntrypointError, match="not a registered role"):
            entrypoints.assert_lanes("shadow_reviewer", reads=[], writes=[])


# ---------------------------------------------------------------------------
# the guarded prologue
# ---------------------------------------------------------------------------


class TestGuardedPrologue:
    def test_the_prologue_passes_for_every_role_under_a_valid_deployment(self) -> None:
        for role in ALL_ROLES:
            log = entrypoints.AccessLog(role=role)
            entrypoints._guarded(
                _config(role),
                **_lanes(role),
                environment=_env(),
                loaded_module_names=["json"],
                log=log,
            )
            assert log.event_ids() == (
                "identity_assertion_passed",
                "lane_check_passed",
                "import_isolation_passed",
            )

    def test_a_log_bound_to_another_role_is_refused(self) -> None:
        with pytest.raises(EntrypointError, match="bound to a different role"):
            entrypoints._guarded(
                _config("stage_e"),
                **_lanes("stage_e"),
                environment=_env(),
                loaded_module_names=["json"],
                log=entrypoints.AccessLog(role="stage_p"),
            )

    def test_a_refusal_is_recorded_as_a_closed_event(self) -> None:
        log = entrypoints.AccessLog(role="stage_e")
        with pytest.raises(EntrypointError):
            entrypoints._guarded(
                _config("stage_e"),
                **_lanes("stage_e"),
                environment={},
                loaded_module_names=["json"],
                log=log,
            )
        assert log.event_ids() == ("identity_assertion_refused",)
        assert log.events[0]["status"] == "refused"

    def test_the_lane_check_runs_before_the_import_check(self) -> None:
        """Order is part of the contract: the first refusal must name the real fault."""
        log = entrypoints.AccessLog(role="reviewer_a")
        lanes = _lanes("reviewer_a")
        lanes["reads"].append("scoring_labels")
        with pytest.raises(EntrypointError):
            entrypoints._guarded(
                _config("reviewer_a"),
                **lanes,
                environment=_env(),
                loaded_module_names=["jspace_observation.eval_parsing"],
                log=log,
            )
        assert log.event_ids() == ("identity_assertion_passed", "lane_check_refused")


class TestAccessLogIsContentFree:
    def test_only_closed_event_ids_are_accepted(self) -> None:
        log = entrypoints.AccessLog(role="stage_e")
        with pytest.raises(SchemaValidationError):
            log.record("read_case_42_text")

    def test_a_rejected_event_is_not_appended(self) -> None:
        log = entrypoints.AccessLog(role="stage_e")
        with pytest.raises(SchemaValidationError):
            log.record("not_a_registered_event")
        assert log.events == []

    def test_the_step_counter_does_not_advance_on_a_rejected_event(self) -> None:
        log = entrypoints.AccessLog(role="stage_e")
        log.record("entrypoint_started")
        with pytest.raises(SchemaValidationError):
            log.record("not_a_registered_event")
        second = log.record("entrypoint_completed")
        assert second["occurred_at_step"] == 1

    def test_an_unregistered_role_cannot_log(self) -> None:
        log = entrypoints.AccessLog(role="shadow_reviewer")
        with pytest.raises(SchemaValidationError):
            log.record("entrypoint_started")

    def test_every_recorded_event_validates_against_the_bound_schema(self) -> None:
        log = entrypoints.AccessLog(role="stage_p")
        log.record("payload_read_started", read_class="sealed_v2_inputs", object_count=120)
        for event in log.events:
            package_schemas.assert_valid("phase1-parser-v3-v2-access-event/v1", event)

    def test_the_schema_has_no_field_that_could_carry_content(self) -> None:
        schema = package_schemas.get_schema("phase1-parser-v3-v2-access-event/v1")
        assert schema["additionalProperties"] is False
        for forbidden in ("prompt", "response", "object_name", "message", "detail", "text"):
            assert forbidden not in schema["properties"]


# ---------------------------------------------------------------------------
# the entrypoints invoke the real implementations
# ---------------------------------------------------------------------------


class TestEntrypointsInvokeTheRealImplementation:
    """A wrapper that reimplemented its dependency would pass every check above.

    Each control replaces the real implementation with one that raises a
    sentinel and asserts the sentinel escapes: proof of an actual call, not of a
    similarly named local copy.
    """

    class Sentinel(Exception):
        pass

    def _boom(self, *args, **kwargs):
        raise TestEntrypointsInvokeTheRealImplementation.Sentinel()

    def test_stage_p_calls_the_real_run_stage_p(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.evaluation, "run_stage_p", self._boom)
        with pytest.raises(self.Sentinel):
            entrypoints.run_stage_p(
                config=_config("stage_p"),
                environment=_env(),
                loaded_module_names=["json"],
                lock={"stage_p_read_classes": ["sealed_v2_inputs"]},
                lock_digest="0" * 64,
                state="PREREGISTERED",
                ordinal=0,
                locked_inputs=[],
                parser=lambda case: case,
            )

    def test_stage_e_calls_the_real_run_stage_e(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.evaluation, "run_stage_e", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_stage_e(
                existing_result_digests=(),
                config=_config("stage_e"),
                environment=_env(),
                loaded_module_names=["json"],
                lock={"stage_e_read_classes": ["sealed_predictions", "scoring_labels"]},
                lock_digest="0" * 64,
                prediction_receipt={},
                sealed_members=[],
                labels={},
                strata={},
            )

    def test_the_preregistration_compiler_calls_the_real_lock_creator(
        self, monkeypatch
    ) -> None:
        monkeypatch.setattr(entrypoints.evaluation, "create_preregistration_lock", self._boom)
        with pytest.raises(self.Sentinel):
            entrypoints.run_preregistration_compiler(
                existing_lock_digest=None,
                config=_config("preregistration_compiler"),
                environment=_env(),
                loaded_module_names=["json"],
                bindings={},
            )

    def test_the_prediction_sealer_calls_the_real_sealer(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.evaluation, "seal_prediction_stream", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_prediction_sealer(
                existing_objects=(),
                config=_config("prediction_sealer"),
                environment=_env(),
                loaded_module_names=["json"],
                stream={},
                sealed_case_ids=[],
                write_order=[],
                terminal_manifest="manifest.json",
            )

    def test_the_seal_custodian_calls_the_real_create_only_check(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.lifecycle, "assert_create_only_plan", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_seal_custodian(
                existing_objects=(),
                config=_config("seal_custodian"),
                environment=_env(),
                loaded_module_names=["json"],
                plan={
                    "planned_objects": ["a"],
                    "write_order": ["a", "manifest.json"],
                    "terminal_manifest": "manifest.json",
                },
            )

    def test_the_selector_calls_the_real_set_invariants(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.construction, "assert_final_set_invariants", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_selector(
                config=_config("selector"),
                environment=_env(),
                loaded_module_names=["json"],
                admitted=[],
            )

    def test_the_auditor_calls_the_real_set_invariants(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.construction, "assert_final_set_invariants", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_private_set_auditor(
                config=_config("private_set_auditor"),
                environment=_env(),
                loaded_module_names=["json"],
                admitted=[],
            )

    def test_a_reviewer_calls_the_real_blindness_check(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.construction, "assert_reviewer_packet_is_blind", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_reviewer_a(
                config=_config("reviewer_a"),
                environment=_env(),
                loaded_module_names=["json"],
                packets=[{"case_content": "x", "public_ontology_packet": {}}],
                decide=lambda packet: {},
            )

    def test_the_arbiter_calls_the_real_scope_check(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.construction, "assert_arbiter_packet_is_scoped", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_arbiter(
                config=_config("arbiter"),
                environment=_env(),
                loaded_module_names=["json"],
                packets=[{}],
                adjudicate=lambda packet: {},
            )

    def test_the_broker_calls_the_real_routing_rule(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.construction, "routes_to_arbiter", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_broker(
                config=_config("broker"),
                environment=_env(),
                loaded_module_names=["json"],
                pairs=[
                    {
                        "case_ref": "case-001",
                        "case_content": "x",
                        "public_ontology_packet": {},
                        "reviewer_a": {},
                        "reviewer_b": {},
                    }
                ],
            )

    def test_the_receipt_exporter_calls_the_real_parser_field_check(self, monkeypatch) -> None:
        monkeypatch.setattr(entrypoints.construction, "assert_no_parser_field", self._boom)
        monkeypatch.setattr(entrypoints, "_validate_each", lambda *a, **k: None)
        with pytest.raises(self.Sentinel):
            entrypoints.run_receipt_exporter(
                config=_config("receipt_exporter"),
                environment=_env(),
                loaded_module_names=["json"],
                receipt={},
            )


class TestEveryEntrypointRefusesBeforeTouchingItsPayload:
    """The prologue must run before the payload, for every role without exception.

    Each entrypoint is called with a deliberately invalid identity and a payload
    that would raise a different, recognisable error if it were reached first.
    """

    POISON = object()

    @pytest.mark.parametrize("name", entrypoints.ENTRYPOINT_NAMES)
    def test_a_wrong_identity_refuses_before_the_payload_is_read(self, name: str) -> None:
        spec = entrypoints.ENTRYPOINTS[name]
        bad_env = {"AZURE_CLIENT_ID": "00000000-0000-0000-0000-000000000000"}
        payloads: dict[str, dict[str, object]] = {
            "source_custodian": {"admission_records": self.POISON},
            "normalizer": {"admission_records": self.POISON},
            "reviewer_a": {"packets": self.POISON, "decide": self.POISON},
            "reviewer_b": {"packets": self.POISON, "decide": self.POISON},
            "broker": {"pairs": self.POISON},
            "arbiter": {"packets": self.POISON, "adjudicate": self.POISON},
            "selector": {"admitted": self.POISON},
            "private_set_auditor": {"admitted": self.POISON},
            "facts_compiler": {"admitted": self.POISON, "facts": self.POISON},
            "seal_custodian": {
                "plan": self.POISON,
                "existing_objects": self.POISON,
            },
            "preregistration_compiler": {
                "bindings": self.POISON,
                "existing_lock_digest": self.POISON,
            },
            "stage_p": {
                "lock": {"stage_p_read_classes": ["sealed_v2_inputs"]},
                "lock_digest": "0" * 64,
                "state": "PREREGISTERED",
                "ordinal": 0,
                "locked_inputs": self.POISON,
                "parser": self.POISON,
            },
            "prediction_sealer": {
                "stream": self.POISON,
                "sealed_case_ids": self.POISON,
                "write_order": self.POISON,
                "terminal_manifest": self.POISON,
                "existing_objects": self.POISON,
            },
            "stage_e": {
                "lock": {"stage_e_read_classes": ["sealed_predictions", "scoring_labels"]},
                "lock_digest": "0" * 64,
                "prediction_receipt": self.POISON,
                "sealed_members": self.POISON,
                "labels": self.POISON,
                "strata": self.POISON,
                "existing_result_digests": self.POISON,
            },
            "receipt_exporter": {"receipt": self.POISON},
        }
        with pytest.raises(EntrypointError, match="registered identity"):
            spec.function(
                config=_config(spec.role),
                environment=bad_env,
                loaded_module_names=["json"],
                **payloads[spec.role],
            )
