/* =============================================
   app.js — GitHub Portfolio Reviewer Frontend
   ============================================= */

const API = '';  // empty = same origin

/* ──── Theme Toggle ──── */
const themeToggleBtn = document.getElementById('theme-toggle');
const htmlEl = document.documentElement;

const ICONS = { dark: '🌙', light: '☀️' };

function applyTheme(theme) {
  htmlEl.setAttribute('data-theme', theme);
  themeToggleBtn.textContent = ICONS[theme === 'dark' ? 'dark' : 'light'];
  localStorage.setItem('portfolio-theme', theme);
}

function toggleTheme() {
  const current = htmlEl.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';

  // Ripple animation
  themeToggleBtn.classList.add('ripple');
  setTimeout(() => themeToggleBtn.classList.remove('ripple'), 450);

  applyTheme(next);
}

// Apply saved preference immediately (before paint)
(function() {
  const saved = localStorage.getItem('portfolio-theme') || 'dark';
  applyTheme(saved);
})();

themeToggleBtn.addEventListener('click', toggleTheme);


const usernameInput    = document.getElementById('username-input');
const githubTokenInput = document.getElementById('github-token-input');
const geminiKeyInput   = document.getElementById('gemini-key-input');
const scanBtn          = document.getElementById('scan-btn');
const advancedToggle   = document.getElementById('advanced-toggle');
const advancedOptions  = document.getElementById('advanced-options');
const errorBanner      = document.getElementById('error-banner');
const errorMsg         = document.getElementById('error-msg');

const loadingSection  = document.getElementById('loading-section');
const resultsSection  = document.getElementById('results-section');
const historySection  = document.getElementById('history-section');

/* Profile */
const profileAvatar   = document.getElementById('profile-avatar');
const profileName     = document.getElementById('profile-name');
const profileUsername = document.getElementById('profile-username');
const profileBio      = document.getElementById('profile-bio');
const statRepos       = document.getElementById('stat-repos');
const statFollowers   = document.getElementById('stat-followers');
const statFollowing   = document.getElementById('stat-following');
const aiLabel         = document.getElementById('ai-label');

/* Score */
const ringFg          = document.getElementById('ring-fg');
const scoreValue      = document.getElementById('score-value');
const scoreBadge      = document.getElementById('score-badge');

/* Content areas */
const summaryText        = document.getElementById('summary-text');
const improvementList    = document.getElementById('improvement-list');
const repoGrid           = document.getElementById('repo-grid');
const projectCards       = document.getElementById('project-cards');
const historyGrid        = document.getElementById('history-grid');

/* README Modal */
const readmeModal        = document.getElementById('readme-modal');
const modalRepoName      = document.getElementById('modal-repo-name');
const readmeContent      = document.getElementById('readme-content');
const readmeGenerating   = document.getElementById('readme-generating');
const customInstructions = document.getElementById('custom-instructions');
const copyBtn            = document.getElementById('copy-btn');
const regenBtn           = document.getElementById('regen-btn');
const closeModalBtn      = document.getElementById('close-modal');

/* Toast */
const toast = document.getElementById('toast');

/* State */
let currentUser  = '';
let currentRepo  = '';
let currentGeminiKey = '';

/* ──── Language colour map ──── */
const langColors = {
  Python: '#3572A5', JavaScript: '#f1e05a', TypeScript: '#3178c6',
  HTML: '#e34c26', CSS: '#563d7c', Java: '#b07219', Go: '#00ADD8',
  Rust: '#dea584', Ruby: '#701516', PHP: '#4F5D95', Swift: '#F05138',
  'C#': '#178600', 'C++': '#f34b7d', C: '#555555', Kotlin: '#A97BFF',
  Dart: '#00B4AB', Shell: '#89e051', Vue: '#41b883', Svelte: '#ff3e00',
};

/* ──── Helpers ──── */
function showToast(msg, emoji = '✅') {
  toast.innerHTML = `<span>${emoji}</span> ${msg}`;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3000);
}

function setError(msg) {
  errorMsg.textContent = msg;
  errorBanner.classList.add('visible');
}

function clearError() {
  errorBanner.classList.remove('visible');
}

function setLoading(on) {
  loadingSection.classList.toggle('visible', on);
  if (on) {
    resultsSection.classList.remove('visible');
    historySection.style.display = 'none';
  }
}

function animateScore(score) {
  const circumference = 283;
  const offset = circumference - (score / 100) * circumference;
  let color;
  if (score >= 80)      { color = '#22c55e'; scoreBadge.className = 'score-badge badge-excellent'; scoreBadge.textContent = 'Excellent'; }
  else if (score >= 60) { color = '#06b6d4'; scoreBadge.className = 'score-badge badge-good'; scoreBadge.textContent = 'Good'; }
  else if (score >= 40) { color = '#f59e0b'; scoreBadge.className = 'score-badge badge-average'; scoreBadge.textContent = 'Average'; }
  else                  { color = '#ef4444'; scoreBadge.className = 'score-badge badge-poor'; scoreBadge.textContent = 'Needs Work'; }

  ringFg.style.stroke = color;
  scoreValue.style.color = color;

  // animate counter
  let cur = 0;
  const step = Math.ceil(score / 50);
  const timer = setInterval(() => {
    cur = Math.min(cur + step, score);
    scoreValue.textContent = cur;
    if (cur >= score) clearInterval(timer);
  }, 30);

  // animate ring after small delay
  setTimeout(() => {
    ringFg.style.strokeDashoffset = offset;
  }, 100);
}

function severityClass(sev) {
  if (!sev) return 'sev-low';
  const s = sev.toLowerCase();
  if (s === 'high')   return 'sev-high';
  if (s === 'medium') return 'sev-medium';
  return 'sev-low';
}

function difficultyClass(diff) {
  if (!diff) return 'diff-medium';
  const d = diff.toLowerCase();
  if (d.includes('beginner')) return 'diff-beginner';
  if (d.includes('hard') || d.includes('advanced')) return 'diff-advanced';
  return 'diff-medium';
}

/* ──── Render Improvements ──── */
function renderImprovements(items) {
  if (!items || items.length === 0) {
    improvementList.innerHTML = '<div class="empty-state"><div class="empty-icon">🎉</div>No issues found — amazing portfolio!</div>';
    return;
  }
  improvementList.innerHTML = items.map(item => `
    <div class="improvement-item">
      <div class="improvement-header">
        <span class="severity-dot ${severityClass(item.severity)}"></span>
        <span class="improvement-title">${escHtml(item.title)}</span>
        <span class="category-tag">${escHtml(item.category || '')}</span>
      </div>
      <div class="improvement-desc">${escHtml(item.description)}</div>
    </div>
  `).join('');
}

/* ──── Render Repositories ──── */
function renderRepos(repos, username) {
  if (!repos || repos.length === 0) {
    repoGrid.innerHTML = '<div class="empty-state"><div class="empty-icon">📂</div>No repositories found.</div>';
    return;
  }

  repoGrid.innerHTML = repos.map(repo => {
    const lang = repo.language || 'Unknown';
    const langColor = langColors[lang] || '#64748b';
    const stars = repo.stars || 0;
    const forks = repo.forks || 0;

    const checks = [
      { key: 'has_readme',      label: 'README' },
      { key: 'has_license',     label: 'License' },
      { key: 'has_gitignore',   label: '.gitignore' },
      { key: 'has_tests',       label: 'Tests' },
      { key: 'has_ci',          label: 'CI/CD' },
      { key: 'has_docker',      label: 'Docker' },
    ];

    const chipsHtml = checks.map(c =>
      `<span class="check-chip ${repo[c.key] ? 'chip-ok' : 'chip-err'}">${repo[c.key] ? '✓' : '✗'} ${c.label}</span>`
    ).join('');

    return `
      <div class="repo-card">
        <a class="repo-name" href="${escHtml(repo.html_url)}" target="_blank" rel="noopener" onclick="event.stopPropagation()">
          ${escHtml(repo.name)}
        </a>
        <div class="repo-desc">${escHtml(repo.description || 'No description provided.')}</div>
        <div class="repo-meta">
          <span class="lang-dot" style="background:${langColor}"></span>
          <span>${escHtml(lang)}</span>
          <span>⭐ ${stars}</span>
          <span>🍴 ${forks}</span>
        </div>
        <div class="repo-checks">${chipsHtml}</div>
        <button class="readme-btn" onclick="openReadmeModal('${escHtml(username)}', '${escHtml(repo.name)}')">
          📝 Generate README
        </button>
      </div>
    `;
  }).join('');
}

/* ──── Render Recommended Projects ──── */
function renderProjects(projects) {
  if (!projects || projects.length === 0) {
    projectCards.innerHTML = '<div class="empty-state"><div class="empty-icon">💡</div>No project recommendations available.</div>';
    return;
  }

  projectCards.innerHTML = projects.map(p => {
    const techs = (p.tech_stack || '').split(',').map(t => t.trim()).filter(Boolean);
    const tasks  = p.tasks || [];
    const diff   = p.difficulty || 'Medium';

    return `
      <div class="project-card">
        <div class="project-header">
          <div class="project-title">${escHtml(p.title)}</div>
          <span class="difficulty-badge ${difficultyClass(diff)}">${escHtml(diff)}</span>
        </div>
        <div class="project-desc">${escHtml(p.description)}</div>
        <div class="tech-stack">
          ${techs.map(t => `<span class="tech-chip">${escHtml(t)}</span>`).join('')}
        </div>
        ${tasks.length ? `
          <div class="project-tasks">
            <div class="project-tasks-title">Implementation Steps</div>
            <ul class="task-list">
              ${tasks.map(t => `<li>${escHtml(t)}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    `;
  }).join('');
}

/* ──── Render History ──── */
function renderHistory(items) {
  if (!items || items.length === 0) {
    historyGrid.innerHTML = '<div class="empty-state"><div class="empty-icon">🕐</div>No scans yet. Search a GitHub username above.</div>';
    return;
  }

  historyGrid.innerHTML = items.map(item => {
    const score = item.score || 0;
    let scoreColor = score >= 80 ? '#22c55e' : score >= 60 ? '#06b6d4' : score >= 40 ? '#f59e0b' : '#ef4444';
    const initial  = (item.name || item.username || '?')[0].toUpperCase();
    const avatarHtml = item.avatar_url
      ? `<img class="history-avatar" src="${escHtml(item.avatar_url)}" alt="${escHtml(item.username)}" loading="lazy">`
      : `<div class="history-avatar-fallback">${escHtml(initial)}</div>`;

    return `
      <div class="history-item" onclick="loadCached('${escHtml(item.username)}')">
        ${avatarHtml}
        <div class="history-info">
          <div class="history-name">${escHtml(item.name || item.username)}</div>
          <div class="history-meta">
            <span>@${escHtml(item.username)}</span>
            <span>·</span>
            <span>${item.repo_count} repos</span>
          </div>
        </div>
        <div class="history-score" style="color:${scoreColor}">${score}</div>
      </div>
    `;
  }).join('');
}

/* ──── Display Full Results ──── */
function displayResults(data) {
  // Profile header
  profileAvatar.src = data.avatar_url || '';
  profileAvatar.alt = data.username;
  profileName.textContent = data.name || data.username;
  profileUsername.textContent = `@${data.username}`;
  profileBio.textContent = data.bio || 'No bio provided.';
  statRepos.textContent = data.public_repos || 0;
  statFollowers.textContent = data.followers || 0;
  statFollowing.textContent = data.following || 0;

  const isAI = data.analysis?.is_ai_generated;
  aiLabel.style.display = isAI ? 'inline-flex' : 'none';

  // Score
  animateScore(data.analysis?.score || 0);

  // Summary
  summaryText.textContent = data.analysis?.summary || 'No summary available.';

  // Improvements
  renderImprovements(data.analysis?.improvements || []);

  // Repos
  renderRepos(data.repositories || [], data.username);

  // Projects
  renderProjects(data.analysis?.recommended_projects || []);

  // Show results
  setLoading(false);
  resultsSection.classList.add('visible');
  resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* ──── Scan Portfolio ──── */
async function scanPortfolio() {
  const username = usernameInput.value.trim();
  if (!username) { setError('Please enter a GitHub username.'); return; }

  clearError();
  currentUser = username;
  currentGeminiKey = geminiKeyInput.value.trim();

  // Animate loading steps
  setLoading(true);
  animateLoadingSteps();

  try {
    const body = {
      username,
      github_token: githubTokenInput.value.trim() || null,
      gemini_api_key: currentGeminiKey || null
    };

    const res = await fetch(`${API}/api/portfolio/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    displayResults(data);
    loadHistory();

  } catch (err) {
    setLoading(false);
    setError(err.message || 'An unexpected error occurred. Please try again.');
  }
}

/* ──── Load Cached Profile ──── */
async function loadCached(username) {
  clearError();
  currentUser = username;
  usernameInput.value = username;
  setLoading(true);
  animateLoadingSteps();

  try {
    const res = await fetch(`${API}/api/portfolio/${encodeURIComponent(username)}`);
    if (!res.ok) {
      // Not cached — trigger fresh scan
      await scanPortfolio();
      return;
    }
    const data = await res.json();
    displayResults(data);
  } catch (err) {
    setLoading(false);
    setError(err.message || 'Failed to load cached data.');
  }
}

/* ──── Load History ──── */
async function loadHistory() {
  try {
    const res = await fetch(`${API}/api/history`);
    if (!res.ok) return;
    const data = await res.json();
    renderHistory(data);
    historySection.style.display = 'block';
  } catch {}
}

/* ──── README Modal ──── */
function openReadmeModal(username, repoName) {
  currentUser = username;
  currentRepo = repoName;
  modalRepoName.textContent = repoName;
  customInstructions.value = '';
  readmeContent.textContent = '';
  readmeContent.style.display = 'none';
  readmeGenerating.style.display = 'flex';
  readmeModal.classList.add('open');
  generateReadme();
}

async function generateReadme() {
  readmeGenerating.style.display = 'flex';
  readmeContent.style.display = 'none';

  try {
    const body = {
      username: currentUser,
      repo_name: currentRepo,
      gemini_api_key: currentGeminiKey || null,
      custom_instructions: customInstructions.value.trim() || null
    };

    const res = await fetch(`${API}/api/projects/readme`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    readmeContent.textContent = data.content;
    readmeGenerating.style.display = 'none';
    readmeContent.style.display = 'block';
    showToast('README generated!', '📝');

  } catch (err) {
    readmeGenerating.style.display = 'none';
    readmeContent.textContent = `Error: ${err.message}`;
    readmeContent.style.display = 'block';
  }
}

function closeModal() {
  readmeModal.classList.remove('open');
}

async function copyReadme() {
  const text = readmeContent.textContent;
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!', '📋');
  } catch {
    showToast('Copy failed — please select and copy manually.', '⚠️');
  }
}

/* ──── Loading Step Animator ──── */
function animateLoadingSteps() {
  const steps = document.querySelectorAll('.step-item');
  steps.forEach(s => { s.className = 'step-item'; });
  let idx = 0;
  const advance = () => {
    if (idx < steps.length) {
      if (idx > 0) steps[idx-1].className = 'step-item done';
      steps[idx].className = 'step-item active';
      idx++;
      setTimeout(advance, 1400);
    }
  };
  advance();
}

/* ──── Escape HTML ──── */
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* ──── Event Listeners ──── */
scanBtn.addEventListener('click', scanPortfolio);

usernameInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') scanPortfolio();
});

advancedToggle.addEventListener('click', () => {
  advancedOptions.classList.toggle('open');
  const icon = advancedToggle.querySelector('.toggle-icon');
  icon.textContent = advancedOptions.classList.contains('open') ? '▲' : '▼';
});

closeModalBtn.addEventListener('click', closeModal);
copyBtn.addEventListener('click', copyReadme);
regenBtn.addEventListener('click', generateReadme);

readmeModal.addEventListener('click', (e) => {
  if (e.target === readmeModal) closeModal();
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

/* ──── Init ──── */
(async function init() {
  await loadHistory();
})();
