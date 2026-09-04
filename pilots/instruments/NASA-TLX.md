# NASA-TLX (Task Load Index) — STUDY-006 Instrument

**Protocol ID:** `STUDY-006-PREREG-001`  
**Measure:** Cognitive Workload (HEVO & TLX, primary outcome in preregistration)  
**Administration:** Post-task, after each of the 4 enterprise workflows  
**Time to Complete:** ~3–5 minutes per task

---

## 1. Overview

NASA-TLX is a standardized multidimensional self-report measure of subjective workload. It consists of 6 subscales:

1. **Mental Demand** – How much mental and perceptual activity was required?
2. **Physical Demand** – How much physical activity was required?
3. **Temporal Demand** – How much time pressure did you feel?
4. **Performance** – How successful were you in accomplishing your goals?
5. **Effort** – How much effort did you exert to accomplish your goals?
6. **Frustration** – How insecure, discouraged, irritated, or stressed did you feel?

---

## 2. Rating Scale (0–20)

For each subscale, mark your rating on a line from **0 (Low)** to **20 (High)**:

| Subscale | 0 (Low) | 20 (High) |
|----------|---------|-----------|
| Mental Demand | Low | High |
| Physical Demand | Low | High |
| Temporal Demand | Low | High |
| Performance | Good | Poor |
| Effort | Low | High |
| Frustration | Low | High |

*Note: Participants typically rate by marking a tick on a physical line; the scorer records the nearest integer value.*

---

## 3. Scoring Instructions

### 3.1 Raw Score (Unweighted) — Primary Protocol

For STUDY-006, the **unweighted average** is the primary score:

1. Sum the 6 subscale ratings: `Sum = MD + PD + TD + Perf + Effort + Frustr`
2. Divide by 6: `TLX_Score = Sum / 6`

**Result:** 0–100 (each 20-point subscale averaged)

### 3.2 Weighted Score (Alternative/Research Note)

If the weighted version is needed (Hart & Staveland, 1988):

1. **Pairwise Comparisons:** Before rating, participants compare each pair of subscales (15 pairs total) to identify which contributed more to workload.
2. **Weights:** Count how many times each subscale was selected (weight = 0–5).
3. **Weighted Score:** `TLX_Weighted = (MD×W_MD + PD×W_PD + TD×W_TD + Perf×W_Perf + Effort×W_Effort + Frustr×W_Frustr) / 15`

*For STUDY-006, the unweighted version is sufficient; weighting can be used in exploratory analysis.*

---

## 4. Interpretation

| Score Range | Workload Level |
|-------------|----------------|
| 0–30 | Low |
| 31–60 | Moderate |
| 61–100 | High |

**Primary Analysis:** Compare mean TLX scores across the 4 arms (Chat-Only, GUI, Hybrid, Mission-Centric).

---

## 5. References

- Hart, S. G., & Staveland, L. E. (1988). Development of NASA-TLX (Task Load Index): Results of empirical and theoretical research. In *Human Mental Workload* (pp. 139–183). Elsevier.

---

*Instrument version: 1.0 — Matches STUDY-006 preregistration (Section 3.2)*
