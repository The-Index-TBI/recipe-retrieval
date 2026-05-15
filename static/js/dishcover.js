/* ── Mock Data ─────────────────────────────────────────────────────
 * Schema mirrors the real OpenSearch response:
 *   _score      → raw BM25 relevance float (e.g. 4.99)
 *   ingredients → full strings with quantities
 *   directions  → array of instruction steps
 *   ner         → clean extracted ingredient names
 *   link        → original recipe URL
 *   source      → dataset source label
 * ────────────────────────────────────────────────────────────────── */
const RECIPES = [
  {
    id: "bqQoJ54BHiJNC1YaaKA5",
    title: "Lo-Cal Tuna And Fruit Sandwich",
    _score: 4.99,
    ingredients: [
      "1 (7 oz.) can water packed tuna, drained",
      "3 Tbsp. lo-cal spicy sweet French dressing",
      "2 Tbsp. chopped celery",
      "4 slices lite processed cheese",
      "1 (8 oz.) can sliced pineapple in natural juices",
      "2 sandwich buns, split and toasted",
      "paprika",
    ],
    directions: [
      "In a small bowl, mix first 3 ingredients.",
      "Place equal amounts on bun halves.",
      "Top with cheese and pineapple slice.",
      "Broil until cheese melts.",
      "Sprinkle with paprika.",
    ],
    link: "www.cookbooks.com/Recipe-Details.aspx?id=759777",
    source: "Gathered",
    ner: ["tuna", "French dressing", "celery", "cheese", "pineapple", "sandwich buns", "paprika"],
  },
  {
    id: "EqQoJ54BHiJNC1YaZ5",
    title: "Sweet And Sour Chicken Stir-Fry",
    _score: 4.53,
    ingredients: [
      "1 (8 oz.) can pineapple chunks in own juice",
      "1 Tbsp. vegetable oil",
      "2 half boneless chicken breasts, skinned and cubed",
      "1/4 to 1/2 tsp. red pepper flakes",
      "1 (16 oz.) can cut green beans, drained",
      "3/4 c. sweet and sour sauce",
    ],
    directions: [
      "Drain pineapple; reserve 1/4 cup juice.",
      "In a wok or skillet, heat oil over medium heat.",
      "Add chicken; cook 5 minutes, stirring occasionally.",
      "Season with salt and pepper, if desired.",
      "Stir in reserved juice and red pepper.",
      "Add green beans, pineapple and sauce. Cover and cook until heated through.",
      "Serve over hot cooked rice. Makes 4 servings.",
    ],
    link: "www.cookbooks.com/Recipe-Details.aspx?id=540440",
    source: "Gathered",
    ner: ["pineapple", "vegetable oil", "chicken breasts", "red pepper", "green beans", "sweet and sour sauce"],
  },
  {
    id: "VKQoJ54BHiJNC1Yaaamo",
    title: "Spicy Taters",
    _score: 4.39,
    ingredients: [
      "6 medium potatoes",
      "vegetable oil",
      "Mrs. Dash extra spicy seasoning",
    ],
    directions: [
      "Wash and cut potatoes into wedges, leaving skins on.",
      "In a casserole dish, pour just enough vegetable oil to coat bottom.",
      "Put the potatoes in the casserole dish and sprinkle with Mrs. Dash extra spicy seasoning.",
      "Cover dish with wax paper and microwave on High for 20 minutes.",
      "Allow to set for 5 minutes before serving.",
    ],
    link: "www.cookbooks.com/Recipe-Details.aspx?id=510630",
    source: "Gathered",
    ner: ["potatoes", "vegetable oil"],
  },
  {
    id: "mkRpK54BHiJNC1Ya8bQ2",
    title: "Classic Italian Minestrone",
    _score: 3.87,
    ingredients: [
      "2 Tbsp. olive oil",
      "1 medium onion, chopped",
      "3 cloves garlic, minced",
      "2 medium carrots, diced",
      "2 stalks celery, diced",
      "1 (14 oz.) can diced tomatoes",
      "1 (15 oz.) can cannellini beans, drained",
      "4 c. vegetable broth",
      "1 c. ditalini pasta",
      "1 tsp. dried oregano, salt and pepper to taste",
    ],
    directions: [
      "Heat olive oil in a large pot over medium heat.",
      "Saute onion and garlic until softened, about 3 minutes.",
      "Add carrots and celery; cook 5 minutes.",
      "Stir in tomatoes, beans, and broth. Bring to a boil, then simmer 15 minutes.",
      "Add pasta and cook until tender, about 8 minutes.",
      "Season with oregano, salt, and pepper. Serve hot.",
    ],
    link: "www.cookbooks.com/Recipe-Details.aspx?id=123456",
    source: "Gathered",
    ner: ["olive oil", "onion", "garlic", "carrots", "celery", "tomatoes", "cannellini beans", "vegetable broth", "pasta", "oregano"],
  },
  {
    id: "nkSpL54BHiJNC1Ya9cR3",
    title: "Garlic Butter Shrimp Scampi",
    _score: 3.54,
    ingredients: [
      "1 lb. large shrimp, peeled and deveined",
      "4 Tbsp. unsalted butter",
      "4 cloves garlic, minced",
      "1/4 c. dry white wine",
      "juice of 1 lemon",
      "1/4 tsp. red pepper flakes",
      "2 Tbsp. fresh parsley, chopped",
      "8 oz. linguine, cooked",
    ],
    directions: [
      "Cook linguine according to package directions; drain and set aside.",
      "Melt butter in a large skillet over medium-high heat.",
      "Add garlic and red pepper flakes; saute 30 seconds.",
      "Add shrimp and cook 2 minutes per side until pink.",
      "Pour in white wine and lemon juice; simmer 1 minute.",
      "Toss with pasta and garnish with fresh parsley.",
    ],
    link: "www.cookbooks.com/Recipe-Details.aspx?id=234567",
    source: "Gathered",
    ner: ["shrimp", "butter", "garlic", "white wine", "lemon", "red pepper flakes", "parsley", "linguine"],
  },
  {
    id: "okTqM54BHiJNC1Ya0dS4",
    title: "Honey Mustard Glazed Salmon",
    _score: 3.21,
    ingredients: [
      "4 salmon fillets (6 oz. each)",
      "3 Tbsp. Dijon mustard",
      "2 Tbsp. honey",
      "1 Tbsp. olive oil",
      "1 tsp. garlic powder",
      "salt and black pepper to taste",
      "fresh dill for garnish",
    ],
    directions: [
      "Preheat oven to 400°F. Line a baking sheet with foil.",
      "Whisk together mustard, honey, olive oil, and garlic powder.",
      "Season salmon with salt and pepper; place on prepared baking sheet.",
      "Brush salmon generously with the honey mustard glaze.",
      "Bake 12-15 minutes until salmon flakes easily with a fork.",
      "Garnish with fresh dill and serve immediately.",
    ],
    link: "www.cookbooks.com/Recipe-Details.aspx?id=345678",
    source: "Gathered",
    ner: ["salmon", "Dijon mustard", "honey", "olive oil", "garlic powder", "dill"],
  },
];

/* ── State ──────────────────────────────────────────────────────── */
let activeQuery  = '';
let activeFilter = 'All';

/* ── DOM refs ────────────────────────────────────────────────────── */
const searchInput = document.getElementById('search-input');
const searchBtn   = document.getElementById('search-btn');
const filterBar   = document.getElementById('filter-bar');
const grid        = document.getElementById('recipe-grid');
const metaEl      = document.getElementById('results-meta');
const emptyEl     = document.getElementById('empty-state');

/* ── Helpers ─────────────────────────────────────────────────────── */
function extractDomain(link) {
  try {
    const url = new URL(link.startsWith('http') ? link : 'https://' + link);
    return url.hostname.replace('www.', '');
  } catch {
    return link.split('/')[0];
  }
}

function applyFilter(recipes) {
  switch (activeFilter) {
    case 'Few Ingredients': return recipes.filter(r => r.ner.length <= 4);
    case 'Simple':          return recipes.filter(r => r.directions.length <= 4);
    case 'Many Steps':      return recipes.filter(r => r.directions.length > 5);
    default:                return recipes;
  }
}

/* ── Card builder ────────────────────────────────────────────────── */
function buildCard(recipe) {
  const visibleNer  = recipe.ner.slice(0, 5);
  const moreNer     = recipe.ner.length - 5;

  const visibleIng  = recipe.ingredients.slice(0, 3);
  const moreIng     = recipe.ingredients.length - 3;

  const firstStep   = recipe.directions[0] || '';
  const stepsTotal  = recipe.directions.length;
  const domain      = extractDomain(recipe.link);
  const fullLink    = recipe.link.startsWith('http') ? recipe.link : 'https://' + recipe.link;

  const nerHtml = visibleNer.map(n => `<span class="ner-chip">${n}</span>`).join('')
    + (moreNer > 0 ? `<span class="ner-more">+${moreNer}</span>` : '');

  const ingHtml = visibleIng.map(i =>
    `<li class="ingredient-item">${i}</li>`
  ).join('') + (moreIng > 0 ? `<li class="ingredient-more">+${moreIng} more</li>` : '');

  return `
    <article class="card" id="card-${recipe.id}">
      <div class="card-header">
        <h2 class="card-title">${recipe.title}</h2>
        <div class="score-badge">
          <span class="score-value">${recipe._score.toFixed(2)}</span>
          <span class="score-label">score</span>
        </div>
      </div>

      <div class="ner-tags">${nerHtml}</div>

      <div class="card-divider"></div>

      <ul class="ingredient-list">${ingHtml}</ul>

      <div class="card-divider"></div>

      <div>
        <p class="directions-preview">${firstStep}</p>
        <span class="steps-count">${stepsTotal} step${stepsTotal !== 1 ? 's' : ''} total</span>
      </div>

      <div class="card-footer">
        <a href="${fullLink}" class="card-link" target="_blank" rel="noopener">↗ ${domain}</a>
        <span class="card-source">${recipe.source}</span>
      </div>
    </article>`;
}

/* ── Render ──────────────────────────────────────────────────────── */
function render() {
  const filtered = applyFilter(RECIPES);

  // Meta line
  if (activeQuery) {
    metaEl.innerHTML = `Showing ${filtered.length} result${filtered.length !== 1 ? 's' : ''} for &mdash; <strong>${activeQuery}</strong>`;
  } else {
    metaEl.innerHTML = `Showing ${filtered.length} recipe${filtered.length !== 1 ? 's' : ''}`
      + (activeFilter !== 'All' ? ` &mdash; <strong>${activeFilter}</strong>` : '');
  }

  if (filtered.length === 0) {
    grid.innerHTML         = '';
    emptyEl.style.display  = 'flex';
  } else {
    emptyEl.style.display  = 'none';
    grid.innerHTML         = filtered.map(buildCard).join('');
  }
}

/* ── Events ──────────────────────────────────────────────────────── */
function doSearch() {
  activeQuery = searchInput.value.trim();
  render();
}

searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

filterBar.addEventListener('click', e => {
  const chip = e.target.closest('.chip');
  if (!chip) return;
  filterBar.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeFilter = chip.dataset.filter;
  render();
});

/* ── Init ────────────────────────────────────────────────────────── */
render();
