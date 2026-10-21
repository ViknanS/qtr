# SecRespond

<h4 align="center">
    <p>
        <a href="README.md">English</a>&nbsp; | &nbsp;
        <b>中文</b>
    </p>
</h4>

<p align="center">
    🤗 <a href="https://huggingface.co/datasets/Alibaba-NLP/SecRespond">Hugging Face</a>&nbsp; | &nbsp;
    🤖 <a href="https://modelscope.cn/datasets/iic/SecRespond">ModelScope</a>&nbsp; | &nbsp;
    📄 <a href="https://arxiv.org/abs/2607.26791">论文</a>
</p>

## 简介

**SecRespond：面向真实世界攻陷后应急响应的 AI Agent 基准评测**，用于评估 AI Agent 能否在攻击已经成功后调查一台受攻陷主机。

在每个网络靶场中，响应 Agent 会获得一份冻结的取证磁盘快照和模拟的主机安全产品输出，并据此生成有证据支撑的事件分析与处置方案。本基准关注攻陷后的调查与响应，而非攻陷前的漏洞发现。

## 数据包结构

完整 Hugging Face 数据集采用以下结构。所有路径均相对于数据集仓库根目录：

```text
.
├── LICENSE
├── README.md
├── README_zh.md
├── task-prompts/
│   ├── linux.md
│   └── windows.md
├── evaluation/
│   ├── SKILL.md
│   └── prompt.md
└── ranges/
    └── <range>/
        ├── checklist.md
        ├── checklist.en.md
        ├── sas-mock/
        ├── disk.tar.gz
        └── disk.tar.gz.sha256
```

GitHub 目录包含相同的轻量级基准资源，但有意不包含 `disk.tar.gz`、`disk.tar.gz.sha256` 和展开后的 `disk/` 目录。完整 Hugging Face 数据集会为每个靶场补充一份归档及其校验文件。

完整数据集包含两个响应 Agent 提示词、两个评测文件和 10 个靶场。每个靶场均包含权威评分标准 `checklist.md`、与其对齐的英文版本 `checklist.en.md`、一个 `disk.tar.gz` 和一个 `disk.tar.gz.sha256`；不同靶场可提供不同的 `sas-mock` 文件。

| 路径 | 用途 |
| :--- | :--- |
| `task-prompts/` | 不同平台的响应 Agent 提示词。 |
| `evaluation/` | 评测 Agent 提示词及基准评分 Skill。 |
| `ranges/<range>/checklist.md` | 专家编写的权威评分标准。 |
| `ranges/<range>/checklist.en.md` | 与评分标准对齐的英文翻译。 |
| `ranges/<range>/sas-mock/` | 少量模拟告警、漏洞发现或基线检查结果；不同靶场提供的文件可能不同。 |
| `ranges/<range>/disk.tar.gz` | 压缩后的合成取证文件系统。 |
| `ranges/<range>/disk.tar.gz.sha256` | 靶场归档的完整性校验文件。 |
| `ranges/<range>/disk/` | 运行时展开的只读取证工作区。 |

某类 `sas-mock` 数据缺失时，请勿自行创建占位文件。展开后的 `disk/` 目录属于运行时制品，不包含在数据集中。

## 任务与评测资源

### 响应 Agent

`task-prompts/` 目录包含两个完整、独立且不依赖 Skill 的响应 Agent 提示词：

| 靶场平台 | 提示词 |
| :------- | :----- |
| Linux | `task-prompts/linux.md` |
| Windows | `task-prompts/windows.md` |

必须根据靶场平台选择其中一个提示词，不能拼接 Linux 和 Windows 提示词。

每个响应 Agent 提示词使用以下占位符：

| 占位符 | 运行框架提供的值 |
| :----- | :--------------- |
| `{{DISK_PATH}}` | 展开后的只读 `disk/` 目录路径。 |
| `{{SAS_PATH}}` | 所选靶场的 `sas-mock/` 目录路径。 |
| `{{OUTPUT_PATH}}` | 响应 Agent 输出的可写目录。 |

响应 Agent 需要写出五个文件：

| 输出 | 用途 |
| :--- | :--- |
| `progress.md` | 调查时间线和工作检查清单。 |
| `intrusion-report.md` | 攻击链还原、证据、实体、持久化机制和影响分析。 |
| `vuln-report.md` | 对已利用漏洞或其他相关漏洞进行验证。 |
| `baseline-report.md` | 评估高风险配置和暴露服务。 |
| `remediation-plan.md` | 给出按优先级排序、正确、完整且可验证的处置步骤。 |

五个文件缺一不可。当模型运行成功但缺少任一必需输出时，`run_task.sh` 返回退出码 `4`。`run_evaluation.sh` 会在创建评测输出工作区前检查完整文件集合；如果缺少任何报告，则会在调用模型前退出。

### 评测 Agent

评测 Agent 由一个提示词和基准评分 Skill 组成：

```text
evaluation/
├── SKILL.md
└── prompt.md
```

渲染 `prompt.md` 时需要填充以下占位符：

| 占位符 | 运行框架提供的值 |
| :----- | :--------------- |
| `{{CHECKLIST_PATH}}` | `ranges/<range>/checklist.md` 的路径。 |
| `{{DETECTION_REPORTS_PATH}}` | 包含响应报告的目录；名称沿用论文中的 Detection 术语。 |
| `{{EVALUATION_SKILL_PATH}}` | `evaluation/SKILL.md` 的路径。 |
| `{{OUTPUT_PATH}}` | 评测 Agent 输出的可写目录。 |

评测 Agent 写出：

- `evaluation-report.md`：逐检查项分数、评分理由、引用证据和汇总。
- `scores.json`：包含逐检查项 Detection、Plan 分数及总体汇总的结构化文件。

## 还原靶场磁盘

下载完整 Hugging Face 数据集后，每个靶场均包含 `disk.tar.gz` 和 `disk.tar.gz.sha256`。在数据集仓库根目录中，解压前先校验所选归档：

```bash
RANGE=ssh-miner
RANGE_DIR="ranges/${RANGE}"

(cd "$RANGE_DIR" && sha256sum -c disk.tar.gz.sha256 && tar -xzf disk.tar.gz)
```

归档必须展开到唯一的顶层 `disk/` 目录下：

```text
ranges/ssh-miner/disk/
```

请将展开后的目录作为只读取证工作区提供给响应 Agent。包含所有靶场的单个聚合归档不能替代按靶场提供 `disk.tar.gz` 的发布约定。

## 运行时集成约定

提示词和 Skill 文件均为静态资源，不会被自动发现。兼容的运行框架必须：

1. 根据靶场平台选择 `task-prompts/linux.md` 或 `task-prompts/windows.md`。
2. 将 `DISK_PATH`、`SAS_PATH` 和 `OUTPUT_PATH` 渲染到所选响应 Agent 提示词中。
3. 在分析机器上运行响应 Agent，并以只读方式提供取证磁盘。
4. 渲染评测 Agent 的全部四个占位符，并加载 `evaluation/SKILL.md`。
5. 使用所选靶场的 `checklist.md` 评测响应 Agent 输出。

独立的 Hugging Face 数据集不包含可执行运行代码。qqr 仓库在 `scripts/secrespond/` 目录下提供两个 OpenCode 运行脚本：

- `scripts/secrespond/run_task.sh`：运行单个靶场的响应任务。
- `scripts/secrespond/run_evaluation.sh`：评测单个靶场已经生成的完整响应报告。

运行这些脚本依赖 [OpenCode](https://opencode.ai/docs/zh-cn#%E5%AE%89%E8%A3%85)。请先按照官方文档完成安装和模型配置，再运行以下示例。

请在 qqr 仓库根目录执行：

```bash
DATA_DIR=/path/to/secrespond
TASK_OUTPUT=/path/to/task-output
EVALUATION_OUTPUT=/path/to/evaluation-output
MODEL=alibaba-cn/qwen3.7-max  # 请替换为 OpenCode 中已配置的模型。

scripts/secrespond/run_task.sh ssh-miner \
  --data-dir "$DATA_DIR" \
  --disk-path "$DATA_DIR/ranges/ssh-miner/disk" \
  --output-dir "$TASK_OUTPUT" \
  --model "$MODEL"

scripts/secrespond/run_evaluation.sh ssh-miner \
  --data-dir "$DATA_DIR" \
  --reports-dir "$TASK_OUTPUT" \
  --output-dir "$EVALUATION_OUTPUT" \
  --model "$MODEL"
```

`--data-dir` 必须指向同时包含 `task-prompts/`、`evaluation/` 和 `ranges/` 的数据集根目录。任务运行脚本默认使用该目录下的 `ranges/<range>/disk` 和 `ranges/<range>/sas-mock`；如果任一输入位于其他位置，可使用 `--disk-path` 或 `--sas-path` 指定。脚本会原地读取所选磁盘目录，不会复制或创建软链接；如果需要保护源数据，请使用只读挂载或隔离副本。

`run_task.sh` 只渲染一个与平台对应的独立提示词。`run_evaluation.sh` 会渲染评测 Agent 的全部四个占位符，并通过具体路径引用 `evaluation/SKILL.md`。两个脚本均使用 OpenCode 的常规配置发现机制；请在 OpenCode 中配置 provider、端点和凭据。`--model` 用于选择已配置的模型；如果 OpenCode 已设置默认模型，也可以省略。两个脚本均支持 `--prepare-only`，无需调用模型即可完成配置验证。

基于旧版嵌套 `agents/` 结构、`{{SKILLS_PATH}}` 或 `{{RESPONDER_OUTPUT_PATH}}` 的集成必须先完成更新。评测 Agent 仅接受 `CHECKLIST_PATH`、`DETECTION_REPORTS_PATH`、`EVALUATION_SKILL_PATH` 和 `OUTPUT_PATH`。

## 靶场输入

每个靶场提供三类逻辑输入：

| 输入 | 用途 |
| :--- | :--- |
| `ranges/<range>/disk/` | 合成取证快照，包含日志、残留文件、配置变更、持久化制品及其他攻击痕迹。 |
| `ranges/<range>/sas-mock/` | 部分模拟安全产品证据；告警只是调查起点，并非完整事实。 |
| `ranges/<range>/checklist.md` | 权威评分约定，定义证据、归因、处置要求和能力标签。 |

每个靶场还包含 `ranges/<range>/checklist.en.md`，作为与评分标准对齐的英文翻译；运行框架使用的权威约定仍为 `checklist.md`。

SecRespond 有意混合告警可见和静默的攻击制品。完整调查必须主动分析磁盘，而不能只复述告警内容。

## 靶场

当前数据包包含 10 个网络靶场，覆盖四类攻击入口、21 项 MITRE ATT&CK 技术和五种操作系统。

| 靶场 | 入口类型 | 场景概述 | 平台 | 检查项 |
| :--- | :------- | :------- | :--- | -----: |
| `ssh-miner` | 基线弱点 | SSH 暴力破解，随后进行挖矿并建立多重持久化。 | Linux (CentOS 7) | 23 |
| `shiro-fastjson` | 已知 CVE | 利用 Shiro 默认密钥和 Fastjson 反序列化部署 WebShell、提权并挖矿。 | Linux (CentOS 8) | 45 |
| `log4j-rce` | 已知 CVE | 利用 Log4Shell 部署 WebShell、提权、建立持久化并挖矿。 | Linux (CentOS 8) | 22 |
| `docker-escape` | 基线弱点 | 利用暴露的 Docker API 逃逸容器并接管宿主机。 | Linux (Ubuntu 20.04) | 24 |
| `redis-rce` | 基线弱点 | 利用未授权 Redis 注入 SSH 密钥，获取 root 权限、挖矿并建立持久化。 | Linux (Ubuntu 22.04) | 24 |
| `jenkins-rce` | 业务代码 | 通过 Jenkins Script Console 执行代码，随后挖矿、窃取凭据并建立持久化。 | Linux (Ubuntu 22.04) | 24 |
| `nextjs-rce` | 已知 CVE | 利用 Next.js RCE，随后提权、执行 rootkit 风格行为并挖矿。 | Linux (Ubuntu 22.04) | 37 |
| `npm-worm` | 供应链 | 恶意 npm 包传播蠕虫、窃取凭据、连接 C2 并挖矿。 | Linux (Ubuntu 22.04) | 39 |
| `aspnet-viewstate` | 已知 CVE | 利用 ASP.NET ViewState 反序列化执行 RCE，随后部署 WebShell、窃取凭据并建立持久化。 | Windows Server | 22 |
| `rdp-service-abuse` | 基线弱点 | RDP 密码喷洒后滥用弱服务权限，以 SYSTEM 身份执行、建立持久化、转储凭据并连接 C2。 | Windows Server | 20 |

## 评测

每个靶场的 `checklist.md` 是权威评测约定，`checklist.en.md` 是与其对齐的英文翻译。SecRespond 将应急响应能力划分为五类：

| 能力 | 说明 |
| :--- | :--- |
| 入侵实体 (ENT) | 识别并处置恶意进程、文件、网络端点和被篡改制品。 |
| 持久化机制 (PER) | 发现并处置重启后仍然生效的植入，包括计划任务、服务、Shell Hook、WebShell、账户后门、WMI 或加载器级 Hook。 |
| 基线风险 (BAS) | 识别不安全的主机配置、暴露服务、弱凭据和权限风险。 |
| 漏洞风险 (VUL) | 验证已被利用或其他相关的软件漏洞。 |
| 调查与响应质量 (Q) | 评估攻击链还原、证据质量、诚实性、完整性、处置验证和业务影响意识。 |

Detection 和 Plan 分别计分：

| 维度 | 满分 | 含义 |
| :--- | ---: | :--- |
| Detection | 3 | 是否发现、提供具体证据并正确归因。 |
| Plan | 2 | 处置操作是否正确且完整，包括验证步骤和副作用。 |

部分检查项仅评估 Detection，因此没有 Plan 分数；另一些仅评估 Plan，因此没有 Detection 分数。相应维度的汇总会排除 N/A 项。各靶场的评分标准可能要求将质量类 (`Q`) 检查项与能力汇总分开报告。不得将 Detection 和 Plan 合并为单一分数。

## 引用

如果 SecRespond 对您的研究有帮助，请引用：

```bibtex
@misc{wang2026secrespondbenchmarkingaiagents,
  title={SecRespond: Benchmarking AI Agents for Real-World Post-Compromise Incident Response},
  author={Lehan Wang and Boli Chen and Ruixue Ding and Pengjun Xie and Jinwei Huang and Zhendong Liu and Shuo Wang and Tao Lei and Xin Ouyang and Xiaomeng Li},
  year={2026},
  eprint={2607.26791},
  archivePrefix={arXiv},
  primaryClass={cs.CR},
  url={https://arxiv.org/abs/2607.26791},
}
```

## 伦理声明

### 第三方模型评测

本数据集评测环节涉及的第三方模型仅用于学术研究目的。所有实验结果均为受控实验环境下的评测数据，仅用于能力对比与技术讨论。引用模型、供应商名称及分数不代表相应供应商或品牌的任何官方立场或背书。使用这些服务获得的模型输出以及由此形成的评测记录，均不用于训练、微调或蒸馏任何竞争性模型。

### 安全研究与使用限制

所有基准数据均在我们授权并控制的隔离实验环境中生成，而非从生产系统采集。每个网络靶场均为我们专门搭建、实施攻击并创建快照的主机。发布的取证及安全产品制品均为合成数据，不包含任何客户、生产或真实业务系统数据。我们对每份磁盘快照进行了脱敏，以占位符替换真实凭据、密钥和个人数据，仅保留分析所需的取证制品。场景中的攻击技术、CVE 和漏洞利用方法仅来源于 MITRE ATT&CK、公开漏洞数据库等公开知识库与漏洞披露。本基准包含取证证据而非可执行的漏洞利用链；不包含任何专有或内部研发的高阶攻击技术，也不包含超出公开来源的增量攻击信息，且无法直接用于对真实系统实施攻击。本基准仅供防御性安全研究使用。严禁将其用于未经授权的入侵、破坏性测试、攻击性活动，或任何其他违反适用法律法规的目的。

## 许可证

本仓库中的数据集文件采用 [知识共享署名—非商业性使用—相同方式共享 4.0 协议国际版 (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans) 授权。完整许可文本见 [LICENSE](LICENSE)。
