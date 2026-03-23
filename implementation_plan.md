# ASKTHEPEOPLE — Complete Rebrand & Redesign Plan

## What This App Does (Current State)

This is a **multi-agent social simulation engine**. Users upload documents (news articles, reports), and the system:

1. **Builds a knowledge graph** from the document (entities, relationships)
2. **Generates AI agent profiles** (simulated people with personalities & memories)
3. **Runs a social media simulation** (agents post, comment, react on Twitter/Reddit-like platforms)
4. **Produces a prediction report** via a ReportAgent that analyzes the simulation
5. **Allows interactive Q&A** with individual agents and the ReportAgent

The entire UI is in **Chinese**. The brand is **MiroFish** ("Predict Everything"), affiliated with **Shanda Group** and GitHub user **666ghj**.

---

## Scope of Rebrand

### Layer 1: Surface Text (40+ files)

| Location | What to change |
| :--- | :--- |
| [frontend/index.html](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/index.html) | Title, meta description |
| [frontend/src/views/Home.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/views/Home.vue) | Navbar brand `MIROFISH`, hero text, logo `<img>`, GitHub link, engine badge `MiroFish-V1.0`, all Chinese marketing copy |
| [frontend/src/views/MainView.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/views/MainView.vue) | Navbar `MIROFISH` |
| [frontend/src/views/SimulationView.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/views/SimulationView.vue) | Navbar `MIROFISH` |
| [frontend/src/views/SimulationRunView.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/views/SimulationRunView.vue) | Navbar `MIROFISH` |
| [frontend/src/views/ReportView.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/views/ReportView.vue) | Navbar `MIROFISH` |
| [frontend/src/views/InteractionView.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/views/InteractionView.vue) | Navbar `MIROFISH` |
| [frontend/src/views/Process.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/views/Process.vue) | Navbar `MIROFISH` |
| [frontend/src/components/Step2EnvSetup.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step2EnvSetup.vue) | `Automated planning simulating reality...` description text |
| [frontend/src/components/Step5Interaction.vue](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step5Interaction.vue) | `Has the complete memory of the simulation` description text |
| [package.json](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/package.json) | `"name": "mirofish"`, `"description"` |
| [docker-compose.yml](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/docker-compose.yml) | `image: ghcr.io/666ghj/mirofish`, `container_name: mirofish` |
| [.github/workflows/docker-image.yml](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/.github/workflows/docker-image.yml) | `images: ghcr.io/.../mirofish` |

### Layer 2: Internal Code References (Backend)

| File | What to change |
| :--- | :--- |
| [backend/pyproject.toml](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/pyproject.toml) | `name = "mirofish-backend"`, description, authors |
| [backend/requirements.txt](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/requirements.txt) | Header comment `MiroFish Backend Dependencies` |
| [backend/app/**init**.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/__init__.py) | Docstring, [setup_logger('mirofish')](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/utils/logger.py#30-89), startup logs `MiroFish Backend`, health check `'service': 'MiroFish Backend'` |
| [backend/app/config.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/config.py) | Comment `MiroFish/.env`, `SECRET_KEY` default `'mirofish-secret-key'` |
| [backend/app/utils/logger.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/utils/logger.py) | Default logger name `'mirofish'` in [setup_logger()](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/utils/logger.py#30-89) and [get_logger()](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/utils/logger.py#91-105) |
| [backend/run.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/run.py) | Docstring `MiroFish Backend Startup Entry` |
| [backend/app/api/graph.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/api/graph.py) | Logger `'mirofish.api'`, default graph name `'MiroFish Graph'`, build logger `'mirofish.build'` |
| [backend/app/api/simulation.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/api/simulation.py) | Logger `'mirofish.api.simulation'`, docstring examples `"graph_id": "mirofish_xxxx"` |
| [backend/app/api/report.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/api/report.py) | Logger `'mirofish.api.report'`, docstring examples `"graph_id": "mirofish_xxxx"` |
| [backend/app/services/graph_builder.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/graph_builder.py) | Default `graph_name = "MiroFish Graph"`, ID prefix `mirofish_`, description `"MiroFish Social Simulation Graph"` |
| [backend/app/services/ontology_generator.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/ontology_generator.py) | `'Automatically generated for social simulation'` |
| [backend/app/services/simulation_manager.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/simulation_manager.py) | `conda activate MiroFish`, logger `'mirofish.simulation'` |
| [backend/app/services/simulation_runner.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/simulation_runner.py) | Logger `'mirofish.simulation_runner'` |
| [backend/app/services/simulation_config_generator.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/simulation_config_generator.py) | Logger `'mirofish.simulation_config'` |
| [backend/app/services/simulation_ipc.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/simulation_ipc.py) | Logger `'mirofish.simulation_ipc'` |
| [backend/app/services/report_agent.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/report_agent.py) | Logger `'mirofish.report_agent'`, log filter names |
| [backend/app/services/oasis_profile_generator.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/oasis_profile_generator.py) | Logger `'mirofish.oasis_profile'` |
| [backend/app/services/zep_tools.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/zep_tools.py) | Logger `'mirofish.zep_tools'` |
| [backend/app/services/zep_graph_memory_updater.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/zep_graph_memory_updater.py) | Logger `'mirofish.zep_graph_memory_updater'` |
| [backend/app/services/zep_entity_reader.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/zep_entity_reader.py) | Logger `'mirofish.zep_entity_reader'` |

### Layer 3: External Affiliations to Purge

| Item | Action |
| :--- | :--- |
| [README.md](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/README.md) / [README-EN.md](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/README-EN.md) | **Rewrite from scratch.** Remove ALL: Trendshift badge, Shanda logo + link, GitHub badge URLs (`666ghj/MiroFish`), DeepWiki link, X/Instagram handles (`mirofish_ai`), Bilibili video embeds, hiring section (`mirofish@shanda.com`), Star History chart, QQ group, OASIS/CAMEL-AI acknowledgment |
| [static/image/MiroFish_logo.jpeg](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/static/image/MiroFish_logo.jpeg) | **Delete** |
| [static/image/MiroFish_logo_compressed.jpeg](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/static/image/MiroFish_logo_compressed.jpeg) | **Delete** |
| [static/image/shanda_logo.png](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/static/image/shanda_logo.png) | **Delete** |
| [static/image/武大模拟演示封面.png](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/static/image/%E6%AD%A6%E5%A4%A7%E6%A8%A1%E6%8B%9F%E6%BC%94%E7%A4%BA%E5%B0%81%E9%9D%A2.png) | **Delete** |
| [static/image/红楼梦模拟推演封面.jpg](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/static/image/%E7%BA%A2%E6%A5%BC%E6%A2%A6%E6%A8%A1%E6%8B%9F%E6%8E%A8%E6%BC%94%E5%B0%81%E9%9D%A2.jpg) | **Delete** |
| [static/image/QQ群.png](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/static/image/QQ%E7%BE%A4.png) | **Delete** |
| [frontend/src/assets/logo/MiroFish_logo_compressed.jpeg](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/assets/logo/MiroFish_logo_compressed.jpeg) | **Delete** |
| [frontend/src/assets/logo/MiroFish_logo_left.jpeg](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/assets/logo/MiroFish_logo_left.jpeg) | **Delete** |

### Layer 4: Language Localization (Chinese → English)

The **entire frontend UI** is in Chinese. Every view and component contains Chinese text:

- Navigation labels, button text, form labels, status messages, error messages
- Workflow step descriptions (Graph Building, Env Setup, Start Simulation, Report Generation, Deep Interaction)
- Placeholder text, tooltips, headings
- [index.html](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/index.html) `lang="zh-CN"` → `lang="en"`

Backend Chinese text:

- [.env.example](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/.env.example) comments
- Config comments, error messages, log messages
- LLM prompt instructions in [ontology_generator.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/ontology_generator.py), [simulation_config_generator.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/simulation_config_generator.py), [oasis_profile_generator.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/oasis_profile_generator.py), [report_agent.py](file:///c:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/backend/app/services/report_agent.py)

### Layer 5: Visual Redesign (Bauhaus Pivot)

The design is moving away from the "Premium Dark" theme towards a **Creative Studio Minimalistic Bauhaus** aesthetic.

**Core Design Principles:**

- **Background:** Stark White (`#FFFFFF`) or off-white/bone (`#F9F9F8`).
- **Typography:** High-contrast sans-serif.
  - Primary: `Space Grotesk` or `Inter`.
  - Secondary (Mono): `JetBrains Mono` for data and IDs.
  - Large, bold headings with generous letter spacing.
- **Color Palette:** High-contrast black/white base with primary color accents used sparingly for functionality:
  - **Accent Red:** `#FF3333` (Alerts, critical status)
  - **Accent Blue:** `#448FFF` (Primary actions, active states)
  - **Accent Yellow:** `#FFD700` (Information, warnings)
- **Geometry & Borders:**
  - Sharp 90-degree corners (No `border-radius`).
  - Visible grid structure using thin black lines (`1px solid #000000`).
  - No shadows, no gradients, no blurs (Flat design).
- **Layout:** Asymmetric but balanced grid system. Significant white space ("Negative space").
- **Animations:** Snap-to-place transitions, no easing-out fuzziness. Functional transitions only.

---

## User Review Required

> [!IMPORTANT]
> **Big decisions that need your input:**
>
> 1. **LLM prompts are in Chinese** — the AI agents are instructed in Chinese to simulate Chinese social media (Weibo-style). Should I translate all LLM prompts to English, or keep them bilingual?
> 2. **README rewrite** — Should I write a completely new English-only README, or maintain a bilingual version?
> 3. **Conda environment name** — Code references `conda activate MiroFish`. Should I change this to `askthepeople`?
> 4. **Graph ID prefix** — Internal IDs are generated as `mirofish_<uuid>`. Changing this to `atp_<uuid>` would break compatibility with any existing data. Is that OK?

---

## Execution Order

1. **Backend logger/config rename** (mechanical find-replace, low risk)
2. **Backend LLM prompt updates** (translate & rebrand Chinese text)
3. **Frontend navbar/brand text** (simple text swap across 7 views)
4. **Home.vue full rewrite** (hero section, copy, logo, links)
5. **Component brand text** (Step2EnvSetup.vue, Step5Interaction.vue)
6. **index.html** (title, meta, lang)
7. **Delete old assets** (logos, Chinese images)
8. **Generate new logo/favicon**
9. **CSS redesign** (App.vue global styles + all scoped styles)
10. **README rewrite from scratch**
11. **Config files** (package.json, pyproject.toml, docker-compose, CI)
12. **Final sweep** — grep for any remaining `mirofish`, `666ghj`, `shanda`

## Verification

1. `grep -ri "mirofish\|666ghj\|shanda" --include="*.py" --include="*.vue" --include="*.js" --include="*.json" --include="*.yml" --include="*.md" --include="*.html" --include="*.toml" --include="*.txt"` → **must return 0 results**
2. `cd frontend && npm run build` → must succeed
3. Visual audit in browser — verify dark theme, no old logos, all English text
