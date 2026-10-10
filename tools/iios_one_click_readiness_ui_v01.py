from __future__ import annotations

"""Chinese, human-friendly renderer for the read-only IIOS readiness report."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.iios_one_click_readiness_v01 import CASE_ID, build_report


BLOCKER_TEXT = {
    "CASE_MANIFEST_MISSING": (
        "规范公司案例清单不存在。",
        "从 canonical main 恢复正式文件；不要手工重建或猜测字段。"
    ),
    "CANONICAL_REQUEST_BUNDLE_NOT_FOUND": (
        "找不到该公司的正式 canonical request bundle。普通案例模板、demo 和测试输入已明确排除。",
        "这不是让你继续去电脑里找文件。系统需要先增加受治理的请求包生成步骤，把真实投资请求与正式证据清单绑定；在此之前不能启动正式运行。"
    ),
    "REQUEST_BUNDLE_EVIDENCE_PATHS_NOT_USABLE": (
        "请求包引用的真实证据清单或原始证据目录无法在当前 canonical checkout 中完整验证。",
        "通过正式证据摄取流程恢复清单与原始字节；不能创建占位文件。"
    ),
    "CANONICAL_ADMISSION_ROOT_NOT_PROVISIONED": (
        "本次 GitHub 云端预检没有可用的正式 admission 根目录。云端运行环境无法读取你 Mac 上的本地文件夹。",
        "无需再手动选择目录，也不要把私有准入记录上传到 GitHub。后续必须在真正的执行 Host 上挂载已有的正式准入存储；没有正式记录时应先补齐受治理的准入流程。"
    ),
    "B2_LEDGER_MISSING": (
        "最新的 B2 证据/PIT 检查记录不存在。",
        "从 canonical main 恢复正式来源审查记录后再检查。"
    ),
    "B2_EVIDENCE_PIT_NOT_ADMITTED": (
        "B2 Evidence/PIT 仍未通过；605016 的 market_price 仍为 UNKNOWN / 未准入。",
        "继续解决截止时点正确、来源合法且满足 HTTPS 与复用授权要求的价格证据，再运行原有 B2/PIT 验证。不得修改阈值或人为标记通过。"
    ),
}


def render_chinese(report: dict) -> str:
    status = "阻塞（符合预期的 fail-closed 结果）" if report["status"] == "BLOCKED" else "预检候选通过，但未执行正式运行"
    b2 = report["b2"]
    lines = [
        "# IIOS 一键预检报告：605016", "",
        f"- **结果：** {status}",
        f"- **案例：** {CASE_ID}",
        f"- **Canonical main 检出版本：** {report['canonical_git_head']}",
        f"- **生成时间：** {report['generated_at']}",
        "- **本次操作范围：** 只读检查；不是投资结论、正式验收或交易授权。", "",
        "## 一眼看懂",
        f"- 公司证据清单：{'存在' if report['company_case_manifest_present'] else '缺失'}",
        f"- 找到正式请求包候选：{len(report['request_bundle_candidates'])} 个",
        f"- 本次运行可用的正式准入存储：{'是' if report['admission_root']['usable'] else '否'}",
        f"- Evidence/PIT 准入：{'通过' if b2['evidence_admission'] is True and b2['pit_admission'] is True else '未通过 / 未准入'}",
        f"- 缺失必需证据组：{', '.join(b2['missing_required_field_groups']) or '当前记录未列出缺失项'}", "",
        "## 为什么不能继续正式运行",
    ]
    if not report["blockers"]:
        lines.append("本次有限预检未发现上述阻塞项，但这不代表正式 canonical-run 已执行或投资案例已验收。")
    else:
        for i, blocker in enumerate(report["blockers"], 1):
            title, next_action = BLOCKER_TEXT.get(
                blocker["id"],
                (blocker.get("finding", blocker["id"]), blocker.get("next", "请按 canonical 合同修复后重新预检。")),
            )
            lines.extend([
                f"### {i}. {title}",
                f"**当前情况：** {title}",
                f"**下一步：** {next_action}", "",
            ])
    if b2.get("missing_required_field_groups"):
        lines.extend([
            "## 605016 当前最关键的真实数据阻塞",
            "截止时点要求下的市场价格证据尚未正式准入。现有记录指出：官方 SSE 日线数据候选只能通过普通 HTTP 获取，不能满足现有 HTTPS 摄取边界；Eastmoney 的复用条款要求事先书面授权；2026-10-09 当日收盘价不能替代原案例 2026-10-09 日期截止时点对应的价格。请继续寻找满足原规则的 HTTPS 来源，不要放宽 PIT 或复用条件。", "",
        ])
    lines.extend([
        "## 点击本次操作实际做了什么",
        "- 只检查了 GitHub 上 canonical 仓库里的正式文件，并生成报告。",
        "- 没有读取你电脑上的文件夹，没有创建或修改准入记录。",
        "- 没有调用 ChatGPT，没有运行正式投资决策链，没有生成正式 Decision、投资报告或完整 Run Receipt。",
        "- 没有执行或授权任何交易。Actions 任务显示成功，只代表报告成功生成；请以本报告内的“结果”字段为准。", "",
        "## 你可以直接打开的页面",
        "- [605016 公司证据清单](https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/manifests/company_cases/RC-CN-A-605016-20261009.json)",
        "- [最新 B2 阻塞记录](https://github.com/kebofeierdawei5-cloud/convergence-research/blob/main/evidence/real_cases/RC-CN-A-605016-20261009/FOLLOWUP_B2_RUN_20261010.json)",
        "- [打开免费 ChatGPT](https://chatgpt.com/)", "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--report-dir", default="artifacts/operator-readiness")
    parser.add_argument("--admission-root", default=os.environ.get("IIOS_CANONICAL_ADMISSION_ROOT"))
    args = parser.parse_args()
    root = Path(args.repo_root).expanduser().resolve(strict=True)
    out = Path(args.report_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(root, args.admission_root)
    report["status_zh"] = "阻塞" if report["status"] == "BLOCKED" else "预检候选通过（未执行正式运行）"
    markdown = out / f"{CASE_ID}-readiness.md"
    machine = out / f"{CASE_ID}-readiness.json"
    markdown.write_text(render_chinese(report), encoding="utf-8")
    machine.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "diagnostic_generation": "SUCCESS",
        "case_status": report["status"],
        "case_status_zh": report["status_zh"],
        "blocker_count": len(report["blockers"]),
        "markdown_report": str(markdown),
        "machine_report": str(machine),
        "formal_run_executed": False,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
