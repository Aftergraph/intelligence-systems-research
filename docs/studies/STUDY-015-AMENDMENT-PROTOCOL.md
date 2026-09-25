# STUDY-015 Amendment Protocol

**Status:** Draft rule for G15-8.

After G15 protocol freeze, no confirmatory protocol artifact may be silently replaced.

Every amendment must:

1. use the next sequential ID `S15-AMD-NNN`;
2. state the trigger and rationale;
3. record UTC timestamp;
4. bind the exact before/after protocol SHA-256;
5. state whether data had already been observed;
6. classify prior observations as admissible, invalidated, or segregated;
7. never overwrite historical raw records;
8. update the freeze/admissibility manifest if the implementation identity changes.

A failed hypothesis is never a reason to change a frozen endpoint, condition, exclusion rule, or statistical test.
