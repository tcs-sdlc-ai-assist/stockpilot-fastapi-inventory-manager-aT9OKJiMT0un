# StockPilot

**StockPilot** is an intelligent inventory management system built with Python and FastAPI, designed to help businesses track stock levels, manage products, and streamline warehouse operations with AI-powered insights.

## Features

- **Product Management** — Create, update, and delete products with detailed metadata
- **Inventory Tracking** — Real-time stock level monitoring with low-stock alerts
- **Order Management** — Track incoming and outgoing orders with status workflows
- **AI-Powered Insights** — RAG-based search and recommendations using vector embeddings
- **Role-Based Access Control** — Admin and Staff roles with granular permissions
- **Audit Logging** — Full history of inventory changes and user actions
- **RESTful API** — Fully documented OpenAPI/Swagger endpoints
- **Background Tasks** — Automated stock alerts and report generation

## Tech Stack

- **Backend:** Python 3.12, FastAPI
- **Database:** PostgreSQL with SQLAlchemy 2.0 (async)
- **Vector Store:** ChromaDB for AI-powered search and RAG pipelines
- **Authentication:** JWT-based auth with passlib (bcrypt)
- **Validation:** Pydantic v2
- **Task Queue:** FastAPI BackgroundTasks
- **Testing:** pytest, httpx, pytest-asyncio
- **Deployment:** Docker, Vercel (serverless)

## Folder Structure

```
stockpilot/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Pydantic Settings configuration
│   ├── database.py             # Async database session management
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── inventory.py
│   │   └── order.py
│   ├── schemas/                # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── inventory.py
│   │   └── order.py
│   ├── routers/                # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── products.py
│   │   ├── inventory.py
│   │   └── orders.py
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── user_service.py
│   │   ├── product_service.py
│   │   ├── inventory_service.py
│   │   ├── order_service.py
│   │   └── vector_service.py
│   ├── dependencies/           # FastAPI dependency injection
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   └── database.py
│   ├── middleware/              # Custom middleware
│   │   ├── __init__.py
│   │   └── logging.py
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       ├── embeddings.py
│       └── security.py
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_products.py
│   ├── test_inventory.py
│   └── test_orders.py
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
├── alembic.ini
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── vercel.json
├── .env.example
└── README.md
```

## Setup Instructions

### Prerequisites

- Python 3.12+
- PostgreSQL 15+
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/stockpilot.git
cd stockpilot
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and update the values:

```bash
cp .env.example .env
```

Required environment variables:

| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@localhost:5432/stockpilot` |
| `SECRET_KEY` | JWT signing secret (min 32 chars) | `your-super-secret-key-change-in-production` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry in minutes | `30` |
| `CHROMA_DB_PATH` | Path to ChromaDB persistent storage | `./data/chromadb` |
| `OPENAI_API_KEY` | OpenAI API key for embeddings | `sk-...` |
| `CORS_ORIGINS` | Comma-separated allowed origins | `http://localhost:3000,https://yourdomain.com` |
| `ENVIRONMENT` | Runtime environment | `development` |

### 5. Run Database Migrations

```bash
alembic upgrade head
```

### 6. Start the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs are at `http://localhost:8000/docs`.

### Running with Docker

```bash
docker-compose up --build
```

## Running Tests

```bash
pytest -v
```

Run with coverage:

```bash
pytest --cov=app --cov-report=term-missing
```

## Deployment Guide (Vercel)

### 1. Install the Vercel CLI

```bash
npm install -g vercel
```

### 2. Configure `vercel.json`

Ensure your `vercel.json` is configured for the FastAPI serverless function:

```json
{
  "builds": [
    {
      "src": "app/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "app/main.py"
    }
  ]
}
```

### 3. Set Environment Variables

Add all required environment variables in the Vercel dashboard under **Settings → Environment Variables**. Ensure `CORS_ORIGINS` includes your production domain and `ENVIRONMENT` is set to `production`.

### 4. Deploy

```bash
vercel --prod
```

### Production Considerations

- Set `CORS_ORIGINS` to your specific production domains — never use `*`
- Use a managed PostgreSQL instance (e.g., Supabase, Neon, AWS RDS)
- Rotate `SECRET_KEY` periodically and use a cryptographically random value
- Enable HTTPS for all traffic
- Configure rate limiting at the infrastructure level
- Use a persistent volume or cloud storage for ChromaDB data in production

## Roles

### Admin

- Full access to all system features
- Manage users (create, update, deactivate)
- Configure system settings and thresholds
- View audit logs and analytics
- Manage product catalog and categories
- Override inventory adjustments

### Staff

- View and search products
- Record inventory movements (receive, dispatch, adjust)
- Create and process orders
- View own activity history
- Receive low-stock notifications

## Default Credentials

> ⚠️ **WARNING:** Change these credentials immediately after first login. Leaving default credentials in a production environment is a critical security risk.

| Role | Email | Password |
|---|---|---|
| Admin | `admin@stockpilot.com` | `admin123!` |
| Staff | `staff@stockpilot.com` | `staff123!` |

Default accounts are created during the initial database seed. Run the seed command:

```bash
python -m app.utils.seed
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI JSON:** `http://localhost:8000/openapi.json`

## License

**Private** — All rights reserved. This software is proprietary and confidential. Unauthorized copying, distribution, or modification of this project is strictly prohibited.