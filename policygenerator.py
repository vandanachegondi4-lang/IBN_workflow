import json
import re

# ---------------------------------------------------------
# Load intent templates (hierarchical: type → sub → action)
# ---------------------------------------------------------
with open("datafortraining/intent_template.json") as f:
    templates = json.load(f)

# ---------------------------------------------------------
# Full constraint dictionary for ALL placeholders
# ---------------------------------------------------------
CONSTRAINTS = {
    # Device / Port
    "port": "string-or-port-range",

    # VLAN
    "vlan_id": "1-4094",
    "vlan_name": "string",
    "tagging_mode": ["tagged", "untagged"],
    "pvid": "1-4094",

    # IP addressing
    "ip_address": "ipv4",
    "netmask": "ipv4",
    "gateway": "ipv4",
    "dns_server": "ipv4",
    "syslog_server": "ipv4",
    "sntp_server": "ipv4",
    "server_ip": "ipv4",
    "destination": "ipv4-or-subnet",
    "source": "string-or-ip",

    # System
    "hostname": "string",
    "timezone": "string",
    "service_name": "string",

    # User management
    "username": "string",
    "role": ["admin", "operator", "guest", "read-only"],

    # Interface
    "speed": ["10", "100", "1000", "2500", "10000"],
    "operating_mode": ["full", "half", "auto"],
    "mtu": "1-9216",
    "description": "string",

    # MAC / Security
    "macaddress": "mac",
    "aging_time": "1-100000",
    "limit": "1-1024",
    "violation_action": ["shutdown", "restrict", "protect"],

    # QoS
    "qnumber": "0-7",
    "min_bandwidth": "1-100000",
    "dscp": "0-63",
    "rate": "1-1000000",

    # LACP / MRP / HSR / PRP
    "lag_id": "1-64",
    "ring_id": "1-64",
    "protocol": ["hsr", "prp"],
    "priority": "0-61440",

    # DHCP
    "pool_name": "string",

    # SNMP
    "community": "string",

    # Firmware / Files
    "image_name": "string",
    "image_slot": ["primary", "secondary"],
    "filename": "string",
    "destination": "string-or-path",

    # LLDP-MED
    "policy_name": "string",

    # PoE
    "power": "1-300",

    # Monitoring
    "source_port": "string-or-port-range",
    "destination_port": "string-or-port-range",

    # Traffic control
    "null_scan_filter": ["enable", "disable"],

    # Network load control
    "vlanid": "1-4094"
}

# ---------------------------------------------------------
# Extract placeholders from template string
# ---------------------------------------------------------
def extract_placeholders(template_str):
    return set(re.findall(r"{(.*?)}", template_str))


# ---------------------------------------------------------
# Build policy for one allow/deny/get group
# ---------------------------------------------------------
def build_policy_for_action(action_templates):
    per_template_placeholders = []

    for t in action_templates:
        per_template_placeholders.append(extract_placeholders(t))

    # Union: appears in at least one template
    all_placeholders = set().union(*per_template_placeholders)

    # Intersection: appears in every template
    common_placeholders = set(per_template_placeholders[0])
    for phs in per_template_placeholders[1:]:
        common_placeholders &= phs

    # Remove {action}
    all_placeholders.discard("action")
    common_placeholders.discard("action")

    required = []
    optional = []

    # device required only if used
    if "device" in all_placeholders:
        required.append("device")

    #  platform ALWAYS required
    if "platform" not in required:
        required.append("platform")

   # Correct port logic
    if "port" in common_placeholders:
        required.append("port")
    elif "port" in all_placeholders:
    # Only optional if THIS action’s templates use {port}
      if any("port" in phs for phs in per_template_placeholders):
        optional.append("port")


    # Everything else
    for p in sorted(all_placeholders):
        if p in ["device", "port"]:
            continue
        if p in common_placeholders:
            required.append(p)
        else:
            optional.append(p)

    # Apply constraints
    constraints = {
        p: CONSTRAINTS[p]
        for p in all_placeholders
        if p in CONSTRAINTS
    }

    return {
        "required_parameters": required,
        "optional_parameters": optional,
        "constraints": constraints
    }


# ---------------------------------------------------------
# Build full hierarchical policy template
# ---------------------------------------------------------
policy = {}

for intent_type, sub_intents in templates.items():
    policy[intent_type] = {}

    for sub_intent_type, actions in sub_intents.items():
        policy[intent_type][sub_intent_type] = {}

        for action, action_templates in actions.items():

            # Handle empty allow/deny/get groups safely
            if not action_templates:
                policy[intent_type][sub_intent_type][action] = {
                    "required_parameters": ["platform"],
                    "optional_parameters": [],
                    "constraints": {}
                }
                continue

            # Normal case
            policy[intent_type][sub_intent_type][action] = build_policy_for_action(action_templates)


# ---------------------------------------------------------
# Save output
# ---------------------------------------------------------
with open("datafortraining/policy_template.json", "w") as f:
    json.dump(policy, f, indent=4)

print("Auto-generated policy_template.json created successfully.")
