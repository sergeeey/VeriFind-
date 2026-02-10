# APE 2026 - Project Brief

## Overview
**Autonomous Prediction Engine (APE)** - AI-powered financial analysis platform with multi-agent debate system, temporal knowledge graph, and prediction tracking.

## Core Purpose
Provide institutional-grade financial predictions with:
- Multi-source data verification
- AI agent debate for consensus
- Temporal knowledge graph
- Track record with accuracy metrics

## Current Status
**Phase**: Week 2 Complete (Production Ready)
**Grade**: 8.5/10 (target 9.0/10)
**Date**: 2026-02-10

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, LangGraph
- **Database**: Neo4j (graph), TimescaleDB (time-series)
- **Cache**: Redis
- **LLM**: DeepSeek → Anthropic → OpenAI (fallback chain)
- **Frontend**: Next.js 14
- **Monitoring**: Prometheus + Grafana

## Key Features
1. **Query Processing**: Natural language → structured analysis
2. **Multi-Agent Debate**: Bull vs Bear agents with synthesis
3. **Truth Boundary**: Verification gate with confidence scoring
4. **Predictions**: Price corridors with accuracy tracking
5. **WebSocket**: Real-time updates with Redis pub/sub

## Architecture
```
Query → Router → Plan → Fetch → Debate → Verify → Predict
         ↓        ↓       ↓        ↓        ↓        ↓
      LLM     Strategy  Data   Agents   Gate    Store
```

## Production Readiness
- ✅ Security: 0 HIGH issues, passwords rotated
- ✅ Tests: 19/19 critical passing
- ✅ Resilience: Circuit breaker pattern
- ✅ Monitoring: Health endpoints + Prometheus
- ✅ Documentation: Complete deploy guide

## Quick Links
- Deploy Guide: `docs/PRODUCTION_DEPLOY.md`
- API Tests: `tests/integration/test_api_critical.py`
- Load Tests: `tests/load/`
- Security: `docs/security/API_KEY_MANAGEMENT.md`
