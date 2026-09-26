import { readFile, writeFile, mkdir, readdir, copyFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// Build real links into HTML so navigation also works without JavaScript.
// Only public assets below can enter the deployment package.
const root = fileURLToPath(new URL('../', import.meta.url));
const mode = process.argv[2] ?? '--preview';
if (!['--preview', '--production'].includes(mode) || process.argv.length > 3) {
  throw new Error('Usage: node scripts/build-site.mjs --preview|--production');
}
const preview = mode === '--preview';
const config = JSON.parse(await readFile(path.join(root, 'commerce.config.json'), 'utf8'));
const pages = ['index.html', 'shop.html', 'product.html', 'product-tee.html', 'product-cap.html'];
const staticFiles = ['styles.css', 'script.js', '.nojekyll'];
const images = ['brand-logo.webp', 'campaign-ig.webp', 'hero-campaign.webp', 'jacket-ig.webp', 'jacket-ig-card.webp', 'tee-ig.webp', 'tee-ig-card.webp', 'cap-ig.webp', 'cap-ig-card.webp', 'favicon.svg'];
const productPages = { 'product.html': 'denim-jacket', 'product-tee.html': 'logo-tee', 'product-cap.html': 'logo-cap' };
const live = !preview && config.enabled === true;
const escape = value => String(value).replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);

function publicUrl(value, label) {
  let url;
  try { url = new URL(value); } catch { throw new Error(`${label}: HTTPS URLを入力してください。`); }
  if (url.protocol !== 'https:' || url.username || url.password || url.port || url.search || url.hash) {
    throw new Error(`${label}: 認証情報・クエリ・ハッシュを含まないHTTPS URLが必要です。`);
  }
  if (url.hostname === 'localhost' || url.hostname.endsWith('.localhost') || url.hostname.endsWith('.example') || url.hostname === 'example.com' || url.hostname.endsWith('.example.com')) {
    throw new Error(`${label}: 実際の公開URLを指定してください。`);
  }
  return url;
}

let shop;
let brand;
const itemUrls = new Map();
if (live) {
  shop = publicUrl(config.baseShopUrl, 'baseShopUrl');
  if (shop.pathname !== '/') throw new Error('baseShopUrlにはBASEショップのトップURLを指定してください。');
  brand = publicUrl(config.brandSiteUrl, 'brandSiteUrl');
  if (brand.hostname === 'github.io' || brand.hostname.endsWith('.github.io')) {
    throw new Error('販売用サイトはGitHub Pages以外の公開先を設定してください。');
  }
  if (!brand.pathname.endsWith('/')) brand.pathname += '/';
  for (const id of Object.values(productPages)) {
    const product = config.products?.[id];
    if (product?.confirmed !== true) continue;
    const item = publicUrl(product.baseItemUrl, `products.${id}.baseItemUrl`);
    if (item.origin !== shop.origin || !/^\/items\/\d+\/?$/.test(item.pathname)) {
      throw new Error(`${id}: 同じBASEショップの /items/商品ID というURLを指定してください。`);
    }
    item.pathname = item.pathname.replace(/\/$/, '');
    itemUrls.set(id, item.href);
  }
}

function replaceRegion(html, name, content) {
  const expression = new RegExp(`<!-- commerce:${name}:start -->[\\s\\S]*?<!-- commerce:${name}:end -->`, 'g');
  return html.replace(expression, () => content);
}

function purchaseBlock(id) {
  const url = itemUrls.get(id);
  if (!url) return null;
  return `<div class="product-price"><strong>販売ページで確認</strong><span>最新の価格・在庫</span></div>
        <p class="purchase-note">実際の商品写真・サイズ・仕様・配送条件は、公式オンラインストアでご確認ください。</p>
        <a class="button purchase-link" href="${escape(url)}">BASEで商品・購入条件を見る <span aria-hidden="true">↗</span></a>
        <p class="purchase-note">公式オンラインストア（BASE）へ移動します。サイズ・数量の選択とお支払いは移動先で行えます。</p>`;
}

const output = path.join(root, '.publish', preview ? 'preview' : 'production');
await mkdir(path.join(output, 'assets'), { recursive: true });
// Reject unknown files instead of accidentally shipping old private material.
for (const [folder, allowed] of [[output, [...pages, ...staticFiles, 'assets', 'robots.txt']], [path.join(output, 'assets'), images]]) {
  for (const entry of await readdir(folder)) {
    if (!allowed.includes(entry)) throw new Error(`公開フォルダに想定外のファイルがあります: ${path.join(folder, entry)}`);
  }
}

for (const page of pages) {
  let html = await readFile(path.join(root, page), 'utf8');
  // Keep the brand site connected to the shop while its BASE catalog is still being prepared.
  // Product-specific purchase links remain gated by `enabled` and confirmed item URLs below.
  const shopUrl = publicUrl(config.baseShopUrl, 'baseShopUrl');
  if (shopUrl.pathname !== '/') throw new Error('baseShopUrlにはBASEショップのトップURLを指定してください。');
  html = html.replace(/<a class="header-shop" data-base-shop href="[^"]*">[\s\S]*?<\/a>/g,
    () => `<a class="header-shop" href="${escape(shopUrl.href)}">BASE STORE <span aria-hidden="true">↗</span></a>`);
  html = html.replace(/(<a class="hero-collection-link" data-base-shop href=")[^"]*("[^>]*>)/g,
    (_, before, after) => `${before}${escape(shopUrl.href)}${after}`);
  html = html.replace(/(<a class="text-link" data-base-shop href=")[^"]*("[^>]*>)/g,
    (_, before, after) => `${before}${escape(shopUrl.href)}${after}`);
  if (live) {
    html = html.replace(/<a class="header-shop" href="[^"]*">BASEショップへ <span aria-hidden="true">↗<\/span><\/a>/g,
      () => `<a class="header-shop" href="${escape(shop.href)}">BASEショップへ <span aria-hidden="true">↗</span></a>`);
    html = html.replace(/<div class="announcement">[\s\S]*?<\/div>/,
      '<div class="announcement"><span>LIFE IS MAX BET</span><span>商品はBASEで販売中</span></div>');
    html = replaceRegion(html, 'store-panel', `<section class="store-panel" aria-labelledby="store-panel-title"><div><p class="eyebrow">公式オンラインストア</p><h2 id="store-panel-title">気になる一着を、オンラインで。</h2><p>販売中の商品、サイズ、価格はBASEの商品ページでご確認いただけます。</p></div><a class="button" href="${escape(shop.href)}">BASEショップを見る <span aria-hidden="true">↗</span></a></section>`);
    html = replaceRegion(html, 'guide-purchase', '<details><summary>どこで購入できますか？</summary><p>公式オンラインストア（BASE）で購入できます。商品・サイズ・数量を選び、カートから購入手続きへお進みください。このサイトの写真には制作イメージが含まれます。実際の商品写真と販売条件はBASEの商品ページをご確認ください。</p></details>');
    html = replaceRegion(html, 'guide-intro', '<p>お買いものは公式オンラインストアへ。<br>新作や日々の様子は、公式Instagramへ。</p>');
    html = replaceRegion(html, 'guide-delivery', '<details><summary>サイズ・配送・返品について</summary><p>サイズ展開や実寸、送料、発送目安、返品・交換条件は、公式オンラインストア（BASE）の商品ページとご利用案内をご確認ください。</p></details>');
    const purchase = purchaseBlock(productPages[page]);
    if (purchase) html = replaceRegion(html, 'purchase', purchase);
    for (const [id] of itemUrls) {
      html = html.replaceAll(`<span data-product-price="${id}">価格未定</span>`, '<span>価格は販売ページへ</span>');
    }
    if (purchase) {
      html = replaceRegion(html, 'product-terms', '<details><summary>素材・サイズについて</summary><p>実際の素材、実寸、カラー・サイズ展開は、リンク先のBASE商品ページでご確認ください。</p></details><details><summary>配送・返品について</summary><p>最新の送料、発送目安、返品・交換条件は公式オンラインストア（BASE）でご確認ください。</p></details>');
      html = html.replaceAll('実際の商品情報は発売前にご案内します。', '実際の商品情報は公式オンラインストアでご確認ください。');
    }
    html = html.replaceAll('実際の商品・仕様・価格は発売前にご案内します。', '実際の商品・仕様・価格は公式オンラインストアでご確認ください。');
    html = html.replaceAll('実際の商品写真、仕様、価格は販売開始前にご案内します。', '実際の商品写真、仕様、価格は公式オンラインストアでご確認ください。');
    const canonical = new URL(page === 'index.html' ? './' : page, brand).href;
    const imageUrl = new URL(page === 'index.html' ? 'assets/hero-campaign.webp' : 'assets/campaign-ig.webp', brand).href;
    html = html.replace(/<meta property="og:image" content="[^"]*">/, () => `<meta property="og:image" content="${escape(imageUrl)}">`);
    html = html.replace('</head>', `  <link rel="canonical" href="${escape(canonical)}">\n  <meta property="og:url" content="${escape(canonical)}">\n</head>`);
  } else {
    html = html.replace('</head>', '  <meta name="robots" content="noindex, nofollow">\n</head>');
  }
  await writeFile(path.join(output, page), html, 'utf8');
}
for (const file of staticFiles) await copyFile(path.join(root, file), path.join(output, file));
for (const file of images) await copyFile(path.join(root, 'assets', file), path.join(output, 'assets', file));
await writeFile(path.join(output, 'robots.txt'), live ? 'User-agent: *\nAllow: /\n' : 'User-agent: *\nDisallow: /\n');
console.log(`Output: ${output}\nBASE links: ${live ? `enabled (${itemUrls.size} confirmed products)` : 'disabled / preview'}\nBASEへの登録・デプロイ・購入は行っていません。`);
