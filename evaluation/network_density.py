"""
network_density.py

Computes social network formation metrics over a simulation run.
A social connection is defined as: two agents have had at least one conversation.
Network density = 2|E| / |V|(|V|-1)  — same formula as Park et al.

Also tracks:
- Unique conversation pairs over time
- Density at regular intervals (every 1h sim time)
- Final network adjacency

Output: network_report.json

Usage:
    python3 network_density.py <sim_code>
    python3 network_density.py July1_the_ville_isabella_maria_Klaus-step-3-20
"""

import json
import os
import sys
from collections import defaultdict

from sim_loader import load_movements, get_persona_names, STORAGE


def compute_network(final_sim_code: str) -> dict:
    """
    Returns:
    {
        "n_agents": int,
        "final_density": float,
        "final_edges": [[agent_a, agent_b], ...],
        "density_over_time": [
            {"step": int, "sim_time": str, "edges": int, "density": float}, ...
        ],
        "conversation_counts": {"Agent A -> Agent B": int, ...}
    }
    """
    steps = load_movements(final_sim_code)
    persona_names = get_persona_names(final_sim_code)
    n = len(persona_names)

    edges = set()  # frozensets of pairs
    conversation_counts = defaultdict(int)
    density_over_time = []

    # Sample density every 360 steps (1 sim hour)
    SAMPLE_INTERVAL = 360
    last_sample_step = -1
    seen_chat_keys = set()

    for step_data in steps:
        step = step_data["step"]
        sim_time = step_data["sim_time"]

        for persona, info in step_data["personas"].items():
            chat = info.get("chat")
            if not chat:
                continue
            key = str(chat[0])
            if key in seen_chat_keys:
                continue
            seen_chat_keys.add(key)

            # All unique speakers in this conversation
            speakers = list({u[0] for u in chat})
            for i in range(len(speakers)):
                for j in range(i + 1, len(speakers)):
                    pair = frozenset([speakers[i], speakers[j]])
                    edges.add(pair)
                    pair_key = f"{speakers[i]} <-> {speakers[j]}"
                    conversation_counts[pair_key] += 1

        # Sample density at interval
        if step >= last_sample_step + SAMPLE_INTERVAL:
            max_edges = n * (n - 1) / 2
            density = len(edges) / max_edges if max_edges > 0 else 0
            density_over_time.append({
                "step": step,
                "sim_time": sim_time,
                "edges": len(edges),
                "density": round(density, 4),
            })
            last_sample_step = step

    # Final density
    max_edges = n * (n - 1) / 2
    final_density = len(edges) / max_edges if max_edges > 0 else 0

    return {
        "n_agents": n,
        "max_possible_edges": int(max_edges),
        "final_edges_count": len(edges),
        "final_density": round(final_density, 4),
        "final_edges": [sorted(list(e)) for e in edges],
        "density_over_time": density_over_time,
        "conversation_counts": dict(conversation_counts),
    }


def print_report(report: dict):
    print(f"\n{'='*60}")
    print(f"NETWORK FORMATION REPORT")
    print(f"{'='*60}")
    print(f"Agents: {report['n_agents']}")
    print(f"Max possible edges: {report['max_possible_edges']}")
    print(f"Final edges: {report['final_edges_count']}")
    print(f"Final density: {report['final_density']:.4f}")
    print(f"\nConnected pairs:")
    for edge in report["final_edges"]:
        pair_key = f"{edge[0]} <-> {edge[1]}"
        count = report["conversation_counts"].get(pair_key, "?")
        print(f"  {edge[0]} <-> {edge[1]}  ({count} conversations)")
    print(f"\nDensity over time (sampled hourly):")
    for snap in report["density_over_time"]:
        bar = "#" * int(snap["density"] * 40)
        print(f"  {snap['sim_time']}  density={snap['density']:.4f}  {bar}")


def save_report(final_sim_code: str, report: dict):
    out_path = os.path.join(STORAGE, final_sim_code, "network_report.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nSaved network report to {out_path}")


if __name__ == "__main__":
    sim = sys.argv[1] if len(sys.argv) > 1 else "July1_the_ville_isabella_maria_Klaus-step-3-20"
    print(f"Computing network density for: {sim}")
    report = compute_network(sim)
    print_report(report)
    save_report(sim, report)
