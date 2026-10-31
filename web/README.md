# web (dashboard)

Static Next.js dashboard for The Research Roundup. It reads the JSON and newsletter HTML that the pipeline writes into `public/data/` and `public/newsletters/`; there is no server at runtime.

```bash
cd web
npm install
npm run dev     # http://localhost:3000
npm run build   # static site in out/
```
