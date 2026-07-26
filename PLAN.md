# Design: horizontal tab scrolling, rewritten

A from-scratch scroll layer that plugs into the current tabstrip, verified against
Chromium HEAD (read from the mirror, not guessed). It does not resurrect the
deleted `TabStripScrollContainer`; that code targeted a tab data model that no
longer exists.

## The current tabstrip (what we build against)

- `TabStripRegionView` is now a pure abstract interface owned by `BrowserView`.
- Two concrete backends are chosen at construction by `kTabStripUnification`
  (`horizontal_tab_strip_region_view.cc:905`):
  - `HorizontalTabStripRegionViewOld` — the default, shipping path. This is the
    target.
  - `HorizontalTabStripRegionViewNew` (over `BaseTabStripRegionView`) — the
    collection-based unification path, flag-off. Out of scope for now.
- In the Old path the tab row is: `Tab` → `TabContainerImpl` → `TabStrip` →
  `HorizontalTabStripRegionViewOld`. The region view adds the strip as a
  FlexLayout child: `tab_strip_ = AddChildView(CreateTabStrip(this, browser_view));`
  (`:223`).

## The one seam that matters: available width

`TabContainerImpl::GetAvailableWidthForTabContainer()` (`tab_container_impl.cc:694`)
decides how much width the tabs lay out within:

```cpp
return available_width_callback_
           ? available_width_callback_.Run()
           : parent()->GetAvailableSize(this).width().value();
```

Today the callback is never set, so width comes from the parent's FlexLayout
allocation, which shrinks tabs toward a minimum when there are too many. Set that
callback to the tab strip's full preferred width and tabs keep their size and
overflow instead. `TabStrip::SetAvailableWidthCallback` (`tab_strip.cc:1197`)
forwards to the container. This is the exact hook the removed feature used; it
survived the removal.

## The implementation

**New file — `HorizontalTabScrollContainer`** (`views/tabs/horizontal_tab_scroll_container.{h,cc}`).
A `views::ScrollView` subclass that:
- takes ownership of the `TabStrip` as its scrollable contents,
- scrolls horizontally only (`SetHorizontalScrollBarMode(kHiddenButEnabled)`,
  vertical disabled), with the overflow fade indicator on,
- exposes `GetUnclippedTabStripWidth()` — the strip's full preferred width — for
  the available-width callback,
- maps a plain mouse wheel to horizontal scrolling (`OnMouseWheel`).

**Integration** (`integration/integrate.py`, anchored edits):
1. New feature flag `tabs::kHorizontalTabScrolling`, declared in `features.h` and
   defined `ENABLED_BY_DEFAULT` in `features.cc` (this fork ships it on).
2. `HorizontalTabStripRegionViewOld` construction: when the flag is on, wrap the
   strip in the scroll container and wire the available-width callback:
   ```cpp
   auto tab_strip = CreateTabStrip(this, browser_view);
   tab_strip_ = tab_strip.get();
   if (base::FeatureList::IsEnabled(tabs::kHorizontalTabScrolling)) {
     scroll_container_ = AddChildView(
         std::make_unique<HorizontalTabScrollContainer>(std::move(tab_strip)));
     tab_strip_->SetAvailableWidthCallback(base::BindRepeating(
         &HorizontalTabScrollContainer::GetUnclippedTabStripWidth,
         base::Unretained(scroll_container_)));
   } else {
     tab_strip_ = AddChildView(std::move(tab_strip));
   }
   ```
   `tab_strip_` stays valid in both paths, so every existing `tab_strip_->…`
   reference keeps working.
3. The FlexLayout `kFlexBehaviorKey` moves to whichever view is the direct child
   (the scroll container when scrolling, else the strip).
4. New-tab-button placement anchors on the outer flex child's right edge.
5. `chrome/browser/ui/BUILD.gn` gains the two new source entries.
6. `IsPositionInWindowCaption` hit-tests the scroll viewport before delegating to
   the nested tab strip.
7. `TabStrip::SetSelection` scrolls the active tab into view so keyboard
   shortcuts, session restore, and programmatic selection do not leave it hidden.

## Known follow-ups (the CI compile loop will surface these)

- **New-tab-button / caption / z-order coupling.** `Layout(PassKey)`,
  `IsPositionInWindowCaption`, and `GetChildrenInZOrder` are now handled by
  anchored edits and asserted by `integrate-check`; the CI compile loop is still
  the final signal for signature or include drift.
- **Drag auto-scroll.** Hook `DraggingTabsSession::MoveAttached` to scroll the
  viewport when a dragged tab nears an edge; drag-area geometry comes from
  `TabStrip::TabDragContextImpl::GetTabDragAreaWidth()`, which already special-
  cases scrolling. Not in the first pass.
- **Scroll active tab into view.** Implemented in `TabStrip::SetSelection` via
  `View::ScrollRectToVisible` on the newly active tab.
- **chrome://flags entry.** Implemented by the integrator as
  `chrome://flags/#horizontal-tab-scrolling`; `integrate-check` verifies the
  anchors against upstream HEAD.

## 2026 browser pain-point overlay roadmap

Phase 1: runtime profiles and docs for performance, privacy, AI/model-download
opt-out, and adblock/extension-manifest compatibility.

Phase 2: CI validation for runtime flag syntax, docs presence, and upstream
feature-name drift.

Phase 3: optional `chrome://flags` integration for fork builds where Chromium has
a supported feature path.

Phase 4: managed-policy templates for extension/adblock deployments.

## Why this survives rebases

The integration is anchored string edits, not line-context diffs, and CI's
`integrate-check` job re-binds those anchors against upstream HEAD on every push.
When a roll moves an anchor, the check goes red with the exact file and string to
fix, instead of a silent mis-apply.
