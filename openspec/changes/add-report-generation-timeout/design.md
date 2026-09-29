# Design

## Context

See [proposal.md](proposal.md) for the motivation. The current quality-assess worker executes `quality.assess()` directly. The PDF path has several blocking boundaries:

- PyVista `Plotter(off_screen=True)` and `screenshot()`: in-process native rendering;
- Plotly `write_image()`: Kaleido launches Chrome through Choreographer;
- PyLaTeX `generate_pdf()`: launches `latexmk`/`xelatex` through `subprocess.check_output()`.

PyLaTeX's subprocess call has no timeout. PyVista native calls cannot be interrupted reliably by a Python thread. Therefore a thread-only watchdog or `subprocess.timeout` around one compiler is insufficient. The change must supervise the report phase as a separate process and terminate the complete process tree on timeout.

The timeout is deliberately scoped to report generation, not to upstream point-cloud loading, registration or deviation computation. The supervisor starts its countdown when the report phase marker appears, so a long but legitimate upstream calculation is not killed by this change.

## Goals / Non-Goals

**Goals:**

- Enforce a default 300-second timeout for report rendering and PDF compilation.
- Return a failed task with a user-visible error that includes the timeout seconds and the last report sub-stage.
- Ensure no PDF artifact is registered after timeout.
- Release the worker so queued tasks can continue.
- Clean up child processes reliably on Linux and Windows.
- Keep successful report behavior, naming and layout unchanged.

**Non-Goals:**

- Do not change point-cloud algorithms, deviation calculations, report templates or PDF naming.
- Do not add a global timeout for the entire quality-assessment task.
- Do not introduce a new external dependency such as `psutil`; use standard-library process APIs plus platform commands.
- Do not attempt to repair the underlying Chrome, MiKTeX or graphics-driver problem; only contain it.

## Decisions

### D1: Supervise the complete report phase in a dedicated child process

Use a dedicated Python subprocess (`python -m app.report.worker`) for the quality-assess report phase. The existing worker becomes the supervisor: it writes an internal payload, starts the subprocess, monitors a report-state file and result/error JSON, and raises `ReportTimeoutError` if the report phase exceeds the configured timeout. The payload is internal work-directory data, not browser input.

Alternative considered: interrupt `pylatex` or Kaleido with a Python thread. Rejected because native PyVista calls and external browser/LaTeX subprocesses may not observe Python cancellation.

Alternative considered: apply `subprocess.run(timeout=...)` only to `latexmk`. Rejected because it would not cover PyVista or Kaleido and would leave the task hanging in those stages.

### D2: Start the timeout at the report-phase marker, not at worker startup

`quality.assess()` first completes upstream data loading, filtering and deviation calculation, then writes a state file before the first report-specific operation and updates its `stage` before each blocking sub-stage. The supervisor waits for `report_started=true`, then starts the 300-second countdown. This ordering keeps upstream algorithm time outside the report timeout.

Suggested stable stages:

- `渲染输入点云图`
- `渲染环境/检测点图`
- `渲染偏差云图`
- `导出偏差直方图（Plotly/Kaleido）`
- `编译 PDF（latexmk/xelatex）`

This keeps the timeout focused on the report path and gives the user a meaningful failure reason.

Alternative considered: start the timeout when the child process starts. Rejected because upstream point-cloud processing could legitimately exceed 5 minutes, and the requirement targets PDF/report generation.

### D3: Make the timeout configurable with a fixed default

Add `WUYE_REPORT_TIMEOUT_SECONDS` with default `300`. Parse it as a positive integer with a sane lower/upper bound. The default satisfies the required 5-minute behavior; tests can inject a short value without waiting five minutes.

Alternative considered: hard-code 300 in the code. Rejected because tests and future deployment tuning need a controlled override.

### D4: Terminate the whole process tree with platform-specific semantics

The report subprocess is launched with `subprocess.Popen`:

- On Linux/macOS, `start_new_session=True` creates a new session/process group; timeout cleanup sends `SIGKILL` to that process group.
- On Windows, `CREATE_NEW_PROCESS_GROUP` is used and cleanup invokes `taskkill /F /T /PID <pid>` so Chrome, `latexmk`, `xelatex` and other descendants are terminated with the report child.

The supervisor waits for termination and ignores already-exited children. A timeout is converted to `ReportTimeoutError(timeout_seconds, last_stage)`, which the job runner records as a normal task failure.

Alternative considered: call `Process.terminate()` only. Rejected because on Windows it may leave descendant Chrome/TeX processes running and continue to occupy resources.

### D5: Do not register partial report artifacts

The child writes report outputs to the job work directory. The supervisor only returns the result metadata after the child exits successfully. If the child times out or exits non-zero, the worker raises an exception and the existing job runner does not call `register_artifact()`. Partial `.jpg`, `.tex`, `.pdf` files may remain in the work directory for diagnosis, but they are never exposed as session artifacts.

### D6: Keep timeout state file separate from the existing progress schema

Add a report-specific state file (for example `report_state.json`) rather than expanding `progress.json`:

- `report_started`: boolean
- `stage`: last report sub-stage
- `updated_at`: ISO timestamp

The existing progress JSON remains compatible with the frontend. The supervisor reads the report state file while waiting; if the file is temporarily missing or malformed, it keeps the last valid stage and continues monitoring.

## Risks / Trade-offs

- [The report subprocess or its descendants may be blocked in native code] → Kill the process tree from the supervisor; do not rely on Python-level cleanup handlers inside the child.
- [Windows `taskkill` may be unavailable or return non-zero] → Treat cleanup as best-effort, record the timeout failure regardless, and log the cleanup command result.
- [A legitimate report could take longer than 300 seconds] → The timeout is configurable; the default satisfies the requested behavior.
- [Child-process startup adds overhead] → The report phase already launches Chrome and LaTeX; one additional process startup is negligible and the process is not created for non-quality tools.
- [Partial files may remain after timeout] → They stay in the internal job work directory, are not registered, and can be inspected for the failing sub-stage.
- [Tests must not depend on real Chrome/TeX hangs] → Inject a blocking test callable and a short timeout into the supervisor; keep existing real report tests for the successful path.

## Migration Plan

1. Add configuration and the report timeout/supervisor helpers.
2. Add report-phase markers around the existing PyVista/Kaleido/LaTeX calls.
3. Route quality-assess through the supervisor.
4. Add unit and integration tests, including a forced short timeout and worker-release check.
5. Run existing backend tests and the real report toolchain test.
6. Roll back by removing the supervisor route and restoring direct `quality.assess()` execution; normal PDF behavior is unchanged.

## Open Questions

None. The agreed scope is a default 5-minute timeout for the report-generation phase, covering report images, Kaleido export and PDF compilation, with stage-specific failure reporting on Linux and Windows.
