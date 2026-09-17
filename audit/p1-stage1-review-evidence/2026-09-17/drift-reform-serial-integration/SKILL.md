---
name: drift-reform-serial-integration
description: Re-form a reviewed candidate lane onto a moved base and integrate it ff-only, without rewriting history or laundering a review PASS. Use when a stage integrates lanes serially and the second lane's base is now stale ("MASTER_DRIFT"), when a candidate must be cherry-picked onto a newer main before merging, when a prior review PASS must be re-bound to a new SHA rather than renamed, or when a serial ff-only main integration needs honest CI classification. Triggers include "MASTER_DRIFT", "stale base", "re-form", "rebase the candidate onto main", "ff-only integrate", "re-bind the review to the new SHA", "the reviewed SHA is no longer a descendant of main".
agent_created: true
---

# Drift re-form + serial ff-only integration

Integrate a **reviewed** candidate whose base has moved, without rewriting reviewed history and
without laundering a review verdict onto a SHA that was never reviewed.

## When this applies

- A stage declares an integration **order** (e.g. `LANE A -> LANE B`) and integrating A moves `main`.
- B was branched from the pre-A base, so B's tip is **no longer a descendant of main**.
- You must land B anyway, and B already holds a review PASS at its old SHA.

## The one distinction that decides everything

```
MASTER_DRIFT      = mechanical sequencing condition  -> RE-FORM + FRESH REVIEW   (proceed)
CONTENT_CONFLICT  = the two changes disagree         -> STOP, adjudicate        (do not proceed)
```

`MASTER_DRIFT != CONTENT_CONFLICT`. Establish which one you have **before** choosing a merge method —
this is the difference between routine work and a STOP.

**Authorities to read first (in this order):**

1. the repo's git/CI/integration reference — the `MASTER_DRIFT` / `CONTENT_CONFLICT` clause and the
   exact-SHA review clause ("when blast radius did not expand, fresh review = previous reviewed SHA
   + delta").
2. the repo's stage/execution reference — the clause requiring the *later* integrator to re-fetch and
   re-form before merging.
3. the repo's review-and-repair reference — for the independence rules and the repair budget.

Do **not** assume the merge method. Search for the repo's own override of the ff-only default before
using the default (`grep -E 'OVERRIDE *=' -r <repo>` — definitional prose only, no active override,
means the default stands). A host (GitHub/GitLab) setting is **not** the policy source.

## Procedure

### 1. Classify, don't guess

```bash
git fetch origin
git merge-base --is-ancestor <INTEGRATED_SHA> <CANDIDATE_SHA> || echo "MASTER_DRIFT"
# and prove the two lanes' write surfaces are disjoint:
comm -12 <(git diff --name-only <BASE> <TIP_A> | sort) \
         <(git diff --name-only <BASE> <TIP_B> | sort)     # empty => disjoint
```

### 2. Prove content identity, two independent ways

Never assert "the re-form changed nothing" — measure it.

```bash
# (a) per-path blob identity
for f in $(git diff --name-only <BASE> <OLD_TIP>); do
  a=$(git rev-parse <OLD_TIP>:"$f"); b=$(git rev-parse <NEW_TIP>:"$f")
  [ "$a" = "$b" ] || echo "DIFFERS: $f"
done

# (b) aggregate contribution-patch digest — must be identical for both bases
git diff <OLD_BASE> <OLD_TIP> | shasum -a 256
git diff <NEW_BASE> <NEW_TIP> | shasum -a 256
```

Record both digests in the evidence file. A non-empty delta is **not** automatically fatal — it just
means the delta review must actually review the delta.

### 3. Prove the base advance cannot reach the candidate

The strongest available certificate is **additivity**:

```bash
git diff --numstat <OLD_BASE> <NEW_BASE> -- <every file the candidate references>
git diff <OLD_BASE> <NEW_BASE> -- <those files> | grep '^-' | grep -v '^---'   # must be EMPTY
```

**If deletions on the base advance are zero, anchor rot is mechanically impossible** — a change that
deletes nothing cannot delete the anchor the candidate cites. Also compute field/key-name collisions
between the two lanes; the intersection must be empty.

### 4. Re-form

```bash
git worktree add -b <branch>-reform ../<wt> <NEW_BASE_SHA>
git cherry-pick <OLD_BASE>..<OLD_TIP>
```

Do **not** amend/squash/rebase-rewrite the old commits. The old reviewed SHA must stay addressable on
its original branch (keep that branch pushed). `git merge --ff-only` only — the integrator authors no
commit, so the commit-count delta equals the candidate's commit count.

### 5. Budget the review honestly

- Re-run the repo's full local gate harness on the re-formed tree, then get **real CI bound to the new
  exact SHA** (push the branch; confirm the run's `head_sha` equals the new tip). `LOCAL_TESTS != REAL_CI`.
- Commission a **fresh, independent DELTA review** by a context that did not author anything. Two
  reviewers with different framings is the safe default (identity/non-interference + adversarial).
- **Never rename the old PASS into a new-SHA PASS.** The re-formed SHA gets its own review artifact
  that *cites* the content-identity proof. This is the single most common way a re-form launders
  evidence.

### 6. Integrate and verify

```bash
git merge --ff-only <NEW_TIP>
git push origin main                    # see §Auth note below
```

Then re-verify from **more than one read channel** (e.g. `git ls-remote` + two API/`gh` reads), check
the tree hash matches the candidate, re-check ancestry of every prior integration commit, and confirm
the post-main CI run's `head_sha` equals the new main.

## Honesty rules that reviewers actually enforce

- **`NOT_TRIGGERED` / `UNKNOWN` / `KNOWN_BASELINE_FAILURE` / `SKIPPED` are never PASS.** A workflow
  excluded by a `paths:` filter is a non-PASS state — declare it with the full non-PASS evidence block
  and classify the blocker (`SCHEDULING` for a path filter), rather than quietly omitting it or
  reporting "all CI green".
- Worker CI classification is `PROPOSAL_ONLY` until an independent reviewer accepts it.
- Distinguish *point-in-time* from *authoritative*: a recovery snapshot's `last_verified_remote_sha`
  legitimately lags HEAD; durability is proven by remote verification + CI, never by a self-referential
  follow-up commit. Do not build SHA-chasing loops.
- A recovery snapshot is never authoritative over the live tracker. On conflict, the tracker wins.
- If the base advance was **not** additive, downgrade the claim from "provably non-interfering" to
  "reviewed delta" and say so.

## Environment gotchas (WorkBuddy sandbox, macOS)

- **`grep` BRE alternation silently fails.** `grep "A\|B" f` returns nothing with `rc=1` *even when
  matches exist*, while `grep -E "A|B"` and plain single patterns work — the binary is a brokered
  shim. **Never conclude absence from a `\|` grep.** Use `-E`/`-F`, or the built-in search tool.
  Re-run any earlier `\|` search before relying on its emptiness.
- **`sitecustomize.py` shim via `PYTHONPATH`** makes some `mkdir`-using tests fail with
  `PermissionError(EEXIST)`. Run python as `env -u PYTHONPATH <python3>` and wrap this in a gate
  script so local evidence is faithful; classify the failures as a sandbox artifact, not a repo defect.
- **An invalid `GH_TOKEN` may be exported.** Use `env -u GH_TOKEN gh ...` and
  `env -u GH_TOKEN git -c credential.helper='!gh auth git-credential' push ...`. A public repo makes
  anonymous fetch succeed, masking the problem until the first push.
- The repo's own link checker may validate only *file* existence, not `#fragment` — resolve anchors
  yourself when a fixture cites one.

## Close-out

Before declaring the lane closed: re-verify **every** item of the ticket's `CLOSURE_EVIDENCE`
checklist at the integrated SHA (not at the old candidate SHA), persist live state to the tracker as a
**comment** (never by mutating the reviewed contract body), recompute the frontier from **fresh**
tracker state, and surface — do not unilaterally decide — any state-flush merge that would require
direct master construction.
