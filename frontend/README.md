# Campus Customs Operations Desk (frontend)

React 19 + Vite + TypeScript dashboard for the Campus Customs agent team. See the project [README](../README.md) for the full setup.

```bash
npm install          # once
npm run dev          # http://localhost:5173 (expects the backend on http://localhost:8000)
npm run build        # type-check and production build into dist/
```

The backend URL comes from `VITE_API_BASE_URL` (see `.env.example`), with `http://localhost:8000` as the default. All requests go through `src/api/client.ts`, and `src/api/types.ts` mirrors the FastAPI response models. Design notes are in [`output/design.md`](../output/design.md).
