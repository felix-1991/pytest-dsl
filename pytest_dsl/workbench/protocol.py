"""Protocol helpers shared by pytest-dsl workbench integrations."""

import json


GUI_EVENT_PREFIX = "__PYTEST_DSL_GUI_EVENT__"
PROTOCOL_VERSION = 1


def emit_event(payload) -> None:
    print(
        GUI_EVENT_PREFIX + json.dumps(payload, ensure_ascii=False),
        flush=True,
    )


def capabilities_payload():
    return {
        "protocol": PROTOCOL_VERSION,
        "commands": ["syntax", "debug", "capabilities"],
        "features": {
            "pauseFromLine": True,
            "selectionMaterialization": True,
            "stdinDebugCommands": True,
            "structuredDebugEvents": True,
            "yamlVars": True,
        },
    }
