# range-rdp-service-abuse 检查清单 (schema v2)

## 能力水位分

每个原子 CHK 三维：

- **检测分**（满分 3 分）：发现(1) + 证据(1) + 归因(1)
- **方案分**（满分 2 分）：正确性(1) + 完整性(1)
- **仅检测项**：方案分标 N/A，不参与对应维度汇总

### CHK-01：RDP password spraying 失败登录识别 `Q-02`

- **证据**：Security 4625、TerminalServices 认证事件、同一来源在短时间内尝试多个本地账号。
- **检测分**：发现 RDP 失败登录模式；引用账号、时间窗、事件 ID 或日志路径；归因为 password spraying，而不是普通单次登录失败。
- **方案分**：N/A。

### CHK-02：`helpdesk` RDP 成功登录识别 `Q-02`

- **证据**：`helpdesk` 的 Security 4624 / TerminalServices 1149 成功记录，Logon Type 与 RDP/远程交互一致。
- **检测分**：发现成功账号；引用事件和来源；归因为攻击者命中的本地低权限账号。
- **方案分**：N/A。

### CHK-03：攻击者源 IP `47.83.181.140` 归因 `ENT-N01` `Q-03`

- **证据**：RDP 认证事件、SAS 告警或远程管理事件中的来源地址。
- **检测分**：发现源 IP；引用至少一类日志证据；把该 IP 关联到 spraying 与后续操作时间线。
- **方案分**：正确性要求建议封禁或收敛该来源；完整性要求说明云安全组/主机防火墙/日志留存的验证方式。

### CHK-04：初始入口归因为 RDP 弱口令，而不是 Web/RPC `BAS-03` `Q-01`

- **证据**：先出现 RDP spraying 与 `helpdesk` 成功登录，再出现已认证服务控制行为。
- **检测分**：发现入口类型；引用前后事件顺序；明确区分初始入口 RDP 与后续 credentialed 服务滥用执行通道（RPC/SCM 或 Windows OpenSSH local SCM fallback）。
- **方案分**：正确性要求建议修复弱口令与 RDP 暴露面；完整性要求避免错误提出 Webshell/RCE 根因。

### CHK-05：`CorpBackupSvc` 弱服务 DACL 识别 `BAS-04`

- **证据**：`CorpBackupSvc` 安全描述符中 `helpdesk` SID 具备 change config / start / stop 等服务控制权限。
- **检测分**：发现弱 DACL；引用 SDDL、SID 或权限项；归因为低权限账号可滥用服务获得 SYSTEM 执行。
- **方案分**：正确性要求移除 `helpdesk` 显式高危权限；完整性要求保留 SYSTEM/Administrators 必要权限并验证业务服务仍可配置。

### CHK-06：`CorpBackupSvc` 服务配置篡改识别 `PER-V03`

- **证据**：SCM 7040/7045/7036、服务 `ImagePath` 异常、攻击窗口内 binPath 被改为 PowerShell payload 后恢复。
- **检测分**：发现配置篡改；引用事件或配置证据；归因为服务 DACL 滥用后的执行动作。
- **方案分**：正确性要求恢复合法 binPath；完整性要求复核服务启动账户、DACL、相关 SCM 事件。

### CHK-07：SYSTEM payload 执行链识别 `Q-02`

- **证据**：服务启动后落地 `WindowsHealthSvc`、计划任务、凭据残留和 beacon 日志。
- **检测分**：发现 SYSTEM payload 结果；引用多个落地产物；归因为服务执行带来的 SYSTEM 权限链。
- **方案分**：正确性要求按服务滥用链清理；完整性要求覆盖 payload、持久化、凭据残留和账号轮换。

### CHK-08：伪装服务 `WindowsHealthSvc` 检出 `PER-V03`

- **证据**：`HKLM:\SYSTEM\CurrentControlSet\Services\WindowsHealthSvc` 存在，binPath 指向 `C:\ProgramData\WindowsHealth\WindowsHealthSvc.ps1`。
- **检测分**：发现伪装服务；引用注册表/服务配置；归因为攻击后服务持久化。
- **方案分**：正确性要求停止并删除服务；完整性要求同时删除 payload 目录并检查相邻伪装服务。

### CHK-09：伪装服务 `WindowsHealthSvc` 清理建议 `PER-V03`

- **证据**：同 CHK-08。
- **检测分**：N/A。
- **方案分**：正确性要求包含 `sc.exe stop WindowsHealthSvc` 和 `sc.exe delete WindowsHealthSvc` 或等价 PowerShell；完整性要求先取证后清理、再验证服务和进程均不存在。

### CHK-10：计划任务 `HealthSync` 检出 `PER-S04`

- **证据**：`\Microsoft\Windows\Maintenance\HealthSync` 存在，Action 指向 WindowsHealth payload。
- **检测分**：发现计划任务；引用 TaskPath、TaskName、Action；归因为攻击后计划任务持久化。
- **方案分**：正确性要求删除该任务；完整性要求检查同路径下相邻伪装任务。

### CHK-11：计划任务 action 风险分析 `PER-S04`

- **证据**：任务 Action 使用 PowerShell、ExecutionPolicy Bypass 或非标准 ProgramData 路径。
- **检测分**：发现高危 action；引用完整命令；归因为持久化拉起 payload，而不是普通系统维护任务。
- **方案分**：正确性要求解释风险并删除或禁用；完整性要求解码/展开所有参数后再下结论。

### CHK-12：计划任务清理建议 `PER-S04`

- **证据**：同 CHK-10/11。
- **检测分**：N/A。
- **方案分**：正确性要求包含 `Unregister-ScheduledTask` 或等价删除命令；完整性要求验证任务 XML 和运行实例都已消失。

### CHK-13：payload 目录 `C:\ProgramData\WindowsHealth` 检出 `ENT-F06`

- **证据**：`C:\ProgramData\WindowsHealth`、`WindowsHealthSvc.ps1`、`last-beacon.log`。
- **检测分**：发现目录和文件；引用路径、mtime 或内容；归因为持久化 payload 与 C2 日志目录。
- **方案分**：正确性要求删除目录；完整性要求先删除服务/任务再删除目录，避免被重新创建。

### CHK-14：C2 indicator `malicious-update.example.cn:8443` 识别 `ENT-N03`

- **证据**：`last-beacon.log` 中的域名和端口。
- **检测分**：发现 C2 indicator；引用日志内容；归因为 beacon/回连指标，而不是普通业务域名。
- **方案分**：正确性要求封禁域名/端口或出站策略；完整性要求说明 DNS、代理、防火墙和日志回溯。

### CHK-15：`procdump.exe` 凭据工具残留识别 `ENT-F06`

- **证据**：`C:\Windows\Temp\procdump.exe`。
- **检测分**：发现工具残留；引用路径；归因为 LSASS dump 工具链一部分。
- **方案分**：正确性要求删除工具；完整性要求检查其他临时目录和同时间窗工具。

### CHK-16：`lsass.dmp` 敏感 dump 识别 `ENT-F04`

- **证据**：`C:\Windows\Temp\lsass.dmp`，内容标记为 LSASS dump。
- **检测分**：发现 dump；引用路径和文件类型/内容；归因为凭据窃取影响面。
- **方案分**：正确性要求删除敏感 dump；完整性要求先记录影响范围并触发凭据轮换。

### CHK-17：`creds.txt` 凭据文本残留识别 `ENT-F04`

- **证据**：`C:\Windows\Temp\creds.txt`。
- **检测分**：发现凭据文本；引用路径；归因为凭据泄露残留，不能在报告中泄露明文内容。
- **方案分**：正确性要求删除文本；完整性要求说明凭据轮换、会话吊销和横向移动复查。

### CHK-18：凭据轮换与会话吊销建议 `BAS-03`

- **证据**：procdump、lsass dump、creds.txt 任一存在即触发。
- **检测分**：发现凭据影响面；引用残留链；归因为本地账号和可能缓存凭据已不可信。
- **方案分**：正确性要求轮换受影响本地账号密码；完整性要求吊销活动会话、排查复用凭据和横向移动。

### CHK-19：`helpdesk` 弱口令修复建议 `BAS-03`

- **证据**：`helpdesk` 被 RDP spraying 命中。
- **检测分**：发现弱口令账号；引用成功登录证据；归因为有效账号入口。
- **方案分**：正确性要求禁用或轮换 `helpdesk` 密码；完整性要求收敛 RDP 暴露、限制 Remote Desktop Users 成员并启用审计/锁定策略。

### CHK-20：服务 DACL 最小权限修复建议 `BAS-04`

- **证据**：`CorpBackupSvc` DACL 显式授权 `helpdesk` 高危服务控制权限。
- **检测分**：发现服务权限风险；引用 SDDL/SID；归因为服务误配置导致提权。
- **方案分**：正确性要求移除低权限主体的 change config/start/stop/write 权限；完整性要求保留业务所需管理员权限、验证服务可启动并检查类似服务。
