from __future__ import annotations

from dataclasses import dataclass
import random

from .archive import QDArchive
from .engine import Candidate, _descriptor, _evaluate, _random_genome, _select_parents
from .harness import benchmark_manifest_hash
from .operators import crossover, mutate_numeric


@dataclass(frozen=True)
class BaselineResult:
    name: str
    best: Candidate
    best_quality: float
    evaluations: int


def _budget(population_size: int, generations: int) -> int:
    if population_size < 2:
        raise ValueError("population_size must be at least 2")
    if generations < 0:
        raise ValueError("generations must be non-negative")
    return population_size * (generations + 1)


def _best(candidates: list[Candidate]) -> Candidate:
    return max(candidates, key=lambda c: c.quality)


def run_random(cases, seed: int, population_size: int = 20, generations: int = 10) -> BaselineResult:
    rng = random.Random(seed)
    count = _budget(population_size, generations)
    candidates = [
        _evaluate(_random_genome(rng), cases, seed * 100000 + index)
        for index in range(count)
    ]
    best = _best(candidates)
    return BaselineResult("B0-random", best, best.quality, count)


def run_fixed(cases, seed: int, population_size: int = 20, generations: int = 10) -> BaselineResult:
    from .models import PolicyGenome

    count = _budget(population_size, generations)
    genome = PolicyGenome(
        routing_policy=("discover", "execute", "verify"),
        parallelism=2,
        retry_ceiling=2,
        confidence_threshold=0.85,
        verification_depth=3,
        operator_weights=(("numeric", 0.5), ("crossover", 0.5)),
    )
    candidates = [_evaluate(genome, cases, seed * 100000 + index) for index in range(count)]
    best = _best(candidates)
    return BaselineResult("B1-fixed", best, best.quality, count)


def run_ga(cases, seed: int, population_size: int = 20, generations: int = 10) -> BaselineResult:
    rng = random.Random(seed)
    population = [
        _evaluate(_random_genome(rng), cases, seed * 1000 + index)
        for index in range(population_size)
    ]
    global_best = _best(population)
    for generation in range(generations):
        parents = sorted(population, key=lambda c: c.quality, reverse=True)[: max(2, population_size // 3)]
        children = []
        for slot in range(population_size):
            parent = rng.choice(parents)
            op_seed = rng.randrange(2**31)
            if rng.random() < 0.65:
                genome, _ = mutate_numeric(parent.genome, op_seed)
            else:
                genome, _ = crossover(parent.genome, rng.choice(parents).genome, op_seed)
            child = _evaluate(genome, cases, seed * 100000 + generation * population_size + slot)
            children.append(child)
            if child.quality > global_best.quality:
                global_best = child
        population = children
    return BaselineResult("B2-simple-ga", global_best, global_best.quality, _budget(population_size, generations))


def run_pareto(cases, seed: int, population_size: int = 20, generations: int = 10) -> BaselineResult:
    rng = random.Random(seed)
    population = [
        _evaluate(_random_genome(rng), cases, seed * 1000 + index)
        for index in range(population_size)
    ]
    global_best = _best(population)
    for generation in range(generations):
        parents = _select_parents(population)
        children = []
        for slot in range(population_size):
            parent = rng.choice(parents)
            op_seed = rng.randrange(2**31)
            if rng.random() < 0.5:
                genome, _ = mutate_numeric(parent.genome, op_seed)
            else:
                genome, _ = crossover(parent.genome, rng.choice(parents).genome, op_seed)
            child = _evaluate(genome, cases, seed * 100000 + generation * population_size + slot)
            children.append(child)
            if child.quality > global_best.quality:
                global_best = child
        population = children
    return BaselineResult("B5-pareto-style", global_best, global_best.quality, _budget(population_size, generations))


def run_qd(cases, seed: int, population_size: int = 20, generations: int = 10) -> BaselineResult:
    rng = random.Random(seed)
    archive = QDArchive()
    candidates: dict[str, Candidate] = {}
    population = [
        _evaluate(_random_genome(rng), cases, seed * 1000 + index)
        for index in range(population_size)
    ]
    global_best = _best(population)
    for candidate in population:
        candidates[candidate.genome.identity] = candidate
        archive.insert(candidate.genome.identity, _descriptor(candidate), candidate.outcome)

    for generation in range(generations):
        parent_pool = [
            candidates[entry.candidate_id]
            for entry in archive.entries()
            if entry.candidate_id in candidates
        ] or population
        children = []
        for slot in range(population_size):
            parent = rng.choice(parent_pool)
            genome, _ = mutate_numeric(parent.genome, rng.randrange(2**31))
            child = _evaluate(genome, cases, seed * 100000 + generation * population_size + slot)
            candidates[child.genome.identity] = child
            archive.insert(child.genome.identity, _descriptor(child), child.outcome)
            children.append(child)
            if child.quality > global_best.quality:
                global_best = child
        population = children
    return BaselineResult("B6-qd-style", global_best, global_best.quality, _budget(population_size, generations))
