'use strict';

const menuButton = document.querySelector('.menu-toggle');
const navigation = document.querySelector('#main-nav');
function closeMenu() {
  menuButton?.setAttribute('aria-expanded', 'false');
  menuButton?.setAttribute('aria-label', 'メニューを開く');
  navigation?.classList.remove('open');
}
menuButton?.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!isOpen));
  menuButton.setAttribute('aria-label', isOpen ? 'メニューを開く' : 'メニューを閉じる');
  navigation.classList.toggle('open', !isOpen);
});
navigation?.querySelectorAll('a').forEach(link => link.addEventListener('click', closeMenu));
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
    closeMenu();
    menuButton.focus();
  }
});
document.addEventListener('click', event => {
  if (!event.target.closest('.site-header')) closeMenu();
});
window.matchMedia('(min-width: 701px)').addEventListener('change', closeMenu);

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
  if (countLabel) countLabel.textContent = count + (count === 1 ? ' CONCEPT' : ' CONCEPTS');
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

