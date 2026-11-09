# B83-5 — local operator defaults and repeat-input reduction

**Date:** 2026-11-09  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Scope:** reusable portfolio guardrails and a valuation-model suggestion only. No research, valuation, risk-gate or decision logic changes.

## Operator experience

### First use

After Round B, the existing wizard collects the operator's portfolio constraints, this company's entry-price band and this company's primary valuation-model choice/project scope. IIOS then asks once whether to save reusable defaults. The default answer is **0 = do not save**. Saving requires an explicit `1`.

The saved profile contains only the cross-company portfolio guardrails and the last selected model family as a future suggestion. It does **not** store the current company's entry-price band or project-in-baseline decision.

### Subsequent use

When a later task reaches operator context capture, IIOS shows the profile's last update date and a concise summary of the saved portfolio guardrails. One prompt offers:

- `1` — reuse the saved cross-company portfolio guardrails (default);
- `2` — re-enter and change them;
- `0` — manually enter constraints for this task without using the saved values.

When saved portfolio guardrails are reused and the constraint status is PASS, the system still asks for a fresh entry-price band for the current company. That price band never comes from the profile.

The last selected valuation model is displayed as the default choice in the current company's model prompt. It is only a preselection: the operator must confirm or change it for every company. For EPS_MULTIPLE, whether the relevant project/expansion value is already included in the baseline is asked again for every company.

If manually entered reusable preferences differ from the profile, IIOS asks whether to update the defaults. The default answer is **0 = keep the old profile**. It never silently rewrites saved settings.

An interrupted task continues to use its own journaled partial inputs. A later profile edit does not retroactively alter an existing task.

## Stored data and location

Path:

```
~/.iios-private/local-pilot/profile/operator-defaults.json
```

Profile schema: `IIOS-LOCAL-OPERATOR-PROFILE-0.2`.

Stored values:
- Cross-company portfolio guardrails: constraint status, add-risk permission, risk budget, and initial/target/maximum position percentages. A deliberate `UNKNOWN` / `BLOCKED` / no-portfolio-input state can also be stored.
- Last selected valuation model family, used only as the default suggestion in the next company's model-selection prompt.

Not stored:
- Per-company entry-price band.
- Whether the project/expansion is included in a specific company's baseline valuation.
- Company research, ChatGPT responses, holdings list, account identifiers, credentials, browser data or market-data API keys.

## Security and failure behavior

- Parent directories are checked for symlinks and kept at POSIX mode `0700`; the profile and lock file use `0600`.
- The profile must remain under the current user's home directory; path traversal is rejected.
- The file is opened without following symlinks, checked as a regular file, size-limited to 64 KiB and parsed as strict UTF-8 JSON.
- Schema and field allowlists are strict. Cross-company percentages, position ordering and suggested model family are validated on load. The current company's entry-price band and project-scope decision are separately collected and validated in that task.
- Writes use a same-directory private temporary file, flush/fsync and atomic replacement under a local process lock.
- Corrupt JSON, unsupported schema, unsafe path, symlink or invalid values fail closed. IIOS does not silently reset or overwrite an unreadable profile.
- Save/update always requires explicit operator confirmation. Existing saved values are not overwritten on a normal reuse.

**Important privacy limitation:** POSIX permissions restrict access by other local accounts but do not encrypt the file. The profile is not sent to GitHub by IIOS, but a user-configured whole-home backup or synchronization tool may still copy it. Use macOS FileVault and review local backup/sync policy. This is not a substitute for full-disk encryption.

## Test coverage

The local-pilot CI compiles the profile, quick-start and guided runner modules and runs:
- private profile round-trip and file/directory permissions;
- exclusion of per-company entry-price band and project scope from saved profile;
- invalid portfolio and valuation field rejection;
- symlinked private parent rejection;
- corrupt profile fail-closed behavior without reset;
- default portfolio reuse while requiring current-company price-band input;
- last model family used as a suggestion, not an automatic valuation decision;
- opt-in save defaulting to no;
- dedicated quick-start and one-shot clipboard tests.

Latest observed local-pilot CI: Ubuntu / Python 3.12, **394 passed**. Passing CI does not establish macOS Finder, filesystem permission, FileVault or clipboard acceptance. B34 macOS acceptance and B89 full acceptance remain open.

## Explicit boundaries

This feature does not:
- infer or change portfolio constraints;
- auto-select or auto-confirm a valuation model;
- reuse a prior company's price zone or project-scope assumption;
- change a task's journaled inputs after creation;
- store the profile in the repository or Git;
- add browser automation, background clipboard access, network calls or order execution;
- create a formal investment decision.
