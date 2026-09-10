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

    const header = document.createElement('div');
    header.className = 'card-header';
    const heading = document.createElement('h3');
    const familyLabel = document.createElement('small');
    heading.textContent = `${v.family} `;
    familyLabel.textContent = `(${v.status})`;
    heading.appendChild(familyLabel);

    const bodyId = `body-${v.id}`;
    const toggle = document.createElement('button');
    toggle.setAttribute('aria-expanded', 'true');
    toggle.setAttribute('aria-controls', bodyId);
    toggle.setAttribute('aria-label', `隐藏 ${v.family} 样例`);
    toggle.textContent = 'Toggle';
    header.append(heading, toggle);

    const description = document.createElement('p');
    description.textContent = v.description;

    const body = document.createElement('div');
    body.setAttribute('id', bodyId);
    body.className = 'variant-body';
    const styleBlocks = new Map();
    for (const name of ['Regular', 'Bold', 'Italic', 'BoldItalic']) {
      const block = document.createElement('div');
      block.className = 'style-block';
      block.setAttribute('data-style', name);
      const styleHeading = document.createElement('h4');
      styleHeading.textContent = name;
      const sample = document.createElement('div');
      sample.className = 'sample-text';
      block.append(styleHeading, sample);
      body.appendChild(block);
      styleBlocks.set(name, { block, sample });
    }

    card.append(header, description, body);
    stack.appendChild(card);

    toggle.addEventListener('click', (e) => {
      const expanded = e.target.getAttribute('aria-expanded') === 'true';
      body.hidden = expanded;
      e.target.setAttribute('aria-expanded', !expanded);
    });

    for (const [name, url] of Object.entries(v.styles)) {
      const weight = name.includes('Bold') ? '700' : '400';
      const style = name.includes('Italic') ? 'italic' : 'normal';
      const styleElements = styleBlocks.get(name);
      const block = styleElements.block;
      const sample = styleElements.sample;

      try {
        await loadFont(v.family, url, weight, style);
        sample.style.fontFamily = `"${v.family}"`;
        sample.style.fontWeight = weight;
        sample.style.fontStyle = style;
        sample.textContent = INITIAL_TEXT;
        loadedCount++;
      } catch (e) {
        sample.remove();
        const errorMessage = document.createElement('span');
        errorMessage.className = 'error-msg';
        errorMessage.textContent = `Failed: ${e.message}`;
        block.appendChild(errorMessage);
        block.classList.add('is-error');
        errors.hidden = false;
        const errorItem = document.createElement('li');
        errorItem.textContent = `${v.family} ${name}: ${e.message}`;
        errors.appendChild(errorItem);
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
