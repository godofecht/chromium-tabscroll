// Copyright 2026 The Chromium Authors
// Use of this source code is governed by a BSD-style license that can be
// found in the LICENSE file.

#include "chrome/browser/ui/views/tabs/horizontal_tab_scroll_container.h"

#include <algorithm>
#include <optional>
#include <utility>

#include "chrome/browser/ui/views/tabs/tab_strip.h"
#include "ui/base/metadata/metadata_impl_macros.h"
#include "ui/events/event.h"
#include "ui/gfx/geometry/rect.h"

HorizontalTabScrollContainer::HorizontalTabScrollContainer(
    std::unique_ptr<TabStrip> tab_strip) {
  // Scroll horizontally only. The strip's height is fixed to the tab height by
  // the region view's layout, so no vertical scrolling should ever occur.
  SetHorizontalScrollBarMode(
      views::ScrollView::ScrollBarMode::kHiddenButEnabled);
  SetVerticalScrollBarMode(views::ScrollView::ScrollBarMode::kDisabled);
  // Draw the fade indicator at the overflowing edge(s) so it's clear more tabs
  // exist off-screen.
  SetDrawOverflowIndicator(true);
  // Inherit the tabstrip background rather than painting an opaque fill.
  SetBackgroundColor(std::nullopt);

  tab_strip_ = SetContents(std::move(tab_strip));
}

HorizontalTabScrollContainer::~HorizontalTabScrollContainer() = default;

int HorizontalTabScrollContainer::GetUnclippedTabStripWidth() const {
  // The tab strip's intrinsic preferred width (all tabs at full size). This is
  // independent of the available-width callback, so reading it here does not
  // recurse: TabContainerImpl::CalculatePreferredSize() is driven by the layout
  // helper, not by GetAvailableWidthForTabContainer().
  return tab_strip_ ? tab_strip_->GetPreferredSize().width() : 0;
}

bool HorizontalTabScrollContainer::OnMouseWheel(
    const ui::MouseWheelEvent& event) {
  // Map a plain vertical mouse wheel onto horizontal tab scrolling, so a normal
  // wheel scrolls the strip. Trackpads and shift+wheel already produce an
  // x_offset, which we honor directly.
  const int delta = event.x_offset() != 0 ? event.x_offset() : event.y_offset();
  if (delta == 0 || !contents()) {
    return views::ScrollView::OnMouseWheel(event);
  }

  const gfx::Rect visible = GetVisibleRect();
  const int max_x = std::max(0, contents()->width() - visible.width());
  // Wheel-up (positive offset) reveals earlier tabs, i.e. scroll content right.
  const int new_x = std::clamp(visible.x() - delta, 0, max_x);
  contents()->ScrollRectToVisible(
      gfx::Rect(new_x, 0, visible.width(), contents()->height()));
  return true;
}

BEGIN_METADATA(HorizontalTabScrollContainer)
END_METADATA
