let currentIndex = 0;
let games = [];

const BASE_GAME_ZOOM = 1.25;
const BASE_COMMENTARY_ZOOM = 1.33;
let zoomScale = 1.0;

function adjustZoom(delta) {
  zoomScale = Math.round((zoomScale + delta) * 10) / 10;
  zoomScale = Math.max(0.5, Math.min(2.0, zoomScale));
  applyZoom();
}

function applyZoom() {
  const root = document.documentElement;
  root.style.setProperty('--game-zoom', BASE_GAME_ZOOM * zoomScale);
  root.style.setProperty('--commentary-zoom', BASE_COMMENTARY_ZOOM * zoomScale);
  document.getElementById('zoom-level').textContent =
    Math.round(zoomScale * 100) + '%';
}

function init(gamesData) {
  games = gamesData;
  const list = document.getElementById('game-list');
  games.forEach((g, i) => {
    const li = document.createElement('li');
    const labelDiv = document.createElement('div');
    labelDiv.className = 'game-label';
    labelDiv.textContent = `$${g.latex_name}$`;
    const descDiv = document.createElement('div');
    descDiv.className = 'game-desc';
    descDiv.textContent = g.description;
    li.appendChild(labelDiv);
    li.appendChild(descDiv);
    li.onclick = () => { showGame(i); closeNav(); };
    list.appendChild(li);
  });
  // Navigate to hash, overview, or first game
  const hash = window.location.hash.slice(1);
  if (!hash || hash === 'overview') {
    showOverview();
  } else {
    const idx = games.findIndex(g => g.label === hash);
    showGame(idx >= 0 ? idx : 0);
  }
}

function makePanel(label, latexName, svgSrc) {
  const panel = document.createElement('div');
  panel.className = 'game-panel';
  const header = document.createElement('div');
  header.className = 'game-panel-header';
  header.textContent = `$${latexName}$`;
  panel.appendChild(header);
  const img = new Image();
  img.alt = label;
  img.src = svgSrc;
  panel.appendChild(img);
  return panel;
}

function showOverview() {
  currentIndex = -1;
  window.location.hash = 'overview';

  // Update sidebar highlight
  document.querySelectorAll('#game-list li').forEach(li => {
    li.classList.remove('active');
  });
  document.getElementById('nav-overview').classList.add('active');

  // Update title
  document.getElementById('game-title').textContent = 'Proof Overview';
  document.getElementById('game-subtitle').textContent = '';

  // Hide game display, show overview
  document.getElementById('game-display').style.display = 'none';
  const overview = document.getElementById('overview-display');
  overview.style.display = 'block';
  overview.innerHTML = '';

  // Build proof structure diagram
  const container = document.createElement('div');
  container.className = 'overview-flow';

  games.forEach((g, i) => {
    const card = document.createElement('div');
    card.className = 'overview-card';
    card.onclick = () => showGame(i);

    const label = document.createElement('div');
    label.className = 'overview-card-label';
    label.textContent = `$${g.latex_name}$`;
    card.appendChild(label);

    if (g.description) {
      const desc = document.createElement('div');
      desc.className = 'overview-card-desc';
      desc.textContent = g.description;
      card.appendChild(desc);
    }

    container.appendChild(card);
  });

  overview.appendChild(container);

  // Re-typeset MathJax
  if (window.MathJax && MathJax.typesetPromise) {
    MathJax.typesetPromise([overview]).catch(console.error);
  }

  // Update buttons
  document.getElementById('btn-prev').disabled = true;
  document.getElementById('btn-next').disabled = false;
}

function showGame(idx) {
  if (idx < 0 || idx >= games.length) return;
  currentIndex = idx;

  // Hide overview, show game display
  document.getElementById('overview-display').style.display = 'none';
  document.getElementById('game-display').style.display = 'flex';

  const g = games[idx];
  window.location.hash = g.label;

  // Update nav highlight
  document.getElementById('nav-overview').classList.remove('active');
  document.querySelectorAll('#game-list li').forEach((li, i) => {
    li.classList.toggle('active', i === idx);
    if (i === idx) li.scrollIntoView({ block: 'nearest' });
  });

  // Update title and subtitle
  document.getElementById('game-title').textContent = `$${g.latex_name}$`;
  document.getElementById('game-subtitle').textContent = g.description || '';

  // Build side-by-side display
  const container = document.getElementById('game-svg-container');
  container.innerHTML = '';

  const findGame = (label) => games.find(x => x.label === label);

  if (g.reduction && g.related_games && g.related_games.length > 0) {
    // Reduction with related games: show clean game(s) alongside highlighted reduction
    if (g.related_games.length === 1) {
      // 2-panel: clean game on left, highlighted reduction on right
      const rg = findGame(g.related_games[0]);
      if (rg) {
        container.appendChild(
          makePanel(rg.label, rg.latex_name, `games/${rg.label}-clean.svg`)
        );
      }
      container.appendChild(
        makePanel(g.label, g.latex_name, `games/${g.label}.svg`)
      );
    } else {
      // 3-panel: clean game[0] left, highlighted reduction middle, clean game[1] right
      const rg0 = findGame(g.related_games[0]);
      if (rg0) {
        container.appendChild(
          makePanel(rg0.label, rg0.latex_name, `games/${rg0.label}-clean.svg`)
        );
      }
      container.appendChild(
        makePanel(g.label, g.latex_name, `games/${g.label}.svg`)
      );
      const rg1 = findGame(g.related_games[1]);
      if (rg1) {
        container.appendChild(
          makePanel(rg1.label, rg1.latex_name, `games/${rg1.label}-clean.svg`)
        );
      }
    }
  } else if (idx > 0 && !g.reduction) {
    // Regular game transition: show previous non-reduction game with removed
    // highlights alongside the current highlighted game.
    let prev = null;
    for (let j = idx - 1; j >= 0; j--) {
      if (!games[j].reduction) { prev = games[j]; break; }
    }
    if (prev) {
      container.appendChild(
        makePanel(prev.label, prev.latex_name, `games/${prev.label}-removed.svg`)
      );
    }
    container.appendChild(
      makePanel(g.label, g.latex_name, `games/${g.label}.svg`)
    );
  } else {
    // First game or reduction with no related_games: show alone
    container.appendChild(
      makePanel(g.label, g.latex_name, `games/${g.label}.svg`)
    );
  }

  // Update commentary (rendered as SVG image)
  const box = document.getElementById('commentary-box');
  if (g.has_commentary) {
    const img = new Image();
    img.alt = g.label + ' commentary';
    img.src = `games/${g.label}_commentary.svg`;
    box.innerHTML = '';
    box.appendChild(img);
  } else {
    box.innerHTML = '';
  }

  // Re-typeset MathJax
  if (window.MathJax && MathJax.typesetPromise) {
    MathJax.typesetPromise([
      document.getElementById('game-title'),
      document.getElementById('game-subtitle'),
      document.getElementById('game-svg-container'),
      document.getElementById('nav'),
    ]).catch(console.error);
  }

  // Update buttons (Prev is never disabled since G0 can go back to overview)
  document.getElementById('btn-prev').disabled = false;
  document.getElementById('btn-next').disabled = (idx === games.length - 1);
}

function navigate(delta) {
  if (currentIndex === -1) {
    // From overview, Next goes to first game
    if (delta > 0) showGame(0);
    return;
  }
  if (currentIndex === 0 && delta < 0) {
    showOverview();
    return;
  }
  showGame(currentIndex + delta);
}

function toggleHelp() {
  document.getElementById('help-overlay').classList.toggle('visible');
}

function toggleNav() {
  const nav = document.getElementById('nav');
  const backdrop = document.getElementById('nav-backdrop');
  const isOpen = nav.classList.toggle('open');
  backdrop.classList.toggle('visible', isOpen);
}

function closeNav() {
  document.getElementById('nav').classList.remove('open');
  document.getElementById('nav-backdrop').classList.remove('visible');
}

// --- Print support ---
function renderAllForPrint() {
  const pv = document.getElementById('print-view');
  pv.innerHTML = '';

  const findGame = (label) => games.find(x => x.label === label);
  const nonRedGames = games.filter(g => !g.reduction);

  games.forEach((g, idx) => {
    const section = document.createElement('div');
    section.className = 'print-game';

    const heading = document.createElement('h2');
    heading.className = 'print-game-title';
    heading.textContent = `$${g.latex_name}$`;
    section.appendChild(heading);

    if (g.description) {
      const desc = document.createElement('p');
      desc.className = 'print-game-desc';
      desc.textContent = g.description;
      section.appendChild(desc);
    }

    // Build panels matching the interactive view
    const panels = document.createElement('div');
    panels.className = 'print-panels';

    if (g.reduction && g.related_games && g.related_games.length > 0) {
      if (g.related_games.length === 1) {
        const rg = findGame(g.related_games[0]);
        if (rg) panels.appendChild(makePrintPanel(rg.label, rg.latex_name, `games/${rg.label}-clean.svg`));
        panels.appendChild(makePrintPanel(g.label, g.latex_name, `games/${g.label}.svg`));
      } else {
        const rg0 = findGame(g.related_games[0]);
        if (rg0) panels.appendChild(makePrintPanel(rg0.label, rg0.latex_name, `games/${rg0.label}-clean.svg`));
        panels.appendChild(makePrintPanel(g.label, g.latex_name, `games/${g.label}.svg`));
        const rg1 = findGame(g.related_games[1]);
        if (rg1) panels.appendChild(makePrintPanel(rg1.label, rg1.latex_name, `games/${rg1.label}-clean.svg`));
      }
    } else if (idx > 0 && !g.reduction) {
      let prev = null;
      for (let j = idx - 1; j >= 0; j--) {
        if (!games[j].reduction) { prev = games[j]; break; }
      }
      if (prev) panels.appendChild(makePrintPanel(prev.label, prev.latex_name, `games/${prev.label}-removed.svg`));
      panels.appendChild(makePrintPanel(g.label, g.latex_name, `games/${g.label}.svg`));
    } else {
      panels.appendChild(makePrintPanel(g.label, g.latex_name, `games/${g.label}.svg`));
    }

    section.appendChild(panels);

    if (g.has_commentary) {
      const cbox = document.createElement('div');
      cbox.className = 'print-commentary';
      const cimg = new Image();
      cimg.alt = g.label + ' commentary';
      cimg.src = `games/${g.label}_commentary.svg`;
      cbox.appendChild(cimg);
      section.appendChild(cbox);
    }

    pv.appendChild(section);
  });

  // Typeset MathJax in print view
  if (window.MathJax && MathJax.typesetPromise) {
    MathJax.typesetPromise([pv]).catch(console.error);
  }
}

function makePrintPanel(label, latexName, svgSrc) {
  const panel = document.createElement('div');
  panel.className = 'print-panel';
  const header = document.createElement('div');
  header.className = 'print-panel-header';
  header.textContent = `$${latexName}$`;
  panel.appendChild(header);
  const img = new Image();
  img.alt = label;
  img.src = svgSrc;
  panel.appendChild(img);
  return panel;
}

function restoreFromPrint() {
  document.getElementById('print-view').innerHTML = '';
}

window.addEventListener('beforeprint', renderAllForPrint);
window.addEventListener('afterprint', restoreFromPrint);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.getElementById('help-overlay').classList.remove('visible');
    return;
  }
  if (e.key === '?') { toggleHelp(); return; }
  if (e.key === 'Home') { showOverview(); return; }
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') navigate(-1);
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') navigate(+1);
  if (e.key === '+' || e.key === '=') adjustZoom(+0.1);
  if (e.key === '-') adjustZoom(-0.1);
});

window.addEventListener('hashchange', () => {
  const hash = window.location.hash.slice(1);
  if (!hash || hash === 'overview') {
    if (currentIndex !== -1) showOverview();
  } else {
    const idx = games.findIndex(g => g.label === hash);
    if (idx >= 0 && idx !== currentIndex) showGame(idx);
  }
});
