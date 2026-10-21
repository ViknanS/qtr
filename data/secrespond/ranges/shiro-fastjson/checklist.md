# range-shiro-fastjson 检查清单

评估的评分标准（ground truth）。每个检查点拆分为检测分、方案分两个独立评分维度。

- **检测分**（满分 3 分）：发现(1) + 证据(1) + 归因(1) — 评判检测 Agent 的分析报告 — LLM-as-a-Judge
- **方案分**（满分 2 分）：正确性(1) + 完整性(1) — 评判检测 Agent 输出的修复方案 — LLM-as-a-Judge
- **仅检测项**：方案分标记 N/A，不参与对应汇总

## 维度 1：入侵实体识别与处置（8 项）

### CHK-01：JSP Webshell 1 (error.jsp) `ENT-F01`
- **证据**：`/opt/tomcat/webapps/ROOT/static/css/error.jsp` — JSP Webshell 伪装在 CSS 目录下
- **检测分**（3 分）
  - 发现：识别到可疑 JSP 文件存在于静态资源目录
  - 证据：指出文件路径，识别 JSP 文件不应出现在 css 目录
  - 归因：将 Webshell 与攻击者通过 Shiro RCE 植入关联
- **方案分**（2 分）
  - 正确性：方案给出正确的文件删除命令
  - 完整性：方案建议扫描所有 webapps 目录下的异常 JSP/JSPX 文件

### CHK-02：JSP Webshell 2 (analytics.jsp) `ENT-F01`
- **证据**：`/opt/tomcat/webapps/ROOT/static/js/analytics.jsp` — 伪装为统计脚本
- **检测分**（3 分）
  - 发现：识别到第二个 Webshell
  - 证据：指出 JSP 文件出现在 js 目录的异常性
  - 归因：识别攻击者使用多个 Webshell 作为备用入口
- **方案分**（2 分）
  - 正确性：方案给出删除命令
  - 完整性：方案建议全面扫描，不遗漏其他隐藏 Webshell

### CHK-03：挖矿进程检测 `ENT-P01`
- **证据**：进程 `/opt/.cache/.java-updater` 正在运行
- **检测分**（3 分）
  - 发现：识别到挖矿进程
  - 证据：指出路径 `/opt/.cache/.java-updater`，识别伪装名称
  - 归因：将挖矿进程与攻击者入侵后的牟利行为关联
- **方案分**（2 分）
  - 正确性：方案给出正确的进程终止命令
  - 完整性：方案涵盖终止进程 + 删除文件 + 检查守护机制

### CHK-04：挖矿二进制文件清理 `ENT-F02`
- **证据**：文件 `/opt/.cache/.java-updater` 存在
- **检测分**（3 分）
  - 发现：识别到恶意文件
  - 证据：指出文件路径和类型
  - 归因：将其与挖矿行为关联
- **方案分**（2 分）
  - 正确性：方案给出正确的删除命令
  - 完整性：方案建议检查 /opt/.cache/ 目录下其他可疑文件（含日志 .java-updater.log）

### CHK-05：MySQL dump 文件清理 `ENT-F04`
- **证据**：`/tmp/.sql_dump` — 攻击者导出的 MySQL 用户表数据
- **检测分**（3 分）
  - 发现：发现攻击者遗留的数据库 dump 文件
  - 证据：指出文件路径和内容（sys_user 表数据）
  - 归因：识别为攻击者数据窃取行为的证据
- **方案分**（2 分）
  - 正确性：方案建议先保留用于取证分析
  - 完整性：方案说明取证完成后的清理步骤

### CHK-06：MySQL UDF 持久化与后门文件清除 `ENT-F02` `PER-D01`
- **证据**：MySQL plugin 目录下的 `lib_mysqludf_json.so` — 恶意 UDF 共享库
- **检测分**（3 分）
  - 发现：识别到 MySQL plugin 目录中的可疑 SO 文件与异常 UDF 函数
  - 证据：指出文件路径和对应的 UDF 函数 (sys_exec)
  - 归因：将 UDF 后门与攻击者获取数据库密码后的持久化行为关联
- **方案分**（2 分）
  - 正确性：方案给出 DROP FUNCTION + 删除 SO 文件的命令
  - 完整性：方案建议审计 MySQL plugin 目录中所有非标准 SO，检查所有 UDF 函数 (`SELECT * FROM mysql.func`)

### CHK-07：Webshell 目录伪装识别 `ENT-F01`  *仅检测项*
- **证据**：两个 Webshell 分别放在 `static/css/` 和 `static/js/` 目录下
- **检测分**（3 分）
  - 发现：指出 JSP 文件放置在静态资源目录的伪装手法
  - 证据：对比正常 Tomcat 应用结构，指出目录位置异常
  - 归因：识别为攻击者通过目录伪装躲避常规 Webshell 扫描
- **方案分**：N/A（处置由 CHK-01/02 覆盖）
- **加分项**：Agent 建议设置 Tomcat 静态资源目录的 JSP 执行限制

### CHK-08：攻击者 SSH 公钥识别与 SSH 密钥持久化 `ENT-F04` `PER-A01`
- **证据**：`/root/.ssh/authorized_keys` 中包含注释为 `deploy@ci-ruoyi` 的异常密钥
- **检测分**（3 分）
  - 发现：识别到 authorized_keys 中的可疑 SSH 公钥
  - 证据：指出密钥注释 `deploy@ci-ruoyi` 和密钥内容特征
  - 归因：识别为攻击者植入的持久化后门密钥
- **方案分**（2 分）
  - 正确性：方案给出移除特定密钥行的命令
  - 完整性：方案建议核查所有用户的 authorized_keys

## 维度 2：基线风险（8 项）

### CHK-09：tomcat sudo 权限收紧 `BAS-04`
- **证据**：`/etc/sudoers.d/tomcat` 授予了 `NOPASSWD: /usr/bin/find, /usr/bin/vim`
- **检测分**（3 分）
  - 发现：识别到 tomcat 用户的危险 sudo 权限
  - 证据：指出 find -exec 和 vim :!bash 可用于提权
  - 归因：将 sudo 权限与攻击者从 tomcat 提权到 root 的路径关联
- **方案分**（2 分）
  - 正确性：方案建议移除 find/vim 的 NOPASSWD 权限
  - 完整性：方案包含 `visudo -c` 验证步骤，建议替换为安全的日志查看工具

### CHK-10：sudoers 后门持久化与清除 `PER-A02`
- **证据**：`/etc/sudoers.d/99-java-ops` — 攻击者植入的后门规则 `java-ops ALL=(ALL) NOPASSWD: ALL`
- **检测分**（3 分）
  - 发现：识别到 /etc/sudoers.d/ 中的异常 sudoers 文件
  - 证据：指出 99-java-ops 文件和 java-ops 用户的 NOPASSWD ALL 权限
  - 归因：识别为攻击者植入的持久化提权后门
- **方案分**（2 分）
  - 正确性：方案给出删除文件命令
  - 完整性：方案建议检查 /etc/sudoers.d/ 下所有文件，核查是否有其他异常规则

### CHK-11：application.yml 凭证保护 `BAS-03`
- **证据**：`/opt/ruoyi/application.yml` 中包含明文数据库密码 `RuoYi@2024`
- **检测分**（3 分）
  - 发现：识别到配置文件中的明文凭证
  - 证据：引用具体配置行和密码值
  - 归因：指出攻击者通过读取此文件获取了数据库访问权限
- **方案分**（2 分）
  - 正确性：方案建议更换数据库密码并使用加密存储
  - 完整性：方案建议文件权限收紧（chmod 600）、使用环境变量或 Jasypt 加密

### CHK-12：MySQL 远程访问控制 `BAS-02`
- **证据**：MySQL root 用户可从 `%`（任意主机）访问，密码 `RuoYi@2024`
- **检测分**（3 分）
  - 发现：识别到远程 root MySQL 访问的风险
  - 证据：指出 `root@'%'` 的授权和 bind-address=0.0.0.0
  - 归因：指出此配置可被外部攻击者利用
- **方案分**（2 分）
  - 正确性：方案给出限制为 localhost 的 SQL 命令和 bind-address 修改
  - 完整性：方案包含修改后的验证步骤

### CHK-13：Shiro 默认密钥 `BAS-03`
- **证据**：`application.yml` 中 `shiro.rememberMe.cipherKey: zSyK5Kp6PZAAjlT+eeNMlg==`
- **检测分**（3 分）
  - 发现：识别到 Shiro 使用默认加密密钥
  - 证据：引用配置文件中的 cipherKey 值，指出这是众所周知的默认密钥
  - 归因：将默认密钥与 Shiro 反序列化 RCE 入口直接关联
- **方案分**（2 分）
  - 正确性：方案建议更换为随机密钥或升级 Shiro 版本
  - 完整性：方案给出多层修复建议（换密钥 / 升级 / 关闭 rememberMe）

### CHK-14：Tomcat 运行用户权限 `BAS-04`
- **证据**：Tomcat 以 tomcat 用户运行，但该用户有过度 sudo 权限
- **检测分**（3 分）
  - 发现：识别到 Tomcat 进程的用户权限配置
  - 证据：指出 tomcat 用户的 sudo 配置
  - 归因：将过度权限与提权路径关联
- **方案分**（2 分）
  - 正确性：方案建议遵循最小权限原则
  - 完整性：方案建议移除不必要的 sudo 权限，仅保留业务必需

### CHK-15：Tomcat 端口主机层访问控制 `BAS-06`
- **证据**：Tomcat 监听 8080 端口承载 RuoYi 应用，主机层未配置防火墙限制
- **检测分**（3 分）
  - 发现：识别到 Tomcat 端口在主机层缺少访问控制
  - 证据：指出 8080 端口无访问控制
  - 归因：将端口可达性与 Shiro 漏洞利用的攻击面关联
- **方案分**（2 分）
  - 正确性：方案建议在主机防火墙或反向代理上限制 8080 访问来源
  - 完整性：方案给出防火墙规则修改建议

### CHK-16：MySQL 密码强度 `BAS-03`
- **证据**：MySQL root 密码 `RuoYi@2024` 为弱密码（规律性强，可猜测）
- **检测分**（3 分）
  - 发现：识别到数据库使用弱密码
  - 证据：指出密码规律性
  - 归因：指出弱密码被攻击者从配置文件读取后直接利用
- **方案分**（2 分）
  - 正确性：方案建议更换为强密码
  - 完整性：方案给出密码复杂度要求

## 维度 3：持久化清除（8 项）

### CHK-17：Systemd 服务持久化 `PER-V01`
- **证据**：`/etc/systemd/system/java-app-monitor.service` — 伪装为 Java 应用监控
- **检测分**（3 分）
  - 发现：识别到可疑 systemd 服务
  - 证据：指出 unit 文件路径和 ExecStart 指向 /opt/.cache/.java-updater
  - 归因：识别为挖矿持久化机制
- **方案分**（2 分）
  - 正确性：方案给出 stop + disable + 删除 unit + daemon-reload 的完整命令
  - 完整性：方案包含清理后的验证步骤

### CHK-18：Systemd 服务伪装识别 `PER-V01`  *仅检测项*
- **证据**：服务名 `java-app-monitor` 和描述 `Java Application Monitor Service` 模仿合法监控服务
- **检测分**（3 分）
  - 发现：指出服务名称的伪装手法
  - 证据：对比合法系统服务，指出命名模仿
  - 归因：识别为攻击者通过命名伪装躲避人工审查
- **方案分**：N/A

### CHK-19：Crontab 持久化 `PER-S01`
- **证据**：`crontab -l` 显示 `*/10 * * * * /opt/.cache/.java-updater >/dev/null 2>&1`
- **检测分**（3 分）
  - 发现：识别到可疑 crontab 条目
  - 证据：引用具体 crontab 内容，指出定时执行间隔和静默输出
  - 归因：将 crontab 与挖矿持久化关联
- **方案分**（2 分）
  - 正确性：方案给出删除恶意 crontab 条目的方法
  - 完整性：方案建议检查所有用户的 crontab 和 /etc/cron.d/

### CHK-20：profile.d 持久化 `PER-I01`
- **证据**：`/etc/profile.d/java-env.sh` — 伪装为 Java 环境变量脚本，实际启动挖矿
- **检测分**（3 分）
  - 发现：识别到 profile.d 中的恶意脚本
  - 证据：指出文件中包含启动 .java-updater 的代码
  - 归因：识别为每次用户登录时自动重启挖矿的持久化手段
- **方案分**（2 分）
  - 正确性：方案给出删除文件命令
  - 完整性：方案建议检查 /etc/profile.d/ 下所有脚本

### CHK-21：at 延迟任务 `PER-S03`
- **证据**：`atq` 显示待执行的延迟任务
- **检测分**（3 分）
  - 发现：识别到 at 队列中的可疑任务
  - 证据：指出任务内容（执行 .java-updater）
  - 归因：识别为攻击者设置的延迟执行机制，用于对抗一次性清理
- **方案分**（2 分）
  - 正确性：方案给出 `atrm` 删除命令
  - 完整性：方案建议检查所有待执行 at 任务并考虑禁用 atd

### CHK-22：rc.local 持久化 `PER-V02`
- **证据**：`/etc/rc.d/rc.local` 中包含 `.java-updater` 启动命令
- **检测分**（3 分）
  - 发现：识别到 rc.local 中的可疑条目
  - 证据：引用具体行内容
  - 归因：识别为开机自启的挖矿持久化
- **方案分**（2 分）
  - 正确性：方案给出删除对应行的方法
  - 完整性：方案建议审查 rc.local 全部内容

### CHK-23：全面的持久化扫描 `Q-05`  *仅检测项*
- **证据**：本靶场共 8 种持久化机制
- **检测分**（3 分）
  - 发现：执行系统性的持久化扫描（覆盖 systemd/cron/profile.d/ssh keys/sudoers/MySQL UDF/at/rc.local/init.d 等）
  - 证据：记录扫描范围和方法
  - 归因：证明排查的全面性
- **方案分**：N/A

### CHK-24：持久化关联分析 `Q-05`  *仅检测项*
- **证据**：8 种持久化机制都指向同一个挖矿程序 `/opt/.cache/.java-updater`
- **检测分**（3 分）
  - 发现：识别到多种持久化机制的关联性
  - 证据：指出所有持久化最终都启动同一个程序
  - 归因：分析为攻击者的冗余持久化策略
- **方案分**：N/A

## 维度 4：根因溯源（10 项）

### CHK-25：入口判定 — Shiro 反序列化 `Q-01` `Q-04`  *仅检测项*
- **证据**：Shiro 默认密钥 + rememberMe=deleteMe 指纹 + Webshell 部署 + 无 SSH 暴力破解痕迹
- **检测分**（3 分）
  - 发现：正确判定入口为"Shiro 默认密钥反序列化 RCE"
  - 证据：引用 Shiro 版本、默认密钥、CommonsCollections gadget
  - 归因：排除 SSH 暴力破解和其他入口，正确定性为 CVE 利用场景
- **方案分**：N/A
- **关键**：Agent 不应编造不存在的 CVE 编号

### CHK-26：Shiro 版本与密钥配置定位 `VUL-01`
- **证据**：`/opt/tomcat/webapps/ROOT/WEB-INF/lib/shiro-core-1.7.0.jar`（库本身已移除硬编码默认密钥），但 `application.yml` 中 `shiro.rememberMe.cipherKey` 仍配置了众所周知的默认密钥 `zSyK5Kp6PZAAjlT+eeNMlg==`
- **检测分**（3 分）
  - 发现：在 JAR 依赖中定位 Shiro 版本，并在应用配置中发现使用了已知默认密钥
  - 证据：指出 JAR 文件路径和版本号 1.7.0，以及 application.yml 中的 cipherKey 值
  - 归因：将应用层配置的已知默认密钥与 Shiro 反序列化 RCE 入口关联
- **方案分**（2 分）
  - 正确性：方案建议替换 application.yml 中的 cipherKey 为强随机 key
  - 完整性：方案给出多层修复（换密钥 / 关闭 rememberMe）

### CHK-27：Fastjson 版本定位 `VUL-01`
- **证据**：`/opt/tomcat/webapps/ROOT/WEB-INF/lib/fastjson-1.2.68.jar`
- **检测分**（3 分）
  - 发现：在 JAR 依赖中定位 Fastjson 版本
  - 证据：指出 JAR 文件路径和版本号 1.2.68（存在 autoType 漏洞）
  - 归因：将 Fastjson 1.2.68 与反序列化漏洞关联
- **方案分**（2 分）
  - 正确性：方案建议升级 Fastjson 到 >= 1.2.83 或替换为 Jackson
  - 完整性：方案说明 autoType 的风险和配置缓解方案

### CHK-28：CommonsCollections gadget 识别 `VUL-01`  *仅检测项*
- **证据**：`/opt/tomcat/webapps/ROOT/WEB-INF/lib/commons-collections-3.2.1.jar`
- **检测分**（3 分）
  - 发现：识别到 CommonsCollections 3.2.1 作为 gadget chain 依赖
  - 证据：指出 JAR 版本和反序列化利用关系
  - 归因：将 CC 3.x 与 Shiro 反序列化 RCE 的 gadget chain 关联
- **方案分**：N/A（升级由 CHK-26/27 覆盖）

### CHK-29：Java 进程链溯源 `Q-02`  *仅检测项*
- **证据**：告警中 `parent_procpath=/usr/bin/java` → Tomcat → RuoYi → Shiro/Fastjson
- **检测分**（3 分）
  - 发现：从 Java 进程追踪到具体应用
  - 证据：建立 java → tomcat → ruoyi → shiro/fastjson 的关联链
  - 归因：完成从进程到漏洞的完整溯源
- **方案分**：N/A

### CHK-30：sudo 提权路径还原 `Q-02`  *仅检测项*
- **证据**：攻击者使用 `sudo find /tmp -exec /bin/bash -p \;` 从 tomcat 提权到 root
- **检测分**（3 分）
  - 发现：还原 sudo find 提权路径
  - 证据：指出 find -exec 的提权原理和 sudoers 配置
  - 归因：将提权与后续 root 权限操作（持久化、挖矿）关联
- **方案分**：N/A（修复由 CHK-09 覆盖）

### CHK-31：攻击时间线重建 `Q-02`  *仅检测项*
- **证据**：Tomcat access log 时间戳、Webshell 文件 mtime、挖矿部署时间、持久化机制创建时间
- **检测分**（3 分）
  - 发现：构建出连贯的攻击时间线
  - 证据：Shiro RCE → Webshell 部署 → 信息收集 → 提权 → 持久化 → 挖矿
  - 归因：将多个时间戳来源交叉关联
- **方案分**：N/A

### CHK-32：Tomcat 日志部分清理识别 `Q-02` `Q-03`  *仅检测项*
- **证据**：access log 中 rememberMe/error.jsp 请求被删除，但 analytics.jsp 请求保留（攻击者疏忽）
- **检测分**（3 分）
  - 发现：识别到 Tomcat access log 的部分清理痕迹
  - 证据：发现 analytics.jsp 请求记录仍在，而其他攻击请求缺失
  - 归因：识别日志不完整性本身为攻击者清理痕迹的证据
- **方案分**：N/A

### CHK-33：攻击者 IP 识别 `Q-03`  *仅检测项*
- **证据**：Tomcat access log 中的攻击请求来源 IP
- **检测分**（3 分）
  - 发现：识别出攻击者的源 IP 地址
  - 证据：引用具体日志行和 IP 地址
  - 归因：将该 IP 与 Webshell 访问和 Shiro 攻击关联
- **方案分**：N/A（封禁由 CHK-38 覆盖）

### CHK-34：数据泄露评估 `Q-02`  *仅检测项*
- **证据**：`/tmp/.sql_dump` 包含 sys_user 表数据；application.yml 凭证已泄露
- **检测分**（3 分）
  - 发现：评估数据泄露范围（用户表、数据库凭证）
  - 证据：指出被导出的具体数据内容
  - 归因：将数据窃取与攻击者的信息收集阶段关联
- **方案分**：N/A

## 维度 5：漏洞修复（6 项）

### CHK-35：Shiro 漏洞修复 `VUL-01`
- **证据**：Shiro 1.2.4 使用默认密钥
- **检测分**（3 分）
  - 发现：建议修复 Shiro 默认密钥漏洞
  - 证据：引用 Shiro 版本和默认密钥
  - 归因：将修复需求与入口漏洞直接关联
- **方案分**（2 分）
  - 正确性：方案层次合理（更换密钥 / 升级版本 / 关闭功能）
  - 完整性：方案说明各层修复的优缺点和适用场景

### CHK-36：Fastjson 漏洞修复 `VUL-01`
- **证据**：Fastjson 1.2.68 存在 autoType 反序列化漏洞
- **检测分**（3 分）
  - 发现：建议修复 Fastjson autoType 漏洞
  - 证据：引用版本号和已知漏洞
  - 归因：将 Fastjson 作为攻击备用入口与修复优先级关联
- **方案分**（2 分）
  - 正确性：方案建议升级到安全版本或替换为 Jackson
  - 完整性：方案包含 autoType 全局禁用配置

### CHK-37：CommonsCollections 升级 `VUL-01`
- **证据**：commons-collections-3.2.1 是 Shiro 反序列化的 gadget chain
- **检测分**（3 分）
  - 发现：建议升级 CommonsCollections
  - 证据：指出 CC 3.x 作为 gadget 的角色
  - 归因：升级 CC 可阻断 gadget chain
- **方案分**（2 分）
  - 正确性：方案建议升级到 CC 3.2.2+ 或 4.x（已修复反序列化）
  - 完整性：方案说明版本兼容性影响

### CHK-38：攻击者 IP 防火墙封禁 `ENT-N01`
- **证据**：从 Tomcat access log 中识别的攻击者 IP
- **检测分**（3 分）
  - 发现：建议封禁攻击者 IP
  - 证据：引用具体 IP 地址
  - 归因：关联到 Web 攻击流量
- **方案分**（2 分）
  - 正确性：方案给出正确的防火墙规则
  - 完整性：方案包含持久化规则和验证步骤

### CHK-39：挖矿外连封禁 `ENT-N02`
- **证据**：挖矿连接 `stratum+tcp://pool.evil-example.invalid:3333`
- **检测分**（3 分）
  - 发现：建议封禁矿池出站连接
  - 证据：引用矿池地址和端口
  - 归因：识别为挖矿 C2 通信
- **方案分**（2 分）
  - 正确性：方案给出出站防火墙规则
  - 完整性：方案包含 IP + 端口封禁和规则持久化

### CHK-40：漏洞修复方案评估 `Q-07`  *仅检测项*
- **证据**：Shiro/Fastjson/CC 三个组件的修复方案
- **检测分**（3 分）
  - 发现：评估修复方案的层次性和完整性
  - 证据：区分最低修复（换密钥）、推荐修复（升级版本）、最佳修复（多层防御）
  - 归因：体现对 Java 安全生态的理解深度
- **方案分**：N/A

## 维度 6：修复闭环（5 项）

### CHK-41：漏洞修复验证 `Q-07`
- **证据**：Shiro/Fastjson 修复后应通过验证
- **检测分**（3 分）
  - 发现：建议执行修复后验证
  - 证据：说明验证方法（rememberMe Cookie 不再触发 RCE）
  - 归因：体现修复闭环意识
- **方案分**（2 分）
  - 正确性：方案给出验证步骤
  - 完整性：方案包含回归测试建议

### CHK-42：Webshell 清理确认 `Q-07`
- **证据**：两个 Webshell 应已清理
- **检测分**（3 分）
  - 发现：建议确认 Webshell 清理完整性
  - 证据：给出扫描所有 webapps 目录的方法
  - 归因：防止遗漏其他 Webshell
- **方案分**（2 分）
  - 正确性：方案给出全面 Webshell 扫描命令
  - 完整性：方案建议部署文件完整性监控

### CHK-43：服务重启与验证 `Q-07`
- **证据**：Tomcat、MySQL 在修复后应正常运行
- **检测分**（3 分）
  - 发现：建议验证修复未影响业务服务
  - 证据：列出需验证的关键服务
  - 归因：体现业务影响意识
- **方案分**（2 分）
  - 正确性：方案列出关键服务的状态检查命令
  - 完整性：方案涵盖 Tomcat、MySQL，考虑端口监听确认

### CHK-44：数据库凭证轮转 `Q-07`
- **证据**：MySQL 密码和 application.yml 凭证已泄露
- **检测分**（3 分）
  - 发现：建议进行凭证轮转
  - 证据：列出需轮转的凭证（MySQL 密码、application.yml 中所有密码）
  - 归因：泄露的凭证即使修复漏洞后仍有被重用的风险
- **方案分**（2 分）
  - 正确性：方案给出密码轮转步骤
  - 完整性：方案涵盖 MySQL、Redis、应用凭证的全面轮转

### CHK-45：持久化清除完整性验证 `Q-07`
- **证据**：8 种持久化机制应全部清除
- **检测分**（3 分）
  - 发现：建议逐一验证所有持久化已清除
  - 证据：给出每种持久化的验证命令
  - 归因：防止遗漏导致攻击者重新建立控制
- **方案分**（2 分）
  - 正确性：方案列出 8 种持久化的逐项验证方法
  - 完整性：方案建议重启后再次检查
