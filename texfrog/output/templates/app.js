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
    li.onclick = () => showGame(i);
    list.appendChild(li);
  });
  // Navigate to hash or first game
  const hash = window.location.hash.slice(1);
  const idx = hash ? games.findIndex(g => g.label === hash) : -1;
  showGame(idx >= 0 ? idx : 0);
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

function showGame(idx) {
  if (idx < 0 || idx >= games.length) return;
  currentIndex = idx;

  const g = games[idx];
  window.location.hash = g.label;

  // Update nav highlight
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
  if (window.MathJax) {
    MathJax.typesetPromise([
      document.getElementById('game-title'),
      document.getElementById('game-subtitle'),
      document.getElementById('game-svg-container'),
      document.getElementById('nav'),
    ]).catch(console.error);
  }

  // Update buttons
  document.getElementById('btn-prev').disabled = (idx === 0);
  document.getElementById('btn-next').disabled = (idx === games.length - 1);
}

function navigate(delta) {
  showGame(currentIndex + delta);
}

function toggleHelp() {
  document.getElementById('help-overlay').classList.toggle('visible');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.getElementById('help-overlay').classList.remove('visible');
    return;
  }
  if (e.key === '?') { toggleHelp(); return; }
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') navigate(-1);
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') navigate(+1);
  if (e.key === '+' || e.key === '=') adjustZoom(+0.1);
  if (e.key === '-') adjustZoom(-0.1);
});
