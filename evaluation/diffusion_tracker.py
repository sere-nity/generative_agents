"""
diffusion_tracker.py

Tracks information diffusion across a simulation run.
Specifically: when does each agent first become aware of the Valentine's Day party?

Two detection methods:
  1. chat field — agent mentions party in a conversation transcript
  2. description field — agent's action description references the party
     (catches awareness even when no new chat is recorded)

Output: diffusion_report.json

Usage:
    python3 diffusion_tracker.py <sim_code>
    python3 diffusion_tracker.py July1_the_ville_isabella_maria_Klaus-step-3-20
"""

import json
import os
import sys

from sim_loader import load_movements, get_persona_names, STORAGE

AWARENESS_KEYWORDS = [
    "valentine", "party", "hobbs cafe party", "valentine's day",
    "feb 14", "february 14", "5pm", "celebration"
]


def _mentions_party(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in AWARENESS_KEYWORDS)


def track_diffusion(final_sim_code: str) -> dict:
    """
    Returns:
    {
        "first_awareness": {
            "Isabella Rodriguez": {"step": 0, "sim_time": "...", "method": "initiator"},
            "Klaus Mueller": {"step": 4095, "sim_time": "...", "method": "chat"},
            ...
        },
        "diffusion_timeline": [
            {"step": int, "sim_time": str, "newly_aware": [str], "total_aware": int,
             "pct_aware": float},
            ...
        ],
        "transmission_graph": [
            {"from": str, "to": str, "step": int, "sim_time": str}
        ]
    }
    """
    steps = load_movements(final_sim_code)
    persona_names = get_persona_names(final_sim_code)
    n_agents = len(persona_names)

    first_awareness = {}
    transmission_graph = []
    diffusion_timeline = []
    prev_aware_count = 0

    seen_chat_keys = set()

    for step_data in steps:
        step = step_data["step"]
        sim_time = step_data["sim_time"]
        newly_aware = []

        for persona, info in step_data["personas"].items():
            chat = info.get("chat")
            if chat:
                key = str(chat[0])
                # Mark initiator as aware from the first step of the conversation
                initiator = chat[0][0]
                if initiator not in first_awareness and _mentions_party(" ".join(u[1] for u in chat)):
                    first_awareness[initiator] = {
                        "step": step, "sim_time": sim_time, "method": "initiator"
                    }
                    newly_aware.append(initiator)

                # Mark non-initiators as learning via chat (deduplicated)
                if key not in seen_chat_keys:
                    seen_chat_keys.add(key)
                    full_text = " ".join(u[1] for u in chat)
                    if _mentions_party(full_text):
                        speakers = list({u[0] for u in chat})
                        teller = next((s for s in speakers if s in first_awareness), None)
                        for speaker in speakers:
                            if speaker not in first_awareness:
                                first_awareness[speaker] = {
                                    "step": step, "sim_time": sim_time, "method": "chat"
                                }
                                newly_aware.append(speaker)
                                if teller:
                                    transmission_graph.append({
                                        "from": teller, "to": speaker,
                                        "step": step, "sim_time": sim_time
                                    })

            if persona in first_awareness:
                continue

            # Method 2: check description
            if persona not in first_awareness:
                desc = info.get("description", "")
                if _mentions_party(desc):
                    first_awareness[persona] = {
                        "step": step, "sim_time": sim_time, "method": "description"
                    }
                    newly_aware.append(persona)

        # Record timeline snapshot whenever awareness changes
        if len(first_awareness) > prev_aware_count:
            diffusion_timeline.append({
                "step": step,
                "sim_time": sim_time,
                "newly_aware": newly_aware,
                "total_aware": len(first_awareness),
                "pct_aware": round(len(first_awareness) / n_agents * 100, 1),
            })
            prev_aware_count = len(first_awareness)

    # Snapshot at 24h/48h/72h for comparison with Park et al.
    checkpoints = {}
    checkpoint_steps = {
        "24h": 8640, "48h": 17280, "72h": 25920
    }
    max_step = steps[-1]["step"] if steps else 0
    for label, target_step in checkpoint_steps.items():
        aware_at = [p for p, v in first_awareness.items() if v["step"] <= target_step]
        checkpoints[label] = {
            "aware_agents": aware_at,
            "count": len(aware_at),
            "pct": round(len(aware_at) / n_agents * 100, 1),
            "available": target_step <= max_step,
        }

    return {
        "n_agents": n_agents,
        "first_awareness": first_awareness,
        "diffusion_timeline": diffusion_timeline,
        "transmission_graph": transmission_graph,
        "checkpoints": checkpoints,
    }


def print_report(report: dict):
    print(f"\n{'='*60}")
    print(f"INFORMATION DIFFUSION REPORT")
    print(f"{'='*60}")
    print(f"Total agents: {report['n_agents']}")
    print(f"\nFirst awareness per agent:")
    for persona, info in sorted(report["first_awareness"].items(),
                                key=lambda x: x[1]["step"]):
        print(f"  {persona:25s} step {info['step']:5d} | {info['sim_time']} | via {info['method']}")

    print(f"\nDiffusion timeline:")
    for event in report["diffusion_timeline"]:
        print(f"  {event['sim_time']} — {event['newly_aware']} "
              f"({event['total_aware']}/{report['n_agents']} = {event['pct_aware']}%)")

    print(f"\nCheckpoint awareness:")
    for label, data in report["checkpoints"].items():
        if data["available"]:
            print(f"  {label}: {data['count']}/{report['n_agents']} agents "
                  f"({data['pct']}%) aware")
        else:
            print(f"  {label}: simulation did not reach this point")

    if report["transmission_graph"]:
        print(f"\nTransmission graph:")
        for t in report["transmission_graph"]:
            print(f"  {t['from']} → {t['to']} at {t['sim_time']}")


def save_report(final_sim_code: str, report: dict):
    out_path = os.path.join(STORAGE, final_sim_code, "diffusion_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved diffusion report to {out_path}")


if __name__ == "__main__":
    sim = sys.argv[1] if len(sys.argv) > 1 else "July1_the_ville_isabella_maria_Klaus-step-3-20"
    print(f"Tracking diffusion in: {sim}")
    report = track_diffusion(sim)
    print_report(report)
    save_report(sim, report)
