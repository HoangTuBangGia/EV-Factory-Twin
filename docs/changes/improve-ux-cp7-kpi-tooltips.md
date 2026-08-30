# KPI Contextual Tooltips

## Summary

Adds concise Vietnamese explanations to every live KPI card through a reusable, accessible tooltip
that works with hover, keyboard focus, and touch.

## Motivation

Labels such as throughput and starvation assume factory-domain knowledge. The dashboard should
explain how to interpret each value without forcing an evaluator to leave the current context.

## Architecture / Contract Impact

- Adds a dependency-free tooltip with CSS positioning and hover/focus visibility; state is used only
  to pin or dismiss the tooltip for touch interaction.
- Each KPI card and its info trigger reference the tooltip content with `aria-describedby`.
- The CP7 draft requested live congestion in place of Active tasks, but `FactoryMetrics` has no
  authoritative congestion field. Scenario results own `congestion_percent`, so the live grid keeps
  Active tasks and explains it rather than inventing a frontend KPI.
- No backend, WebSocket, metric, simulation, or database contract changed.

## Files Changed

- `apps/frontend/src/components/ui/tooltip.tsx`
- `apps/frontend/src/components/ui/tooltip.test.tsx`
- `apps/frontend/src/components/dashboard/kpi-grid.tsx`
- `apps/frontend/src/components/dashboard/kpi-grid.test.tsx`
- `apps/frontend/src/app/globals.css`
- `docs/changes/improveUX.md`
- `docs/changes/improve-ux-cp7-kpi-tooltips.md`

## Verification

- `npm --prefix apps/frontend test -- --run src/components/ui/tooltip.test.tsx src/components/dashboard/kpi-grid.test.tsx`: 2 files / 5 tests passed.
- `npm --prefix apps/frontend run lint`: passed.
- `npm --prefix apps/frontend run typecheck`: passed.
- `npm --prefix apps/frontend test -- --run`: 44 files / 205 tests passed.
- `npm --prefix apps/frontend run build`: passed; 14/14 static pages generated.
- Manual smoke: passed for desktop hover/focus, keyboard dismissal, mobile tap toggling,
  responsive positioning, and all five KPI explanations.

## CI / Build Impact

No dependency or CI configuration changed. Vitest covers accessible relationships, touch toggling,
Escape dismissal, and all five KPI explanations.

## Follow-up

Expose live congestion only if the backend adds it to the authoritative `FactoryMetrics` contract.
