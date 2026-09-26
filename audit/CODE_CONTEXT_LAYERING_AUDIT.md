# Code Context Layering & Architecture Audit

**Scope**: Hermes Code Agent Context Architecture Decoupling (V2.1 Hardening)  
**Standard**: FlapPearLabs Agent Governance Layering Model  

---

## 1. 核心架构四层分工模型 (4-Tier Context Decoupling)

为彻底解决提示词臃肿、规则冲突与代码漂移，Code Bot 严格实现以下四层解耦：

```text
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: SOUL.md (Who / Behavior)                               │
│ - Identity, behavioral invariants, direct tone, evidence creed   │
│ - Minimal tokens (~1KB), zero hardcoded file paths               │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ Layer 2: GLOBAL CODE CONTEXT (~/.hermes/profiles/code/AGENTS.md) │
│ - How engineering is governed across all projects               │
│ - Global Governance Pointer to canonical B/D layer              │
│ - Task classification & Risk-based closure policy               │
│ - Review execution contract & Dual-layer architecture           │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ Layer 3: REPO CONTEXT (<repo>/AGENTS.md, CLAUDE.md, docs/agents)│
│ - How THIS specific repository works                            │
│ - Architecture seams, package managers, test entrypoints        │
│ - Local domain invariants, local triage labels                  │
└────────────────────────────────┬────────────────────────────────┘
                                 │
┌────────────────────────────────▼────────────────────────────────┐
│ Layer 4: SKILLS (~/.hermes/skills/ or repo skills)              │
│ - How a SPECIFIC operation is performed                         │
│ - Matt Pocock primitives: to-spec, to-tickets, tdd, code-review │
│ - Ephemeral execution procedures, no governance override        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 运行时指令与工程事实权威的双维度解耦 (Two Orthogonal Authority Dimensions)

### 维度 A: 运行时上下文加载顺序 (Runtime Context Precedence)
由 Hermes Runtime 机械加载控制：
$$\text{System Core Prompt} \rightarrow \text{Out-of-Band User Message} \rightarrow \text{User Message} \rightarrow \text{Directory-Scoped AGENTS.md} \rightarrow \text{Profile AGENTS.md} \rightarrow \text{Skills}$$
*规则：下游指令不得伪造系统级事件；用户实时转向指令（Out-of-band）具备即时最高转向权威。*

### 维度 B: 软件工程事实源权威 (Engineering Artifact Authority)
由 `agent-engineering-governance` 定义的真理事实链：
$$\text{Approved Spec / ADR} > \text{Baseline Test Suite} > \text{Repo Architecture Docs} > \text{Existing Code Implementation} > \text{Ephemeral Chat Context}$$
*规则：代码实现不一致时，以 Approved Spec/Tests 为准；聊天记录不能推翻代码库持久化的 ADR。*

---

## 3. Governance Pointer 动态指针机制
- Code Bot 绝对不将数十页的 `RULES.md` 和 `AGENTS.md` 硬编码拷贝到 SOUL 或 Profile 中。
- 动态指针固定指向：`/Users/songshiyao/Desktop/Projects/agent-engineering-governance/`。
- 只有在执行 `FEATURE`, `REFACTOR`, `ARCHITECTURAL_CHANGE`, `REVIEW`, `REPAIR`, `INTEGRATION` 等核心任务时，才按需读取最新规则。TRIVIAL_CHANGE 保持轻量执行。这确保治理规则更新时，所有下游 Bot 零漂移同步生效。
