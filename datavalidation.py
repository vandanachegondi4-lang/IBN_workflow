import json
import re

# -----------------------------
# Helper to load JSON
# -----------------------------
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

# -----------------------------
# Load dataset + policy + devices
# -----------------------------
dataset = load_json("datafortraining/intent_dataset.json")
policy_templates = load_json("datafortraining/policy_template.json")
devices_list = load_json("datafortraining/devices_list.json")

# -----------------------------
# Build device → ports map (supports your JSON format)
# -----------------------------
devices = {}
for platform, devs in devices_list.items():
    for dev, info in devs.items():

        # Convert "192.168.x.x" → {"ip": "...", "ports": ["1/1"]}
        if isinstance(info, str):
            info = {"ip": info, "ports": ["1/1"]}

        raw_ports = info.get("ports", [])
        if isinstance(raw_ports, str):
            raw_ports = [raw_ports]

        ports = [p for p in raw_ports if isinstance(p, str)]
        if not ports:
            ports = ["1/1"]

        devices[dev] = {
            "platform": platform,
            "ports": ports
        }

# -----------------------------
# Platform‑specific verb rules
# -----------------------------
PLATFORM_VERBS = {
    "HIOS": {
        "allow": ["configure", "enable", "set", "apply", "allow"],
        "deny": ["disable", "remove", "clear", "reset"],
        "get": ["show", "display", "retrieve", "get", "fetch"]
    },
    "HIEOS": {
        "allow": ["set", "enable", "configure"],
        "deny": ["disable", "delete"],
        "get": ["show", "get"]
    },
    "CLASSIC": {
        "allow": ["set", "enable"],
        "deny": ["disable", "clear"],
        "get": ["show"]
    },
    "raspberrypi": {
        "allow": ["sudo", "apply", "set"],
        "deny": ["sudo", "remove"],
        "get": ["sudo", "check"]
    },
    "edge": {
        "allow": ["configure"],
        "deny": ["disable"],
        "get": ["show"]
    },
    "bat": {
        "allow": ["configure"],
        "deny": ["disable"],
        "get": ["show"]
    }
}

# -----------------------------
# VLAN rules
# -----------------------------
VALID_TAG_MODES = ["tagged", "untagged"]
VALID_VLAN_NAMES = ["office", "iot", "guest", "camera", "prod", "dev", "lab"]

# -----------------------------
# CHECK FUNCTIONS
# -----------------------------
def check_natural_language(entry):
    nl = entry["natural_language"]
    if not isinstance(nl, str) or len(nl.strip()) < 5:
        return "FAIL", "Natural language too short or invalid"
    if "{" in nl or "}" in nl:
        return "FAIL", "Unresolved placeholder found"
    return "PASS", "Sentence is well‑formed"

def check_verb(entry):
    nl = entry["natural_language"].lower().strip()
    action = entry["intent_action"]
    platform = entry["parameters"]["platform"]

    first_word = nl.split()[0]

    valid_verbs = PLATFORM_VERBS.get(platform, {}).get(action, [])

    if first_word not in valid_verbs:
        return "FAIL", f"Verb '{first_word}' invalid for action '{action}' on platform '{platform}'"

    return "PASS", f"Verb '{first_word}' valid for platform '{platform}'"

def check_tagging_mode(entry):
    params = entry["parameters"]
    if "tagging_mode" not in params:
        return "SKIPPED", "tagging_mode not present"
    if params["tagging_mode"] not in VALID_TAG_MODES:
        return "FAIL", f"Invalid tagging_mode '{params['tagging_mode']}'"
    return "PASS", "tagging_mode valid"

def check_vlan_name(entry):
    params = entry["parameters"]
    if "vlan_name" not in params:
        return "SKIPPED", "vlan_name not present"
    if params["vlan_name"] not in VALID_VLAN_NAMES:
        return "FAIL", f"Invalid vlan_name '{params['vlan_name']}'"
    return "PASS", "vlan_name valid"

def check_required_parameters(entry):
    intent = entry["intent_type"]
    sub = entry["intent_sub_type"]
    action = entry["intent_action"]
    params = entry["parameters"]

    required = policy_templates[intent][sub][action]["required_parameters"]
    missing = [r for r in required if r not in params]

    if missing:
        return "FAIL", f"Missing required parameters: {missing}"
    return "PASS", "All required parameters present"

def check_optional_parameters(entry):
    intent = entry["intent_type"]
    sub = entry["intent_sub_type"]
    action = entry["intent_action"]
    params = entry["parameters"]

    required = policy_templates[intent][sub][action]["required_parameters"]
    optional = policy_templates[intent][sub][action]["optional_parameters"]

    unknown = [
        p for p in params
        if p not in required and p not in optional and p not in ["device", "port", "platform"]
    ]

    if unknown:
        return "FAIL", f"Unexpected parameters: {unknown}"
    return "PASS", "Optional parameters valid"

def check_device(entry):
    dev = entry["parameters"].get("device")
    if dev not in devices:
        return "FAIL", f"Invalid device '{dev}'"
    return "PASS", "Device exists"

def check_port(entry):
    params = entry["parameters"]
    if "port" not in params:
        return "SKIPPED", "port not present"

    dev = params["device"]
    port = params["port"]

    if dev not in devices:
        return "FAIL", f"Device '{dev}' not found"

    if port not in devices[dev]["ports"]:
        return "FAIL", f"Port '{port}' invalid for device '{dev}'"

    return "PASS", "Port valid"

def check_constraints(entry):
    intent = entry["intent_type"]
    sub = entry["intent_sub_type"]
    action = entry["intent_action"]
    params = entry["parameters"]
    constraints = policy_templates[intent][sub][action]["constraints"]

    for p, rule in constraints.items():
        if p not in params:
            continue
        value = params[p]

        if rule == "ipv4":
            if not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", value):
                return "FAIL", f"Invalid IPv4 '{value}'"

        if isinstance(rule, list):
            if value not in rule:
                return "FAIL", f"Value '{value}' not allowed for {p}"

    return "PASS", "Constraints satisfied"

def check_policy_alignment(entry):
    intent = entry["intent_type"]
    sub = entry["intent_sub_type"]
    action = entry["intent_action"]

    if intent not in policy_templates:
        return "FAIL", f"Intent '{intent}' not in policy"

    if sub not in policy_templates[intent]:
        return "FAIL", f"Sub‑intent '{sub}' invalid for '{intent}'"

    if action not in policy_templates[intent][sub]:
        return "FAIL", f"Action '{action}' invalid for {intent}/{sub}"

    return "PASS", "Policy alignment OK"

def check_placeholders(entry):
    nl = entry["natural_language"]
    if "{" in nl or "}" in nl:
        return "FAIL", "Unresolved placeholder found"
    return "PASS", "No unresolved placeholders"

# -----------------------------
# RUN VALIDATION ON ONE EXAMPLE
# -----------------------------
CHECKS = [
    ("Natural Language", check_natural_language),
    ("Verb", check_verb),
    ("Tagging Mode", check_tagging_mode),
    ("VLAN Name", check_vlan_name),
    ("Required Parameters", check_required_parameters),
    ("Optional Parameters", check_optional_parameters),
    ("Device", check_device),
    ("Port", check_port),
    ("Constraints", check_constraints),
    ("Placeholder", check_placeholders),
    ("Policy Alignment", check_policy_alignment),
]

example = dataset[0]

lines = []
lines.append("=== VALIDATION FOR EXAMPLE INTENT ===\n")
lines.append(f"Natural Language: {example['natural_language']}")
lines.append(f"Parameters: {example['parameters']}\n")
lines.append("--------------------------------------\n")

for name, func in CHECKS:
    status, reason = func(example)
    lines.append(f"{name} Check → {status} | {reason}")

# -----------------------------
# WRITE FILE
# -----------------------------
with open("datafortraining/validation_text.txt", "w") as f:
    f.write("\n".join(lines))

print("validation_text.txt created.")
