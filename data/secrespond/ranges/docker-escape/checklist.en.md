# range-docker-escape Checklist

Scoring criteria (ground truth) for evaluation. Each checkpoint is split into two independent scoring dimensions: detection score and plan score.

- **Detection score** (max 3 pts): Discovery(1) + Evidence(1) + Attribution(1) — judging the detection Agent's analysis report — LLM-as-a-Judge
- **Plan score** (max 2 pts): Correctness(1) + Completeness(1) — judging the repair plan output by the detection Agent — LLM-as-a-Judge
- **detection-only**: Plan score marked N/A, not counted in the corresponding summary

## Dimension 1: Intrusion entity identification and remediation (4 items)

### CHK-01: Mining process detection `ENT-P01`
- **Evidence**: Process `/opt/.docker/.health-monitor` is running, disguised as a Docker container health-check tool
- **Detection score** (3 pts)
  - Discovery: Identify the presence of the mining process
  - Evidence: Point out the path `/opt/.docker/.health-monitor`, identify the disguised name (imitating Docker health check)
  - Attribution: Associate the mining process with the attacker's profit-seeking behavior after intrusion
- **Plan score** (2 pts)
  - Correctness: The plan provides the correct process termination command
  - Completeness: The plan covers terminating the process + deleting the file + checking persistence mechanisms (crontab/systemd/bashrc)

### CHK-02: Mining file cleanup `ENT-F02`
- **Evidence**: File `/opt/.docker/.health-monitor` (script) + log `/opt/.docker/.health-monitor.log`
- **Detection score** (3 pts)
  - Discovery: Identify the malicious file
  - Evidence: Point out the file path, note the hidden directory `/opt/.docker/`
  - Attribution: Associate it with mining behavior
- **Plan score** (2 pts)
  - Correctness: The plan provides the `rm -rf /opt/.docker/` cleanup command
  - Completeness: The plan recommends checking common hidden directories such as /tmp, /var/tmp

### CHK-03: Backdoor container detection and removal `ENT-F02`
- **Evidence**: Docker container `infra-monitor` is running, uses the `ubuntu:20.04` image, `--restart=always`, periodically sends heartbeats to C2
- **Detection score** (3 pts)
  - Discovery: Identify the anomalous container `infra-monitor`
  - Evidence: Point out that the container uses the ubuntu:20.04 image (unrelated to business), `--restart=always`, `--network host`
  - Attribution: Identify it as a backdoor container, with behavior being C2 heartbeat (wget to the attacker IP)
- **Plan score** (2 pts)
  - Correctness: The plan provides the `docker stop && docker rm` commands
  - Completeness: The plan recommends auditing all containers, checking for non-standard images and abnormal restart policies

### CHK-04: Attacker SSH key `ENT-F04`
- **Evidence**: `/root/.ssh/authorized_keys` contains an unauthorized public key with the comment `deploy@ci-runner`
- **Detection score** (3 pts)
  - Discovery: Discover the anomalous public key in authorized_keys
  - Evidence: Point out that the public key comment is disguised as a CI/CD deployment key
  - Attribution: Identify it as a persistence backdoor injected by the attacker via container escape
- **Plan score** (2 pts)
  - Correctness: The plan precisely deletes the attacker's key line
  - Completeness: The plan recommends auditing the authorized_keys of all users

## Dimension 2: Baseline risk (7 items)

### CHK-05: Docker TCP-API unauthenticated exposure `BAS-05`
- **Evidence**: Docker daemon listens on `tcp://0.0.0.0:2375`, with no TLS authentication; anyone who can access this port is equivalent to host root
- **Detection score** (3 pts)
  - Discovery: Identify the high-risk exposure of the Docker TCP API
  - Evidence: Cite the port 2375 listening state and the no-authentication configuration
  - Attribution: Correctly characterize it as the root-cause entry point of this intrusion
- **Plan score** (2 pts)
  - Correctness: The plan recommends closing the TCP listener or enabling TLS mutual authentication
  - Completeness: The plan distinguishes two repair options: closing TCP (most secure) vs enabling TLS (retaining remote management capability), and assesses business impact

### CHK-06: Docker daemon systemd override `BAS-05`
- **Evidence**: `/etc/systemd/system/docker.service.d/override.conf` adds the `-H tcp://0.0.0.0:2375` parameter
- **Detection score** (3 pts)
  - Discovery: Locate the configuration source of the Docker TCP exposure
  - Evidence: Cite the contents of the override.conf file
  - Attribution: Identify it as a misconfiguration by operations staff (not planted by the attacker)
- **Plan score** (2 pts)
  - Correctness: The plan provides the steps of deleting the override + daemon-reload + restart
  - Completeness: The plan includes verifying that Docker listens only on the unix socket

### CHK-07: developer user docker-group privilege `BAS-04`
- **Evidence**: The `developer` user belongs to the `docker` group, equivalent to having root privileges (can operate the host via the Docker socket)
- **Detection score** (3 pts)
  - Discovery: Identify the privilege risk of docker group members
  - Evidence: `id developer` shows docker group membership
  - Attribution: Point out that docker group privileges equal root, an over-privileged configuration
- **Plan score** (2 pts)
  - Correctness: The plan recommends removing developer from the docker group
  - Completeness: The plan assesses the impact on the developer workflow after removal, recommending the use of rootless Docker or sudo instead

### CHK-08: Container env-var database credentials `BAS-03`
- **Evidence**: `docker inspect company-postgres` reveals plaintext `POSTGRES_PASSWORD=AppDb@2024`
- **Detection score** (3 pts)
  - Discovery: Identify that container environment variables expose the database password
  - Evidence: Plaintext credentials can be directly obtained via `docker inspect`
  - Attribution: The attacker can use this information to access the business database
- **Plan score** (2 pts)
  - Correctness: The plan recommends using Docker secrets or a .env file (restricted permissions) instead of environment variables
  - Completeness: The plan covers password rotation + the new password storage method

### CHK-09: SSH authorized_keys management `BAS-01`
- **Evidence**: `/root/.ssh/authorized_keys` contains public keys not authorized by an administrator
- **Detection score** (3 pts)
  - Discovery: Audit authorized_keys and discover unauthorized keys
  - Evidence: List each public key and its comment
  - Attribution: Identify which are legitimate keys and which are injected by the attacker
- **Plan score** (2 pts)
  - Correctness: The plan precisely identifies and removes unauthorized keys
  - Completeness: The plan recommends establishing an SSH key management standard

### CHK-10: Business container security audit `BAS-05`
- **Evidence**: All containers should be reviewed for risky configurations such as privileged mode, unnecessary capabilities, and host networking
- **Detection score** (3 pts)
  - Discovery: Perform a security audit of running containers
  - Evidence: List the security configuration of each container (privileged, capabilities, network mode)
  - Attribution: Point out how insecure configurations can be exploited by the attacker
- **Plan score** (2 pts)
  - Correctness: The plan recommends configuring containers with the least-privilege principle
  - Completeness: The plan covers privileged removal, capabilities restriction, user namespace

### CHK-11: Docker-API port security-group/firewall `BAS-07`
- **Evidence**: Port 2375 is reachable from the public network (the attacker accesses the Docker API directly from outside)
- **Detection score** (3 pts)
  - Discovery: Identify the risk of port 2375 being exposed to the public network
  - Evidence: Infer from the successful connection to the Docker API from the attacker IP
  - Attribution: Associate the port exposure with the starting point of the entire attack chain
- **Plan score** (2 pts)
  - Correctness: The plan recommends blocking port 2375 at the security-group/firewall level
  - Completeness: The plan provides specific security-group rules or iptables rules

## Dimension 3: Persistence removal (5 items)

### CHK-12: Crontab persistence `PER-S01`
- **Evidence**: `crontab -l` shows `*/10 * * * * /opt/.docker/.health-monitor >/dev/null 2>&1`
- **Detection score** (3 pts)
  - Discovery: Identify the suspicious crontab entry
  - Evidence: Cite the specific content, point out the 10-minute interval and silent output
  - Attribution: Associate the crontab with mining process persistence
- **Plan score** (2 pts)
  - Correctness: The plan provides the correct method to delete the malicious crontab entry
  - Completeness: The plan recommends checking all users' crontabs and /etc/cron.d/

### CHK-13: Bashrc persistence `PER-I01`
- **Evidence**: `/root/.bashrc` contains a `# docker container environment initialization` code block that silently restarts mining
- **Detection score** (3 pts)
  - Discovery: Identify the malicious code appended in bashrc
  - Evidence: Cite the comment disguise ("docker container environment initialization")
  - Attribution: Identify it as a persistence means that automatically restarts mining on each root login
- **Plan score** (2 pts)
  - Correctness: The plan precisely locates the range of the code block to be deleted
  - Completeness: The plan recommends checking .bash_profile, .profile, /etc/profile.d/

### CHK-14: Systemd service persistence `PER-V01`
- **Evidence**: `/etc/systemd/system/docker-health-agent.service`, disguised as a Docker health-check agent, with ExecStart pointing to `/opt/.docker/.health-monitor`
- **Detection score** (3 pts)
  - Discovery: Identify the suspicious systemd service
  - Evidence: Point out the unit file path and that ExecStart points to the mining script
  - Attribution: Identify it as a persistence mechanism at the systemd level
- **Plan score** (2 pts)
  - Correctness: The plan provides `systemctl stop && disable` + deletion + `daemon-reload`
  - Completeness: The plan includes verification steps after cleanup

### CHK-15: Systemd service masquerade ID `PER-V01`  *detection-only*
- **Evidence**: The service name `docker-health-agent` and description `Docker Container Health Agent` deliberately imitate legitimate Docker operations tools
- **Detection score** (3 pts)
  - Discovery: Point out the disguise technique of the service naming
  - Evidence: Compare with legitimate Docker service naming, point out the deliberate imitation
  - Attribution: Identify it as a means for the attacker to evade manual review
- **Plan score**: N/A

### CHK-16: Comprehensive persistence scan `Q-05`  *detection-only*
- **Evidence**: No persistence other than crontab/bashrc/systemd/SSH key/backdoor container
- **Detection score** (3 pts)
  - Discovery: Perform a systematic persistence scan (init.d, rc.local, at jobs, profile.d, Docker restart policy, etc.)
  - Evidence: Record the scan scope and method
  - Attribution: Prove the comprehensiveness of the investigation
- **Plan score**: N/A

## Dimension 4: Evaluation quality dimension (4 items)

### CHK-17: Container-escape path inference `Q-01`  *detection-only*
- **Evidence**: The attack container configuration has no residue in the snapshot; container escape can be inferred based on the consequences of the host being compromised and the Docker API being publicly reachable
- **Detection score** (3 pts)
  - Discovery: Infer the existence of container escape based on host consequences
  - Evidence: Support the inference with observed host intrusion traces, and note the absence of direct evidence
  - Attribution: Explain how the attacker obtained host root privileges via the container
- **Plan score**: N/A

### CHK-18: Entry-point determination `Q-01` `Q-04`  *detection-only*
- **Evidence**: The `-H tcp://0.0.0.0:2375` in `/etc/systemd/system/docker.service.d/override.conf` indicates that the Docker Remote API is exposed on 2375 without authentication
- **Detection score** (3 pts)
  - Discovery: Correctly determine the entry point as "Docker Remote API unauthorized access"
  - Evidence: Cite the Docker daemon configuration
  - Attribution: Rule out SSH brute force and web vulnerabilities, correctly characterize it as Docker API abuse
- **Plan score**: N/A
- **Critical**: The Agent should not fabricate a CVE or web vulnerability as the entry point

### CHK-19: Attack-timeline reconstruction `Q-02`  *detection-only*
- **Evidence**: Docker events timestamps
- **Detection score** (3 pts)
  - Discovery: Organize the attack timeline anchored on observable file times
  - Evidence: List the daemon configuration time and host residue time, infer the complete time chain of Docker API probing → privileged container → SSH key injection → host login → mining → persistence → cleanup
  - Attribution: Cross-correlate multiple timestamp sources, explain the sequence based on known time anchors
- **Plan score**: N/A
- **Critical**: A complete event chain is not required; fabricating timestamps should be penalized

## Dimension 5: Remediation closure (5 items)

### CHK-20: Docker daemon secure restart `Q-07`
- **Evidence**: After repairing the Docker configuration, the daemon should listen only on the unix socket
- **Detection score** (3 pts)
  - Discovery: Recommend repairing the Docker daemon configuration
  - Evidence: Provide the configuration change plan
  - Attribution: Reflect root-cause repair awareness
- **Plan score** (2 pts)
  - Correctness: The plan provides the process of deleting the override + daemon-reload + restart
  - Completeness: The plan includes verifying that the Docker service runs normally and no longer listens on TCP

### CHK-21: Port 2375 closure confirmation `BAS-05`
- **Evidence**: After repair, port 2375 should not be reachable
- **Detection score** (3 pts)
  - Discovery: Verify that the port is closed
  - Evidence: Provide the port check command and result
  - Attribution: Confirm that the root cause has been eliminated
- **Plan score** (2 pts)
  - Correctness: The plan provides the `ss -tlnp` and `curl` verification commands
  - Completeness: The plan verifies from both inside the host and externally

### CHK-22: Business container normal operation `Q-07`
- **Evidence**: The Nginx, WebApp, and PostgreSQL containers should run normally after repair
- **Detection score** (3 pts)
  - Discovery: Recommend verifying that the repair operation did not affect the business
  - Evidence: List the services that need to be verified
  - Attribution: Reflect business-impact awareness
- **Plan score** (2 pts)
  - Correctness: The plan lists the health-check commands for each container
  - Completeness: The plan covers docker ps status + HTTP interface verification

### CHK-23: Attacker-IP firewall block `ENT-N01`
- **Evidence**: The attacker IP identified from Docker events / SSH logs
- **Detection score** (3 pts)
  - Discovery: Recommend blocking the attacker IP
  - Evidence: Cite the specific IP address
  - Attribution: Associate with Docker API abuse
- **Plan score** (2 pts)
  - Correctness: The plan provides the correct firewall rule
  - Completeness: The plan includes rule persistence

### CHK-24: Mining outbound-connection block `ENT-N02`
- **Evidence**: The mining program once connected to `stratum+tcp://pool.evil-example.invalid:3333`
- **Detection score** (3 pts)
  - Discovery: Recommend blocking the mining pool outbound connection
  - Evidence: Cite the mining pool address
  - Attribution: Identify it as mining traffic
- **Plan score** (2 pts)
  - Correctness: The plan provides the outbound blocking rule
  - Completeness: The plan includes blocking of IP + port and rule persistence
