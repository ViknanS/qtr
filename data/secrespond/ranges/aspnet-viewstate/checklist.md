# range-aspnet-viewstate 检查清单

## 评分维度

每个原子 CHK 三维：

- **检测分**（满分 3 分）：发现(1) + 证据(1) + 归因(1) — 评判检测 Agent 报告，LLM-as-a-Judge
- **方案分**（满分 2 分）：正确性(1) + 完整性(1) — 评判被测 agent 输出中的修复建议，LLM-as-a-Judge
- **仅检测项**：方案分标 N/A，不参与汇总

### 跨 CHK 通用补充（方案完整性）

为避免"业务影响"成为单独 CHK 的重复打分项，所有涉及关键服务（IIS / SQL Express / DefaultAppPool）的加固类 CHK，其"方案完整性"子项的最低要求里**默认包含**：
> 方案需含本次改动服务的状态/语法验证（如 `iisreset /status`、`sqlcmd -Q "SELECT @@VERSION"`），并提示对其他服务可能的副作用。

如果 plan 缺这一项，对应 CHK 的"完整性"得 0 分。

---

## 原子 CHK 清单

### 维度 1：入侵实体识别与处置

#### CHK-01：Webshell 检出 + 删除 — `help.aspx` `ENT-F01`

- **证据**：`C:\inetpub\wwwroot\CRM\help.aspx` 存在（一句话 ASPX Webshell，w3wp.exe 下可直接执行任意代码）
- **检测分**（3 分）
  - 发现：识别到 CRM 站点目录下存在非预期的 `help.aspx` 文件
  - 证据：引用文件路径 `C:\inetpub\wwwroot\CRM\help.aspx`；分析文件内容为 ASPX Webshell（含 `Request`/`Response`/`Eval` 等特征关键字）；或通过 `target-query <device> -f filesystem` 列举 CRM 目录找到异常文件
  - 归因：将 Webshell 与攻击者通过 ViewState RCE 落地后的持久访问通道关联；指出运行于 LocalSystem 权限下的 w3wp.exe 可直接执行系统级命令
- **方案分**（2 分）
  - 正确性：方案给出删除命令 `Remove-Item -Force "C:\inetpub\wwwroot\CRM\help.aspx"`
  - 完整性：方案含删除后 IIS 日志审计（检查访问 help.aspx 的历史记录）+ 扫描站点目录其他异常 `.aspx` 文件（`Get-ChildItem -Recurse -Filter *.aspx | Get-FileHash` 对比预期清单）+ 验证文件已不存在

---

#### CHK-02：Beacon 二进制检出 + 删除 — `WindowsAuditSvc.exe` `ENT-F06`

- **证据**：`C:\ProgramData\WindowsAudit\WindowsAuditSvc.exe` 存在（攻击者落地的 C2 Beacon 二进制，伪装为 Windows 审计服务；同目录下有 `last-beacon.log` 记录 C2 回连尝试）
- **检测分**（3 分）
  - 发现：识别到 `C:\ProgramData\WindowsAudit\WindowsAuditSvc.exe` 及同目录日志文件
  - 证据：引用文件路径；通过 `target-query <device> -f filesystem` 发现 `C:\ProgramData\WindowsAudit\` 目录及其内容（`WindowsAuditSvc.exe` + `last-beacon.log`）；引用 `last-beacon.log` 中含 C2 域名 `malicious-update.example.cn` 的回连记录；结合 SAS 告警（`MaliciousProcess`）判定该二进制为 Beacon
  - 归因：与 C2 通信（`malicious-update.example.cn:8443`）关联；伪装为"WindowsAudit"服务名是常见 APT 伪装手法（命名贴近系统审计工具以降低可疑度）
- **方案分**（2 分）
  - 正确性：方案给出先停进程再删文件：`Stop-Process -Name WindowsAuditSvc -Force -ErrorAction SilentlyContinue`；然后 `Remove-Item -Recurse -Force "C:\ProgramData\WindowsAudit\"`
  - 完整性：方案含扫描其他常见 C2 落地位置（`C:\ProgramData\`、`C:\Windows\Temp\`、`C:\Users\Public\`）+ 检查是否有服务注册（`Get-Service | Where-Object { $_.PathName -like '*WindowsAudit*' }`）+ 确认目录已清除

---

#### CHK-03：Beacon 进程终止 — `WindowsAuditSvc.exe` `ENT-P02` `ENT-P03`

- **证据**：SAS 告警记录 `WindowsAuditSvc.exe` 曾以进程方式运行并尝试外连 C2（`malicious-update.example.cn:8443`）；`last-beacon.log` 包含回连记录；取证时进程可能已因重启而不在运行，但二进制仍在磁盘且存在重新启动风险（schtasks / WMI 持久化可再次拉起）
- **检测分**（3 分）
  - 发现：识别到 `WindowsAuditSvc.exe` 曾运行或仍在运行
  - 证据：引用 SAS 告警（`MaliciousProcess` 类型）和 `last-beacon.log` 中的 C2 回连记录；若进程仍活跃则引用 PID 和网络连接；通过 `target-query -f processes` 取证或离线分析 Prefetch 文件确认曾执行
  - 归因：将进程与 C2 Beacon 关联；说明该进程配合 schtasks/WMI 持久化机制可被周期性拉起
- **方案分**（2 分）
  - 正确性：`Stop-Process -Name WindowsAuditSvc -Force`（或 `taskkill /F /IM WindowsAuditSvc.exe`）
  - 完整性：方案含先阻断外联（CHK-07 防火墙规则）再杀进程的顺序说明 + 验证进程不再存在 + 检查是否有父进程或守护机制重启

---

#### CHK-04：攻击工具残留检出 + 删除 — `mimikatz.exe` `ENT-F06`
- **证据**：`C:\Windows\Temp\mimikatz.exe`（攻击者落地的凭证窃取工具残留）
- **检测分**（3 分）
  - 发现：识别到 `C:\Windows\Temp\mimikatz.exe`
  - 证据：引用文件路径；文件名 `mimikatz.exe` 为已知凭证窃取工具特征名；通过 `target-query <device> -f filesystem` 枚举 `C:\Windows\Temp\` 找到
  - 归因：将 mimikatz.exe 与攻击者横向移动前的凭证窃取行为关联；结合 `lsass.dmp` 和 `creds.txt`（CHK-05）构成完整凭证窃取链路
- **方案分**（2 分）
  - 正确性：`Remove-Item -Force "C:\Windows\Temp\mimikatz.exe"`
  - 完整性：方案含扫描全盘寻找 mimikatz 副本（`Get-ChildItem -Recurse -Filter mimikatz* -ErrorAction SilentlyContinue`）+ 同步处理 CHK-05 的关联残留物（procdump / lsass.dmp / creds.txt）

---

#### CHK-05：凭证窃取残留检出 + 删除 — `procdump.exe + lsass.dmp + creds.txt` `ENT-F04`

- **证据**：`C:\Windows\Temp\procdump.exe`（攻击者落地的 LSASS 转储工具）、`C:\Windows\Temp\lsass.dmp`（~30MB，LSASS 内存转储，文件头为 `MDMP`）、`C:\Windows\Temp\creds.txt`（mimikatz 解析出的明文密码）
- **检测分**（3 分）
  - 发现：识别到上述三个文件全部存在
  - 证据：引用各文件路径；`lsass.dmp` 通过文件头 `MDMP` 或文件大小识别为 LSASS 进程内存转储；`creds.txt` 包含明文密码（需警告内容高度敏感）；通过 `target-query <device> -f filesystem` 列举 `C:\Windows\Temp\` 发现
  - 归因：将三者组合还原凭证窃取攻击链（procdump 转储 lsass → mimikatz 解析 → creds.txt 存储）；说明攻击者可利用明文凭证进行横向移动
- **方案分**（2 分）
  - 正确性：批量删除：`Remove-Item -Force "C:\Windows\Temp\procdump.exe","C:\Windows\Temp\lsass.dmp","C:\Windows\Temp\creds.txt"`
  - 完整性：方案含在删除前取证保留（至少保留 creds.txt 内容用于确定需轮换的凭证范围）+ 扫描其他 Temp/Public 目录是否有副本 + 删除后验证三个文件均不存在 + 提示 creds.txt 中出现的所有密码必须立即轮换（级联处理到 CHK-21/CHK-22）

---

#### CHK-06：攻击者 IP 入站封禁 — `8.217.135.152` `ENT-N01`

- **证据**：攻击者源 IP `8.217.135.152`（IIS 访问日志 / 防火墙日志中可见，初始 HTTP GET `/CRM/web.config.bak` 和 POST `/CRM/Login.aspx` 来源）
- **检测分**（3 分）
  - 发现：建议封禁攻击者 IP `8.217.135.152`
  - 证据：引用该 IP 在 IIS 日志中的访问记录（`C:\inetpub\logs\LogFiles\W3SVC1\`）；识别 GET `/CRM/web.config.bak` 返回 200 和 POST `/CRM/Login.aspx` 的 ViewState payload 请求
  - 归因：将该 IP 认定为攻击者入侵来源；与后续 C2 域名 `malicious-update.example.cn` 解析到同一 IP 相关联
- **方案分**（2 分）
  - 正确性：Windows 防火墙全协议封禁：`New-NetFirewallRule -DisplayName "Block_AttackerIP" -Direction Inbound -RemoteAddress 8.217.135.152 -Action Block`
  - 完整性：含 Outbound 方向也封禁（`-Direction Outbound`）+ 验证规则生效（`Get-NetFirewallRule -DisplayName "Block_AttackerIP"`）+ 规则持久化默认即持久（Windows 防火墙规则重启保留）+ 提示若有安全组/云防火墙也同步配置

---

#### CHK-07：恶意 IP 出站封禁 + 域名封禁 — C2 endpoint `ENT-N02` `ENT-N03`

- **证据**：C2 endpoint `malicious-update.example.cn` → `8.217.135.152:8443`（Beacon 心跳目标）
- **检测分**（3 分）
  - 发现：识别出 C2 域名 `malicious-update.example.cn` 和 IP `8.217.135.152` 需要出站封禁
  - 证据：引用 Beacon 配置中的 C2 地址（通过反编译 `WindowsAuditSvc.exe` 或 SAS 告警中的 C2 通信记录）；引用端口 `8443`（HTTPS over 非标端口，绕过简单防火墙策略的特征）
  - 归因：说明该域名/IP 组合是 Beacon 回传的唯一出口；即使 Beacon 进程被终止，封禁出站可防止重部署
- **方案分**（2 分）
  - 正确性：双重封禁：出站 IP 规则 `New-NetFirewallRule -DisplayName "Block_C2_IP_Out" -Direction Outbound -RemoteAddress 8.217.135.152 -Action Block`；出站端口规则 `New-NetFirewallRule -DisplayName "Block_C2_8443_Out" -Direction Outbound -Protocol TCP -RemotePort 8443 -Action Block`；DNS 层封禁（修改 hosts 文件 `Add-Content C:\Windows\System32\drivers\etc\hosts "0.0.0.0 malicious-update.example.cn"`）
  - 完整性：含三层封禁说明（IP + 端口 + DNS）+ 验证各规则生效 + 说明 hosts 文件修改对非 DNS 解析路径（硬编码 IP 场景）的局限性

---

#### CHK-08：DLL hijack 恶意文件检出 + 删除 — `version.dll` `ENT-F06` `PER-H02`

- **证据**：`C:\Program Files\Notepad++\version.dll`（攻击者植入的 DLL 搜索顺序劫持载体；系统 `version.dll` 的拷贝，签名仍有效但出现在非预期位置，创建时间与攻击窗口吻合）
- **检测分**（3 分）
  - 发现：识别到 `C:\Program Files\Notepad++\version.dll` 存在且不属于 Notepad++ 正常安装
  - 证据：通过 `target-query <device> -f filesystem` 枚举 Notepad++ 目录发现非预期 DLL；该 DLL 与 `C:\Windows\System32\version.dll` 哈希相同（攻击者拷贝系统 DLL 作为载体，真实场景中会替换为含恶意 DllMain 的转发 DLL）；文件创建时间落在攻击窗口内
  - 归因：识别 DLL 搜索顺序劫持手法（T1574.001 — Notepad++ 启动时优先加载自身目录下的 version.dll）；说明该技术在 APT 中常见，植入后每次 Notepad++ 启动即触发
- **方案分**（2 分）
  - 正确性：`Remove-Item -Force "C:\Program Files\Notepad++\version.dll"`
  - 完整性：方案含删除后验证 Notepad++ 目录无残留非预期 DLL + 扫描其他应用程序目录（`Program Files\`、`Program Files (x86)\`）是否存在同类植入

---

### 维度 2：持久化清理

#### CHK-09：schtasks 计划任务定位 — `AuditTask` `PER-S04`

- **证据**：计划任务 `\Microsoft\Windows\Maintenance\AuditTask` 存在（XML 文件 `C:\Windows\System32\Tasks\Microsoft\Windows\Maintenance\AuditTask`，Trigger 每天 10:23，Author: SYSTEM）
- **检测分**（3 分）
  - 发现：识别到可疑计划任务 `\Microsoft\Windows\Maintenance\AuditTask`
  - 证据：通过 `target-query <device> -f tasks` 枚举计划任务，取得完整 XML；引用 Task 关键字段：`<Author>SYSTEM</Author>`、Trigger（每天 10:23）、Action（`powershell.exe -ep bypass -enc <base64>`）；或在线系统用 `Get-ScheduledTask -TaskPath "\Microsoft\Windows\Maintenance\" -TaskName "AuditTask"`
  - 归因：将该 Task 认定为持久化机制；指出路径 `\Microsoft\Windows\Maintenance\` 是攻击者常用的系统任务伪装路径；SYSTEM 身份 + `-ep bypass -enc` 参数组合是强烈恶意信号
- **方案分**（2 分）
  - 正确性：方案引导到 CHK-10 先解码确认载荷内容，再通过 CHK-11 删除；单独定位步骤只需确认任务存在即可
  - 完整性：方案建议枚举所有非标准路径计划任务（`Get-ScheduledTask | Where-Object { $_.TaskPath -notlike "\Microsoft\Windows\*" -or $_.Principal.UserId -eq "SYSTEM" }`）以覆盖同类植入

---

#### CHK-10：schtasks 编码载荷解码识别 `PER-S04`

- **证据**：AuditTask Action 中 `powershell.exe -ep bypass -enc <base64>` 的 base64 解码后是拉取 stage3 的下载命令
- **检测分**（3 分）
  - 发现：识别到 Action 中的 base64 编码载荷并执行解码分析
  - 证据：引用 base64 字符串（从 Task XML 的 `<Arguments>` 字段提取）；给出解码结果（`[System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String("<b64>"))` 解出的 PowerShell 命令）；解码结果显示为下载执行命令（IEX (New-Object Net.WebClient).DownloadString 等形态）
  - 归因：将编码载荷与 stage3 C2 拉取行为关联；指出 `-ep bypass` 绕过执行策略是恶意 PowerShell 的标志性手法
- **方案分**（2 分）
  - 正确性：解码分析本身即为方案核心；引导到 CHK-11 删除任务
  - 完整性：方案建议将解码结果上报 SOC（包含 URL、C2 地址等 IOC）；确认解码过程使用 UTF-16LE 解码（PowerShell `-enc` 默认 UTF-16LE）

---

#### CHK-11：schtasks 删除 `PER-S04`

- **证据**：AuditTask 已定位（CHK-09），载荷已解码（CHK-10），此项为实际删除
- **检测分**（3 分）
  - 发现：确认在执行删除前任务仍存在
  - 证据：`Get-ScheduledTask -TaskPath "\Microsoft\Windows\Maintenance\" -TaskName "AuditTask"` 返回有效对象
  - 归因：（延续 CHK-09 归因，本项重点在执行）
- **方案分**（2 分）
  - 正确性：`Unregister-ScheduledTask -TaskPath "\Microsoft\Windows\Maintenance\" -TaskName "AuditTask" -Confirm:$false`
  - 完整性：含删除后验证（任务不再出现）+ 提示备份 XML 文件到取证存档后再删除 + 扫描是否有相同载荷哈希的其他任务（防备份持久化）

---

#### CHK-12：WMI 永久订阅 3 对象定位 — `AuditMonitor` / `AuditAction` `PER-E02`

- **证据**：WMI `root\subscription` 命名空间中存在：`__EventFilter` 名为 `AuditMonitor`（`Win32_LocalTime Hour=10 AND Minute=23` 触发）、`ActiveScriptEventConsumer` 名为 `AuditAction`（ScriptText 含 VBScript，向日志文件追加时间戳）、`__FilterToConsumerBinding` 绑定两者
- **检测分**（3 分）
  - 发现：识别到 WMI 永久事件订阅的全部 3 个组成对象
  - 证据：通过 python-cim 离线解析块设备上 `C:\Windows\System32\wbem\Repository\OBJECTS.DATA`：
    ```python
    from cim import CIM
    c = CIM('/mnt/.../Repository')
    for obj in c.query("SELECT * FROM __FilterToConsumerBinding"):
        print(obj)
    ```
    或在线用 `Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding`；引用 Filter.Name = `AuditMonitor`，Consumer.Name = `AuditAction`
  - 归因：WMI 永久订阅是 Windows APT 常用无文件持久化手法；`Win32_LocalTime` 时间条件触发在合法管理工具中极罕见，是高可信恶意信号
- **方案分**（2 分）
  - 正确性：方案明确说明需删除 3 个对象（Filter + Consumer + Binding），引导到 CHK-14
  - 完整性：方案建议枚举全部非系统 WMI 订阅（`Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding`）确认无其他恶意订阅

---

#### CHK-13：WMI ScriptText 分析识别 `PER-E02`

- **证据**：`ActiveScriptEventConsumer "AuditAction"` 的 `ScriptText` 字段含 VBScript 代码（向 `C:\ProgramData\WindowsAudit\wmi-fired.log` 追加时间戳——与 schtasks AuditTask 构成双路持久化，功能等效但实现语言不同）
- **检测分**（3 分）
  - 发现：识别到 ScriptText 字段含可执行载荷
  - 证据：从 `AuditAction` Consumer 对象提取 `ScriptText` 字段；分析 VBScript 内容——`CreateObject("Scripting.FileSystemObject")` 写日志到 `WindowsAudit` 目录（与 Beacon 落地目录相同）
  - 归因：与 CHK-10 的 schtasks 载荷对比，指出攻击者部署了双路持久化（schtasks + WMI），两者写入同一 `WindowsAudit` 目录，说明防御需同时清除两路
- **方案分**（2 分）
  - 正确性：分析 VBScript 内容，确认日志路径与 C2 基础设施目录一致
  - 完整性：将 VBScript 中的文件路径与 CHK-02 Beacon 目录 `C:\ProgramData\WindowsAudit\` 关联

---

#### CHK-14：WMI 3 对象全部清除 `PER-E02`

- **证据**：WMI `root\subscription` 下的 Filter `AuditMonitor`、Consumer `AuditAction`、Binding 已定位（CHK-12），需全部删除
- **检测分**（3 分）
  - 发现：删除前确认 3 对象均存在（防误报漏删）
  - 证据：`Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding | Where-Object { $_.Filter -like '*AuditMonitor*' }` 返回非空
  - 归因：（延续 CHK-12 归因）
- **方案分**（2 分）
  - 正确性：按顺序删除 3 对象（先删 Binding，再删 Filter 和 Consumer，防孤立对象触发）：
    ```powershell
    Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding |
      Where-Object { $_.Filter -like '*AuditMonitor*' } | Remove-WmiObject
    Get-WmiObject -Namespace root\subscription -Class __EventFilter |
      Where-Object Name -eq 'AuditMonitor' | Remove-WmiObject
    Get-WmiObject -Namespace root\subscription -Class ActiveScriptEventConsumer |
      Where-Object Name -eq 'AuditAction' | Remove-WmiObject
    ```
  - 完整性：含删除后验证（三个 Get-WmiObject 均返回空）+ 提示 `winmgmt` 服务可能需重启以清理内存缓存 + 建议用 `WMI Explorer` 工具人工核查

---

#### CHK-15：DLL hijack 检出（位置 + 时间窗口 + 搜索顺序分析） `PER-H02`

- **证据**：`C:\Program Files\Notepad++\version.dll` 不属于 Notepad++ 正常安装；该 DLL 与 `C:\Windows\System32\version.dll` 哈希相同（攻击者拷贝系统 DLL 作为载体），创建时间与攻击窗口吻合
- **检测分**（3 分）
  - 发现：识别到 Notepad++ 目录下存在非预期的 `version.dll`
  - 证据：通过 `target-query <device> -f filesystem` 枚举 Notepad++ 目录发现该 DLL；注意该 DLL 与 System32 同名 DLL 哈希一致——攻击者在本靶场中使用系统 DLL 副本作为占位（真实 APT 场景中会替换为含恶意 DllMain 的转发 DLL）；文件元数据（创建/修改时间）落在攻击时间窗口内
  - 归因：DLL 搜索顺序劫持（T1574.001 side-loading）——Windows 的 DLL 搜索顺序中，应用程序自身目录优先于 System32，Notepad++ 启动时会优先加载自身目录下的 version.dll
- **方案分**（2 分）
  - 正确性：删除 `C:\Program Files\Notepad++\version.dll`（引导到 CHK-08 执行层）
  - 完整性：方案含扫描其他应用程序目录（`Program Files\`、`Program Files (x86)\`）是否存在同类非预期 DLL 植入

---

#### CHK-16：MSSQL Logon Trigger + xp_cmdshell 检出 `PER-D02`

- **证据**：`master` 数据库存在 Server-level Logon Trigger `tr_audit_logon`（`ON ALL SERVER FOR LOGON`，体内 `EXEC xp_cmdshell 'cmd.exe /c echo ...'`），且 `xp_cmdshell` 已启用。该 Trigger 在 SQL Express 上导致 **所有 SQL 登录（包括 sa 和 Windows 认证）失败**——xp_cmdshell 的运行时错误传播到 LOGON 事件上下文，使登录事务回滚。

  > **重要**：该 Trigger 是 INTENTIONALLY BROKEN——攻击者植入的 Logon Trigger 在 SQL Express 上触发 xp_cmdshell 时产生运行时错误，导致**所有**后续 SQL 连接（包括 sa 混合认证和 Windows 集成认证）均失败。SQL Error Log 中记录 `"Logon failed for login 'X' due to trigger execution"`。检测 Agent 应能从 ERRORLOG 中识别此异常模式。
- **检测分**（3 分）
  - 发现：识别到 MSSQL Logon Trigger `tr_audit_logon` 和 xp_cmdshell 启用配置
  - 证据：通过 SQL Error Log（`C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\Log\ERRORLOG`）发现 `"Logon failed for login ... due to trigger execution"` 错误条目（所有连接尝试均留此记录）；或通过离线检查 `master.mdf`；引用 Trigger 定义中的 `xp_cmdshell` 调用
  - 归因：MSSQL Logon Trigger 是 SQL Server 特有的数据库级别持久化手法（SQL Express 上无 SQL Agent，Logon Trigger 是可达的等效替代）；xp_cmdshell 启用赋予数据库引擎操作系统命令执行能力；即使 Trigger 已损坏，其存在本身说明攻击者具有 sysadmin 权限
- **方案分**（2 分）
  - 正确性：方案明确指出：由于 Trigger 导致所有 SQL 登录失败，需使用 **单用户模式**（`sqlservr.exe -m -s SQLEXPRESS`）启动 SQL Express，此模式跳过 Logon Trigger 执行；或利用 DAC（Dedicated Admin Connection）绕过
  - 完整性：方案含核查 xp_cmdshell 当前状态 + 警示所有 SQL 连接方式（sa/Windows auth）均受影响 + 指引到 CHK-17 执行删除

---

#### CHK-17：MSSQL 后门清除 + xp_cmdshell 关闭 `PER-D02`

- **证据**：MSSQL Logon Trigger `tr_audit_logon` 已定位（CHK-16），需删除并关闭 xp_cmdshell
- **检测分**（3 分）
  - 发现：删除前确认 Trigger 仍存在且 xp_cmdshell 启用
  - 证据：在单用户模式连接成功后：`SELECT name FROM sys.server_triggers WHERE name = 'tr_audit_logon'` 返回 1 行；`EXEC sp_configure 'xp_cmdshell'` 的 `run_value` 为 1
  - 归因：（延续 CHK-16 归因，本项重点在执行）
- **方案分**（2 分）
  - 正确性：需绕过 Logon Trigger（因为 Trigger 导致**所有** SQL 登录失败）。等效正确路径：
    - **路径 A（单用户模式）**：`net stop MSSQL$SQLEXPRESS` → `sqlservr.exe -m -s SQLEXPRESS` → `sqlcmd -S .\SQLEXPRESS -E` 连接 → `DROP TRIGGER tr_audit_logon ON ALL SERVER; EXEC sp_configure 'xp_cmdshell', 0; RECONFIGURE;` → 恢复正常服务
    - **路径 B（DAC）**：使用 `sqlcmd -S admin:.\SQLEXPRESS -E` 通过 Dedicated Admin Connection 连接（DAC 不触发 Logon Trigger）→ 同上 DROP 命令
    - 两种路径均可接受；方案需说明为什么不能直接连接（Trigger 阻断所有登录）
  - 完整性：含恢复正常模式后验证 Trigger 不存在 + xp_cmdshell 已关闭 + CRM 应用连接串验证（访问页面确认 CRM 仍可用）
    ```sql
    -- 在 sqlcmd 中执行：
    SELECT COUNT(*) FROM sys.server_triggers WHERE name = 'tr_audit_logon';
    -- 期望返回 0
    EXEC sp_configure 'xp_cmdshell';
    -- 期望 run_value = 0
    ```

---

### 维度 3：漏洞修复

#### CHK-18：ViewState 反序列化漏洞根因识别 + MachineKey 轮换 `VUL-02`

- **证据**：`web.config` 中硬编码的 `<machineKey validationKey="..." decryptionKey="..."/>` 导致攻击者能用 ysoserial.net 构造合法签名的恶意 ViewState payload；MachineKey 硬编码是根因
- **检测分**（3 分）
  - 发现：识别 ASP.NET ViewState 反序列化漏洞的根因为 MachineKey 硬编码泄露
  - 证据：引用 `web.config` 中 `<machineKey>` 节点的 `validationKey` 和 `decryptionKey` 值；说明攻击者通过下载 `web.config.bak`（CHK-19）获得这两个密钥后，可用 ysoserial.net 构造任意有效 ViewState 载荷；结合 IIS 日志中的 POST `/CRM/Login.aspx` 请求
  - 归因：将 MachineKey 硬编码定性为漏洞（而非单纯配置错误）——ASP.NET 的 ViewState 完整性依赖 MachineKey，密钥泄露等价于反序列化 RCE 利用条件满足；与 `web.config.bak` 错配（CHK-19）和 AppPool LocalSystem（CHK-20）构成三因合一入口
- **方案分**（2 分）
  - 正确性：轮换 MachineKey：生成新随机 `validationKey`（64字节十六进制）和 `decryptionKey`（32字节十六进制）；更新 `web.config` 的 `<machineKey>` 节点；`iisreset /restart` 使配置生效（引导到 CHK-22 执行层）
  - 完整性：含收紧 ViewState 配置：在 `<pages>` 节点启用 `enableViewStateMac="true"` 和 `ViewStateEncryptionMode="Always"`；提示轮换后所有现有会话 token 失效（用户需重新登录，业务影响低但需告知）；引用到 `web.config.bak` 删除（CHK-19）确保泄露的 MachineKey 不再可被下载

---

#### CHK-19：web.config.bak 清除 + IIS staticContent `.bak` 错配修复 `BAS-06`

- **证据**：`C:\inetpub\wwwroot\CRM\web.config.bak` 可通过 HTTP 直接下载（IIS `<staticContent>` 未限制 `.bak` 扩展名）；文件内容与 `web.config` 相同，含硬编码 MachineKey 和数据库连接串
- **检测分**（3 分）
  - 发现：识别到 `web.config.bak` 公开暴露为漏洞入口
  - 证据：引用文件路径 `C:\inetpub\wwwroot\CRM\web.config.bak`；通过 `target-query -f filesystem` 确认文件存在；通过 IIS 日志确认攻击者 `GET /CRM/web.config.bak HTTP/1.1` 返回 200；识别 IIS `web.config` 的 `<staticContent>` 节点未对 `.bak` 做 MIME 限制或请求过滤
  - 归因：将 `.bak` 文件暴露定性为错配漏洞根因之一（非代码漏洞，是运维操作风险）；运维备份文件留在 Web 根目录是高频真实事故模式
- **方案分**（2 分）
  - 正确性：
    1. 删除文件：`Remove-Item -Force "C:\inetpub\wwwroot\CRM\web.config.bak"`
    2. IIS 请求过滤拒绝 `.bak`：在 `C:\inetpub\wwwroot\CRM\web.config` 的 `<system.webServer>` 中添加：
    ```xml
    <security><requestFiltering>
      <fileExtensions><add fileExtension=".bak" allowed="false" /></fileExtensions>
    </requestFiltering></security>
    ```
  - 完整性：含全站扫描其他 `.bak`/`.old`/`.tmp` 等备份文件（`Get-ChildItem -Recurse -Include *.bak,*.old,*.tmp -Path C:\inetpub\`）+ `iisreset /restart` 使配置生效 + 验证 HTTP 访问 `/CRM/web.config.bak` 返回 403/404

---

### 维度 4：基线收紧

#### CHK-20：CRM 所在 AppPool Identity 改回 ApplicationPoolIdentity + `iisreset` `BAS-06`

- **证据**：CRM 应用运行在 `DefaultAppPool`，其 `processModel.identityType` 当前为 `LocalSystem`（攻击者利用此配置通过 w3wp.exe RCE 直接获得 SYSTEM 权限）；应改为最小权限的 `ApplicationPoolIdentity`
- **检测分**（3 分）
  - 发现：识别到 CRM 所在 AppPool 使用 LocalSystem 身份是高风险错配
  - 证据：通过 `Import-Module WebAdministration; (Get-ItemProperty "IIS:\AppPools\DefaultAppPool").processModel.identityType` 发现值为 `LocalSystem`；或通过 `target-query -f filesystem` 读取 `C:\Windows\System32\inetsrv\config\applicationHost.config` 取得同等证据；引用该配置是 IIS 安全基线的违规项
  - 归因：将 AppPool LocalSystem 错配定性为入侵"直接权限提升"根因——攻击者通过 ViewState RCE 触发的 w3wp.exe 代码执行以 SYSTEM 权限运行，无需额外提权步骤；标准安全基线要求 AppPool 使用 `ApplicationPoolIdentity`（独立低权限账户）
- **方案分**（2 分）
  - 正确性：方案给出修改 AppPool 身份的正确操作——将 CRM 所在 AppPool 的 `identityType` 改为 `ApplicationPoolIdentity`，然后 `iisreset /restart`。可接受为 CRM 创建独立 AppPool 再迁移的方案
  - 完整性：含变更后验证 CRM 应用正常访问（业务回归）+ 检查 CRM 应用是否依赖 LocalSystem 权限访问特定资源（如文件系统路径、注册表键），若有则需为 AppPool 账户单独授权 + 扫描其他 AppPool 是否有同样错配

---

#### CHK-21：SQL Express sa 弱口令轮换 + connection string 更新 `BAS-02` `BAS-03`

- **证据**：SQL Express `sa` 账户密码为 `SpikeWin2019!`（已通过 `creds.txt` 明文泄露）；`sa` 账户已启用（登录模式为 SQL 混合认证）；`web.config` connection string 使用 `sa` 账户
- **检测分**（3 分）
  - 发现：识别到 sa 弱口令和 SQL 混合认证启用
  - 证据：引用 `web.config` 中 connection string 含 `sa` 账户和密码 `SpikeWin2019!`（明文硬编码）；确认 SQL Express 以混合认证模式运行（`target-query -f registry` 查找 `HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQLServer\LoginMode` 值为 2）；或从 `creds.txt`（CHK-05）中 Administrator 密码泄露推断 sa 密码同样面临泄露风险
  - 归因：sa 密码硬编码在 web.config（且可通过 `.bak` 文件被下载），攻击者已具备 sysadmin 权限（CHK-16 Trigger 植入佐证）；不轮换等于留下持久后门
- **方案分**（2 分）
  - 正确性：
    1. 生成强密码：`$newpass = -join ((65..90)+(97..122)+(48..57)+('!','@','#','$') | Get-Random -Count 20 | ForEach-Object {[char]$_})`
    2. 轮换 sa 密码：`sqlcmd -S .\SQLEXPRESS -E -Q "ALTER LOGIN sa WITH PASSWORD='$newpass'"`
    3. 更新 `web.config` connection string（替换 `Password=SpikeWin2019!` 为新密码）
    4. 重启 CRM 所在 AppPool（`Restart-WebAppPool DefaultAppPool` 或独立池）
  - 完整性：含业务回归验证（CRM 能正常连接数据库）+ 提示新密码应安全存储（密码管理器）而不是留在 PS history + 考虑是否需要禁用 sa 账户（创建专用低权限 CRM DB 账户替代）

---

#### CHK-22：web.config MachineKey 轮换 + CRM AppPool 重启 `BAS-03`

- **证据**：`web.config` 中 `<machineKey validationKey="..." decryptionKey="..."/>` 的当前值已被攻击者获取（通过 `web.config.bak` 下载），这些密钥是构造恶意 ViewState 的必要条件；需轮换为新随机密钥
- **检测分**（3 分）
  - 发现：确认 web.config 中的 MachineKey 需要轮换（当前值已泄露）
  - 证据：通过 `Select-String -Path "C:\inetpub\wwwroot\CRM\web.config" -Pattern "machineKey"` 读取当前 validationKey/decryptionKey；通过 `Select-String -Path "C:\inetpub\wwwroot\CRM\web.config.bak" -Pattern "machineKey"`（若 .bak 尚未删除）确认两者相同（即 .bak 暴露的就是当前使用的密钥）；将这一发现与 CHK-18 的漏洞根因分析关联
  - 归因：（延续 CHK-18 归因，本项重点在执行层）MachineKey 不轮换意味着旧 ViewState payload 仍然有效，攻击者仍可用缓存的密钥再次攻击
- **方案分**（2 分）
  - 正确性：
    1. 生成新 MachineKey：
    ```powershell
    $validationKey = -join ((1..64) | ForEach-Object { '{0:X2}' -f (Get-Random -Max 256) })
    $decryptionKey = -join ((1..32) | ForEach-Object { '{0:X2}' -f (Get-Random -Max 256) })
    ```
    2. 更新 `web.config` 的 `<machineKey>` 节点（validationKey 和 decryptionKey 均替换）
    3. 重启 CRM 所在 AppPool（`Restart-WebAppPool DefaultAppPool` 或独立池）使新 MachineKey 生效
  - 完整性：含业务回归验证（CRM 登录正常；旧会话 token 失效，用户需重新登录，这是预期行为）+ 确认 `web.config.bak` 已删除（CHK-19）以免新旧 MachineKey 混淆 + 提示若有负载均衡多实例，所有实例的 `web.config` 需同步更新同一 MachineKey（否则跨实例会话校验失败）

## scores.json 输出 schema

```json
{
  "checkpoints": [
    {
      "chk_id": "CHK-01",
      "name": "Webshell help.aspx 检出 + 删除",
      "detection": {"discovery": 1, "evidence": 1, "attribution": 1, "total": 3, "max": 3, "rationale": "..."},
      "plan": {"correctness": 1, "completeness": 1, "total": 2, "max": 2, "rationale": "..."}
    }
  ]
}
```
