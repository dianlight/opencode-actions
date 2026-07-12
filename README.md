# opencode-actions
Main repository form my Opencode Github Actions to share to multiple repository and maintain in sync

## Documentation

- [**Workflow Flows**](.github/workflows/WORKFLOWS.md) — End-to-end diagrams and
  descriptions of the six-process automation pipeline (review → discuss → work → task).

## Model Recommendations by Task Type

> Automatically updated by `opencode-maintenance` workflow.
> Last updated: **2026-07-12 14:20 UTC**.
> LiveBench data: **121 models scored**.
> LiveBench snapshot: **2026_01_08**.
> Source: https://livebench.ai/table_2026_01_08.csv
> Free-first threshold: **5%**.

| Task Type | Description | Best Zen Model | Zen Score | Best Free Model | Free Score | Best Go Model | Go Score |
|-----------|-------------|----------------|-----------|-----------------|------------|---------------|----------|
| `Plan` | Planning, architecture decisions, task decomposition | `gpt-5.5` | 89.5 | `deepseek-v4-flash-free` | 73.1 | 🏆 `deepseek-v4-pro` | 83.9 |
| `Ask` | General Q&A, explanations, analysis | `gemini-3.1-pro` | 79.6 | `deepseek-v4-flash-free` | 69.4 | 🏆 `qwen3.7-max` | 76.6 |
| `Code` | Code generation, implementation, refactoring | `claude-opus-4-7` | 70.3 | `deepseek-v4-flash-free` | 57.7 | 🏆 `kimi-k2.6` | 66.4 |
| `issue-triage` | Triage, label, categorize, route issues | `gemini-3.1-pro` | 79.6 | `deepseek-v4-flash-free` | 69.4 | 🏆 `qwen3.7-max` | 76.6 |
| `issue-implementation` | Implement, fix, resolve issues | `claude-opus-4-7` | 70.3 | `deepseek-v4-flash-free` | 57.7 | 🏆 `kimi-k2.6` | 66.4 |
| `pr-review` | Review PRs, pull requests, diffs | `gpt-5.5` | 89.5 | `deepseek-v4-flash-free` | 73.1 | 🏆 `deepseek-v4-pro` | 83.9 |
| `code-implementation` | Generate code, refactor, implement features | `claude-opus-4-7` | 70.3 | `deepseek-v4-flash-free` | 57.7 | 🏆 `kimi-k2.6` | 66.4 |
| `frontend-design` | UI design, components, layouts, mockups | `gpt-5.5` | 76.3 | `mimo-v2.5-free` | 54.0 | 🏆 `glm-5.2` | 63.6 |
| `frontend-testing` | Playwright, Cypress, E2E, frontend tests | `claude-opus-4-7` | 70.3 | `deepseek-v4-flash-free` | 57.7 | 🏆 `kimi-k2.6` | 66.4 |
| `api-testing` | API testing, integration tests, OpenAPI, Postman | `claude-opus-4-7` | 70.3 | `deepseek-v4-flash-free` | 57.7 | 🏆 `kimi-k2.6` | 66.4 |
| `other` | Everything else | `gemini-3.1-pro` | 80.7 | `deepseek-v4-flash-free` | 67.7 | 🏆 `qwen3.7-max` | 75.2 |

### LiveBench Score Reference

| Model | Tier | Source | Best For | Overall | Coding | Reasoning | Vision | Instruction Following |
|-------|------|--------|----------|---------|--------|-----------|--------|----------------------|
| `deepseek-v4-flash` | Go (Paid) | ✅ LiveBench | Plan, Review | 67.7 | 57.7 | 73.1 | 46.9 | 69.4 |
| `deepseek-v4-flash-free` | Free | ✅ LiveBench | Plan, Review | 67.7 | 57.7 | 73.1 | 46.9 | 69.4 |
| `deepseek-v4-pro` | Go (Paid) | ✅ LiveBench | Plan, Review | 74.4 | 62.0 | 83.9 | 56.4 | 70.3 |
| `glm-5` | Go (Paid) | ✅ LiveBench | Plan, Review | 68.7 | 62.5 | 74.0 | 63.6 | 65.0 |
| `glm-5.1` | Go (Paid) | ✅ LiveBench | Plan, Review | 70.6 | 63.1 | 75.6 | 60.3 | 69.5 |
| `glm-5.2` | Go (Paid) | ✅ LiveBench | Plan, Review | 68.7 | 62.5 | 74.0 | 63.6 | 65.0 |
| `hy3-free` | Free | 📋 Fallback | Plan, Review | 54.0 | 55.0 | 60.0 | 8.0 | 58.0 |
| `hy3-preview` | Go (Paid) | 📋 Fallback | Plan, Review | 54.0 | 55.0 | 60.0 | 8.0 | 58.0 |
| `kimi-k2.5` | Go (Paid) | ✅ LiveBench | Plan, Review | 69.2 | 60.1 | 76.7 | 55.0 | 65.3 |
| `kimi-k2.6` | Go (Paid) | ✅ LiveBench | Plan, Review | 72.4 | 66.4 | 77.9 | 58.1 | 69.7 |
| `kimi-k2.7-code` | Go (Paid) | 📋 Fallback | Code, Impl | 58.0 | 61.0 | 55.0 | 48.0 | 58.0 |
| `mimo-v2-omni` | Go (Paid) | 📋 Fallback | Design, Ask | 50.0 | 42.0 | 48.0 | 55.0 | 50.0 |
| `mimo-v2-pro` | Go (Paid) | ✅ LiveBench | Plan, Review | 58.4 | 45.5 | 65.8 | 43.6 | 57.8 |
| `mimo-v2.5` | Go (Paid) | 📋 Fallback | Ask, Triage | 62.0 | 60.0 | 64.0 | 58.0 | 65.0 |
| `mimo-v2.5-free` | Free | 📋 Fallback | Ask, Triage | 58.0 | 56.0 | 60.0 | 54.0 | 62.0 |
| `mimo-v2.5-pro` | Go (Paid) | 📋 Fallback | Ask, Triage | 68.0 | 66.0 | 70.0 | 55.0 | 74.0 |
| `minimax-m2.5` | Go (Paid) | ✅ LiveBench | Plan, Review | 60.3 | 59.3 | 62.3 | 31.3 | 62.2 |
| `minimax-m2.7` | Go (Paid) | ✅ LiveBench | Plan, Review | 65.0 | 52.0 | 72.4 | 34.0 | 67.4 |
| `minimax-m3` | Go (Paid) | ✅ LiveBench | Plan, Review | 70.1 | 63.3 | 76.7 | 50.2 | 66.9 |
| `nemotron-3-ultra-free` | Free | ✅ LiveBench | Ask, Triage | 50.7 | 56.5 | 42.9 | 36.5 | 62.5 |
| `north-mini-code-free` | Free | 📋 Fallback | Ask, Triage | 32.0 | 35.0 | 38.0 | 5.0 | 40.0 |
| `qwen3.5-plus` | Go (Paid) | 📋 Fallback | Plan, Review | 58.0 | 52.0 | 62.0 | 42.0 | 60.0 |
| `qwen3.6-plus` | Go (Paid) | ✅ LiveBench | Plan, Review | 70.8 | 64.3 | 77.0 | 52.5 | 67.7 |
| `qwen3.7-max` | Go (Paid) | ✅ LiveBench | Plan, Review | 75.2 | 60.7 | 82.4 | 58.7 | 76.6 |
| `qwen3.7-plus` | Go (Paid) | 📋 Fallback | Plan, Ask | 66.0 | 62.0 | 72.0 | 62.0 | 72.0 |

## Workflow Model Audit

> Audited: **2026-07-12 14:20 UTC**
> Workflows checked: **3**
> OpenCode steps found: **6**

| Workflow | Job | Step | Task Type | Current Model | Recommended Zen | Recommended Free | Recommended Go | Status |
|----------|-----|------|-----------|---------------|-----------------|------------------|----------------|--------|
| `opencode-issue-handler` | `process-4` | `Run opencode (Process 4 — Issue Review & Refinement)` | `issue-triage` | `opencode/deepseek-v4-flash-free` | `gemini-3.1-pro` (+15%) | `deepseek-v4-flash-free` | 🏆 `qwen3.7-max` (+10%) | ✅ |
| `opencode-issue-handler` | `process-5` | `Run opencode (Process 5 — Issue Work & PR Creation)` | `issue-implementation` | `opencode/north-mini-code-free` | `claude-opus-4-7` (+101%) | `deepseek-v4-flash-free` | 🏆 `kimi-k2.6` (+15%) | ⚠️ |
| `opencode-pr-comment` | `process-2` | `Run opencode (Process 2 — Bot thread reply)` | `pr-review` | `opencode/deepseek-v4-flash-free` | `gpt-5.5` (+22%) | `deepseek-v4-flash-free` | 🏆 `deepseek-v4-pro` (+15%) | ✅ |
| `opencode-pr-comment` | `process-3` | `Run opencode (Process 3 — User-owned thread takeover)` | `pr-review` | `opencode/deepseek-v4-flash-free` | `gpt-5.5` (+22%) | `deepseek-v4-flash-free` | 🏆 `deepseek-v4-pro` (+15%) | ✅ |
| `opencode-pr-comment` | `process-6` | `Run opencode (Process 6 — PR Task Execution)` | `code-implementation` | `opencode/north-mini-code-free` | `claude-opus-4-7` (+101%) | `deepseek-v4-flash-free` | 🏆 `kimi-k2.6` (+15%) | ⚠️ |
| `opencode-pr-review` | `review` | `Run opencode (PR code review)` | `pr-review` | `opencode/deepseek-v4-flash-free` | `gpt-5.5` (+22%) | `deepseek-v4-flash-free` | 🏆 `deepseek-v4-pro` (+15%) | ✅ |

_Legend: ✅ Optimal · ⚠️ Suboptimal · ❌ Wrong (paying when free equivalent exists). 🏆 marks the preferred model after free-first policy (free within 5% of best Go → prefer free). Recommended Zen shows best Zen model with score difference vs current model (e.g., `model (+15%)`)._