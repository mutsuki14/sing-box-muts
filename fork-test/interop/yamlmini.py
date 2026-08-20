"""Minimal YAML serializer for controlled mihomo configuration values."""
from __future__ import annotations

import json
from typing import Any


def _scalar(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def dumps(value: Any, indent: int = 0) -> str:
    pad = " " * indent
    if isinstance(value, dict):
        lines = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{key}:")
                lines.append(dumps(item, indent + 2))
            else:
                lines.append(f"{pad}{key}: {_scalar(item)}")
        return "\n".join(lines)
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                first, *rest = list(item.items())
                key, child = first
                if isinstance(child, (dict, list)):
                    lines.append(f"{pad}- {key}:")
                    lines.append(dumps(child, indent + 4))
                else:
                    lines.append(f"{pad}- {key}: {_scalar(child)}")
                for extra_key, extra_value in rest:
                    if isinstance(extra_value, (dict, list)):
                        lines.append(f"{pad}  {extra_key}:")
                        lines.append(dumps(extra_value, indent + 4))
                    else:
                        lines.append(f"{pad}  {extra_key}: {_scalar(extra_value)}")
            elif isinstance(item, list):
                lines.append(f"{pad}-")
                lines.append(dumps(item, indent + 2))
            else:
                lines.append(f"{pad}- {_scalar(item)}")
        return "\n".join(lines)
    return f"{pad}{_scalar(value)}"
