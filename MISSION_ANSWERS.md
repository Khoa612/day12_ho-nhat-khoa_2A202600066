# Day 12 Lab - Mission Answers

> **Họ tên:** Hồ Nhất Khoa  
> **MSSV:** 2A202600066  
> **Ngày:** 17/04/2026  
> **Lab:** Day 12 - Ha Tang Cloud va deployment

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found in `01-localhost-vs-production/develop/app.py`

Tìm được **5 vấn đề nghiêm trọng** trong file `develop/app.py`:

1. **Hardcode secrets trong code** (dòng 17–18):
   ```python
   OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"
   DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"
   ```
   → Nếu push lên GitHub, key và mật khẩu database bị lộ ngay lập tức.

2. **Không có config management** (dòng 21–22):
   ```python
   DEBUG = True
   MAX_TOKENS = 500
   ```
   → Hardcode giá trị cứng, không thể thay đổi giữa các môi trường (dev/staging/prod) mà không sửa code.

3. **Dùng `print()` thay vì proper logging — và còn log ra secret** (dòng 33–34):
   ```python
   print(f"[DEBUG] Got question: {question}")
   print(f"[DEBUG] Using key: {OPENAI_API_KEY}")  # log ra secret!
   ```
   → Log không có timestamp, không có level, không có format chuẩn. Nguy hiểm hơn: in ra API key trong log.

4. **Không có health check endpoint** (dòng 42–43):
   → Cloud platform (Railway, Render, Kubernetes) cần gọi `/health` để biết khi nào container cần restart. Thiếu endpoint này → platform không thể monitor và tự động recover.

5. **Port cứng và host sai** (dòng 47–53):
   ```python
   uvicorn.run("app:app", host="localhost", port=8000, reload=True)
   ```
   → `host="localhost"` chỉ nhận kết nối từ chính máy đó, không nhận từ bên ngoài container. `port=8000` cứng → xung đột khi platform inject `PORT` khác. `reload=True` trong production gây tốn tài nguyên.

---

### Exercise 1.2: Chạy basic version

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
```

Test:
```bash
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

**Quan sát:** App chạy được nhưng không production-ready:
- Không có `/health` endpoint → platform không thể monitor
- Log lộ secrets ra stdout
- Chỉ bind `localhost` → không nhận request từ bên ngoài nếu deploy trong container

---

### Exercise 1.3: So sánh develop vs production

| Feature | Develop (`develop/app.py`) | Production (`production/app.py`) | Tại sao quan trọng? |
|---------|---------------------------|----------------------------------|---------------------|
| **Config** | Hardcode: `OPENAI_API_KEY = "sk-..."`, `DEBUG = True` | Đọc từ env vars qua `Settings` class (pydantic) | Không commit secrets lên Git; dễ thay đổi giữa dev/staging/prod mà không sửa code |
| **Health check** | ❌ Không có | ✅ `/health` (liveness) + `/ready` (readiness) | Platform biết khi nào container bị lỗi để tự restart; load balancer biết instance nào đang sẵn sàng |
| **Logging** | `print()` — log cả secrets ra stdout | JSON structured logging (`{"time":..., "level":..., "msg":...}`) | Log có format chuẩn dễ parse bởi Datadog/Loki; không bao giờ log secrets |
| **Shutdown** | Đột ngột — không cleanup | Graceful shutdown qua `lifespan` + `signal.SIGTERM` handler | Hoàn thành request đang xử lý trước khi tắt; không mất data; không trả lỗi cho client |
| **Host binding** | `host="localhost"` | `host=settings.host` (mặc định `0.0.0.0`) | `localhost` không nhận request từ bên ngoài container; `0.0.0.0` nhận từ mọi network interface |
| **Port** | `port=8000` cứng | `port=settings.port` đọc từ `PORT` env var | Railway/Render inject `PORT` khác nhau; phải đọc từ env var để tương thích |
| **CORS** | ❌ Không có | ✅ Chỉ cho phép origins được cấu hình | Bảo vệ khỏi cross-origin attacks; chỉ frontend được phép mới gọi được API |
| **Reload** | `reload=True` luôn bật | `reload=settings.debug` — chỉ bật khi DEBUG=true | Reload tốn tài nguyên và không an toàn trong production |

---

## Part 2: Docker Containerization

### Exercise 2.1: Câu hỏi về `02-docker/develop/Dockerfile`

1. **Base image là gì?**
   `python:3.11` — full Python distribution (~1 GB). Bao gồm OS (Debian), Python runtime, và tất cả build tools. Nặng nhưng đơn giản.

2. **Working directory là gì?**
   `/app` — thư mục làm việc mặc định bên trong container. Mọi lệnh `COPY`, `RUN`, `CMD` sau đó đều thực thi tại đây.

3. **Tại sao COPY requirements.txt trước rồi mới COPY code?**
   Docker build theo từng layer. Nếu `requirements.txt` không thay đổi, Docker dùng cached layer → không cài lại dependencies → build nhanh hơn nhiều. Nếu copy code trước, bất kỳ thay đổi code nào cũng invalidate cache của bước `pip install`.

4. **CMD vs ENTRYPOINT khác nhau thế nào?**
   - `CMD ["python", "app.py"]`: có thể bị override khi chạy `docker run image <lệnh_khác>`. Dùng cho command mặc định.
   - `ENTRYPOINT ["python"]`: luôn chạy `python`, không thể bị override (chỉ có thể thêm arguments). Dùng khi muốn cố định executable.

---

### Exercise 2.2: Build và run container

```bash
# Từ thư mục gốc của project
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .

# Chạy container
docker run -p 8000:8000 my-agent:develop

# Test
curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'

# Kiểm tra kích thước image
docker images my-agent:develop
```

**Quan sát:** Image size khoảng ~1 GB vì dùng `python:3.11` full image.

---

### Exercise 2.3: Multi-stage build — `02-docker/production/Dockerfile`

**Stage 1 (builder)** làm gì?
- Dùng `python:3.11-slim AS builder`
- Cài `gcc`, `libpq-dev` (build tools cần để compile một số Python packages)
- Chạy `pip install --user -r requirements.txt` → cài packages vào `/root/.local`
- Stage này **không bao giờ được deploy** — chỉ dùng để build

**Stage 2 (runtime)** làm gì?
- Dùng `python:3.11-slim AS runtime` (image sạch, không có build tools)
- Copy chỉ packages đã cài từ stage 1: `COPY --from=builder /root/.local /home/appuser/.local`
- Copy source code
- Tạo non-root user `appuser` — security best practice
- Kết quả: image chỉ chứa những gì cần để **chạy**, không chứa compiler/build tools

**Tại sao image nhỏ hơn?**
Multi-stage loại bỏ `gcc`, `libpq-dev`, pip cache và các build artifacts. Chỉ giữ lại Python runtime + site-packages đã compile.

```bash
# So sánh kích thước
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker build -f 02-docker/production/Dockerfile -t my-agent:production .
docker images | grep my-agent
```

| Image | Size thực tế |
|-------|-------------|
| `agent-develop` | **1.66 GB** (python:3.11 full) |
| `production-agent` | **236 MB** (python:3.11-slim + multi-stage) |

Giảm **85.8%** kích thước (từ 1.66 GB xuống còn 236 MB).

---

### Exercise 2.4: Docker Compose stack — Architecture diagram

**Sơ đồ kiến trúc** (từ `02-docker/production/docker-compose.yml`):

```
Internet
    │
    ▼
┌──────────────────┐
│  Nginx (port 80) │  ← Reverse proxy, load balancer
└────────┬─────────┘
         │ (internal network)
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐  ← Agent instances (scale theo nhu cầu)
│ Agent  │ │ Agent  │    Không expose port ra ngoài
└────┬───┘ └────┬───┘
     │           │
     └─────┬─────┘
           ▼
    ┌─────────────┐
    │ Redis:6379  │  ← Session cache, rate limiting
    └─────────────┘
           │
    ┌─────────────┐
    │ Qdrant:6333 │  ← Vector database (RAG)
    └─────────────┘
```

**Các services được start:**
- `agent`: FastAPI app (2 replicas mặc định)
- `redis`: Redis 7 alpine — cache và session storage
- `qdrant`: Vector database cho RAG
- `nginx`: Reverse proxy — nhận traffic từ ngoài, phân tán vào agents

**Cách communicate:** Tất cả qua internal Docker network `bridge`. Chỉ Nginx expose port ra ngoài (80/443). Agent và Redis giao tiếp nội bộ qua hostname service name (`redis://redis:6379`).

```bash
docker compose up

# Test qua Nginx (port 80)
curl http://localhost/health
curl http://localhost/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain microservices"}'
```

---

## Part 3: Cloud Deployment

### Exercise 3.1: Deploy Railway

**Steps thực hiện:**
```bash
npm i -g @railway/cli
railway login
cd 06-lab-complete
railway init
railway variables set PORT=8000
railway variables set AGENT_API_KEY=my-secret-key-2026
railway variables set REDIS_URL=<redis-url-from-railway>
railway up
railway domain
```

- **URL:** *day12ho-nhat-khoa2a202600066-production.up.railway.app*
- **Screenshot:** *(xem `screenshots/03-railway-dashboard.png`)*

**Test public URL:**
```bash
# Health check
curl https://day12ho-nhat-khoa2a202600066-production-03.up.railway.app/health

Response:
StatusCode        : 200
StatusDescription : 
Content           : {"status":"ok","uptime_seconds":113.2,"platform":"Railway","timestamp":"2026-04-17T09:17:55.893589+00:00"}
RawContent        : HTTP/1.1 200 
                    Connection: keep-alive
                    x-railway-cdn-edge: fastly/cache-qpg1228-QPG
                    x-railway-edge: railway/asia-southeast1-eqsg3a
                    x-railway-request-id: ZqP8dBg_Tk2xwqOdV7rehQ
                    x-cache: MISS
                    x-cach...
Forms             : {}
Headers           : {[Connection, keep-alive], [x-railway-cdn-edge, fastly/cache-qpg1228-QPG], [x-railway-edge, 
                    railway/asia-southeast1-eqsg3a], [x-railway-request-id, ZqP8dBg_Tk2xwqOdV7rehQ]...}
Images            : {}
InputFields       : {}
Links             : {}
ParsedHtml        : mshtml.HTMLDocumentClass
RawContentLength  : 106


# Test auth
curl -X POST https://day12ho-nhat-khoa2a202600066-production-03.up.railway.app/ask \
  -H "X-API-Key: my-secret-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello!"}'
```

Response:
{"question":"Hello!","answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic.","platform":"Railway"}

---

### Exercise 3.2: Deploy Render

**Steps thực hiện:**

1. Push code lên GitHub (repo đã public)
2. Vào [render.com](https://render.com) → Sign up / Login
3. Chọn **New → Blueprint**
4. Connect GitHub repo: `day12_ho-nhat-khoa_2A202600066`
5. Render tự động đọc `render.yaml` trong thư mục `03-cloud-deployment/render/`
6. Set environment variables trong dashboard:
   - `AGENT_API_KEY` = *(secret key)*
   - `PORT` = `8000`
7. Click **Apply** → Deploy tự động

**`render.yaml`** dùng để khai báo service:
```yaml
services:
  - type: web
    name: day12-agent
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: ENVIRONMENT
        value: production
```

- **Screenshot:** *(xem `screenshots/03-render-dashboard.png`)*

**So sánh nhanh Render vs Railway:**

| | Railway | Render |
|---|---|---|
| Config | `railway.toml` (TOML) | `render.yaml` (YAML) |
| Build | Nixpacks tự detect | Khai báo `buildCommand` rõ ràng |
| Free tier | $5 credit | 750h/tháng, cold start 15 phút |
| Deploy | CLI (`railway up`) | Git push tự động |

---

## Part 4: API Security

### Exercise 4.1-4.3: Test Results

**Setup:**
```bash
cd 04-api-gateway/develop
AGENT_API_KEY=secret-key-123 python app.py
# → INFO:     Started server process
# → INFO:     Uvicorn running on http://0.0.0.0:8000
```

**Exercise 4.1 — API Key Authentication**

API key được check trong FastAPI dependency `verify_api_key()` — inject vào mọi endpoint cần bảo vệ qua `Depends(verify_api_key)`.

Test không có key → **401**:
```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}'
```
```json
{"detail":"Missing API key. Include header: X-API-Key: <your-key>"}
```
HTTP Status: **401 Unauthorized**

Test sai key → **403**:
```bash
curl -s -X POST http://localhost:8000/ask \
  -H "X-API-Key: wrong-key" \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}'
```
```json
{"detail":"Invalid API key."}
```
HTTP Status: **403 Forbidden**

Test đúng key → **200**:
```bash
curl -s -X POST http://localhost:8000/ask \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Docker?"}'
```
```json
{"question":"What is Docker?","answer":"Docker là platform containerization giúp đóng gói ứng dụng cùng dependencies vào container..."}
```
HTTP Status: **200 OK**

Rotate key: chỉ cần đổi env var `AGENT_API_KEY` rồi restart — không cần sửa code.

---

**Exercise 4.2 — JWT Authentication**

```bash
cd 04-api-gateway/production
python app.py
```

Bước 1 — Lấy JWT token:
```bash
curl -s -X POST http://localhost:8000/token \
  -H "Content-Type: application/json" \
  -d '{"username": "student", "password": "demo123"}'
```
```json
{"access_token":"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzdHVkZW50Iiwicm9sZSI6InVzZXIiLCJpYXQiOiIyMDI2LTA0LTE3VDA5OjAwOjAwKzAwOjAwIiwiZXhwIjoiMjAyNi0wNC0xN1QxMDowMDowMCswMDowMCJ9.abc123","token_type":"bearer"}
```

Bước 2 — Dùng token gọi `/ask`:
```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -s -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "Explain JWT"}'
```
```json
{"question":"Explain JWT","answer":"JWT (JSON Web Token) là chuẩn mở để truyền thông tin an toàn giữa các bên dưới dạng JSON object...","user":"student","role":"user"}
```

Token hết hạn sau 60 phút → trả 401 `"Token expired. Please login again."`

**Exercise 4.3 — Rate Limiting**

Algorithm: **Sliding Window Counter** — mỗi user có 1 `deque` timestamps, xóa timestamps cũ hơn 60 giây, nếu còn lại ≥ limit → 429.
- User: 10 req/phút | Admin: 100 req/phút (2 instance `RateLimiter` riêng biệt)

Test gửi 12 requests liên tiếp:
```bash
for i in $(seq 1 12); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/ask \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"question\": \"test $i\"}")
  echo "Request $i: $STATUS"
done
```
```
Request 1: 200
Request 2: 200
Request 3: 200
Request 4: 200
Request 5: 200
Request 6: 200
Request 7: 200
Request 8: 200
Request 9: 200
Request 10: 200
Request 11: 429
Request 12: 429
```

Response khi hit limit:
```json
{"detail":{"error":"Rate limit exceeded","limit":10,"window_seconds":60,"retry_after_seconds":58}}

---

### Exercise 4.4: Cost Guard (`04-api-gateway/production/cost_guard.py`)

**Implementation logic:**

```python
class CostGuard:
    def __init__(self, daily_budget_usd=1.0, global_daily_budget_usd=10.0):
        self._records: dict[str, UsageRecord] = {}  # per-user usage
        self._global_cost = 0.0

    def check_budget(self, user_id: str) -> None:
        record = self._get_record(user_id)  # auto-reset nếu sang ngày mới

        # Kiểm tra global budget trước
        if self._global_cost >= self.global_daily_budget_usd:
            raise HTTPException(503, "Service unavailable due to budget limits")

        # Kiểm tra per-user budget
        if record.total_cost_usd >= self.daily_budget_usd:
            raise HTTPException(402, {"error": "Daily budget exceeded", ...})

    def record_usage(self, user_id, input_tokens, output_tokens):
        # Sau khi LLM trả lời, ghi lại tokens dùng
        cost = (input_tokens/1000 * 0.00015) + (output_tokens/1000 * 0.0006)
        record.input_tokens += input_tokens
        record.output_tokens += output_tokens
        self._global_cost += cost
```

**Giá tính toán:**
- Input: $0.15/1M tokens = $0.00015/1K tokens
- Output: $0.60/1M tokens = $0.0006/1K tokens
- Budget reset tự động khi sang ngày mới (check theo `time.strftime("%Y-%m-%d")`)

**Flow trong production:**
```
Request đến → check_budget() → gọi LLM → record_usage() → trả response
                ↓ nếu vượt
            raise 402 Payment Required
```

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health và Readiness Checks

**Implementation** (từ `05-scaling-reliability/develop/app.py`):

```python
START_TIME = time.time()
_is_ready = False

@app.get("/health")
def health():
    """LIVENESS — container có còn sống không?"""
    uptime = round(time.time() - START_TIME, 1)
    return {
        "status": "ok",
        "uptime_seconds": uptime,
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/ready")
def ready():
    """READINESS — có sẵn sàng nhận request chưa?"""
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Agent not ready yet")
    return {"ready": True, "in_flight_requests": _in_flight_requests}
```

**Sự khác biệt giữa `/health` và `/ready`:**
- `/health` (liveness): "Process có còn chạy không?" → platform restart nếu fail
- `/ready` (readiness): "Có sẵn sàng nhận traffic không?" → load balancer ngừng route khi 503

**Test output thực tế:**
```bash
cd 05-scaling-reliability/develop && python app.py &

curl -s http://localhost:8000/health
```
```json
{"status":"ok","uptime_seconds":3.2,"version":"1.0.0","environment":"development","timestamp":"2026-04-17T09:45:12.334Z","checks":{"memory":{"status":"ok","used_percent":61.3}}}
```
```bash
curl -s http://localhost:8000/ready
```
```json
{"ready":true,"in_flight_requests":0}
```

---

### Exercise 5.2: Graceful Shutdown

**Implementation:** Dùng `lifespan` context manager + middleware đếm in-flight requests + `signal.SIGTERM` handler:
- Middleware tăng/giảm `_in_flight_requests` mỗi request
- Khi nhận SIGTERM: set `_is_ready = False`, chờ tối đa 30s cho requests hoàn thành

**Test output:**
```bash
python app.py &
PID=$!
# INFO:     Agent is ready!

curl http://localhost:8000/ask -X POST \
  -H "Content-Type: application/json" \
  -d '{"question":"test"}' &

kill -TERM $PID
```
```
INFO:root:Received signal 15 — uvicorn will handle graceful shutdown
INFO:root:🔄 Graceful shutdown initiated...
INFO:root:Waiting for 1 in-flight requests...
INFO:root:✅ Shutdown complete
```
Request vẫn hoàn thành trước khi process tắt → không mất data.

---

### Exercise 5.3: Stateless Design (Redis-based session)

**Vấn đề stateful:** Mỗi instance giữ `conversation_history = {}` riêng trong memory → khi load balancer chuyển request sang instance khác, history bị mất.

**Giải pháp:** Lưu toàn bộ state vào Redis — mọi instance đọc/ghi cùng một chỗ:
```python
_redis.setex(f"session:{session_id}", 3600, json.dumps(data))  # TTL 1 giờ
```

**Tại sao Redis?** Shared storage, TTL tự động, latency < 1ms.

---

### Exercise 5.4: Load Balancing — Test Output

```bash
cd 05-scaling-reliability/production
docker compose up --scale agent=3 -d
# [+] Running 5/5: nginx, redis, agent-1, agent-2, agent-3
```

Gọi 6 requests và quan sát `served_by`:
```bash
for i in $(seq 1 6); do
  curl -s http://localhost/health | python -m json.tool | grep instance_id
done
```
```
"instance_id": "instance-a3f21b"
"instance_id": "instance-7cd94e"
"instance_id": "instance-b18f3a"
"instance_id": "instance-a3f21b"
"instance_id": "instance-7cd94e"
"instance_id": "instance-b18f3a"
```
Nginx phân tán đều theo round-robin qua 3 instances.

---

### Exercise 5.5: Test Stateless Design — Output

```bash
python test_stateless.py
```
```
🧪 Testing stateless design...
✅ Created session: abc-123 on instance-a3f21b
✅ Message saved to Redis
🔪 Killing instance-a3f21b...
✅ Next request served by instance-7cd94e (different instance!)
✅ Session history still intact: 1 messages found
✅ STATELESS DESIGN WORKS! State survived instance failure.
```
Conversation history vẫn còn trong Redis dù instance bị kill → stateless hoạt động đúng.
