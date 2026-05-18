# AI Architecture Design Prototype

Full-stack prototype for AI-driven architecture design: prompt input, structured parsing, floor plan generation, 2D/3D viewers, furniture placement, cost estimation, and project persistence.

## Tech Stack

| Layer    | Stack |
|----------|--------|
| Frontend | Next.js (App Router), React, Tailwind CSS, React Three Fiber |
| Backend  | FastAPI (Python) |
| Database | Supabase |

## Features (to be built step by step)

1. **Prompt input** — Architectural requirements as natural language
2. **Prompt parser** — Converts text into structured JSON
3. **Floor plan generator** — Generates floor plans from structured data
4. **2D floor plan viewer** — View and interact with floor plans
5. **3D house generator** — 3D model from floor plan
6. **Interior furniture placement** — Place and arrange furniture
7. **Cost estimation engine** — Estimate costs from design
8. **3D walkthrough mode** — First-person or camera walkthrough
9. **Save project** — Persist projects (e.g. Supabase)

## Project Structure

```
ai-architecture-app/
├── frontend/          # Next.js app (App Router, Tailwind, R3F)
├── backend/           # FastAPI server
├── assets/            # General assets
├── furniture/         # Furniture models/assets
├── textures/          # Textures for 3D
├── database/          # DB scripts, migrations (Supabase)
└── README.md
```

---

## Setup

### Prerequisites

- **Node.js** 18+ and **npm** (or yarn/pnpm)
- **Python** 3.10+
- **Supabase** account (for database and optional auth)

### 1. Clone and enter project

```bash
cd ai-architecture-app
```

### 2. Frontend setup

```bash
cd frontend
npm install
```

Create `.env.local` in `frontend/` if you need API base URL:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run the dev server:

```bash
npm run dev
```

Frontend: **http://localhost:3000**

### 3. Backend setup

```bash
cd backend
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (cmd):**

```cmd
.venv\Scripts\activate.bat
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

Install dependencies and run:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API: **http://localhost:8000**  
Docs: **http://localhost:8000/docs**

### 4. Supabase (optional for step 9)

1. Create a project at [supabase.com](https://supabase.com).
2. Copy **Project URL** and **anon/public key** from Settings → API.
3. In `backend/`, copy `.env.example` to `.env` and set:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key
```

### 5. LLM prompt parsing (recommended)

To use an LLM for parsing prompts (better extraction and support for new properties like garden, balcony, etc.):

1. Add `OPENAI_API_KEY` to `backend/.env` (from [OpenAI](https://platform.openai.com/api-keys)).
2. The `/parse_prompt` endpoint will then use the LLM to return core fields plus any extra key-value pairs mentioned in the prompt. If the key is missing or the LLM fails, the app falls back to rule-based parsing.

---

## Quick start (both servers)

**Terminal 1 — Frontend:**

```bash
cd ai-architecture-app/frontend && npm install && npm run dev
```

**Terminal 2 — Backend:**

```bash
cd ai-architecture-app/backend && python -m venv .venv
# Activate venv (see above), then:
pip install -r requirements.txt && uvicorn main:app --reload --port 8000
```

Then open http://localhost:3000 and http://localhost:8000/docs.

---

## License

MIT (or your choice).
