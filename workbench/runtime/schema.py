"""Validate the bundled JSON Schema subset without a third-party dependency.

Only the keywords used by our bundled schemas are implemented. This is not a
general JSON Schema validator and never accepts schemas supplied by a client.
"""
import json
from pathlib import Path


def validate(value, schema, root=None, path="$"):
    root = root or schema
    if "$ref" in schema:
        target = root
        for part in schema["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        return validate(value, target, root, path)
    kinds = schema.get("type", [])
    kinds = [kinds] if isinstance(kinds, str) else kinds
    checks = {"object": isinstance(value, dict), "array": isinstance(value, list),
              "string": isinstance(value, str), "integer": type(value) is int,
              "number": type(value) in (int, float), "boolean": type(value) is bool,
              "null": value is None}
    if kinds and not any(checks.get(k, False) for k in kinds):
        raise ValueError(path + ": invalid type")
    if "const" in schema and value != schema["const"]:
        raise ValueError(path + ": invalid constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(path + ": invalid enum value")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        raise ValueError(path + ": too short")
    if type(value) in (int, float) and value < schema.get("minimum", value):
        raise ValueError(path + ": below minimum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                raise ValueError(path + ": missing " + key)
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False and set(value) - set(properties):
            raise ValueError(path + ": unknown properties")
        for key in value.keys() & properties.keys():
            validate(value[key], properties[key], root, path + "." + key)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            raise ValueError(path + ": too few items")
        if schema.get("uniqueItems") and len({json.dumps(x, sort_keys=True, ensure_ascii=False) for x in value}) != len(value):
            raise ValueError(path + ": duplicate items")
        for i, item in enumerate(value):
            validate(item, schema.get("items", {}), root, path + "[" + str(i) + "]")


def bundled_validate(name, value):
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / name).read_text(encoding="utf-8"))
    validate(value, schema)
