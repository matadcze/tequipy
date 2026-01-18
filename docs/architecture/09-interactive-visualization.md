# Interactive Architecture Visualization

## Overview

This document provides interactive Mermaid diagrams for exploring the Tequipy architecture at different levels of detail.

## Live Architecture Explorer

### Request Flow Visualization

The following diagram shows how a request flows through the system:

```mermaid
sequenceDiagram
    autonumber
    participant U as User Browser
    participant N as Nginx
    participant F as Frontend<br/>(Next.js)
    participant B as Backend<br/>(FastAPI)
    participant R as Redis
    participant P as PostgreSQL
    participant OM as Open-Meteo

    rect rgb(240, 248, 255)
        Note over U,N: TLS Termination
        U->>N: HTTPS Request
        N->>N: Decrypt TLS
        N->>N: Add Security Headers
    end

    alt UI Request (/)
        N->>F: Proxy to :3000
        F-->>N: HTML/JS/CSS
        N-->>U: Response
    else API Request (/api/*)
        rect rgb(255, 248, 240)
            Note over N,B: API Processing
            N->>B: Proxy to :8000
            B->>B: Middleware Chain
            Note right of B: 1. RequestLogging<br/>2. Metrics<br/>3. RateLimit<br/>4. Security<br/>5. CORS
        end

        alt Auth Required
            B->>B: Validate JWT
        end

        alt Database Query
            B->>P: SQL Query
            P-->>B: Result
        end

        alt Cache Operation
            B->>R: Get/Set Cache
            R-->>B: Cached Data
        end

        alt Weather Request
            B->>R: Check Cache
            alt Cache Miss
                B->>OM: GET /forecast
                OM-->>B: Weather Data
                B->>R: Cache Result (60s)
            else Cache Hit
                R-->>B: Cached Weather
            end
        end

        B-->>N: JSON Response
        N-->>U: Response
    end
```

### Authentication Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant B as Backend
    participant R as Redis
    participant P as PostgreSQL

    rect rgb(230, 255, 230)
        Note over U,P: Registration Flow
        U->>F: Fill Registration Form
        F->>B: POST /auth/register
        B->>R: Check Rate Limit
        R-->>B: OK
        B->>P: Check Email Exists
        P-->>B: Not Found
        B->>B: Hash Password (bcrypt)
        B->>P: INSERT User
        B->>P: INSERT Audit Event
        B-->>F: User Created (201)
        F-->>U: Success Message
    end

    rect rgb(255, 255, 230)
        Note over U,P: Login Flow
        U->>F: Enter Credentials
        F->>B: POST /auth/login
        B->>R: Check Rate Limit
        B->>P: SELECT User by Email
        B->>B: Verify Password
        B->>B: Generate JWT Tokens
        B->>P: Store Refresh Token Hash
        B->>P: INSERT Audit Event
        B-->>F: {access_token, refresh_token}
        F->>F: Store in localStorage
        F-->>U: Redirect to Dashboard
    end

    rect rgb(230, 240, 255)
        Note over U,P: Token Refresh
        U->>F: Access Token Expired
        F->>B: POST /auth/refresh
        B->>P: Validate Refresh Token
        B->>P: Revoke Old Token
        B->>B: Generate New Tokens
        B->>P: Store New Refresh Token
        B-->>F: New Token Pair
        F->>F: Update localStorage
    end
```

### Weather API Flow

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        U[User Request<br/>GET /weather/current?lat=52.52&lon=13.41]
    end

    subgraph API["API Layer"]
        R[Weather Router]
        V[Pydantic Validation<br/>lat: -90..90<br/>lon: -180..180]
    end

    subgraph Domain["Domain Layer"]
        S[WeatherService]
    end

    subgraph Infra["Infrastructure Layer"]
        C[WeatherCache<br/>Redis]
        W[OpenMeteoClient<br/>httpx]
    end

    subgraph External["External"]
        OM[(Open-Meteo API)]
    end

    U --> R
    R --> V
    V --> S

    S --> C
    C -->|Cache Hit| S
    C -->|Cache Miss| W
    W -->|1s timeout| OM
    OM --> W
    W -->|Store 60s| C

    S --> R
    R --> U

    classDef api fill:#e6f3ff,stroke:#0066cc
    classDef domain fill:#fff3e6,stroke:#cc6600
    classDef infra fill:#e6ffe6,stroke:#00cc00
    classDef external fill:#ffe6e6,stroke:#cc0000

    class R,V api
    class S domain
    class C,W infra
    class OM external
```

### Component Dependency Graph

```mermaid
graph LR
    subgraph API["API Layer"]
        AR[Auth Router]
        WR[Weather Router]
        AuR[Audit Router]
        AgR[Agent Router]
        MW[Middleware Stack]
    end

    subgraph Domain["Domain Layer"]
        AS[AuthService]
        WS[WeatherService]
        E[Entities]
        EX[Exceptions]
    end

    subgraph Infra["Infrastructure Layer"]
        UR[UserRepository]
        TR[TokenRepository]
        AUR[AuditRepository]
        JWT[JWTProvider]
        PWD[PasswordUtils]
        WC[WeatherClient]
        WCH[WeatherCache]
        RL[RateLimiter]
    end

    subgraph Data["Data Stores"]
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    subgraph External["External APIs"]
        OM[Open-Meteo]
    end

    AR --> AS
    AR --> MW
    WR --> WS
    WR --> MW
    AuR --> MW
    AgR --> MW

    AS --> UR
    AS --> TR
    AS --> JWT
    AS --> PWD
    AS --> RL

    WS --> WC
    WS --> WCH

    UR --> PG
    TR --> PG
    AUR --> PG

    WCH --> RD
    RL --> RD
    WC --> OM

    classDef api fill:#4a90d9,color:white
    classDef domain fill:#f5a623,color:white
    classDef infra fill:#7ed321,color:white
    classDef data fill:#9013fe,color:white
    classDef external fill:#d0021b,color:white

    class AR,WR,AuR,AgR,MW api
    class AS,WS,E,EX domain
    class UR,TR,AUR,JWT,PWD,WC,WCH,RL infra
    class PG,RD data
    class OM external
```

### Kubernetes Deployment Architecture

```mermaid
graph TB
    subgraph Internet
        USER[Users]
    end

    subgraph K8s["Kubernetes Cluster"]
        subgraph Ingress["Ingress Layer"]
            ING[Ingress Controller]
        end

        subgraph App["Application Namespace: tequipy"]
            subgraph Backend["Backend Deployment"]
                B1[Pod 1<br/>FastAPI]
                B2[Pod 2<br/>FastAPI]
                Bn[Pod N<br/>FastAPI]
            end

            SVC[Service<br/>ClusterIP]
            HPA[HPA<br/>2-10 replicas]
            PDB[PDB<br/>minAvailable: 1]

            subgraph Config
                CM[ConfigMap]
                SEC[Secret]
            end
        end

        subgraph Data["Data Layer"]
            PG[(PostgreSQL<br/>StatefulSet)]
            RD[(Redis<br/>Deployment)]
        end

        subgraph Monitoring["Monitoring"]
            PROM[Prometheus]
            GRAF[Grafana]
        end
    end

    subgraph External
        OM[Open-Meteo API]
    end

    USER --> ING
    ING --> SVC
    SVC --> B1
    SVC --> B2
    SVC --> Bn

    HPA -.->|scales| Backend
    PDB -.->|protects| Backend

    B1 --> PG
    B1 --> RD
    B1 --> OM

    B2 --> PG
    B2 --> RD
    B2 --> OM

    PROM -->|scrape| B1
    PROM -->|scrape| B2
    GRAF --> PROM

    CM -.->|env| B1
    CM -.->|env| B2
    SEC -.->|secrets| B1
    SEC -.->|secrets| B2

    classDef user fill:#9013fe,color:white
    classDef ingress fill:#f5a623,color:white
    classDef app fill:#4a90d9,color:white
    classDef data fill:#7ed321,color:white
    classDef monitoring fill:#50e3c2,color:black
    classDef external fill:#d0021b,color:white

    class USER user
    class ING ingress
    class B1,B2,Bn,SVC,HPA,PDB,CM,SEC app
    class PG,RD data
    class PROM,GRAF monitoring
    class OM external
```

### Metrics Collection Flow

```mermaid
flowchart LR
    subgraph App["Application"]
        B[Backend<br/>FastAPI]
        M[Metrics<br/>Middleware]
        E[/metrics<br/>endpoint/]
    end

    subgraph Prometheus
        P[Prometheus<br/>Server]
        A[(Time Series<br/>Database)]
    end

    subgraph Grafana
        G[Grafana<br/>Dashboards]
        D1[API Performance]
        D2[Auth Metrics]
        D3[Weather Cache]
    end

    B --> M
    M --> E
    P -->|scrape /metrics<br/>every 15s| E
    P --> A

    G --> P
    G --> D1
    G --> D2
    G --> D3

    style B fill:#4a90d9,color:white
    style P fill:#e6522c,color:white
    style G fill:#f46800,color:white
```

## How to Use These Diagrams

### Viewing in GitHub/GitLab

All diagrams use [Mermaid](https://mermaid.js.org/) syntax and render automatically in:

- GitHub README/Markdown files
- GitLab README/Markdown files
- VS Code with Mermaid extension

### Editing Diagrams

1. Use the [Mermaid Live Editor](https://mermaid.live/) for real-time preview
2. Copy diagram code from this file
3. Modify and preview
4. Copy back to this file

### Exporting to Images

```bash
# Using mermaid-cli
npm install -g @mermaid-js/mermaid-cli
mmdc -i 09-interactive-visualization.md -o diagrams/

# Or use the Live Editor export feature
```

## Diagram Legend

| Color            | Meaning                |
| ---------------- | ---------------------- |
| Blue (#4a90d9)   | API/Presentation Layer |
| Orange (#f5a623) | Domain/Business Layer  |
| Green (#7ed321)  | Infrastructure Layer   |
| Purple (#9013fe) | Data Stores            |
| Red (#d0021b)    | External Services      |
| Cyan (#50e3c2)   | Monitoring             |

## Related Documentation

- [System Context (C4 Level 1)](./01-system-context.md)
- [Container Architecture (C4 Level 2)](./02-container-architecture.md)
- [Component Architecture (C4 Level 3)](./03-component-architecture.md)
- [Deployment Architecture](./06-deployment-architecture.md)
