# Plug-And-Play Frontend Tab Template

Use this template when building a new page tab outside the main thread. It matches the current static frontend structure in `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css`.

## Current Tab Pattern

Every tab has three pieces:

1. A tab button in `frontend/index.html`:

```html
<button class="tab" data-tab="example" type="button">Example</button>
```

2. A matching page section in `frontend/index.html`:

```html
<section id="example" class="page">
  <div class="page-head">
    <div>
      <h2>Example</h2>
      <p>Short page subtitle.</p>
    </div>
    <button id="example-refresh" class="button secondary" type="button">Refresh</button>
  </div>

  <div class="layout-two">
    <section class="panel">
      <h3>Primary Panel</h3>
      <div id="example-primary"></div>
    </section>

    <section class="panel">
      <h3>Secondary Panel</h3>
      <div id="example-secondary"></div>
    </section>
  </div>
</section>
```

3. JavaScript hooks in `frontend/app.js`:

```js
// Add only the state this tab owns.
const appState = {
  // ...
  example: null,
};

function bindEvents() {
  // Existing bindings...
  $("#example-refresh").addEventListener("click", handleExampleRefresh);
}

function renderAll() {
  // Existing render calls...
  renderExample();
}

function activateTab(tabId) {
  $$(".tab").forEach((button) => button.classList.toggle("active", button.dataset.tab === tabId));
  $$(".page").forEach((page) => page.classList.toggle("active", page.id === tabId));
  if (tabId === "example") renderExample();
}

async function handleExampleRefresh() {
  if (!requirePortfolio()) return;
  try {
    appState.example = await api(`/portfolios/${appState.selectedPortfolioId}/example`);
    renderExample();
    toast("Example updated.");
  } catch (error) {
    toast(error.message, true);
  }
}

function renderExample() {
  if (!appState.portfolio) return;

  const primary = $("#example-primary");
  const secondary = $("#example-secondary");

  if (!appState.example) {
    primary.innerHTML = `<div class="activity-item"><strong>No data</strong><span>Refresh to load this view.</span></div>`;
    secondary.innerHTML = "";
    return;
  }

  renderTable(primary, ["Label", "Value"], appState.example.rows.map((row) => [
    row.label,
    row.value,
  ]));

  secondary.innerHTML = appState.example.summary.map((item) => resultItem(item.label, item.value)).join("");
}
```

## CSS Template

Add tab-specific CSS only when existing primitives are not enough. Prefer `panel`, `layout-two`, `metric-grid`, `table-wrap`, `activity-item`, `result-item`, `bar-list`, and `button`.

```css
.example-grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.example-card {
  background: #fbfcfc;
  border: 1px solid var(--border);
  border-radius: 8px;
  display: grid;
  gap: 6px;
  padding: 12px;
}

@media (max-width: 900px) {
  .example-grid {
    grid-template-columns: 1fr;
  }
}
```

## Backend Route Shape

If the tab needs new backend data, keep route code thin and put calculations in services or quant modules.

```python
@router.get(
    "/portfolios/{portfolio_id}/example",
    response_model=PortfolioExampleResponse,
    tags=["example"],
)
def get_portfolio_example(
    portfolio_id: str,
    current_user: User = Depends(_current_user),
) -> PortfolioExampleResponse:
    portfolio = _get_portfolio_or_404(portfolio_id, current_user)
    return build_portfolio_example(portfolio)
```

Pydantic response example:

```python
class ExampleRow(BaseModel):
    label: str
    value: float


class PortfolioExampleResponse(BaseModel):
    portfolio_id: str
    rows: list[ExampleRow]
    summary: list[ChartPoint]
```

## Rules For Another AI

- Do not put quant math directly in `frontend/app.js` or route functions if it belongs in `app/quant` or `app/api/services.py`.
- Use `api(...)`, `toast(...)`, `requirePortfolio()`, `renderTable(...)`, `renderTableHtml(...)`, `resultItem(...)`, `metricCard(...)`, `money(...)`, `pct(...)`, `fixed(...)`, and `escapeHtml(...)` instead of recreating helpers.
- Match `data-tab` exactly to the page section `id`.
- Put persistent client state under `appState`.
- Add one render function per tab.
- Call that render function from `renderAll()`.
- Add event listeners in `bindEvents()`.
- Keep IDs prefixed with the tab name, for example `example-primary`, to avoid collisions.
- Keep cards at `8px` radius or less.
- Avoid landing-page or marketing-style content inside app tabs.
- Do not request current price from the user. Use market data already available through the backend.

## Minimal Copy/Paste Checklist

Replace `example` and `Example` everywhere:

```html
<button class="tab" data-tab="example" type="button">Example</button>

<section id="example" class="page">
  <div class="page-head"><h2>Example</h2></div>
  <section class="panel">
    <h3>Example View</h3>
    <div id="example-output"></div>
  </section>
</section>
```

```js
appState.example = null;

function bindExampleEvents() {
  // Optional tab-specific bindings.
}

function renderExample() {
  if (!appState.portfolio) return;
  $("#example-output").innerHTML = `<div class="activity-item"><strong>Ready</strong><span>Example tab mounted.</span></div>`;
}
```

Then wire:

```js
// inside bindEvents()
bindExampleEvents();

// inside renderAll()
renderExample();

// inside activateTab(tabId)
if (tabId === "example") renderExample();
```
