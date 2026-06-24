import json

DATASET_PATH = "datafortraining/intent_dataset.json"
REPORT_PATH = "datafortraining/empty_values_report.txt"

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def check_none_values(dataset):
    report = []
    total_none = 0
    samples_with_none = 0

    report.append("=== NONE VALUE REPORT ===\n")
    report.append(f"Total samples: {len(dataset)}\n\n")

    for entry in dataset:
        uid = entry.get("uid")
        params = entry.get("parameters", {})

        # Find parameters with None
        none_fields = [k for k, v in params.items() if v is None]

        if none_fields:
            samples_with_none += 1
            total_none += len(none_fields)

            report.append(f"UID: {uid}\n")
            report.append(f"  Intent: {entry.get('intent_name')}\n")
            report.append(f"  Natural: {entry.get('natural_language')}\n")
            report.append(f"  None parameters: {none_fields}\n\n")

    report.append("=== SUMMARY ===\n")
    report.append(f"Samples containing None: {samples_with_none}\n")
    report.append(f"Total None values found: {total_none}\n")

    return "".join(report)

def main():
    dataset = load_json(DATASET_PATH)
    report = check_none_values(dataset)

    with open(REPORT_PATH, "w") as f:
        f.write(report)

    print(f"Report written to {REPORT_PATH}")

if __name__ == "__main__":
    main()
