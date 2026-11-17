"""표준 라이브러리만으로 쓰는 작은 JSON 스키마 검사기(LLM 출력 검증용)."""

_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def check_schema(obj, schema: dict) -> bool:
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](obj) for x in types):
            return False
    if "enum" in schema and obj not in schema["enum"]:
        return False
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if "minimum" in schema and obj < schema["minimum"]:
            return False
        if "maximum" in schema and obj > schema["maximum"]:
            return False
    if isinstance(obj, dict):
        props = schema.get("properties", {})
        if any(k not in obj for k in schema.get("required", [])):
            return False
        if schema.get("additionalProperties") is False and any(k not in props for k in obj):
            return False
        for k, sub in props.items():
            if k in obj and not check_schema(obj[k], sub):
                return False
    if isinstance(obj, list) and "items" in schema:
        if not all(check_schema(x, schema["items"]) for x in obj):
            return False
    return True
