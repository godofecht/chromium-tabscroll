// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#ifndef CHROME_BROWSER_UI_VIEWS_TABS_HORIZONTAL_TAB_SCROLL_CONTAINER_H_
#define CHROME_BROWSER_UI_VIEWS_TABS_HORIZONTAL_TAB_SCROLL_CONTAINER_H_

#include <memory>

#include "base/memory/raw_ptr.h"
#include "ui/base/metadata/metadata_header_macros.h"
#include "ui/views/controls/scroll_view.h"

namespace ui {
class MouseWheelEvent;
}  // namespace ui

class TabStrip;

// A horizontal viewport that hosts the `TabStrip` and lets the row of tabs
// overflow and scroll sideways instead of shrinking to a minimum width.
//
// Background: `TabContainerImpl` normally lays tabs out within the width handed
// to it by `TabContainer::GetAvailableWidthForTabContainer()`, shrinking tabs
// toward a minimum when there are too many. That width comes from an optional
// callback (`TabStrip::SetAvailableWidthCallback`); when the callback is unset,
// it falls back to the parent's allocated width, which forces shrinking.
//
// This container is inserted between `HorizontalTabStripRegionViewOld`'s
// FlexLayout and the `TabStrip` when `tabs::kHorizontalTabScrolling` is enabled.
// It supplies an available-width callback that reports the tab strip's full,
// unclipped preferred width, so tabs keep their normal size, overflow the
// viewport, and scroll horizontally.
//
// This is an additive layer over the current (Old) tabstrip. It deliberately
// does not resurrect the pre-2025 `TabStripScrollContainer`; that code targeted
// a tab data model that no longer exists.
class HorizontalTabScrollContainer : public views::ScrollView {
  METADATA_HEADER(HorizontalTabScrollContainer, views::ScrollView)

 public:
  explicit HorizontalTabScrollContainer(std::unique_ptr<TabStrip> tab_strip);
  HorizontalTabScrollContainer(const HorizontalTabScrollContainer&) = delete;
  HorizontalTabScrollContainer& operator=(const HorizontalTabScrollContainer&) =
      delete;
  ~HorizontalTabScrollContainer() override;

  TabStrip* tab_strip() { return tab_strip_; }
  const TabStrip* tab_strip() const { return tab_strip_; }

  // The width the `TabStrip` should lay its tabs out within: its full preferred
  // width, so tabs keep full size and overflow rather than shrink. Bound into
  // `TabStrip::SetAvailableWidthCallback` by the region view.
  int GetUnclippedTabStripWidth() const;

  // views::View:
  bool OnMouseWheel(const ui::MouseWheelEvent& event) override;

 private:
  // Owned by the ScrollView contents; destroyed with this view.
  raw_ptr<TabStrip> tab_strip_ = nullptr;
};

#endif  // CHROME_BROWSER_UI_VIEWS_TABS_HORIZONTAL_TAB_SCROLL_CONTAINER_H_
