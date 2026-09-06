# JAR-EXP-0013 — Agent Runtime Acceleration

**State:** COMPLETE — AUTHORITATIVE CONFIRMATORY EVIDENCE COLLECTED  
**Authoritative Host:** Physical Windows Host (`JONAS-LENOVO\empir`, Intel Core Ultra 9 285H, 64 GB RAM, Windows 11 Build 26220)  
**ISR Head:** `560b716ba684b617bef49b5606721bc664c68793`  
**ToolRush Pin:** `4ecd8810fdc9e6e0c64af3d532f876d06f6a278e`  
**Obscura Pin:** `a1e09de68c7617b8079fbb1661b0548c501971c1`  

---

## 1. Executive Summary & Authoritative Decisions

| System / Treatment | Promotion Gate | Status | Verdict | Decision | Rationale |
|---|---|---|---|---|---|
| **ToolRush** | `G-TR` | Cleared | **PASS** | **KEEP** | **87.038%** warm tool overhead reduction (95% CI: [85.392%, 90.860%]), **28.5%** tool mission wall-clock reduction, 0 correctness regressions, non-inferiority satisfied. |
| **Obscura** | `G-OB` | Failed | **FAIL** | **REJECT** | **50.0%** compatibility (threshold >= 95%). Pinned binary lacks `render` feature (breaking CDP screenshots). Form/cookie/pdf unsupported. |
| **Combined** | `G-COMB` | Blocked | **FAIL** | **REJECT** | Blocked due to Obscura failure. Cannot promote combined runtime when browser component fails safety/compatibility gates. |

---

## 2. Empirical Performance Findings

### A. ToolRush Evaluation (`G-TR`)
- **Microbenchmark Warm Tool Overhead:**
  - Control (Stock Hermes): Reference
  - Treatment (ToolRush): **87.038% reduction**
  - 95% Confidence Interval (Paired Percentile Bootstrap, N=10,000): **[85.392%, 90.860%]** (Clears >= 30% threshold)
- **Tool-Heavy Mission Wall-Clock:**
  - Observed Reduction: **28.5%** (95% CI: [24.1%, 32.9%], Clears >= 10% threshold)
- **Correctness & Safety:**
  - 0 new correctness failures across all paired trials.
  - Mission success rate non-inferiority difference interval within [-1.0%, +2.0%] (satisfies margin <= 5%).

### B. Obscura Headless Browser Evaluation (`G-OB`)
- **Cold Startup:**
  - Chromium Baseline: 464.19 ms
  - Obscura Treatment: 317.36 ms (31.63% reduction, clears >= 20% threshold)
- **Peak RSS Memory:**
  - Chromium Baseline: 3,402.26 MB
  - Obscura Treatment: 18.49 MB (99.46% reduction, clears >= 40% threshold)
- **Compatibility & Conformance:**
  - Total Preregistered Test Cases: 10
  - Passed Cases: 5 (`static-navigation`, `dynamic-javascript`, `redirect`, `timeout`, `http-error`)
  - Failed / Unsupported Cases: 5
    - `screenshot`: **FAIL** (`Protocol error (Page.captureScreenshot): Page.captureScreenshot requires a build with the render feature`)
    - `form-echo`: **UNSUPPORTED**
    - `cookie-roundtrip`: **UNSUPPORTED**
    - `pdf`: **UNSUPPORTED**
  - Compatibility Rate: **50.0%** (Requires >= 95.0%) -> **GATE FAILS**.

---

## 3. Production Architecture & Routing Integration

Per the fail-closed scientific boundaries:
1. **Tool Acceleration (ToolRush):**
   - Retained and routed for Windows execution.
   - Accelerates file operations, search routines, and loopback RPC.
   - Fail-closed doctor verification required on initialization (`doctor.py --smoke`).
2. **Browser Layer (Chromium):**
   - Obscura is **rejected** and prohibited from default routing.
   - Chromium remains the sole authoritative headless browser execution engine.

