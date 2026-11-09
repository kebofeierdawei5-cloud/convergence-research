# B83-6 — compact new-research entry and launcher environment checks

**Date:** 2026-11-09  
**Branch:** `feat/b83-durable-task-resume-20261108`  
**Scope:** operator input reduction and local launcher safety only. Research prompts, evidence, valuation arithmetic, return hurdles and decision gates are unchanged.

## New-research input flow

The ordinary new-research entry now asks for six items, with safe defaults where possible:

1. Company name.
2. Ticker. A/H market is inferred from the unambiguous ticker syntax or code length; there is no separate market-selection prompt.
3. Analysis cutoff. Press Enter for the latest weekday close that is not in the future in Shanghai time. Entering `YYYY-MM-DD` means that date at 15:30 Shanghai time. For a strict date-level cutoff, enter an explicit timestamp such as `2026-11-09T00:00:00+08:00`.
4. Current position percentage; default is `0`.
5. Operator-attested current price, with optional observation date/time in the same field:
   - `19.74` — use the default observation date and 15:00 Shanghai close.
   - `19.74@2026-11-06` — use the specified date at 15:00 Shanghai time.
   - `19.74@2026-11-06T14:30:00+08:00` — use the specified exact instant.
6. One confirmation screen summarizing company, inferred market, cutoff, price, observation time and holding.

This removes the standalone market, cutoff-mode, price-observation-date and price-time-mode prompts. The price is still manually supplied and is explicitly labeled `OPERATOR_ATTESTED_NOT_SOURCE_VERIFIED`.

## Market inference rules

- Six-digit code, or explicit `SH` / `SZ` / `BJ` prefix/suffix: A-share market.
- Four- or five-digit code, `HK` prefix or `.HK` suffix: Hong Kong market.
- Unrecognized or malformed input fails with an actionable error; IIOS does not silently guess.

Four-digit HK inputs are zero-padded to five digits when normalized.

## Point-in-time and date safeguards

- Default cutoff date uses Asia/Shanghai, not the Mac's local timezone.
- The default is the latest weekday close that is not in the future: before 15:30 on a weekday, it rolls back to the preceding weekday; at/after 15:30, it may use that day's close; on weekends, it rolls back to Friday.
- A full ISO timestamp must include a timezone and is normalized to Shanghai time.
- The default price observation date respects the cutoff clock. A cutoff before 15:00 cannot default to that day's 15:00 price.
- Price observation date must be a weekday and price-known-at must not exceed the cutoff.
- No exchange holiday calendar is consulted. A weekday may still be a market holiday; the operator must verify that the observation date was an actual trading day.

## Launcher environment boundary

`IIOS.command` now:
- sets `umask 077` for files created by the launcher process;
- uses the project's `.venv/bin/python` if that environment exists; if it is broken, stops rather than silently selecting another Python;
- otherwise uses the existing `python3`;
- requires Python 3.10 or newer and imports the quick-start entry before launch;
- uses `PYTHONNOUSERSITE=1` and an explicit project `PYTHONPATH`;
- does not install packages, use network bootstrap, call shell `eval`, use `sudo` or automate a browser session.

GitHub's contents API does not preserve the executable bit. After checkout, the one-time `chmod +x IIOS.command` remains required before Finder double-click.

## Tests and acceptance

New tests cover:
- A/H market inference including bare 6-digit A and 4/5-digit HK formats;
- HK four-digit normalization;
- Shanghai cutoff parsing and latest-completed-close defaulting;
- one-line price parsing with date or exact timestamp;
- rejection of a price known after cutoff and weekend observations;
- launcher isolation, Python version and no-bootstrap boundaries;
- the new compact wizard sequence and interruption-safe existing guided workflow.

Latest observed prior B83-5 validation: 394 passed. B83-6 introduced a first CI run with 409 passing and 2 failing (bare 5-digit HK inference and one test still using the old prompt sequence). Both issues have been corrected in subsequent commits; the corrected branch run is pending / not yet confirmed at the time this document was authored.

CI runs Ubuntu / Python 3.12. It does not establish real macOS Finder, local virtualenv, clipboard permission or full real-company acceptance. B34 macOS acceptance and B89 full acceptance remain open.

No canonical main changes; PR #588 remains Draft and unmerged.
