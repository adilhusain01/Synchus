# Meridian Web

Reactive operations client for the Meridian context layer.

## Stack

- React 19 and Vite
- TanStack Router and Query
- Zustand for shared route controls
- shadcn-style primitives and CVA
- Tailwind utilities directly in JSX
- MapLibre with OpenStreetMap raster tiles
- Koboyo operational iconography

## Development

Start `api_server.py` from the repository root, then:

```bash
pnpm install
pnpm dev
```

The Vite server proxies `/api` to `http://127.0.0.1:8780`. Server-sent context events invalidate the relevant TanStack cache automatically.

## Verification

```bash
pnpm build
pnpm lint
```
