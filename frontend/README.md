# imigrAI frontend

Base frontend separada com Next.js App Router para consumir a API FastAPI.

## Stack

- Next.js + TypeScript
- Tailwind CSS
- React Query
- React Hook Form + Zod

## Setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Frontend local: `http://localhost:3000`

## Variaveis

- `NEXT_PUBLIC_API_BASE_URL` (padrao: `http://localhost:8000/api/v1`)

## Rotas implementadas

- `/`
- `/login`
- `/register`
- `/onboarding`
- `/results/[assessmentId]`
- `/pricing`
- `/roadmaps/[roadmapId]`
- `/dashboard`
- `/settings/subscription`

## Hooks de dominio

- `useAssessment`
- `useRoadmap`
- `useSubscription`

## Testes

```bash
npm run test
npm run test:e2e
```
