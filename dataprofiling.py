import json
import re
from collections import Counter, defaultdict
from statistics import mean, median, pstdev

DATASET_PATH = "datafortraining/intent_dataset.json"
OUTPUT_PATH = "datafortraining/data_profiling_report.txt"


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def is_ipv4(s):
    if not isinstance(s, str):
        return False
    m = re.match(r"^\d{1,3}(\.\d{1,3}){3}$", s)
    if not m:
        return False
    parts = [int(x) for x in s.split(".")]
    return all(0 <= p <= 255 for p in parts)


def profile_dataset(dataset):
    n = len(dataset)
    lines = []
    lines.append("=== DATA PROFILING REPORT ===\n")
    lines.append(f"Total samples: {n}\n\n")

    # ---------------------------------------------------------
    # 1. Intent / Sub‑Intent / Action Distribution
    # ---------------------------------------------------------
    intent_counter = Counter()
    sub_intent_counter = Counter()
    action_counter = Counter()

    for e in dataset:
        it = e.get("intent_type")
        st = e.get("intent_sub_type")
        ac = e.get("intent_action")
        intent_counter[it] += 1
        sub_intent_counter[(it, st)] += 1
        action_counter[ac] += 1

    lines.append("1) Intent Distribution:\n")
    for it, c in intent_counter.most_common():
        lines.append(f"   {it:25s} {c:6d} ({c/n:.2%})\n")
    lines.append("\n")

    lines.append("2) Sub‑Intent Distribution (Top 20):\n")
    for (it, st), c in sub_intent_counter.most_common(20):
        lines.append(f"   {it:20s} / {st:20s} {c:6d} ({c/n:.2%})\n")
    lines.append("\n")

    lines.append("3) Action Distribution:\n")
    for ac, c in action_counter.most_common():
        lines.append(f"   {ac:10s} {c:6d} ({c/n:.2%})\n")
    lines.append("\n")

    # ---------------------------------------------------------
    # 2. Natural Language Profiling
    # ---------------------------------------------------------
    lengths = []
    unresolved = 0
    noise_detected = 0

    NOISE_WORDS = [
        "basically", "sort of", "kind of", "technically", "somehow",
        "just to be clear", "by the way", "as far as I know",
        "if possible", "when you get a chance"
    ]

    for e in dataset:
        nl = e.get("natural_language", "")
        if not isinstance(nl, str):
            continue
        tokens = nl.split()
        lengths.append(len(tokens))

        if "{" in nl or "}" in nl:
            unresolved += 1

        if any(w in nl.lower() for w in NOISE_WORDS):
            noise_detected += 1

    lines.append("4) Natural Language Profiling:\n")
    lines.append(f"   Avg length: {mean(lengths):.2f} tokens\n")
    lines.append(f"   Median length: {median(lengths):.2f}\n")
    lines.append(f"   Std deviation: {pstdev(lengths):.2f}\n")
    lines.append(f"   Min length: {min(lengths)}\n")
    lines.append(f"   Max length: {max(lengths)}\n")
    lines.append(f"   Unresolved placeholders: {unresolved} ({unresolved/n:.2%})\n")
    lines.append(f"   Noise‑injected sentences: {noise_detected} ({noise_detected/n:.2%})\n\n")

    # ---------------------------------------------------------
    # 3. Parameter Profiling
    # ---------------------------------------------------------
    param_counter = Counter()
    param_type_counter = defaultdict(Counter)
    ipv4_counter = Counter()
    numeric_ranges = defaultdict(list)

    for e in dataset:
        params = e.get("parameters", {})
        for k, v in params.items():
            param_counter[k] += 1
            param_type_counter[k][type(v).__name__] += 1

            if is_ipv4(v):
                ipv4_counter[k] += 1

            if isinstance(v, int):
                numeric_ranges[k].append(v)

    lines.append("5) Parameter Frequency (Top 30):\n")
    for k, c in param_counter.most_common(30):
        lines.append(f"   {k:20s} {c:6d} ({c/n:.2%}) types={dict(param_type_counter[k])}\n")
    lines.append("\n")

    lines.append("6) IPv4‑like Parameters:\n")
    for k, c in ipv4_counter.most_common():
        lines.append(f"   {k:20s} {c:6d} ({c/n:.2%})\n")
    lines.append("\n")

    lines.append("7) Numeric Parameter Ranges:\n")
    for k, values in numeric_ranges.items():
        if len(values) < 5:
            continue
        lines.append(f"   {k:20s} min={min(values)} max={max(values)} mean={mean(values):.2f}\n")
    lines.append("\n")

    # ---------------------------------------------------------
    # 4. Duplicate Detection
    # ---------------------------------------------------------
    nl_counter = Counter(e.get("natural_language", "") for e in dataset)
    dup_sentences = sum(1 for _, c in nl_counter.items() if c > 1)
    max_dup = max(nl_counter.values()) if nl_counter else 0

    lines.append("8) Duplicate Analysis:\n")
    lines.append(f"   Unique NL sentences: {len(nl_counter)}\n")
    lines.append(f"   Sentences with duplicates: {dup_sentences}\n")
    lines.append(f"   Max duplicates for a single sentence: {max_dup}\n\n")

    # ---------------------------------------------------------
    # 5. Outlier Detection
    # ---------------------------------------------------------
    outliers = [l for l in lengths if l > mean(lengths) + 3 * pstdev(lengths)]
    lines.append("9) Outlier Detection:\n")
    lines.append(f"   Outlier sentences (>3σ): {len(outliers)}\n\n")

    lines.append("=== END OF DATA PROFILING REPORT ===\n")

    return "".join(lines)


def main():
    dataset = load_json(DATASET_PATH)
    report = profile_dataset(dataset)

    with open(OUTPUT_PATH, "w") as f:
        f.write(report)

    print(f"Data profiling report written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
