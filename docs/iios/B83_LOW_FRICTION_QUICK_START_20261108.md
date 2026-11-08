# B83-4 — Low-friction local quick start

**Date:** 2026-11-08  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Scope:** operator workflow only; no research, valuation, risk-gate or decision-model changes.

## Delivered

1. `python -m iios_mvp.quick_start_v01` is a stable quick-start entry point.
2. If exactly one unfinished durable task exists, it resumes that task without asking the user for a Task ID.
3. If several unfinished tasks exist, it asks for one numbered choice and shows company, ticker and current stage; it does not guess.
4. If no unfinished task exists, it starts the existing guided wizard.
5. Completed tasks are ignored. A blocked task, symlinked private path, invalid task entry, or corrupt/unverifiable task stops quick start rather than being silently skipped.
6. `IIOS.command` is a local macOS launcher. It uses the repository's `.venv/bin/python` when present, otherwise the existing `python3`; it does not install dependencies, contact a server, request elevated privileges, or run an updater.

## First-time launcher setup

The GitHub file-contents interface stores a new script as non-executable. After checking out this branch, run this one-time command from the repository root:

```bash
chmod +x IIOS.command
```

After that, double-click `IIOS.command` in Finder to launch IIOS. The launcher remains tied to its own repository directory; it does not depend on the shell's current working directory.

## Normal use

- One unfinished task: launch; IIOS continues from the verified journal-derived phase.
- Multiple unfinished tasks: launch; choose the numbered company/ticker entry.
- No unfinished task: launch; enter a new research case.
- At Round A/B: send the copied prompt in ChatGPT, copy the complete answer, return to the IIOS terminal and press Enter once. Existing B83-3 clipboard intake reads the clipboard once only after that explicit Enter action. No TextEdit or JSON file editing is needed on the normal path.
- Invalid/incomplete answers continue through the existing repair and validation path; they do not advance the durable task.

## Security boundary

- No browser automation, cookies, passwords, session tokens, Accessibility permission, screen recording, clipboard polling or background clipboard daemon.
- Clipboard read remains one-shot and user-triggered; response bytes remain subject to the existing 2 MiB / UTF-8 / immutable-attempt / schema validation path.
- AI output is parsed as data; it is never executed as code or shell input.
- Task discovery verifies each candidate task through the existing journal and artifact hash checks. Ambiguous/corrupt/blocked state fails closed.
- No sudo, auto-install, auto-update, network call, order execution or formal decision authority is added.
- The launcher does not repair or bypass a broken Python environment. It reports the problem without silently changing the machine.

## Validation status and acceptance boundary

- New quick-start routing tests are in `tests/test_quick_start_v01.py`.
- GitHub Actions must validate the new commits; no result is claimed until observed.
- Real macOS acceptance remains required for the executable bit, Finder launch, local Python environment, ChatGPT copy/paste flow and interruption/resume.
- The quick-start code does not close B34 macOS acceptance or B89 full acceptance.
- PR #588 remains Draft and unmerged. Canonical `main` is unchanged.

## Explicit non-goals

This slice does not yet replace the initial new-company data-entry wizard with a saved-profile form, and it does not automate ChatGPT sending or browser interaction. Those would add separate permission/security and product-design decisions. The current aim is to remove Task ID handling, manual response-file editing and manual resume command construction first.
