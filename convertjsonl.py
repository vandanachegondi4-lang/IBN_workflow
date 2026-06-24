import json

INPUT_PATH = "datafortraining/intent_dataset.json"
OUTPUT_PATH = "datafortraining/llama_training.jsonl"

INSTRUCTION = "Convert the following natural language intent into structured JSON."

def to_jsonl(entry):
    nl = entry["natural_language"]

    output_obj = {
        "intent_type": entry["intent_type"],
        "intent_sub_type": entry["intent_sub_type"],
        "intent_action": entry["intent_action"],
        "parameters": entry["parameters"]
    }

    return {
        "instruction": INSTRUCTION,
        "input": nl,
        "output": json.dumps(output_obj, indent=2)
    }

with open(INPUT_PATH) as f:
    dataset = json.load(f)

with open(OUTPUT_PATH, "w") as f:
    for entry in dataset:
        f.write(json.dumps(to_jsonl(entry)) + "\n")
