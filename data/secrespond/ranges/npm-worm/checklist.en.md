# range-npm-worm Checklist

Scoring criteria (ground truth) for evaluation. Each checkpoint is split into two independent scoring dimensions: detection score and plan score.

- **Detection score** (max 3 pts): Discovery(1) + Evidence(1) + Attribution(1) — judging the detection Agent's analysis report — LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness(1) + Completeness(1) — judging the repair plan output by the detection Agent — LLM-as-a-Judge
- **detection-only**: plan score marked N/A, not counted in the corresponding summary

## Dimension 1: Intrusion entity identification and handling (9 items)

### CHK-01: Worm process detection `ENT-P01`
- **Evidence**: `python3 /tmp/.ld.py` process is running
- **Detection score** (3 pts)
  - Discovery: Identified a suspicious Python process
  - Evidence: Pointed out the path `/tmp/.ld.py`, identified it as a malicious worm script (not a system component)
  - Attribution: Associated the worm process with automated attack behavior following supply-chain poisoning
- **Plan score** (2 pts)
  - Correctness: Plan provides kill/pkill command to terminate the process
  - Completeness: Plan covers terminating the process + checking auto-restart mechanisms (crontab, bashrc)

### CHK-02: Worm script file cleanup `ENT-F02`
- **Evidence**: `/tmp/.ld.py` file exists, timestamp is forged (mtime matches /usr/bin/python3)
- **Detection score** (3 pts)
  - Discovery: Identified a hidden Python worm script
  - Evidence: Pointed out the file path and content characteristics (network scanning, credential-theft logic)
  - Attribution: Associated it with the npm postinstall attack chain
- **Plan score** (2 pts)
  - Correctness: Plan provides `rm -f /tmp/.ld.py`
  - Completeness: Recommends searching /tmp, /var/tmp and other directories to confirm no copies exist

### CHK-03: JS dropper identification `ENT-F01`  *detection-only*
- **Evidence**: `/opt/webapp/node_modules/@corp-utils/logger/scripts/setup.js` contains `curl` download and `python3` execution logic
- **Detection score** (3 pts)
  - Discovery: Identified a malicious dropper script in an npm package
  - Evidence: Pointed out the C2 address, download command, and execution chain in setup.js
  - Attribution: Identified it as the initial payload dropper for supply-chain poisoning (JS → curl → Python cross-language chain)
- **Plan score**: N/A (actual handling is covered by CHK-04 full malicious-package removal)

### CHK-04: Malicious npm package removal `ENT-F01`
- **Evidence**: `/opt/webapp/node_modules/@corp-utils/logger/` directory exists, package.json has a postinstall hook
- **Detection score** (3 pts)
  - Discovery: Identified the malicious npm package `@corp-utils/logger`
  - Evidence: Pointed out the postinstall hook and the abnormal dependency in package.json
  - Attribution: Characterized it as a supply-chain poisoning vector
- **Plan score** (2 pts)
  - Correctness: Plan provides `npm uninstall @corp-utils/logger` or manual deletion
  - Completeness: Recommends checking package-lock.json to trace the package source URL, and removing the dependency from package.json

### CHK-05: Mining process detection `ENT-P01`
- **Evidence**: `/opt/.node-helpers/.npm-gc` process is running, log file contains a mining-pool address
- **Detection score** (3 pts)
  - Discovery: Identified a mining process
  - Evidence: Pointed out the path, disguised name (mimicking npm cache cleanup), mining-pool address visible in the log
  - Attribution: Associated the mining with the attacker's subsequent exploitation
- **Plan score** (2 pts)
  - Correctness: Plan provides a command to terminate the process
  - Completeness: Covers termination + file deletion + checking systemd auto-restart

### CHK-06: Mining binary cleanup `ENT-F02`
- **Evidence**: `/opt/.node-helpers/.npm-gc` script and `/opt/.node-helpers/.npm-gc.log` log
- **Detection score** (3 pts)
  - Discovery: Identified a hidden mining script
  - Evidence: Pointed out the hidden directory path `/opt/.node-helpers/`
  - Attribution: Associated it with mining-pool outbound behavior
- **Plan score** (2 pts)
  - Correctness: Plan provides `rm -rf /opt/.node-helpers`
  - Completeness: Recommends searching for other hidden directories

### CHK-07: Credential cache cleanup `ENT-F04`
- **Evidence**: Stolen npmrc, SSH keys, .env, Git credentials, etc. stored under `/var/tmp/.npm-cache/`
- **Detection score** (3 pts)
  - Discovery: Discovered the attacker's data staging directory
  - Evidence: Listed the contents of each subdirectory (npmrc/, ssh_keys/, env_files/, git_credentials/, bash_history/)
  - Attribution: Identified it as a product of the worm's credential-theft behavior
- **Plan score** (2 pts)
  - Correctness: Plan provides `rm -rf /var/tmp/.npm-cache`
  - Completeness: Recommends assessing the rotation needs for the leaked credentials

### CHK-08: Worm propagation artifacts `ENT-F04`
- **Evidence**: The scripts.postinstall of `/opt/internal-tools/package.json` was injected with a worm download command
- **Detection score** (3 pts)
  - Discovery: Discovered that another npm project was infected by the worm
  - Evidence: Pointed out the modified package.json and the injected postinstall content
  - Attribution: Identified it as the worm's self-propagation behavior
- **Plan score** (2 pts)
  - Correctness: Plan provides a method to restore package.json
  - Completeness: Recommends scanning all local npm projects for similar infections

### CHK-09: C2 communication residue `ENT-F04`  *detection-only*
- **Evidence**: `/var/tmp/.npm-cache/sysinfo.json` contains system-information callback records; the C2 address is visible in the worm code
- **Detection score** (3 pts)
  - Discovery: Identified the worm's C2 callback behavior
  - Evidence: Pointed out the C2 address (attacker machine IP:8888) and the /beacon path
  - Attribution: Associated the C2 communication with the worm's automated callback behavior
- **Plan score**: N/A (outbound blocking is covered by CHK-38)

## Dimension 2: Baseline risk (9 items)

### CHK-10: SSH PermitRootLogin `BAS-01`
- **Evidence**: `PermitRootLogin yes` in `/etc/ssh/sshd_config`
- **Detection score** (3 pts)
  - Discovery: Reported the risk of PermitRootLogin yes
  - Evidence: Cited the specific configuration line
  - Attribution: Pointed out that the attacker uses weak-password SSH login as root for subsequent persistence deployment
- **Plan score** (2 pts)
  - Correctness: Recommends changing to `no` or `prohibit-password`
  - Completeness: Includes `sshd -t` verification and sshd restart steps

### CHK-11: SSH PasswordAuthentication `BAS-01`
- **Evidence**: `PasswordAuthentication yes` in `/etc/ssh/sshd_config`
- **Detection score** (3 pts)
  - Discovery: Identified the risk of password authentication being enabled
  - Evidence: Cited the specific configuration line
  - Attribution: Associated it with the worm's SSH brute-force scanning behavior
- **Plan score** (2 pts)
  - Correctness: Recommends setting `PasswordAuthentication no`
  - Completeness: Emphasizes first confirming that key authentication is available

### CHK-12: Root password strength `BAS-01`
- **Evidence**: root password is `npm@2024` (weak password)
- **Detection score** (3 pts)
  - Discovery: Identified that root uses a weak password
  - Evidence: Pointed out that the password is vulnerable to dictionary attacks
  - Attribution: Associated the weak password with the attacker's Phase 3 SSH login
- **Plan score** (2 pts)
  - Correctness: Recommends setting a strong password
  - Completeness: Provides password-complexity requirements

### CHK-13: Webhook endpoint no auth `BAS-06`
- **Evidence**: `/api/webhook/deploy` accepts arbitrary POST with no authentication, and the `packages` parameter is passed directly to `npm install`
- **Detection score** (3 pts)
  - Discovery: Identified that the Webhook endpoint lacks authentication
  - Evidence: Cited the routing logic in server.js, pointed out the command-injection risk
  - Attribution: Characterized the unauthenticated Webhook as the entry point for supply-chain poisoning
- **Plan score** (2 pts)
  - Correctness: Recommends adding a token/signature authentication mechanism
  - Completeness: Recommends whitelist validation of the packages parameter, prohibiting arbitrary URLs

### CHK-14: npm token plaintext exposure `BAS-03`
- **Evidence**: `/home/developer/.npmrc` contains a plaintext `_authToken`
- **Detection score** (3 pts)
  - Discovery: Discovered a plaintext npm registry token
  - Evidence: Cited the file path and token content
  - Attribution: The worm has already stolen this token to /var/tmp/.npm-cache/npmrc/
- **Plan score** (2 pts)
  - Correctness: Recommends rotating the npm token
  - Completeness: Recommends using `npm token revoke` to invalidate the old token + least-privilege

### CHK-15: SSH private key unencrypted `BAS-03`
- **Evidence**: `/home/developer/.ssh/id_rsa` has no passphrase protection
- **Detection score** (3 pts)
  - Discovery: Discovered an unencrypted SSH private key
  - Evidence: Pointed out the file path and the fact that it has no password protection
  - Attribution: The worm has already stolen this key to /var/tmp/.npm-cache/ssh_keys/
- **Plan score** (2 pts)
  - Correctness: Recommends regenerating a key pair with a passphrase
  - Completeness: Recommends rotating the associated authorized_keys

### CHK-16: .env file permissions too loose `BAS-05`
- **Evidence**: `/opt/webapp/.env` has permissions 644 (readable by any user), contains DB password, API Key, JWT Secret
- **Detection score** (3 pts)
  - Discovery: Identified the .env file permission problem
  - Evidence: Pointed out the permission value and the list of sensitive credentials in the file
  - Attribution: The worm exploited the loose permissions to steal the .env content
- **Plan score** (2 pts)
  - Correctness: Recommends `chmod 600 .env` and restricting readability to only the running user
  - Completeness: Recommends rotating all credentials in .env

### CHK-17: Git credentials plaintext storage `BAS-03`
- **Evidence**: `/home/developer/.git-credentials` contains plaintext GitHub/GitLab credentials
- **Detection score** (3 pts)
  - Discovery: Discovered a plaintext Git credentials file
  - Evidence: Cited the file path and credential content
  - Attribution: The worm has already stolen this file
- **Plan score** (2 pts)
  - Correctness: Recommends using a credential manager instead of plaintext storage
  - Completeness: Recommends rotating all Git Personal Access Tokens

### CHK-18: developer user sudo privilege `BAS-04`
- **Evidence**: `/etc/sudoers.d/developer` grants `ALL=(ALL:ALL) ALL`
- **Detection score** (3 pts)
  - Discovery: Identified overly broad sudo privileges
  - Evidence: Cited the sudoers configuration content
  - Attribution: The worm/attacker can use this to escalate to root
- **Plan score** (2 pts)
  - Correctness: Recommends restricting to specific commands (e.g. only allowing pm2, nginx operations)
  - Completeness: Includes `visudo -c` verification

## Dimension 3: Persistence removal (8 items)

### CHK-19: Crontab persistence `PER-S01`
- **Evidence**: `crontab -l` shows `*/10 * * * * python3 /tmp/.ld.py --c2 <IP>:<PORT> >/dev/null 2>&1`
- **Detection score** (3 pts)
  - Discovery: Identified a suspicious crontab entry
  - Evidence: Cited the specific content, pointed out the 10-minute interval and the worm C2 parameter
  - Attribution: Associated the crontab with the worm's auto-restart persistence
- **Plan score** (2 pts)
  - Correctness: Provides a method to delete the malicious entry
  - Completeness: Recommends checking all users' crontabs and /etc/cron.d/

### CHK-20: Bashrc persistence `PER-I01`
- **Evidence**: A code block starting with `# npm cache optimization` in `/home/developer/.bashrc`, which checks and restarts the worm on each login
- **Detection score** (3 pts)
  - Discovery: Identified the malicious code block appended in bashrc
  - Evidence: Cited the comment disguise and the specific malicious content
  - Attribution: Identified it as the worm's login-triggered persistence mechanism
- **Plan score** (2 pts)
  - Correctness: Precisely locates and deletes the malicious code block
  - Completeness: Recommends checking .bash_profile, .profile, /root/.bashrc

### CHK-21: Systemd service persistence `PER-V01`
- **Evidence**: `/etc/systemd/system/npm-cache-gc.service` — ExecStart points to `/opt/.node-helpers/.npm-gc`
- **Detection score** (3 pts)
  - Discovery: Identified a suspicious systemd service
  - Evidence: Pointed out the unit file path and that ExecStart points to the mining script
  - Attribution: Identified it as a mining persistence mechanism
- **Plan score** (2 pts)
  - Correctness: Provides `systemctl stop && disable` + deleting the unit file + `daemon-reload`
  - Completeness: Includes post-cleanup verification steps

### CHK-22: Systemd service masquerade `PER-V01`  *detection-only*
- **Evidence**: The service name `npm-cache-gc` and description `NPM Cache Garbage Collector` mimic legitimate npm cache management
- **Detection score** (3 pts)
  - Discovery: Pointed out the disguise technique in the service name and description
  - Evidence: Compared against legitimate npm/node service naming patterns
  - Attribution: Identified it as the attacker evading scrutiny through naming disguise
- **Plan score**: N/A (actual handling is covered by CHK-21)

### CHK-23: SSH key injection `PER-A01`
- **Evidence**: `/root/.ssh/authorized_keys` and `/home/developer/.ssh/authorized_keys` contain an attacker public key commented as `ops@npm-registry`
- **Detection score** (3 pts)
  - Discovery: Identified an abnormal SSH public key
  - Evidence: Pointed out that the key comment `ops@npm-registry` is not a local user
  - Attribution: Associated the key injection with the worm's automated persistence behavior
- **Plan score** (2 pts)
  - Correctness: Plan provides a command to delete the specific key line
  - Completeness: Recommends auditing all users' authorized_keys

### CHK-24: Profile.d backdoor `PER-E01`
- **Evidence**: `/etc/profile.d/node-env.sh` hides mining-restart logic (`pgrep -f npm-gc || nohup ...`)
- **Detection score** (3 pts)
  - Discovery: Identified the malicious script in profile.d
  - Evidence: Pointed out that the script is disguised as a Node.js environment configuration but actually contains a backdoor
  - Attribution: Identified it as a persistence method that automatically restarts mining on each user login
- **Plan score** (2 pts)
  - Correctness: Plan provides `rm /etc/profile.d/node-env.sh`
  - Completeness: Recommends scanning all non-distribution scripts in /etc/profile.d/

### CHK-25: npm project infection persistence `PER-S01`  *detection-only*
- **Evidence**: The postinstall of `/opt/internal-tools/package.json` was injected with a worm download command
- **Detection score** (3 pts)
  - Discovery: Identified that the worm propagates by modifying npm projects
  - Evidence: Pointed out the modified package.json and the injected content
  - Attribution: Identified it as the worm's self-propagation mechanism (distinct from conventional persistence; this is supply-chain-specific behavior)
- **Plan score**: N/A (actual handling is covered by CHK-08)
- **Bonus**: The Agent scans all local npm projects instead of only checking known paths

### CHK-26: Comprehensive persistence scan `Q-05`  *detection-only*
- **Evidence**: No persistence other than crontab/bashrc/systemd/authorized_keys/profile.d/npm postinstall
- **Detection score** (3 pts)
  - Discovery: Performs a systematic persistence scan (init.d, rc.local, at jobs, motd, etc.)
  - Evidence: Documents the scan scope and method
  - Attribution: Even if no additional items are found, demonstrates the thoroughness of the investigation
- **Plan score**: N/A

## Dimension 4: Evaluation quality dimension (9 items)

### CHK-27: Cross-language attack-chain tracing `Q-06`  *detection-only*
- **Evidence**: The complete attack chain is npm install → node setup.js → curl → python3 ld.py, spanning both the JavaScript and Python runtimes
- **Detection score** (3 pts)
  - Discovery: Identified the cross-language multi-stage attack chain
  - Evidence: Accurately described the complete path of npm postinstall → JS dropper → curl download → Python worm
  - Attribution: Correctly linked the stages together, explaining that the cross-language boundary does not affect tracing
- **Plan score**: N/A
- **Critical**: The process chain may break at the node → curl → python3 boundary; the Agent needs to proactively associate them

### CHK-28: Malicious package attribution `Q-01`  *detection-only*
- **Evidence**: The `resolved` field of `@corp-utils/logger` in `/opt/webapp/package-lock.json` points to an attacker-machine HTTP URL
- **Detection score** (3 pts)
  - Discovery: Located the malicious package source from package-lock.json
  - Evidence: Cited the resolved URL, version number, integrity hash
  - Attribution: Associated the package source URL with the attacker-machine IP
- **Plan score**: N/A
- **Bonus**: The Agent compares package.json and package-lock.json to discover the manually injected dependency

### CHK-29: Entry-point determination `Q-01` `Q-04`  *detection-only*
- **Evidence**: Webhook access log + npm install log + no SSH brute-force records (the worm's scanning occurs after the attack)
- **Detection score** (3 pts)
  - Discovery: Correctly determined the entry point as "CI/CD Webhook exploited + npm supply-chain poisoning"
  - Evidence: Cited the POST /api/webhook/deploy records in Nginx access.log and the npm install records in deploy.log
  - Attribution: Ruled out the SSH weak password as the initial entry point (the SSH login occurred in Phase 3, later than the Webhook call)
- **Plan score**: N/A
- **Critical**: The Agent should not misjudge the entry point as the SSH weak password — although the SSH configuration does have weaknesses, the causal relationship of the attack chain is Webhook first, then SSH

### CHK-30: Attacker-IP identification `Q-03`  *detection-only*
- **Evidence**: The source IP of POST /api/webhook/deploy in Nginx access.log; the SSH login source IP in auth.log; the hardcoded C2 address in the worm code
- **Detection score** (3 pts)
  - Discovery: Identified the attacker source IP
  - Evidence: Cited at least two independent sources (Webhook log + SSH log or worm code)
  - Attribution: Confirmed that the same IP runs through the Webhook call, SSH login, and C2 callback
- **Plan score**: N/A (blocking plan is covered by CHK-39)

### CHK-31: Network-scanning behavior `Q-02`  *detection-only*
- **Evidence**: `/var/tmp/.npm-cache/scan_results.txt` contains scan results; auth.log may contain SSH attempt records initiated by the worm
- **Detection score** (3 pts)
  - Discovery: Identified internal SSH port-scanning behavior
  - Evidence: Cited the scan results file and/or the abnormal SSH attempts in auth.log
  - Attribution: Associated the network scanning with the worm's lateral-propagation capability
- **Plan score**: N/A
- **Bonus**: Assesses the network-segment range covered by the scan and the potential propagation risk

### CHK-32: Credential-leak scope assessment `Q-08`  *detection-only*
- **Evidence**: The worm stole 5 categories of credentials: npm token, SSH private key, .env secrets, Git credentials, commands in bash_history
- **Detection score** (3 pts)
  - Discovery: Comprehensively assessed the credential-leak scope
  - Evidence: Listed each category of stolen credentials and its business impact
  - Attribution: Pointed out the secondary attack surface that credential leakage can cause (e.g. an npm token can publish malicious packages, an SSH key can log in to other servers)
- **Plan score**: N/A
- **Critical**: The Agent should assess the leak consequences of each of the 5 credential categories, rather than vaguely saying "credential leak"

### CHK-33: Attack-timeline reconstruction `Q-02`  *detection-only*
- **Evidence**: Nginx access.log (Webhook call), deploy.log (npm install), file ctime (worm creation), auth.log (SSH login), systemd unit creation time
- **Detection score** (3 pts)
  - Discovery: Constructed a coherent attack timeline
  - Evidence: Webhook call → npm install → worm startup → credential theft → SSH login → mining deployment → persistence
  - Attribution: Cross-correlated multiple timestamp sources to form a complete attack narrative
- **Plan score**: N/A
- **Bonus**: The Agent notices partial log cleanup (the corp-utils-logger line deleted from deploy.log, auth.log partially truncated)

### CHK-34: Worm C2 communication pattern `Q-03`  *detection-only*
- **Evidence**: The `/beacon` HTTP callback path + `/report` initial-infection report path in the worm code
- **Detection score** (3 pts)
  - Discovery: Extracted the C2 communication protocol from the worm code
  - Evidence: Pointed out the HTTP callback URL, data format (JSON), transmitted content (system information + list of stolen credential directories)
  - Attribution: Distinguished that the C2 callback and the mining-pool outbound connection are two different malicious outbound communications
- **Plan score**: N/A

## Dimension 5: Remediation closed loop (5 items)

### CHK-35: Malicious-package removal + npm audit `VUL-01`
- **Evidence**: Run npm audit after removing the malicious package
- **Detection score** (3 pts)
  - Discovery: Recommends running `npm audit` to check for other known vulnerabilities
  - Evidence: Explains the scope and limitations of npm audit
  - Attribution: Reflects continuous-monitoring awareness of supply-chain security
- **Plan score** (2 pts)
  - Correctness: Provides `npm uninstall @corp-utils/logger && npm audit`
  - Completeness: Recommends configuring `npm install --ignore-scripts` or using `.npmrc`'s `ignore-scripts=true`

### CHK-36: Full credential rotation `BAS-03`
- **Evidence**: All 5 categories of credentials have been stolen
- **Detection score** (3 pts)
  - Discovery: Recommends rotating all leaked credentials
  - Evidence: Lists the specific credentials that need rotation (npm token, SSH key, DB/API/JWT/SMTP passwords in .env, Git token)
  - Attribution: Not rotating credentials after a leak means the attacker still holds valid access
- **Plan score** (2 pts)
  - Correctness: Provides the specific rotation method for each category of credentials
  - Completeness: Covers all 5 categories, explaining the rotation order and verification method

### CHK-37: C2 + mining-pool outbound blocking `ENT-N02`
- **Evidence**: The worm calls back to C2 (attacker machine IP:8888) + mining connects to the pool (pool.evil-example.invalid:4444)
- **Detection score** (3 pts)
  - Discovery: Recommends blocking both categories of malicious outbound connections
  - Evidence: Cited the C2 address and the mining-pool address
  - Attribution: Distinguished that the worm C2 and the mining pool are two independent malicious outbound targets
- **Plan score** (2 pts)
  - Correctness: Provides iptables/ufw outbound rules
  - Completeness: Includes rule persistence

### CHK-38: Attacker-IP inbound blocking `ENT-N01`
- **Evidence**: The attacker IP identified from Nginx logs and auth.log
- **Detection score** (3 pts)
  - Discovery: Recommends blocking the attacker inbound IP
  - Evidence: Cited the attacker IP and multiple log sources
  - Attribution: Associated it with the Webhook call and SSH login
- **Plan score** (2 pts)
  - Correctness: Provides a firewall inbound-reject rule
  - Completeness: Includes security-group/firewall rule persistence

### CHK-39: Service restart and verification `Q-07`
- **Evidence**: Nginx, Express webapp, and SSH should run normally after remediation
- **Detection score** (3 pts)
  - Discovery: Recommends verifying that the remediation operations did not affect business services
  - Evidence: Lists the key services that need verification
  - Attribution: Reflects business-impact awareness
- **Plan score** (2 pts)
  - Correctness: Lists status-check commands for the key services
  - Completeness: Covers nginx, webapp (PM2), sshd