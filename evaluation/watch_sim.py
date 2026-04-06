"""
watch_sim.py

Live progress monitor for a running generative agents simulation.
Shows a clean one-line status update every N seconds.

Usage:
    python3 watch_sim.py <sim_code> [interval_seconds]
    python3 watch_sim.py base_the_ville_n25_v1_day1
    python3 watch_sim.py base_the_ville_n25_v1_day1 5
"""

import json
import os
import sys
import time

STORAGE = os.path.join(
    os.path.dirname(__file__),
    "../generative_agents/environment/frontend_server/storage"
)
TOTAL_STEPS = 8640  # 1 sim day


def get_status(sim_code):
    movement_dir = os.path.join(STORAGE, sim_code, "movement")
    if not os.path.exists(movement_dir):
        return None

    files = [f for f in os.listdir(movement_dir) if f.endswith(".json")]
    if not files:
        return None

    latest = max(files, key=lambda x: int(x.split(".")[0]))
    step = int(latest.split(".")[0])

    with open(os.path.join(movement_dir, latest)) as f:
        data = json.load(f)
    sim_time = data["meta"]["curr_time"]

    # Token log
    token_path = os.path.join(STORAGE, sim_code, "token_log.json")
    cost = None
    calls = None
    if os.path.exists(token_path):
        try:
            with open(token_path) as f:
                tdata = json.load(f)
            cost = tdata["summary"]["estimated_cost_usd"]
            calls = tdata["summary"]["calls"]
        except Exception:
            pass

    pct = step / TOTAL_STEPS * 100
    bar_len = 30
    filled = int(bar_len * step / TOTAL_STEPS)
    bar = "█" * filled + "░" * (bar_len - filled)

    return {
        "step": step,
        "sim_time": sim_time,
        "pct": pct,
        "bar": bar,
        "cost": cost,
        "calls": calls,
        "total_files": len(files),
    }


def main():
    sim_code = sys.argv[1] if len(sys.argv) > 1 else "base_the_ville_n25_v1_day1"
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    print(f"Watching: {sim_code}  (refreshing every {interval}s, Ctrl+C to stop)\n")

    try:
        while True:
            s = get_status(sim_code)
            if s is None:
                print(f"\r  Waiting for movement files...", end="", flush=True)
            else:
                cost_str = f"  ${s['cost']:.4f}" if s["cost"] is not None else ""
                calls_str = f"  {s['calls']} calls" if s["calls"] is not None else ""
                line = (
                    f"\r  [{s['bar']}] {s['pct']:5.1f}%"
                    f"  step {s['step']}/{TOTAL_STEPS}"
                    f"  {s['sim_time']}"
                    f"{cost_str}{calls_str}   "
                )
                print(line, end="", flush=True)

                if s["step"] >= TOTAL_STEPS:
                    print(f"\n\n  Done! Simulation complete.")
                    break

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Stopped.")


if __name__ == "__main__":
    main()
