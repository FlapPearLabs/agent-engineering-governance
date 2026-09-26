# Hermes Multi-Profile & Bot Roster Audit Report

**Audit Date**: 2026-09-25  
**Auditor**: Hermes Agent Core Architecture  
**Target Environment**: macOS 26.2 (Darwin) / Desktop Hermes  
**Auditing Entity**: FlapPearLabs Governance Center  

---

## 1. Executive Summary

This document presents the full architectural audit, profile specification, skill allocation matrix, and workspace breakdown for the newly established Hermes Multi-Bot System.

A multi-bot architecture has been initialized on top of the host Hermes environment using strict **Profile Isolation**. The deployment establishes six dedicated roles:
1. `default`: Personal Chief of Staff / Generalist Manager
2. `code`: Dedicated Software Engineering Agent
3. `media`: Media Strategy, Scripting, and Visual Production Agent
4. `research`: Evidence-First Intelligence & Research Agent
5. `edu`: Curriculum Architecture & Learning Closed-Loop Agent
6. `markets`: Macroeconomic & Asset Research Agent (Read-Only)

All six profiles have passed syntax assertions, memory isolation gates, tool/MCP configuration audits, and local smoke tests.

---

## 2. Profile Architecture & Isolation Gates

In Hermes, a Bot corresponds 1:1 to an underlying Profile. Each profile is physically isolated at `~/.hermes/profiles/<name>/` (with `default` at `~/.hermes/`):

- **SOUL.md**: Distinct identity and governance constraints.
- **config.yaml**: Independent model routing, toolsets, and MCP configurations.
- **profile.yaml**: Canonical metadata for Hermes Desktop Bot Mode roster.
- **memories/**: Fully isolated memory directory. For all newly generated profiles (`code`, `media`, `research`, `edu`, `markets`), default memory was uninherited and zeroed to prevent context pollution and token waste.
- **state.db & sessions**: Separate session lifecycles. Default retains cross-project user history; satellite bots operate within fresh canonical lifecycles.

---

## 3. Bot Detailed Profiles

### 3.1 Default (`default`)
- **Profile Path**: `/Users/songshiyao/.hermes/`
- **Display Name**: Default
- **Role**: PERSONAL_CHIEF_OF_STAFF
- **Mandate**: Long-term memory keeper, decision continuity, cross-project orchestration, career advice, and high-level routing.
- **Model**: `gemini-3.8-flash-tiered` (via Antigravity custom provider)
- **Active MCP**: `agentmemory`, `codegraph`, `chrome-devtools`
- **Memory Status**: Full historical memory preserved (100% intact).

### 3.2 Code (`code`)
- **Profile Path**: `/Users/songshiyao/.hermes/profiles/code/`
- **Display Name**: Code
- **Role**: DEDICATED_SOFTWARE_ENGINEER
- **Mandate**: Production repo implementation, testing, code review, PR & CI conformance.
- **Governance Reference**: Follows `/Users/songshiyao/Desktop/Projects/agent-engineering-governance/AGENTS.md`.
- **Hard Rules**: Spec/Ticket first; Contract before code; Counterexample first (RED -> GREEN); Self-review != Independent review; Exact-SHA PASS binding; No false closure; No force push.
- **Model**: `gemini-3.8-flash-tiered` (with fast access to `sonnet` / `pro-high` aliases)
- **Active MCP**: `codegraph`, `agentmemory`, `chrome-devtools`
- **Memory Status**: Isolated, zeroed default memories.

### 3.3 Media (`media`)
- **Profile Path**: `/Users/songshiyao/.hermes/profiles/media/`
- **Display Name**: Media
- **Role**: MEDIA_STRATEGIST & VISUAL_PRODUCER
- **Mandate**: Authentic storytelling, topic verification, scripts, Xiaohongshu/WeChat layout, video pipelines.
- **Hard Rules**: Anti-marketing buzzwords; No fabricated case studies; Professional, cool, engineering-grounded tone; Less chicken soup.
- **Model**: `gemini-3.8-flash-tiered` + Edge-TTS pipeline
- **Active MCP**: `chrome-devtools` (Preview/DOM)
- **Workspace**: Dedicated directory structure at `~/.hermes/profiles/media/workspace/` with `ideas/`, `research/`, `scripts/`, `assets/`, `video-projects/`, `published/`, `analytics/`, `experiments/`.
- **Memory Status**: Isolated, zeroed default memories.

### 3.4 Research (`research`)
- **Profile Path**: `/Users/songshiyao/.hermes/profiles/research/`
- **Display Name**: Research
- **Role**: EVIDENCE_FIRST_INTELLIGENCE_ANALYST
- **Mandate**: AI frontiers, academic papers, OSINT, competitive research, technology scouting.
- **Hard Rules**: Primary sources first (official docs, papers, source code, filings); Social media downgraded to sentiment indicator only; Explicit timestamping; 4-tier output schema (FACT, EVIDENCE, INFERENCE, UNCERTAINTY).
- **Model**: `gemini-3.8-flash-tiered`
- **Active MCP**: `chrome-devtools`
- **Memory Status**: Isolated, zeroed default memories.

### 3.5 Edu (`edu`)
- **Profile Path**: `/Users/songshiyao/.hermes/profiles/edu/`
- **Display Name**: Edu
- **Role**: CURRICULUM_ARCHITECT & LEARNING_ENGINEER
- **Mandate**: AI literacy curriculum, teacher/parent guides, English training loops, US driver exam guides.
- **Hard Rules**: Real beginner state first; Diagnostic -> Weakness ledger -> Targeted intervention -> Output test -> Delayed retest (D+1/D+3/D+7) -> Acceptance.
- **Model**: `gemini-3.8-flash-tiered`
- **Active MCP**: `chrome-devtools`
- **Memory Status**: Isolated, zeroed default memories.

### 3.6 Markets (`markets`)
- **Profile Path**: `/Users/songshiyao/.hermes/profiles/markets/`
- **Display Name**: Markets
- **Role**: MACROECONOMIC_RESEARCHER (READ-ONLY)
- **Mandate**: Macro indicators (CPI, NFP, Fed), Polymarket prediction tracking, risk asset correlations.
- **Hard Rules**: Strict ESR Framework (Event -> Expectation -> Surprise -> Positioning -> Price Response -> 2nd Order Effect); READ / ANALYZE ONLY; Zero automated trading authorization.
- **Model**: `gemini-3.8-flash-tiered`
- **Active MCP**: `chrome-devtools` (Read-only)
- **Memory Status**: Isolated, zeroed default memories.

---

## 4. Bot × MCP Matrix

| Profile | `agentmemory` | `codegraph` | `chrome-devtools` | Rationale & Privilege Surface |
| :--- | :---: | :---: | :---: | :--- |
| **`default`** | [X] | [X] | [X] | Comprehensive visibility for Chief of Staff orchestration. |
| **`code`** | [X] | [X] | [X] | Code navigation, symbol resolution, persistent session logs. |
| **`media`** | [ ] | [ ] | [X] | Stripped dev tools; retained browser for visual rendering & preview. |
| **`research`**| [ ] | [ ] | [X] | Retained browser for deep web retrieval & paywall/DOM navigation. |
| **`edu`** | [ ] | [ ] | [X] | Retained browser for courseware inspection and doc rendering. |
| **`markets`** | [ ] | [ ] | [X] | Read-only browser for real-time dashboards; zero trading write tools. |

---

## 5. Machine Skills Audit & Distribution

### 5.1 Engineering Suite (Matt Pocock Skills)
- **Status**: PRESENT (Native in Hermes default environment)
- **Assigned Bot**: `code` (Primary), `default` (Orchestration)
- **Key Skills**:
  - `to-spec` / `to-tickets`: PRD & issue contract decomposition.
  - `tdd`: Test-driven development loop (RED -> GREEN -> REFACTOR).
  - `code-review`: Independent, read-only exact-SHA verification.
  - `grilling`: Relentless requirement clarification before execution.
  - `writing-plans` / `wayfinder`: Complex codebase navigation.
  - `impeccable`: Frontend craft and UI polish.

### 5.2 Media & Visual Production
- **Status**: PRESENT (Hybrid native + local tools)
- **Assigned Bot**: `media`
- **Key Skills**:
  - `huashu-mac-use`: Native desktop UI drive & capture.
  - `animate` / `animate-expo`: Web and React Native animation architecture.
  - `architecture-diagram` / `excalidraw`: System & flow visualization.
  - `text_to_speech`: High-fidelity edge-tts narration pipeline.

### 5.3 Research & Discovery
- **Status**: PRESENT
- **Assigned Bot**: `research`
- **Key Skills**:
  - `deep-research`: Multi-agent recursive web and literature scouting.
  - `arxiv`: Academic paper search, download, and metadata parse.
  - `global-biblio-base`: Access to global academic journals and literature.

### 5.4 Education & Learning Systems
- **Status**: PRESENT
- **Assigned Bot**: `edu`
- **Key Skills**:
  - `teach`: Interactive learning and concept breakdown.
  - `teachany`: Courseware design for K-12, higher ed, and adult AI literacy.
  - `scaffold-exercises`: Progressive diagnostic test scaffolding.

### 5.5 Macro & Markets
- **Status**: PRESENT
- **Assigned Bot**: `markets`
- **Key Skills**:
  - `polymarket`: Prediction market orderbook and probability tracking.
  - Macro data research and cross-asset correlation analysis.

---

## 6. Workspace & File System Architecture

```text
/Users/songshiyao/.hermes/
├── config.yaml            # Default profile config (Antigravity provider, toolsets)
├── profile.yaml           # Default metadata for Bot Mode
├── memories/              # Default curated persistent memories
├── skills/                # Shared & custom skills
└── profiles/              # Isolated satellite bots
    ├── code/
    │   ├── config.yaml    # Code engineering config
    │   ├── profile.yaml   # Code Bot Mode metadata
    │   ├── SOUL.md        # Governance & Codex-style engineering SOUL
    │   └── memories/      # Clean isolated memory (no default leakage)
    ├── media/
    │   ├── config.yaml    # Media & TTS config
    │   ├── profile.yaml   # Media Bot Mode metadata
    │   ├── SOUL.md        # Authentic, anti-AI-tone content SOUL
    │   ├── memories/      # Clean isolated memory
    │   └── workspace/     # Physical assets repository
    │       ├── ideas/
    │       ├── research/
    │       ├── scripts/
    │       ├── assets/
    │       ├── video-projects/
    │       ├── published/
    │       ├── analytics/
    │       └── experiments/
    ├── research/
    │   ├── config.yaml    # Research-tuned toolsets
    │   ├── profile.yaml   # Research Bot Mode metadata
    │   ├── SOUL.md        # Primary-sources-first intelligence SOUL
    │   └── memories/      # Clean isolated memory
    ├── edu/
    │   ├── config.yaml    # Educational toolsets
    │   ├── profile.yaml   # Edu Bot Mode metadata
    │   ├── SOUL.md        # Learning closed-loop & diagnostic SOUL
    │   └── memories/      # Clean isolated memory
    └── markets/
        ├── config.yaml    # Read-only market analysis config
        ├── profile.yaml   # Markets Bot Mode metadata
        ├── SOUL.md        # ESR framework & zero-trade SOUL
        └── memories/      # Clean isolated memory
```

---

## 7. Verification & Smoke Test Results

1. **`hermes profile list` Assertion**:
   - `default`: Active / Running (Model: `gemini-3.8-flash-tiered`)
   - `code`: Initialized / Validated
   - `media`: Initialized / Validated
   - `research`: Initialized / Validated
   - `edu`: Initialized / Validated
   - `markets`: Initialized / Validated
2. **Governance Audit on `code`**:
   - Checked against `/Users/songshiyao/Desktop/Projects/agent-engineering-governance/AGENTS.md`. Confirmed authority hierarchy, exact-SHA binding, and non-self review doctrines are embedded.
3. **Workspace Integrity on `media`**:
   - Confirmed directory hierarchy in `workspace/` exists and is ready for programmatic artifact writes.
4. **Safety & Security Assertion**:
   - Zero credentials, secrets, or API keys were printed or leaked into audit manifests or git trees.
   - All models leverage authenticated local proxy routing (`custom:antigravity`).

---

## 8. Review Checklist for External Auditor (ChatGPT)

To the reviewing LLM (ChatGPT):
Please verify this implementation against production multi-agent standards:
1. **Isolation**: Are system prompts, memory paths, and session state machines properly segregated across profiles?
2. **Blast Radius**: Is the tool surface for `markets` properly restricted from executing trades, and is `media` stripped of unnecessary infrastructure code tools?
3. **Engineering Integrity**: Does the `code` bot definition comply with test-driven, verifiable pull-request governance instead of free-wheeling code hallucinations?
4. **Pragmatism**: Is the default personal chief of staff protected from token bloat and context poisoning?

