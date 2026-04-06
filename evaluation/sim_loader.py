"""
sim_loader.py

Utility for loading movement files from a generative_agents simulation,
handling the fork-chain structure where a single logical run is split
across multiple storage folders.

Usage:
    from sim_loader import load_movements
    steps = load_movements("July1_the_ville_isabella_maria_Klaus-step-3-20")
    # steps is a list of dicts sorted by step number, each containing:
    #   step, sim_time, personas: {name: {movement, description, chat}}
"""

import json
import os

STORAGE = os.path.join(
    os.path.dirname(__file__),
    "../generative_agents/environment/frontend_server/storage"
)


def _get_fork_chain(final_sim_code: str) -> list[tuple[str, int]]:
    """
    Walk backwards from final_sim_code through fork_sim_code links.
    Returns list of (sim_code, cumulative_step_count) in chronological order.
    The base sim (step=0) is excluded since it has no movement files.
    """
    chain = []
    curr = final_sim_code
    visited = set()

    while curr and curr not in visited:
        meta_path = os.path.join(STORAGE, curr, "reverie", "meta.json")
        if not os.path.exists(meta_path):
            break
        visited.add(curr)
        with open(meta_path) as f:
            meta = json.load(f)
        chain.append((curr, meta["step"]))
        parent = meta["fork_sim_code"]
        if not os.path.exists(os.path.join(STORAGE, parent, "reverie", "meta.json")):
            break
        curr = parent

    chain.reverse()  # chronological order
    return chain


def load_movements(final_sim_code: str) -> list[dict]:
    """
    Load all movement steps from the full fork chain ending at final_sim_code.
    Deduplicates across forks: each step number appears exactly once,
    taken from the earliest fork that contains it.

    Returns a list of dicts sorted by step number:
    {
        "step": int,
        "sim_time": str,          # e.g. "February 13, 2023, 11:22:30"
        "personas": {
            "Isabella Rodriguez": {
                "movement": [x, y],
                "description": str,
                "chat": list or None
            },
            ...
        }
    }
    """
    chain = _get_fork_chain(final_sim_code)
    seen_steps = set()
    all_steps = []

    prev_step_count = 0
    for sim_code, cumulative_steps in chain:
        movement_dir = os.path.join(STORAGE, sim_code, "movement")
        if not os.path.exists(movement_dir):
            prev_step_count = cumulative_steps
            continue

        files = sorted(os.listdir(movement_dir), key=lambda x: int(x.split(".")[0]))
        for fname in files:
            step_num = int(fname.split(".")[0])
            if step_num in seen_steps:
                continue
            seen_steps.add(step_num)
            with open(os.path.join(movement_dir, fname)) as f:
                raw = json.load(f)
            all_steps.append({
                "step": step_num,
                "sim_time": raw["meta"]["curr_time"],
                "personas": raw["persona"],
            })

        prev_step_count = cumulative_steps

    all_steps.sort(key=lambda x: x["step"])
    return all_steps


def get_persona_names(final_sim_code: str) -> list[str]:
    meta_path = os.path.join(STORAGE, final_sim_code, "reverie", "meta.json")
    with open(meta_path) as f:
        meta = json.load(f)
    return meta["persona_names"]


if __name__ == "__main__":
    sim = "July1_the_ville_isabella_maria_Klaus-step-3-20"
    steps = load_movements(sim)
    print(f"Total steps loaded: {len(steps)}")
    print(f"First step: {steps[0]['sim_time']}")
    print(f"Last step:  {steps[-1]['sim_time']}")
    print(f"Personas: {list(steps[0]['personas'].keys())}")
