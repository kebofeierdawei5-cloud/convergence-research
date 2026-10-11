# Path A — Operator-attested price input for private scenario analysis

- Date: 2026-10-11
- Status: IMPLEMENTED IN PR #354; ANALYSIS-ONLY; NOT CANONICAL PRICE ADMISSION
- Data handling: actual operator quote values and source labels stay in the operator's private file; this public document deliberately records no numerical quotes.
- Runtime: deterministic Python only; no local LLM, Ollama, external model API, or paid provider is required.

## 1. Intent and non-claims

Path A is the low-friction way to keep valuation / target-entry / price-sensitivity analysis moving when the operator manually supplies a current or recent close. It creates an explicitly labelled `OPERATOR_ATTESTED_MARKET_DATA` input usable by scenario valuation.

It is **not** any of the following:
- source-origin verification;
- source-vintage verification of the exchange/vendor's original bytes;
- written data-use permission;
- formal company Evidence/PIT admission;
- canonical current-price registry admission;
- authority to create a formal IIOS Decision, publication, complete Run Receipt or execution permission.

The SHA-256 values in the local receipt attest only to the exact submitted JSON and normalized private record bytes. They are not signatures by the exchange, Sina, Sohu, FinanceResult, or any other source. Source names, quote values and timestamps remain operator-asserted unless separate evidence verifies them.

## 2. Time semantics and frozen-case protection

The existing C1 (605016) and C2 (002001) historical cases use date-only cutoff `2026-10-09`, interpreted as **2026-10-09 00:00:00 Asia/Shanghai**. Therefore, a closing price observed later on 2026-10-09 cannot be inserted into either frozen case's original PIT record.

The operator-supplied prices have been assigned a separate price-analysis overlay with cutoff `2026-10-10` (start of day Asia/Shanghai), so the operator-attested observation times are before the overlay cutoff. This is only the price-input's temporal check:
- the frozen base-case cutoff is not edited;
- the entire company evidence set has **not** been revalidated as a unified `2026-10-10` PIT case;
- the overlay is not a new, canonical Case admission and cannot independently produce a formal decision.

When evaluating the result, label it as a price-updated scenario on the previously reviewed thesis/fundamentals, and flag any material company announcements between the base cutoff and the overlay cutoff for human review.

## 3. Schema and private-file contract

The incoming private JSON has this shape (the following is a template with no real quote values):

```json
{
  "schema_version": "IIOS-OPERATOR-ATTESTED-PRICE-INPUT-0.1",
  "operator_confirmed": true,
  "analysis_cutoff_date": "2026-10-10",
  "batch_id": "path-a-prices-20261011",
  "records": [
    {
      "base_case_id": "RC-CN-A-002001-20261009",
      "market": "CN-A",
      "symbol": "002001",
      "exchange": "SZSE",
      "observation_date": "2026-10-09",
      "price": "ENTER_OPERATOR_PRICE",
      "currency": "CNY",
      "adjustment_semantics": "UNADJUSTED_CLOSE",
      "operator_attested_known_at": "YYYY-MM-DDTHH:MM:SS+08:00",
      "sources_claimed": ["ENTER_SOURCE_NAMES"],
      "attestation_note": "Operator-attested input; source origin and rights remain unverified."
    }
  ]
}
```

Use one record per symbol and observation date. Accepted fields:
- six-digit A-share symbol and matching exchange code;
- positive finite price, CNY/share, explicitly unadjusted close;
- ISO observation date and a timezone-aware, operator-attested time on that date;
- a date-only analysis cutoff whose Shanghai-local start is later than the attested time;
- non-empty source claims and explicit operator confirmation.

The file must remain outside the public repository. The ingestion helper writes:
- the private normalized price record, mode `0600`, containing quote values;
- a sanitized receipt, mode `0600`, containing the symbol/date and status only, not quote values or source labels.

Files are immutable in the helper; a rerun refuses to overwrite either output. Keep the input and private normalized record out of GitHub, CI artifacts, chat transcripts not needed for analysis, and public reports.

## 4. Local no-model command

From a canonical checkout with the repo's Python test/runtime dependencies installed, save the manually entered input JSON under the private directory and run:

```bash
python -m iios_mvp.operator_attested_price_input_v01 \
  --input "$HOME/.iios-private/incoming/operator-attested-prices-path-a.json" \
  --private-root "$HOME/.iios-private/analysis-inputs"
```

Only the price-redacted receipt is printed. The actual normalized prices are written to the private root. Do not paste the normalized file into ChatGPT or commit it to Git.

The deterministic resolver `resolve_scenario_price(...)` explicitly returns an `OPERATOR_ATTESTED_SCENARIO_INPUT_ONLY` object. It may feed scenario valuation but cannot feed the canonical current-price resolver or grant formal-decision authority. The existing canonical price registry, Evidence/PIT validator, signed-admission registry and decisions are not modified by this path.

## 5. Path A result semantics

For each record, the following controls must always remain false:
- `source_origin_verified`
- `source_vintage_verified`
- `source_use_rights_verified`
- `canonical_price_admission`
- `formal_evidence_pit_admission`
- `decision_authority`

The analysis may report price-relative valuation, expected-return sensitivity, target-entry gap and scenario sizing, but must show a conspicuous textual qualification such as:

> **价格输入：人工确认；仅供估值/情景分析，不代表正式行情证据准入。** 本分析使用的是操作者提供的未复权收盘价；来源原始字节、精确首次公开时间、行情使用权限及同一截止时点的全部公司证据尚未被正式复验。投资结论为条件性研究结论，不构成已通过 IIOS canonical 决策门控的正式 Decision。

Do not output `SOURCE_VINTAGE_VERIFIED` for these records. Do not use them to claim formal BUY/ADD/REDUCE decisions, canonical publication, completed Run Receipt or trade execution authorization.

## 6. Closure criteria for formal route

Path A is immediately usable for scenario work after local private-input validation. The separate formal route remains open until the appropriate market-data use basis, source-vintage evidence, authorized trusted signer(s), independent signature verification and any full Case PIT requirements all pass. This distinction is intentional; manual input reduces an operational bottleneck without weakening IIOS's evidence authority.
