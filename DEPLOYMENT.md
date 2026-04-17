# Deployment Information

> **Họ tên:** Hồ Nhất Khoa | **MSSV:** 2A202600066

---

## Public URL

```
https://day12ho-nhat-khoa2a202600066-06-production.up.railway.app
```

## Platform

**Railway** (primary deployment)

---

## Test Commands

### Health Check
```bash
curl https://day12ho-nhat-khoa2a202600066-06-production.up.railway.app/health
```
Expected response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 42.3,
  "total_requests": 1,
  "checks": {"llm": "openai/gpt-4o-mini"},
  "timestamp": "2026-04-17T10:00:00.000000+00:00"
}
```

### Authentication Required (no key → 401)
```bash
curl -X POST https://day12ho-nhat-khoa2a202600066-06-production.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"hello"}'
```
Expected: `{"detail":"Invalid or missing API key. Include header: X-API-Key: <key>"}` — HTTP 401

### API Test (with authentication)
```bash
curl -X POST https://day12ho-nhat-khoa2a202600066-06-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"khoa","question":"Tìm vé máy bay từ Hà Nội đi Đà Nẵng"}'
```
Expected response:
```json
{
  "question": "Tìm vé máy bay từ Hà Nội đi Đà Nẵng",
  "answer": "**Chuyến bay:** ...",
  "user_id": "khoa",
  "model": "gpt-4o-mini",
  "timestamp": "2026-04-17T10:00:05.123456+00:00"
}
```

### Conversation History Test (cùng user_id → agent nhớ context)
```bash
# Lượt 1
curl -X POST https://day12ho-nhat-khoa2a202600066-06-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"khoa","question":"Tìm vé máy bay từ Hà Nội đi Đà Nẵng"}'

# Lượt 2 — agent nhớ câu hỏi trước
curl -X POST https://day12ho-nhat-khoa2a202600066-06-production.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"khoa","question":"Tôi vừa hỏi gì vậy?"}'
```
Expected lượt 2: Agent trả lời nhắc lại câu hỏi về vé máy bay HN → Đà Nẵng.

### Rate Limit Test (→ 429 after limit)
```bash
for i in $(seq 1 25); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST https://day12ho-nhat-khoa2a202600066-06-production.up.railway.app/ask \
    -H "X-API-Key: my-secret-key-2026" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"test_rate\",\"question\":\"test $i\"}")
  echo "Request $i: $STATUS"
done
```
Expected: Requests 1–20 → `200`, Request 21+ → `429 Too Many Requests`

---

## Environment Variables Set on Railway

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `AGENT_API_KEY` | *(secret — set via dashboard)* |
| `OPENAI_API_KEY` | *(secret — set via dashboard)* |
| `DAILY_BUDGET_USD` | `5.0` |
| `RATE_LIMIT_PER_MINUTE` | `20` |

---

## Architecture (06-lab-complete)

| Component | Implementation |
|---|---|
| **LLM** | OpenAI `gpt-4o-mini` via LangChain |
| **Agent** | LangGraph `StateGraph` với ReAct pattern |
| **Conversation History** | `MemorySaver` — per `user_id` thread |
| **Tools** | `search_flights`, `search_hotels`, `calculate_budget` |
| **Auth** | `X-API-Key` header (`app/auth.py`) |
| **Rate Limiting** | Sliding window counter (`app/rate_limiter.py`) |
| **Cost Guard** | Daily budget USD (`app/cost_guard.py`) |
| **Deploy** | Docker multi-stage build, non-root user |

---

## Screenshots

- [Railway Dashboard](screenshots/06-railway-dashboard.png)
- [Health Check](screenshots/06-health-check.png)

---

## Deployment Config Files

- Railway: [`06-lab-complete/railway.toml`](06-lab-complete/railway.toml)
- Render: [`03-cloud-deployment/render/render.yaml`](03-cloud-deployment/render/render.yaml)
