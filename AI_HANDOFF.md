# AI handoff: retail-cancellation-leakage

A shared technical record for project work. It contains no local machine paths, credentials, or private account data.

## Working rules

- Keep this repository's project changes separate from protected projects.
- Report checks only when they actually ran; include failures and skipped checks.
- Keep public profile and resume claims aligned with verified repository state.
- Keep generated data and large exports out of Git; regenerate them from the pipeline.

## Verified repository snapshot

- Repository: https://github.com/Anubhavkumarkanth/retail-cancellation-leakage
- Default branch: `main`
- Baseline reviewed commit: `6cf7820029df3010dfc8b2b84a88b2686fdcffac`
- Local suite at baseline: 16 passed, 0 skipped; CI ran 9 SQL-logic tests and passed.
- Published metrics: gross sales £19,699,785; cancelled value £719,656; headline rate 3.65%; same-day reversals £356,000; adjusted rate 1.88%; reversal share 49.5%.

## B7–B10 work prepared

- Star-schema exporter, six tests, and Power BI guide are included. The four CSVs are generated data and remain ignored.
- Landing page, site build script, and GitHub Pages workflow are included; the first hosted build and deploy succeeded.
- README, CI comment, and figure-title updates are merged; the README now links to the verified live dashboard.
- B9 AI-summary work was skipped per the owner's prior decision.
- The `.pbix` report has not been created; its five cards need to match the values above.

## Deployment status

1. Completed: Pages workflow and site files were merged in PR #1.
2. Completed: GitHub Pages is enabled with GitHub Actions as the source.
3. Completed: site and figures verified; the live URL is in the README and repository homepage.
4. The resume and GitHub profile reflect the verified site and 22 tests. The `.pbix` is still owner-built and is not claimed.

## Stage log

### B5a — 24-hour reversal boundary test

- Commit `6cf7820` added cases for 23h59m and exactly 24h as reversals, and 24h01m as other.
- Verification: 9 SQL-logic tests passed in CI; 16 tests passed locally; mutation checks showed both widened and narrowed boundaries fail the new cases.
- Codex review: pass with warnings. No code changes were made by the review.

### B1–B6 — read-only walkthrough

- Worked examples were verified against the real data. B1 answer 3 was refined: `dtype=str` protects the pandas string-filtering stage; SQLite stores mixed invoice identifiers in its TEXT column.
- B2–B6 checks and exercises were covered. Worked examples do not establish the owner's independent understanding.

### B7–B10 — prepared drafts

- Baseline replay in a temporary clone: data pipeline rebuilt, 16 original tests passed, and `kpi_overview.csv` matched the committed output.
- Star-schema check: 1,032,918 fact rows, 739 dates, 4,892 products, 5,875 customers; six draft tests passed.
- Site check: no horizontal overflow at 1280px or 400px, no broken images or console errors, dashboard chart rendered.
- At draft time, GitHub-hosted Pages, the live site, Power BI report, real-phone view, and current LinkedIn text had not been verified. The deployment and live-site checks are now recorded below.

### Release candidate — Pages and Power BI additions

- Action majors verified on 2026-10-24: checkout v7, setup-python v7, cache v6, upload-pages-artifact v5, deploy-pages v5.
- The workflow YAML parsed into two jobs with least-privilege permissions; the deploy job receives only Pages and OIDC permissions.
- The combined suite passed 22 tests locally (9 SQL logic, 7 real-data, 6 star-schema). The new star-schema test resolves `data/retail.db` relative to the repository, so CI can run it after `run_all.py`.
- The site built locally and all template placeholders were substituted. The local Playwright check did not finish in this runner; Claude's separate local check reported no overflow at 1280px and 400px, broken images, or console errors.
- The GitHub-hosted Pages build and deploy succeeded. The live homepage and dashboard returned HTTP 200; all seven local assets returned HTTP 200; 3.65%, 1.88%, and 49.5% are present; no KPI template placeholders remain.
- The `.pbix`, real-phone view, and current LinkedIn text remain unverified.

### 2026-10-24 — Release published

- PR #1 merged as `bd431ff`; both pull-request SQL-logic checks passed.
- GitHub Pages enabled with Actions. Workflow run 40117269003 completed successfully; the build job ran the pipeline and full 22-test suite before deploy.
- Live URL: https://anubhavkumarkanth.github.io/retail-cancellation-leakage/
- Live landing page and dashboard returned HTTP 200. The five figures, Excel workbook, and CSV listing returned HTTP 200. KPI values and template substitution verified.
- Repository homepage now points to the live site; repository About description now reflects the live dashboard and 22 tests.
- .pbix remains unbuilt because Power BI Desktop is not installed in the available environment. It is not claimed in the README or resume.
