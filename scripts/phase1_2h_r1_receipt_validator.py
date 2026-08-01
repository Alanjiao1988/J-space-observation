"""Phase 1.2H-R1 content-free access-receipt validator.

This module is deliberately standalone. It imports nothing from
``jspace_observation``, because that package's ``__init__`` eagerly imports the
legacy parser, and the access probe has no business pulling parser code into a
process that touches the authoritative sealed source.

It also deliberately implements the draft-07 subset used by
``docs/phase1_2h_r1_access_receipt.schema.json`` rather than depending on
``jsonschema``. Two reasons:

* the runtime image stays at the standard library, so the dependency graph the
  auditors have to reason about is the standard library plus the Azure SDK; and
* an unrecognised schema keyword is an error here rather than something silently
  ignored. A validator that ignores the keyword it does not understand is not a
  closed schema, it is a schema-shaped comment.

The validator fails closed in both directions: an instance that violates the
schema is rejected, and a schema containing a construct this validator does not
implement is also rejected.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

__all__ = [
    "ReceiptSchemaError",
    "ReceiptValidationError",
    "SUPPORTED_KEYWORDS",
    "ANNOTATION_KEYWORDS",
    "load_schema",
    "validate_receipt",
    "validate_instance",
]


class ReceiptSchemaError(Exception):
    """The schema itself uses a construct this validator does not implement."""


class ReceiptValidationError(Exception):
    """The instance does not satisfy the schema."""


# Keywords that constrain the instance. Anything outside this set and
# ANNOTATION_KEYWORDS raises, so the schema cannot quietly grow a constraint
# that is never enforced.
SUPPORTED_KEYWORDS = frozenset(
    {
        "type",
        "const",
        "enum",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "pattern",
        "minimum",
        "maximum",
        "minLength",
        "maxLength",
        "minItems",
        "maxItems",
        "format",
    }
)

# Keywords that carry documentation only and constrain nothing.
ANNOTATION_KEYWORDS = frozenset({"$schema", "$id", "title", "description"})

_TYPES: dict[str, tuple[type, ...] | type] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}

# RFC 3339 with a mandatory offset. The receipt's timestamps must be
# unambiguous, because they are the only ordering evidence a reader has.
_DATE_TIME = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt]\d{2}:\d{2}:\d{2}(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$"
)


def load_schema(path: str | Path) -> dict[str, Any]:
    """Load and structurally check the committed receipt schema."""

    schema = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        raise ReceiptSchemaError("schema root must be an object")
    _check_schema(schema, "$")
    return schema


def _check_schema(schema: Any, where: str) -> None:
    if not isinstance(schema, dict):
        raise ReceiptSchemaError(f"{where}: subschema must be an object")
    unknown = set(schema) - SUPPORTED_KEYWORDS - ANNOTATION_KEYWORDS
    if unknown:
        raise ReceiptSchemaError(
            f"{where}: unsupported schema keyword(s) {sorted(unknown)}. This "
            "validator refuses to ignore a keyword it does not enforce."
        )

    declared = schema.get("type")
    if declared is not None:
        names = declared if isinstance(declared, list) else [declared]
        for name in names:
            if name not in _TYPES:
                raise ReceiptSchemaError(f"{where}: unknown type {name!r}")

    if "format" in schema and schema["format"] != "date-time":
        raise ReceiptSchemaError(
            f"{where}: only the date-time format is implemented, got "
            f"{schema['format']!r}"
        )

    props = schema.get("properties")
    if props is not None:
        if not isinstance(props, dict):
            raise ReceiptSchemaError(f"{where}: properties must be an object")
        for name, sub in props.items():
            _check_schema(sub, f"{where}.{name}")

    if "additionalProperties" in schema:
        extra = schema["additionalProperties"]
        if extra is not False:
            raise ReceiptSchemaError(
                f"{where}: additionalProperties must be false. An open object "
                "in a content-free receipt schema is exactly the hole this "
                "round exists to close."
            )

    if schema.get("type") == "object" and "additionalProperties" not in schema:
        raise ReceiptSchemaError(
            f"{where}: an object subschema must state additionalProperties: false"
        )

    items = schema.get("items")
    if items is not None:
        if isinstance(items, list):
            raise ReceiptSchemaError(f"{where}: tuple-form items is not implemented")
        _check_schema(items, f"{where}[]")

    required = schema.get("required")
    if required is not None:
        if not isinstance(required, list) or not all(
            isinstance(r, str) for r in required
        ):
            raise ReceiptSchemaError(f"{where}: required must be a list of strings")
        if props is not None:
            missing = [r for r in required if r not in props]
            if missing:
                raise ReceiptSchemaError(
                    f"{where}: required names {missing} have no property schema, "
                    "so they would be required but unconstrained"
                )


def validate_instance(instance: Any, schema: Mapping[str, Any], where: str = "$") -> None:
    """Raise :class:`ReceiptValidationError` if *instance* violates *schema*."""

    declared = schema.get("type")
    if declared is not None:
        names = declared if isinstance(declared, list) else [declared]
        if not _type_matches(instance, names):
            raise ReceiptValidationError(
                f"{where}: expected type {declared!r}, got "
                f"{type(instance).__name__}"
            )

    if "const" in schema and instance != schema["const"]:
        raise ReceiptValidationError(
            f"{where}: expected constant {schema['const']!r}, got {instance!r}"
        )

    if "enum" in schema and instance not in schema["enum"]:
        raise ReceiptValidationError(
            f"{where}: value not in the closed vocabulary {schema['enum']!r}"
        )

    if isinstance(instance, str):
        _validate_string(instance, schema, where)
    if isinstance(instance, bool):
        # bool is a subclass of int; numeric bounds must not silently apply.
        pass
    elif isinstance(instance, (int, float)):
        _validate_number(instance, schema, where)
    if isinstance(instance, list):
        _validate_array(instance, schema, where)
    if isinstance(instance, dict):
        _validate_object(instance, schema, where)


def _type_matches(instance: Any, names: Sequence[str]) -> bool:
    for name in names:
        expected = _TYPES[name]
        if name == "integer":
            if isinstance(instance, bool):
                continue
            if isinstance(instance, int):
                return True
            continue
        if name == "number":
            if isinstance(instance, bool):
                continue
            if isinstance(instance, (int, float)):
                return True
            continue
        if name == "boolean":
            if isinstance(instance, bool):
                return True
            continue
        if isinstance(instance, expected):
            return True
    return False


def _validate_string(instance: str, schema: Mapping[str, Any], where: str) -> None:
    pattern = schema.get("pattern")
    if pattern is not None and re.search(pattern, instance) is None:
        raise ReceiptValidationError(f"{where}: value does not match {pattern!r}")
    if "minLength" in schema and len(instance) < schema["minLength"]:
        raise ReceiptValidationError(f"{where}: shorter than {schema['minLength']}")
    if "maxLength" in schema and len(instance) > schema["maxLength"]:
        raise ReceiptValidationError(f"{where}: longer than {schema['maxLength']}")
    if schema.get("format") == "date-time" and _DATE_TIME.match(instance) is None:
        raise ReceiptValidationError(
            f"{where}: not an RFC 3339 date-time with an explicit offset"
        )


def _validate_number(instance: Any, schema: Mapping[str, Any], where: str) -> None:
    if "minimum" in schema and instance < schema["minimum"]:
        raise ReceiptValidationError(f"{where}: below minimum {schema['minimum']}")
    if "maximum" in schema and instance > schema["maximum"]:
        raise ReceiptValidationError(f"{where}: above maximum {schema['maximum']}")


def _validate_array(instance: list, schema: Mapping[str, Any], where: str) -> None:
    if "minItems" in schema and len(instance) < schema["minItems"]:
        raise ReceiptValidationError(f"{where}: fewer than {schema['minItems']} items")
    if "maxItems" in schema and len(instance) > schema["maxItems"]:
        raise ReceiptValidationError(f"{where}: more than {schema['maxItems']} items")
    item_schema = schema.get("items")
    if item_schema is not None:
        for index, item in enumerate(instance):
            validate_instance(item, item_schema, f"{where}[{index}]")


def _validate_object(instance: dict, schema: Mapping[str, Any], where: str) -> None:
    props: Mapping[str, Any] = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in instance:
            raise ReceiptValidationError(f"{where}: required field {name!r} is missing")
    if schema.get("additionalProperties") is False:
        extra = sorted(set(instance) - set(props))
        if extra:
            raise ReceiptValidationError(
                f"{where}: undeclared field(s) {extra}. The receipt schema is "
                "closed precisely so an undeclared field cannot carry private "
                "material past review."
            )
    for name, value in instance.items():
        sub = props.get(name)
        if sub is not None:
            validate_instance(value, sub, f"{where}.{name}")


def validate_receipt(receipt: Any, schema_path: str | Path) -> None:
    """Validate *receipt* against the committed schema at *schema_path*."""

    validate_instance(receipt, load_schema(schema_path))
    _assert_invariant_count_agrees(receipt)


def _assert_invariant_count_agrees(receipt: Any) -> None:
    """Require ``invariants_checked`` to equal the invariants actually listed.

    JSON Schema cannot compare two sibling fields, and this validator refuses
    keywords it does not enforce rather than accepting ones it silently ignores,
    so the cross-field rule lives here.

    Audit C (C-12) found ``invariants_checked`` emitted as a literal. The fix
    was to derive it from the checks that ran and to list them; this makes the
    list and the count unable to disagree, so a receipt cannot claim twelve
    invariants while naming three.
    """

    if not isinstance(receipt, Mapping):
        return
    verdict = receipt.get("verdict")
    if not isinstance(verdict, Mapping) or "invariants_evaluated" not in verdict:
        # Receipt 003 predates the field. Its count is a literal, which is
        # recorded in the schema and in the limitations ledger rather than
        # papered over here.
        return
    evaluated = verdict["invariants_evaluated"]
    checked = verdict.get("invariants_checked")
    if len(evaluated) != checked:
        raise ReceiptValidationError(
            f"$.verdict: invariants_checked is {checked} but "
            f"{len(evaluated)} invariants are named; the count must be the "
            "length of the list, not an independent assertion"
        )
    if len(set(evaluated)) != len(evaluated):
        raise ReceiptValidationError(
            "$.verdict.invariants_evaluated: contains a duplicate; an "
            "invariant evaluated twice is still one invariant"
        )


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("receipt", help="path to a receipt JSON document")
    parser.add_argument(
        "--schema",
        default=str(
            Path(__file__).resolve().parents[1]
            / "docs"
            / "phase1_2h_r1_access_receipt.schema.json"
        ),
    )
    args = parser.parse_args(argv)
    try:
        validate_receipt(
            json.loads(Path(args.receipt).read_text(encoding="utf-8")), args.schema
        )
    except (ReceiptSchemaError, ReceiptValidationError) as exc:
        print(f"receipt validation: FAIL: {exc}")
        return 1
    print("receipt validation: OK")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(_main())
