set dotenv-load := true

# Prefer local virtualenv binaries
export PATH := justfile_directory() + "/.venv/bin:" + env_var("PATH")

default:
  just --list

# Run FastAPI API server with hot-reload
run *args:
  uvicorn src.main:app --reload --port 8000 {{args}}

# Run Celery worker for background jobs
celery *args:
  celery -A src.orders.tasks.celery_app worker --loglevel=info {{args}}

# ── Migrations ────────────────────────────────────────────────────────────────
# Generate a new migration revision
mm *args:
  alembic revision --autogenerate -m "{{args}}"

# Run pending migrations
migrate:
  alembic upgrade head

# Rollback migrations
downgrade *args:
  alembic downgrade {{args}}

# ── Database & Seed ───────────────────────────────────────────────────────────
# Seed initial admin, customer, products, categories and homepage
seed:
  python -m scripts.seed

# ── Tests ─────────────────────────────────────────────────────────────────────
# Run pytest test suite
test *args:
  pytest -v {{args}}

# Run test coverage
test-cov *args:
  pytest -v --cov=src --cov-report=term-missing {{args}}

# ── Formatting & Linting ──────────────────────────────────────────────────────
# Format and lint code with ruff
lint:
  uv tool run ruff format src
  uv tool run ruff check --fix src

# Format check with ruff
check:
  uv tool run ruff check src
  uv tool run ruff format --check src

# ── Docker ────────────────────────────────────────────────────────────────────
# Start docker compose services in background
up *args:
  docker compose up -d {{args}}

# Stop docker compose services
down:
  docker compose down

# Check docker compose services status
ps:
  docker compose ps

# Rebuild docker compose containers
build:
  docker compose build

# ── Dependencies ──────────────────────────────────────────────────────────────
# Install dependencies into .venv
install:
  pip install -r requirements.txt

# ── Frontend Shortcuts (from Backend) ─────────────────────────────────────────
# Start Admin Panel frontend
admin *args:
  just -f ../e-commerce-admin-site/justfile -d ../e-commerce-admin-site dev {{args}}

# Start Customer Storefront
customer *args:
  just -f ../e-commerce-customer-site/justfile -d ../e-commerce-customer-site dev {{args}}
