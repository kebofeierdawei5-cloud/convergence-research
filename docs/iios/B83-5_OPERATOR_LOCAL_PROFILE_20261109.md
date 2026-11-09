# B83-5 — local operator defaults and repeat-input reduction

**Date:** 2026-11-09  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Scope:** reuse of operator-owned portfolio and valuation preferences only. No research, valuation, risk-gate or decision logic changes.

## Operator experience

### First use

After Round B, the existing wizard collects the operator's portfolio risk constraints and primary valuation-model selection. It then asks once whether these values should be saved as local defaults. The default answer is **0 = do not save**. Saving requires an explicit `1`.

The saved profile is optional. Choosing not to save does not affect the current task or its report.

### Subsequent use

When a later task reaches operator context capture, IIOS displays a concise summary of each saved section and offers:

- `1` — reuse the saved value (default);
- `2` — re-enter and change it;
- `0` — manually enter values for this task without using the saved value.

If manually entered values differ from the current profile, IIOS asks separately whether to update the default. The default is **0 = keep the old profile**. It never silently rewrites saved settings.

An interrupted task continues to use its own journaled partial inputs. A later profile edit does not retroactively alter an existing task. The profile update date is shown before reuse so stale portfolio assumptions are visible.

## Stored data and location

Path:

```
~/.iios-private/local-pilot/profile/operator-defaults.json
```

Only these operator-owned values are stored:
- Cross-company portfolio guardrails: constraint status, add-risk permission, risk budget and initial/target/maximum position percentages. A deliberate `UNKNOWN` / `BLOCKED` / no-portfolio-input state can also be stored.
- The last selected valuation model family is stored only as a suggested default for the next company-specific model prompt. The operator must still confirm the model for every new company.

No per-company entry-price band, valuation project-scope decision, company research, ChatGPT response, holdings list, account identifier, credential, browser data or market-data API key is stored in this profile. The entry-price band must be entered separately for each company. For EPS_MULTIPLE, the question of whether the project/expansion value is already included in the baseline must be answered again for each company.

## Security and failure behavior

- Parent directories are checked for symlinks and kept at POSIX mode `0700`; the profile and lock file use `0600`.
- The profile must remain under the current user's home directory; path traversal is rejected.
- The file is opened without following symlinks, checked as a regular file, size-limited to 64 KiB and parsed as strict UTF-8 JSON.
- Schema and field allowlists are strict. Percentages, entry-price range, position ordering, model family, confirmation state and project-scope fields are validated before reuse.
- Writes use a same-directory private temporary file, flush/fsync and atomic replacement under a local process lock.
- Corrupt JSON, unsupported schema, unsafe path, symlink or invalid values fail closed. IIOS does not silently reset or overwrite an unreadable profile.
- Save/update always requires explicit operator confirmation. Existing saved values are not overwritten on a normal reuse.

**Important privacy limitation:** POSIX permissions restrict access by other local accounts but do not encrypt the file. The profile is not sent to GitHub by IIOS, but a user-configured whole-home backup or synchronization tool may still copy it. Use macOS FileVault and review local backup/sync policy. This is not a substitute for full-disk encryption.

## Test coverage

The local-pilot CI now compiles the new profile and quick-start modules and runs:
- private profile round-trip and file/directory permissions;
- invalid portfolio and valuation field rejection;
- symlinked private parent rejection;
- corrupt profile fail-closed behavior without reset;
- default reuse without invoking the manual prompts;
- opt-in save defaulting to no;
- the dedicated quick-start test file and existing one-shot clipboard tests.

CI is Ubuntu/Python 3.12. Passing CI does not establish macOS Finder, filesystem permission, FileVault or clipboard acceptance. B34 macOS acceptance and B89 full acceptance remain open.

## Explicit boundaries

This feature does not:
- infer or change portfolio constraints;
- auto-select a valuation model;
- change a task's journaled inputs after creation;
- store the profile in the repository or Git;
- add browser automation, background clipboard access, network calls or order execution;
- create a formal investment decision.

