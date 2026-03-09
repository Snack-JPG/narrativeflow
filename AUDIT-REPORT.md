# NarrativeFlow Demo Readiness Audit

Date: 2026-03-09
Repo: `/Users/austin/Desktop/narrative-flow`

## What I checked
- Startup/import paths: `main.py`, `app/main.py`, `narrative_flow/api/main.py`
- Container orchestration: `docker-compose.yml`, `Dockerfile`, frontend Docker build
- Dependency completeness: `requirements.txt`
- Frontend/backend integration: REST base URL + WebSocket protocol compatibility
- Placeholder/TODO coverage and test/lint/build status
- Circular dependency scan (static import graph)

## Verification summary
- `python3 -m compileall ...` -> **PASS** (syntax is valid)
- `import narrative_flow.api.main` -> **PASS**
- `import app.main` -> **PASS**
- `docker compose config` -> **PASS** (valid after fixes)
- `python3 -m pytest -q` -> **FAIL** during collection (stale test imports)
- `frontend npm run lint` -> **FAIL** (36 errors, 7 warnings)
- `frontend npm run build` -> **FAIL in this environment** (Google Fonts fetch blocked)
- Static circular import scan -> **No cycles found**

## P0 - Critical / Broken
### Fixed during this audit
1. Broken API entrypoint in `app/main.py` (imported non-existent modules, causing immediate startup failure).
   - Fix: replaced with compatibility wrapper that serves `narrative_flow.api.main:app`.

2. `narrative_flow/api/briefing_routes.py` startup-breaking issues:
   - Bad import: `get_db_session` imported from wrong module.
   - Eager `ClaudeClient()` construction crashed import when `ANTHROPIC_API_KEY` is unset.
   - Invalid `DivergenceDetector()` instantiation without required DB session.
   - Fix: corrected DB import, made Claude/briefing generator lazy, removed invalid detector init.

3. Docker Compose frontend build blocker:
   - `frontend/Dockerfile` was referenced but missing.
   - Fix: added `frontend/Dockerfile`.

4. Docker Compose runtime blocker for AI service:
   - `python -m app.services.ai_analyzer` target module did not exist.
   - Fix: added `app/services/ai_analyzer.py` worker entrypoint.

5. Docker Compose runtime/module visibility issue:
   - Services mounted `./app:/app`, hiding `narrative_flow` package and breaking imports at runtime.
   - Fix: changed service mounts to `./:/app` for backend services.

6. Postgres async DB configuration mismatch:
   - Compose used `postgresql://...` while SQLAlchemy async engine requires async driver URL.
   - `asyncpg` dependency missing.
   - Fix: updated compose DB URLs to `postgresql+asyncpg://...` and added `asyncpg==0.30.0` to `requirements.txt`.

7. Collector service command exited immediately:
   - `python -m narrative_flow.scheduler` previously only imported module and returned.
   - Fix: added runnable scheduler service loop + `main()` entrypoint in `narrative_flow/scheduler.py`.

8. Hardcoded service credentials in compose:
   - Postgres/Grafana passwords were hardcoded literals.
   - Fix: moved to env-driven defaults (`POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`).

### Remaining P0 blockers
- None confirmed after the above fixes.

## P1 - Major Issues
1. Source metadata is not persisted correctly in collectors.
   - Evidence: collectors write `metadata=...` instead of model field `source_metadata`.
   - Affected: `narrative_flow/collectors/base.py`, `binance.py`, `coingecko.py`, `defi_llama.py`.
   - Impact: metadata-dependent logic (sentiment enrichment, source details, APIs) silently loses data.

2. AI hybrid classification path can crash when AI fallback is triggered.
   - Evidence: `ClassificationRequest` expects `source_metadata`, but caller passes `metadata`.
   - Affected: `narrative_flow/engine/ai_classifier.py`.
   - Impact: runtime `TypeError` on AI-path classifications.

3. WebSocket `request_current` path uses DB dependency incorrectly.
   - Evidence: `async with get_db() as db` where `get_db()` is an async generator dependency.
   - Affected: `narrative_flow/api/websocket.py`.
   - Impact: runtime failure when clients request current signals.

4. Briefing generation data loaders are placeholders.
   - Evidence: helper methods return empty lists/dicts (`_get_social_data`, `_get_onchain_data`, `_get_price_data`, `_get_divergences`, etc.).
   - Affected: `narrative_flow/api/briefing_routes.py`.
   - Impact: “generate briefing” does not analyze real market data.

5. Frontend real-time integration is protocol-incompatible.
   - Evidence: frontend uses `socket.io-client`; backend exposes plain FastAPI WebSocket endpoint.
   - Affected: `frontend/lib/websocket.ts` vs `narrative_flow/api/main.py` + `narrative_flow/api/websocket.py`.
   - Impact: dashboard connection appears disconnected/no live alerts.

6. Telegram alert history retrieval loop condition is incorrect.
   - Evidence: Redis scan loop uses `cursor = "0"` then `while cursor != 0` (string vs int mismatch).
   - Affected: `narrative_flow/telegram/alerts.py`.
   - Impact: potential infinite loop / stuck reads.

7. Automated tests are currently broken.
   - Evidence: `python3 -m pytest -q` fails in collection (`LifecycleStage` import mismatch from `market_regime`).
   - Affected: `tests/test_ai_layer.py` and AI regime model naming consistency.

## P2 - Minor Issues
1. Local frontend default API base URL does not match backend route layout.
   - Evidence: default `NEXT_PUBLIC_API_URL` is `http://localhost:8000/api`, while most endpoints are mounted at root (except briefing under `/api/briefing`).
   - Affected: `frontend/lib/api.ts`.

2. Frontend quality gates fail (`npm run lint`).
   - Evidence: 36 lint errors, 7 warnings (`any` usage, hook dependency/declaration order issues).
   - Impact: poor maintainability and likely CI failures.

3. Dashboard uses mock data in core views.
   - Evidence: mock/fallback logic in `RotationChart`, `AIBriefingPanel`, `TopTokensPanel`.
   - Impact: demo can appear functional while disconnected from real backend state.

4. Offline/air-gapped frontend build is brittle.
   - Evidence: build fails when fetching Google Fonts (`Geist`, `Geist Mono`).
   - Impact: reproducibility issues in restricted network demo environments.

## P3 - Polish
1. Documentation drift.
   - Root `README.md` describes endpoints/tests/components that do not match current implementation.
   - `frontend/README.md` is still default Next.js boilerplate.

2. Legacy Compose schema warning.
   - `version:` key is obsolete in modern Docker Compose.

3. Some metrics/services are placeholders rather than instrumented.
   - Example: performance tracker includes hardcoded assumptions and mock-like defaults.

## Direct answers to requested checks
- Can the app start and run (`main.py`, `docker-compose.yml`, `requirements.txt`)?
  - `docker-compose.yml`: now structurally valid and no longer references missing files/modules.
  - `requirements.txt`: now includes async Postgres driver (`asyncpg`) required by compose DB URL.
  - `main.py`: codepath is valid, but in this local environment `apscheduler` and `praw` were not installed, so full startup could not be executed here.

- Placeholder/TODO comments for unfinished work?
  - Yes: briefing data helper functions are explicit placeholders.
  - UI also contains explicit mock data fallbacks.

- API keys properly handled?
  - Generally yes (env vars), with one improvement made: removed hardcoded infra passwords from compose to env-driven defaults.

- Frontend render + backend connectivity?
  - Render likely works, but real-time path is currently broken due Socket.IO vs plain WS mismatch.
  - REST connectivity depends on correct `NEXT_PUBLIC_API_URL` (default local value is currently inconsistent for non-briefing routes).

- Import errors/circular dependencies?
  - Circular dependencies: none detected in static scan.
  - Import errors: fixed critical import errors in `app/main.py` and briefing routes; remaining local import failures were dependency-install related in this environment.
