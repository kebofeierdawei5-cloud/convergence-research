# macOS 命令文件执行权限重复故障记录

日期：2026-10-20  
重复次数：用户确认这是第 4 次相似故障。  
范围：IIOS 当前主线一键启动器与全流程 + Replay 本地验收入口。  
性质：交付 / 启动方式缺陷；不是投资计算结论，也不证明底层代码本身失败。

## 已确认的流程缺口

以前的交付说明要求从 GitHub 单独下载原始 .command 文本文件，再在 Finder 中双击。这个路径没有验证下载后的 Unix 执行权限；CI 只验证过 Bash 语法，没验证最终发行包中的 POSIX mode，也没有把“通过 Bash 显式解释执行”写成标准回退。于是同一类“没有执行权限”问题反复落到用户身上。

不能把“脚本语法通过”等同于“用户下载后能够启动”。必须同时验证：
1. 发行 ZIP 中的每个 .command 文件记录 Unix mode 100755；
2. 自动化测试读取 ZIP 外部属性并断言权限位；
3. README 提供不依赖执行位的调用方式；
4. 发布与验收默认采用工作流生成的 ZIP 发行包，不再把 raw 单文件下载当作推荐路径。

## 立即可用的无 chmod 运行方式

若文件直接保存在 Downloads，打开 Terminal 后运行：

    /bin/bash "$HOME/Downloads/IIOS_独立安全启动当前主线.command"

若命令文件位于刚解压的 ZIP 子目录内，则在 Terminal 输入 /bin/bash （末尾保留一个空格），把 Finder 中的 .command 文件拖进 Terminal，再按回车。Terminal 会填入其实际路径。这个方式让 Bash 读取脚本文本，不要求该文件自身带有执行位。

不要为了处理这类故障反复让用户运行 chmod +x；它可以临时绕过问题，但不能修复交付流程。也不要建议关闭 Gatekeeper 或其他系统安全功能。

## 后续强制规则

- 推荐交付物为 GitHub Actions 的 IIOS macOS launcher distribution 工作流产出的 IIOS-macos-launchers-SHA.zip。
- 每次修改启动器或打包脚本，必须运行发行包构建、Unix mode 验证和权限回退说明测试。
- ZIP 的每个 .command 文件都必须保存 POSIX mode 100755；如果校验不符，打包流程失败，不上传产物。
- 即使 ZIP 模式验证通过，操作说明仍保留 /bin/bash 回退，避免再次让用户陷入 Finder 执行权限问题。
- 私有研究输入、分析报告、运行回执、日志及验收 ZIP 始终写入 ~/.iios-private/，不进入 Git 发行包或代码提交。
