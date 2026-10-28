# Freeze v2 input — fresh-review log (validator 2.8.9 → 2.8.12)

Reviewer for every round: a fresh DeepSeek v4.1 flash session (opencode) in its own clone at the
exact SHA, prompt = attack list + "every finding needs a reproducer". Findings were re-verified
here before any fix; every fix carries a regression test that is red against the reviewed SHA.

```text
REVIEW  SHA       VERDICT            FINDINGS                                   FIXED IN
#1      ad87629   CHANGES_REQUIRED   P2 TMPDIR-dependent verdicts; P3 x4        667ffe4 (2.8.9)
#2      667ffe4   CHANGES_REQUIRED   P1 pin chose the env (r51/r52); P2 probe   83cb72d (2.8.10)
                                     env; P2 pairs view not program-made; P3
#3      83cb72d   CHANGES_REQUIRED   P2 non-moving guards not re-run symlinked; 5090f44 (2.8.11)
                                     P3 probe-agreement overclaim
#4      5090f44   CHANGES_REQUIRED   P2 guard_unmeasured resolved-only; P2      ce6fc9d (2.8.12)
                                     freeze-v2 README oracle claim; P3 x3
#5      ce6fc9d   PASS (P0=P1=P2=0)  P3 x3 (below)                              recorded, not fixed
```

Found here, not by a reviewer, and fixed in the same commits: 83cb72d — the admission README and
alignment.json had restated two recipe identifiers since 38d3674, breaking the CE-28
single-declaration tests (earlier gate runs missed it); alignment.py read an unreadable ticket as
empty. 5090f44 — the first 2.8.11 draft renamed true verdicts to ENVIRONMENT_SENSITIVE_ACCEPTANCE
(caught by comparing per-pair verdicts, re-measured, not relabelled).

KNOWN_P3 at ce6fc9d (non-load-bearing; no shipped datum triggers any; carried to the next change
of the files concerned, as N2.1 carried its P3s):

```text
P3-1  admission/README.md §3.1 is headed "the 23 valid requests" — it describes batches 1-3 only
      (the file's §3/§6 correctly say 40).
P3-2  delivery_anchors.py does not count "expected failure" / "unexpected success" as a status
      change (scripts/tests has no expectedFailure; delivery only adds files).
P3-3  ledger.py REGRESSED_GUARDS rows show the resolved rc_base/rc_cand; a guard regressing only
      under the symlinked spelling would be listed without its rc_alt (no shipped row has it).
```

Reviewer limits stated in #5: the batch 1-3 validator runs were not re-executed (argued from the
unchanged files and the 0/3077 latent count); alignment.py was not re-run (network).
