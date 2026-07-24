# chromium-tabscroll

Horizontal tab scrolling for Chromium, rewritten from scratch against the current
tabstrip and built on free CI.

## Background

Chrome had a horizontal tab-scrolling feature behind `chrome://flags/#scrollable-tabstrip`
from Chrome 75 (June 2019). It never shipped enabled on stable. On 2025-11-25,
commit [`ef29babd`](https://chromium.googlesource.com/chromium/src/+/ef29babd0ce95da5665fbdd4adec6cc92770a889)
("Removing Tab Scrolling feature", Eshwar Stalin, reviewed by David Pennington and
Alison Gale, bug 414802341) deleted the whole subsystem, `+49 / -4,654` across 35
files. It shipped in Chromium 144, January 2026, taking scrolling out of Chrome,
Brave, and every Chromium browser at once.

Google's reason: the old code "relied on outdated code that couldn't be maintained
alongside the new one being built." The tabstrip is being unified (see
`kTabStripUnification`, `kVerticalTabs`), and the six-year-old scrolling
implementation was in the way.

## Why a rewrite, not a revert

Reverting `ef29babd` brings back code written for the pre-2025 tabstrip. It fights
the current architecture and breaks on the next upstream roll. The tabstrip is now
an interface (`TabStripRegionView`) with concrete backends
(`HorizontalTabStripRegionView` over `BaseTabStripRegionView`). This project adds
scrolling as a new, additive layer that plugs into the current horizontal backend,
behind its own feature flag, so it survives rebases.

The old removal diff is kept in `reference/` for study only.

## Layout

```
src/            new source files (self-authored, dropped into the tree as an overlay)
integration/    thin patches wiring the new files into BUILD.gn + the region view + flags
config/args.gn  reduced-cost release build args
scripts/        apply-patches.sh, reclaim-disk.sh
.github/        the free-CI build pipeline
reference/      the original removal diff, for reference only
PLAN.md         the re-implementation design
```

## Building on free CI

Nothing about compiling Chromium is light: a cold build is ~20-40 CPU-hours. Free
GitHub-hosted runners are 4 vCPU / 16 GB RAM / 14 GB disk. Two constraints and how
the pipeline handles them:

- **Disk.** 14 GB can't hold the checkout. `scripts/reclaim-disk.sh` frees ~30 GB
  by removing preinstalled SDKs.
- **Time.** A cold build won't finish in the 6-hour job limit. The pipeline warms
  an `sccache` so each run is mostly cache hits and resumes where the last stopped.
  GitHub's 10 GB cache is smaller than Chromium's object volume, so a truly free run
  makes partial progress; a full downloadable Chrome artifact realistically needs a
  few dollars of S3/R2 object storage (wire it via the `s3` cache backend). See
  `.github/workflows/build.yml`.

## Local build

```bash
export CHROMIUM_SRC=/path/to/chromium/src
./scripts/apply-patches.sh
cp config/args.gn "$CHROMIUM_SRC/out/Default/args.gn"
cd "$CHROMIUM_SRC" && gn gen out/Default && autoninja -C out/Default chrome
```

Toggle at runtime with `chrome://flags/#horizontal-tab-scrolling`.

Source of truth is `chromium.googlesource.com`; the code was read from the read-only
`github.com/chromium/chromium` mirror.
