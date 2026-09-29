# Design

## Context

See `proposal.md` for motivation. The current quality-assessment result stores the same Plotly figure used for the report in `summary.figure`. Point2Point test data produces 5348 bars and 1337 tick labels; Plotly rendering that figure in the browser takes about 19 seconds. Point2Plane currently produces no bars, so its render is negligible.

The PDF figure is generated before the result summary is assembled. The browser also does not need every original bin to understand the distribution or preserve the four reported metrics.

## Goals / Non-Goals

**Goals:**

- Bound browser histogram rendering to a fixed maximum number of bars and x-axis ticks.
- Generate the browser figure from the same error array and cut line as the PDF figure.
- Preserve the four statistical metrics, PDF image, PDF layout, and report naming.
- Keep the existing `summary.figure` contract intact for compatibility.

**Non-Goals:**

- Do not change Point2Point or Point2Plane algorithms or their numerical results.
- Do not change `base_software`.
- Do not change PDF rendering, TeX templates, or report image resolution.
- Do not remove `figure` from session results in this change.
- Do not introduce a general-purpose charting or data-visualization dependency.

## Decisions

### D1: Add a browser-only `summary.ui_figure`

Add an optional `summary.ui_figure` alongside the existing raw `summary.figure`. The frontend uses `ui_figure` for the interactive chart. This keeps existing result consumers compatible and makes the distinction between report data and browser presentation explicit.

Alternative considered: replace `summary.figure` with the bounded figure. Rejected because it silently changes the existing result contract and makes it harder to distinguish report data from UI data.

Alternative considered: downsample entirely in the browser. Rejected because the browser would still receive and parse the pathological figure, and the transformation would be duplicated outside the report/statistics layer.

### D2: Fixed UI limits of 256 bars and 20 ticks

The UI figure must contain at most 256 bars and at most 20 x-axis tick values. For the observed 5347.33 mm result, this reduces 5348 bars and 1337 ticks to roughly 255 bars and at most 20 ticks.

The UI builder uses adaptive bin width and tick stride rather than dropping frequency data:

- `ui_step = max(1, ceil(max_error_mm / 256))`
- `ui_tick_stride = max(1, ceil(ui_bin_count / 20))`
- `show_clum(..., step=ui_step, IS=ui_tick_stride)` builds the UI figure from the same sorted error array.

The original report call remains `step=1, IS=4`. The cut line, annotations, mean, median, max, and other statistics are computed from the same `error_sorted` array.

Alternative considered: cap at 512 bars and 50 ticks. Rejected for this demo because 256/20 gives more margin on Windows and still preserves the distribution shape.

### D3: Reuse the existing histogram builder

Use `backend/app/report/figures.py` as the single source of histogram construction. Add a small helper for UI parameters and call the existing `show_clum` twice: once for the unchanged report figure and once for the bounded UI figure.

This keeps hover templates, cut-line behavior, and layout semantics aligned. A post-processing implementation that edits Plotly JSON after serialization was rejected because compressed `bdata` arrays make aggregation brittle.

### D4: Frontend selects the UI figure, with compatibility fallback

Add a small `selectHistogramFigure(summary)` helper in `frontend/src/utils/qa.ts`. `QualityAssessView.vue` uses it to pass `summary.ui_figure` to `DeviationHistogram.vue`; if `ui_figure` is absent, the helper retains the current `figure` fallback so existing result shapes still render.

No frontend charting dependency or new API endpoint is required.

### D5: Keep limits as code constants for this change

Use fixed constants in the quality/report layer, for example `UI_HISTOGRAM_MAX_BARS = 256` and `UI_HISTOGRAM_MAX_TICKS = 20`. Do not add an environment variable in this change; configuration can be introduced later if a real need appears.

### D6: Convert the Vue reactive figure to plain JSON before Plotly

The real-browser reproduction showed that `Plotly.react()` receives a deeply reactive Vue Proxy for `summary.ui_figure`. Plotly's deep traversal of that proxy can block the renderer indefinitely even for 21 bars. The same figure cloned to a plain JSON object renders in about 121 ms.

Add `toPlainFigure()` at the Plotly boundary and use it in `DeviationHistogram.vue`. The input figure is already a JSON API payload, so `JSON.parse(JSON.stringify(...))` is a simple and faithful boundary conversion. Alternative `markRaw`/`shallowRef` changes were rejected because they affect reactivity across the page and do not guarantee that every nested value passed to Plotly is plain data.

## Risks / Trade-offs

- [Aggregation hides individual one-mm bins] → Keep the raw `figure` and PDF unchanged; expose the aggregated interval in hover data and preserve all reported statistics.
- [A future change raises the limits without testing Windows] → Keep the limits explicit constants, assert them in backend tests, and treat a limit increase as a performance-affecting change.
- [An old result lacks `ui_figure`] → Frontend fallback keeps compatibility; new quality-assessment jobs always include `ui_figure`.
- [Plotly's typed-array JSON representation differs from plain arrays] → Build the UI figure through the existing Plotly serializer and test the emitted `ui_figure` structure, not a browser-only transformation.
- [Plotly receives a reactive Proxy] → Clone the figure to a plain JSON object at the Plotly boundary; test the invariant with a reactive source object.
- [The empty Point2Plane figure has no bars] → Do not special-case it; the bounded UI figure remains empty and renders quickly.

## Migration Plan

1. Add the UI limit constants and helper in the backend histogram layer.
2. Build and serialize `ui_figure` after the unchanged report figure is generated.
3. Switch the quality page to `ui_figure` with a compatibility fallback, then clone the selected figure to plain JSON before `Plotly.react`.
4. Add backend tests for bar/tick limits, numerical metadata, and empty results.
5. Add frontend tests for figure selection and run a real browser check with a large Point2Point result.

Rollback is limited to removing `ui_figure` and restoring the frontend to `figure`; no data migration or API versioning is required.

## Open Questions

None. The approved scope fixes the display cap and keeps report/algorithm behavior unchanged.
