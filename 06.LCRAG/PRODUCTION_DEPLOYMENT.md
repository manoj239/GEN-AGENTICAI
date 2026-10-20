# Production Deployment Guide — Domain-Aware Agentic RAG Assistant

This document explains how the RAG application in this repo (`FastapiNaiveRag.py`,
`CommonRAG.py`, `RAG.py`) can be taken from a local script to a production-grade
service that supports 100+ concurrent users, with load balancing, autoscaling,
monitoring, and CI/CD — on AWS using Docker/FastAPI.

---

## 1. High-Level Production Architecture (AWS)

```
                                   ┌───────────────────────┐
                                   │        Users          │
                                   └──────────┬────────────┘
                                              │ HTTPS
                                              ▼
                                   ┌───────────────────────┐
                                   │  Route 53 (DNS)        │
                                   └──────────┬────────────┘
                                              ▼
                                   ┌───────────────────────┐
                                   │  CloudFront (CDN/WAF)  │  ← rate limiting, bot/IP protection
                                   └──────────┬────────────┘
                                              ▼
                                   ┌───────────────────────┐
                                   │ Application Load      │  ← SSL termination, health checks
                                   │ Balancer (ALB)         │
                                   └──────────┬────────────┘
                                              ▼
                     ┌───────────────────────────────────────────────┐
                     │        ECS Fargate / EKS Service               │
                     │  ┌───────────┐ ┌───────────┐ ┌───────────┐    │
                     │  │FastAPI Pod│ │FastAPI Pod│ │FastAPI Pod│ ... │  ← Docker containers
                     │  │(RAG app)  │ │(RAG app)  │ │(RAG app)  │    │     Auto Scaling Group
                     │  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘    │     (CPU/latency/queue based)
                     └────────┼─────────────┼─────────────┼──────────┘
                              │             │             │
              ┌───────────────┴───┐   ┌─────┴─────┐  ┌────┴─────────┐
              ▼                   ▼   ▼           ▼  ▼              ▼
     ┌──────────────┐   ┌──────────────────┐  ┌───────────────┐ ┌────────────────┐
     │ Vector DB     │   │ Redis (ElastiCache)│ │ Gemini API /   │ │ Secrets Manager │
     │ Pinecone/     │   │ cache + rate limit │ │ LLM Provider   │ │ / IAM roles     │
     │ Chroma on EFS │   └──────────────────┘  └───────────────┘ └────────────────┘
     └──────────────┘

              ┌─────────────────────────────────────────────────┐
              │ Observability: CloudWatch Logs/Metrics/Alarms,    │
              │ X-Ray/OpenTelemetry tracing, LangSmith/RAGAS eval │
              └─────────────────────────────────────────────────┘

              ┌─────────────────────────────────────────────────┐
              │ CI/CD: GitHub Actions → ECR → ECS/EKS deploy       │
              │ (build, test, scan, push, blue/green deploy)      │
              └─────────────────────────────────────────────────┘
```

### Component responsibilities

| Layer | AWS Service | Purpose |
|---|---|---|
| DNS + Edge | Route 53, CloudFront, AWS WAF | Domain routing, CDN caching for static assets, DDoS/bot protection |
| Load Balancing | Application Load Balancer (ALB) | Distributes traffic across containers, SSL termination, health checks, path-based routing (`/ask`, `/ingest`, `/health`) |
| Compute | ECS Fargate (or EKS) | Runs the FastAPI + LangChain RAG app as stateless Docker containers |
| Autoscaling | ECS Service Auto Scaling | Scales task count based on CPU, memory, ALB request count, or custom CloudWatch metric (e.g., queue depth) |
| Vector Store | Chroma (EFS-backed) or managed Pinecone | Stores embeddings; Pinecone preferred in prod for managed scaling/HA |
| Caching | ElastiCache (Redis) | Caches frequent query embeddings/answers, implements per-user rate limiting |
| Secrets | Secrets Manager / Parameter Store | Stores Gemini API key, DB credentials — never hardcoded or committed |
| IAM | IAM roles per task | Least-privilege access (task role vs execution role) |
| Monitoring | CloudWatch Logs/Metrics/Alarms, X-Ray | Latency, error rate, token usage, retrieval quality dashboards |
| Tracing/Eval | LangSmith, RAGAS | Debug chains, evaluate faithfulness/relevance in prod |
| CI/CD | GitHub Actions/CodePipeline + ECR | Build, test, scan, push image, rolling/blue-green deploy |

---

## 2. Containerizing with Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user for security
RUN useradd -m appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "FastapiNaiveRag:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

- Use **multiple Uvicorn workers** (or Gunicorn + Uvicorn workers) per container to use
  multi-core CPUs efficiently.
- Keep the vector DB persistence directory (`chroma_db/`) **outside** the container —
  mount EFS or use a managed vector DB so restarts/redeploys don't lose data.
- Never bake `.env` secrets into the image; inject via ECS task definition / Secrets Manager.

## 3. Scaling to 100+ concurrent users

- **Stateless app containers**: no session state in-process → any instance can serve any request.
- **Horizontal scaling**: run 3+ ECS tasks minimum behind the ALB; Auto Scaling policy
  triggers on `ALBRequestCountPerTarget` or CPU > 60%.
- **Async I/O**: the app already uses `async def` endpoints with `ainvoke` for LLM and
  retriever calls — this lets one worker handle many concurrent I/O-bound requests
  without blocking.
- **Connection pooling / timeouts**: set explicit timeouts on Gemini and vector DB calls
  so one slow request doesn't exhaust worker threads.
- **Queueing for spikes**: for bursty ingestion/heavy workloads, offload to SQS + worker
  tasks instead of handling synchronously in the request path.
- **Caching**: cache repeated queries/embeddings in Redis to cut LLM and vector DB calls.

## 4. Monitoring & Observability

| What to track | Why |
|---|---|
| API latency (p50/p95/p99) | Detect slow responses before users complain |
| Error rate (4xx/5xx) | Catch broken retrieval or LLM failures |
| Retrieval latency vs LLM latency | Identify whether vector DB or Gemini is the bottleneck |
| Token usage / cost per request | Control LLM API spend |
| Retrieval quality (RAGAS: faithfulness, relevance) | Detect answer quality drift |
| % queries needing corrective/web-search fallback | Signal gaps in knowledge base |
| Container health/restarts, CPU/memory | Capacity planning & stability |

Tooling: **CloudWatch** dashboards/alarms for infra metrics, **LangSmith** for
trace-level chain debugging, **RAGAS** for periodic offline/online evaluation,
**AWS X-Ray/OpenTelemetry** for distributed tracing across ALB → ECS → vector DB → LLM.

## 5. CI/CD Pipeline

1. Push to `main` → GitHub Actions triggers.
2. Run unit tests + lint + dependency vulnerability scan.
3. Build Docker image, scan with `trivy`/ECR scan-on-push.
4. Push image to Amazon ECR.
5. Update ECS task definition, deploy via rolling update or blue/green (CodeDeploy).
6. Run smoke test against `/health` endpoint; auto-rollback on failure.

## 6. Security Checklist

- API keys/secrets only via Secrets Manager — never in code or `.env` committed to git.
- ALB terminates TLS; enforce HTTPS only.
- WAF rules for rate limiting and common injection patterns.
- IAM least privilege per ECS task role.
- Input validation via Pydantic (already used) to prevent malformed/oversized requests.
- Sanitize/limit prompt size to mitigate prompt-injection and cost abuse.
- Network isolation: app containers in private subnets, only ALB in public subnet.

---

## 7. Interview Q&A — Deployment Experience

**Q1: Walk me through how you deployed this RAG application in production.**
> The FastAPI app was containerized with Docker and deployed on ECS Fargate across
> multiple tasks in private subnets, fronted by an Application Load Balancer for
> SSL termination and health-check-based routing. Auto Scaling adjusted task count
> based on CPU and request count. Secrets (API keys) were managed via AWS Secrets
> Manager and injected through the ECS task definition. CI/CD via GitHub Actions
> built, scanned, and deployed new images to ECR/ECS automatically.

**Q2: How did you handle 100+ concurrent users without degrading latency?**
> By keeping the app stateless and async (using `ainvoke` for both retrieval and
> LLM calls), running multiple Uvicorn workers per container, and horizontally
> scaling container count behind the ALB. Frequently repeated queries were cached
> in Redis to avoid redundant vector search and LLM calls.

**Q3: What were the main challenges you faced while deploying this to production?**
> - **Cold start / latency**: loading the embedding model, vector store, and
>   reranker at startup increased container boot time, which affected autoscaling
>   responsiveness — solved by warming up instances and using smaller/optimized
>   reranker models.
> - **Vector DB persistence**: Chroma's local file-based persistence doesn't scale
>   well across multiple replicas — migrated to a managed vector DB (Pinecone) or
>   mounted shared EFS storage for consistency.
> - **LLM latency/timeouts**: Gemini API calls occasionally spiked in latency;
>   added explicit timeouts, retries with backoff, and circuit breakers.
> - **Cost control**: uncapped token usage from long contexts could spike cost —
>   added context length limits, response caching, and token usage monitoring.
> - **Secrets/config management**: moving from local `.env` files to centralized
>   secret storage with proper IAM scoping.
> - **Observability**: initially had no visibility into retrieval quality in
>   production — added RAGAS-based periodic evaluation and LangSmith tracing to
>   debug poor answers.

**Q4: What was your specific role in this project?**
> I designed and implemented the RAG pipeline — document ingestion and chunking,
> embedding generation, vector store integration, CrossEncoder-based reranking,
> and the FastAPI service layer exposing it as an API. I also defined the
> production deployment approach (containerization, load balancing, autoscaling,
> monitoring) and evaluation strategy (RAGAS/LangSmith) to ensure answer quality
> and reliability at scale.

**Q5: How would you improve this architecture further?**
> Add an API gateway with authentication/authorization (SSO/OAuth), introduce a
> message queue for heavy ingestion workloads instead of synchronous processing,
> add canary/blue-green deployments for safer rollouts, and expand monitoring to
> include automated alerting on retrieval-quality regression.

**Q6: How do you ensure the system stays reliable if the LLM provider (Gemini) has an outage?**
> Implement retries with exponential backoff, circuit breaker pattern, graceful
> degradation (e.g., return top retrieved chunks without generation, or fall back
> to a secondary LLM provider), and alerting via CloudWatch when failure rate
> crosses a threshold.
