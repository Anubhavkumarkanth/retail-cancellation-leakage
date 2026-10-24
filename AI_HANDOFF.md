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
- Landing page, site build script, and GitHub Pages workflow are included. The live workflow has not run yet.
- README, CI comment, and figure-title changes prepared as patches and checked against a temporary clone.
- B9 AI-summary work was skipped per the owner's prior decision.
- The `.pbix` report has not been created; its five cards need to match the values above.

## Deployment sequence

1. Review and merge the Pages workflow and site files.
2. Enable GitHub Pages with GitHub Actions as the source.
3. Verify the deployed site and figures before adding the live URL to public materials.
4. Update resume/profile claims only from verified results; do not imply the Power BI report exists until it has been built and checked.

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
- GitHub-hosted Pages run, live site, Power BI report, real-phone view, and current LinkedIn text remain unverified.

### Release candidate — Pages and Power BI additions

- Action majors verified on 2026-10-24: checkout v7, setup-python v7, cache v6, upload-pages-artifact v5, deploy-pages v5.
- The workflow YAML parsed into two jobs with least-privilege permissions; the deploy job receives only Pages and OIDC permissions.
- The combined suite passed 22 tests locally (9 SQL logic, 7 real-data, 6 star-schema). The new star-schema test resolves `data/retail.db` relative to the repository, so CI can run it after `run_all.py`.
- The site built locally and all template placeholders were substituted. The local Playwright check did not finish in this runner; Claude's separate local check reported no overflow at 1280px and 400px, broken images, or console errors.
- The GitHub-hosted Pages run, live site, `.pbix`, real-phone view, and current LinkedIn text remain unverified.