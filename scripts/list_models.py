"""List current Mistral and Qwen models on OpenRouter with prices, so you pick real IDs.

  python scripts/list_models.py              # mistral + qwen
  python scripts/list_models.py llama gemma  # any search terms
"""
import json
import sys
import urllib.request


def main():
    terms = [t.lower() for t in sys.argv[1:]] or ["mistral", "qwen"]
    with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=30) as resp:
        models = json.load(resp)["data"]
    rows = []
    for m in models:
        mid = m["id"].lower()
        if any(t in mid for t in terms):
            p = m.get("pricing", {})
            prompt = float(p.get("prompt", 0) or 0) * 1e6
            completion = float(p.get("completion", 0) or 0) * 1e6
            rows.append((prompt + completion, m["id"], m.get("context_length"), prompt, completion))
    rows.sort()
    print(f"{'model id':60s} {'context':>9s} {'$ in/M':>8s} {'$ out/M':>8s}")
    for _, mid, ctx, pi, po in rows:
        print(f"{mid:60s} {str(ctx):>9s} {pi:8.2f} {po:8.2f}")


if __name__ == "__main__":
    main()
