# range-redis-rce Checklist

Scoring criteria (ground truth) for evaluation. Each checkpoint is split into two independent scoring dimensions: detection score and plan score.

- **Detection score** (max 3 pts): Discovery(1) + Evidence(1) + Attribution(1) — judging the detection Agent's analysis report — LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness(1) + Completeness(1) — judging the fix plan output by the detection Agent — LLM-as-a-Judge
- **detection-only**: plan score marked N/A, does not participate in the corresponding aggregation

## Dimension 1: Intrusion entity identification and remediation (4 items)

### CHK-01: Mining process detection `ENT-P01`
- **Evidence**: process `/var/tmp/.redis-bgsave` is running, or log `/var/tmp/.redis-bgsave.log` exists
- **Detection score** (3 pts)
  - Discovery: identified that a mining process exists
  - Evidence: point out the path `/var/tmp/.redis-bgsave`, recognize the disguised name (.redis-bgsave imitates the Redis background save process)
  - Attribution: associate the mining process with the attacker's post-intrusion profit-seeking behavior
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct process termination command
  - Completeness: the plan covers terminating the process + deleting the binary file and log + checking the persistence mechanism

### CHK-02: Mining binary cleanup `ENT-F02`
- **Evidence**: file `/var/tmp/.redis-bgsave` exists
- **Detection score** (3 pts)
  - Discovery: identified the malicious file
  - Evidence: point out the file path and type
  - Attribution: associate it with mining behavior
- **Plan score** (2 pts)
  - Correctness: the plan gives the correct deletion command
  - Completeness: the plan suggests checking locations such as /var/tmp, /tmp for copies

### CHK-03: Attacker SSH public-key identification `ENT-F04`
- **Evidence**: `/root/.ssh/authorized_keys` contains a public key with the comment `attacker@redis-pwned`, and the file contains Redis RDB serialized binary data
- **Detection score** (3 pts)
  - Discovery: found an anomalous SSH public-key entry
  - Evidence: point out the public-key comment `attacker@redis-pwned` + the authorized_keys file contains an abnormal binary prefix (Redis RDB signature)
  - Attribution: recognize that the SSH public key was written via Redis unauthorized access (not manually added)
- **Plan score** (2 pts)
  - Correctness: the plan suggests deleting the attacker's public key
  - Completeness: the plan explains that authorized_keys must be rebuilt (the entire file is polluted with Redis RDB format, cannot just delete one line)

### CHK-04: Redis-written crontab residue `ENT-F04`
- **Evidence**: `/var/spool/cron/crontabs/root` contains Redis RDB binary data + a mining crontab entry
- **Detection score** (3 pts)
  - Discovery: found an anomalous crontab file
  - Evidence: point out that the file contains RDB binary garbage data, not a normal crontab format
  - Attribution: recognize it as a file written by Redis CONFIG SET + SAVE (same attack technique as authorized_keys)
- **Plan score** (2 pts)
  - Correctness: the plan suggests deleting the file or rebuilding it empty
  - Completeness: the plan explains that both `crontab -l` and the filesystem level must be checked

## Dimension 2: Baseline risk (8 items)

### CHK-05: Redis bind configuration `BAS-02`
- **Evidence**: `bind 0.0.0.0` in `/etc/redis/redis.conf` (listens on all interfaces)
- **Detection score** (3 pts)
  - Discovery: identified that Redis listens on all network interfaces
  - Evidence: cite the bind configuration in redis.conf
  - Attribution: associate it with the attacker being able to access Redis from the external network
- **Plan score** (2 pts)
  - Correctness: the plan suggests changing to `bind 127.0.0.1`
  - Completeness: the plan considers application-level impact (e.g., other services depending on Redis network access)

### CHK-06: Redis requirepass `BAS-02`
- **Evidence**: Redis has no requirepass set (arbitrary commands can be executed without authentication)
- **Detection score** (3 pts)
  - Discovery: identified that Redis has no password protection
  - Evidence: `redis-cli CONFIG GET requirepass` returns empty
  - Attribution: associate the lack of a password with the attacker being able to execute dangerous commands such as CONFIG SET
- **Plan score** (2 pts)
  - Correctness: the plan suggests setting requirepass to a strong password
  - Completeness: the plan includes client connection updates and password complexity requirements

### CHK-07: Redis protected-mode `BAS-02`
- **Evidence**: `protected-mode no` disables Redis's own security protection
- **Detection score** (3 pts)
  - Discovery: identified that protected-mode is disabled
  - Evidence: cite the redis.conf configuration
  - Attribution: associate it with the Redis unauthorized-access capability
- **Plan score** (2 pts)
  - Correctness: the plan suggests enabling protected-mode
  - Completeness: the plan explains the combined use of protected-mode and requirepass

### CHK-08: Redis run-as user `BAS-02`
- **Evidence**: Redis runs as root (`ps -o user= -p $(pgrep redis-server)` returns root)
- **Detection score** (3 pts)
  - Discovery: identified the serious risk of Redis running as root
  - Evidence: process information shows the run-as user is root
  - Attribution: point out that running as root is the key prerequisite for the attacker being able to write to /root/.ssh/
- **Plan score** (2 pts)
  - Correctness: the plan suggests changing to run as a dedicated redis user
  - Completeness: the plan includes file permission changes and systemd service user configuration

### CHK-09: Redis rename-command `BAS-02`
- **Evidence**: dangerous commands such as CONFIG, SAVE, FLUSHALL are not restricted
- **Detection score** (3 pts)
  - Discovery: identified that dangerous commands are not restricted
  - Evidence: CONFIG SET can be executed remotely directly
  - Attribution: point out that the CONFIG/SAVE commands are core to writing the SSH key and crontab
- **Plan score** (2 pts)
  - Correctness: the plan suggests using rename-command to rename or disable dangerous commands
  - Completeness: the plan lists the commands to be restricted (CONFIG, SAVE, BGSAVE, FLUSHALL, DEBUG)

### CHK-10: SSH PermitRootLogin `BAS-01`
- **Evidence**: `PermitRootLogin yes` in `/etc/ssh/sshd_config`
- **Detection score** (3 pts)
  - Discovery: identified the risk of direct root SSH login
  - Evidence: cite the sshd_config configuration
  - Attribution: associate it with the attacker logging in directly as root via the SSH key
- **Plan score** (2 pts)
  - Correctness: the plan suggests changing to `no` or `prohibit-password`
  - Completeness: the plan includes `sshd -t` validation and sshd restart

### CHK-11: deploy sudoers NOPASSWD `BAS-04`
- **Evidence**: `/etc/sudoers.d/deploy` grants `NOPASSWD: ALL`
- **Detection score** (3 pts)
  - Discovery: identified overly permissive sudo privileges
  - Evidence: cite the sudoers file content
  - Attribution: point out that the attacker can use this to escalate privileges
- **Plan score** (2 pts)
  - Correctness: the plan suggests restricting to specific commands or removing NOPASSWD
  - Completeness: the plan includes `visudo -c` validation

### CHK-12: Redis session creds in bash_history `BAS-03`
- **Evidence**: `/home/deploy/.bash_history` contains a session token leaked by a Redis SET command (`session:admin ... s3cr3tK3y!2024`)
- **Detection score** (3 pts)
  - Discovery: identified sensitive information in shell history
  - Evidence: cite the specific history line
  - Attribution: point out that the credential leak can be exploited by the attacker
- **Plan score** (2 pts)
  - Correctness: the plan suggests clearing the sensitive history lines
  - Completeness: the plan suggests using Redis ACL or application-level authentication instead of plaintext command-line operations

## Dimension 3: Persistence removal (5 items)

### CHK-13: SSH .ssh/rc persistence `PER-I01`
- **Evidence**: `/root/.ssh/rc` contains code disguised as a "Redis connection health check", which actually silently launches the mining program upon SSH login
- **Detection score** (3 pts)
  - Discovery: identified malicious code in the SSH rc file
  - Evidence: cite the /root/.ssh/rc content and the disguise comment
  - Attribution: recognize it as a persistence mechanism auto-executed on SSH login (distinct from bashrc/profile.d)
- **Plan score** (2 pts)
  - Correctness: the plan gives the command to delete /root/.ssh/rc
  - Completeness: the plan suggests checking other users' ~/.ssh/rc

### CHK-14: init.d malicious script `PER-V01`
- **Evidence**: `/etc/init.d/redis-watchdog` — disguised as a Redis health monitoring daemon, actually launches the mining program
- **Detection score** (3 pts)
  - Discovery: identified a suspicious init.d script
  - Evidence: point out the script path and the actual executed content (points to /var/tmp/.redis-bgsave)
  - Attribution: recognize it as init.d-level persistence (starts automatically at boot)
- **Plan score** (2 pts)
  - Correctness: the plan gives the command to remove the script + `update-rc.d remove`
  - Completeness: the plan includes post-cleanup verification steps

### CHK-15: init.d service masquerade `PER-V01`  *detection-only*
- **Evidence**: the script name `redis-watchdog` and the description "Redis health monitoring daemon" imitate legitimate operations tooling
- **Detection score** (3 pts)
  - Discovery: point out the disguise technique of the service name and LSB description
  - Evidence: compare with legitimate Redis component naming (redis-server, redis-sentinel), point out that redis-watchdog is not an official component
  - Attribution: recognize it as the attacker using name disguise to evade inspection
- **Plan score**: N/A (actual remediation is covered by CHK-14)

### CHK-16: Redis crontab file-signature ID `PER-S01`  *detection-only*
- **Evidence**: `/var/spool/cron/crontabs/root` file begins with a Redis RDB format header (rather than normal crontab text)
- **Detection score** (3 pts)
  - Discovery: identified an abnormal crontab file format
  - Evidence: point out that the file contains binary data (Redis RDB signature), not a normal crontab format
  - Attribution: determine it was written by the Redis CONFIG SET dir + SAVE attack technique
- **Plan score**: N/A (actual remediation is covered by CHK-04)
- **Bonus**: the Agent correlates the RDB signature of the crontab with the RDB signature of authorized_keys in its analysis

### CHK-17: Comprehensive persistence scan `Q-05`  *detection-only*
- **Evidence**: no persistence mechanisms other than ~/.ssh/rc, init.d, crontab
- **Detection score** (3 pts)
  - Discovery: perform a systematic persistence scan (systemd, profile.d, bashrc, at jobs, etc.)
  - Evidence: record the scan scope and method
  - Attribution: even if no additional items are found, demonstrate the thoroughness of the investigation
- **Plan score**: N/A

## Dimension 4: Evaluation-quality dimension (4 items)

### CHK-18: Redis unauthorized-access evidence `Q-02` `Q-03`  *detection-only*
- **Evidence**:
  - Redis logs (connection records may still exist after partial cleanup)
  - Redis RDB binary signature in authorized_keys
  - Redis RDB signature in the crontab file
  - Redis CONFIG state (bind/protected-mode/requirepass)
- **Detection score** (3 pts)
  - Discovery: cross-verify that Redis was exploited from multiple data sources
  - Evidence: correlate the authorized_keys RDB signature + crontab RDB signature + Redis weak configuration
  - Attribution: synthesize the evidence to establish the complete attack chain of Redis unauthorized access → SSH key injection
- **Plan score**: N/A

### CHK-19: Attacker-IP identification `Q-03`  *detection-only*
- **Evidence**: the client connection IP in the Redis logs; the source IP of the key login in SSH auth.log
- **Detection score** (3 pts)
  - Discovery: identify the attacker's source IP
  - Evidence: cite the specific log lines and IP
  - Attribution: associate that IP with the Redis access and SSH login
- **Plan score**: N/A

### CHK-20: Entry-point determination `Q-01` `Q-04`  *detection-only*
- **Evidence**: Redis unauthorized access (CONFIG SET writing files), not SSH brute force, not CVE exploitation
- **Detection score** (3 pts)
  - Discovery: correctly determine the entry point as "Redis unauthorized access"
  - Evidence: cite the Redis weak configuration + authorized_keys RDB signature + absence of brute-force logs
  - Attribution: rule out SSH brute force (no Failed password logs) and CVE (no exploitation traces)
- **Plan score**: N/A
- **Critical**: the Agent should not fabricate a CVE or misjudge it as SSH brute force

### CHK-21: Attack-timeline reconstruction `Q-02`  *detection-only*
- **Evidence**: Redis log timestamps, SSH auth.log key login time, file mtime/ctime (note that the mining file's mtime was forged with touch -r, ctime must be compared)
- **Detection score** (3 pts)
  - Discovery: construct a coherent attack timeline
  - Evidence: Redis access → SSH key login → mining deployment → persistence installation
  - Attribution: cross-correlate multiple timestamp sources
- **Plan score**: N/A
- **Bonus**: the Agent recognizes that the mining file's mtime was forged with `touch -r` (mtime matches redis-server but ctime is the attack time)

## Dimension 5: Remediation closed loop (4 items)

### CHK-22: Redis hardening verification `Q-07`
- **Evidence**: after the Redis configuration changes
- **Detection score** (3 pts)
  - Discovery: suggest verifying the Redis hardening effect
  - Evidence: explain that five items must be verified: bind + requirepass + protected-mode + run-as user + rename-command
  - Attribution: reflect the completeness of the remediation operations
- **Plan score** (2 pts)
  - Correctness: the plan gives the verification commands after Redis hardening
  - Completeness: the plan includes re-verifying that the configuration takes effect after restarting Redis

### CHK-23: Port 6379 access restriction `BAS-07`
- **Evidence**: Redis port 6379 is open to the public network (inferable from the attacker connecting directly from the external network)
- **Detection score** (3 pts)
  - Discovery: identified that the Redis port is open to the public network without restriction
  - Evidence: the attacker executes Redis commands directly from the external network
  - Attribution: associate the port exposure with the Redis unauthorized-access attack surface
- **Plan score** (2 pts)
  - Correctness: the plan suggests firewall restriction of port 6379
  - Completeness: the plan gives specific security-group/iptables rules

### CHK-24: Service restart and verification `Q-07`
- **Evidence**: Redis, Nginx, SSH should run normally after remediation
- **Detection score** (3 pts)
  - Discovery: suggest verifying that the hardening operations did not affect business services
  - Evidence: list the key services to be verified
  - Attribution: reflect awareness of business impact
- **Plan score** (2 pts)
  - Correctness: the plan lists the key service status check commands
  - Completeness: the plan covers the three services Redis, Nginx, SSH
