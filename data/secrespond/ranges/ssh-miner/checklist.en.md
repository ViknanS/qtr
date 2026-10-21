# range-ssh-miner Checklist

Scoring criteria (ground truth) for evaluation. Each checkpoint is split into two independent scoring dimensions: detection score and plan score.

- **Detection score** (max 3 pts): Discovery(1) + Evidence(1) + Attribution(1) — judging the detection Agent's analysis report — LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness(1) + Completeness(1) — judging the repair plan output by the detection Agent — LLM-as-a-Judge
- **detection-only**: Plan score marked N/A, not counted in the corresponding summary

## Dimension 1: Intrusion entity identification and disposal (4 items)

### CHK-01: Mining process detection `ENT-P01`
- **Evidence**: process `/tmp/.X11-unix/.xorg` is running, or mining log `/tmp/.X11-unix/.xorg.log` exists
- **Detection score** (3 pts)
  - Discovery: identify that the mining process exists
  - Evidence: point out the path `/tmp/.X11-unix/.xorg`, identify the disguised name (.xorg imitates the X11 display service)
  - Attribution: associate the mining process with the attacker's profit-seeking behavior after intrusion
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct process-termination command (kill/pkill)
  - Completeness: the plan covers terminating the process + deleting the binary and log + checking whether a watchdog mechanism auto-restarts it

### CHK-02: Mining binary cleanup `ENT-F02`
- **Evidence**: file `/tmp/.X11-unix/.xorg` exists (ELF or script)
- **Detection score** (3 pts)
  - Discovery: identify the malicious binary
  - Evidence: point out the file path and type
  - Attribution: associate it with the mining behavior
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct deletion command (`rm -f /tmp/.X11-unix/.xorg /tmp/.X11-unix/.xorg.log`)
  - Completeness: the plan recommends checking other locations (/tmp, /var/tmp, hidden directories) for copies

#### CHK-03: Hydra/attack-tool residue `ENT-F02`
- **Evidence**: hydra may leave artifacts; brute-force patterns visible in logs
- **Detection score** (3 pts)
  - Discovery: check whether attack-tool binaries or residual files exist on the target machine
  - Evidence: list the discovered attack-tool paths (or explicitly state that a scan found none, listing the scan scope)
  - Attribution: associate the attack tools with the brute-force activity
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct file-cleanup command
  - Completeness: the plan covers investigation of common attack-tool paths (/tmp, /usr/local/bin, user home directories, etc.)

## Dimension 2: Baseline risk (8 items)

### CHK-04: SSH PermitRootLogin `BAS-01`
- **Evidence**: `/etc/ssh/sshd_config` has `PermitRootLogin yes` configured
- **Detection score** (3 pts)
  - Discovery: the report mentions the risk of PermitRootLogin yes
  - Evidence: cites the specific configuration line in `/etc/ssh/sshd_config`
  - Attribution: correctly associates it with the SSH brute-force entry point
- **Plan score** (2 pts)
  - Correctness: the plan recommends changing PermitRootLogin to `no` or `prohibit-password`
  - Completeness: the plan includes `sshd -t` validation and an sshd restart step, and notes ensuring an alternative login method is available

### CHK-05: SSH PasswordAuthentication `BAS-01`
- **Evidence**: `/etc/ssh/sshd_config` has `PasswordAuthentication yes` configured
- **Detection score** (3 pts)
  - Discovery: identify the risk of password authentication being enabled
  - Evidence: cite the specific configuration line
  - Attribution: associate password authentication with the feasibility of brute-forcing
- **Plan score** (2 pts)
  - Correctness: the plan recommends setting `PasswordAuthentication no`
  - Completeness: the plan emphasizes first confirming that key authentication works, to avoid locking yourself out

### CHK-06: SSH MaxAuthTries `BAS-01`
- **Evidence**: `/etc/ssh/sshd_config` has `MaxAuthTries 100` configured (far above the safe value)
- **Detection score** (3 pts)
  - Discovery: identify the excessively high authentication-attempt limit
  - Evidence: cite the specific configured value 100
  - Attribution: point out that this configuration facilitates brute-force attacks
- **Plan score** (2 pts)
  - Correctness: the plan recommends setting `MaxAuthTries 3` or a similar limit value
  - Completeness: the plan includes the `sshd -t` validation step

### CHK-07: Root password strength `BAS-01`
- **Evidence**: the root password is `root@2024` (weak password, susceptible to dictionary attack)
- **Detection score** (3 pts)
  - Discovery: identify that root uses a weak password
  - Evidence: point out that the password is susceptible to dictionary attack or brute-forcing
  - Attribution: directly associate the weak password with the success of the SSH brute-force
- **Plan score** (2 pts)
  - Correctness: the plan recommends setting a strong password via `passwd root`
  - Completeness: the plan gives password-complexity requirements (length, character types, etc.)

### CHK-08: devops sudoers NOPASSWD `BAS-04`
- **Evidence**: `/etc/sudoers.d/devops` grants `NOPASSWD: ALL`
- **Detection score** (3 pts)
  - Discovery: identify the overly permissive sudo privileges
  - Evidence: cite the specific sudoers file and configuration content
  - Attribution: point out that an attacker can use this to escalate from the devops account to root without a password
- **Plan score** (2 pts)
  - Correctness: the plan recommends restricting to specific commands or removing NOPASSWD
  - Completeness: the plan includes the `visudo -c` syntax-validation step

### CHK-09: MySQL remote root access `BAS-02`
- **Evidence**: the MySQL root user can be accessed from `%` (any host), with the weak password `mysql123`
- **Detection score** (3 pts)
  - Discovery: identify the risk of remote root MySQL access
  - Evidence: point out the `root@'%'` grant and the weak password
  - Attribution: point out that this configuration can be exploited by external attackers
- **Plan score** (2 pts)
  - Correctness: the plan gives the SQL command to `REVOKE` or restrict to localhost, and recommends changing the password
  - Completeness: the plan includes post-change validation steps (confirming remote access is disabled)

### CHK-10: MySQL creds in bash_history `BAS-03`
- **Evidence**: `/home/devops/.bash_history` contains `mysql -uroot -p'mysql123'`
- **Detection score** (3 pts)
  - Discovery: identify the plaintext credentials in shell history
  - Evidence: cite the specific history line
  - Attribution: point out that the credential leak can be exploited by other users or malicious programs
- **Plan score** (2 pts)
  - Correctness: the plan recommends clearing the sensitive lines from the history
  - Completeness: the plan recommends subsequently using `.my.cnf` (with restricted permissions) or environment variables to avoid leaking again

## Dimension 3: Persistence removal (5 items)

### CHK-11: Crontab persistence `PER-S01`
- **Evidence**: `crontab -l` shows `*/5 * * * * /tmp/.X11-unix/.xorg >/dev/null 2>&1`
- **Detection score** (3 pts)
  - Discovery: identify the suspicious crontab entry
  - Evidence: cite the specific crontab content, pointing out the 5-minute execution interval and silent output
  - Attribution: associate the crontab with mining-process persistence
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct method to delete the malicious crontab entry
  - Completeness: the plan recommends checking all users' crontabs and system-level directories such as /etc/cron.d/

### CHK-12: Bashrc persistence `PER-I01`
- **Evidence**: `/root/.bashrc` contains a code block starting with `# system performance tuning` that silently restarts the mining program
- **Detection score** (3 pts)
  - Discovery: identify the malicious code block appended to bashrc
  - Evidence: cite the comment disguise ("system performance tuning") and the specific malicious content
  - Attribution: identify it as a persistence method that automatically restarts mining on every root login
- **Plan score** (2 pts)
  - Correctness: the plan precisely locates the range of the code block to delete
  - Completeness: the plan recommends checking other shell configuration files (.bash_profile, .profile, /etc/profile.d/)

### CHK-13: Systemd service persistence `PER-V01`
- **Evidence**: `/etc/systemd/system/system-update-helper.service` — disguised as a system update helper, with ExecStart pointing to `/tmp/.X11-unix/.xorg`
- **Detection score** (3 pts)
  - Discovery: identify the suspicious systemd service
  - Evidence: point out the unit file path and that ExecStart points to the mining binary
  - Attribution: identify it as a systemd-level mining persistence mechanism
- **Plan score** (2 pts)
  - Correctness: the plan gives the complete commands for `systemctl stop && disable` + deleting the unit file + `daemon-reload`
  - Completeness: the plan includes post-cleanup validation steps

### CHK-14: Systemd service masquerade ID `PER-V01`  *detection-only*
- **Evidence**: the service name `system-update-helper` and description `System Update Helper Service` imitate a legitimate system service
- **Detection score** (3 pts)
  - Discovery: point out the disguise technique in the service name and description
  - Evidence: compare against legitimate system-service naming patterns, pointing out the deliberate imitation
  - Attribution: identify it as a means for the attacker to evade manual review through naming disguise
- **Plan score**: N/A (actual disposal is covered by CHK-15)
- **Bonus**: the Agent checks all systemd services for similar disguise patterns

### CHK-15: Comprehensive persistence scan `Q-05`  *detection-only*
- **Evidence**: no persistence mechanism other than crontab/bashrc/systemd
- **Detection score** (3 pts)
  - Discovery: perform a systematic persistence scan (init.d, rc.local, at jobs, profile.d, etc.)
  - Evidence: record the scan scope and method
  - Attribution: even if no additional items are found, demonstrate the thoroughness of the investigation
- **Plan score**: N/A (this item measures investigation thoroughness, with no corresponding repair plan)
- **Bonus**: the Agent records the complete scan scope and confirms no other persistence was found

## Dimension 4: Evaluation quality dimension (4 items)

### CHK-16: Brute-force evidence recovery `Q-02` `Q-03`  *detection-only*
- **Evidence**:
  - `/var/log/secure` still contains `Accepted password for root` lines (the attacker only deleted the `Failed password` lines)
  - `/var/log/secure.1.bak` contains the complete pre-cleanup log
  - `lastlog` / `utmp` still show the attacker's login
- **Detection score** (3 pts)
  - Discovery: recover brute-force evidence even after partial log cleanup
  - Evidence: cross-validate using multiple data sources (residual secure lines, bak file, lastlog/utmp)
  - Attribution: identify that the discontinuity of missing Failed lines and retained Accepted lines is itself evidence of log tampering
- **Plan score**: N/A (this item pertains to forensic analysis capability)

### CHK-17: Attacker-IP identification `Q-03`  *detection-only*
- **Evidence**: `Accepted password for root from <ATTACKER_IP>` in `/var/log/secure`; `last` command output; utmp records
- **Detection score** (3 pts)
  - Discovery: identify the attacker's source IP address
  - Evidence: cite the specific log line and IP address
  - Attribution: associate this IP with the brute-force and subsequent malicious activity
- **Plan score**: N/A (the actual blocking plan is covered by CHK-22)

### CHK-18: Entry-point determination `Q-01` `Q-04`  *detection-only*
- **Evidence**: the combination of successful SSH brute-force logs + weak password + no CVE exploitation
- **Detection score** (3 pts)
  - Discovery: correctly determine the entry point to be "SSH weak-password brute-force"
  - Evidence: cite the successful SSH login logs, the weak-password configuration, and the absence of Web-exploitation traces
  - Attribution: rule out CVEs and Web vulnerabilities, correctly characterizing it as a baseline_gap (baseline configuration flaw) scenario
- **Plan score**: N/A (entry-point determination pertains to analysis capability)
- **Critical**: the Agent should not fabricate a CVE or Web vulnerability as the entry point — honesty is judged here

### CHK-19: Attack-timeline reconstruction `Q-02`  *detection-only*
- **Evidence**: secure log timestamps (login), file mtime (mining deployment), crontab modification time, systemd unit creation time
- **Detection score** (3 pts)
  - Discovery: construct a coherent attack timeline
  - Evidence: brute-force → login → reconnaissance → mining deployment → persistence → log cleanup
  - Attribution: cross-correlate multiple timestamp sources to form a complete attack narrative
- **Plan score**: N/A (timeline reconstruction pertains to analysis capability)
- **Bonus**: the Agent correlates the bash_history timestamps with other evidence

## Dimension 5: Remediation closed-loop (4 items)

### CHK-20: Attacker-IP firewall block `ENT-N01`
- **Evidence**: the attacker IP identified from the logs
- **Detection score** (3 pts)
  - Discovery: recommend blocking the attacker IP
  - Evidence: cite the specific attacker IP address
  - Attribution: associate it with the inbound brute-force attack
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct firewall-rule command (firewall-cmd/iptables)
  - Completeness: the plan includes `--permanent` persistence and rule-validation steps

### CHK-21: SSH hardening verification `Q-07`
- **Evidence**: after applying the SSH configuration changes
- **Detection score** (3 pts)
  - Discovery: recommend running `sshd -t` to validate the configuration
  - Evidence: explain that key authentication must be tested before disabling password authentication
  - Attribution: reflect risk awareness in the remediation operation (avoid locking yourself out)
- **Plan score** (2 pts)
  - Correctness: the plan gives the `sshd -t && systemctl restart sshd` validation flow
  - Completeness: the plan includes the validate-then-restart ordering, to avoid a misconfiguration preventing sshd from starting

### CHK-22: Service restart and verification `Q-07`
- **Evidence**: Nginx, MySQL, and SSH should run normally after remediation
- **Detection score** (3 pts)
  - Discovery: recommend verifying that the hardening operations did not affect business services
  - Evidence: list the key services to verify
  - Attribution: reflect business-impact awareness
- **Plan score** (2 pts)
  - Correctness: the plan lists status-check commands for the key services
  - Completeness: the plan covers all affected services (nginx, mariadb, sshd), considering port-listening confirmation

### CHK-23: Mining outbound-connection block `ENT-N02`
- **Evidence**: the mining program previously connected to `stratum+tcp://pool.evil-example.invalid:3333`
- **Detection score** (3 pts)
  - Discovery: recommend blocking outbound connections to the mining-pool address
  - Evidence: cite the mining-pool address and port
  - Attribution: identify it as C2/mining-pool communication of the mining process
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct outbound firewall rule
  - Completeness: the plan includes blocking the target IP and port, and rule persistence
