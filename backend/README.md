# SmartTap Backend

FastAPI + Supabase + Stripe + Resend.

## Local dev

```bash
cd backend
cp .env.example .env
# fill in secrets
uv sync
uv run uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs
