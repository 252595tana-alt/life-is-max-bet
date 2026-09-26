'use strict';

const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#main-nav');
// Keep the home hero clear; reveal navigation after the visitor starts scrolling.
const scrollHeader = document.querySelector('.home-page .site-header');
if (scrollHeader) {
  let headerUpdatePending = false;
  const updateScrollHeader = () => {
    scrollHeader.classList.toggle('is-visible', window.scrollY > 32);
    headerUpdatePending = false;
  };
  window.addEventListener('scroll', () => {
    if (headerUpdatePending) return;
    headerUpdatePending = true;
    window.requestAnimationFrame(updateScrollHeader);
  }, { passive: true });
  window.addEventListener('pageshow', updateScrollHeader);
  updateScrollHeader();
}
function closeMenu(restoreFocus = false) {
  menuButton?.setAttribute('aria-expanded', 'false');
  menuButton?.setAttribute('aria-label', 'メニューを開く');
  navigation?.classList.remove('open');
  document.body.classList.remove('menu-open');
  document.querySelectorAll('main, .site-footer').forEach(element => { element.inert = false; });
  if (restoreFocus) menuButton?.focus();
}
menuButton?.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  if (isOpen) { closeMenu(true); return; }
  menuButton.setAttribute('aria-expanded', 'true');
  menuButton.setAttribute('aria-label', 'メニューを閉じる');
  navigation.classList.add('open');
  document.body.classList.add('menu-open');
  document.querySelectorAll('main, .site-footer').forEach(element => { element.inert = true; });
  navigation.querySelector('a')?.focus();
});
navigation?.querySelectorAll('a').forEach(link => link.addEventListener('click', () => closeMenu()));
document.addEventListener('keydown', event => {
  if (menuButton?.getAttribute('aria-expanded') !== 'true') return;
  if (event.key === 'Escape') {
    event.preventDefault();
    closeMenu(true);
  } else if (event.key === 'Tab') {
    const controls = [...document.querySelectorAll('.site-header a, .menu-toggle')];
    const first = controls[0];
    const last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  }
});
document.addEventListener('click', event => {
  if (!event.target.closest('.site-header')) closeMenu();
});
window.matchMedia('(min-width: 901px)').addEventListener('change', () => closeMenu());

// Motion can be paused without losing the original English brand copy.
const ticker = document.querySelector('.ticker');
const tickerButton = document.querySelector('.ticker-toggle');
tickerButton?.addEventListener('click', () => {
  const paused = ticker.classList.toggle('paused');
  tickerButton.setAttribute('aria-pressed', String(paused));
  tickerButton.setAttribute('aria-label', paused ? '流れる文字を再生' : '流れる文字を一時停止');
  tickerButton.querySelector('span').textContent = paused ? '▶' : 'Ⅱ';
});

// Collection filtering preserves a shareable URL and browser back/forward.
const filters = [...document.querySelectorAll('[data-filter]')];
const cards = [...document.querySelectorAll('.catalog .product-card')];
function applyFilter(category) {
  const selected = filters.some(button => button.dataset.filter === category) ? category : 'ALL';
  filters.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.filter === selected)));
  let count = 0;
  cards.forEach(card => {
    card.hidden = selected !== 'ALL' && card.dataset.category !== selected;
    if (!card.hidden) count += 1;
  });
  const countLabel = document.querySelector('.item-count');
  if (countLabel) countLabel.textContent = count + '点の商品イメージ';
  document.querySelector('.catalog')?.classList.toggle('filtered', selected !== 'ALL');
}
if (filters.length) {
  applyFilter(new URLSearchParams(location.search).get('category'));
  filters.forEach(button => button.addEventListener('click', () => {
    const category = button.dataset.filter;
    applyFilter(category);
    const url = new URL(location.href);
    if (category === 'ALL') url.searchParams.delete('category');
    else url.searchParams.set('category', category);
    history.pushState({}, '', url);
  }));
  window.addEventListener('popstate', () => applyFilter(new URLSearchParams(location.search).get('category')));
}

// Product image detail and native, keyboard-accessible zoom dialog.
const stage = document.querySelector('.gallery-stage');
const dialog = document.querySelector('.image-dialog');
document.querySelectorAll('.gallery-tabs button').forEach(button => {
  button.addEventListener('click', () => {
    stage.dataset.view = button.dataset.view;
    document.querySelectorAll('.gallery-tabs button').forEach(tab => {
      tab.setAttribute('aria-pressed', String(tab === button));
    });
  });
});
if (stage && dialog) {
  stage.addEventListener('click', () => {
    closeMenu();
    dialog.showModal();
    document.body.classList.add('dialog-open');
  });
  dialog.querySelector('button').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      dialog.close();
    }
  });
  dialog.addEventListener('close', () => {
    document.body.classList.remove('dialog-open');
    stage.focus({ preventScroll: true });
  });
}

