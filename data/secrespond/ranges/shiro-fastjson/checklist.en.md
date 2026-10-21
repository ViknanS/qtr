# range-shiro-fastjson Checklist

Scoring criteria (ground truth) for evaluation. Each checkpoint is split into two independent scoring dimensions: detection score and plan score.

- **Detection score** (max 3 pts): Discovery(1) + Evidence(1) + Attribution(1) — judging the detection Agent's analysis report — LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness(1) + Completeness(1) — judging the repair plan output by the detection Agent — LLM-as-a-Judge
- **detection-only**: plan score marked N/A, not included in the corresponding summary

## Dimension 1: Intrusion entity identification and disposal (8 items)

### CHK-01: JSP Webshell 1 (error.jsp) `ENT-F01`
- **Evidence**: `/opt/tomcat/webapps/ROOT/static/css/error.jsp` — JSP Webshell disguised under the CSS directory
- **Detection score** (3 pts)
  - Discovery: Identifies a suspicious JSP file present in the static-resource directory
  - Evidence: Points out the file path, recognizes that a JSP file should not appear in the css directory
  - Attribution: Associates the Webshell with the attacker's implantation via Shiro RCE
- **Plan score** (2 pts)
  - Correctness: Plan gives the correct file deletion command
  - Completeness: Plan recommends scanning all webapps directories for anomalous JSP/JSPX files

### CHK-02: JSP Webshell 2 (analytics.jsp) `ENT-F01`
- **Evidence**: `/opt/tomcat/webapps/ROOT/static/js/analytics.jsp` — disguised as an analytics script
- **Detection score** (3 pts)
  - Discovery: Identifies a second Webshell
  - Evidence: Points out the anomaly of a JSP file appearing in the js directory
  - Attribution: Recognizes the attacker's use of multiple Webshells as backup entry points
- **Plan score** (2 pts)
  - Correctness: Plan gives the deletion command
  - Completeness: Plan recommends a comprehensive scan, not missing other hidden Webshells

### CHK-03: Mining process detection `ENT-P01`
- **Evidence**: Process `/opt/.cache/.java-updater` is running
- **Detection score** (3 pts)
  - Discovery: Identifies the mining process
  - Evidence: Points out the path `/opt/.cache/.java-updater`, recognizes the disguised name
  - Attribution: Associates the mining process with the attacker's profit-seeking behavior after intrusion
- **Plan score** (2 pts)
  - Correctness: Plan gives the correct process termination command
  - Completeness: Plan covers terminating the process + deleting the file + checking the guard mechanism

### CHK-04: Mining binary cleanup `ENT-F02`
- **Evidence**: File `/opt/.cache/.java-updater` exists
- **Detection score** (3 pts)
  - Discovery: Identifies the malicious file
  - Evidence: Points out the file path and type
  - Attribution: Associates it with the mining behavior
- **Plan score** (2 pts)
  - Correctness: Plan gives the correct deletion command
  - Completeness: Plan recommends checking other suspicious files under /opt/.cache/ (including the log .java-updater.log)

### CHK-05: MySQL dump file cleanup `ENT-F04`
- **Evidence**: `/tmp/.sql_dump` — MySQL user-table data exported by the attacker
- **Detection score** (3 pts)
  - Discovery: Discovers the database dump file left by the attacker
  - Evidence: Points out the file path and content (sys_user table data)
  - Attribution: Identifies it as evidence of the attacker's data theft behavior
- **Plan score** (2 pts)
  - Correctness: Plan recommends preserving it first for forensic analysis
  - Completeness: Plan describes the cleanup steps after forensics is complete

### CHK-06: MySQL UDF persistence & backdoor `ENT-F02` `PER-D01`
- **Evidence**: `lib_mysqludf_json.so` in the MySQL plugin directory — a malicious UDF shared library
- **Detection score** (3 pts)
  - Discovery: Identifies a suspicious SO file and anomalous UDF function in the MySQL plugin directory
  - Evidence: Points out the file path and the corresponding UDF function (sys_exec)
  - Attribution: Associates the UDF backdoor with the attacker's persistence behavior after obtaining the database password
- **Plan score** (2 pts)
  - Correctness: Plan gives the DROP FUNCTION + delete SO file commands
  - Completeness: Plan recommends auditing all non-standard SO files in the MySQL plugin directory and checking all UDF functions (`SELECT * FROM mysql.func`)

### CHK-07: Webshell dir. masquerade `ENT-F01`  *detection-only*
- **Evidence**: The two Webshells are placed under `static/css/` and `static/js/` respectively
- **Detection score** (3 pts)
  - Discovery: Points out the disguise technique of placing JSP files in the static-resource directory
  - Evidence: Compares against the normal Tomcat application structure, points out the anomalous directory location
  - Attribution: Recognizes it as the attacker using directory disguise to evade routine Webshell scans
- **Plan score**: N/A (disposal covered by CHK-01/02)
- **Bonus**: Agent recommends setting JSP execution restrictions on the Tomcat static-resource directory

### CHK-08: Attacker SSH key injection `ENT-F04` `PER-A01`
- **Evidence**: `/root/.ssh/authorized_keys` contains an anomalous key with the comment `deploy@ci-ruoyi`
- **Detection score** (3 pts)
  - Discovery: Identifies the suspicious SSH public key in authorized_keys
  - Evidence: Points out the key comment `deploy@ci-ruoyi` and the key content characteristics
  - Attribution: Identifies it as a persistence backdoor key implanted by the attacker
- **Plan score** (2 pts)
  - Correctness: Plan gives the command to remove the specific key line
  - Completeness: Plan recommends checking the authorized_keys of all users

## Dimension 2: Baseline risk (8 items)

### CHK-09: Tomcat sudo priv. tightening `BAS-04`
- **Evidence**: `/etc/sudoers.d/tomcat` grants `NOPASSWD: /usr/bin/find, /usr/bin/vim`
- **Detection score** (3 pts)
  - Discovery: Identifies the dangerous sudo privileges of the tomcat user
  - Evidence: Points out that find -exec and vim :!bash can be used for privilege escalation
  - Attribution: Associates the sudo privileges with the attacker's path from tomcat to root
- **Plan score** (2 pts)
  - Correctness: Plan recommends removing the NOPASSWD privileges for find/vim
  - Completeness: Plan includes the `visudo -c` verification step, recommends replacing with a safe log-viewing tool

### CHK-10: sudoers backdoor cleanup `PER-A02`
- **Evidence**: `/etc/sudoers.d/99-java-ops` — backdoor rule `java-ops ALL=(ALL) NOPASSWD: ALL` implanted by the attacker
- **Detection score** (3 pts)
  - Discovery: Identifies the anomalous sudoers file in /etc/sudoers.d/
  - Evidence: Points out the 99-java-ops file and the NOPASSWD ALL privilege of the java-ops user
  - Attribution: Identifies it as a persistence privilege-escalation backdoor implanted by the attacker
- **Plan score** (2 pts)
  - Correctness: Plan gives the file deletion command
  - Completeness: Plan recommends checking all files under /etc/sudoers.d/ and verifying whether there are other anomalous rules

### CHK-11: application .yml cred. protection `BAS-03`
- **Evidence**: `/opt/ruoyi/application.yml` contains the plaintext database password `RuoYi@2024`
- **Detection score** (3 pts)
  - Discovery: Identifies the plaintext credential in the configuration file
  - Evidence: Quotes the specific configuration line and password value
  - Attribution: Points out that the attacker obtained database access by reading this file
- **Plan score** (2 pts)
  - Correctness: Plan recommends changing the database password and using encrypted storage
  - Completeness: Plan recommends tightening file permissions (chmod 600), using environment variables or Jasypt encryption

### CHK-12: MySQL remote access ctrl. `BAS-02`
- **Evidence**: MySQL root user can access from `%` (any host), password `RuoYi@2024`
- **Detection score** (3 pts)
  - Discovery: Identifies the risk of remote root MySQL access
  - Evidence: Points out the `root@'%'` grant and bind-address=0.0.0.0
  - Attribution: Points out that this configuration can be exploited by external attackers
- **Plan score** (2 pts)
  - Correctness: Plan gives the SQL command to restrict to localhost and the bind-address modification
  - Completeness: Plan includes the verification step after modification

### CHK-13: Shiro default key `BAS-03`
- **Evidence**: `application.yml` contains `shiro.rememberMe.cipherKey: zSyK5Kp6PZAAjlT+eeNMlg==`
- **Detection score** (3 pts)
  - Discovery: Identifies that Shiro uses a default encryption key
  - Evidence: Quotes the cipherKey value in the configuration file, points out that this is a well-known default key
  - Attribution: Directly associates the default key with the Shiro deserialization RCE entry point
- **Plan score** (2 pts)
  - Correctness: Plan recommends replacing with a random key or upgrading the Shiro version
  - Completeness: Plan gives multi-layer repair recommendations (change key / upgrade / disable rememberMe)

### CHK-14: Tomcat run-as user priv. `BAS-04`
- **Evidence**: Tomcat runs as the tomcat user, but that user has excessive sudo privileges
- **Detection score** (3 pts)
  - Discovery: Identifies the user-privilege configuration of the Tomcat process
  - Evidence: Points out the sudo configuration of the tomcat user
  - Attribution: Associates the excessive privileges with the privilege-escalation path
- **Plan score** (2 pts)
  - Correctness: Plan recommends following the principle of least privilege
  - Completeness: Plan recommends removing unnecessary sudo privileges, keeping only what the business requires

### CHK-15: Tomcat port host-level access ctrl. `BAS-06`
- **Evidence**: Tomcat listens on port 8080 serving the RuoYi application, with no firewall restriction configured at the host layer
- **Detection score** (3 pts)
  - Discovery: Identifies the lack of access control on the Tomcat port at the host layer
  - Evidence: Points out that port 8080 has no access control
  - Attribution: Associates port reachability with the attack surface of Shiro exploitation
- **Plan score** (2 pts)
  - Correctness: Plan recommends restricting the source of 8080 access on the host firewall or reverse proxy
  - Completeness: Plan gives firewall rule modification recommendations

### CHK-16: MySQL password strength `BAS-03`
- **Evidence**: The MySQL root password `RuoYi@2024` is a weak password (highly patterned, guessable)
- **Detection score** (3 pts)
  - Discovery: Identifies that the database uses a weak password
  - Evidence: Points out the regularity of the password
  - Attribution: Points out that the weak password is directly exploited by the attacker after reading it from the configuration file
- **Plan score** (2 pts)
  - Correctness: Plan recommends changing to a strong password
  - Completeness: Plan gives password complexity requirements

## Dimension 3: Persistence removal (8 items)

### CHK-17: Systemd service persistence `PER-V01`
- **Evidence**: `/etc/systemd/system/java-app-monitor.service` — disguised as Java application monitoring
- **Detection score** (3 pts)
  - Discovery: Identifies the suspicious systemd service
  - Evidence: Points out the unit file path and that ExecStart points to /opt/.cache/.java-updater
  - Attribution: Identifies it as a mining persistence mechanism
- **Plan score** (2 pts)
  - Correctness: Plan gives the complete commands of stop + disable + delete unit + daemon-reload
  - Completeness: Plan includes the verification step after cleanup

### CHK-18: Systemd service masquerade `PER-V01`  *detection-only*
- **Evidence**: The service name `java-app-monitor` and description `Java Application Monitor Service` imitate a legitimate monitoring service
- **Detection score** (3 pts)
  - Discovery: Points out the disguise technique of the service name
  - Evidence: Compares against legitimate system services, points out the naming imitation
  - Attribution: Recognizes it as the attacker using naming disguise to evade manual review
- **Plan score**: N/A

### CHK-19: Crontab persistence `PER-S01`
- **Evidence**: `crontab -l` shows `*/10 * * * * /opt/.cache/.java-updater >/dev/null 2>&1`
- **Detection score** (3 pts)
  - Discovery: Identifies the suspicious crontab entry
  - Evidence: Quotes the specific crontab content, points out the scheduled execution interval and silent output
  - Attribution: Associates the crontab with mining persistence
- **Plan score** (2 pts)
  - Correctness: Plan gives the method to delete the malicious crontab entry
  - Completeness: Plan recommends checking the crontab of all users and /etc/cron.d/

### CHK-20: profile.d persistence `PER-I01`
- **Evidence**: `/etc/profile.d/java-env.sh` — disguised as a Java environment-variable script, actually launches mining
- **Detection score** (3 pts)
  - Discovery: Identifies the malicious script in profile.d
  - Evidence: Points out that the file contains code to launch .java-updater
  - Attribution: Recognizes it as a persistence means that automatically restarts mining on every user login
- **Plan score** (2 pts)
  - Correctness: Plan gives the file deletion command
  - Completeness: Plan recommends checking all scripts under /etc/profile.d/

### CHK-21: at deferred task `PER-S03`
- **Evidence**: `atq` shows a pending delayed task
- **Detection score** (3 pts)
  - Discovery: Identifies the suspicious task in the at queue
  - Evidence: Points out the task content (executing .java-updater)
  - Attribution: Recognizes it as a delayed-execution mechanism set by the attacker to counter one-time cleanup
- **Plan score** (2 pts)
  - Correctness: Plan gives the `atrm` deletion command
  - Completeness: Plan recommends checking all pending at tasks and considering disabling atd

### CHK-22: rc.local persistence `PER-V02`
- **Evidence**: `/etc/rc.d/rc.local` contains a `.java-updater` startup command
- **Detection score** (3 pts)
  - Discovery: Identifies the suspicious entry in rc.local
  - Evidence: Quotes the specific line content
  - Attribution: Recognizes it as boot-time auto-start mining persistence
- **Plan score** (2 pts)
  - Correctness: Plan gives the method to delete the corresponding line
  - Completeness: Plan recommends reviewing the entire content of rc.local

### CHK-23: Comprehensive persistence scan `Q-05`  *detection-only*
- **Evidence**: This range has 8 persistence mechanisms in total
- **Detection score** (3 pts)
  - Discovery: Performs a systematic persistence scan (covering systemd/cron/profile.d/ssh keys/sudoers/MySQL UDF/at/rc.local/init.d, etc.)
  - Evidence: Records the scan scope and method
  - Attribution: Demonstrates the comprehensiveness of the investigation
- **Plan score**: N/A

### CHK-24: Persistence correlation analysis `Q-05`  *detection-only*
- **Evidence**: All 8 persistence mechanisms point to the same mining program `/opt/.cache/.java-updater`
- **Detection score** (3 pts)
  - Discovery: Identifies the correlation among the multiple persistence mechanisms
  - Evidence: Points out that all persistence mechanisms ultimately launch the same program
  - Attribution: Analyzes it as the attacker's redundant persistence strategy
- **Plan score**: N/A

## Dimension 4: Root-cause tracing (10 items)

### CHK-25: Entry-point Shiro deserialization `Q-01` `Q-04`  *detection-only*
- **Evidence**: Shiro default key + rememberMe=deleteMe fingerprint + Webshell deployment + no SSH brute-force traces
- **Detection score** (3 pts)
  - Discovery: Correctly determines the entry point as "Shiro default-key deserialization RCE"
  - Evidence: Quotes the Shiro version, default key, CommonsCollections gadget
  - Attribution: Rules out SSH brute-force and other entry points, correctly characterizes it as a CVE-exploitation scenario
- **Plan score**: N/A
- **Critical**: Agent should not fabricate a non-existent CVE number

### CHK-26: Shiro version & key config locate `VUL-01`
- **Evidence**: `/opt/tomcat/webapps/ROOT/WEB-INF/lib/shiro-core-1.7.0.jar` (the library itself has already removed the hardcoded default key), but `application.yml`'s `shiro.rememberMe.cipherKey` still configures the well-known default key `zSyK5Kp6PZAAjlT+eeNMlg==`
- **Detection score** (3 pts)
  - Discovery: Locates the Shiro version in the JAR dependencies and discovers the use of a known default key in the application configuration
  - Evidence: Points out the JAR file path and version number 1.7.0, as well as the cipherKey value in application.yml
  - Attribution: Associates the known default key configured at the application layer with the Shiro deserialization RCE entry point
- **Plan score** (2 pts)
  - Correctness: Plan recommends replacing the cipherKey in application.yml with a strong random key
  - Completeness: Plan gives multi-layer repair (change key / disable rememberMe)

### CHK-27: Fastjson version locate `VUL-01`
- **Evidence**: `/opt/tomcat/webapps/ROOT/WEB-INF/lib/fastjson-1.2.68.jar`
- **Detection score** (3 pts)
  - Discovery: Locates the Fastjson version in the JAR dependencies
  - Evidence: Points out the JAR file path and version number 1.2.68 (has the autoType vulnerability)
  - Attribution: Associates Fastjson 1.2.68 with the deserialization vulnerability
- **Plan score** (2 pts)
  - Correctness: Plan recommends upgrading Fastjson to >= 1.2.83 or replacing it with Jackson
  - Completeness: Plan describes the risk of autoType and configuration mitigation options

### CHK-28: Commons-Collections gadget ID `VUL-01`  *detection-only*
- **Evidence**: `/opt/tomcat/webapps/ROOT/WEB-INF/lib/commons-collections-3.2.1.jar`
- **Detection score** (3 pts)
  - Discovery: Identifies CommonsCollections 3.2.1 as a gadget chain dependency
  - Evidence: Points out the JAR version and the deserialization exploitation relationship
  - Attribution: Associates CC 3.x with the gadget chain of the Shiro deserialization RCE
- **Plan score**: N/A (upgrade covered by CHK-26/27)

### CHK-29: Java process-chain provenance `Q-02`  *detection-only*
- **Evidence**: In the alert, `parent_procpath=/usr/bin/java` → Tomcat → RuoYi → Shiro/Fastjson
- **Detection score** (3 pts)
  - Discovery: Traces from the Java process to the specific application
  - Evidence: Establishes the correlation chain java → tomcat → ruoyi → shiro/fastjson
  - Attribution: Completes the full tracing from process to vulnerability
- **Plan score**: N/A

### CHK-30: sudo privesc-path reconstruction `Q-02`  *detection-only*
- **Evidence**: The attacker uses `sudo find /tmp -exec /bin/bash -p \;` to escalate from tomcat to root
- **Detection score** (3 pts)
  - Discovery: Reconstructs the sudo find privilege-escalation path
  - Evidence: Points out the escalation principle of find -exec and the sudoers configuration
  - Attribution: Associates the escalation with subsequent root-privilege operations (persistence, mining)
- **Plan score**: N/A (repair covered by CHK-09)

### CHK-31: Attack-timeline reconstruction `Q-02`  *detection-only*
- **Evidence**: Tomcat access log timestamps, Webshell file mtime, mining deployment time, persistence-mechanism creation time
- **Detection score** (3 pts)
  - Discovery: Constructs a coherent attack timeline
  - Evidence: Shiro RCE → Webshell deployment → information gathering → privilege escalation → persistence → mining
  - Attribution: Cross-correlates multiple timestamp sources
- **Plan score**: N/A

### CHK-32: Tomcat log partial-wipe ID `Q-02` `Q-03`  *detection-only*
- **Evidence**: The rememberMe/error.jsp requests in the access log were deleted, but the analytics.jsp request was retained (attacker oversight)
- **Detection score** (3 pts)
  - Discovery: Identifies the partial-cleanup traces in the Tomcat access log
  - Evidence: Finds that the analytics.jsp request record is still present, while other attack requests are missing
  - Attribution: Identifies the log incompleteness itself as evidence of the attacker cleaning traces
- **Plan score**: N/A

### CHK-33: Attacker IP identification `Q-03`  *detection-only*
- **Evidence**: The source IP of the attack requests in the Tomcat access log
- **Detection score** (3 pts)
  - Discovery: Identifies the attacker's source IP address
  - Evidence: Quotes the specific log line and IP address
  - Attribution: Associates that IP with Webshell access and the Shiro attack
- **Plan score**: N/A (blocking covered by CHK-38)

### CHK-34: Data-leak assessment `Q-02`  *detection-only*
- **Evidence**: `/tmp/.sql_dump` contains sys_user table data; application.yml credentials have been leaked
- **Detection score** (3 pts)
  - Discovery: Assesses the scope of the data leak (user table, database credentials)
  - Evidence: Points out the specific data content that was exported
  - Attribution: Associates the data theft with the attacker's information-gathering stage
- **Plan score**: N/A

## Dimension 5: Vulnerability remediation (6 items)

### CHK-35: Shiro vuln fix `VUL-01`
- **Evidence**: Shiro 1.2.4 uses a default key
- **Detection score** (3 pts)
  - Discovery: Recommends remediating the Shiro default-key vulnerability
  - Evidence: Quotes the Shiro version and default key
  - Attribution: Directly associates the remediation need with the entry-point vulnerability
- **Plan score** (2 pts)
  - Correctness: Plan is reasonably layered (change key / upgrade version / disable feature)
  - Completeness: Plan describes the pros, cons, and applicable scenarios of each layer of remediation

### CHK-36: Fastjson vuln fix `VUL-01`
- **Evidence**: Fastjson 1.2.68 has the autoType deserialization vulnerability
- **Detection score** (3 pts)
  - Discovery: Recommends remediating the Fastjson autoType vulnerability
  - Evidence: Quotes the version number and known vulnerability
  - Attribution: Associates Fastjson as a backup attack entry point with remediation priority
- **Plan score** (2 pts)
  - Correctness: Plan recommends upgrading to a safe version or replacing with Jackson
  - Completeness: Plan includes the autoType global-disable configuration

### CHK-37: Commons-Collections upgrade `VUL-01`
- **Evidence**: commons-collections-3.2.1 is the gadget chain for Shiro deserialization
- **Detection score** (3 pts)
  - Discovery: Recommends upgrading CommonsCollections
  - Evidence: Points out the role of CC 3.x as a gadget
  - Attribution: Upgrading CC can break the gadget chain
- **Plan score** (2 pts)
  - Correctness: Plan recommends upgrading to CC 3.2.2+ or 4.x (deserialization fixed)
  - Completeness: Plan describes the version-compatibility impact

### CHK-38: Attacker IP firewall block `ENT-N01`
- **Evidence**: The attacker IP identified from the Tomcat access log
- **Detection score** (3 pts)
  - Discovery: Recommends blocking the attacker IP
  - Evidence: Quotes the specific IP address
  - Attribution: Associates it with the Web attack traffic
- **Plan score** (2 pts)
  - Correctness: Plan gives the correct firewall rule
  - Completeness: Plan includes persistent rules and verification steps

### CHK-39: Mining outbound block `ENT-N02`
- **Evidence**: Mining connection `stratum+tcp://pool.evil-example.invalid:3333`
- **Detection score** (3 pts)
  - Discovery: Recommends blocking the mining-pool outbound connection
  - Evidence: Quotes the mining-pool address and port
  - Attribution: Identifies it as mining C2 communication
- **Plan score** (2 pts)
  - Correctness: Plan gives the outbound firewall rule
  - Completeness: Plan includes IP + port blocking and rule persistence

### CHK-40: Vuln-fix plan assessment `Q-07`  *detection-only*
- **Evidence**: The remediation plans for the three components Shiro/Fastjson/CC
- **Detection score** (3 pts)
  - Discovery: Assesses the layering and completeness of the remediation plan
  - Evidence: Distinguishes minimal remediation (change key), recommended remediation (upgrade version), best remediation (multi-layer defense)
  - Attribution: Reflects the depth of understanding of the Java security ecosystem
- **Plan score**: N/A

## Dimension 6: Remediation closure (5 items)

### CHK-41: Vuln-fix verification `Q-07`
- **Evidence**: Shiro/Fastjson should pass verification after remediation
- **Detection score** (3 pts)
  - Discovery: Recommends performing post-remediation verification
  - Evidence: Describes the verification method (rememberMe Cookie no longer triggers RCE)
  - Attribution: Reflects remediation-closure awareness
- **Plan score** (2 pts)
  - Correctness: Plan gives the verification steps
  - Completeness: Plan includes regression-testing recommendations

### CHK-42: Webshell cleanup confirmation `Q-07`
- **Evidence**: The two Webshells should have been cleaned up
- **Detection score** (3 pts)
  - Discovery: Recommends confirming the completeness of Webshell cleanup
  - Evidence: Gives the method to scan all webapps directories
  - Attribution: Prevents missing other Webshells
- **Plan score** (2 pts)
  - Correctness: Plan gives the comprehensive Webshell scan command
  - Completeness: Plan recommends deploying file-integrity monitoring

### CHK-43: Service restart & verification `Q-07`
- **Evidence**: Tomcat and MySQL should run normally after remediation
- **Detection score** (3 pts)
  - Discovery: Recommends verifying that the remediation did not affect business services
  - Evidence: Lists the key services to be verified
  - Attribution: Reflects business-impact awareness
- **Plan score** (2 pts)
  - Correctness: Plan lists the status-check commands for the key services
  - Completeness: Plan covers Tomcat and MySQL, considers port-listening confirmation

### CHK-44: Database credential rotation `Q-07`
- **Evidence**: The MySQL password and application.yml credentials have been leaked
- **Detection score** (3 pts)
  - Discovery: Recommends performing credential rotation
  - Evidence: Lists the credentials to be rotated (MySQL password, all passwords in application.yml)
  - Attribution: Leaked credentials still carry a reuse risk even after the vulnerability is remediated
- **Plan score** (2 pts)
  - Correctness: Plan gives the password rotation steps
  - Completeness: Plan covers comprehensive rotation of MySQL, Redis, and application credentials

### CHK-45: Persistence-cleanup integrity `Q-07`
- **Evidence**: All 8 persistence mechanisms should be fully removed
- **Detection score** (3 pts)
  - Discovery: Recommends verifying one by one that all persistence has been removed
  - Evidence: Gives the verification command for each type of persistence
  - Attribution: Prevents omissions that let the attacker re-establish control
- **Plan score** (2 pts)
  - Correctness: Plan lists the item-by-item verification methods for the 8 persistence mechanisms
  - Completeness: Plan recommends re-checking after reboot
