import json
import random
import uuid
import re

# ---------------------------------------------------------
# Load JSON files
# ---------------------------------------------------------
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

INTENT_TEMPLATES = load_json("datafortraining/intent_template.json")
POLICY_TEMPLATES = load_json("datafortraining/policy_template.json")

# ---------------------------------------------------------
# Platform → Capability Mapping
# ---------------------------------------------------------
PLATFORM_CAPABILITIES = {
    "HIOS": [
        "system_mgmt", "user_mgmt", "interface", "vlan", "mac_table",
        "port_security", "qos", "acl", "traffic_control", "lldp",
        "lldp_med", "spanning_tree", "lacp", "mrp", "hsr_prp",
        "routing", "dhcp", "dns", "sntp", "syslog", "snmp",
        "igmp_mld", "dhcp_snooping", "arp_inspection",
        "industrial_protocols", "monitoring", "poe",
        "firmware_file_mgmt", "usb_sd", "config_mgmt"
    ],

    "HIEOS": [
        "system_mgmt", "user_mgmt", "interface", "vlan", "mac_table",
        "port_security", "qos", "lldp", "lldp_med", "spanning_tree",
        "lacp", "routing", "dhcp", "dns", "syslog", "snmp",
        "monitoring", "poe", "firmware_file_mgmt", "config_mgmt"
    ],

    "CLASSIC": [
        "system_mgmt", "user_mgmt", "interface", "vlan",
        "lldp", "spanning_tree", "routing", "dhcp",
        "dns", "syslog", "snmp"
    ],

    "raspberrypi": [
        "system_mgmt", "user_mgmt",
        "vlan",
        "lldp",
        "snmp",
        "monitoring"
    ],

    "edge": [
        "system_mgmt", "monitoring"
    ],

    "bat": [
        "system_mgmt"
    ]
}

# ---------------------------------------------------------
# Platform-specific parameter constraints
# ---------------------------------------------------------
PLATFORM_PARAMETER_CONSTRAINTS = {
    "HIOS": {
        "port_range": [f"1/{i}" for i in range(1, 25)],
        "mtu_range": (576, 9000),
        "qos_supported": True,
        "poe_supported": True,
        "lldp_med_supported": True
    },

    "HIEOS": {
        "port_range": [f"1/{i}" for i in range(1, 17)],
        "mtu_range": (576, 9000),
        "qos_supported": True,
        "poe_supported": True,
        "lldp_med_supported": True
    },

    "CLASSIC": {
        "port_range": [f"1/{i}" for i in range(1, 9)],
        "mtu_range": (576, 1500),
        "qos_supported": False,
        "poe_supported": False,
        "lldp_med_supported": False
    },

    "raspberrypi": {
        "port_range": ["eth0", "wlan0"],
        "mtu_range": (576, 1500),
        "qos_supported": False,
        "poe_supported": False,
        "lldp_med_supported": False
    },

    "edge": {
        "port_range": ["1/1"],
        "mtu_range": (576, 1500),
        "qos_supported": False,
        "poe_supported": False,
        "lldp_med_supported": False
    },

    "bat": {
        "port_range": ["1/1"],
        "mtu_range": (576, 1500),
        "qos_supported": False,
        "poe_supported": False,
        "lldp_med_supported": False
    }
}

# ---------------------------------------------------------
# Load devices
# ---------------------------------------------------------
def load_devices(path="datafortraining/devices_list.json"):
    with open(path, "r") as f:
        data = json.load(f)

    devices = {}
    for platform, devs in data.items():
        for dev_name, info in devs.items():

            if isinstance(info, str):
                info = {"ip": info, "ports": ["1/1"]}

            raw_ports = info.get("ports", [])
            if isinstance(raw_ports, str):
                raw_ports = [raw_ports]

            ports = [p for p in raw_ports if isinstance(p, str)]
            if not ports:
                ports = ["1/1"]

            devices[dev_name] = {
                "platform": platform,
                "ip": info.get("ip", "0.0.0.0"),
                "ports": ports
            }

    return devices

# ---------------------------------------------------------
# Action verbs
# ---------------------------------------------------------
VERBS = {
    "allow": ["configure", "enable", "set", "apply", "allow", "assign", "activate"],
    "deny": ["deny", "block", "disable", "remove", "clear", "reset", "deactivate"],
    "get": ["show", "display", "retrieve", "get", "fetch"]
}

# ---------------------------------------------------------
# Noise injection
# ---------------------------------------------------------
NOISE_PREFIX = [
    "just to be clear,",
    "by the way,",
    "as far as I know,",
    "for this setup,",
    "if I understand correctly,"
]

NOISE_MID = ["basically", "sort of", "kind of", "technically", "somehow"]
NOISE_TRAIL = ["if possible", "when you get a chance", "as soon as you can", "whenever that works"]
NOISE_REDUNDANT = ["go ahead and", "please make sure to", "you can just", "go on and"]
NOISE_CONTEXT = ["for the maintenance window,", "as per earlier discussion,", "for the new deployment,"]

def inject_noise(sentence):
    r = random.random()
    if r < 0.20:
        return f"{random.choice(NOISE_PREFIX)} {sentence}"
    if r < 0.35:
        parts = sentence.split(" ", 1)
        if len(parts) > 1:
            return f"{parts[0]} {random.choice(NOISE_MID)} {parts[1]}"
        return sentence
    if r < 0.55:
        return f"{sentence}, {random.choice(NOISE_TRAIL)}"
    if r < 0.65:
        return f"{random.choice(NOISE_REDUNDANT)} {sentence}"
    if r < 0.75:
        return f"{random.choice(NOISE_CONTEXT)} {sentence}"
    if r < 0.85:
        return sentence.replace(" ", "  ")
    return sentence

# ---------------------------------------------------------
# Placeholder value generator
# ---------------------------------------------------------
VLAN_NAMES = ["office", "iot", "guest", "camera", "prod", "dev", "lab"]
TAG_MODES = ["tagged", "untagged"]

def generate_value(param):
    if param == "vlan_id":
        return random.randint(1, 4094)
    if param == "vlan_name":
        return random.choice(VLAN_NAMES)
    if param == "tagging_mode":
        return random.choice(TAG_MODES)

    if param in ["ip_address", "netmask", "gateway", "dns_server", "syslog_server", "sntp_server", "server_ip"]:
        return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    if param == "destination":
        return random.choice(["usb", "tftp://10.0.0.1", "/flash/configs"])
    if param == "source":
        return random.choice(["default", "manual", "static"])

    if param == "hostname":
        return f"sw-{random.randint(1, 999)}"
    if param == "timezone":
        return random.choice(["UTC", "CET", "EST", "PST"])
    if param == "service_name":
        return random.choice(["ssh", "telnet", "http", "https", "snmp"])

    if param == "username":
        return f"user{random.randint(1, 999)}"
    if param == "role":
        return random.choice(["admin", "operator", "guest", "read-only"])

    if param == "speed":
        return random.choice(["10", "100", "1000", "2500", "10000"])
    if param == "operating_mode":
        return random.choice(["full", "half", "auto"])
    if param == "mtu":
        return random.randint(576, 9000)
    if param == "description":
        return random.choice(["uplink", "camera", "sensor", "server", "client"])

    if param == "macaddress":
        return "02:00:%02x:%02x:%02x:%02x" % tuple(random.randint(0, 255) for _ in range(4))
    if param == "aging_time":
        return random.randint(60, 100000)
    if param == "limit":
        return random.randint(1, 64)
    if param == "violation_action":
        return random.choice(["shutdown", "restrict", "protect"])

    if param == "qnumber":
        return random.randint(0, 7)
    if param == "min_bandwidth":
        return random.randint(1, 100000)
    if param == "dscp":
        return random.randint(0, 63)
    if param == "rate":
        return random.randint(1, 1000000)

    if param == "lag_id":
        return random.randint(1, 64)
    if param == "ring_id":
        return random.randint(1, 64)
    if param == "protocol":
        return random.choice(["hsr", "prp"])
    if param == "priority":
        return random.choice([0, 4096, 8192, 16384, 32768, 61440])

    if param == "pool_name":
        return random.choice(["office_pool", "iot_pool", "guest_pool"])

    if param == "community":
        return random.choice(["public", "private", "monitor"])

    if param == "image_name":
        return random.choice(["imageA", "imageB", "hios-10.3", "hios-9.4"])
    if param == "image_slot":
        return random.choice(["primary", "secondary"])
    if param == "filename":
        return random.choice(["config.cfg", "backup.cfg", "startup.cfg"])

    if param == "policy_name":
        return random.choice(["voice", "video", "data"])
    if param == "tlv_type":
        return random.choice([
            "port-description", "system-name", "system-description",
            "system-capabilities", "management-address"
        ])

    if param == "power":
        return random.randint(5, 30)

    if param == "source_port":
        return f"1/{random.randint(1, 24)}"
    if param == "destination_port":
        return f"1/{random.randint(1, 24)}"

    if param == "null_scan_filter":
        return random.choice(["enable", "disable"])

    if param == "name":
        return random.choice(["rule10", "block_camera", "allow_iot", "deny_guest", "acl_001"])

    return f"{param}_{random.randint(1,999)}"

# ---------------------------------------------------------
# Intent Generator
# ---------------------------------------------------------
class IntentGenerator:
    def __init__(self, devices):
        self.devices = devices

    def _pick_device_and_port(self):
        device = random.choice(list(self.devices.keys()))
        ports = self.devices[device]["ports"]
        return device, random.choice(ports)

    def generate_intent(self):
        device, port = self._pick_device_and_port()
        platform = self.devices[device]["platform"]

        # PLATFORM-AWARE INTENT TYPE SELECTION
        allowed_intents = PLATFORM_CAPABILITIES[platform]
        intent_type = random.choice(allowed_intents)

        # SUB-INTENT SELECTION (no extra filtering here)
        sub_intent_type = random.choice(list(INTENT_TEMPLATES[intent_type].keys()))

        # ACTION SELECTION
        actions_dict = INTENT_TEMPLATES[intent_type][sub_intent_type]
        valid_actions = [a for a, t in actions_dict.items() if t]

        if not valid_actions:
            action = random.choice(list(actions_dict.keys()))
            template = "{action} " + intent_type
            policy = POLICY_TEMPLATES[intent_type][sub_intent_type][action]
        else:
            action = random.choice(valid_actions)
            template = random.choice(actions_dict[action])
            policy = POLICY_TEMPLATES[intent_type][sub_intent_type][action]

        action_word = random.choice(VERBS.get(action, ["do"]))

        # PARAMETER GENERATION
        parameters = {
            "device": device,
            "platform": platform
        }

        if "port" in policy["required_parameters"] or "{port}" in template:
            parameters["port"] = port

        for req in policy["required_parameters"]:
            if req not in parameters:
                parameters[req] = generate_value(req)

        for opt in policy["optional_parameters"]:
            if "{" + opt + "}" in template:
                parameters[opt] = generate_value(opt)

        placeholders = re.findall(r"{(.*?)}", template)
        for ph in placeholders:
            if ph == "action":
                continue
            if ph not in parameters:
                parameters[ph] = generate_value(ph)

        # PLATFORM-SPECIFIC PARAMETER ENFORCEMENT
        rules = PLATFORM_PARAMETER_CONSTRAINTS[platform]

        if "port" in parameters:
            parameters["port"] = random.choice(rules["port_range"])

        if "mtu" in parameters:
            lo, hi = rules["mtu_range"]
            parameters["mtu"] = random.randint(lo, hi)

        if not rules["qos_supported"]:
            for p in ["qnumber", "min_bandwidth", "dscp", "rate"]:
                parameters.pop(p, None)

        if not rules["poe_supported"]:
            parameters.pop("power", None)

        if not rules["lldp_med_supported"]:
            for p in ["policy_name", "tlv_type"]:
                parameters.pop(p, None)

        # REMOVE PARAMETERS NOT IN POLICY
        required = policy["required_parameters"]
        optional = policy["optional_parameters"]
        allowed = set(required + optional + ["device", "platform", "port"])

        for p in list(parameters.keys()):
            if p not in allowed:
                parameters.pop(p)

        # CLEAN TEMPLATE
        for ph in ["tlv_type", "policy_name"]:
            if ph not in parameters:
                template = template.replace("{" + ph + "}", "")

        natural = inject_noise(template.format(action=action_word, **parameters))

        return {
            "uid": str(uuid.uuid4()),
            "natural_language": natural,
            "intent_type": intent_type,
            "intent_sub_type": sub_intent_type,
            "intent_action": action,
            "intent_name": f"{intent_type}_{sub_intent_type}_{action}",
            "parameters": parameters,
            "policy": policy
        }

# ---------------------------------------------------------
# Main
# ---------------------------------------------------------
if __name__ == "__main__":
    devices = load_devices("datafortraining/devices_list.json")
    generator = IntentGenerator(devices)

    N = 5000
    dataset = [generator.generate_intent() for _ in range(N)]

    with open("datafortraining/intent_dataset.json", "w") as f:
        json.dump(dataset, f, indent=4)

    print(f"Dataset saved with {N} samples.")
