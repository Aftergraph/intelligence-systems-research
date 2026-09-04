from abc import ABC, abstractmethod

# ponytail: Universal Runtime Adapter Interface (Phase E).
# Ensures a single Mission contract can compile into heterogeneous runtime configurations
# while preserving identical semantic invariants, objectives, and acceptance criteria.

class BaseRuntimeAdapter(ABC):
    def __init__(self, name):
        self.name = name

    @abstractmethod
    def compile_mission(self, mission_doc):
        """Translates a declarative Mission contract into runtime-specific execution topology."""
        pass

    @abstractmethod
    def extract_semantic_invariants(self, compiled_runtime):
        """Extracts normalized semantic invariants to verify cross-runtime equivalence."""
        pass
