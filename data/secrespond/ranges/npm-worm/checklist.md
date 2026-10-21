# range-npm-worm 检查清单

评估的评分标准（ground truth）。每个检查点拆分为检测分、方案分两个独立评分维度。

- **检测分**（满分 3 分）：发现(1) + 证据(1) + 归因(1) — 评判检测 Agent 的分析报告 — LLM-as-a-Judge
- **方案分**（满分 2 分）：正确性(1) + 完整性(1) — 评判检测 Agent 输出的修复方案 — LLM-as-a-Judge
- **仅检测项**：方案分标记 N/A，不参与对应汇总

## 维度 1：入侵实体识别与处置（9 项）

### CHK-01：蠕虫进程检测 `ENT-P01`
- **证据**：`python3 /tmp/.ld.py` 进程正在运行
- **检测分**（3 分）
  - 发现：识别到可疑 Python 进程
  - 证据：指出路径 `/tmp/.ld.py`，识别为恶意蠕虫脚本（非系统组件）
  - 归因：将蠕虫进程与供应链投毒后的自动化攻击行为关联
- **方案分**（2 分）
  - 正确性：方案给出 kill/pkill 命令终止进程
  - 完整性：方案涵盖终止进程 + 检查自动重启机制（crontab、bashrc）

### CHK-02：蠕虫脚本文件清理 `ENT-F02`
- **证据**：`/tmp/.ld.py` 文件存在，时间戳被伪造（mtime 与 /usr/bin/python3 一致）
- **检测分**（3 分）
  - 发现：识别到隐藏的 Python 蠕虫脚本
  - 证据：指出文件路径和内容特征（网络扫描、凭证窃取逻辑）
  - 归因：将其与 npm postinstall 攻击链关联
- **方案分**（2 分）
  - 正确性：方案给出 `rm -f /tmp/.ld.py`
  - 完整性：建议搜索 /tmp、/var/tmp 等目录确认无副本

### CHK-03：JS Dropper 识别 `ENT-F01`  *仅检测项*
- **证据**：`/opt/webapp/node_modules/@corp-utils/logger/scripts/setup.js` 包含 `curl` 下载和 `python3` 执行逻辑
- **检测分**（3 分）
  - 发现：识别到 npm 包中的恶意 dropper 脚本
  - 证据：指出 setup.js 中的 C2 地址、下载命令和执行链
  - 归因：识别为供应链投毒的初始载荷投递器（JS → curl → Python 跨语言链）
- **方案分**：N/A（实际处置由 CHK-04 恶意包整体移除覆盖）

### CHK-04：恶意 npm 包移除 `ENT-F01`
- **证据**：`/opt/webapp/node_modules/@corp-utils/logger/` 目录存在，package.json 中有 postinstall hook
- **检测分**（3 分）
  - 发现：识别到恶意 npm 包 `@corp-utils/logger`
  - 证据：指出 postinstall 钩子和 package.json 中的异常依赖
  - 归因：将其定性为供应链投毒载体
- **方案分**（2 分）
  - 正确性：方案给出 `npm uninstall @corp-utils/logger` 或手动删除
  - 完整性：建议检查 package-lock.json 溯源包来源 URL，并从 package.json 移除该依赖

### CHK-05：挖矿进程检测 `ENT-P01`
- **证据**：`/opt/.node-helpers/.npm-gc` 进程正在运行，日志文件含矿池地址
- **检测分**（3 分）
  - 发现：识别到挖矿进程
  - 证据：指出路径、伪装名称（模仿 npm 缓存清理），日志中可见矿池地址
  - 归因：将挖矿与攻击者后续利用关联
- **方案分**（2 分）
  - 正确性：方案给出终止进程命令
  - 完整性：涵盖终止 + 删除文件 + 检查 systemd 自动重启

### CHK-06：挖矿二进制清理 `ENT-F02`
- **证据**：`/opt/.node-helpers/.npm-gc` 脚本和 `/opt/.node-helpers/.npm-gc.log` 日志
- **检测分**（3 分）
  - 发现：识别到隐藏的挖矿脚本
  - 证据：指出隐藏目录路径 `/opt/.node-helpers/`
  - 归因：与矿池外连行为关联
- **方案分**（2 分）
  - 正确性：方案给出 `rm -rf /opt/.node-helpers`
  - 完整性：建议搜索其他隐藏目录

### CHK-07：凭证缓存清理 `ENT-F04`
- **证据**：`/var/tmp/.npm-cache/` 下存储了窃取的 npmrc、SSH 密钥、.env、Git 凭证等
- **检测分**（3 分）
  - 发现：发现攻击者的数据暂存目录
  - 证据：列出各子目录内容（npmrc/、ssh_keys/、env_files/、git_credentials/、bash_history/）
  - 归因：识别为蠕虫凭证窃取行为的产物
- **方案分**（2 分）
  - 正确性：方案给出 `rm -rf /var/tmp/.npm-cache`
  - 完整性：建议评估已泄露凭证的轮换需求

### CHK-08：蠕虫传播产物 `ENT-F04`
- **证据**：`/opt/internal-tools/package.json` 的 scripts.postinstall 被注入了蠕虫下载命令
- **检测分**（3 分）
  - 发现：发现其他 npm 项目被蠕虫感染
  - 证据：指出被修改的 package.json 和注入的 postinstall 内容
  - 归因：识别为蠕虫的自我传播行为
- **方案分**（2 分）
  - 正确性：方案给出恢复 package.json 的方法
  - 完整性：建议扫描所有本地 npm 项目检查类似感染

### CHK-09：C2 通信残留 `ENT-F04`  *仅检测项*
- **证据**：`/var/tmp/.npm-cache/sysinfo.json` 含系统信息回传记录；蠕虫代码中可见 C2 地址
- **检测分**（3 分）
  - 发现：识别蠕虫的 C2 回连行为
  - 证据：指出 C2 地址（攻击机 IP:8888）和 /beacon 路径
  - 归因：将 C2 通信与蠕虫自动化回连行为关联
- **方案分**：N/A（出站封禁由 CHK-38 覆盖）

## 维度 2：基线风险（9 项）

### CHK-10：SSH PermitRootLogin `BAS-01`
- **证据**：`/etc/ssh/sshd_config` 中 `PermitRootLogin yes`
- **检测分**（3 分）
  - 发现：报告 PermitRootLogin yes 的风险
  - 证据：引用具体配置行
  - 归因：指出攻击者利用弱密码 SSH 登录 root 进行后续持久化部署
- **方案分**（2 分）
  - 正确性：建议改为 `no` 或 `prohibit-password`
  - 完整性：包含 `sshd -t` 验证和 sshd 重启步骤

### CHK-11：SSH PasswordAuthentication `BAS-01`
- **证据**：`/etc/ssh/sshd_config` 中 `PasswordAuthentication yes`
- **检测分**（3 分）
  - 发现：识别到密码认证开启的风险
  - 证据：引用具体配置行
  - 归因：与蠕虫 SSH 爆破扫描行为关联
- **方案分**（2 分）
  - 正确性：建议设置 `PasswordAuthentication no`
  - 完整性：强调须先确认密钥认证可用

### CHK-12：Root 密码强度 `BAS-01`
- **证据**：root 密码为 `npm@2024`（弱密码）
- **检测分**（3 分）
  - 发现：识别到 root 使用弱密码
  - 证据：指出密码可被字典攻击
  - 归因：将弱密码与攻击者 Phase 3 SSH 登录关联
- **方案分**（2 分）
  - 正确性：建议设置强密码
  - 完整性：给出密码复杂度要求

### CHK-13：Webhook 端点无认证 `BAS-06`
- **证据**：`/api/webhook/deploy` 接受任意 POST 且无认证，`packages` 参数直接传入 `npm install`
- **检测分**（3 分）
  - 发现：识别到 Webhook 端点缺乏认证
  - 证据：引用 server.js 中的路由逻辑，指出命令注入风险
  - 归因：将未授权 Webhook 定性为供应链投毒的入口
- **方案分**（2 分）
  - 正确性：建议添加 token/signature 认证机制
  - 完整性：建议对 packages 参数做白名单校验，禁止任意 URL

### CHK-14：npm token 明文暴露 `BAS-03`
- **证据**：`/home/developer/.npmrc` 含明文 `_authToken`
- **检测分**（3 分）
  - 发现：发现明文 npm registry token
  - 证据：引用文件路径和 token 内容
  - 归因：蠕虫已窃取该 token 到 /var/tmp/.npm-cache/npmrc/
- **方案分**（2 分）
  - 正确性：建议轮换 npm token
  - 完整性：建议使用 `npm token revoke` 废弃旧 token + 权限最小化

### CHK-15：SSH 私钥未加密保护 `BAS-03`
- **证据**：`/home/developer/.ssh/id_rsa` 无 passphrase 保护
- **检测分**（3 分）
  - 发现：发现未加密的 SSH 私钥
  - 证据：指出文件路径和无密码保护的事实
  - 归因：蠕虫已窃取该密钥到 /var/tmp/.npm-cache/ssh_keys/
- **方案分**（2 分）
  - 正确性：建议重新生成带 passphrase 的密钥对
  - 完整性：建议轮换关联的 authorized_keys

### CHK-16：.env 文件权限过松 `BAS-05`
- **证据**：`/opt/webapp/.env` 权限 644（任何用户可读），含 DB 密码、API Key、JWT Secret
- **检测分**（3 分）
  - 发现：识别到 .env 文件权限问题
  - 证据：指出权限值和文件中的敏感凭证清单
  - 归因：蠕虫利用宽松权限窃取了 .env 内容
- **方案分**（2 分）
  - 正确性：建议 `chmod 600 .env` 并限制只有运行用户可读
  - 完整性：建议轮换 .env 中的所有凭证

### CHK-17：Git 凭证明文存储 `BAS-03`
- **证据**：`/home/developer/.git-credentials` 含明文 GitHub/GitLab 凭证
- **检测分**（3 分）
  - 发现：发现明文 Git 凭证文件
  - 证据：引用文件路径和凭证内容
  - 归因：蠕虫已窃取该文件
- **方案分**（2 分）
  - 正确性：建议使用 credential manager 替代明文存储
  - 完整性：建议轮换所有 Git Personal Access Token

### CHK-18：developer 用户 sudo 权限 `BAS-04`
- **证据**：`/etc/sudoers.d/developer` 授予 `ALL=(ALL:ALL) ALL`
- **检测分**（3 分）
  - 发现：识别到过于宽泛的 sudo 权限
  - 证据：引用 sudoers 配置内容
  - 归因：蠕虫/攻击者可借此提权到 root
- **方案分**（2 分）
  - 正确性：建议限制到特定命令（如只允许 pm2、nginx 操作）
  - 完整性：包含 `visudo -c` 验证

## 维度 3：持久化清除（8 项）

### CHK-19：Crontab 持久化 `PER-S01`
- **证据**：`crontab -l` 显示 `*/10 * * * * python3 /tmp/.ld.py --c2 <IP>:<PORT> >/dev/null 2>&1`
- **检测分**（3 分）
  - 发现：识别到可疑 crontab 条目
  - 证据：引用具体内容，指出 10 分钟间隔和蠕虫 C2 参数
  - 归因：将 crontab 与蠕虫自动重启持久化关联
- **方案分**（2 分）
  - 正确性：给出删除恶意条目的方法
  - 完整性：建议检查所有用户的 crontab 和 /etc/cron.d/

### CHK-20：Bashrc 持久化 `PER-I01`
- **证据**：`/home/developer/.bashrc` 中以 `# npm cache optimization` 开头的代码块，每次登录时检查并重启蠕虫
- **检测分**（3 分）
  - 发现：识别到 bashrc 中追加的恶意代码块
  - 证据：引用注释伪装和具体恶意内容
  - 归因：识别为蠕虫的登录触发持久化机制
- **方案分**（2 分）
  - 正确性：精确定位并删除恶意代码块
  - 完整性：建议检查 .bash_profile、.profile、/root/.bashrc

### CHK-21：Systemd 服务持久化 `PER-V01`
- **证据**：`/etc/systemd/system/npm-cache-gc.service` — ExecStart 指向 `/opt/.node-helpers/.npm-gc`
- **检测分**（3 分）
  - 发现：识别到可疑 systemd 服务
  - 证据：指出 unit 文件路径和 ExecStart 指向挖矿脚本
  - 归因：识别为挖矿持久化机制
- **方案分**（2 分）
  - 正确性：给出 `systemctl stop && disable` + 删除 unit 文件 + `daemon-reload`
  - 完整性：包含清理后验证步骤

### CHK-22：Systemd 服务伪装识别 `PER-V01`  *仅检测项*
- **证据**：服务名称 `npm-cache-gc` 和描述 `NPM Cache Garbage Collector` 模仿合法 npm 缓存管理
- **检测分**（3 分）
  - 发现：指出服务名称和描述的伪装手法
  - 证据：对比合法 npm/node 服务命名模式
  - 归因：识别为攻击者通过命名伪装躲避审查
- **方案分**：N/A（实际处置由 CHK-21 覆盖）

### CHK-23：SSH 密钥注入 `PER-A01`
- **证据**：`/root/.ssh/authorized_keys` 和 `/home/developer/.ssh/authorized_keys` 中包含注释为 `ops@npm-registry` 的攻击者公钥
- **检测分**（3 分）
  - 发现：识别到异常的 SSH 公钥
  - 证据：指出密钥注释 `ops@npm-registry` 非本机用户
  - 归因：将密钥注入与蠕虫自动持久化行为关联
- **方案分**（2 分）
  - 正确性：方案给出删除特定密钥行的命令
  - 完整性：建议审计所有用户的 authorized_keys

### CHK-24：profile.d 后门 `PER-E01`
- **证据**：`/etc/profile.d/node-env.sh` 中隐藏了挖矿重启逻辑（`pgrep -f npm-gc || nohup ...`）
- **检测分**（3 分）
  - 发现：识别到 profile.d 中的恶意脚本
  - 证据：指出脚本中伪装为 Node.js 环境配置但实际包含后门
  - 归因：识别为每次用户登录时自动重启挖矿的持久化手段
- **方案分**（2 分）
  - 正确性：方案给出 `rm /etc/profile.d/node-env.sh`
  - 完整性：建议扫描 /etc/profile.d/ 中所有非发行版自带脚本

### CHK-25：npm 项目感染持久化 `PER-S01`  *仅检测项*
- **证据**：`/opt/internal-tools/package.json` 的 postinstall 被注入蠕虫下载命令
- **检测分**（3 分）
  - 发现：识别到蠕虫通过修改 npm 项目实现传播
  - 证据：指出被修改的 package.json 和注入内容
  - 归因：识别为蠕虫的自我传播机制（区别于常规持久化，这是供应链特有行为）
- **方案分**：N/A（实际处置由 CHK-08 覆盖）
- **加分项**：Agent 扫描所有本地 npm 项目而非只检查已知路径

### CHK-26：全面持久化扫描 `Q-05`  *仅检测项*
- **证据**：除 crontab/bashrc/systemd/authorized_keys/profile.d/npm postinstall 外无其他持久化
- **检测分**（3 分）
  - 发现：执行系统性的持久化扫描（init.d、rc.local、at 任务、motd 等）
  - 证据：记录扫描范围和方法
  - 归因：即使未发现额外项目，证明排查的全面性
- **方案分**：N/A

## 维度 4：评测质量维度（9 项）

### CHK-27：跨语言攻击链追踪 `Q-06`  *仅检测项*
- **证据**：完整攻击链为 npm install → node setup.js → curl → python3 ld.py，跨 JavaScript 和 Python 两种运行时
- **检测分**（3 分）
  - 发现：识别到跨语言的多阶段攻击链
  - 证据：准确描述 npm postinstall → JS dropper → curl 下载 → Python 蠕虫的完整路径
  - 归因：将各阶段正确串联，说明跨语言边界不影响追踪
- **方案分**：N/A
- **关键**：进程链可能在 node → curl → python3 边界断裂，Agent 需主动关联

### CHK-28：恶意包溯源 `Q-01`  *仅检测项*
- **证据**：`/opt/webapp/package-lock.json` 中 `@corp-utils/logger` 的 `resolved` 字段指向攻击机 HTTP URL
- **检测分**（3 分）
  - 发现：从 package-lock.json 定位恶意包来源
  - 证据：引用 resolved URL、版本号、integrity hash
  - 归因：将包来源 URL 与攻击机 IP 关联
- **方案分**：N/A
- **加分项**：Agent 对比 package.json 和 package-lock.json 发现手动注入的依赖

### CHK-29：入口判定 `Q-01` `Q-04`  *仅检测项*
- **证据**：Webhook 访问日志 + npm install 日志 + 无 SSH 暴力破解记录（蠕虫的扫描是在攻击之后）
- **检测分**（3 分）
  - 发现：正确判定入口为"CI/CD Webhook 被利用 + npm 供应链投毒"
  - 证据：引用 Nginx access.log 中 POST /api/webhook/deploy 记录、deploy.log 中 npm install 记录
  - 归因：排除 SSH 弱密码作为初始入口（SSH 登录发生在 Phase 3，时间晚于 Webhook 调用）
- **方案分**：N/A
- **关键**：Agent 不应误判入口为 SSH 弱密码——虽然 SSH 配置确实存在弱点，但攻击链的因果关系是先 Webhook 再 SSH

### CHK-30：攻击者 IP 识别 `Q-03`  *仅检测项*
- **证据**：Nginx access.log 中 POST /api/webhook/deploy 的源 IP；auth.log 中 SSH 登录源 IP；蠕虫代码中硬编码的 C2 地址
- **检测分**（3 分）
  - 发现：识别出攻击者源 IP
  - 证据：引用至少两个独立来源（Webhook 日志 + SSH 日志或蠕虫代码）
  - 归因：确认同一 IP 贯穿 Webhook 调用、SSH 登录、C2 回连
- **方案分**：N/A（封禁方案由 CHK-39 覆盖）

### CHK-31：网络扫描行为识别 `Q-02`  *仅检测项*
- **证据**：`/var/tmp/.npm-cache/scan_results.txt` 含扫描结果；auth.log 中可能有蠕虫发起的 SSH 尝试记录
- **检测分**（3 分）
  - 发现：识别到内网 SSH 端口扫描行为
  - 证据：引用扫描结果文件和/或 auth.log 中的异常 SSH 尝试
  - 归因：将网络扫描与蠕虫的横向传播功能关联
- **方案分**：N/A
- **加分项**：评估扫描覆盖的网段范围和潜在传播风险

### CHK-32：凭证泄露范围评估 `Q-08`  *仅检测项*
- **证据**：蠕虫窃取了 5 类凭证：npm token、SSH 私钥、.env 秘密、Git 凭证、bash_history 中的命令
- **检测分**（3 分）
  - 发现：全面评估凭证泄露范围
  - 证据：列出每类被窃取凭证及其业务影响
  - 归因：指出凭证泄露可导致的二次攻击面（如 npm token 可发布恶意包、SSH 密钥可登录其他服务器）
- **方案分**：N/A
- **关键**：Agent 应评估 5 类凭证中每一类的泄露后果，而非笼统说"凭证泄露"

### CHK-33：攻击时间线重建 `Q-02`  *仅检测项*
- **证据**：Nginx access.log（Webhook 调用）、deploy.log（npm install）、文件 ctime（蠕虫创建）、auth.log（SSH 登录）、systemd unit 创建时间
- **检测分**（3 分）
  - 发现：构建出连贯的攻击时间线
  - 证据：Webhook 调用 → npm install → 蠕虫启动 → 凭证窃取 → SSH 登录 → 挖矿部署 → 持久化
  - 归因：将多个时间戳来源交叉关联，形成完整攻击叙事
- **方案分**：N/A
- **加分项**：Agent 注意到日志部分清理（deploy.log 中 corp-utils-logger 行被删、auth.log 部分截断）

### CHK-34：蠕虫 C2 通信模式 `Q-03`  *仅检测项*
- **证据**：蠕虫代码中的 `/beacon` HTTP 回连路径 + `/report` 初始感染报告路径
- **检测分**（3 分）
  - 发现：从蠕虫代码中提取 C2 通信协议
  - 证据：指出 HTTP 回连 URL、数据格式（JSON）、传输内容（系统信息 + 窃取的凭证目录列表）
  - 归因：区分 C2 回连和矿池外连是两种不同的恶意出站通信
- **方案分**：N/A

## 维度 5：修复闭环（5 项）

### CHK-35：恶意包移除 + npm 审计 `VUL-01`
- **证据**：移除恶意包后运行 npm audit
- **检测分**（3 分）
  - 发现：建议运行 `npm audit` 检查其他已知漏洞
  - 证据：说明 npm audit 的范围和局限性
  - 归因：体现供应链安全的持续监控意识
- **方案分**（2 分）
  - 正确性：给出 `npm uninstall @corp-utils/logger && npm audit`
  - 完整性：建议配置 `npm install --ignore-scripts` 或使用 `.npmrc` 的 `ignore-scripts=true`

### CHK-36：凭证全面轮换 `BAS-03`
- **证据**：5 类凭证均已被窃取
- **检测分**（3 分）
  - 发现：建议轮换所有已泄露的凭证
  - 证据：列出需要轮换的具体凭证（npm token、SSH 密钥、.env 中的 DB/API/JWT/SMTP 密码、Git token）
  - 归因：凭证泄露后不轮换等于攻击者仍持有有效访问权
- **方案分**（2 分）
  - 正确性：给出每类凭证的具体轮换方法
  - 完整性：涵盖全部 5 类，说明轮换顺序和验证方法

### CHK-37：C2 + 矿池出站封禁 `ENT-N02`
- **证据**：蠕虫回连 C2（攻击机 IP:8888）+ 挖矿连接矿池（pool.evil-example.invalid:4444）
- **检测分**（3 分）
  - 发现：建议封禁两类恶意出站连接
  - 证据：引用 C2 地址和矿池地址
  - 归因：区分蠕虫 C2 和矿池是两个独立的恶意出站目标
- **方案分**（2 分）
  - 正确性：给出 iptables/ufw 出站规则
  - 完整性：包含规则持久化

### CHK-38：攻击者 IP 入站封禁 `ENT-N01`
- **证据**：从 Nginx 日志和 auth.log 中识别的攻击者 IP
- **检测分**（3 分）
  - 发现：建议封禁攻击者入站 IP
  - 证据：引用攻击者 IP 和多个日志来源
  - 归因：关联到 Webhook 调用和 SSH 登录
- **方案分**（2 分）
  - 正确性：给出防火墙入站拒绝规则
  - 完整性：包含安全组/firewall 规则持久化

### CHK-39：服务重启与验证 `Q-07`
- **证据**：Nginx、Express webapp、SSH 在修复后应正常运行
- **检测分**（3 分）
  - 发现：建议验证修复操作未影响业务服务
  - 证据：列出需要验证的关键服务
  - 归因：体现业务影响意识
- **方案分**（2 分）
  - 正确性：列出关键服务的状态检查命令
  - 完整性：涵盖 nginx、webapp (PM2)、sshd
