# Path A macOS One-Click Launcher Permission Failure — 2026-10-11

## Observed operator failure

The local launcher returned `OUTPUT_ROOT_PERMISSIONS_TOO_OPEN`, followed by a Bash `nounset` error on the error-reporting line. The analysis command did not proceed past the output-root safety gate, so this event is **not** a failed valuation calculation and provides no analysis result.

## Root cause

1. The launcher used `mkdir -p` for `~/.iios-private/scenario-analysis` but did not set the new output-root directory mode. With a normal macOS umask this can leave group/other permission bits enabled.
2. The scenario module intentionally fails closed when an existing output root is too open; it does not silently chmod an operator-owned directory.
3. The operator's second error indicates an unset-parameter expansion in the executed launcher variant. The fixed launcher initializes the exit-code variable and uses an ordinary braced expansion on the error path.

## Fix

The tracked replacement launcher:
- uses `mkdir -m 700` for a new output root;
- rejects symlinks, non-directories and output roots owned by another UID;
- if an existing output root is owned by the current user but has group/other permission bits, asks explicitly before changing **only that directory** to mode `0700`;
- does not delete or overwrite any existing analysis bundle and blocks if the operator cancels;
- initializes and quotes the Python exit code so `set -u` cannot mask the original failure;
- retains pinned GitHub commit and Git blob SHA-1 checks for the Python modules.

The separate ZIP is generated from this tracked launcher and passed `bash -n` plus ZIP integrity checks. CI static tests cover launcher syntax, permissions guard and pinned hashes.

## Non-goals / current state

This correction does not make a local Mac run pass; actual operator replay remains pending until the user launches the replacement bundle. It does not admit the private price input into canonical evidence, validate source-use rights, create a formal Forecast/Valuation/Decision, or change C1/C2 signer gates. No prices are uploaded to GitHub by the launcher.
