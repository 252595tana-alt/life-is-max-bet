# LIFE IS MAX BET

Red and black editorial brand site focused on the LIFE IS MAX BET identity. The custom TOP stays independent; a BASE store handles official product details, inventory, cart, payment and orders. Production is hosted at <https://polished-river-d244.252595tana.workers.dev/>. GitHub Pages hosts a non-selling design preview only.

## Pages

- index.html: LMB logo hero, street and field imagery, brand story, Instagram and official store links
- shop.html, product.html, product-tee.html, product-cap.html: legacy URLs that redirect to the brand TOP, with a visible fallback link

The brand TOP does not publish a product catalog or accept orders. Its header and footer link to the official BASE store at <https://lifeismaxbet.base.shop/>. No actual products have been decided or listed.

## Assets

The remaining editorial photo is an AI-created image based on the official Instagram profile (https://www.instagram.com/lifeismaxbet/). It is labeled as an illustration on the site. Earlier product mockups remain in assets/ for URL compatibility but are no longer displayed on the brand TOP. The full prompt set and original requirement documents are retained locally outside Git tracking.

The home hero uses `assets/hero-lmb-logo.png`, a copy of the LMB logo image prepared for the BASE footer. The same image appears at desktop and mobile sizes.

## Editing and publishing

Edit the HTML pages, styles.css and script.js directly. Product imagery can be replaced in assets/. Keep repeated navigation, footer and product cards consistent. Update the stylesheet/script version parameters when changing them.

The main branch builds a preview with .github/workflows/pages.yml. Only explicitly selected HTML, CSS, JS and image files are copied into the public artifact. Private requirements and working material are excluded by .gitignore. The preview build does not activate product purchase links and includes noindex, regardless of the production configuration.

### Cloudflare production deployment

`wrangler.jsonc` targets the existing `polished-river-d244` Worker. Wrangler runs `node scripts/build-site.mjs --production` and uploads only `.publish/production`.

The intended automatic deployment trigger is a push to `main` through Cloudflare Workers Builds. The GitHub App is authorized as of 2026-09-27; the build connection still needs its deployment token configured and is not active yet. Set the Cloudflare build command to `node scripts/build-site.mjs --production` and the deploy command to `npx wrangler deploy`. Workers Builds requires an explicit build command rather than relying on Wrangler's local custom build configuration.

Once connected, routine site changes should include a commit and push of the intended public files. Local file saves alone do not deploy. Build failures must be reported and fixed; do not describe a push as a successful production deployment until Cloudflare reports success. BASE design settings remain separate and are applied with BASE's Save control.

## BASE integration

The store uses BASE's free SIMPLE theme. Its existing top logo is preserved. The navigation's ブランドサイト link returns to the Cloudflare production URL; LOOKBOOK was removed. No custom BASE template, API credentials, local cart, iframe checkout or database is required.

`commerce.config.json` is the source of the connection settings. The real BASE shop and production brand-site URLs are recorded. General store links work, while product purchase links remain disabled until the store and real product mappings are ready:

- `enabled`: activate only after the BASE store is ready.
- `brandSiteUrl`: the final HTTPS brand site URL, not GitHub Pages.
- `baseShopUrl`: the actual BASE store root URL.
- `products.*.baseItemUrl`: the matching BASE product URL, under the same store origin and `/items/` path.
- `products.*.confirmed`: activate the product link only after confirming the editorial concept corresponds to the real item.

The build writes links directly into the HTML. Purchase navigation works without browser JavaScript. It does not fetch or duplicate current prices, stock, sizes or order/customer data. These remain in BASE. Store URLs are public; do not add secrets to the config.

```sh
node scripts/build-site.mjs --preview
node scripts/build-site.mjs --production
```

Outputs: `.publish/preview/` and `.publish/production/`. The production output remains a preview while `enabled` is false. Unknown files in an output directory cause the build to stop rather than accidentally including private data. Builds do not deploy or modify BASE.

Production hosting uses Cloudflare Workers Static Assets. Only upload the generated `.publish/production` output; never upload the repository root. The BASE ブランドサイト navigation already points to production.

GitHub Pages [does not permit e-commerce hosting](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). Keep it as a design preview and move production before enabling sales links. BASE's standard plan has no initial/monthly fee, but sales and payout fees apply. New paid plans, domains and Apps have not been purchased.

## Before selling

The BASE HOME order is the existing logo, approved campaign image, ITEMS (desktop four columns / mobile two columns), CONCEPT, and Instagram. Its shop is currently private and BASE has suspended its payment feature pending a settings update. No products have been decided or listed. Before selling, restore payment and shop visibility, add confirmed product photos and details in BASE, complete shipping and seller information, and set confirmed product mappings. No purchase flow has been tested.

Detailed Japanese handoff material, the logo and a product-mapping worksheet are retained locally under `ECサイト構築素材/BASE設定パッケージ/`; the architecture decision is in `ECサイト構築素材/スクラッチとBASEの連携方針.md`.

Official references: [BASE navigation](https://help.thebase.in/hc/ja/articles/206418081), [BASE design settings](https://help.thebase.in/hc/ja/articles/900002956603), [widget restrictions](https://help.thebase.in/hc/ja/articles/900000108823), [BASE pricing](https://thebase.com/payments), [Cloudflare static HTML](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/).
