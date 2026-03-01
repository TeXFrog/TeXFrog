let currentIndex = 0;
let games = [];

function init(gamesData) {
  games = gamesData;
  const list = document.getElementById('game-list');
  games.forEach((g, i) => {
    const li = document.createElement('li');
    li.innerHTML = `<div class="game-label">$${g.latex_name}$</div>
                    <div class="game-desc">${g.description}</div>`;
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
  header.innerHTML = `$${latexName}$`;
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
  document.getElementById('game-title').innerHTML = `$${g.latex_name}$`;
  document.getElementById('game-subtitle').innerHTML = g.description || '';

  // Build side-by-side display
  const container = document.getElementById('game-svg-container');
  container.innerHTML = '';

  if (idx > 0 && !g.reduction) {
    // Show previous game (with red strikethrough on removed lines) on the left
    const prev = games[idx - 1];
    container.appendChild(
      makePanel(prev.label, prev.latex_name, `games/${prev.label}-removed.svg`)
    );
  }

  // Current game (with highlights) on the right, or alone for first game / reductions
  container.appendChild(
    makePanel(g.label, g.latex_name, `games/${g.label}.svg`)
  );

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

document.addEventListener('keydown', e => {
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') navigate(-1);
  if (e.key === 'ArrowRight' || e.key === 'ArrowDown') navigate(+1);
});
