# Track B Instruments — STUDY-006 Pilot Kit

**Date:** 2026-09-04  
**Status:** BUILD COMPLETE — READY FOR RECUITMENT  
**Study:** STUDY-006 HCI Trial (N=64, 4 arms)

---

## Instrument Files

| File | Description |
|------|-------------|
| `pilots/instruments/NASA-TLX.md` | Cognitive workload measure (6 subscales, 0–20 rating) |
| `pilots/instruments/SUS.md` | System Usability Scale (10 items, 0–100 score) |
| `pilots/instruments/TRUST-CALIBRATION.md` | Trust self-report (5 items) + behavioral proxies |
| `pilots/instruments/SESSION-LOGGING.md` | Telemetry schema (participant_id, arm, task_id, event_type, timestamp, payload_hash) |
| `pilots/RECRUITMENT-POST.md` | Recruitment text (Danish + English) |

---

## Measures Aligned With Protocol

Per `STUDY-006-HCI-PREREGISTRATION.md` (Section 3):

| Outcome | Instrument |
|---------|------------|
| HEVO (Human Effort per Verified Outcome) | Platform telemetry (intervention count) |
| NASA-TLX (Cognitive Workload) | NASA-TLX.md |
| UEHR (Undetected Error Rate) | Platform telemetry (errors_detected) |
| Calibrated Reliance & Trust | TRUST-CALIBRATION.md |
| TVO (Time to Verified Outcome) | Platform telemetry (timestamp delta) |
| SUS (Usability) | SUS.md |

---

## Next Steps

- [ ] Recruit 64 participants via RECRUITMENT-POST.md
- [ ] Verify Track B.4 telemetry implementation (SESSION-LOGGING.md)
- [ ] Obtain ethics/IRB approval before first session
- [ ] Train research assistants on instrument administration

---

*State updated: 2026-09-04 — Track B instruments complete*
