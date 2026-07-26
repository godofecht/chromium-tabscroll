# AI / ML Feature Opt-Out Notes

Goal: make implicit browser AI behavior visible and easy to disable.

Runtime profile:

```bash
./scripts/print-flags.sh no-ai
```

Tracked feature-name targets:

- `OptimizationGuideModelDownloading`
- `OptimizationGuideOnDeviceModel`
- `Compose`
- `TabOrganization`
- `HistorySearch`
- `LensOverlay`

Use `scripts/check-feature-drift.sh` against a Chromium checkout to see whether
these names still exist. The check is intentionally conservative: it warns about
missing strings and does not claim total AI removal unless each source path has
been inspected for the target Chromium revision.
