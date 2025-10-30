# Backend CORS and Frontend Integration

To avoid 502/blocked requests in preview environments, configure CORS properly:

- The backend reads allowed origins from:
  1. `CORS_ORIGINS` (comma-separated list)
  2. If not set, it derives from `FRONTEND_ORIGIN` or `REACT_APP_FRONTEND_URL` if provided
  3. Always includes `http://localhost:3000` as a fallback

Recommended settings:
- Local development:
  - Frontend: `REACT_APP_API_BASE=http://localhost:3001`
  - Backend: `CORS_ORIGINS=http://localhost:3000`
- Cloud preview:
  - Frontend: set `REACT_APP_API_BASE` to the backend preview URL (https)
  - Backend: set `FRONTEND_ORIGIN` (or `CORS_ORIGINS`) to the frontend preview URL

Static media:
- Files are saved under `MEDIA_DIR` (default: `./media`) and served at `/media`.
