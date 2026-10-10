# P0 — Free ChatGPT Web Operator Runtime — 2026-10-10

**Purpose:** let the canonical IIOS request-interpreter and thesis-semantic callbacks use the user's free ChatGPT web UI without a local model, API endpoint, paid API key, browser automation, cookie access or private-session integration.

**Acceptance class:** operator-mediated callback implementation candidate. This is not API-backed provider authentication and is not production acceptance.

## Why manual handoff is used

ChatGPT Free web UI and the OpenAI API are separate products/interfaces; OpenAI's billing documentation explicitly says their billing systems are separate: https://help.openai.com/en/articles/9039756-managing-billing-settings-on-the-chatgpt-web-and-api-platform. The web UI does not expose a supported generic Responses API endpoint that this repository can call. This implementation does not reverse engineer web sessions or automate browser interaction.

Instead, IIOS emits the exact prompt to a private local handoff directory and fails closed with `CHATGPT_CHAT_RESPONSE_REQUIRED:<task_id>`. The operator pastes that prompt into ChatGPT Chat, copies the raw JSON response to a local file, imports it, and reruns the exact same canonical command. The next missing model stage emits its own distinct handoff.

## Runtime configuration

Set the canonical factory selector; no LLM provider endpoint, provider API key, or provider runtime-signing key is required for this manual channel:

```bash
export IIOS_CANONICAL_RUNTIME_FACTORY=iios_mvp.chatgpt_chat_runtime_v01:build_chatgpt_chat_runtime
export IIOS_CANONICAL_ADMISSION_ROOT=/absolute/path/to/canonical-admissions
export IIOS_CHATGPT_HANDOFF_ROOT=/absolute/path/to/private/chatgpt-handoff
```

The admission root must already exist and contain whatever canonical upstream admissions the requested case requires. Do not create synthetic admissions to make the runtime start.

## Operator loop

1. Run the unchanged canonical entry using the same staged request bundle, run ID, request ID and cutoff for every retry:

   ```bash
   python -m iios_mvp.cli canonical-run /absolute/path/to/request-bundle.json --out /absolute/path/to/run-output
   ```

2. The first attempt normally returns `BLOCKED` with reason `CHATGPT_CHAT_RESPONSE_REQUIRED:<task_id>`. Open `$IIOS_CHATGPT_HANDOFF_ROOT/requests/<task_id>.prompt.txt`, copy the **entire exact file** into ChatGPT Chat and ask it to return only the requested JSON object. Do not ask it to change the case, dates, schema or authority boundaries.

3. Copy the raw JSON response without Markdown fences into a UTF-8 text file. Import it with:

   ```bash
   python -m iios_mvp.chatgpt_chat_handoff_v01 import-response \\
     --root "$IIOS_CHATGPT_HANDOFF_ROOT" \\
     --task-id "<task_id>" \\
     --response-file /absolute/path/to/chatgpt-response.txt
   ```

4. Rerun the exact same `canonical-run` command. The imported response is available only for the matching task ID and prompt hash. After the request-intent stage validates, IIOS will create a second handoff for the thesis-semantic stage. Repeat the same copy/import/re-run loop.

5. Stop immediately on any schema, case-binding, evidence, PIT, resolver, valuation or Decision block. Do not edit the generated prompt, force a status, create admission records by hand, or treat a response as a passed gate.

## Integrity and provenance

- Prompt requests bind stage, run ID, request ID, case ID, cutoff date and exact prompt SHA-256.
- Response JSON must be a single strict JSON object. Markdown-wrapped output, duplicate keys, non-finite numbers, hash mismatches, task mismatch and mutation of an existing response are blocked.
- The handoff response and receipt files are private (0600), content-hashed and write-once. Replay also validates the receipt hash and its task/response bindings.
- **`provider_origin_verified=false` is mandatory.** A locally imported reply's hash proves file integrity relative to the saved bytes, not that OpenAI produced those bytes. The operator-reported origin is not cryptographically verified; this is not an OpenAI API-signed provider receipt.
- The content-hash receipt is a separate audit artifact in the handoff root. This candidate does not assert that it is already embedded as a formal signed provider receipt in the full `IIOS_RUN_RECEIPT`. That lineage integration remains subject to review and production acceptance.

## What it does not change

The current free ChatGPT manual route can supply only the two existing LLM callbacks: request intent and thesis-semantic proposal. It does not supply market data, source authenticity, PIT admission, an independent forecast, valuation inputs, authority records, or price. It does not bypass any upstream resolver. The 605016 case remains blocked wherever its `market_price` or any other required admission is UNKNOWN/unadmitted.

This does not call or authorize ChatGPT to decide or execute a trade. Formal Decisions remain deterministic IIOS outputs after their gates; human approval remains mandatory; automatic order execution is disabled.

## Validation plan

The dedicated workflow runs the operator-handoff contract tests, compiles both modules, and checks formatting. CI never calls ChatGPT and never claims a live ChatGPT response. Real operator use is separately recorded as a manual-run artifact; P0-LLM-001/P0-LLM-004 remain OPEN until the complete real-company provenance chain, report, full receipt replay and independent red-team pass.
