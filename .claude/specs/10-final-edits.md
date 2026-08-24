# Spec: Final Edits

## Overview

This step is a visual/layout redesign of the already-implemented `/profile` dashboard. No new routes, no new business logic, and no schema changes — every underlying function (add, edit, delete, filter) already works correctly. The goal is purely to rearrange and restyle what's already on the page: (1) merge the "Add expense" action and the date-range filter into a single panel instead of the add-expense CTA linking out to a separate page, (2) turn the "Spend by category" bar chart into a pie/donut chart and move it to a side column, (3) rename "Recent expenses" to "All expenses", show the user's full expense history (not just the latest 5) in a scrollable panel, and place that panel in the wider, central column. Edit/delete links on each expense row are unchanged.

## Depends on

- Step 4 (Profile Page Design) — this reshapes `profile.html` / `profile.css` and the stats/chart/list it introduced.
- Step 5 (Date Filter) — the date-range filter being merged into the new combined panel.
- Step 7 (Add Expense) — the add-expense form being embedded inline; the `POST /expenses/add` handler is reused as-is.
- Step 8 (Edit Expense) / Step 9 (Delete Expense) — the per-row edit/delete links carried over unchanged into the "All expenses" panel.

## Routes

No new routes. No routes are removed.

- `GET /profile` — unchanged signature; now also passes `categories` (the existing `ALLOWED_CATEGORIES` list) so the inline add-expense form can render its category `<select>`, and calls `get_all_expenses()` instead of `get_recent_expenses()`.
- `POST /expenses/add` — unchanged; the form embedded in the profile panel posts here exactly like the current standalone `add_expense.html` page does. The standalone `GET /expenses/add` page and template are left in place (still reachable directly) — this step does not delete that route.

## Database changes

No new tables, columns, or constraints.

One new function in `database/db.py`, following the existing `_apply_date_range()` pattern used by `get_expense_summary`, `get_category_breakdown`, and `get_recent_expenses`:

- `get_all_expenses(user_id, start_date=None, end_date=None)` — parameterized `SELECT * FROM expenses WHERE user_id = ?` with the same optional `AND date BETWEEN ? AND ?` clause, `ORDER BY date DESC, id DESC`, **no `LIMIT`**. Returns an empty list (not `None`) when the user has no expenses in range.

`get_recent_expenses()` becomes unused once `profile()` switches to `get_all_expenses()` — remove it from both `database/db.py` and the `app.py` import list rather than leaving dead code behind.

## Templates

**Modify:**
- `templates/profile.html` —
  - Remove the header's `+ Add expense` link-out button.
  - Merge `.profile-filter` (the date-range form) and a new inline add-expense form into one panel card, e.g. two sections stacked or side-by-side inside a single `panel-card` (implementer's call on exact sub-layout, as long as both live in one visual panel). The inline form posts to `url_for('add_expense')`, uses the same fields/validation as `add_expense.html` (`amount`, `category` via `categories`, `date`, `description`), and re-displays the same `error` on failed validation.
  - Replace the "Spend by category" bar chart markup with a pie/donut chart (CSS `conic-gradient` — no new JS chart library) built from `category_breakdown`, each slice using the matching `--cat-{{ category|lower }}` token. Keep a text legend beside/below the chart (category name + dot, same as today) — color stays a secondary channel, never the sole identifier.
  - Rename the "Recent expenses" panel title to "All expenses" and source it from `get_all_expenses()` (renders via a new `all_expenses` context var) instead of `recent_expenses`. Wrap the list in a scrollable container (fixed `max-height`, `overflow-y: auto`) so an arbitrarily long history doesn't push the rest of the page down. Keep the existing per-row Edit/Delete links unchanged.
  - Re-layout `.profile-panels` so the pie chart panel is the narrower side column and the "All expenses" panel is the wider, central column.

**No new templates.** `templates/add_expense.html` is untouched.

## Files to change

- `templates/profile.html` — combined add-expense + filter panel; pie chart in place of the bar chart; "All expenses" panel (renamed, full list, scrollable); reflowed `.profile-panels` layout; remove header CTA button
- `static/css/profile.css` — styles for: the combined panel (form + filter together), the pie/donut chart (`conic-gradient` circle + legend), the scrollable all-expenses list, and the revised side/center grid split
- `app.py` — `profile()`: pass `categories=ALLOWED_CATEGORIES` to the template, call `get_all_expenses(...)` instead of `get_recent_expenses(...)`, pass result as `all_expenses`; update the `database.db` import list (drop `get_recent_expenses`, add `get_all_expenses`)
- `database/db.py` — remove `get_recent_expenses`, add `get_all_expenses`

## Files to create

None.

## New dependencies

No new dependencies — the pie chart is CSS-only (`conic-gradient`), consistent with "vanilla JS only, no npm packages."

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Use CSS variables — never hardcode hex values; pie slices and legend dots reuse the existing `--cat-*` tokens from `style.css`, the same palette already validated for the bar chart
- All templates extend `base.html` (no change to `profile.html`'s `{% extends %}`)
- Color remains a secondary identity channel — every pie slice/category is still text-labeled in the legend, never color-only
- The scrollable "All expenses" panel must use a contained `overflow-y: auto` (fixed `max-height`), not a page-level scrollbar — the rest of the dashboard (header, combined panel, pie chart) stays fully visible without scrolling
- The inline add-expense form must reuse the exact same field set, `name` attributes, and validation error display as the existing `POST /expenses/add` handler — don't fork the validation logic, just relocate the markup
- Keep the empty-state messages ("No expenses yet." / "No expenses in this range.") for both the pie chart and the "All expenses" panel when there's no data
- Preserve the existing per-row Edit/Delete links and their `url_for('edit_expense', ...)` / `url_for('delete_expense', ...)` targets exactly as they are today
- Use `url_for()` for every internal link/action — never hardcode paths
- Keep the layout responsive — collapse the side/center columns to a single column on small viewports, same breakpoint pattern already used in `profile.css`

## Definition of done

- [ ] `/profile` no longer shows a separate "+ Add expense" button that navigates away — an add-expense form is visible inline, in the same panel as the date-range filter
- [ ] Submitting the inline add-expense form with valid data adds the expense and returns to `/profile` showing it, exactly like the standalone form does today
- [ ] Submitting the inline add-expense form with invalid data (e.g. blank amount) re-renders the panel with the same validation error text used today
- [ ] The date-range filter still works exactly as before (filters stats, pie chart, and the expenses list; "Clear filter" still works) from within the combined panel
- [ ] The category chart renders as a pie/donut (not bars), with each slice colored from the `--cat-*` tokens and a text legend naming every category — no category is identifiable by color alone
- [ ] The pie chart panel sits in a narrower side column; the expenses panel sits in the wider central column
- [ ] The second panel's title reads "All expenses", not "Recent expenses"
- [ ] The "All expenses" panel lists every expense for the current user/filter (not just 5), newest first, inside a scrollable container — the rest of the page does not grow or require page-level scrolling to reveal it
- [ ] Edit and Delete links on each row in "All expenses" still work and point at the same routes as before
- [ ] A user/filter range with zero expenses shows the existing empty-state message in both the pie chart panel and the "All expenses" panel, not an error or a blank box
- [ ] The layout is responsive: side/center columns collapse to a single column on narrow viewports, matching the existing breakpoint pattern in `profile.css`
- [ ] `database/db.py` no longer defines `get_recent_expenses`; `get_all_expenses` is used instead, is parameterized, and returns `[]` (not `None`) for no matching rows
- [ ] The app starts and runs without errors on `python app.py` (port 5001)
