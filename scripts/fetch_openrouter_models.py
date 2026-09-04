"""Fetch OpenRouter model catalog and filter free models for STUDY-011 planning."""
import urllib.request, json, ssl, sys, os

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_KEY:
    print("ERROR: OPENROUTER_API_KEY env var required (no hardcoded defaults).", file=sys.stderr)
    sys.exit(1)

ctx = ssl.create_default_context()
req = urllib.request.Request(
    "https://openrouter.ai/api/v1/models",
    headers={
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "HTTP-Referer": "https://github.com/jonas-abde-research",
        "Accept": "application/json",
    },
)
with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
    data = json.loads(r.read())

models = data.get("data", [])

def is_free(m):
    p = m.get("pricing", {})
    prompt_cost = str(p.get("prompt", "1"))
    completion_cost = str(p.get("completion", "1"))
    model_id = m.get("id", "")
    return (
        prompt_cost in ("0", "0.0")
        and completion_cost in ("0", "0.0")
    ) or model_id.endswith(":free")

free_models = [m for m in models if is_free(m)]
paid_models = [m for m in models if not is_free(m)]

print(f"Total models on OpenRouter: {len(models)}")
print(f"Free models: {len(free_models)}")
print(f"Paid models: {len(paid_models)}")
print()

# Sort free models by context window desc, then id
free_sorted = sorted(free_models, key=lambda x: (-x.get("context_length", 0), x.get("id", "")))

print("FREE MODELS (sorted by context window):")
print(f"{'Model ID':<60} {'Ctx':>8}  {'Family/Org'}")
print("-" * 90)
for m in free_sorted:
    mid = m.get("id", "?")
    ctx_k = m.get("context_length", 0) // 1000
    name = m.get("name", "")
    print(f"{mid:<60} {ctx_k:>7}K  {name[:30]}")

# Also check top paid models for reference
print()
print("TOP PAID MODELS (by context, for reference only):")
for m in sorted(paid_models, key=lambda x: -x.get("context_length", 0))[:10]:
    mid = m.get("id", "?")
    ctx_k = m.get("context_length", 0) // 1000
    pp = m.get("pricing", {}).get("prompt", "?")
    print(f"  {mid:<55} ctx={ctx_k}K  prompt=${pp}/tok")

# Save full catalog
with open("data/openrouter_model_catalog.json", "w", encoding="utf-8") as f:
    json.dump({"total": len(models), "free_count": len(free_models),
               "retrieved_at": "2026-09-04T01:41:00Z",
               "free_models": free_sorted,
               "all_models": models}, f, indent=2)
print()
print("Saved: data/openrouter_model_catalog.json")
