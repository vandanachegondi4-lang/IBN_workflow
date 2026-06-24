import json

# Platform-specific port definitions
PLATFORM_PORTS = {
    "HIOS": [f"1/{i}" for i in range(1, 13)],      # 1/1 → 1/12
    "CLASSIC": [f"1/{i}" for i in range(1, 11)],      # 1/1 → 1/10
    "HIEOS": [f"1/{i}" for i in range(1, 12)],   # 1/1 → 1/11
    "raspberrypi": ["eth0", "wlan0"],
    "edge": [f"1/{i}" for i in range(1, 17)],    # 1/1 → 1/16
    "bat": ["1/1"]
}

INPUT_FILE = "datafortraining/devices_list.json"
OUTPUT_FILE = "datafortraining/devices_list.json"   # overwrite same file


def update_json_with_ports():
    with open(INPUT_FILE, "r") as f:
        data = json.load(f)

    updated = {}

    for platform, devices in data.items():
        updated[platform] = {}

        for dev_name, ip in devices.items():
            ports = PLATFORM_PORTS.get(platform, ["eth0"])

            updated[platform][dev_name] = {
                "ip": ip,
                "ports": ports
            }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(updated, f, indent=4)

    print("✔ devices_list.json updated with ports.")


if __name__ == "__main__":
    update_json_with_ports()
