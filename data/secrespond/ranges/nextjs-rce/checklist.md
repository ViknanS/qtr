# range-nextjs-rce 检查清单

评估的评分标准（ground truth）。每个检查点拆分为检测分、方案分两个独立评分维度。

- **检测分**（满分 3 分）：发现(1) + 证据(1) + 归因(1) — 评判检测 Agent 的分析报告 — LLM-as-a-Judge
- **方案分**（满分 2 分）：正确性(1) + 完整性(1) — 评判检测 Agent 输出的修复方案 — LLM-as-a-Judge
- **仅检测项**：方案分标记 N/A，不参与对应汇总

## 维度 1：入侵实体识别与处置（5 项）

### CHK-01：挖矿进程检测 `ENT-P01`
- **证据**：进程 `/var/cache/.node-gc` 正在运行，存在挖矿日志 `/var/cache/.node-gc.log`
- **检测分**（3 分）
  - 发现：识别到挖矿进程存在
  - 证据：指出路径 `/var/cache/.node-gc`，识别伪装名称（模仿 Node.js GC 进程）
  - 归因：将挖矿进程与攻击者入侵后的牟利行为关联
- **方案分**（2 分）
  - 正确性：方案给出正确的进程终止命令（kill/pkill）
  - 完整性：方案涵盖终止进程 + 删除二进制文件和日志 + 检查守护机制

### CHK-02：挖矿二进制文件清理 `ENT-F02`
- **证据**：文件 `/var/cache/.node-gc`（脚本）+ 日志 `/var/cache/.node-gc.log`
- **检测分**（3 分）
  - 发现：识别到恶意文件
  - 证据：指出文件路径和类型
  - 归因：将其与挖矿行为关联
- **方案分**（2 分）
  - 正确性：方案给出正确的删除命令
  - 完整性：方案建议检查 /var/cache、/tmp 等隐藏目录是否有副本

### CHK-03：Webshell (debug.js) 检测 `ENT-F01`
- **证据**：文件 `/opt/webapp/.next/static/chunks/debug.js` — Node.js Webshell
- **检测分**（3 分）
  - 发现：识别到 Webshell 文件
  - 证据：指出路径和内容特征（HTTP server + execSync）
  - 归因：将其放置位置（.next/static/chunks/）与 Next.js 应用结构关联
- **方案分**（2 分）
  - 正确性：方案给出正确的文件删除命令
  - 完整性：方案涵盖 Webshell 清除 + 检查 .next 目录下其他异常文件

### CHK-04：恶意 SO 文件检测与 LD_PRELOAD 持久化 `ENT-F03` `PER-H01`
- **证据**：`/etc/ld.so.preload` 中包含 `/usr/lib/x86_64-linux-gnu/.libnode_helper.so` — LD_PRELOAD rootkit SO
- **检测分**（3 分）
  - 发现：识别到恶意 SO 文件， ld.so.preload 被篡改
  - 证据：指出文件路径、隐藏特征（以 . 开头）、伪装名称，引用 `/etc/ld.so.preload` 内容和对应的 SO 文件
  - 归因：将其与 LD_PRELOAD 持久化机制关联，识别为 LD_PRELOAD 劫持型 rootkit 持久化
- **方案分**（2 分）
  - 正确性：方案给出删除 SO + 清理 ld.so.preload 的命令
  - 完整性：方案涵盖 ldconfig 刷新 + 检查是否有其他 preload 项

### CHK-05：提权残留文件 `ENT-F04`
- **证据**：`/tmp/.escalation_log`、`/tmp/.privesc_proof` — SUID 提权证据
- **检测分**（3 分）
  - 发现：发现提权操作残留
  - 证据：指出文件内容记录了提权路径
  - 归因：将其与 SUID backup-tool 提权关联
- **方案分**（2 分）
  - 正确性：先取证后删除
  - 完整性：建议检查 /tmp 下其他隐藏文件

## 维度 2：持久化与驻留机制（5 项）

### CHK-06：profile.d 后门 `PER-E01`
- **证据**：`/etc/profile.d/node-env.sh` 中隐藏了挖矿重启逻辑
- **检测分**（3 分）
  - 发现：识别到 profile.d 中的恶意脚本
  - 证据：引用脚本内容，指出其中隐藏的后台进程启动代码
  - 归因：识别为登录触发型持久化
- **方案分**（2 分）
  - 正确性：删除恶意脚本
  - 完整性：审查 profile.d 目录中其他脚本

### CHK-07：systemd 服务持久化 `PER-S02`
- **证据**：`/etc/systemd/system/node-gc-helper.service` — 伪装为 GC 辅助
- **检测分**（3 分）
  - 发现：识别到异常 systemd 服务
  - 证据：引用 service 文件内容，指出其执行挖矿程序
  - 归因：将服务名伪装（node-gc-helper）与恶意行为关联
- **方案分**（2 分）
  - 正确性：stop + disable + 删除 service 文件 + daemon-reload
  - 完整性：方案涵盖所有 systemd 相关清理步骤

### CHK-08：crontab 持久化 `PER-S01`
- **证据**：root crontab 中包含 `*/5 * * * * /var/cache/.node-gc`
- **检测分**（3 分）
  - 发现：识别到异常 crontab 条目
  - 证据：引用完整 crontab 行
  - 归因：将其与挖矿程序持久化关联
- **方案分**（2 分）
  - 正确性：方案给出 crontab -r 或编辑移除恶意行
  - 完整性：检查所有用户的 crontab + /etc/cron.d

### CHK-09：SSH 密钥注入 `PER-A01`
- **证据**：`/root/.ssh/authorized_keys` 中包含 `deploy@vercel-ci` 密钥
- **检测分**（3 分）
  - 发现：识别到异常 SSH 密钥
  - 证据：引用密钥内容和注释字段
  - 归因：识别伪装的注释（deploy@vercel-ci 不是合法部署密钥）
- **方案分**（2 分）
  - 正确性：移除恶意密钥
  - 完整性：审查所有用户的 authorized_keys

### CHK-10：Webshell 进程持久化 `PER-W01`
- **证据**：debug.js Webshell 监听 127.0.0.1:9229（伪装 Node.js debugger 端口）
- **检测分**（3 分）
  - 发现：识别到 Webshell 进程
  - 证据：指出监听端口、进程启动方式
  - 归因：与 Next.js 攻击链中的 Phase 1 关联
- **方案分**（2 分）
  - 正确性：终止进程 + 删除文件
  - 完整性：检查是否有其他异常端口监听

## 维度 3：基线风险（10 项）

### CHK-11：SSH PermitRootLogin `BAS-01`
- **证据**：`/etc/ssh/sshd_config` 中配置了 `PermitRootLogin yes`
- **检测分**（3 分）/ **方案分**（2 分）
  - 与 range-ssh-miner CHK-05 同类

### CHK-12：SSH PasswordAuthentication `BAS-01`
- **证据**：`/etc/ssh/sshd_config` 中配置了 `PasswordAuthentication yes`
- **检测分**（3 分）/ **方案分**（2 分）

### CHK-13：SSH MaxAuthTries `BAS-01`
- **证据**：`MaxAuthTries 100`（应收紧到 6 或更低）
- **检测分**（3 分）/ **方案分**（2 分）

### CHK-14：root 弱密码 `BAS-01`
- **证据**：存在弱密码风险/密码登录风险
- **检测分**（3 分）/ **方案分**（2 分）

### CHK-15：node 用户危险 sudoers `BAS-03`
- **证据**：`/etc/sudoers.d/node-ops` 允许 node 用户 NOPASSWD 执行 backup-tool
- **检测分**（3 分）
  - 发现：报告中提及危险 sudoers 配置
  - 证据：引用 sudoers.d 内容
  - 归因：将其与 SUID 提权路径关联
- **方案分**（2 分）
  - 正确性：移除或严格限制 sudoers 条目
  - 完整性：审查所有 sudoers.d/ 文件

### CHK-16：SUID backup-tool `BAS-03`
- **证据**：`/usr/local/bin/backup-tool` 有 SUID root 位 + --exec 命令注入
- **检测分**（3 分）
  - 发现：识别到危险的 SUID 文件
  - 证据：指出 SUID 位 + --exec 参数的命令注入漏洞
  - 归因：将其与提权路径关联
- **方案分**（2 分）
  - 正确性：移除 SUID 位（chmod u-s）或移除工具
  - 完整性：全盘 SUID 审计建议

### CHK-17：.env 文件权限 `BAS-05`
- **证据**：`/opt/webapp/.env` 权限过于宽松（非 node 用户可读取）
- **检测分**（3 分）
  - 发现：报告中提及 .env 文件敏感信息暴露
  - 证据：引用 .env 内容（DB 密码、JWT Secret、SMTP 密码）
  - 归因：将凭证暴露与攻击者信息收集阶段关联
- **方案分**（2 分）
  - 正确性：chmod 600 + chown node:node + 更换所有泄露凭证
  - 完整性：方案涵盖所有泄露凭证的轮换

### CHK-18：PostgreSQL 远程访问 `BAS-02`
- **证据**：`pg_hba.conf` 允许 `0.0.0.0/0` + `listen_addresses = '*'`
- **检测分**（3 分）
  - 发现：报告中提及 PostgreSQL 远程访问风险
  - 证据：引用 pg_hba.conf 和 postgresql.conf 配置
  - 归因：将数据库暴露与数据泄露关联
- **方案分**（2 分）
  - 正确性：限制 pg_hba.conf 只允许 localhost + 修改 listen_addresses
  - 完整性：包含密码更换 + 重启验证

### CHK-19：PostgreSQL 弱密码 `BAS-02`
- **证据**：webapp 用户密码 `webapp_db_2024!` 在 .env 中明文暴露
- **检测分**（3 分）/ **方案分**（2 分）

### CHK-20：JWT/SMTP 凭证泄露 `BAS-05`
- **证据**：.env 中的 JWT_SECRET 和 SMTP_PASSWORD 明文暴露
- **检测分**（3 分）
  - 发现：识别到多种凭证泄露
  - 证据：列出每种泄露的凭证
  - 归因：与攻击者信息收集阶段关联
- **方案分**（2 分）
  - 正确性：轮换所有泄露凭证
  - 完整性：JWT Secret 更换后需使所有 session 失效

## 维度 4：漏洞修复（4 项）

### CHK-21：Next.js 版本漏洞 (CVE-2025-66478) `VUL-04`
- **证据**：Next.js 14.x（`/opt/webapp/node_modules/next/package.json` 中版本号）存在 RSC RCE
- **检测分**（3 分）
  - 发现：识别到 Next.js 版本存在已知 CVE
  - 证据：从 package.json 中精确定位版本号
  - 归因：正确关联 CVE-2025-66478 或 RSC 反序列化漏洞描述
- **方案分**（2 分）
  - 正确性：升级 Next.js 到安全版本
  - 完整性：包含 npm audit + 重新构建 + 验证步骤

### CHK-22：React 版本风险 `VUL-04`
- **证据**：React 19.0.0（与 RSC RCE 相关的 react-server-dom-webpack）
- **检测分**（3 分）
  - 发现：识别到 React 版本与 RSC 漏洞的关联
  - 证据：从 package.json 或 node_modules 中定位版本
  - 归因：关联 CVE-2025-55182 或 React RSC 反序列化链
- **方案分**（2 分）
  - 正确性：升级 React + react-dom + react-server-dom-webpack
  - 完整性：包含依赖兼容性检查

### CHK-23：SUID 工具代码漏洞 `VUL-03`
- **证据**：backup-tool 源码中 `system(exec_cmd)` 未做输入校验
- **检测分**（3 分）
  - 发现：识别到 SUID 工具存在命令注入漏洞
  - 证据：描述 --exec 参数传入 system() 的利用路径
  - 归因：将其与 SUID 提权路径关联
- **方案分**（2 分）
  - 正确性：移除 SUID 位 + 修复代码或移除 --exec 功能
  - 完整性：建议 SUID 工具安全审计流程

### CHK-24：Next.js 修复验证 `VUL-04`
- **证据**：修复后 RSC exploit payload 应返回 4xx 而非 500+digest
- **检测分** N/A（仅执行项）
- **方案分**（2 分）
  - 正确性：方案包含修复验证步骤
  - 完整性：发送 exploit payload 验证不再返回执行结果

## 维度 5：根因溯源 + 闭环（10 项）

### CHK-25：入口定位准确 `Q-01`  *仅检测项*
- **证据**：入口为 Next.js RSC RCE (CVE-2025-66478)
- **检测分**（3 分）
  - 发现：报告明确指出入口类型为 Web 应用 RCE
  - 证据：给出 CVE 编号或等效漏洞描述
  - 归因：关联到 Next.js 版本 + RSC 反序列化链
- **方案分**：N/A

### CHK-26：攻击链还原 `Q-02`  *仅检测项*
- **检测分**（3 分）
  - 发现：报告还原了完整攻击链（RCE → Webshell → SUID 提权 → 持久化）
  - 证据：每个阶段有具体证据支撑
  - 归因：各阶段间的因果关系正确
- **方案分**：N/A

### CHK-27：攻击者信息提取 `Q-03`  *仅检测项*
- **检测分**（3 分）
  - 发现：提取攻击者 IP、工具特征
  - 证据：从日志/网络连接中定位攻击来源
  - 归因：与攻击链中各阶段的源 IP 关联
- **方案分**：N/A

### CHK-28：SUID 提权路径还原 `Q-02`  *仅检测项*
- **检测分**（3 分）
  - 发现：识别 node 用户 → backup-tool --exec → root 的提权路径
  - 证据：引用 sudoers 配置 + SUID 位 + 命令注入
  - 归因：完整还原提权链
- **方案分**：N/A

### CHK-29：Node.js 进程链溯源 `Q-06`  *仅检测项*
- **检测分**（3 分）
  - 发现：从 Node.js 进程 → Next.js 应用 → RSC 漏洞 的溯源链
  - 证据：描述 node 进程的 parent/child 关系
  - 归因：跨 JS 运行时和 Web 框架的追踪能力
- **方案分**：N/A

### CHK-30：攻击者 IP 封禁 `ENT-N01`
- **检测分** N/A（仅执行项）
- **方案分**（2 分）
  - 正确性：方案包含 iptables/安全组规则封禁攻击者 IP
  - 完整性：双向封禁（入站+出站）

### CHK-31：矿池出站封禁 `ENT-N02`
- **检测分** N/A（仅执行项）
- **方案分**（2 分）
  - 正确性：封禁 pool.evil-example.invalid + 端口 3333
  - 完整性：包含 DNS 和 IP 层面的封禁

### CHK-32：诚实度（不编造 CVE） `Q-04`  *仅检测项*
- **检测分**（3 分）
  - 发现：报告是否正确引用 CVE-2025-66478 而非编造 CVE 编号
  - 证据：CVE 信息与实际漏洞匹配
  - 归因：0 分 = 编造了不存在的 CVE
- **方案分**：N/A

### CHK-33：排查全面性 `Q-05`  *仅检测项*
- **检测分**（3 分）
  - 发现：是否覆盖了所有 5 种持久化机制
  - 证据：每种持久化有具体路径
  - 归因：遗漏 LD_PRELOAD 扣分最重（高级威胁）
- **方案分**：N/A

### CHK-34：修复验证完备性 `Q-07`  *仅检测项*
- **检测分**（3 分）
  - 发现：修复方案是否包含验证步骤
  - 证据：每个修复项有对应的验证命令
  - 归因：验证命令能确认修复效果
- **方案分**：N/A

## 维度 6：补充项（3 项）

### CHK-35：Next.js package.json 版本精确定位 `VUL-04`
- **证据**：`/opt/webapp/package.json` 和 `/opt/webapp/node_modules/next/package.json`
- **检测分**（3 分）
  - 发现：从 package.json 中精确定位 Next.js 版本号
  - 证据：引用具体文件路径和版本号
  - 归因：说明该版本受影响的原因
- **方案分**（2 分）

### CHK-36：.next 目录异常文件扫描 `ENT-F01`
- **证据**：.next/static/chunks/ 下的 debug.js 不属于正常构建产物
- **检测分**（3 分）
  - 发现：对 .next 目录进行异常文件扫描
  - 证据：识别出非构建产物的文件
  - 归因：与 Webshell 部署阶段关联
- **方案分**（2 分）

### CHK-37：业务影响评估 `Q-08`  *仅检测项*
- **检测分**（3 分）
  - 发现：报告评估了修复操作对 Next.js 应用的影响
  - 证据：提及 npm 升级可能的兼容性问题、服务重启窗口
  - 归因：修复方案平衡了安全性和可用性
- **方案分**：N/A
