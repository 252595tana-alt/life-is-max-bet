# LIFE IS MAX BET

Red and black editorial brand site. The original TOP and lookbook stay independent; a BASE store handles official product details, inventory, cart, payment and orders. GitHub Pages hosts a non-selling design preview only.

## Pages

- index.html: campaign, collection preview, lookbook, brand story, guide
- shop.html: collection and category filtering (URL preserves the selection)
- product.html: denim jacket concept
- product-tee.html: T-shirt concept
- product-cap.html: cap concept

Product pages include detail views, an accessible image zoom dialog, and related items. Current product imagery is illustrative. The selected BASE account's shop URL is <https://lifeismaxbet.base.shop/>. No actual products have been decided or listed, so the brand site does not accept orders and purchase links remain disabled.

## Assets

Four images were created with the built-in image_gen tool using the official Instagram profile (https://www.instagram.com/lifeismaxbet/) as reference: an industrial waterfront campaign, a blue denim jacket, a red logo T-shirt, and a black flat-brim cap. Product mockups use gray backgrounds. The campaign model is fictional. The actual profile logo is used in the header. Each product page links to its source post; captions and product specifications were not accessible, so no price, stock, sizing or material claims are inferred. WebP versions live in assets/, with smaller card variants for product grids. The full prompt set and original requirement documents are retained locally outside Git tracking.

## Editing and publishing

Edit the HTML pages, styles.css and script.js directly. Product imagery can be replaced in assets/. Keep repeated navigation, footer and product cards consistent. Update the stylesheet/script version parameters when changing them.

The main branch builds a preview with .github/workflows/pages.yml. Only explicitly selected HTML, CSS, JS and image files are copied into the public artifact. Private requirements and working material are excluded by .gitignore. The preview build always disables sales links and includes noindex, regardless of the production configuration.

## BASE integration

Use a free official BASE theme for the store. Keep the brand TOP here and add BRAND SITE / LOOKBOOK return links using BASE's navigation settings. No custom BASE template, API credentials, local cart, iframe checkout or database is required.

`commerce.config.json` is the source of the connection settings. The real BASE shop URL is recorded; the integration remains disabled until a production brand-site URL and real BASE product mappings are ready:

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

For production hosting, use a free static host such as Cloudflare Pages: build command `node scripts/build-site.mjs --production`, output directory `.publish/production`. Cloudflare authentication and a production URL are still required. The BASE navigation currently points back to the GitHub Pages preview for BRAND TOP and LOOKBOOK; update both links to the production URL after hosting is ready. Only upload the generated output. Do not upload the repository root.

GitHub Pages [does not permit e-commerce hosting](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). Keep it as a design preview and move production before enabling sales links. BASE's standard plan has no initial/monthly fee, but sales and payout fees apply. New paid plans, domains and Apps have not been purchased.

## Before selling

The selected BASE account is configured with the free SIMPLE theme, a black background, red accents, a high-contrast brand title, and navigation links back to BRAND TOP and LOOKBOOK. Its shop is currently private and BASE has suspended its payment feature pending a settings update, so do not sell yet. No products have been decided or listed. Before selling, restore payment and shop visibility, add confirmed product photos and details in BASE, complete shipping and seller information, move the brand site to production hosting, update the two temporary BASE navigation URLs, and set confirmed product mappings. No purchase flow has been tested.

Detailed Japanese handoff material, the logo and a product-mapping worksheet are retained locally under `ECサイト構築素材/BASE設定パッケージ/`; the architecture decision is in `ECサイト構築素材/スクラッチとBASEの連携方針.md`.

Official references: [BASE navigation](https://help.thebase.in/hc/ja/articles/206418081), [BASE design settings](https://help.thebase.in/hc/ja/articles/900002956603), [widget restrictions](https://help.thebase.in/hc/ja/articles/900000108823), [BASE pricing](https://thebase.com/payments), [Cloudflare static HTML](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/).
