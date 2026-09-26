# LIFE IS MAX BET

Red and black editorial storefront, published with GitHub Pages.

## Pages

- index.html: campaign, collection preview, lookbook, brand story, guide
- shop.html: collection and category filtering (URL preserves the selection)
- product.html: denim jacket concept
- product-tee.html: T-shirt concept
- product-cap.html: cap concept

Product pages include detail views, an accessible image zoom dialog, and related items. All products are illustrative concepts. Prices, sizes, release dates, inventory and checkout have not been configured. The site labels the AI imagery and does not accept orders.

## Assets

Four images were created with the built-in image_gen tool using the official Instagram profile (https://www.instagram.com/lifeismaxbet/) as reference: an industrial waterfront campaign, a blue denim jacket, a red logo T-shirt, and a black flat-brim cap. Product mockups use gray backgrounds. The campaign model is fictional. The actual profile logo is used in the header. Each product page links to its source post; captions and product specifications were not accessible, so no price, stock, sizing or material claims are inferred. WebP versions live in assets/, with smaller card variants for product grids. The full prompt set and original requirement documents are retained locally outside Git tracking.

## Editing and publishing

Edit the HTML pages, styles.css and script.js directly. Product imagery can be replaced in assets/. Keep repeated navigation, footer and product cards consistent. Update the stylesheet/script version parameters when changing them.

The main branch deploys using .github/workflows/pages.yml. Only explicitly selected HTML, CSS, JS and image files are copied into the public artifact. Private requirements and working material are excluded by .gitignore.

## Before selling

Replace concept photos and names with confirmed products, add real prices and size charts, then configure payment, shipping and legal information in BASE. Link each product to its actual BASE product URL. GitHub Pages currently serves the visual preview only.
