# Jonas Abde Intelligence Systems Research Program
## Standalone External Validation Pack (Clean-Room Implementation Challenge)

**Target Audience:** Independent third-party engineering teams, open-source maintainers, and academic researchers.  
**Program Directive:** Phase G & Milestone Gate Evaluation (Implementable Standard Candidate).  
**Rules:** 
1. **Zero Access to Reference Runtime:** You MUST NOT view or use any source files in `runtime/` or `prototype/`.
2. **Implement Strictly from Specification:** Implement your candidate runtime using ONLY the normative requirements in `SPECIFICATION.md` and the schemas in `schemas/`.
3. **Pass the Conformance Suite:** Your implementation must achieve 100% pass rate on `conformance/standalone_runner.py`.

---

## Pack Structure

```
external_validation_pack/
├── README.md                              # This instruction guide
├── SPECIFICATION.md                       # Frozen normative SPEC-001 v0.1
├── BLINDED_INTEROPERABILITY_CHALLENGE.md  # Blinded cross-runtime test definition
├── schemas/                               # Canonical JSON Schemas (Draft 2020-12)
│   ├── intelligence-system.v0alpha1.json
│   ├── mission.v0alpha1.json
│   ├── delegation.v0alpha1.json
│   └── evidence.v0alpha1.json
├── test_vectors/                          # Standardized test inputs & delegations
│   ├── sample_manifest.json
│   ├── sample_mission.json
│   ├── sample_delegation.json
│   └── sample_evidence.json
└── conformance/
    ├── test_cases.json                    # 14 Normative Test Case Definitions
    └── standalone_runner.py               # Clean runner testing your engine interface
```

---

## How to Test Your Candidate Implementation

1. Create your implementation in any language or framework (e.g. Python, Rust, Go, TypeScript).
2. For Python implementations, expose an engine class conforming to:
   ```python
   class YourEngine:
       def load_manifest(self, path_or_dict): ...
       def load_mission(self, path_or_dict): ...
       def authorize(self, delegation_dict): ...
       def start(self): ...
       def execute_action(self, capability_uri, payload=None, tokens=0, cost_usd=0.0): ...
       def finish_execution(self): ...
       def record_evidence(self, evidence_dict): ...
       def evaluate_verification(self) -> bool: ...
       def get_metrics(self) -> dict: ...
   ```
3. Run the standalone conformance runner pointing to your module:
   ```bash
   python conformance/standalone_runner.py --engine-module your_pkg.your_engine --engine-class YourEngine
   ```
4. If all 14 test cases pass, your runtime is officially certified as **SPEC-001 Conforming**.
