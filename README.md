<div align="center">

# ASKTHEPEOPLE

**Crowd Intelligence Engine — Predict Anything**

[![GitHub Stars](https://img.shields.io/github/stars/sergey9519546/ASKTHEPEOPLE?style=flat-square&color=DAA520)](https://github.com/sergey9519546/ASKTHEPEOPLE/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/sergey9519546/ASKTHEPEOPLE?style=flat-square)](https://github.com/sergey9519546/ASKTHEPEOPLE/network)
[![Docker](https://img.shields.io/badge/Docker-Build-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/)

[English](./README-EN.md) | [Chinese Documentation](./README.md)

</div>

## ⚡ Overview

**ASKTHEPEOPLE** is a next-generation AI prediction engine powered by multi-agent technology. Upload any document — a news article, policy draft, financial report, or novel — and it automatically extracts "reality seeds" to construct a high-fidelity parallel digital world. Thousands of agents with independent personalities, long-term memories, and behavioral logic interact and evolve freely. Inject variables from a god's-eye view and precisely simulate future trajectories.

> **Input:** Upload seed material and describe your prediction goal in natural language  
> **Output:** A detailed prediction report + a deeply interactive high-fidelity digital world

## 🔄 Workflow

1. **Graph Construction** — Reality seed extraction + individual/group memory injection + GraphRAG build
2. **Environment Setup** — Entity-relation extraction + persona generation + simulation config inject
3. **Simulation** — Dual-platform parallel simulation + auto-parsed prediction + temporal memory updates
4. **Report Generation** — ReportAgent with rich toolset deep-interacts with the simulation environment
5. **Deep Interaction** — Chat with any agent in the simulated world or with the ReportAgent

## 🚀 Quick Start

### Option A — Source Code (Recommended)

#### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| **Node.js** | 18+ | Frontend runtime |
| **Python** | ≥3.11, ≤3.12 | Backend runtime |
| **uv** | Latest | Python package manager |

#### 1. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in required API keys
```

**Required variables:**

```env
# LLM API (any OpenAI SDK-compatible API)
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL_NAME=qwen-plus

# Zep Cloud (free tier sufficient for basic use)
# https://app.getzep.com/
ZEP_API_KEY=your_zep_api_key
```

#### 2. Install dependencies

```bash
npm run setup:all
```

Or step by step:

```bash
npm run setup          # Node deps (root + frontend)
npm run setup:backend  # Python deps (auto creates virtualenv)
```

#### 3. Start services

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

### Option B — Docker

```bash
cp .env.example .env
docker compose up -d
```

Maps ports `3000 (frontend) / 5001 (backend)` by default.

## 📄 Acknowledgements

The simulation engine is powered by **[OASIS](https://github.com/camel-ai/oasis)**. We sincerely thank the CAMEL-AI team for their open-source contribution!
