const INITIAL_TEXT = document.getElementById('text').value;

async function loadFont(family, url, weight, style) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Status ${response.status}`);
  const data = await response.arrayBuffer();
  const font = new FontFace(family, data, { style, weight });
  await font.load();
  document.fonts.add(font);
}

async function init() {
  const stack = document.getElementById('variants');
  const errors = document.getElementById('font-errors');
  const status = document.getElementById('font-status');
  const count = document.getElementById('variant-count');

  let variants = [];
  try {
    const res = await fetch('./variants.json');
    const data = await res.json();
    variants = data.variants;
  } catch (e) {
    document.body.dataset.previewState = 'error';
    status.textContent = '无法读取 variants.json';
    return;
  }

  let loadedCount = 0;
  for (const v of variants) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = `
      <div class="card-header">
        <h3>${v.family} <small>(${v.status})</small></h3>
        <button aria-expanded="true" aria-controls="body-${v.id}" aria-label="隐藏 ${v.family} 样例">Toggle</button>
      </div>
      <p>${v.description}</p>
      <div id="body-${v.id}" class="variant-body">
        ${['Regular', 'Bold', 'Italic', 'BoldItalic'].map(s => `<div class="style-block" data-style="${s}"><h4>${s}</h4><div class="sample-text"></div></div>`).join('')}
      </div>
    `;
    stack.appendChild(card);

    card.querySelector('button').addEventListener('click', (e) => {
      const body = document.getElementById(`body-${v.id}`);
      const expanded = e.target.getAttribute('aria-expanded') === 'true';
      body.hidden = expanded;
      e.target.setAttribute('aria-expanded', !expanded);
    });

    for (const [name, url] of Object.entries(v.styles)) {
      const weight = name.includes('Bold') ? '700' : '400';
      const style = name.includes('Italic') ? 'italic' : 'normal';
      const block = card.querySelector(`[data-style="${name}"]`);
      const sample = block.querySelector('.sample-text');

      try {
        await loadFont(v.family, url, weight, style);
        sample.style.fontFamily = `"${v.family}"`;
        sample.style.fontWeight = weight;
        sample.style.fontStyle = style;
        sample.textContent = INITIAL_TEXT;
        loadedCount++;
      } catch (e) {
        sample.remove();
        block.innerHTML += `<span class="error-msg">Failed: ${e.message}</span>`;
        block.classList.add('is-error');
        errors.hidden = false;
        errors.innerHTML += `<li>${v.family} ${name}: ${e.message}</li>`;
      }
    }
  }

  document.body.dataset.previewState = loadedCount > 0 ? 'ready' : 'error';
  status.textContent = loadedCount > 0 ? 'Ready' : '全部加载失败';
  count.textContent = `${variants.length} VARIANTS · ${loadedCount}/${variants.length * 4} FACES LOADED`;
  stack.ariaBusy = 'false';

  // Listeners
  document.getElementById('text').addEventListener('input', (e) => {
    document.querySelectorAll('.sample-text:not(.is-error)').forEach(t => t.textContent = e.target.value);
  });

  document.getElementById('reset-text').addEventListener('click', () => {
    document.getElementById('text').value = INITIAL_TEXT;
    document.querySelectorAll('.sample-text:not(.is-error)').forEach(t => t.textContent = INITIAL_TEXT);
  });

  document.getElementById('size').addEventListener('input', (e) => {
    document.querySelectorAll('.sample-text:not(.is-error)').forEach(t => t.style.fontSize = e.target.value + 'px');
    document.getElementById('size-value').textContent = e.target.value + ' px';
  });

  document.getElementById('ligatures').addEventListener('change', (e) => {
    const val = e.target.checked ? 'normal' : 'none';
    document.querySelectorAll('.sample-text:not(.is-error)').forEach(t => t.style.fontVariantLigatures = val);
  });
}

init();
