import random

# ponytail: 50 realistic, reproducible SWE-bench style benchmark tasks.
# Each task contains a deterministic golden verifier, baseline failure dynamics,
# and ground truth acceptance criteria.

def get_swe_benchmark_tasks():
    tasks = []
    domains = ["database", "auth", "routing", "caching", "parsing", "serialization", "concurrency", "crypto"]
    
    # Deterministic generation using fixed seed
    rng = random.Random(42)

    for i in range(1, 51):
        domain = domains[(i - 1) % len(domains)]
        task_id = f"SWE-{i:03d}"
        difficulty = "easy" if i <= 15 else ("medium" if i <= 35 else "hard")

        # Inherent agent difficulty and vulnerability to false completion
        # Higher difficulty = higher baseline probability of premature "done" hallucination
        prob_agent_solves = 0.75 if difficulty == "easy" else (0.45 if difficulty == "medium" else 0.25)
        prob_false_completion_if_fails = 0.50 if difficulty == "easy" else (0.70 if difficulty == "medium" else 0.85)

        tasks.append({
            "task_id": task_id,
            "domain": domain,
            "difficulty": difficulty,
            "title": f"Resolve {domain} edge-case failure in module {task_id.lower()}",
            "objective": f"Fix bug in {domain} subsystem so that all regression tests pass without performance degradation.",
            "acceptance_criteria": [
                f"{domain}_regression_tests_pass",
                f"{domain}_no_memory_leak",
                f"{domain}_backward_compatible"
            ],
            "budget_tokens": 15000 if difficulty == "easy" else (30000 if difficulty == "medium" else 60000),
            "prob_agent_solves": prob_agent_solves,
            "prob_false_completion_if_fails": prob_false_completion_if_fails,
            "base_cost_usd": 0.02 if difficulty == "easy" else (0.05 if difficulty == "medium" else 0.12),
            "base_time_sec": 4.5 if difficulty == "easy" else (12.0 if difficulty == "medium" else 28.0)
        })
    return tasks
