const SEARCH_ENDPOINT = '/api/search/';
const DEFAULT_RESULT_SIZE = 12;

let activeQuery = '';
let activeFilter = 'All';
let recipes = [];
let isLoading = false;
let currentAbortController = null;
let activeRequestId = 0;
let searchError = '';
let currentPage = 1;
let totalResults = 0;
let totalRelation = 'eq';

const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const includeInput = document.getElementById('include-input');
const excludeInput = document.getElementById('exclude-input');
const filterBar = document.getElementById('filter-bar');
const grid = document.getElementById('recipe-grid');
const metaEl = document.getElementById('results-meta');
const emptyEl = document.getElementById('empty-state');
const paginationEl = document.getElementById('pagination');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageStatusEl = document.getElementById('page-status');

function toArray(value) {
  if (Array.isArray(value)) return value;
  if (value === null || value === undefined || value === '') return [];
  return [String(value)];
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function normalizeRecipe(raw) {
  return {
    id: raw.id ?? '',
    title: raw.title ?? 'Untitled recipe',
    score: Number(raw.score ?? raw._score ?? 0),
    ingredients: toArray(raw.ingredients),
    directions: toArray(raw.directions),
    link: raw.link ?? '',
    source: raw.source ?? 'RecipeNLG',
    ner: toArray(raw.ner),
  };
}

function extractDomain(link) {
  if (!link) return 'source';

  try {
    const url = new URL(toSourceUrl(link));
    return url.hostname.replace('www.', '');
  } catch {
    return link.split('/')[0] || 'source';
  }
}

function toSourceUrl(link) {
  if (!link) return '';
  if (link.startsWith('http://') || link.startsWith('https://')) return link;

  const host = link.split('/')[0].replace('www.', '');
  const protocol = host === 'cookbooks.com' ? 'http' : 'https';
  return `${protocol}://${link}`;
}

function applyFilter(items) {
  switch (activeFilter) {
    case 'Few Ingredients':
      return items.filter(recipe => recipe.ner.length > 0 && recipe.ner.length <= 4);
    case 'Simple':
      return items.filter(recipe => recipe.directions.length > 0 && recipe.directions.length <= 4);
    case 'Many Steps':
      return items.filter(recipe => recipe.directions.length > 5);
    default:
      return items;
  }
}

function setLoadingState(nextIsLoading) {
  isLoading = nextIsLoading;
  searchBtn.disabled = isLoading;
  searchBtn.textContent = isLoading ? 'Searching' : 'Search';
}

function setEmptyCopy(title, subtitle) {
  const paragraphs = emptyEl.querySelectorAll('p');
  if (paragraphs[0]) paragraphs[0].textContent = title;
  if (paragraphs[1]) paragraphs[1].textContent = subtitle;
}

function getIngredientFilters() {
  return {
    include: includeInput.value.trim(),
    exclude: excludeInput.value.trim(),
  };
}

function updatePagination(filteredCount) {
  const hasQuery = Boolean(activeQuery);
  const hasResults = filteredCount > 0;
  paginationEl.style.display = hasQuery && hasResults ? 'flex' : 'none';

  if (!hasQuery || !hasResults) return;

  const seenResults = (currentPage - 1) * DEFAULT_RESULT_SIZE + recipes.length;
  const exactTotalReached = totalRelation === 'eq' && seenResults >= totalResults;
  const shortPageReached = recipes.length < DEFAULT_RESULT_SIZE;
  const hasNextPage = !exactTotalReached && !shortPageReached;

  prevPageBtn.disabled = currentPage <= 1 || isLoading;
  nextPageBtn.disabled = !hasNextPage || isLoading;

  const totalLabel = totalRelation === 'gte' ? `${totalResults}+` : String(totalResults);
  pageStatusEl.textContent = `Page ${currentPage} / ${totalLabel}`;
}

function buildCard(recipe) {
  const visibleNer = recipe.ner.slice(0, 5);
  const moreNer = recipe.ner.length - 5;

  const visibleIngredients = recipe.ingredients.slice(0, 3);
  const moreIngredients = recipe.ingredients.length - 3;

  const firstStep = recipe.directions[0] || 'No directions available in this record.';
  const stepsTotal = recipe.directions.length;
  const domain = extractDomain(recipe.link);
  const hasLink = Boolean(recipe.link);
  const fullLink = toSourceUrl(recipe.link);

  const nerHtml = visibleNer.map(item =>
    `<span class="ner-chip">${escapeHtml(item)}</span>`
  ).join('') + (moreNer > 0 ? `<span class="ner-more">+${moreNer}</span>` : '');

  const ingredientsHtml = visibleIngredients.map(item =>
    `<li class="ingredient-item">${escapeHtml(item)}</li>`
  ).join('') + (moreIngredients > 0 ? `<li class="ingredient-more">+${moreIngredients} more</li>` : '');

  const sourceLink = hasLink
    ? `<a href="${escapeHtml(fullLink)}" class="card-link" target="_blank" rel="noopener">open ${escapeHtml(domain)}</a>`
    : `<span class="card-link">no source link</span>`;

  return `
    <article class="card" id="card-${escapeHtml(recipe.id)}">
      <div class="card-header">
        <h2 class="card-title">${escapeHtml(recipe.title)}</h2>
        <div class="score-badge">
          <span class="score-value">${recipe.score.toFixed(2)}</span>
          <span class="score-label">score</span>
        </div>
      </div>

      <div class="ner-tags">${nerHtml || '<span class="ner-more">No tags</span>'}</div>

      <div class="card-divider"></div>

      <ul class="ingredient-list">${ingredientsHtml || '<li class="ingredient-more">No ingredients available</li>'}</ul>

      <div class="card-divider"></div>

      <div>
        <p class="directions-preview">${escapeHtml(firstStep)}</p>
        <span class="steps-count">${stepsTotal} step${stepsTotal !== 1 ? 's' : ''} total</span>
      </div>

      <div class="card-footer">
        ${sourceLink}
        <span class="card-source">${escapeHtml(recipe.source)}</span>
      </div>
    </article>`;
}

function render() {
  if (isLoading) {
    metaEl.textContent = `Searching recipes for "${activeQuery}"...`;
    grid.innerHTML = '';
    emptyEl.style.display = 'none';
    paginationEl.style.display = 'none';
    return;
  }

  if (searchError) {
    metaEl.textContent = 'Search failed.';
    grid.innerHTML = '';
    setEmptyCopy('Search service is unavailable.', searchError);
    emptyEl.style.display = 'flex';
    paginationEl.style.display = 'none';
    return;
  }

  if (!activeQuery) {
    metaEl.textContent = 'Enter a query to search the RecipeNLG index.';
    grid.innerHTML = '';
    setEmptyCopy('Start with a cooking idea.', 'Try an ingredient, dish name, or natural-language craving.');
    emptyEl.style.display = 'flex';
    paginationEl.style.display = 'none';
    return;
  }

  const filtered = applyFilter(recipes);
  const filters = getIngredientFilters();
  const filterParts = [];
  if (filters.include) filterParts.push(`including <strong>${escapeHtml(filters.include)}</strong>`);
  if (filters.exclude) filterParts.push(`excluding <strong>${escapeHtml(filters.exclude)}</strong>`);

  metaEl.innerHTML = `Showing ${filtered.length} result${filtered.length !== 1 ? 's' : ''} for <strong>${escapeHtml(activeQuery)}</strong>`
    + (filterParts.length > 0 ? `, ${filterParts.join(', ')}` : '')
    + (activeFilter !== 'All' ? ` with <strong>${escapeHtml(activeFilter)}</strong>` : '');

  if (filtered.length === 0) {
    grid.innerHTML = '';
    setEmptyCopy('No recipes found.', 'Try a different query or adjust your filters.');
    emptyEl.style.display = 'flex';
    updatePagination(filtered.length);
    return;
  }

  emptyEl.style.display = 'none';
  grid.innerHTML = filtered.map(buildCard).join('');
  updatePagination(filtered.length);
}

async function searchRecipes(query) {
  if (currentAbortController) {
    currentAbortController.abort();
  }

  const requestId = activeRequestId + 1;
  activeRequestId = requestId;
  currentAbortController = new AbortController();
  const abortController = currentAbortController;
  const filters = getIngredientFilters();
  const params = new URLSearchParams({
    q: query,
    size: String(DEFAULT_RESULT_SIZE),
    page: String(currentPage),
  });
  if (filters.include) params.set('include', filters.include);
  if (filters.exclude) params.set('exclude', filters.exclude);

  searchError = '';
  setLoadingState(true);
  render();

  try {
    const response = await fetch(`${SEARCH_ENDPOINT}?${params.toString()}`, {
      signal: abortController.signal,
      headers: {
        Accept: 'application/json',
      },
    });

    const payload = await response.json();

    if (!response.ok) {
      throw new Error(payload.error || payload.details || 'Search request failed.');
    }

    recipes = toArray(payload.results).map(normalizeRecipe);
    currentPage = Number(payload.page || currentPage);
    totalResults = Number(payload.total || 0);
    totalRelation = payload.total_relation || 'eq';
  } catch (error) {
    if (error.name === 'AbortError') return;

    recipes = [];
    searchError = error.message;
  } finally {
    if (requestId !== activeRequestId) return;

    setLoadingState(false);
    currentAbortController = null;
    render();
  }
}

function doSearch() {
  const query = searchInput.value.trim();

  if (!query) {
    if (currentAbortController) {
      currentAbortController.abort();
      currentAbortController = null;
    }

    activeRequestId += 1;
    activeQuery = '';
    currentPage = 1;
    totalResults = 0;
    totalRelation = 'eq';
    recipes = [];
    searchError = '';
    setLoadingState(false);
    render();
    return;
  }

  activeQuery = query;
  currentPage = 1;
  searchRecipes(query);
}

searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', event => {
  if (event.key === 'Enter') doSearch();
});

[includeInput, excludeInput].forEach(input => {
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') doSearch();
  });
});

filterBar.addEventListener('click', event => {
  const chip = event.target.closest('.chip');
  if (!chip) return;

  filterBar.querySelectorAll('.chip').forEach(item => item.classList.remove('active'));
  chip.classList.add('active');
  activeFilter = chip.dataset.filter;
  render();
});

prevPageBtn.addEventListener('click', () => {
  if (currentPage <= 1 || isLoading || !activeQuery) return;
  currentPage -= 1;
  searchRecipes(activeQuery);
});

nextPageBtn.addEventListener('click', () => {
  if (isLoading || !activeQuery) return;
  currentPage += 1;
  searchRecipes(activeQuery);
});

render();
