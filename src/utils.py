from typing import Optional, Union, Dict, Any
import json
import re


def local_name(value: Optional[Union[str, object]]) -> str:
    if value is None:
        return ""
    text = str(value)
    if "}" in text:
        return text.split("}")[-1]
    if ":" in text:
        return text.split(":")[-1]
    return text


PRIMITIVE_RANGES = {
    "string",
    "integer",
    "float",
    "boolean",
    "date",
    "time",
    "datetime",
    "uri",
}

XSD_TO_LINKML_TYPE_MAP = {
    "string": "string",
    "token": "string",
    "normalizedString": "string",
    "anyURI": "uri",
    "float": "float",
    "double": "float",
    "decimal": "float",
    "integer": "integer",
    "int": "integer",
    "long": "integer",
    "short": "integer",
    "byte": "integer",
    "nonNegativeInteger": "integer",
    "positiveInteger": "integer",
    "unsignedLong": "integer",
    "unsignedInt": "integer",
    "unsignedShort": "integer",
    "unsignedByte": "integer",
    "boolean": "boolean",
    "date": "date",
    "dateTime": "datetime",
    "time": "time",
    "ID": "string",
    "IDREF": "string",
    "IDREFS": "string",
}

JSON_TO_LINKML_TYPE_MAP = {
    "string": "string",
    "integer": "integer",
    "number": "float",
    "boolean": "boolean",
    "object": "string",
    "array": "string"
}


def map_xsd_primitive(xsd_type) -> str:
    if xsd_type is None:
        return "string"
    
    type_name = None
    if hasattr(xsd_type, "name") and xsd_type.name:
        type_name = local_name(xsd_type.name)
    elif isinstance(xsd_type, str):
        type_name = local_name(xsd_type)
    elif hasattr(xsd_type, "base_type") and xsd_type.base_type is not None:
        return map_xsd_primitive(xsd_type.base_type)
    
    if not type_name:
        return "string"
    
    if type_name in XSD_TO_LINKML_TYPE_MAP:
        return XSD_TO_LINKML_TYPE_MAP[type_name]
    
    base_type = getattr(xsd_type, "base_type", None)
    if base_type is not None and base_type is not xsd_type:
        mapped = map_xsd_primitive(base_type)
        if mapped:
            return mapped
    
    return "string"


def map_json_type_to_linkml_type(json_type: str) -> str:
    return JSON_TO_LINKML_TYPE_MAP.get(json_type, "object")


def derive_range_from_json_schema(prop_schema: Dict) -> Optional[str]:
    if not isinstance(prop_schema, dict):
        return None
    
    if "$ref" in prop_schema:
        return prop_schema["$ref"].split("/")[-1]
    
    if "allOf" in prop_schema:
        for candidate in prop_schema.get("allOf", []):
            rng = derive_range_from_json_schema(candidate)
            if rng:
                return rng
    
    prop_type = prop_schema.get("type")
    if prop_type == "array":
        items = prop_schema.get("items", {})
        return derive_range_from_json_schema(items)
    
    if prop_type == "object":
        return None
    
    return map_json_type_to_linkml_type(prop_type)


def extract_text(obj: Any) -> str:
    if hasattr(obj, 'tag') and hasattr(obj, 'text'):
        return (obj.text or "").strip()
    
    if isinstance(obj, str):
        return obj.strip()
    
    if isinstance(obj, dict):
        return json.dumps(obj, ensure_ascii=False)
    
    if isinstance(obj, (list, tuple)):
        parts = []
        for item in obj:
            parts.append(extract_text(item))
        return "\n".join([p for p in parts if p])
    
    return str(obj)


def ensure_serializable(value: Any) -> Any:
    if value is None:
        return ""
    
    if hasattr(value, 'tag') and hasattr(value, 'text'):
        return value.text.strip() if value.text else ""
    
    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
        return value
    
    return str(value)


def ensure_schema_serializable(schema: Any) -> Any:
    if isinstance(schema, dict):
        return {k: ensure_schema_serializable(v) for k, v in schema.items() if v is not None}
    elif isinstance(schema, list):
        return [ensure_schema_serializable(item) for item in schema]
    else:
        return ensure_serializable(schema)


def sanitize_enum_name(class_name: str, attr_name: str) -> str:
    base = f"Enum_{class_name}_{attr_name}"
    return re.sub(r"[^A-Za-z0-9_]+", "_", base)

