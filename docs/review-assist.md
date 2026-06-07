# Review-assist (advisory)

After CI is green and before the human merges: a per-criterion review. It reduces the
reviewer's blind spot (useful when you can't read the code deeply) — but it is
**advisory, never a gate**. The human is the final approver; the AI never merges.

## Steps

1. **Gather inputs.** `python -m emkeel.review <KEY>` prints a template with the
   ticket's Acceptance Criteria, one section each. Get the diff with `gh pr diff <N>`.
2. **Verdict per criterion.** For each `AC1..ACn`, the reviewer (AI and/or human) fills:
   - `verdict:` met / not-met / unsure
   - `evidence:` the file/lines in the diff that show it
3. **Concerns.** List anything outside the criteria worth flagging (design, risk).
4. **Ratchet.** Any criterion not backed by a test → file a test. Judgment you make
   once becomes a permanent deterministic check (so next time the machine guards it).
5. **Human approves.** Read the filled template, then merge. The AI never merges.

## Why advisory, not a gate

AI judgment is probabilistic — a non-deterministic CI gate would reintroduce the very
fragility Emkeel removes. So the layers are:

- **CI / gates (deterministic floor)** — tests, linters: cannot be faked.
- **Review-assist (advisory)** — shrinks the human's blind spot, criterion by criterion.
- **Human (final approver)** — judgment + merge.

What the review-assist proves with a test, it hands down to the deterministic floor.
