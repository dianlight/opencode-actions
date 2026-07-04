# opencode-actions
Main repository form my Opencode Github Actions to share to multiple repository and maintain in sync

## Model Recommendations by Task Type

> Automatically updated by `opencode-maintenance` workflow.
> Last updated: **2026-07-04 13:09 UTC**.
> LiveBench data: **127 models scored**.
> LiveBench snapshot: **2026_01_08**.
> Source: https://livebench.ai/table_2026_01_08.csv
> Free-first threshold: **5%**.

| Task Type | Description | Best Free Model | Free Score | Best Go Model | Go Score |
|-----------|-------------|-----------------|------------|---------------|----------|
| `issue-triage` | Triage, label, categorize, route issues | `deepseek-v4-flash-free` | 69.4 | `qwen3.7-max` | 76.6 |
| `issue-implementation` | Implement, fix, resolve issues | `deepseek-v4-flash-free` | 57.7 | `glm-5.2` | 75.9 |
| `pr-review` | Review PRs, pull requests, diffs | `deepseek-v4-flash-free` | 73.1 | `deepseek-v4-pro` | 83.9 |
| `code-implementation` | Generate code, refactor, implement features | `deepseek-v4-flash-free` | 57.7 | `glm-5.2` | 75.9 |
| `frontend-design` | UI design, components, layouts, mockups | `deepseek-v4-flash-free` | 46.9 | `glm-5` | 63.6 |
| `frontend-testing` | Playwright, Cypress, E2E, frontend tests | `deepseek-v4-flash-free` | 57.7 | `glm-5.2` | 75.9 |
| `api-testing` | API testing, integration tests, OpenAPI, Postman | `deepseek-v4-flash-free` | 57.7 | `glm-5.2` | 75.9 |
| `other` | Everything else | `deepseek-v4-flash-free` | 67.7 | `glm-5.2` | 76.2 |

### LiveBench Score Reference

| Model | Tier | Overall | Coding | Reasoning | Vision | Instruction Following |
|-------|------|---------|--------|-----------|--------|----------------------|
| `deepseek-v4-flash` | Go (Paid) | 67.7 | 57.7 | 73.1 | 46.9 | 69.4 |
| `deepseek-v4-flash-free` | Free | 67.7 | 57.7 | 73.1 | 46.9 | 69.4 |
| `deepseek-v4-pro` | Go (Paid) | 74.4 | 62.0 | 83.9 | 56.4 | 70.3 |
| `glm-5` | Go (Paid) | 68.7 | 62.5 | 74.0 | 63.6 | 65.0 |
| `glm-5.1` | Go (Paid) | 70.6 | 63.1 | 75.6 | 60.3 | 69.5 |
| `glm-5.2` | Go (Paid) | 76.2 | 75.9 | 82.1 | 60.7 | 68.2 |
| `hy3-preview` | Go (Paid) | — | — | — | — | — |
| `kimi-k2.5` | Go (Paid) | 69.2 | 60.1 | 76.7 | 55.0 | 65.3 |
| `kimi-k2.6` | Go (Paid) | 72.4 | 66.4 | 77.9 | 58.1 | 69.7 |
| `kimi-k2.7-code` | Go (Paid) | 71.9 | 71.6 | 76.9 | 55.7 | 65.9 |
| `mimo-v2-omni` | Go (Paid) | — | — | — | — | — |
| `mimo-v2-pro` | Go (Paid) | 58.4 | 45.5 | 65.8 | 43.6 | 57.8 |
| `mimo-v2.5` | Go (Paid) | — | — | — | — | — |
| `mimo-v2.5-free` | Free | — | — | — | — | — |
| `mimo-v2.5-pro` | Go (Paid) | — | — | — | — | — |
| `minimax-m2.5` | Go (Paid) | 60.3 | 59.3 | 62.3 | 31.3 | 62.2 |
| `minimax-m2.7` | Go (Paid) | 65.0 | 52.0 | 72.4 | 34.0 | 67.4 |
| `minimax-m3` | Go (Paid) | 70.1 | 63.3 | 76.7 | 50.2 | 66.9 |
| `nemotron-3-ultra-free` | Free | 50.7 | 56.5 | 42.9 | 36.5 | 62.5 |
| `north-mini-code-free` | Free | — | — | — | — | — |
| `qwen3.5-plus` | Go (Paid) | — | — | — | — | — |
| `qwen3.6-plus` | Go (Paid) | 70.8 | 64.3 | 77.0 | 52.5 | 67.7 |
| `qwen3.7-max` | Go (Paid) | 75.2 | 60.7 | 82.4 | 58.7 | 76.6 |
| `qwen3.7-plus` | Go (Paid) | — | — | — | — | — |

## Workflow Model Audit

> Audited: **2026-07-04 13:09 UTC**
> Workflows checked: **3**
> OpenCode steps found: **3**

| Workflow | Job | Step | Task Type | Current Model | Recommended Free | Recommended Go | Status |
|----------|-----|------|-----------|---------------|------------------|----------------|--------|
| `opencode-implement` | `implement` | `Run opencode (implementation only)` | `issue-implementation` | `opencode/deepseek-v4-flash-free` | `deepseek-v4-flash-free` | `glm-5.2` | ✅ |
| `opencode-review` | `review` | `step-1` | `pr-review` | `opencode/deepseek-v4-flash-free` | `deepseek-v4-flash-free` | `deepseek-v4-pro` | ✅ |
| `opencode-triage` | `triage` | `Run opencode (analysis & proposal only)` | `issue-triage` | `opencode/deepseek-v4-flash-free` | `deepseek-v4-flash-free` | `qwen3.7-max` | ✅ |

_Legend: ✅ Optimal · ⚠️ Suboptimal · ❌ Wrong (paying when free equivalent exists)_