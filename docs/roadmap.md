# Suggested Edits And Roadmap

This document captures the sub-agent/Grok-style recommendations for turning this
repo from a tab-scrolling patch into a practical Chromium overlay toolkit for
2026 browser pain points.

## Completed In This Pass

- Added `chrome://flags/#horizontal-tab-scrolling` integration through anchored
  edits in `integration/integrate.py`.
- Extended `scripts/integrate-check.sh` to fetch and assert all touched upstream
  files:
  - `chrome/browser/about_flags.cc`
  - `chrome/browser/flag_descriptions.h`
  - `chrome/browser/ui/tabs/features.{h,cc}`
  - `chrome/browser/ui/BUILD.gn`
  - `chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.{h,cc}`
  - `chrome/browser/ui/views/tabs/tab_strip.cc`
- Added active-tab reveal on selection changes by inserting
  `new_active_tab->ScrollRectToVisible(new_active_tab->GetLocalBounds())` into
  `TabStrip::SetSelection`.
- Fixed caption hit-testing so the scrolled viewport is checked before delegating
  to the nested tab strip.
- Added CI assertions for the new tab-scroll source/header entries, include,
  z-order handling, new-tab-button placement, flag entry, and active-tab reveal.
- Fixed the GitHub Actions build step so real compile failures fail the workflow
  instead of being treated like a timed continuation.
- Added runtime launch profiles in `config/runtime-flags/`:
  - `base`
  - `performance`
  - `privacy`
  - `no-ai`
  - `compatibility`
  - `adblock-friendly`
- Added scripts for runtime profile usage and validation:
  - `scripts/print-flags.sh`
  - `scripts/launch-chromium.sh`
  - `scripts/validate-runtime-flags.sh`
  - `scripts/check-feature-drift.sh`
- Added documentation:
  - `docs/performance-defaults.md`
  - `docs/ai-opt-out.md`
  - `docs/adblock-manifest.md`
- Added managed-policy examples under `config/policies/`.
- Updated `README.md` and `PLAN.md` to describe the broader overlay scope.

## Remaining High-Value Edits

### Drag Edge Auto-Scroll

Add tab-drag auto-scroll when a dragged tab approaches the left or right edge of
the scroll viewport.

Likely upstream target:

```text
chrome/browser/ui/views/tabs/dragging/dragging_tabs_session.{h,cc}
```

Likely anchor:

```cpp
DraggingTabsSession::MoveAttached(gfx::Point point_in_screen)
```

Expected behavior:

- Detect when the dragged tab is near the visible viewport edge.
- Scroll left or right while the drag remains near that edge.
- Keep the implementation tied to the current Chromium drag path, not the old
  deleted `dragging_tabs_session.*` location.

Open design choice:

- Either expose a helper on `HorizontalTabScrollContainer`, or locate the nearest
  parent `views::ScrollView` from the attached `TabDragContext`.

### Scoped New-Tab-Button Replacement

The integrator currently replaces `tab_strip_->bounds().right()` with the scroll
container-aware expression. This is asserted by CI, but the replacement should be
scoped more tightly to `HorizontalTabStripRegionViewOld::Layout(PassKey)` if
upstream introduces another matching expression.

Desired result:

```cpp
scroll_container_ ? scroll_container_->bounds().right()
                  : tab_strip_->bounds().right()
```

### Source-Level Tests

There are no Chromium unit tests for `HorizontalTabScrollContainer` yet.

Candidate coverage:

- available-width callback preserves full preferred width;
- wheel events map to horizontal scroll;
- active tab reveal works after selection changes;
- viewport hit-test avoids unclipped tab-strip geometry.

Likely build target:

```text
chrome/test/BUILD.gn
```

### Feature Drift Checks Without Full Checkout

`scripts/check-feature-drift.sh` works against a local Chromium checkout. Add a
no-checkout variant that fetches selected upstream files through the GitHub API,
similar to `scripts/integrate-check.sh`.

Tracked feature strings:

- `OptimizationGuideModelDownloading`
- `OptimizationGuideOnDeviceModel`
- `Compose`
- `TabOrganization`
- `HistorySearch`
- `LensOverlay`

## Browser Pain-Point Overlay Roadmap

### Phase 1: Runtime Profiles

Keep runtime profiles composable and conservative:

```bash
./scripts/print-flags.sh base performance
./scripts/print-flags.sh base privacy no-ai
./scripts/print-flags.sh adblock-friendly
```

Rules:

- do not promise that every upstream flag remains honored forever;
- merge repeated `--enable-features` and `--disable-features`;
- validate syntax in CI before starting a long Chromium build.

### Phase 2: CI Guardrails

Maintain fast checks before the expensive build:

- anchored upstream integration check;
- runtime flag syntax check;
- docs presence check;
- future no-checkout feature drift check.

### Phase 3: User-Facing Fork Flags

Use `chrome://flags` entries where Chromium has a real feature hook.

Current implemented flag:

```text
chrome://flags/#horizontal-tab-scrolling
```

Potential future flags should be backed by actual source behavior, not just docs.

### Phase 4: Adblock And Extension Policy

Keep the toolkit policy-focused:

- no bundled blocklists;
- no bundled third-party extensions;
- managed-policy samples for controlled installs;
- explicit docs around MV2/MV3 limits and upstream drift.

### Phase 5: AI / ML Opt-Out Tracking

Keep browser AI behavior visible and easy to disable where Chromium exposes a
supported switch or feature name.

Primary user-facing entry point:

```bash
./scripts/print-flags.sh no-ai
```

Do not claim total AI removal unless each source path has been inspected for the
exact Chromium revision being built.

## Grok / Composer Workflow

The local machine has a `grok` CLI:

```bash
grok --version
grok models
```

Useful headless pattern once authenticated:

```bash
grok -p "Audit this Chromium overlay for browser pain-point fixes. Return concrete files, anchors, and risks." \
  --cwd /Users/abhishekshivakumar/quinjet/chromium-tabscroll \
  --model grok-4.5 \
  --permission-mode auto
```

Parallel comparison pattern:

```bash
grok -p "Find the next highest-value Chromium overlay fixes in this repo." \
  --cwd /Users/abhishekshivakumar/quinjet/chromium-tabscroll \
  --model grok-4.5 \
  --best-of-n 3 \
  --permission-mode auto
```

Current blocker:

```text
You are not authenticated.
```

Run `grok login` before using Grok/Composer instances from this workspace.
