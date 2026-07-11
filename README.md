# opencode-actions
Main repository form my Opencode Github Actions to share to multiple repository and maintain in sync

## Documentation

- [**Workflow Flows**](.github/workflows/WORKFLOWS.md) — End-to-end diagrams and
  descriptions of the six-process automation pipeline (review → discuss → work → task).

## Model Recommendations by Task Type

> Automatically updated by `opencode-maintenance` workflow.
> Last updated: **2026-07-11 09:37 UTC**.
> LiveBench data: **121 models scored**.
> LiveBench snapshot: **2026_01_08**.
> Source: https://livebench.ai/table_2026_01_08.csv
> Free-first threshold: **5%**.

| Task Type | Description | Best Zen Model | Zen Score | Best Free Model | Free Score | Best Go Model | Go Score |
|-----------|-------------|----------------|-----------|-----------------|------------|---------------|----------|
| `issue-triage` | Triage, label, categorize, route issues | `gemini-3.1-pro` | 79.6 | `deepseek-v4-flash-free` | 69.4 | `qwen3.7-max` | 76.6 |
| `issue-implementation` | Implement, fix, resolve issues | `claude-opus-4-7` | 70.3 | `north-mini-code-free` | 68.0 | `north-mini-code-free` | 68.0 |
| `pr-review` | Review PRs, pull requests, diffs | `gpt-5.5` | 89.5 | `deepseek-v4-flash-free` | 73.1 | `deepseek-v4-pro` | 83.9 |
| `code-implementation` | Generate code, refactor, implement features | `claude-opus-4-7` | 70.3 | `north-mini-code-free` | 68.0 | `north-mini-code-free` | 68.0 |
| `frontend-design` | UI design, components, layouts, mockups | `gpt-5.5` | 76.3 | `deepseek-v4-flash-free` | 46.9 | `glm-5.2` | 63.6 |
| `frontend-testing` | Playwright, Cypress, E2E, frontend tests | `claude-opus-4-7` | 70.3 | `north-mini-code-free` | 68.0 | `north-mini-code-free` | 68.0 |
| `api-testing` | API testing, integration tests, OpenAPI, Postman | `claude-opus-4-7` | 70.3 | `north-mini-code-free` | 68.0 | `north-mini-code-free` | 68.0 |
| `other` | Everything else | `gemini-3.1-pro` | 80.7 | `deepseek-v4-flash-free` | 67.7 | `qwen3.7-max` | 75.2 |

### LiveBench Score Reference

| Model | Tier | Source | Best For | Overall | Coding | Reasoning | Vision | Instruction Following |
|-------|------|--------|----------|---------|--------|-----------|--------|----------------------|
| `deepseek-v4-flash` | Go (Paid) | ✅ LiveBench | — | 67.7 | 57.7 | 73.1 | 46.9 | 69.4 |
| `deepseek-v4-flash-free` | Free | ✅ LiveBench | — | 67.7 | 57.7 | 73.1 | 46.9 | 69.4 |
| `deepseek-v4-pro` | Go (Paid) | ✅ LiveBench | — | 74.4 | 62.0 | 83.9 | 56.4 | 70.3 |
| `glm-5` | Go (Paid) | ✅ LiveBench | — | 68.7 | 62.5 | 74.0 | 63.6 | 65.0 |
| `glm-5.1` | Go (Paid) | ✅ LiveBench | — | 70.6 | 63.1 | 75.6 | 60.3 | 69.5 |
| `glm-5.2` | Go (Paid) | ✅ LiveBench | — | 68.7 | 62.5 | 74.0 | 63.6 | 65.0 |
| `hy3-free` | Free | 📋 Fallback | — | 55.0 | 50.0 | 60.0 | 40.0 | 55.0 |
| `hy3-preview` | Go (Paid) | 📋 Fallback | — | 55.0 | 50.0 | 60.0 | 40.0 | 55.0 |
| `kimi-k2.5` | Go (Paid) | ✅ LiveBench | — | 69.2 | 60.1 | 76.7 | 55.0 | 65.3 |
| `kimi-k2.6` | Go (Paid) | ✅ LiveBench | — | 72.4 | 66.4 | 77.9 | 58.1 | 69.7 |
| `kimi-k2.7-code` | Go (Paid) | ❌ Missing | — | — | — | — | — | — |
| `mimo-v2-omni` | Go (Paid) | 📋 Fallback | — | 60.0 | 46.0 | 66.0 | 55.0 | 58.0 |
| `mimo-v2-pro` | Go (Paid) | ✅ LiveBench | — | 58.4 | 45.5 | 65.8 | 43.6 | 57.8 |
| `mimo-v2.5` | Go (Paid) | 📋 Fallback | — | 62.0 | 50.0 | 68.0 | 48.0 | 60.0 |
| `mimo-v2.5-free` | Free | 📋 Fallback | — | 60.0 | 48.0 | 66.0 | 46.0 | 59.0 |
| `mimo-v2.5-pro` | Go (Paid) | 📋 Fallback | — | 66.0 | 55.0 | 72.0 | 52.0 | 63.0 |
| `minimax-m2.5` | Go (Paid) | ✅ LiveBench | — | 60.3 | 59.3 | 62.3 | 31.3 | 62.2 |
| `minimax-m2.7` | Go (Paid) | ✅ LiveBench | — | 65.0 | 52.0 | 72.4 | 34.0 | 67.4 |
| `minimax-m3` | Go (Paid) | ✅ LiveBench | — | 70.1 | 63.3 | 76.7 | 50.2 | 66.9 |
| `nemotron-3-ultra-free` | Free | ✅ LiveBench | — | 50.7 | 56.5 | 42.9 | 36.5 | 62.5 |
| `north-mini-code-free` | Free | 📋 Fallback | — | 60.0 | 68.0 | 55.0 | 35.0 | 58.0 |
| `qwen3.5-plus` | Go (Paid) | 📋 Fallback | — | 68.0 | 62.0 | 75.0 | 50.0 | 65.0 |
| `qwen3.6-plus` | Go (Paid) | ✅ LiveBench | — | 70.8 | 64.3 | 77.0 | 52.5 | 67.7 |
| `qwen3.7-max` | Go (Paid) | ✅ LiveBench | — | 75.2 | 60.7 | 82.4 | 58.7 | 76.6 |
| `qwen3.7-plus` | Go (Paid) | 📋 Fallback | — | 72.0 | 62.0 | 80.0 | 55.0 | 72.0 |

## Workflow Model Audit

> Audited: **2026-07-11 09:37 UTC**
> Workflows checked: **4**
> OpenCode steps found: **4**

| Workflow | Job | Step | Task Type | Current Model | Recommended Free | Recommended Go | Status |
|----------|-----|------|-----------|---------------|------------------|----------------|--------|
| `opencode-pr-review` | `review` | `Run opencode (PR code review)` | `pr-review` | `opencode/deepseek-v4-flash-free` | `deepseek-v4-flash-free` | 🏆 `deepseek-v4-pro` (+15%) | ✅ |
| `opencode-pr-comment` | `process-6` | `Run opencode (Process 6)` | `pr-review` | `opencode/north-mini-code-free` | `north-mini-code-free` | 🏆 `glm-5.2` (+12%) | ✅ |
| `opencode-issue-handler` | `process-4` | `Run opencode (Process 4)` | `issue-triage` | `opencode/deepseek-v4-flash-free` | `deepseek-v4-flash-free` | 🏆 `qwen3.7-max` (+10%) | ✅ |
| `opencode-issue-handler` | `process-5` | `Run opencode (Process 5)` | `issue-implementation` | `opencode/north-mini-code-free` | `north-mini-code-free` | 🏆 `glm-5.2` (+12%) | ✅ |

_Legend: ✅ Optimal · ⚠️ Suboptimal · ❌ Wrong (paying when free equivalent exists). 🏆 marks the preferred model after free-first policy (free within 5% of best Go → prefer free). Zen vs Current: +X% means the best Zen model scores X% higher than the current model._