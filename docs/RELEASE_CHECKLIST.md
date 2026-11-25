# ORBITLINK release checks

GitHub Actions runs Python regression tests and the complete frontend module graph on main pushes and pull requests. The module test catches imported-file syntax errors like the previous blank-page regression. It does not establish that WebGL, camera interactions, file dialogs or print layout work in a browser.

Before deployment:
1. Confirm the validation workflow is green for the intended commit.
2. Check catalog freshness and excluded-record counts.
3. Run one site comparison and export a report.
4. Run one acknowledged receiver trial; inspect pending messages and attempt evidence.
5. Open every tab in a real browser; verify globe movement, camera dragging, journey controls, survey save/import and report printing.

After deployment:
1. Confirm Render reports the intended commit live.
2. Request health, static entry assets and a small orbital scenario.
3. Repeat an isolated receiver recovery test and a planner/benchmark API check when their paths changed.
4. Record remaining limitations. Local SQLite and catalog caches on free hosting are ephemeral; hosted PostgreSQL stores delivery data separately, and public orbital predictions do not prove operator service availability.

The current Render deployment is manual. The workflow reports failures but does not itself prevent a manual deployment. Inspect it before publishing.
