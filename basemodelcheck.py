import json
import subprocess
import difflib
import re

MODEL = "phi3:mini"
DATASET_PATH = "datafortraining/llama_training.jsonl"
MAX_TESTS = 5

# ---------------------------------------
# Call Ollama model
# ---------------------------------------
def query_model(instruction, user_input):
    prompt = f"{instruction}\n\n{user_input}"
    result = subprocess.run(
        ["ollama", "run", MODEL],
        input=prompt.encode("utf-8"),
        stdout=subprocess.PIPE
    )
    return result.stdout.decode("utf-8").strip()

# ---------------------------------------
# Extract JSON from model output
# ---------------------------------------
def extract_json(text):
    try:
        # Remove markdown fences if present
        cleaned = re.sub(r"```json|```", "", text).strip()
        return json.loads(cleaned)
    except:
        return None

# ---------------------------------------
# Validate schema (not exact match)
# ---------------------------------------
def validate_schema(expected_json, model_json):
    if model_json is None:
        return False, "Model did not return valid JSON"

    required_keys = ["intent_type", "intent_sub_type", "intent_action", "parameters"]

    missing = [k for k in required_keys if k not in expected_json]
    if missing:
        return False, f"Expected JSON missing keys: {missing}"

    # Check required keys exist in model output
    missing_in_model = [k for k in required_keys if k not in model_json]
    if missing_in_model:
        return False, f"Model JSON missing keys: {missing_in_model}"

    return True, None

# ---------------------------------------
# Main test loop
# ---------------------------------------
def test_dataset():
    passed = 0
    failed = 0

    with open(DATASET_PATH, "r") as f:
        for i, line in enumerate(f):
            if MAX_TESTS and i >= MAX_TESTS:
                break

            entry = json.loads(line)
            instruction = entry["instruction"]
            user_input = entry["input"]
            expected_output = entry["output"]

            print(f"\n=== TEST {i+1} ===")
            print("Input:", user_input)

            model_output = query_model(instruction, user_input)
            model_json = extract_json(model_output)
            expected_json = json.loads(expected_output)

            ok, error = validate_schema(expected_json, model_json)

            if ok:
                print("✔ PASS (schema matched)")
                passed += 1
            else:
                print("✖ FAIL")
                failed += 1
                print("Reason:", error)
                print("\n--- RAW MODEL OUTPUT ---")
                print(model_output)

    print("\n==============================")
    print("TEST SUMMARY")
    print("==============================")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print("==============================")

if __name__ == "__main__":
    test_dataset()
