# Mermaid Diagram Templates for Documentation

This reference provides production-ready Mermaid diagram templates designed for software repository documentation. GitHub and GitLab render Mermaid natively in Markdown code blocks.

---

## 1. High-Level Architecture (Flowchart TD / LR)

Used in `README.md` and `docs/ARCHITECTURE.md` to represent system components, APIs, services, and databases.

```mermaid
flowchart TD
    subgraph ClientLayer["Client & External Ingress"]
        CLI["CLI Tool / Terminal"]
        WebUI["Web Frontend / Browser"]
        ExtAPI["External Webhooks / 3P Services"]
    end

    subgraph AppLayer["Application Core"]
        Router["API Gateway / Router"]
        AuthSvc["Auth & Security Middleware"]
        CoreEngine["Core Processing Engine"]
        WorkerPool["Background Workers / Tasks"]
    end

    subgraph DataLayer["Persistence & External Services"]
        DB[("Main Database (PostgreSQL/MySQL)")]
        Cache[("Cache (Redis/Memory)")]
        ObjectStore[("Cloud Storage / S3")]
        ExternalProvider["Third-Party APIs (Stripe, OpenAI, etc.)"]
    end

    CLI --> Router
    WebUI --> Router
    ExtAPI --> Router

    Router --> AuthSvc
    AuthSvc --> CoreEngine
    CoreEngine --> WorkerPool

    CoreEngine --> DB
    CoreEngine --> Cache
    WorkerPool --> ObjectStore
    WorkerPool --> ExternalProvider
```

---

## 2. Request & Execution Sequence Flow (sequenceDiagram)

Ideal for explaining authentication, request processing, or algorithmic pipelines.

```mermaid
sequenceDiagram
    autonumber
    actor User as Client / User
    participant Gateway as API Gateway
    participant Service as Application Service
    participant DB as Database / Storage
    participant Queue as Task Queue

    User->>Gateway: POST /api/v1/resource (payload)
    activate Gateway
    Gateway->>Gateway: Validate API token & payload
    Gateway->>Service: Forward validated request
    activate Service

    Service->>DB: Query current state / records
    activate DB
    DB-->>Service: Return state
    deactivate DB

    Service->>Service: Compute business logic & transform
    Service->>DB: Persist updated entity
    Service->>Queue: Enqueue asynchronous event
    Service-->>Gateway: Result data object
    deactivate Service

    Gateway-->>User: 200 OK (JSON response)
    deactivate Gateway
```

---

## 3. Data Ingestion & ETL Pipeline (Flowchart LR)

Useful for data analysis, machine learning, scrapers, and data pipelines.

```mermaid
flowchart LR
    subgraph Ingestion["1. Ingestion"]
        S1["Raw Files / CSV"]
        S2["Database CDC"]
        S3["REST API Poller"]
    end

    subgraph Processing["2. Processing & Cleaning"]
        P1["Schema Validation"]
        P2["Deduplication & Imputation"]
        P3["Feature Engineering / Normalization"]
    end

    subgraph Storage["3. Storage & Analytics"]
        DWH[("Data Warehouse / Lakehouse")]
        BI["Dashboards / Analytics UI"]
        ML["ML Model Training / Inference"]
    end

    S1 --> P1
    S2 --> P1
    S3 --> P1

    P1 --> P2
    P2 --> P3

    P3 --> DWH
    DWH --> BI
    DWH --> ML
```

---

## 4. Entity-Relationship Data Model (erDiagram)

For repositories with relational models, ORMs (Prisma, SQLAlchemy, TypeORM, Django), or SQL migrations.

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    USER ||--o{ SESSION : owns
    USER {
        uuid id PK
        string email UK
        string password_hash
        datetime created_at
    }
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER {
        uuid id PK
        uuid user_id FK
        string status
        decimal total_amount
    }
    ORDER_ITEM {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
        decimal unit_price
    }
    PRODUCT ||--o{ ORDER_ITEM : referenced_in
    PRODUCT {
        uuid id PK
        string title
        decimal price
        int inventory_count
    }
```

---

## 5. State Machine / Lifecycle Diagram (stateDiagram-v2)

For tasks, orders, pipeline runs, or agents with explicit states.

```mermaid
stateDiagram-v2
    [*] --> Pending : Job Created
    Pending --> Running : Worker Picked Up
    Running --> Success : Execution Completed
    Running --> Failed : Unhandled Exception
    Failed --> Retrying : Retries Left (> 0)
    Retrying --> Running : Backoff Expired
    Failed --> DeadLetter : Retries Exhausted
    Success --> [*]
    DeadLetter --> [*]
```

---

## Syntax Rules & Anti-Patterns to Avoid

1. **Quote Node Labels**: Always wrap labels containing parentheses, hyphens, brackets, or colons in double quotes:
   - ✅ `NodeA["Process (Thread 1)"]`
   - ❌ `NodeA[Process (Thread 1)]` (causes syntax parse error).
2. **Avoid Raw HTML**: GitHub sanitizes markdown and raw HTML tags inside Mermaid can break rendering. Use standard markdown formatting.
3. **Keep Diagrams Readable**: If a system has >15 components, divide into multiple focused diagrams (e.g., High-Level Overview vs. Ingestion Flow) rather than one unreadable monolith.
