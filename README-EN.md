<div align="center">

# ASKTHEPEOPLE

**Crowd Intelligence Engine — Predict Anything**

[![GitHub Stars](https://img.shields.io/github/stars/sergey9519546/ASKTHEPEOPLE?style=flat-square&color=DAA520)](https://github.com/sergey9519546/ASKTHEPEOPLE/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/sergey9519546/ASKTHEPEOPLE?style=flat-square)](https://github.com/sergey9519546/ASKTHEPEOPLE/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)

[English](./README-EN.md) | [Documentation](./README.md)

</div>

## ⚡ Overview

**ASKTHEPEOPLE** is a next-generation AI prediction engine powered by multi-agent technology. Upload any document — a news article, policy draft, financial report, or novel — and it automatically extracts "reality seeds" to construct a high-fidelity parallel digital world. Thousands of agents with independent personalities, long-term memories, and behavioral logic interact and evolve freely. Inject variables from a god's-eye view and precisely simulate future trajectories.

> **Input:** Upload seed material and describe your prediction goal in natural language  
> **Output:** A detailed prediction report + a deeply interactive high-fidelity digital world

### Our Vision

ASKTHEPEOPLE is dedicated to creating a swarm intelligence mirror that maps reality. By capturing the collective emergence triggered by individual interactions, we break through the limitations of traditional prediction:

- **At the Macro Level**: A rehearsal laboratory for decision-makers — policies and public relations tested at zero risk
- **At the Micro Level**: A creative sandbox for individuals — whether deducing novel endings or exploring imaginative scenarios, fun and accessible

From serious predictions to playful simulations, every "what if" can see its outcome.

## 📸 Screenshots

<div align="center">
<table>
<tr>
<td><img src="./static/image/Screenshot/screenshot1.png" alt="Screenshot 1" width="100%"/></td>
<td><img src="./static/image/Screenshot/screenshot2.png" alt="Screenshot 2" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/screenshot3.png" alt="Screenshot 3" width="100%"/></td>
<td><img src="./static/image/Screenshot/screenshot4.png" alt="Screenshot 4" width="100%"/></td>
</tr>
<tr>
<td><img src="./static/image/Screenshot/screenshot5.png" alt="Screenshot 5" width="100%"/></td>
<td><img src="./static/image/Screenshot/screenshot6.png" alt="Screenshot 6" width="100%"/></td>
</tr>
</table>
</div>

## 🔄 Workflow

1. **Graph Construction** — Reality seed extraction + individual/group memory injection + GraphRAG build
2. **Environment Setup** — Entity-relation extraction + persona generation + simulation config inject
3. **Simulation** — Dual-platform parallel simulation + auto-parsed prediction + temporal memory updates
4. **Report Generation** — ReportAgent with rich toolset deep-interacts with the simulation environment
5. **Deep Interaction** — Chat with any agent in the simulated world or with the ReportAgent

## 🚀 Quick Start

### Option 1: Source Code Deployment (Recommended)

#### Prerequisites

| Tool | Version | Description | Check Installation |
|------|---------|-------------|-------------------|
| **Node.js** | 18+ | Frontend runtime, includes npm | `node -v` |
| **Python** | ≥3.11, ≤3.12 | Backend runtime | `python --version` |
| **uv** | Latest | Python package manager | `uv --version` |

#### 1. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env and fill in required API keys
```

**Required Environment Variables:**

```env
# LLM API (any OpenAI SDK-compatible API)
# Recommended: Alibaba Qwen-plus via Bailian: https://bailian.console.aliyun.com/
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Zep Cloud (free tier sufficient for basic use)
# https://app.getzep.com/
ZEP_API_KEY=your_zep_api_key
```

#### 2. Install Dependencies

```bash
npm run setup:all
```

Or step by step:

```bash
npm run setup          # Node deps (root + frontend)
npm run setup:backend  # Python deps (auto creates virtualenv)
```

#### 3. Start Services

```bash
npm run dev  # Starts both frontend and backend
```

**Service URLs:**

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:5001`

```bash
npm run backend   # Backend only
npm run frontend  # Frontend only
```

### Option 2: Docker Deployment

```bash
cp .env.example .env
docker compose up -d
```

Maps ports `3000 (frontend) / 5001 (backend)` by default.

## 📄 Acknowledgements

The simulation engine is powered by **[OASIS](https://github.com/camel-ai/oasis)**. We sincerely thank the CAMEL-AI team for their open-source contribution!
