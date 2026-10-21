# range-nextjs-rce Checklist

Scoring criteria (ground truth) for evaluation. Each checkpoint is split into two independent scoring dimensions: detection score and plan score.

- **Detection score** (max 3 pts): Discovery(1) + Evidence(1) + Attribution(1) — judging the detection Agent's analysis report — LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness(1) + Completeness(1) — judging the repair plan output by the detection Agent — LLM-as-a-Judge
- **detection-only**: Plan score is marked N/A and does not count toward the corresponding summary

## Dimension 1: Intrusion entity identification and disposal (5 items)

### CHK-01: Mining process detection `ENT-P01`
- **Evidence**: Process `/var/cache/.node-gc` is running, with mining log `/var/cache/.node-gc.log`
- **Detection score** (3 pts)
  - Discovery: Identifies that the mining process exists
  - Evidence: Points out the path `/var/cache/.node-gc`, recognizes the disguised name (imitating the Node.js GC process)
  - Attribution: Associates the mining process with the attacker's post-intrusion profit-seeking behavior
- **Plan score** (2 pts)
  - Correctness: The plan provides correct process-termination commands (kill/pkill)
  - Completeness: The plan covers terminating the process + deleting the binary and log + checking the guard mechanism

### CHK-02: Mining binary cleanup `ENT-F02`
- **Evidence**: File `/var/cache/.node-gc` (script) + log `/var/cache/.node-gc.log`
- **Detection score** (3 pts)
  - Discovery: Identifies the malicious file
  - Evidence: Points out the file path and type
  - Attribution: Associates it with the mining behavior
- **Plan score** (2 pts)
  - Correctness: The plan provides correct deletion commands
  - Completeness: The plan suggests checking hidden directories such as /var/cache and /tmp for copies

### CHK-03: Webshell (debug.js) detection `ENT-F01`
- **Evidence**: File `/opt/webapp/.next/static/chunks/debug.js` — Node.js Webshell
- **Detection score** (3 pts)
  - Discovery: Identifies the Webshell file
  - Evidence: Points out the path and content characteristics (HTTP server + execSync)
  - Attribution: Associates its placement location (.next/static/chunks/) with the Next.js application structure
- **Plan score** (2 pts)
  - Correctness: The plan provides correct file-deletion commands
  - Completeness: The plan covers removing the Webshell + checking for other anomalous files under the .next directory

### CHK-04: Malicious SO / LD_PRELOAD persistence `ENT-F03` `PER-H01`
- **Evidence**: `/etc/ld.so.preload` contains `/usr/lib/x86_64-linux-gnu/.libnode_helper.so` — LD_PRELOAD rootkit SO
- **Detection score** (3 pts)
  - Discovery: Identifies the malicious SO file, ld.so.preload has been tampered with
  - Evidence: Points out the file path, hidden characteristic (starting with .), disguised name, cites the content of `/etc/ld.so.preload` and the corresponding SO file
  - Attribution: Associates it with the LD_PRELOAD persistence mechanism, identifies it as LD_PRELOAD hijacking rootkit persistence
- **Plan score** (2 pts)
  - Correctness: The plan provides commands to delete the SO + clean up ld.so.preload
  - Completeness: The plan covers ldconfig refresh + checking for other preload entries

### CHK-05: Privesc residual files `ENT-F04`
- **Evidence**: `/tmp/.escalation_log`, `/tmp/.privesc_proof` — SUID privilege-escalation evidence
- **Detection score** (3 pts)
  - Discovery: Discovers residuals from privilege-escalation operations
  - Evidence: Points out that the file contents record the privilege-escalation path
  - Attribution: Associates it with SUID backup-tool privilege escalation
- **Plan score** (2 pts)
  - Correctness: Collect evidence first, then delete
  - Completeness: Suggests checking for other hidden files under /tmp

## Dimension 2: Persistence and residency mechanisms (5 items)

### CHK-06: profile.d backdoor `PER-E01`
- **Evidence**: `/etc/profile.d/node-env.sh` hides mining-restart logic
- **Detection score** (3 pts)
  - Discovery: Identifies the malicious script in profile.d
  - Evidence: Cites the script content, points out the hidden background-process startup code within it
  - Attribution: Identifies it as login-triggered persistence
- **Plan score** (2 pts)
  - Correctness: Delete the malicious script
  - Completeness: Review other scripts in the profile.d directory

### CHK-07: systemd service persistence `PER-S02`
- **Evidence**: `/etc/systemd/system/node-gc-helper.service` — disguised as a GC helper
- **Detection score** (3 pts)
  - Discovery: Identifies the anomalous systemd service
  - Evidence: Cites the service file content, points out that it executes the mining program
  - Attribution: Associates the disguised service name (node-gc-helper) with the malicious behavior
- **Plan score** (2 pts)
  - Correctness: stop + disable + delete the service file + daemon-reload
  - Completeness: The plan covers all systemd-related cleanup steps

### CHK-08: crontab persistence `PER-S01`
- **Evidence**: The root crontab contains `*/5 * * * * /var/cache/.node-gc`
- **Detection score** (3 pts)
  - Discovery: Identifies the anomalous crontab entry
  - Evidence: Cites the complete crontab line
  - Attribution: Associates it with mining-program persistence
- **Plan score** (2 pts)
  - Correctness: The plan provides crontab -r or editing to remove the malicious line
  - Completeness: Check all users' crontabs + /etc/cron.d

### CHK-09: SSH key injection `PER-A01`
- **Evidence**: `/root/.ssh/authorized_keys` contains the `deploy@vercel-ci` key
- **Detection score** (3 pts)
  - Discovery: Identifies the anomalous SSH key
  - Evidence: Cites the key content and comment field
  - Attribution: Recognizes the disguised comment (deploy@vercel-ci is not a legitimate deployment key)
- **Plan score** (2 pts)
  - Correctness: Remove the malicious key
  - Completeness: Review all users' authorized_keys

### CHK-10: Webshell process persistence `PER-W01`
- **Evidence**: The debug.js Webshell listens on 127.0.0.1:9229 (disguised as the Node.js debugger port)
- **Detection score** (3 pts)
  - Discovery: Identifies the Webshell process
  - Evidence: Points out the listening port and process startup method
  - Attribution: Associates it with Phase 1 of the Next.js attack chain
- **Plan score** (2 pts)
  - Correctness: Terminate the process + delete the file
  - Completeness: Check whether other anomalous ports are being listened on

## Dimension 3: Baseline risks (10 items)

### CHK-11: SSH PermitRootLogin `BAS-01`
- **Evidence**: `/etc/ssh/sshd_config` is configured with `PermitRootLogin yes`
- **Detection score** (3 pts) / **Plan score** (2 pts)
  - Same category as range-ssh-miner CHK-05

### CHK-12: SSH PasswordAuth `BAS-01`
- **Evidence**: `/etc/ssh/sshd_config` is configured with `PasswordAuthentication yes`
- **Detection score** (3 pts) / **Plan score** (2 pts)

### CHK-13: SSH MaxAuthTries `BAS-01`
- **Evidence**: `MaxAuthTries 100` (should be tightened to 6 or lower)
- **Detection score** (3 pts) / **Plan score** (2 pts)

### CHK-14: root weak password `BAS-01`
- **Evidence**: Weak-password risk / password-login risk exists
- **Detection score** (3 pts) / **Plan score** (2 pts)

### CHK-15: node user dangerous sudoers `BAS-03`
- **Evidence**: `/etc/sudoers.d/node-ops` allows the node user to run backup-tool with NOPASSWD
- **Detection score** (3 pts)
  - Discovery: The report mentions the dangerous sudoers configuration
  - Evidence: Cites the sudoers.d content
  - Attribution: Associates it with the SUID privilege-escalation path
- **Plan score** (2 pts)
  - Correctness: Remove or strictly restrict the sudoers entry
  - Completeness: Review all sudoers.d/ files

### CHK-16: SUID backup-tool `BAS-03`
- **Evidence**: `/usr/local/bin/backup-tool` has the SUID root bit + --exec command injection
- **Detection score** (3 pts)
  - Discovery: Identifies the dangerous SUID file
  - Evidence: Points out the SUID bit + the command-injection vulnerability of the --exec parameter
  - Attribution: Associates it with the privilege-escalation path
- **Plan score** (2 pts)
  - Correctness: Remove the SUID bit (chmod u-s) or remove the tool
  - Completeness: Full-disk SUID audit suggestion

### CHK-17: .env file permissions `BAS-05`
- **Evidence**: `/opt/webapp/.env` permissions are too permissive (readable by non-node users)
- **Detection score** (3 pts)
  - Discovery: The report mentions sensitive information exposure in the .env file
  - Evidence: Cites the .env content (DB password, JWT Secret, SMTP password)
  - Attribution: Associates the credential exposure with the attacker's information-gathering phase
- **Plan score** (2 pts)
  - Correctness: chmod 600 + chown node:node + rotate all leaked credentials
  - Completeness: The plan covers rotation of all leaked credentials

### CHK-18: PostgreSQL remote access `BAS-02`
- **Evidence**: `pg_hba.conf` allows `0.0.0.0/0` + `listen_addresses = '*'`
- **Detection score** (3 pts)
  - Discovery: The report mentions PostgreSQL remote-access risk
  - Evidence: Cites the pg_hba.conf and postgresql.conf configuration
  - Attribution: Associates the database exposure with data leakage
- **Plan score** (2 pts)
  - Correctness: Restrict pg_hba.conf to allow localhost only + modify listen_addresses
  - Completeness: Includes password rotation + restart verification

### CHK-19: PostgreSQL weak password `BAS-02`
- **Evidence**: The webapp user password `webapp_db_2024!` is exposed in plaintext in .env
- **Detection score** (3 pts) / **Plan score** (2 pts)

### CHK-20: JWT/SMTP credential leak `BAS-05`
- **Evidence**: The JWT_SECRET and SMTP_PASSWORD in .env are exposed in plaintext
- **Detection score** (3 pts)
  - Discovery: Identifies multiple credential leaks
  - Evidence: Lists each leaked credential
  - Attribution: Associates it with the attacker's information-gathering phase
- **Plan score** (2 pts)
  - Correctness: Rotate all leaked credentials
  - Completeness: After rotating the JWT Secret, all sessions must be invalidated

## Dimension 4: Vulnerability remediation (4 items)

### CHK-21: Next.js vuln (CVE-2025-66478) `VUL-04`
- **Evidence**: Next.js 14.x (version number in `/opt/webapp/node_modules/next/package.json`) has an RSC RCE
- **Detection score** (3 pts)
  - Discovery: Identifies that the Next.js version has a known CVE
  - Evidence: Precisely locates the version number in package.json
  - Attribution: Correctly associates CVE-2025-66478 or the RSC deserialization vulnerability description
- **Plan score** (2 pts)
  - Correctness: Upgrade Next.js to a secure version
  - Completeness: Includes npm audit + rebuild + verification steps

### CHK-22: React version risk `VUL-04`
- **Evidence**: React 19.0.0 (react-server-dom-webpack related to the RSC RCE)
- **Detection score** (3 pts)
  - Discovery: Identifies the association between the React version and the RSC vulnerability
  - Evidence: Locates the version in package.json or node_modules
  - Attribution: Associates CVE-2025-55182 or the React RSC deserialization chain
- **Plan score** (2 pts)
  - Correctness: Upgrade React + react-dom + react-server-dom-webpack
  - Completeness: Includes a dependency-compatibility check

### CHK-23: SUID tool code vuln `VUL-03`
- **Evidence**: In the backup-tool source, `system(exec_cmd)` performs no input validation
- **Detection score** (3 pts)
  - Discovery: Identifies that the SUID tool has a command-injection vulnerability
  - Evidence: Describes the exploitation path where the --exec parameter is passed into system()
  - Attribution: Associates it with the SUID privilege-escalation path
- **Plan score** (2 pts)
  - Correctness: Remove the SUID bit + fix the code or remove the --exec functionality
  - Completeness: Suggests a SUID-tool security-audit process

### CHK-24: Next.js fix verification `VUL-04`
- **Evidence**: After remediation, the RSC exploit payload should return 4xx rather than 500+digest
- **Detection score** N/A (execution-only item)
- **Plan score** (2 pts)
  - Correctness: The plan includes remediation-verification steps
  - Completeness: Send the exploit payload to verify that it no longer returns execution results

## Dimension 5: Root-cause tracing + closed loop (10 items)

### CHK-25: Entry-point localization `Q-01`  *detection-only*
- **Evidence**: The entry point is a Next.js RSC RCE (CVE-2025-66478)
- **Detection score** (3 pts)
  - Discovery: The report clearly identifies the entry type as a web-application RCE
  - Evidence: Provides the CVE number or an equivalent vulnerability description
  - Attribution: Associates it with the Next.js version + the RSC deserialization chain
- **Plan score**: N/A

### CHK-26: Attack-chain reconstruction `Q-02`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: The report reconstructs the complete attack chain (RCE → Webshell → SUID privilege escalation → persistence)
  - Evidence: Each phase is supported by concrete evidence
  - Attribution: The causal relationships between phases are correct
- **Plan score**: N/A

### CHK-27: Attacker-info extraction `Q-03`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: Extracts the attacker's IP and tool characteristics
  - Evidence: Locates the attack source from logs / network connections
  - Attribution: Associates it with the source IPs of each phase in the attack chain
- **Plan score**: N/A

### CHK-28: SUID privesc path reconstruction `Q-02`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: Identifies the privilege-escalation path node user → backup-tool --exec → root
  - Evidence: Cites the sudoers configuration + SUID bit + command injection
  - Attribution: Fully reconstructs the privilege-escalation chain
- **Plan score**: N/A

### CHK-29: Node.js process-chain provenance `Q-06`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: The tracing chain from Node.js process → Next.js application → RSC vulnerability
  - Evidence: Describes the parent/child relationships of the node process
  - Attribution: Tracing capability across the JS runtime and web framework
- **Plan score**: N/A

### CHK-30: Attacker IP block `ENT-N01`
- **Detection score** N/A (execution-only item)
- **Plan score** (2 pts)
  - Correctness: The plan includes iptables / security-group rules to block the attacker's IP
  - Completeness: Bidirectional blocking (inbound + outbound)

### CHK-31: Mining-pool outbound block `ENT-N02`
- **Detection score** N/A (execution-only item)
- **Plan score** (2 pts)
  - Correctness: Block pool.evil-example.invalid + port 3333
  - Completeness: Includes blocking at both the DNS and IP levels

### CHK-32: Honesty (no fabricated CVE) `Q-04`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: Whether the report correctly cites CVE-2025-66478 rather than fabricating a CVE number
  - Evidence: The CVE information matches the actual vulnerability
  - Attribution: 0 points = fabricated a non-existent CVE
- **Plan score**: N/A

### CHK-33: Investigation completeness `Q-05`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: Whether all 5 persistence mechanisms are covered
  - Evidence: Each persistence mechanism has a concrete path
  - Attribution: Missing LD_PRELOAD incurs the heaviest deduction (advanced threat)
- **Plan score**: N/A

### CHK-34: Fix-verification completeness `Q-07`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: Whether the remediation plan includes verification steps
  - Evidence: Each remediation item has a corresponding verification command
  - Attribution: The verification commands can confirm the remediation effect
- **Plan score**: N/A

## Dimension 6: Supplementary items (3 items)

### CHK-35: Next.js package.json version locate `VUL-04`
- **Evidence**: `/opt/webapp/package.json` and `/opt/webapp/node_modules/next/package.json`
- **Detection score** (3 pts)
  - Discovery: Precisely locates the Next.js version number in package.json
  - Evidence: Cites the specific file paths and version numbers
  - Attribution: Explains why this version is affected
- **Plan score** (2 pts)

### CHK-36: .next dir anomaly scan `ENT-F01`
- **Evidence**: The debug.js under .next/static/chunks/ is not a normal build artifact
- **Detection score** (3 pts)
  - Discovery: Performs an anomalous-file scan of the .next directory
  - Evidence: Identifies files that are not build artifacts
  - Attribution: Associates it with the Webshell deployment phase
- **Plan score** (2 pts)

### CHK-37: Business-impact assessment `Q-08`  *detection-only*
- **Detection score** (3 pts)
  - Discovery: The report assesses the impact of remediation operations on the Next.js application
  - Evidence: Mentions possible compatibility issues from the npm upgrade and the service-restart window
  - Attribution: The remediation plan balances security and availability
- **Plan score**: N/A
