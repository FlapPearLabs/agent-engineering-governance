# Profile Reference Matrix (Mature Agent Pattern Synthesis)

**Audit Date**: 2026-09-26  
**Auditor**: Hermes Multi-Bot Hardening Engine  
**Methodology**: REFERENCE-DRIVEN PROFILE DESIGN (Search -> Identify -> Compare -> Extract -> Adapt)

---

## 1. MEDIA BOT REFERENCE SYNTHESIS

| Source | Purpose | Pattern Worth Copying | Pattern to Reject | Why | Adaptation for User |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Baoyu Canonical Skills (宝玉工作室)** | 科技内容排版、SVG 配图与平台发布 | 结构化 Brief 转化（文章大纲 -> Visual Plan -> SVG/HTML -> 平台适配）；严谨的排版规范 | 无脑套用模版套话；为了迎合算法过度情绪化 | 用户定位是硬核工程背景，浮夸文风会摧毁长期公信力 | 仅吸收其 SVG 架构图生成、Markdown 格式化与平台规整管线。 |
| **Hypit (`hypit-ai/hypit`)** | 视频解构与二次创作流程 | Reference Video 解构（Hook、B-roll、音画节奏拆解）；可编辑工作流声明文件 | 全自动“一键爆款”黑盒生成；侵权素材直接拼接 | 黑盒生成不可控且容易产生低质流水线噪音 | 吸收其 **Hook 拆解 + 分镜节奏标记**，形成本地可复现的脚本与分镜规范。 |
| **OpenMontage (`calesthio/OpenMontage`)** | Agent-First 程序化视频管线 | Manifest 驱动（Pipeline Manifest -> Stage Director -> Tools -> Human Checkpoint -> Render） | 强制前置绑定高成本商用闭源 API | 增加不必要的固定财务支出与环境摩擦 | 采用轻量化本地文件系统工作区（`ideas/`, `scripts/`, `assets/`, `video-projects/`）作为 Manifest 载体。 |

---

## 2. RESEARCH BOT REFERENCE SYNTHESIS

| Source | Purpose | Pattern Worth Copying | Pattern to Reject | Why | Adaptation for User |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenAI Deep Research / Manus Workflow** | 递归式深度资料检索与证据交叉验证 | Claim-Evidence Mapping：先建证据树，对关键事实进行跨来源三角印证（Triangulation） | 论坛/社媒未经核实直接采信为结论 | 社交网络情绪和软文噪音极高，极易形成假象 | 强制执行 **PRIMARY SOURCES FIRST**：社媒仅作为“舆向线索”，禁止升级为定论。 |
| **Bellingcat OSINT Methodology** | 调查性分析与开源情报核验 | 时间戳锚定（Temporal Validity）、信源可信度分级（Source Quality）、明确矛盾证据记录 | 主观猜测填充证据空白 | 不确定性必须诚实暴露，不能脑补事实 | 建立内部 **Claim Pipeline**：每个结论必须包含 Source、Quality、Date、Corroboration、Contradiction。 |
| **ArXiv & Academic Literature Review Standard** | 学术前沿综述与同行评审标准 | 区分事实（Fact）、证据（Evidence）、逻辑推断（Inference）与存疑点（Uncertainty） | 堆砌长篇术语摘要而无实际结论 | 缺乏行动指引的文献综述是信息浪费 | 将四分法从“格式标题”升格为“认知管道”，输出明确的工程与选型建议。 |

---

## 3. EDU BOT REFERENCE SYNTHESIS

| Source | Purpose | Pattern Worth Copying | Pattern to Reject | Why | Adaptation for User |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bloom's Mastery Learning (卡罗尔与布鲁姆掌握学习法)** | 掌握度驱动的阶梯教学 | 诊断性摸底（Diagnostic）-> 靶向形成性评价 -> 达标验收 -> 回潮降难机制 | 按照固定日历进度强推，忽视学习者当前阻断点 | 基础概念夹生会导致后续高阶知识彻底崩溃 | 吸收用户英语训练成功实践：**薄弱点台账（Weakness Ledger）** 与 **回潮降难重训** 机制。 |
| **Retrieval Practice & Spaced Repetition (Roediger & Ebbinghaus)** | 认知心理学提取练习与间隔复测 | 延期复测（Delayed Retest: D+1 / D+3 / D+7）；主动生成（Active Output）优于被动阅读 | 机械填空刷题与假性熟悉度（Fluency Illusion） | 刷题记忆是虚假掌握，无法转化为实际能力 | 考核标准强制要求：**行为证据与主观输出（Explain/Build/Apply）**。 |
| **Cognitive Load Theory (Sweller 认知负荷理论)** | 降低外在认知负荷的脚手架教学 | Worked Examples（样例教学）-> Completion Problems（完形脚手架）-> Independent Practice | 从专家视角觉得简单就跳过基础概念推导 | 初学者的认知带宽极度有限，专家盲区最致命 | 教学设计永远从 **REAL BEGINNER STATE** 出发，严禁专家自嗨。 |

---

## 4. MARKETS BOT REFERENCE SYNTHESIS

| Source | Purpose | Pattern Worth Copying | Pattern to Reject | Why | Adaptation for User |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Bridgewater Macro Economic Framework (达利欧经济机器)** | 宏观事件驱动与多资产传导链 | 区分经济基本面事实、市场已定价预期（Pricing-in）、偏差（Surprise）与二阶反响 | 单纯“出利好就看多、出利空就看空”的机械线性思维 | 资产价格波动取决于实际与预期的差值，而非事件本身 | 固化 **ESR 8-Field Pipeline**（Event, Expectation, Surprise, Positioning, Immediate Response, Cross-Asset, Explanation, Invalidation）。 |
| **Goldman Sachs / Morgan Stanley Sell-Side Event Study** | 投行研报与突发事件量化分析 | 跨资产背离与确认（例如：美元与美债收益率同向或背离的深层含义） | 故事性马后炮事后编造（Post-hoc narrative fitting） | 事后看图说话毫无前瞻预警和风险控制价值 | 强制列出 **Competing Hypotheses（竞争性假说）** 和 **Invalidation Conditions（证伪条件）**。 |
| **Polymarket & Prediction Market Microstructure** | 预测市场赔率与贝叶斯概率修正 | 实时赔率分布、概率边际突变捕捉与大额筹码沉淀点位分析 | 自动交易下单与无风控杠杆执行 | Agent 执行金融资产划转存在灾难级风险 | **绝对红线：READ / ANALYZE ONLY**，严禁挂载交易 API，保持纯粹客观研究定位。 |

