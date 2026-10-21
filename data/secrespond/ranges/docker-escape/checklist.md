# range-docker-escape 检查清单

评估的评分标准（ground truth）。每个检查点拆分为检测分、方案分两个独立评分维度。

- **检测分**（满分 3 分）：发现(1) + 证据(1) + 归因(1) — 评判检测 Agent 的分析报告 — LLM-as-a-Judge
- **方案分**（满分 2 分）：正确性(1) + 完整性(1) — 评判检测 Agent 输出的修复方案 — LLM-as-a-Judge
- **仅检测项**：方案分标记 N/A，不参与对应汇总

## 维度 1：入侵实体识别与处置（4 项）

### CHK-01：挖矿进程检测 `ENT-P01`
- **证据**：进程 `/opt/.docker/.health-monitor` 正在运行，伪装为 Docker 容器健康检查工具
- **检测分**（3 分）
  - 发现：识别到挖矿进程存在
  - 证据：指出路径 `/opt/.docker/.health-monitor`，识别伪装名称（模仿 Docker 健康检查）
  - 归因：将挖矿进程与攻击者入侵后的牟利行为关联
- **方案分**（2 分）
  - 正确性：方案给出正确的进程终止命令
  - 完整性：方案涵盖终止进程 + 删除文件 + 检查守护机制（crontab/systemd/bashrc）

### CHK-02：挖矿文件清理 `ENT-F02`
- **证据**：文件 `/opt/.docker/.health-monitor`（脚本）+ 日志 `/opt/.docker/.health-monitor.log`
- **检测分**（3 分）
  - 发现：识别到恶意文件
  - 证据：指出文件路径，注意隐藏目录 `/opt/.docker/`
  - 归因：将其与挖矿行为关联
- **方案分**（2 分）
  - 正确性：方案给出 `rm -rf /opt/.docker/` 的清理命令
  - 完整性：方案建议检查 /tmp、/var/tmp 等常见隐藏目录

### CHK-03：后门容器检测与清除 `ENT-F02`
- **证据**：Docker 容器 `infra-monitor` 运行中，使用 `ubuntu:20.04` 镜像，`--restart=always`，定期向 C2 发送心跳
- **检测分**（3 分）
  - 发现：识别到异常容器 `infra-monitor`
  - 证据：指出容器使用 ubuntu:20.04 镜像（与业务无关）、`--restart=always`、`--network host`
  - 归因：识别为后门容器，行为为 C2 心跳（wget 到攻击者 IP）
- **方案分**（2 分）
  - 正确性：方案给出 `docker stop && docker rm` 命令
  - 完整性：方案建议审计所有容器，检查非标准镜像和异常 restart policy

### CHK-04：攻击者 SSH 密钥 `ENT-F04`
- **证据**：`/root/.ssh/authorized_keys` 中包含注释为 `deploy@ci-runner` 的非授权公钥
- **检测分**（3 分）
  - 发现：发现 authorized_keys 中的异常公钥
  - 证据：指出公钥注释伪装为 CI/CD 部署密钥
  - 归因：识别为攻击者通过容器逃逸注入的持久化后门
- **方案分**（2 分）
  - 正确性：方案精确删除攻击者密钥行
  - 完整性：方案建议审计所有用户的 authorized_keys

## 维度 2：基线风险（7 项）

### CHK-05：Docker TCP API 未授权暴露 `BAS-05`
- **证据**：Docker daemon 监听 `tcp://0.0.0.0:2375`，无 TLS 认证，任何能访问该端口的人等同于宿主机 root
- **检测分**（3 分）
  - 发现：识别 Docker TCP API 暴露的高危风险
  - 证据：引用端口 2375 监听状态和无认证配置
  - 归因：将其正确定性为本次入侵的根因入口
- **方案分**（2 分）
  - 正确性：方案建议关闭 TCP 监听或启用 TLS 双向认证
  - 完整性：方案区分两种修复方案：关闭 TCP（最安全）vs 启用 TLS（保留远程管理能力），评估业务影响

### CHK-06：Docker daemon systemd override `BAS-05`
- **证据**：`/etc/systemd/system/docker.service.d/override.conf` 添加了 `-H tcp://0.0.0.0:2375` 参数
- **检测分**（3 分）
  - 发现：定位到 Docker TCP 暴露的配置来源
  - 证据：引用 override.conf 文件内容
  - 归因：识别为运维人员的错误配置（非攻击者植入）
- **方案分**（2 分）
  - 正确性：方案给出删除 override + daemon-reload + restart 的步骤
  - 完整性：方案包含验证 Docker 仅监听 unix socket

### CHK-07：developer 用户 docker 组权限 `BAS-04`
- **证据**：`developer` 用户属于 `docker` 组，等同于拥有 root 权限（可通过 Docker socket 操作宿主机）
- **检测分**（3 分）
  - 发现：识别 docker 组成员的权限风险
  - 证据：`id developer` 显示 docker 组成员
  - 归因：指出 docker 组权限等同 root，是权限过大的配置
- **方案分**（2 分）
  - 正确性：方案建议将 developer 移出 docker 组
  - 完整性：方案评估移除后对开发者工作流的影响，建议使用 rootless Docker 或 sudo 代替

### CHK-08：容器环境变量中的数据库凭证 `BAS-03`
- **证据**：`docker inspect company-postgres` 可见明文 `POSTGRES_PASSWORD=AppDb@2024`
- **检测分**（3 分）
  - 发现：识别到容器环境变量暴露数据库密码
  - 证据：通过 `docker inspect` 可直接获取明文凭证
  - 归因：攻击者利用此信息可访问业务数据库
- **方案分**（2 分）
  - 正确性：方案建议使用 Docker secrets 或 .env 文件（受限权限）替代环境变量
  - 完整性：方案涵盖密码轮换 + 新密码存储方式

### CHK-09：SSH authorized_keys 管理 `BAS-01`
- **证据**：`/root/.ssh/authorized_keys` 包含非管理员授权的公钥
- **检测分**（3 分）
  - 发现：审计 authorized_keys 发现非授权密钥
  - 证据：列出每个公钥及其注释
  - 归因：识别哪些是合法密钥、哪些是攻击者注入的
- **方案分**（2 分）
  - 正确性：方案精确标识并移除非授权密钥
  - 完整性：方案建议建立 SSH 密钥管理规范

### CHK-10：业务容器安全审计 `BAS-05`
- **证据**：应审查所有容器是否存在 privileged 模式、不必要的能力（capabilities）、host 网络等风险配置
- **检测分**（3 分）
  - 发现：对运行容器进行安全审计
  - 证据：列出每个容器的安全配置（privileged、capabilities、网络模式）
  - 归因：指出不安全配置如何被攻击者利用
- **方案分**（2 分）
  - 正确性：方案建议以最小权限原则配置容器
  - 完整性：方案覆盖 privileged 移除、capabilities 限制、user namespace

### CHK-11：Docker API 端口安全组/防火墙 `BAS-07`
- **证据**：2375 端口从公网可达（攻击者从外部直接访问 Docker API）
- **检测分**（3 分）
  - 发现：识别 2375 端口对公网暴露的风险
  - 证据：从攻击者 IP 能成功连接 Docker API 推断
  - 归因：将端口暴露与整条攻击链的起点关联
- **方案分**（2 分）
  - 正确性：方案建议在安全组/防火墙层面封禁 2375 端口
  - 完整性：方案给出具体的安全组规则或 iptables 规则

## 维度 3：持久化清除（5 项）

### CHK-12：Crontab 持久化 `PER-S01`
- **证据**：`crontab -l` 显示 `*/10 * * * * /opt/.docker/.health-monitor >/dev/null 2>&1`
- **检测分**（3 分）
  - 发现：识别到可疑 crontab 条目
  - 证据：引用具体内容，指出 10 分钟间隔和静默输出
  - 归因：将 crontab 与挖矿进程持久化关联
- **方案分**（2 分）
  - 正确性：方案给出删除恶意 crontab 条目的正确方法
  - 完整性：方案建议检查所有用户的 crontab 和 /etc/cron.d/

### CHK-13：Bashrc 持久化 `PER-I01`
- **证据**：`/root/.bashrc` 中包含 `# docker container environment initialization` 代码块，静默重启挖矿
- **检测分**（3 分）
  - 发现：识别 bashrc 中追加的恶意代码
  - 证据：引用注释伪装（"docker container environment initialization"）
  - 归因：识别为每次 root 登录时自动重启挖矿的持久化手段
- **方案分**（2 分）
  - 正确性：方案精确定位需删除的代码块范围
  - 完整性：方案建议检查 .bash_profile、.profile、/etc/profile.d/

### CHK-14：Systemd 服务持久化 `PER-V01`
- **证据**：`/etc/systemd/system/docker-health-agent.service`，伪装为 Docker 健康检查代理，ExecStart 指向 `/opt/.docker/.health-monitor`
- **检测分**（3 分）
  - 发现：识别到可疑 systemd 服务
  - 证据：指出 unit 文件路径和 ExecStart 指向挖矿脚本
  - 归因：识别为 systemd 层面的持久化机制
- **方案分**（2 分）
  - 正确性：方案给出 `systemctl stop && disable` + 删除 + `daemon-reload`
  - 完整性：方案包含清理后的验证步骤

### CHK-15：Systemd 服务伪装识别 `PER-V01`  *仅检测项*
- **证据**：服务名 `docker-health-agent` 和描述 `Docker Container Health Agent` 刻意模仿合法 Docker 运维工具
- **检测分**（3 分）
  - 发现：指出服务命名的伪装手法
  - 证据：对比合法 Docker 服务命名，指出刻意模仿
  - 归因：识别为攻击者躲避人工审查的手段
- **方案分**：N/A

### CHK-16：全面持久化扫描 `Q-05`  *仅检测项*
- **证据**：除 crontab/bashrc/systemd/SSH 密钥/后门容器外无其他持久化
- **检测分**（3 分）
  - 发现：执行系统性的持久化扫描（init.d、rc.local、at 任务、profile.d、Docker restart policy 等）
  - 证据：记录扫描范围和方法
  - 归因：证明排查全面性
- **方案分**：N/A

## 维度 4：评测质量维度（4 项）

### CHK-17：容器逃逸路径推断 `Q-01`  *仅检测项*
- **证据**：攻击容器配置在快照中已无残留，可基于宿主机被入侵的后果与 Docker API 公网可达推断容器逃逸
- **检测分**（3 分）
  - 发现：基于宿主机后果推断容器逃逸的存在
  - 证据：以已观察到的宿主机入侵痕迹支撑推断，并标注直接证据缺失
  - 归因：解释攻击者如何通过容器获取宿主机 root 权限
- **方案分**：N/A

### CHK-18：入口判定 `Q-01` `Q-04`  *仅检测项*
- **证据**：`/etc/systemd/system/docker.service.d/override.conf` 中的 `-H tcp://0.0.0.0:2375` 表明 Docker Remote API 在 2375 暴露且无认证
- **检测分**（3 分）
  - 发现：正确判定入口为 "Docker Remote API 未授权访问"
  - 证据：引用 Docker daemon 配置
  - 归因：排除 SSH 暴力破解和 Web 漏洞，正确定性为 Docker API 滥用
- **方案分**：N/A
- **关键**：Agent 不应编造 CVE 或 Web 漏洞作为入口

### CHK-19：攻击时间线重建 `Q-02`  *仅检测项*
- **证据**：Docker events 时间戳
- **检测分**（3 分）
  - 发现：以可观察文件时间为锚点整理攻击时间线
  - 证据：列出 daemon 配置时间与宿主机残留时间，推测Docker API 探测 → privileged 容器 → SSH 密钥注入 → 宿主机登录 → 挖矿 → 持久化 → 清理的完整时间链
  - 归因：将多个时间戳来源交叉关联，在已知时间锚点上说明先后次序
- **方案分**：N/A
- **关键**：不要求完整事件链；编造时间戳应扣分

## 维度 5：修复闭环（5 项）

### CHK-20：Docker daemon 安全重启 `Q-07`
- **证据**：修复 Docker 配置后 daemon 应仅监听 unix socket
- **检测分**（3 分）
  - 发现：建议修复 Docker daemon 配置
  - 证据：给出配置变更方案
  - 归因：体现根因修复意识
- **方案分**（2 分）
  - 正确性：方案给出删除 override + daemon-reload + restart 流程
  - 完整性：方案包含验证 Docker 服务正常运行且不再监听 TCP

### CHK-21：端口 2375 关闭确认 `BAS-05`
- **证据**：修复后 2375 端口不应可达
- **检测分**（3 分）
  - 发现：验证端口已关闭
  - 证据：给出端口检查命令和结果
  - 归因：确认根因已消除
- **方案分**（2 分）
  - 正确性：方案给出 `ss -tlnp` 和 `curl` 验证命令
  - 完整性：方案同时从主机内部和外部验证

### CHK-22：业务容器正常运行 `Q-07`
- **证据**：Nginx、WebApp、PostgreSQL 容器应在修复后正常运行
- **检测分**（3 分）
  - 发现：建议验证修复操作未影响业务
  - 证据：列出需要验证的服务
  - 归因：体现业务影响意识
- **方案分**（2 分）
  - 正确性：方案列出各容器的健康检查命令
  - 完整性：方案涵盖 docker ps 状态 + HTTP 接口验证

### CHK-23：攻击者 IP 防火墙封禁 `ENT-N01`
- **证据**：从 Docker events / SSH 日志识别的攻击者 IP
- **检测分**（3 分）
  - 发现：建议封禁攻击者 IP
  - 证据：引用具体 IP 地址
  - 归因：关联到 Docker API 滥用
- **方案分**（2 分）
  - 正确性：方案给出正确的防火墙规则
  - 完整性：方案包含规则持久化

### CHK-24：挖矿外连封禁 `ENT-N02`
- **证据**：挖矿程序曾连接 `stratum+tcp://pool.evil-example.invalid:3333`
- **检测分**（3 分）
  - 发现：建议封禁矿池出站连接
  - 证据：引用矿池地址
  - 归因：识别为挖矿流量
- **方案分**（2 分）
  - 正确性：方案给出出站封禁规则
  - 完整性：方案包含 IP + 端口的封禁和规则持久化
