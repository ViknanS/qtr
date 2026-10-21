# range-aspnet-viewstate Checklist

## Scoring dimensions

Each atomic CHK has three dimensions:

- **Detection score** (max 3 pts): Discovery (1) + Evidence (1) + Attribution (1) — judges the detection Agent's report, LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness (1) + Completeness (1) — judges the remediation recommendations in the tested agent's output, LLM-as-a-Judge
- **detection-only**: Plan score marked N/A, not counted in the aggregate

### Cross-CHK common addendum (plan completeness)

To avoid "business impact" becoming a duplicate scoring item in a separate CHK, all hardening-type CHKs involving critical services (IIS / SQL Express / DefaultAppPool) **include by default** in the minimum requirement of their "plan completeness" sub-item:
> The plan must include status/syntax validation of the service changed in this operation (e.g. `iisreset /status`, `sqlcmd -Q "SELECT @@VERSION"`), and note possible side effects on other services.

If the plan lacks this item, the corresponding CHK's "completeness" scores 0.

---

## Atomic CHK list

### Dimension 1: Intrusion entity identification and disposal

#### CHK-01: Webshell help.aspx detection/removal — `help.aspx` `ENT-F01`

- **Evidence**: `C:\inetpub\wwwroot\CRM\help.aspx` exists (one-liner ASPX Webshell, can directly execute arbitrary code under w3wp.exe)
- **Detection score** (3 pts)
  - Discovery: Identifies an unexpected `help.aspx` file under the CRM site directory
  - Evidence: References the file path `C:\inetpub\wwwroot\CRM\help.aspx`; analyzes the file content as an ASPX Webshell (containing characteristic keywords such as `Request`/`Response`/`Eval`); or enumerates the CRM directory via `target-query <device> -f filesystem` to find the anomalous file
  - Attribution: Associates the Webshell with the attacker's persistent access channel after landing via ViewState RCE; notes that w3wp.exe running under LocalSystem privileges can directly execute system-level commands
- **Plan score** (2 pts)
  - Correctness: The plan provides the deletion command `Remove-Item -Force "C:\inetpub\wwwroot\CRM\help.aspx"`
  - Completeness: The plan includes post-deletion IIS log auditing (checking historical records of access to help.aspx) + scanning the site directory for other anomalous `.aspx` files (`Get-ChildItem -Recurse -Filter *.aspx | Get-FileHash` compared against the expected inventory) + verifying the file no longer exists

---

#### CHK-02: Beacon binary removal — `WindowsAuditSvc.exe` `ENT-F06`

- **Evidence**: `C:\ProgramData\WindowsAudit\WindowsAuditSvc.exe` exists (a C2 Beacon binary landed by the attacker, disguised as a Windows audit service; the same directory contains `last-beacon.log` recording C2 callback attempts)
- **Detection score** (3 pts)
  - Discovery: Identifies `C:\ProgramData\WindowsAudit\WindowsAuditSvc.exe` and the log file in the same directory
  - Evidence: References the file path; discovers the `C:\ProgramData\WindowsAudit\` directory and its contents (`WindowsAuditSvc.exe` + `last-beacon.log`) via `target-query <device> -f filesystem`; references the callback records in `last-beacon.log` containing the C2 domain `malicious-update.example.cn`; combined with the SAS alert (`MaliciousProcess`) determines the binary to be a Beacon
  - Attribution: Associates with C2 communication (`malicious-update.example.cn:8443`); disguising as a "WindowsAudit" service name is a common APT masquerading technique (naming close to system audit tools to lower suspicion)
- **Plan score** (2 pts)
  - Correctness: The plan stops the process first then deletes the file: `Stop-Process -Name WindowsAuditSvc -Force -ErrorAction SilentlyContinue`; then `Remove-Item -Recurse -Force "C:\ProgramData\WindowsAudit\"`
  - Completeness: The plan includes scanning other common C2 landing locations (`C:\ProgramData\`, `C:\Windows\Temp\`, `C:\Users\Public\`) + checking for service registration (`Get-Service | Where-Object { $_.PathName -like '*WindowsAudit*' }`) + confirming the directory has been removed

---

#### CHK-03: Beacon process termination — `WindowsAuditSvc.exe` `ENT-P02` `ENT-P03`

- **Evidence**: The SAS alert records that `WindowsAuditSvc.exe` once ran as a process and attempted to connect out to C2 (`malicious-update.example.cn:8443`); `last-beacon.log` contains callback records; the process may no longer be running due to a reboot at forensics time, but the binary is still on disk and there is a risk of restart (schtasks / WMI persistence can relaunch it)
- **Detection score** (3 pts)
  - Discovery: Identifies that `WindowsAuditSvc.exe` once ran or is still running
  - Evidence: References the SAS alert (`MaliciousProcess` type) and the C2 callback records in `last-beacon.log`; if the process is still active, references the PID and network connections; performs forensics via `target-query -f processes` or confirms prior execution through offline analysis of Prefetch files
  - Attribution: Associates the process with the C2 Beacon; explains that the process can be periodically relaunched in concert with schtasks/WMI persistence mechanisms
- **Plan score** (2 pts)
  - Correctness: `Stop-Process -Name WindowsAuditSvc -Force` (or `taskkill /F /IM WindowsAuditSvc.exe`)
  - Completeness: The plan includes a sequence explanation of blocking the outbound connection first (CHK-07 firewall rule) before killing the process + verifying the process no longer exists + checking for a parent process or watchdog mechanism that restarts it

---

#### CHK-04: mimikatz residue removal — `mimikatz.exe` `ENT-F06`
- **Evidence**: `C:\Windows\Temp\mimikatz.exe` (residue of the credential-theft tool landed by the attacker)
- **Detection score** (3 pts)
  - Discovery: Identifies `C:\Windows\Temp\mimikatz.exe`
  - Evidence: References the file path; the filename `mimikatz.exe` is a known credential-theft tool signature name; found by enumerating `C:\Windows\Temp\` via `target-query <device> -f filesystem`
  - Attribution: Associates mimikatz.exe with the attacker's credential-theft behavior before lateral movement; combined with `lsass.dmp` and `creds.txt` (CHK-05) forms a complete credential-theft chain
- **Plan score** (2 pts)
  - Correctness: `Remove-Item -Force "C:\Windows\Temp\mimikatz.exe"`
  - Completeness: The plan includes scanning the entire disk for mimikatz copies (`Get-ChildItem -Recurse -Filter mimikatz* -ErrorAction SilentlyContinue`) + concurrently handling the associated residue of CHK-05 (procdump / lsass.dmp / creds.txt)

---

#### CHK-05: Credential-dump residue (lsass) — `procdump.exe + lsass.dmp + creds.txt` `ENT-F04`

- **Evidence**: `C:\Windows\Temp\procdump.exe` (the LSASS dump tool landed by the attacker), `C:\Windows\Temp\lsass.dmp` (~30MB, LSASS memory dump, file header `MDMP`), `C:\Windows\Temp\creds.txt` (plaintext passwords parsed by mimikatz)
- **Detection score** (3 pts)
  - Discovery: Identifies that all three of the above files exist
  - Evidence: References each file path; `lsass.dmp` is identified as an LSASS process memory dump by the file header `MDMP` or file size; `creds.txt` contains plaintext passwords (must warn that the content is highly sensitive); found by enumerating `C:\Windows\Temp\` via `target-query <device> -f filesystem`
  - Attribution: Combines the three to reconstruct the credential-theft attack chain (procdump dumps lsass → mimikatz parses → creds.txt stores); explains that the attacker can use the plaintext credentials for lateral movement
- **Plan score** (2 pts)
  - Correctness: Batch deletion: `Remove-Item -Force "C:\Windows\Temp\procdump.exe","C:\Windows\Temp\lsass.dmp","C:\Windows\Temp\creds.txt"`
  - Completeness: The plan includes forensic preservation before deletion (at minimum preserving the content of creds.txt to determine the scope of credentials to rotate) + scanning other Temp/Public directories for copies + verifying all three files no longer exist after deletion + noting that all passwords appearing in creds.txt must be rotated immediately (cascading to CHK-21/CHK-22)

---

#### CHK-06: Attacker-IP inbound block — `8.217.135.152` `ENT-N01`

- **Evidence**: Attacker source IP `8.217.135.152` (visible in IIS access logs / firewall logs, the source of the initial HTTP GET `/CRM/web.config.bak` and POST `/CRM/Login.aspx`)
- **Detection score** (3 pts)
  - Discovery: Recommends blocking the attacker IP `8.217.135.152`
  - Evidence: References that IP's access records in the IIS logs (`C:\inetpub\logs\LogFiles\W3SVC1\`); identifies GET `/CRM/web.config.bak` returning 200 and the POST `/CRM/Login.aspx` ViewState payload request
  - Attribution: Determines the IP to be the source of the attacker's intrusion; associates it with the subsequent C2 domain `malicious-update.example.cn` resolving to the same IP
- **Plan score** (2 pts)
  - Correctness: Windows firewall all-protocol block: `New-NetFirewallRule -DisplayName "Block_AttackerIP" -Direction Inbound -RemoteAddress 8.217.135.152 -Action Block`
  - Completeness: Includes blocking the Outbound direction as well (`-Direction Outbound`) + verifying the rule takes effect (`Get-NetFirewallRule -DisplayName "Block_AttackerIP"`) + rule persistence is persistent by default (Windows firewall rules survive reboots) + noting that any security group/cloud firewall should be configured in sync

---

#### CHK-07: C2 outbound block — C2 endpoint `ENT-N02` `ENT-N03`

- **Evidence**: C2 endpoint `malicious-update.example.cn` → `8.217.135.152:8443` (Beacon heartbeat target)
- **Detection score** (3 pts)
  - Discovery: Identifies the C2 domain `malicious-update.example.cn` and IP `8.217.135.152` that need outbound blocking
  - Evidence: References the C2 address in the Beacon configuration (by decompiling `WindowsAuditSvc.exe` or the C2 communication records in the SAS alert); references the port `8443` (HTTPS over a non-standard port, a signature of bypassing simple firewall policies)
  - Attribution: Explains that the domain/IP combination is the Beacon's sole callback exit; even if the Beacon process is terminated, blocking outbound prevents redeployment
- **Plan score** (2 pts)
  - Correctness: Double blocking: outbound IP rule `New-NetFirewallRule -DisplayName "Block_C2_IP_Out" -Direction Outbound -RemoteAddress 8.217.135.152 -Action Block`; outbound port rule `New-NetFirewallRule -DisplayName "Block_C2_8443_Out" -Direction Outbound -Protocol TCP -RemotePort 8443 -Action Block`; DNS-layer blocking (modifying the hosts file `Add-Content C:\Windows\System32\drivers\etc\hosts "0.0.0.0 malicious-update.example.cn"`)
  - Completeness: Includes an explanation of three-layer blocking (IP + port + DNS) + verifying each rule takes effect + explaining the limitation of the hosts-file modification for non-DNS-resolution paths (hardcoded-IP scenarios)

---

#### CHK-08: version.dll hijack file — `version.dll` `ENT-F06` `PER-H02`

- **Evidence**: `C:\Program Files\Notepad++\version.dll` (the DLL search-order hijack carrier planted by the attacker; a copy of the system `version.dll`, the signature is still valid but it appears in an unexpected location, and its creation time matches the attack window)
- **Detection score** (3 pts)
  - Discovery: Identifies that `C:\Program Files\Notepad++\version.dll` exists and does not belong to a normal Notepad++ installation
  - Evidence: Discovers the unexpected DLL by enumerating the Notepad++ directory via `target-query <device> -f filesystem`; the DLL has the same hash as `C:\Windows\System32\version.dll` (the attacker copies the system DLL as a carrier; in a real scenario it would be replaced with a forwarding DLL containing a malicious DllMain); the file creation time falls within the attack window
  - Attribution: Identifies the DLL search-order hijack technique (T1574.001 — on Notepad++ startup, the version.dll in its own directory is loaded preferentially); explains that this technique is common in APTs, triggering on every Notepad++ startup once planted
- **Plan score** (2 pts)
  - Correctness: `Remove-Item -Force "C:\Program Files\Notepad++\version.dll"`
  - Completeness: The plan includes post-deletion verification that no residual unexpected DLL remains in the Notepad++ directory + scanning other application directories (`Program Files\`, `Program Files (x86)\`) for similar plants

---

### Dimension 2: Persistence cleanup

#### CHK-09: schtasks task location — `AuditTask` `PER-S04`

- **Evidence**: The scheduled task `\Microsoft\Windows\Maintenance\AuditTask` exists (XML file `C:\Windows\System32\Tasks\Microsoft\Windows\Maintenance\AuditTask`, Trigger daily at 10:23, Author: SYSTEM)
- **Detection score** (3 pts)
  - Discovery: Identifies the suspicious scheduled task `\Microsoft\Windows\Maintenance\AuditTask`
  - Evidence: Enumerates scheduled tasks via `target-query <device> -f tasks` to obtain the complete XML; references key Task fields: `<Author>SYSTEM</Author>`, Trigger (daily at 10:23), Action (`powershell.exe -ep bypass -enc <base64>`); or on a live system uses `Get-ScheduledTask -TaskPath "\Microsoft\Windows\Maintenance\" -TaskName "AuditTask"`
  - Attribution: Determines the Task to be a persistence mechanism; notes that the path `\Microsoft\Windows\Maintenance\` is a system-task masquerading path commonly used by attackers; the SYSTEM identity + `-ep bypass -enc` parameter combination is a strong malicious signal
- **Plan score** (2 pts)
  - Correctness: The plan directs to CHK-10 to decode and confirm the payload content first, then delete via CHK-11; the standalone location step only needs to confirm the task exists
  - Completeness: The plan recommends enumerating all scheduled tasks with non-standard paths (`Get-ScheduledTask | Where-Object { $_.TaskPath -notlike "\Microsoft\Windows\*" -or $_.Principal.UserId -eq "SYSTEM" }`) to cover similar plants

---

#### CHK-10: schtasks payload decoding `PER-S04`

- **Evidence**: The base64 in `powershell.exe -ep bypass -enc <base64>` within the AuditTask Action decodes to a download command that pulls stage3
- **Detection score** (3 pts)
  - Discovery: Identifies the base64-encoded payload in the Action and performs decoding analysis
  - Evidence: References the base64 string (extracted from the `<Arguments>` field of the Task XML); provides the decoding result (the PowerShell command decoded by `[System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String("<b64>"))`); the decoding result shows a download-execute command (in a form such as IEX (New-Object Net.WebClient).DownloadString)
  - Attribution: Associates the encoded payload with the stage3 C2 pull behavior; notes that `-ep bypass` bypassing the execution policy is a hallmark technique of malicious PowerShell
- **Plan score** (2 pts)
  - Correctness: The decoding analysis itself is the core of the plan; directs to CHK-11 to delete the task
  - Completeness: The plan recommends reporting the decoding result to the SOC (including URL, C2 address, and other IOCs); confirms the decoding process uses UTF-16LE decoding (PowerShell `-enc` defaults to UTF-16LE)

---

#### CHK-11: schtasks deletion `PER-S04`

- **Evidence**: AuditTask has been located (CHK-09), the payload has been decoded (CHK-10); this item is the actual deletion
- **Detection score** (3 pts)
  - Discovery: Confirms the task still exists before performing the deletion
  - Evidence: `Get-ScheduledTask -TaskPath "\Microsoft\Windows\Maintenance\" -TaskName "AuditTask"` returns a valid object
  - Attribution: (continues the CHK-09 attribution; this item focuses on execution)
- **Plan score** (2 pts)
  - Correctness: `Unregister-ScheduledTask -TaskPath "\Microsoft\Windows\Maintenance\" -TaskName "AuditTask" -Confirm:$false`
  - Completeness: Includes post-deletion verification (the task no longer appears) + noting to back up the XML file to the forensic archive before deletion + scanning for other tasks with the same payload hash (guarding against backup persistence)

---

#### CHK-12: WMI subscription location — `AuditMonitor` / `AuditAction` `PER-E02`

- **Evidence**: The WMI `root\subscription` namespace contains: an `__EventFilter` named `AuditMonitor` (triggered by `Win32_LocalTime Hour=10 AND Minute=23`), an `ActiveScriptEventConsumer` named `AuditAction` (ScriptText contains VBScript that appends a timestamp to a log file), and a `__FilterToConsumerBinding` binding the two
- **Detection score** (3 pts)
  - Discovery: Identifies all 3 constituent objects of the WMI permanent event subscription
  - Evidence: Offline-parses `C:\Windows\System32\wbem\Repository\OBJECTS.DATA` on the block device via python-cim:
    ```python
    from cim import CIM
    c = CIM('/mnt/.../Repository')
    for obj in c.query("SELECT * FROM __FilterToConsumerBinding"):
        print(obj)
    ```
    or on a live system uses `Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding`; references Filter.Name = `AuditMonitor`, Consumer.Name = `AuditAction`
  - Attribution: WMI permanent subscription is a fileless persistence technique commonly used by Windows APTs; the `Win32_LocalTime` time-condition trigger is extremely rare in legitimate management tools and is a high-confidence malicious signal
- **Plan score** (2 pts)
  - Correctness: The plan explicitly states that 3 objects (Filter + Consumer + Binding) must be deleted; directs to CHK-14
  - Completeness: The plan recommends enumerating all non-system WMI subscriptions (`Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding`) to confirm no other malicious subscriptions

---

#### CHK-13: WMI ScriptText analysis `PER-E02`

- **Evidence**: The `ScriptText` field of `ActiveScriptEventConsumer "AuditAction"` contains VBScript code (appending a timestamp to `C:\ProgramData\WindowsAudit\wmi-fired.log` — forming dual-path persistence together with the schtasks AuditTask, functionally equivalent but implemented in a different language)
- **Detection score** (3 pts)
  - Discovery: Identifies that the ScriptText field contains an executable payload
  - Evidence: Extracts the `ScriptText` field from the `AuditAction` Consumer object; analyzes the VBScript content — `CreateObject("Scripting.FileSystemObject")` writes a log to the `WindowsAudit` directory (the same as the Beacon landing directory)
  - Attribution: Compares with the schtasks payload of CHK-10, noting that the attacker deployed dual-path persistence (schtasks + WMI), both writing to the same `WindowsAudit` directory, indicating that the defense must clear both paths simultaneously
- **Plan score** (2 pts)
  - Correctness: Analyzes the VBScript content, confirming that the log path is consistent with the C2 infrastructure directory
  - Completeness: Associates the file path in the VBScript with the CHK-02 Beacon directory `C:\ProgramData\WindowsAudit\`

---

#### CHK-14: WMI objects full cleanup `PER-E02`

- **Evidence**: The Filter `AuditMonitor`, Consumer `AuditAction`, and Binding under WMI `root\subscription` have been located (CHK-12) and all need to be deleted
- **Detection score** (3 pts)
  - Discovery: Confirms all 3 objects exist before deletion (guarding against false negatives and incomplete removal)
  - Evidence: `Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding | Where-Object { $_.Filter -like '*AuditMonitor*' }` returns non-empty
  - Attribution: (continues the CHK-12 attribution)
- **Plan score** (2 pts)
  - Correctness: Deletes the 3 objects in order (delete the Binding first, then the Filter and Consumer, to prevent orphaned objects from triggering):
    ```powershell
    Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding |
      Where-Object { $_.Filter -like '*AuditMonitor*' } | Remove-WmiObject
    Get-WmiObject -Namespace root\subscription -Class __EventFilter |
      Where-Object Name -eq 'AuditMonitor' | Remove-WmiObject
    Get-WmiObject -Namespace root\subscription -Class ActiveScriptEventConsumer |
      Where-Object Name -eq 'AuditAction' | Remove-WmiObject
    ```
  - Completeness: Includes post-deletion verification (all three Get-WmiObject return empty) + noting that the `winmgmt` service may need to be restarted to clear the in-memory cache + recommending manual review with the `WMI Explorer` tool

---

#### CHK-15: DLL-hijack detection `PER-H02`

- **Evidence**: `C:\Program Files\Notepad++\version.dll` does not belong to a normal Notepad++ installation; the DLL has the same hash as `C:\Windows\System32\version.dll` (the attacker copied the system DLL as a carrier), and its creation time matches the attack window
- **Detection score** (3 pts)
  - Discovery: Identifies an unexpected `version.dll` under the Notepad++ directory
  - Evidence: Discovers the DLL by enumerating the Notepad++ directory via `target-query <device> -f filesystem`; note that the DLL has the same hash as the same-named DLL in System32 — the attacker uses a system DLL copy as a placeholder in this range (in a real APT scenario it would be replaced with a forwarding DLL containing a malicious DllMain); the file metadata (creation/modification time) falls within the attack time window
  - Attribution: DLL search-order hijack (T1574.001 side-loading) — in the Windows DLL search order, the application's own directory takes precedence over System32, so on Notepad++ startup the version.dll in its own directory is loaded preferentially
- **Plan score** (2 pts)
  - Correctness: Delete `C:\Program Files\Notepad++\version.dll` (directs to the CHK-08 execution layer)
  - Completeness: The plan includes scanning other application directories (`Program Files\`, `Program Files (x86)\`) for similar unexpected DLL plants

---

#### CHK-16: MSSQL trigger/xp_cmdshell detection `PER-D02`

- **Evidence**: The `master` database contains a Server-level Logon Trigger `tr_audit_logon` (`ON ALL SERVER FOR LOGON`, with `EXEC xp_cmdshell 'cmd.exe /c echo ...'` in its body), and `xp_cmdshell` is enabled. On SQL Express this Trigger causes **all SQL logins (including sa and Windows authentication) to fail** — the runtime error of xp_cmdshell propagates into the LOGON event context, causing the login transaction to roll back.

  > **Critical**: This Trigger is INTENTIONALLY BROKEN — the attacker-planted Logon Trigger produces a runtime error when triggering xp_cmdshell on SQL Express, causing **all** subsequent SQL connections (including sa mixed authentication and Windows integrated authentication) to fail. The SQL Error Log records `"Logon failed for login 'X' due to trigger execution"`. The detection Agent should be able to identify this anomalous pattern from the ERRORLOG.
- **Detection score** (3 pts)
  - Discovery: Identifies the MSSQL Logon Trigger `tr_audit_logon` and the xp_cmdshell enabled configuration
  - Evidence: Discovers the `"Logon failed for login ... due to trigger execution"` error entries via the SQL Error Log (`C:\Program Files\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQL\Log\ERRORLOG`) (all connection attempts leave this record); or via offline inspection of `master.mdf`; references the `xp_cmdshell` call in the Trigger definition
  - Attribution: The MSSQL Logon Trigger is a database-level persistence technique unique to SQL Server (SQL Express has no SQL Agent, so a Logon Trigger is a reachable equivalent substitute); enabling xp_cmdshell grants the database engine OS-command-execution capability; even though the Trigger is broken, its existence itself indicates that the attacker has sysadmin privileges
- **Plan score** (2 pts)
  - Correctness: The plan explicitly states: since the Trigger causes all SQL logins to fail, SQL Express must be started in **single-user mode** (`sqlservr.exe -m -s SQLEXPRESS`), which skips Logon Trigger execution; or bypass it using DAC (Dedicated Admin Connection)
  - Completeness: The plan includes reviewing the current status of xp_cmdshell + warning that all SQL connection methods (sa/Windows auth) are affected + directing to CHK-17 to perform the deletion

---

#### CHK-17: MSSQL backdoor cleanup `PER-D02`

- **Evidence**: The MSSQL Logon Trigger `tr_audit_logon` has been located (CHK-16) and needs to be deleted with xp_cmdshell disabled
- **Detection score** (3 pts)
  - Discovery: Confirms the Trigger still exists and xp_cmdshell is enabled before deletion
  - Evidence: After successfully connecting in single-user mode: `SELECT name FROM sys.server_triggers WHERE name = 'tr_audit_logon'` returns 1 row; the `run_value` of `EXEC sp_configure 'xp_cmdshell'` is 1
  - Attribution: (continues the CHK-16 attribution; this item focuses on execution)
- **Plan score** (2 pts)
  - Correctness: The Logon Trigger must be bypassed (because the Trigger causes **all** SQL logins to fail). Equivalent correct paths:
    - **Path A (single-user mode)**: `net stop MSSQL$SQLEXPRESS` → `sqlservr.exe -m -s SQLEXPRESS` → `sqlcmd -S .\SQLEXPRESS -E` to connect → `DROP TRIGGER tr_audit_logon ON ALL SERVER; EXEC sp_configure 'xp_cmdshell', 0; RECONFIGURE;` → restore normal service
    - **Path B (DAC)**: Connect via the Dedicated Admin Connection using `sqlcmd -S admin:.\SQLEXPRESS -E` (DAC does not trigger the Logon Trigger) → same DROP commands as above
    - Both paths are acceptable; the plan must explain why a direct connection is not possible (the Trigger blocks all logins)
  - Completeness: Includes verifying the Trigger does not exist after restoring normal mode + xp_cmdshell is disabled + CRM application connection-string verification (accessing the page to confirm CRM is still available)
    ```sql
    -- Execute in sqlcmd:
    SELECT COUNT(*) FROM sys.server_triggers WHERE name = 'tr_audit_logon';
    -- Expect a return of 0
    EXEC sp_configure 'xp_cmdshell';
    -- Expect run_value = 0
    ```

---

### Dimension 3: Vulnerability remediation

#### CHK-18: ViewState root cause + MachineKey `VUL-02`

- **Evidence**: The hardcoded `<machineKey validationKey="..." decryptionKey="..."/>` in `web.config` allows the attacker to craft a validly signed malicious ViewState payload with ysoserial.net; the hardcoded MachineKey is the root cause
- **Detection score** (3 pts)
  - Discovery: Identifies that the root cause of the ASP.NET ViewState deserialization vulnerability is the leak of the hardcoded MachineKey
  - Evidence: References the `validationKey` and `decryptionKey` values of the `<machineKey>` node in `web.config`; explains that after the attacker obtains these two keys by downloading `web.config.bak` (CHK-19), they can craft arbitrary valid ViewState payloads with ysoserial.net; combined with the POST `/CRM/Login.aspx` request in the IIS logs
  - Attribution: Characterizes the hardcoded MachineKey as a vulnerability (rather than a mere misconfiguration) — ASP.NET's ViewState integrity depends on the MachineKey, and a key leak is equivalent to satisfying the exploitation condition for deserialization RCE; together with the `web.config.bak` misconfiguration (CHK-19) and AppPool LocalSystem (CHK-20) forms a three-in-one entry point
- **Plan score** (2 pts)
  - Correctness: Rotate the MachineKey: generate a new random `validationKey` (64-byte hex) and `decryptionKey` (32-byte hex); update the `<machineKey>` node in `web.config`; `iisreset /restart` to apply the config (directs to the CHK-22 execution layer)
  - Completeness: Includes tightening the ViewState configuration: enable `enableViewStateMac="true"` and `ViewStateEncryptionMode="Always"` on the `<pages>` node; note that all existing session tokens become invalid after rotation (users must log in again; business impact is low but must be communicated); references the deletion of `web.config.bak` (CHK-19) to ensure the leaked MachineKey can no longer be downloaded

---

#### CHK-19: web.config.bak + IIS fix `BAS-06`

- **Evidence**: `C:\inetpub\wwwroot\CRM\web.config.bak` can be downloaded directly via HTTP (IIS `<staticContent>` does not restrict the `.bak` extension); the file content is the same as `web.config`, containing the hardcoded MachineKey and database connection string
- **Detection score** (3 pts)
  - Discovery: Identifies that the public exposure of `web.config.bak` is a vulnerability entry point
  - Evidence: References the file path `C:\inetpub\wwwroot\CRM\web.config.bak`; confirms the file exists via `target-query -f filesystem`; confirms via the IIS logs that the attacker's `GET /CRM/web.config.bak HTTP/1.1` returned 200; identifies that the `<staticContent>` node of the IIS `web.config` has no MIME restriction or request filtering for `.bak`
  - Attribution: Characterizes the `.bak` file exposure as one of the root causes of the misconfiguration vulnerability (not a code vulnerability but an operational risk); leaving operational backup files in the Web root is a high-frequency real-world incident pattern
- **Plan score** (2 pts)
  - Correctness:
    1. Delete the file: `Remove-Item -Force "C:\inetpub\wwwroot\CRM\web.config.bak"`
    2. IIS request filtering to deny `.bak`: add to `<system.webServer>` in `C:\inetpub\wwwroot\CRM\web.config`:
    ```xml
    <security><requestFiltering>
      <fileExtensions><add fileExtension=".bak" allowed="false" /></fileExtensions>
    </requestFiltering></security>
    ```
  - Completeness: Includes a site-wide scan for other backup files such as `.bak`/`.old`/`.tmp` (`Get-ChildItem -Recurse -Include *.bak,*.old,*.tmp -Path C:\inetpub\`) + `iisreset /restart` to apply the config + verifying that HTTP access to `/CRM/web.config.bak` returns 403/404

---

### Dimension 4: Baseline hardening

#### CHK-20: CRM AppPool identity reset `BAS-06`

- **Evidence**: The CRM application runs in `DefaultAppPool`, whose `processModel.identityType` is currently `LocalSystem` (the attacker leverages this configuration to directly gain SYSTEM privileges via w3wp.exe RCE); it should be changed to the least-privilege `ApplicationPoolIdentity`
- **Detection score** (3 pts)
  - Discovery: Identifies that the CRM AppPool using the LocalSystem identity is a high-risk misconfiguration
  - Evidence: Discovers the value is `LocalSystem` via `Import-Module WebAdministration; (Get-ItemProperty "IIS:\AppPools\DefaultAppPool").processModel.identityType`; or obtains equivalent evidence by reading `C:\Windows\System32\inetsrv\config\applicationHost.config` via `target-query -f filesystem`; references that this configuration is a violation of the IIS security baseline
  - Attribution: Characterizes the AppPool LocalSystem misconfiguration as the root cause of the intrusion's "direct privilege escalation" — the w3wp.exe code execution triggered by the attacker via ViewState RCE runs with SYSTEM privileges, requiring no additional escalation step; the standard security baseline requires the AppPool to use `ApplicationPoolIdentity` (a separate low-privilege account)
- **Plan score** (2 pts)
  - Correctness: The plan provides the correct operation to modify the AppPool identity — change the `identityType` of the CRM AppPool to `ApplicationPoolIdentity`, then `iisreset /restart`. A plan to create a separate AppPool for CRM and migrate to it is acceptable
  - Completeness: Includes post-change verification that the CRM application is accessible normally (business regression) + checking whether the CRM application depends on LocalSystem privileges to access specific resources (such as file-system paths, registry keys), and if so, separately authorizing the AppPool account + scanning other AppPools for the same misconfiguration

---

#### CHK-21: SQL sa password rotation `BAS-02` `BAS-03`

- **Evidence**: The SQL Express `sa` account password is `SpikeWin2019!` (already leaked in plaintext via `creds.txt`); the `sa` account is enabled (login mode is SQL mixed authentication); the `web.config` connection string uses the `sa` account
- **Detection score** (3 pts)
  - Discovery: Identifies the sa weak password and that SQL mixed authentication is enabled
  - Evidence: References that the connection string in `web.config` contains the `sa` account and the password `SpikeWin2019!` (hardcoded in plaintext); confirms SQL Express runs in mixed authentication mode (`target-query -f registry` looking up `HKLM\SOFTWARE\Microsoft\Microsoft SQL Server\MSSQL15.SQLEXPRESS\MSSQLServer\LoginMode` with value 2); or infers from the Administrator password leak in `creds.txt` (CHK-05) that the sa password faces the same leak risk
  - Attribution: The sa password is hardcoded in web.config (and can be downloaded via the `.bak` file), and the attacker already has sysadmin privileges (corroborated by the CHK-16 Trigger plant); not rotating it is equivalent to leaving a persistent backdoor
- **Plan score** (2 pts)
  - Correctness:
    1. Generate a strong password: `$newpass = -join ((65..90)+(97..122)+(48..57)+('!','@','#','$') | Get-Random -Count 20 | ForEach-Object {[char]$_})`
    2. Rotate the sa password: `sqlcmd -S .\SQLEXPRESS -E -Q "ALTER LOGIN sa WITH PASSWORD='$newpass'"`
    3. Update the `web.config` connection string (replace `Password=SpikeWin2019!` with the new password)
    4. Restart the CRM AppPool (`Restart-WebAppPool DefaultAppPool` or the separate pool)
  - Completeness: Includes business regression verification (CRM can connect to the database normally) + noting that the new password should be stored securely (a password manager) rather than left in PS history + considering whether the sa account should be disabled (creating a dedicated low-privilege CRM DB account as a replacement)

---

#### CHK-22: MachineKey rotation + AppPool restart `BAS-03`

- **Evidence**: The current value of `<machineKey validationKey="..." decryptionKey="..."/>` in `web.config` has been obtained by the attacker (downloaded via `web.config.bak`); these keys are the necessary condition for crafting a malicious ViewState; they must be rotated to new random keys
- **Detection score** (3 pts)
  - Discovery: Confirms the MachineKey in web.config needs to be rotated (the current value has leaked)
  - Evidence: Reads the current validationKey/decryptionKey via `Select-String -Path "C:\inetpub\wwwroot\CRM\web.config" -Pattern "machineKey"`; via `Select-String -Path "C:\inetpub\wwwroot\CRM\web.config.bak" -Pattern "machineKey"` (if the .bak has not yet been deleted) confirms the two are identical (i.e. the .bak exposes exactly the keys currently in use); associates this finding with the vulnerability root-cause analysis of CHK-18
  - Attribution: (continues the CHK-18 attribution; this item focuses on the execution layer) Not rotating the MachineKey means old ViewState payloads remain valid, and the attacker can still attack again with the cached keys
- **Plan score** (2 pts)
  - Correctness:
    1. Generate a new MachineKey:
    ```powershell
    $validationKey = -join ((1..64) | ForEach-Object { '{0:X2}' -f (Get-Random -Max 256) })
    $decryptionKey = -join ((1..32) | ForEach-Object { '{0:X2}' -f (Get-Random -Max 256) })
    ```
    2. Update the `<machineKey>` node in `web.config` (replacing both validationKey and decryptionKey)
    3. Restart the CRM AppPool (`Restart-WebAppPool DefaultAppPool` or the separate pool) to apply the new MachineKey
  - Completeness: Includes business regression verification (CRM login works normally; old session tokens become invalid, users must log in again, which is expected behavior) + confirming that `web.config.bak` has been deleted (CHK-19) to avoid confusion between old and new MachineKeys + noting that if there is a load-balanced multi-instance setup, the `web.config` of all instances must be updated in sync with the same MachineKey (otherwise cross-instance session validation fails)

## scores.json output schema

```json
{
  "checkpoints": [
    {
      "chk_id": "CHK-01",
      "name": "Webshell help.aspx detection/removal",
      "detection": {"discovery": 1, "evidence": 1, "attribution": 1, "total": 3, "max": 3, "rationale": "..."},
      "plan": {"correctness": 1, "completeness": 1, "total": 2, "max": 2, "rationale": "..."}
    }
  ]
}
```
