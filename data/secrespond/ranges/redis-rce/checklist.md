# range-redis-rce 检查清单

评估的评分标准（ground truth）。每个检查点拆分为检测分、方案分两个独立评分维度。

- **检测分**（满分 3 分）：发现(1) + 证据(1) + 归因(1) — 评判检测 Agent 的分析报告 — LLM-as-a-Judge
- **方案分**（满分 2 分）：正确性(1) + 完整性(1) — 评判检测 Agent 输出的修复方案 — LLM-as-a-Judge
- **仅检测项**：方案分标记 N/A，不参与对应汇总

## 维度 1：入侵实体识别与处置（4 项）

### CHK-01：挖矿进程检测 `ENT-P01`
- **证据**：进程 `/var/tmp/.redis-bgsave` 正在运行，或存在日志 `/var/tmp/.redis-bgsave.log`
- **检测分**（3 分）
  - 发现：识别到挖矿进程存在
  - 证据：指出路径 `/var/tmp/.redis-bgsave`，识别伪装名称（.redis-bgsave 模仿 Redis 后台保存进程）
  - 归因：将挖矿进程与攻击者入侵后的牟利行为关联
- **方案分**（2 分）
  - 正确性：方案给出正确的进程终止命令
  - 完整性：方案涵盖终止进程 + 删除二进制文件和日志 + 检查守护机制

### CHK-02：挖矿二进制文件清理 `ENT-F02`
- **证据**：文件 `/var/tmp/.redis-bgsave` 存在
- **检测分**（3 分）
  - 发现：识别到恶意文件
  - 证据：指出文件路径和类型
  - 归因：将其与挖矿行为关联
- **方案分**（2 分）
  - 正确性：方案给出正确的删除命令
  - 完整性：方案建议检查 /var/tmp、/tmp 等位置是否有副本

### CHK-03：攻击者 SSH 公钥识别 `ENT-F04`
- **证据**：`/root/.ssh/authorized_keys` 中包含 `attacker@redis-pwned` 注释的公钥，且文件含 Redis RDB 序列化二进制数据
- **检测分**（3 分）
  - 发现：发现异常的 SSH 公钥条目
  - 证据：指出公钥注释 `attacker@redis-pwned` + authorized_keys 文件包含非正常的二进制前缀（Redis RDB 特征）
  - 归因：识别出 SSH 公钥是通过 Redis 未授权访问写入的（非手动添加）
- **方案分**（2 分）
  - 正确性：方案建议删除攻击者公钥
  - 完整性：方案说明需重建 authorized_keys（整个文件被 Redis RDB 格式污染，不能只删一行）

### CHK-04：Redis 写入的 crontab 残留 `ENT-F04`
- **证据**：`/var/spool/cron/crontabs/root` 包含 Redis RDB 二进制数据 + 挖矿 crontab 条目
- **检测分**（3 分）
  - 发现：发现异常的 crontab 文件
  - 证据：指出文件含 RDB 二进制垃圾数据，非正常 crontab 格式
  - 归因：识别为 Redis CONFIG SET + SAVE 写入的文件（与 authorized_keys 同一攻击手法）
- **方案分**（2 分）
  - 正确性：方案建议删除该文件或重建为空
  - 完整性：方案说明需同时检查 `crontab -l` 和文件系统层面

## 维度 2：基线风险（8 项）

### CHK-05：Redis bind 配置 `BAS-02`
- **证据**：`/etc/redis/redis.conf` 中 `bind 0.0.0.0`（监听所有接口）
- **检测分**（3 分）
  - 发现：识别到 Redis 监听所有网络接口
  - 证据：引用 redis.conf 中的 bind 配置
  - 归因：将其与攻击者能从外网访问 Redis 关联
- **方案分**（2 分）
  - 正确性：方案建议改为 `bind 127.0.0.1`
  - 完整性：方案考虑了应用层面的影响（如其他服务依赖 Redis 网络访问）

### CHK-06：Redis requirepass `BAS-02`
- **证据**：Redis 未设置 requirepass（无认证即可执行任意命令）
- **检测分**（3 分）
  - 发现：识别到 Redis 无密码保护
  - 证据：`redis-cli CONFIG GET requirepass` 返回空
  - 归因：将无密码与攻击者能执行 CONFIG SET 等危险命令关联
- **方案分**（2 分）
  - 正确性：方案建议设置 requirepass 为强密码
  - 完整性：方案包含客户端连接更新和密码复杂度要求

### CHK-07：Redis protected-mode `BAS-02`
- **证据**：`protected-mode no` 关闭了 Redis 自身的安全防护
- **检测分**（3 分）
  - 发现：识别到 protected-mode 被禁用
  - 证据：引用 redis.conf 配置
  - 归因：将其与 Redis 未授权访问能力关联
- **方案分**（2 分）
  - 正确性：方案建议开启 protected-mode
  - 完整性：方案说明 protected-mode 与 requirepass 的组合使用

### CHK-08：Redis 运行用户 `BAS-02`
- **证据**：Redis 以 root 身份运行（`ps -o user= -p $(pgrep redis-server)` 返回 root）
- **检测分**（3 分）
  - 发现：识别到 Redis 以 root 运行的严重风险
  - 证据：进程信息显示运行用户为 root
  - 归因：指出 root 运行是攻击者能写入 /root/.ssh/ 的关键前提
- **方案分**（2 分）
  - 正确性：方案建议改为 redis 专用用户运行
  - 完整性：方案包含文件权限修改和 systemd service 用户配置

### CHK-09：Redis rename-command `BAS-02`
- **证据**：CONFIG、SAVE、FLUSHALL 等危险命令未被限制
- **检测分**（3 分）
  - 发现：识别到危险命令未限制
  - 证据：可直接远程执行 CONFIG SET
  - 归因：指出 CONFIG/SAVE 命令是写入 SSH 密钥和 crontab 的核心
- **方案分**（2 分）
  - 正确性：方案建议使用 rename-command 重命名或禁用危险命令
  - 完整性：方案列出需限制的命令清单（CONFIG、SAVE、BGSAVE、FLUSHALL、DEBUG）

### CHK-10：SSH PermitRootLogin `BAS-01`
- **证据**：`/etc/ssh/sshd_config` 中 `PermitRootLogin yes`
- **检测分**（3 分）
  - 发现：识别到 root 直接 SSH 登录的风险
  - 证据：引用 sshd_config 配置
  - 归因：将其与攻击者通过 SSH 密钥直接登录 root 关联
- **方案分**（2 分）
  - 正确性：方案建议改为 `no` 或 `prohibit-password`
  - 完整性：方案包含 `sshd -t` 验证和 sshd 重启

### CHK-11：deploy 的 sudoers NOPASSWD `BAS-04`
- **证据**：`/etc/sudoers.d/deploy` 授予了 `NOPASSWD: ALL`
- **检测分**（3 分）
  - 发现：识别到过于宽松的 sudo 权限
  - 证据：引用 sudoers 文件内容
  - 归因：指出攻击者可借此提权
- **方案分**（2 分）
  - 正确性：方案建议限制到特定命令或移除 NOPASSWD
  - 完整性：方案包含 `visudo -c` 验证

### CHK-12：bash_history 中的 Redis 会话凭证 `BAS-03`
- **证据**：`/home/deploy/.bash_history` 中包含 Redis SET 命令泄露的会话 token（`session:admin ... s3cr3tK3y!2024`）
- **检测分**（3 分）
  - 发现：识别到 shell 历史中的敏感信息
  - 证据：引用具体历史记录行
  - 归因：指出凭证泄露可被攻击者利用
- **方案分**（2 分）
  - 正确性：方案建议清除敏感历史行
  - 完整性：方案建议使用 Redis ACL 或应用层认证代替明文命令行操作

## 维度 3：持久化清除（5 项）

### CHK-13：~/.ssh/rc 持久化 `PER-I01`
- **证据**：`/root/.ssh/rc` 含伪装为 "Redis connection health check" 的代码，实际在 SSH 登录时静默启动挖矿程序
- **检测分**（3 分）
  - 发现：识别到 SSH rc 文件中的恶意代码
  - 证据：引用 /root/.ssh/rc 内容和伪装注释
  - 归因：识别为 SSH 登录时自动执行的持久化机制（区别于 bashrc/profile.d）
- **方案分**（2 分）
  - 正确性：方案给出删除 /root/.ssh/rc 的命令
  - 完整性：方案建议检查其他用户的 ~/.ssh/rc

### CHK-14：init.d 恶意脚本 `PER-V01`
- **证据**：`/etc/init.d/redis-watchdog` — 伪装为 Redis 健康监控守护进程，实际启动挖矿程序
- **检测分**（3 分）
  - 发现：识别到可疑 init.d 脚本
  - 证据：指出脚本路径和实际执行内容（指向 /var/tmp/.redis-bgsave）
  - 归因：识别为 init.d 层面的持久化（开机自启）
- **方案分**（2 分）
  - 正确性：方案给出移除脚本 + `update-rc.d remove` 命令
  - 完整性：方案包含清理后的验证步骤

### CHK-15：init.d 服务伪装识别 `PER-V01`  *仅检测项*
- **证据**：脚本名称 `redis-watchdog` 和描述 "Redis health monitoring daemon" 模仿合法运维工具
- **检测分**（3 分）
  - 发现：指出服务名称和 LSB 描述的伪装手法
  - 证据：对比合法 Redis 组件命名（redis-server、redis-sentinel），指出 redis-watchdog 不是官方组件
  - 归因：识别为攻击者通过命名伪装躲避审查
- **方案分**：N/A（实际处置由 CHK-14 覆盖）

### CHK-16：Redis 写入的 crontab 文件特征识别 `PER-S01`  *仅检测项*
- **证据**：`/var/spool/cron/crontabs/root` 文件以 Redis RDB 格式 header 开头（而非正常 crontab 文本）
- **检测分**（3 分）
  - 发现：识别到 crontab 文件格式异常
  - 证据：指出文件含二进制数据（Redis RDB 特征），非正常 crontab 格式
  - 归因：判定为 Redis CONFIG SET dir + SAVE 攻击手法写入
- **方案分**：N/A（实际处置由 CHK-04 覆盖）
- **加分项**：Agent 将 crontab 的 RDB 特征与 authorized_keys 的 RDB 特征关联分析

### CHK-17：全面的持久化扫描 `Q-05`  *仅检测项*
- **证据**：除 ~/.ssh/rc、init.d、crontab 外无其他持久化机制
- **检测分**（3 分）
  - 发现：执行系统性的持久化扫描（systemd、profile.d、bashrc、at 任务等）
  - 证据：记录扫描范围和方法
  - 归因：即使未发现额外项目，证明排查的全面性
- **方案分**：N/A

## 维度 4：评测质量维度（4 项）

### CHK-18：Redis 未授权访问证据 `Q-02` `Q-03`  *仅检测项*
- **证据**：
  - Redis 日志（部分清理后仍可能有连接记录）
  - authorized_keys 中的 Redis RDB 二进制特征
  - crontab 文件中的 Redis RDB 特征
  - Redis CONFIG 状态（bind/protected-mode/requirepass）
- **检测分**（3 分）
  - 发现：从多个数据源交叉验证 Redis 被利用
  - 证据：关联 authorized_keys RDB 特征 + crontab RDB 特征 + Redis 弱配置
  - 归因：综合证据建立 Redis 未授权访问 → SSH 密钥注入的完整攻击链
- **方案分**：N/A

### CHK-19：攻击者 IP 识别 `Q-03`  *仅检测项*
- **证据**：Redis 日志中的客户端连接 IP；SSH auth.log 中密钥登录的源 IP
- **检测分**（3 分）
  - 发现：识别出攻击者的源 IP
  - 证据：引用具体日志行和 IP
  - 归因：将该 IP 与 Redis 访问和 SSH 登录关联
- **方案分**：N/A

### CHK-20：入口判定 `Q-01` `Q-04`  *仅检测项*
- **证据**：Redis 未授权访问（CONFIG SET 写文件），不是 SSH 暴力破解、不是 CVE 利用
- **检测分**（3 分）
  - 发现：正确判定入口为 "Redis 未授权访问"
  - 证据：引用 Redis 弱配置 + authorized_keys RDB 特征 + 无暴力破解日志
  - 归因：排除 SSH 暴力破解（无 Failed password 日志）和 CVE（无漏洞利用痕迹）
- **方案分**：N/A
- **关键**：Agent 不应编造 CVE 或将其误判为 SSH 暴力破解

### CHK-21：攻击时间线重建 `Q-02`  *仅检测项*
- **证据**：Redis 日志时间戳、SSH auth.log 密钥登录时间、文件 mtime/ctime（注意挖矿文件的 mtime 被 touch -r 伪造，需对比 ctime）
- **检测分**（3 分）
  - 发现：构建出连贯的攻击时间线
  - 证据：Redis 访问 → SSH 密钥登录 → 挖矿部署 → 持久化安装
  - 归因：将多个时间戳来源交叉关联
- **方案分**：N/A
- **加分项**：Agent 识别到挖矿文件的 mtime 被 `touch -r` 伪造（mtime 与 redis-server 一致但 ctime 为攻击时间）

## 维度 5：修复闭环（4 项）

### CHK-22：Redis 加固验证 `Q-07`
- **证据**：Redis 配置变更后
- **检测分**（3 分）
  - 发现：建议验证 Redis 加固效果
  - 证据：说明需验证 bind + requirepass + protected-mode + 运行用户 + rename-command 五项
  - 归因：体现修复操作的完整性
- **方案分**（2 分）
  - 正确性：方案给出 Redis 加固后的验证命令
  - 完整性：方案包含重启 Redis 后再次验证配置生效

### CHK-23：6379 端口访问限制 `BAS-07`
- **证据**：Redis 6379 端口对公网开放（攻击者从外网直接连接成功可推知）
- **检测分**（3 分）
  - 发现：识别到 Redis 端口对公网无限制开放
  - 证据：攻击者从外网直接执行 Redis 命令
  - 归因：将端口暴露与 Redis 未授权访问攻击面关联
- **方案分**（2 分）
  - 正确性：方案建议防火墙限制 6379 端口
  - 完整性：方案给出具体的安全组/iptables 规则

### CHK-24：服务重启与验证 `Q-07`
- **证据**：Redis、Nginx、SSH 在修复后应正常运行
- **检测分**（3 分）
  - 发现：建议验证加固操作未影响业务服务
  - 证据：列出需要验证的关键服务
  - 归因：体现业务影响意识
- **方案分**（2 分）
  - 正确性：方案列出关键服务状态检查命令
  - 完整性：方案涵盖 Redis、Nginx、SSH 三个服务
