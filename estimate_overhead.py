"""
Computes a REAL tokenizer-based estimate of the fixed system-prompt
overhead from the current lyzr_agent_config.json — no live API call
needed. Useful right now while gpt-4o-mini is down/broken on Lyzr and
you can't get a real trace to calibrate against.

This is NOT the same as a real measured trace (Lyzr may add its own
platform-level boilerplate around your config text that this script
can't see), but it's far more accurate than a word-count guess, since
it uses the actual tokenizer OpenAI's models use.

Usage:
    pip install tiktoken --break-system-packages   # if not already installed
    python estimate_overhead.py --config lyzr_agent_config.json
"""
import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument("--config", default="lyzr_agent_config.json")
args = parser.parse_args()

with open(args.config) as f:
    cfg = json.load(f)

# Reconstruct the system-prompt text the same way Lyzr assembles it from
# your config fields. Order/joining is a best guess (Lyzr doesn't
# document the exact template) — close enough for a real estimate.
parts = [
    cfg.get("agent_role", ""),
    cfg.get("agent_instructions", ""),
    cfg.get("agent_goal", ""),
    cfg.get("agent_context", ""),
    cfg.get("agent_output", ""),
    cfg.get("examples", ""),
]
full_text = "\n\n".join(parts)

try:
    import tiktoken
    enc = tiktoken.encoding_for_model("gpt-4o-mini")
    token_count = len(enc.encode(full_text))
    print(f"Real tokenizer count (tiktoken, gpt-4o-mini encoding): {token_count}")
    print()
    print("This is your best available PROMPT_OVERHEAD_TOKENS estimate")
    print("right now, without needing a working API call.")
    print()
    print("CAVEAT: this only covers YOUR config text. Lyzr's platform may")
    print("add additional system-level boilerplate around it that isn't")
    print("visible here (earlier real traces suggested this could be")
    print("substantial). Treat this as a floor, not a ceiling.")
    print()
    print(f"Update harness.py: PROMPT_OVERHEAD_TOKENS = {token_count}")
    print()
    print("IMPORTANT: the moment gpt-4o-mini (or any model on your agent)")
    print("works again, run `python harness.py --mode calibrate` with a")
    print("real call to true this up against an actual measured trace —")
    print("this script's number is a reasonable stand-in, not a")
    print("replacement for real measurement.")
except ImportError:
    words = len(full_text.split())
    print("tiktoken not installed. Install it for a real count:")
    print("  pip install tiktoken --break-system-packages")
    print()
    print(f"Fallback word-count estimate: {int(words * 1.3)} tokens")
    print("(This is much less accurate — install tiktoken if at all possible.)")
