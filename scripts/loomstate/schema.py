"""Minimal JSON Schema (draft 2020-12 subset) validator — stdlib only.

Supports the keywords loom schemas use: type, required, properties,
additionalProperties, patternProperties, items, enum, const, minLength,
minItems, minimum, pattern, $ref (local #/$defs), anyOf, oneOf.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .core import SCHEMAS_DIR, LoomError

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is_type(value, t: str) -> bool:
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[t])


def _resolve(ref: str, root: dict) -> dict:
    if not ref.startswith("#/"):
        raise LoomError(f"Unsupported $ref: {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _validate(value, schema: dict, root: dict, path: str, errors: list[str]) -> None:
    if "$ref" in schema:
        _validate(value, _resolve(schema["$ref"], root), root, path, errors)
        return

    if "anyOf" in schema:
        if not any(not _collect(value, s, root, path) for s in schema["anyOf"]):
            errors.append(f"{path}: does not match any allowed shape")
    if "oneOf" in schema:
        matches = sum(1 for s in schema["oneOf"] if not _collect(value, s, root, path))
        if matches != 1:
            errors.append(f"{path}: must match exactly one allowed shape (matched {matches})")

    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_is_type(value, x) for x in types):
            errors.append(f"{path}: expected {'|'.join(types)}, got {type(value).__name__}")
            return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: {value!r} does not match /{schema['pattern']}/")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if "items" in schema:
            for i, item in enumerate(value):
                _validate(item, schema["items"], root, f"{path}[{i}]", errors)

    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required '{key}'")
        props = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        for key, sub in value.items():
            child = f"{path}.{key}"
            matched = False
            if key in props:
                _validate(sub, props[key], root, child, errors)
                matched = True
            for pat, psub in patterns.items():
                if re.search(pat, key):
                    _validate(sub, psub, root, child, errors)
                    matched = True
            if not matched:
                extra = schema.get("additionalProperties", True)
                if extra is False:
                    errors.append(f"{child}: unexpected property")
                elif isinstance(extra, dict):
                    _validate(sub, extra, root, child, errors)


def _collect(value, schema, root, path) -> list[str]:
    errs: list[str] = []
    _validate(value, schema, root, path, errs)
    return errs


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    path = SCHEMAS_DIR / f"{name}.schema.json"
    if not path.exists():
        raise LoomError(f"Schema not found: {path}")
    return json.loads(path.read_text())


def validate(data, name: str) -> list[str]:
    schema = load_schema(name)
    return _collect(data, schema, schema, "$")


def validate_file(path: Path, name: str) -> list[str]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError:
        return [f"missing file {path}"]
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    return validate(data, name)
