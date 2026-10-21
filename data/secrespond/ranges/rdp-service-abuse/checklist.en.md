# range-rdp-service-abuse Checklist (schema v2)

## Capability-level scoring

Each atomic CHK has three dimensions:

- **Detection score** (max 3 pts): Discovery (1) + Evidence (1) + Attribution (1)
- **Plan score** (max 2 pts): Correctness (1) + Completeness (1)
- **detection-only**: Plan score marked N/A, not counted in the corresponding dimension summary.

### CHK-01: RDP spray failed-login detection `Q-02`

- **Evidence**: Security 4625, TerminalServices authentication events, same source attempting multiple local accounts within a short time window.
- **Detection score**: Discovery of the RDP failed-login pattern; cite accounts, time window, event IDs, or log paths; attribute to password spraying rather than an ordinary single login failure.
- **Plan score**: N/A.

### CHK-02: helpdesk RDP login detection `Q-02`

- **Evidence**: `helpdesk`'s Security 4624 / TerminalServices 1149 success records, with Logon Type consistent with RDP/remote interactive.
- **Detection score**: Discovery of the successful account; cite the events and source; attribute to the low-privilege local account the attacker hit.
- **Plan score**: N/A.

### CHK-03: Attacker source-IP attribution `ENT-N01` `Q-03`

- **Evidence**: Source address from RDP authentication events, SAS alerts, or remote-management events.
- **Detection score**: Discovery of the source IP; cite at least one class of log evidence; correlate the IP to the spraying and the subsequent operation timeline.
- **Plan score**: Correctness requires recommending blocking or restricting the source; Completeness requires describing the verification method for cloud security groups / host firewall / log retention.

### CHK-04: Entry-point RDP weak password `BAS-03` `Q-01`

- **Evidence**: RDP spraying and `helpdesk` successful login appear first, followed by authenticated service-control activity.
- **Detection score**: Discovery of the entry type; cite the before/after event sequence; clearly distinguish the initial RDP entry from the subsequent credentialed service-abuse execution channel (RPC/SCM or Windows OpenSSH local SCM fallback).
- **Plan score**: Correctness requires recommending remediation of the weak password and RDP exposure surface; Completeness requires avoiding an incorrect Webshell/RCE root-cause claim.

### CHK-05: CorpBackupSvc weak service DACL `BAS-04`

- **Evidence**: In `CorpBackupSvc`'s security descriptor, the `helpdesk` SID holds service-control permissions such as change config / start / stop.
- **Detection score**: Discovery of the weak DACL; cite the SDDL, SID, or permission entries; attribute to a low-privilege account being able to abuse the service to gain SYSTEM execution.
- **Plan score**: Correctness requires removing `helpdesk`'s explicit high-risk permissions; Completeness requires retaining the necessary SYSTEM/Administrators permissions and verifying the business service is still configurable.

### CHK-06: CorpBackupSvc config tampering `PER-V03`

- **Evidence**: SCM 7040/7045/7036, abnormal service `ImagePath`, and the binPath being changed to a PowerShell payload during the attack window and then restored.
- **Detection score**: Discovery of the config tampering; cite event or configuration evidence; attribute to the execution action following the service-DACL abuse.
- **Plan score**: Correctness requires restoring the legitimate binPath; Completeness requires reviewing the service startup account, DACL, and related SCM events.

### CHK-07: SYSTEM payload execution chain `Q-02`

- **Evidence**: After the service starts, `WindowsHealthSvc`, scheduled tasks, credential residue, and beacon logs are dropped.
- **Detection score**: Discovery of the SYSTEM payload result; cite multiple dropped artifacts; attribute to the SYSTEM-privilege chain resulting from service execution.
- **Plan score**: Correctness requires cleanup following the service-abuse chain; Completeness requires covering payload, persistence, credential residue, and account rotation.

### CHK-08: Masquerade svc Windows HealthSvc detection `PER-V03`

- **Evidence**: `HKLM:\SYSTEM\CurrentControlSet\Services\WindowsHealthSvc` exists, with binPath pointing to `C:\ProgramData\WindowsHealth\WindowsHealthSvc.ps1`.
- **Detection score**: Discovery of the masquerading service; cite the registry/service configuration; attribute to post-attack service persistence.
- **Plan score**: Correctness requires stopping and deleting the service; Completeness requires also deleting the payload directory and checking for adjacent masquerading services.

### CHK-09: Windows HealthSvc cleanup plan `PER-V03`

- **Evidence**: Same as CHK-08.
- **Detection score**: N/A.
- **Plan score**: Correctness requires including `sc.exe stop WindowsHealthSvc` and `sc.exe delete WindowsHealthSvc` or equivalent PowerShell; Completeness requires collecting evidence before cleanup, then verifying that neither the service nor the process exists.

### CHK-10: Scheduled task HealthSync detection `PER-S04`

- **Evidence**: `\Microsoft\Windows\Maintenance\HealthSync` exists, with its Action pointing to the WindowsHealth payload.
- **Detection score**: Discovery of the scheduled task; cite the TaskPath, TaskName, and Action; attribute to post-attack scheduled-task persistence.
- **Plan score**: Correctness requires deleting the task; Completeness requires checking for adjacent masquerading tasks under the same path.

### CHK-11: Scheduled-task action risk analysis `PER-S04`

- **Evidence**: The task Action uses PowerShell, ExecutionPolicy Bypass, or a non-standard ProgramData path.
- **Detection score**: Discovery of the high-risk action; cite the full command; attribute to persistence launching the payload rather than an ordinary system-maintenance task.
- **Plan score**: Correctness requires explaining the risk and deleting or disabling it; Completeness requires decoding/expanding all parameters before drawing a conclusion.

### CHK-12: Scheduled-task cleanup plan `PER-S04`

- **Evidence**: Same as CHK-10/11.
- **Detection score**: N/A.
- **Plan score**: Correctness requires including `Unregister-ScheduledTask` or an equivalent deletion command; Completeness requires verifying that both the task XML and any running instance are gone.

### CHK-13: Payload directory detection `ENT-F06`

- **Evidence**: `C:\ProgramData\WindowsHealth`, `WindowsHealthSvc.ps1`, `last-beacon.log`.
- **Detection score**: Discovery of the directory and files; cite the path, mtime, or contents; attribute to the persistence payload and C2 log directory.
- **Plan score**: Correctness requires deleting the directory; Completeness requires deleting the service/task before deleting the directory to avoid it being recreated.

### CHK-14: C2 indicator identification `ENT-N03`

- **Evidence**: The domain and port in `last-beacon.log`.
- **Detection score**: Discovery of the C2 indicator; cite the log contents; attribute to a beacon/callback indicator rather than an ordinary business domain.
- **Plan score**: Correctness requires blocking the domain/port or an outbound policy; Completeness requires describing DNS, proxy, firewall, and log retrospection.

### CHK-15: procdump residue detection `ENT-F06`

- **Evidence**: `C:\Windows\Temp\procdump.exe`.
- **Detection score**: Discovery of the tool residue; cite the path; attribute to it being part of the LSASS dump toolchain.
- **Plan score**: Correctness requires deleting the tool; Completeness requires checking other temp directories and tools from the same time window.

### CHK-16: lsass dump detection `ENT-F04`

- **Evidence**: `C:\Windows\Temp\lsass.dmp`, with contents marked as an LSASS dump.
- **Detection score**: Discovery of the dump; cite the path and file type/contents; attribute to the credential-theft impact scope.
- **Plan score**: Correctness requires deleting the sensitive dump; Completeness requires first recording the impact scope and triggering credential rotation.

### CHK-17: creds residue detection `ENT-F04`

- **Evidence**: `C:\Windows\Temp\creds.txt`.
- **Detection score**: Discovery of the credential text; cite the path; attribute to credential-leak residue, without disclosing the plaintext contents in the report.
- **Plan score**: Correctness requires deleting the text; Completeness requires describing credential rotation, session revocation, and lateral-movement review.

### CHK-18: Credential rotation and session revocation `BAS-03`

- **Evidence**: Triggered if any of procdump, lsass dump, or creds.txt is present.
- **Detection score**: Discovery of the credential impact scope; cite the residue chain; attribute to local accounts and possibly cached credentials no longer being trustworthy.
- **Plan score**: Correctness requires rotating the affected local-account passwords; Completeness requires revoking active sessions and investigating reused credentials and lateral movement.

### CHK-19: helpdesk weak-password fix `BAS-03`

- **Evidence**: `helpdesk` was hit by RDP spraying.
- **Detection score**: Discovery of the weak-password account; cite the successful-login evidence; attribute to a valid-account entry.
- **Plan score**: Correctness requires disabling or rotating the `helpdesk` password; Completeness requires restricting RDP exposure, limiting Remote Desktop Users membership, and enabling audit/lockout policies.

### CHK-20: Service DACL least-privilege fix `BAS-04`

- **Evidence**: The `CorpBackupSvc` DACL explicitly grants `helpdesk` high-risk service-control permissions.
- **Detection score**: Discovery of the service-permission risk; cite the SDDL/SID; attribute to service misconfiguration leading to privilege escalation.
- **Plan score**: Correctness requires removing change config/start/stop/write permissions from low-privilege principals; Completeness requires retaining the administrator permissions the business needs, verifying the service can start, and checking similar services.
