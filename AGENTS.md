# LIFE IS MAX BET project preferences

## Publishing routine site changes

The user wants requested site changes reflected in production as part of the same task. Unless the user explicitly requests a draft or local-only work, include a production build, commit, and push of the relevant public site changes to `main`. Stage explicit paths; do not include unrelated business documents or unreviewed changes.

Cloudflare Workers Builds is the intended deployment mechanism for `polished-river-d244`, configured by `wrangler.jsonc`. Its initial connection may still need completion; consult README.md and the actual Cloudflare state. Do not claim automatic deployment is active until it is connected, or claim a release succeeded until the deployment reports success.

Production: https://polished-river-d244.252595tana.workers.dev/
Build: `node scripts/build-site.mjs --production`
Publish directory: `.publish/production`

Local saves are not the deployment trigger; pushing `main` is. GitHub Pages is a design preview only. Do not turn on sales or change the BASE shop's visibility as part of a routine code deployment.

## Brand and commerce constraints

- Preserve BASE's existing top logo.
- The brand TOP and BASE checkout are separate sites; code deployment does not update BASE theme settings.
- BASE design changes need BASE's Save action.
- Do not invent product prices, inventory, sizing, shipping, or sales claims. Product links remain gated by confirmed mappings in `commerce.config.json`.
- Use the existing free hosting/theme choices; do not buy plans, themes, domains, or Apps.
