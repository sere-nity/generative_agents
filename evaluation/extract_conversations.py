"""
extract_conversations.py

Extracts all unique conversations from a simulation run, handling:
- Deduplication (same chat repeats across multiple steps while agents converse)
- Fork-chain traversal (sim split across multiple storage folders)

Output: conversations.json in the sim's storage folder

Usage:
    python3 extract_conversations.py <sim_code>
    python3 extract_conversations.py July1_the_ville_isabella_maria_Klaus-step-3-20
"""

import json
import os
import sys

from sim_loader import load_movements, get_persona_names, STORAGE


def extract_conversations(final_sim_code: str) -> list[dict]:
    """
    Returns list of unique conversations, each:
    {
        "step": int,                  # step number when conversation started
        "sim_time": str,              # sim time when conversation started
        "participants": [str, ...],   # all agents involved
        "initiator": str,             # first speaker
        "utterances": [               # full transcript
            {"speaker": str, "text": str}, ...
        ],
        "topics": [str]               # keywords from description fields during convo
    }
    """
    steps = load_movements(final_sim_code)
    seen_keys = set()
    conversations = []
    # Track description text during active conversations for topic extraction
    active_convos = {}  # key -> set of description strings

    for step_data in steps:
        for persona, info in step_data["personas"].items():
            chat = info.get("chat")
            if not chat:
                continue

            key = str(chat[0])  # first utterance as dedup key

            if key not in seen_keys:
                seen_keys.add(key)
                utterances = [{"speaker": u[0], "text": u[1]} for u in chat]
                participants = list({u[0] for u in chat})
                conversations.append({
                    "step": step_data["step"],
                    "sim_time": step_data["sim_time"],
                    "participants": participants,
                    "initiator": chat[0][0],
                    "utterances": utterances,
                    "description_snippets": [],
                })
                active_convos[key] = set()

            # Collect description text while conversation is active
            if key in active_convos:
                desc = info.get("description", "")
                if desc:
                    active_convos[key].add(desc)

    # Attach collected descriptions to each conversation
    for convo in conversations:
        key = str([convo["utterances"][0]["speaker"],
                   convo["utterances"][0]["text"]])
        convo["description_snippets"] = list(active_convos.get(key, []))

    return conversations


def save_conversations(final_sim_code: str, conversations: list[dict]):
    out_path = os.path.join(STORAGE, final_sim_code, "conversations.json")
    with open(out_path, "w") as f:
        json.dump(conversations, f, indent=2)
    print(f"Saved {len(conversations)} conversations to {out_path}")


def print_summary(conversations: list[dict]):
    print(f"\n{'='*60}")
    print(f"CONVERSATION SUMMARY — {len(conversations)} unique conversations")
    print(f"{'='*60}")
    for i, c in enumerate(conversations, 1):
        print(f"\n[{i}] Step {c['step']} | {c['sim_time']}")
        print(f"    Participants: {', '.join(c['participants'])}")
        print(f"    Initiator: {c['initiator']}")
        print(f"    First utterance: {c['utterances'][0]['text'][:80]}...")
        if len(c["utterances"]) > 1:
            print(f"    Reply: {c['utterances'][1]['text'][:80]}...")


if __name__ == "__main__":
    sim = sys.argv[1] if len(sys.argv) > 1 else "July1_the_ville_isabella_maria_Klaus-step-3-20"
    print(f"Extracting conversations from: {sim}")
    convos = extract_conversations(sim)
    print_summary(convos)
    save_conversations(sim, convos)
