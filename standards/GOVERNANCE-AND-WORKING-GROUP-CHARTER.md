# Open Intelligence Systems Working Group (OIS-WG) Charter
**Affiliation:** Open Standards Initiative / IEEE SA Partner Track  
**Founding Chair:** Jonas Abde  
**Date of Formation:** September 2026  
**Document ID:** `OIS-CHARTER-001`  

---

## 1. Mission and Scope

The **Open Intelligence Systems Working Group (OIS-WG)** is established to develop, maintain, and promote open, vendor-neutral specifications, schemas, reference runtimes, and conformance suites for autonomous intelligent systems.

The Working Group governs:
1. **SPEC-001 (Intelligence System Contract Specification):** Canonical schemas and lifecycle invariants.
2. **RFC 0001 (ISC-VP):** Protocol wire formats, delegation tokens, and verification interfaces.
3. **MISSION-Bench:** Reproducible multi-domain benchmark test suites and failure injection harnesses.
4. **Open Reference Implementations & Conformance Suites:** Certification test vectors ensuring cross-vendor semantic portability.

---

## 2. Intellectual Property Rights (IPR) Policy

1. **Royalty-Free Licensing (RAND-Z):** All contributors and participating organizations agree to grant a perpetual, non-exclusive, royalty-free, worldwide patent and copyright license (RAND-Zero) to any essential patent claims required to implement conforming implementations of OIS-WG standards.
2. **Defensive Patent Termination:** Any participant asserting patent infringement claims against a conforming implementation of an OIS-WG standard forfeits all licenses granted under this charter.
3. **Open Source Core:** All schemas, test vectors, and reference runtimes are licensed under the **Apache License, Version 2.0**.

---

## 3. Governance and Decision-Making Structure

### 3.1 Technical Steering Committee (TSC)
- The TSC oversees technical direction, approves specification releases, and resolves technical disputes.
- Founding TSC Chair: **Jonas Abde**.
- Seat allocation: Democratic voting among verified independent implementers who have passed 100% of the conformance test suite.

### 3.2 Consensus Model: "Rough Consensus and Running Code"
Following the proven IETF standards philosophy:
1. Specifications are not approved based on abstract committee votes.
2. Every proposed normative feature must have:
   - At least **two independent interoperable implementations**;
   - An automated conformance test vector added to the test suite;
   - Documented empirical evidence demonstrating utility without violating complexity budgets.

---

## 4. Conformance and Certification Program

1. **The "Verified Intelligent System" (VIS) Mark:**
   - Any runtime, cloud platform, or agent framework may brand itself as a *Verified Intelligent System* only after executing the official `conformance/runner.py` suite against all normative test cases and submitting the signed `conformance_report.json` to the public registry with a **100% pass rate**.
2. **Revocation of Certification:** Any certified system found to allow agents to bypass Invariant 1 ($\text{Complete} \not\implies \text{Verified}$) or forge delegation tokens faces immediate decertification.

---
*End of OIS-WG Charter OIS-CHARTER-001.*
