# Changelog

All notable changes to the ACH PDF Splitter Bot are listed here, newest first.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and version numbers match `projectVersion` in `project.json`.

## [Unreleased]

### Changed
- README: added a short "How it works" section covering the merged ACH remittance PDF, the one-PDF-per-payment split, filing under the fiscal period, and the SHA-256 skip for reports that were already filed.
- README: turned "How to run" into "Setup", with separate UiPath Studio and Python steps that spell out the run-date Input folder, the report-date output subfolder, `FileStableMinutes`, and the skip on re-run.

## [1.0.1] - 2026-10-30

First tagged release of the public showcase. It is a sanitized rebuild of the production bot, and all sample data is fictional.

### Added
- UiPath Studio 25.10 Windows project (C#) with all settings in `Config/Config.xlsx`.
- Framework workflows that read and validate the config, work out fiscal-year and period folders from the run date, create missing folders, and pick up only source PDFs that have finished copying (the stable-file check).
- SHA-256 hashing of each source report plus a processed-source manifest, so a report that was already processed is skipped and re-running the bot is always safe.
- `Main.xaml` orchestration and a page-by-page PDF splitter that writes one PDF per ACH transaction, named `001 - Payer - $Amount.pdf`, and keeps multi-page transactions together.
- CSV run log with one row per run (counts of matched, deferred, processed and skipped reports, PDFs created, timing and status).
- Fictional 6-page sample ACH report, the expected split output (five payment PDFs), and an offline Python simulator of the parsing rules.
- README with an architecture diagram, the idempotency design, a config reference, a sample walkthrough, known limitations and a roadmap.
- GitHub Actions CI that runs on every push and pull request. It checks that every `.xaml` file is valid XML, that the simulator's split of the sample matches the expected output, and that a second run skips the report.

### Changed
- Replaced leftover `DEBUG` Write Line activities in `PDF/ProcessSourcePdf.xaml` with Log Message activities at Trace level, so page-level detail stays out of normal robot logs.

[Unreleased]: https://github.com/Chris1112220/uipath-ach-pdf-splitter/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/Chris1112220/uipath-ach-pdf-splitter/releases/tag/v1.0.1
