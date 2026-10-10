# IIOS 一键预检入口（只读）— 2026-10-10

## 怎样操作

打开 GitHub Actions 中的 **IIOS — One-click case readiness (read-only)**，阅读授权说明，勾选“仅授权只读预检”，再点击 **Run workflow**。任务完成后先读 Actions 页面里的中文摘要；同时会附上中文 Markdown 和机器 JSON，可直接下载留档。

这取代之前需要你在 Mac 上手动寻找 request bundle 和 admission 根目录的步骤。预检不需要这些本机路径。

## 这次授权了什么

该入口只检查 canonical 仓库中可见的文件，排除 demo、模板与测试夹具后寻找正式请求包，并读取提交到仓库的 B2 结果。不会读取本机文件，不会创建或修改准入记录，不会调用 ChatGPT，不会执行 canonical-run，不会发布正式 Decision、报告或完整 Run Receipt，也不会授权下单。

Actions 任务变绿只代表诊断报告成功生成，不能当作投资案例通过。请以报告内的“结果”字段为准。

## 当前已知阻塞

canonical 的 605016 B2 记录显示 market_price 仍为 UNKNOWN/未准入，evidence_admission=false、pit_admission=false。GitHub 托管 runner 无法访问 Mac 上的本地准入目录。不要上传私有 admission 文件到 GitHub，也不要创建占位记录。

报告会明确提示：当前仓库找不到完整的正式 request bundle；在真实执行 Host 中也没有挂载可用的正式 admission store。该入口不会伪造这两个缺失项。

## 真正运行前仍要完成的事项

1. 按现有 B2/PIT 合同，取得截止时点正确、来源可接受且复用授权成立的市场价格证据。
2. 通过受治理的请求暂存流程，把真实投资请求绑定到实际准入的证据清单与原始字节。
3. 在正式执行 Host 中挂载与案例匹配的持久化准入存储。
4. 手动使用免费 ChatGPT 网页完成当前支持的两个回调；保留 provider_origin_verified=false。
5. 运行正式 canonical 入口，完成输出与 Run Receipt 全链条复核及独立审计。

一键预检只负责把阻塞说清楚，不声称完成上述任何步骤。
