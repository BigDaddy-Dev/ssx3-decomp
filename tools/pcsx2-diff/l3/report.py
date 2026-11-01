"""The comparison report (markdown) and the trend file (history.jsonl)."""
import json


def _fmt(vals):
    vals = [round(v, 3) if isinstance(v, float) else v for v in vals]
    return str(vals[0]) if len(vals) == 1 else str(vals)


def write_report(path, scenario, commit, divergence, meta):
    lines = [f"# pcsx2-diff: {scenario} @ {commit}", ""]
    for k, v in meta.items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    if divergence is None:
        lines.append("No divergence: every compared race frame matched within tolerance.")
    else:
        lines += [f"**First divergence at race frame {divergence.frame}.**", "",
                  "| field | native | pcsx2 |", "|---|---|---|"]
        for name, (nat, pcs) in divergence.fields.items():
            lines.append(f"| {name} | {_fmt(nat)} | {_fmt(pcs)} |")
    text = "\n".join(lines) + "\n"
    with open(path, "w") as f:
        f.write(text)
    return text


def make_record(commit, scenario, mode, divergence):
    return {"commit": commit, "scenario": scenario, "mode": mode,
            "first_divergence_frame": divergence.frame if divergence else None,
            "fields": sorted(divergence.fields) if divergence else []}


def append_history(path, record):
    with open(path, "a") as f:
        f.write(json.dumps(record) + "\n")
