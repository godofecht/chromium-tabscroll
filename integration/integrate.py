#!/usr/bin/env python3
"""Wire the horizontal tab-scrolling rewrite into a Chromium 'src' checkout.

Uses anchored string edits keyed on exact upstream code rather than line-context
diffs, so it survives most upstream rolls and fails loudly (not silently) when an
anchor moves. Run from anywhere with CHROMIUM_SRC pointing at the checkout:

    CHROMIUM_SRC=/path/to/src python3 integrate.py

Required edits abort on a missing anchor. Best-effort edits warn and continue, so
a first build still happens and CI surfaces exactly what needs a manual touch.
"""
import os
import sys

SRC = os.environ.get("CHROMIUM_SRC", os.getcwd())


class Abort(Exception):
    pass


def edit(rel, anchor, payload, *, mode="after", required=True, once=True):
    """mode: 'after' | 'before' | 'replace' relative to `anchor`."""
    path = os.path.join(SRC, rel)
    if not os.path.isfile(path):
        msg = f"missing file: {rel}"
        if required:
            raise Abort(msg)
        print(f"  WARN  {msg} (skipped)")
        return
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if payload.strip() and payload.strip() in text:
        print(f"  skip  {rel}: already integrated")
        return
    n = text.count(anchor)
    if n == 0:
        msg = f"anchor not found in {rel}: {anchor!r}"
        if required:
            raise Abort(msg)
        print(f"  WARN  {msg} (skipped)")
        return
    if once and n > 1 and mode != "replace":
        print(f"  WARN  anchor appears {n}x in {rel}; editing first only")
    if mode == "after":
        new = text.replace(anchor, anchor + payload, 1)
    elif mode == "before":
        new = text.replace(anchor, payload + anchor, 1)
    elif mode == "replace":
        new = text.replace(anchor, payload, 1 if once else -1)
    else:
        raise Abort(f"bad mode {mode}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"  ok    {rel}")


FEATURES_H = "chrome/browser/ui/tabs/features.h"
FEATURES_CC = "chrome/browser/ui/tabs/features.cc"
BUILD_GN = "chrome/browser/ui/BUILD.gn"
ABOUT_FLAGS_CC = "chrome/browser/about_flags.cc"
FLAG_DESCRIPTIONS_H = "chrome/browser/flag_descriptions.h"
RV_H = "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.h"
RV_CC = "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.cc"
TAB_STRIP_CC = "chrome/browser/ui/views/tabs/tab_strip.cc"


def main():
    print(f">> integrating into {SRC}")

    # 1. Feature flag: declaration + definition, alongside kTabStripUnification.
    edit(FEATURES_H,
         "BASE_DECLARE_FEATURE(kTabStripUnification);",
         "\n\n// Lets the horizontal tab strip scroll sideways when tabs overflow,\n"
         "// instead of shrinking tabs to a minimum width.\n"
         "BASE_DECLARE_FEATURE(kHorizontalTabScrolling);",
         mode="after")
    edit(FEATURES_CC,
         "BASE_FEATURE(kTabStripUnification, base::FEATURE_DISABLED_BY_DEFAULT);",
         "\n\n// This fork ships tab scrolling on; upstream removed it in M144.\n"
         "BASE_FEATURE(kHorizontalTabScrolling, base::FEATURE_ENABLED_BY_DEFAULT);",
         mode="after")

    # 1b. chrome://flags entry: the feature is enabled by default in this fork,
    #     but a visible flag gives users a first-class escape hatch.
    edit(FLAG_DESCRIPTIONS_H,
         "inline constexpr char kTabStripUnificationName[] = \"Tab Strip Unification\";",
         "inline constexpr char kHorizontalTabScrollingName[] =\n"
         "    \"Horizontal tab scrolling\";\n"
         "inline constexpr char kHorizontalTabScrollingDescription[] =\n"
         "    \"Lets the horizontal tab strip scroll sideways when tabs overflow, \"\n"
         "    \"instead of shrinking every tab down to a minimum width.\";\n\n",
         mode="before")
    edit(ABOUT_FLAGS_CC,
         "    {\"tab-strip-unification\", flag_descriptions::kTabStripUnificationName,\n"
         "     flag_descriptions::kTabStripUnificationDescription, kOsDesktop,\n"
         "     FEATURE_VALUE_TYPE(tabs::kTabStripUnification)},",
         "    {\"horizontal-tab-scrolling\",\n"
         "     flag_descriptions::kHorizontalTabScrollingName,\n"
         "     flag_descriptions::kHorizontalTabScrollingDescription, kOsDesktop,\n"
         "     FEATURE_VALUE_TYPE(tabs::kHorizontalTabScrolling)},\n\n",
         mode="before")

    # 2. BUILD.gn: register the new files, alphabetically before tab_container.cc.
    edit(BUILD_GN,
         '      "views/tabs/tab_container.cc",',
         '      "views/tabs/horizontal_tab_scroll_container.cc",\n'
         '      "views/tabs/horizontal_tab_scroll_container.h",\n',
         mode="before")

    # 3. Region view header: forward-declare + member.
    edit(RV_H,
         "class TabStripScrollContainer;",
         "\nclass HorizontalTabScrollContainer;",
         mode="after", required=False)  # forward-decl block may have been cleaned up
    edit(RV_H,
         "raw_ptr<TabStrip> tab_strip_ = nullptr;",
         "\n  // Non-null only when kHorizontalTabScrolling is on; the viewport\n"
         "  // that hosts `tab_strip_` and scrolls it horizontally.\n"
         "  raw_ptr<HorizontalTabScrollContainer> scroll_container_ = nullptr;",
         mode="after")

    # 4. Region view impl: the new container header. base/feature_list.h,
    #    base/functional/bind.h and chrome/browser/ui/tabs/features.h are already
    #    included upstream; only the new header is missing. Placed alphabetically
    #    among the views/tabs/ includes (before hovercard/).
    edit(RV_CC,
         '#include "chrome/browser/ui/views/tabs/hovercard/tab_hover_card_controller.h"',
         '#include "chrome/browser/ui/views/tabs/horizontal_tab_scroll_container.h"\n',
         mode="before")

    # 5. Z-order: when scrolling, the direct child is the scroll container, not
    #    the (now nested) tab strip. List the real direct child so painting and
    #    z-order stay correct. Safe when scroll_container_ is null (flag off):
    #    the else branch keeps the original behavior.
    edit(RV_CC,
         "  if (tab_strip_) {\n"
         "    children.emplace_back(tab_strip_.get());\n"
         "  }",
         "  if (scroll_container_) {\n"
         "    children.emplace_back(scroll_container_.get());\n"
         "  } else if (tab_strip_) {\n"
         "    children.emplace_back(tab_strip_.get());\n"
         "  }",
         mode="replace", required=True)

    # 6. Caption hit-test: exclude the scroll container from the "treat as
    #    caption" fallback loop, the same way tab_strip_ is excluded, so an empty
    #    scrolled region stays window-draggable. No-op when scroll_container_ is
    #    null (child != nullptr is always true).
    edit(RV_CC,
         "    if (child != tab_strip_ && child != reserved_grab_handle_space_ &&",
         "    if (child != tab_strip_ && child != scroll_container_ &&\n"
         "        child != reserved_grab_handle_space_ &&",
         mode="replace", required=False)

    # 7. Caption hit-test: the tab strip is nested and wider than the visible
    #    viewport when scrolling is on. Hit-test the viewport first, then ask the
    #    tab strip about the converted rect.
    edit(RV_CC,
         "  if (IsHitInView(tab_strip_, point)) {\n"
         "    gfx::RectF rect_in_target_coords_f(gfx::Rect(point, gfx::Size(1, 1)));\n"
         "    View::ConvertRectToTarget(this, tab_strip_, &rect_in_target_coords_f);\n"
         "    return tab_strip_->IsRectInWindowCaption(\n"
         "        gfx::ToEnclosingRect(rect_in_target_coords_f));\n"
         "  }",
         "  views::View* tab_hit_view = scroll_container_\n"
         "                                  ? static_cast<views::View*>(scroll_container_)\n"
         "                                  : static_cast<views::View*>(tab_strip_);\n"
         "  if (IsHitInView(tab_hit_view, point)) {\n"
         "    gfx::RectF rect_in_target_coords_f(gfx::Rect(point, gfx::Size(1, 1)));\n"
         "    View::ConvertRectToTarget(this, tab_strip_, &rect_in_target_coords_f);\n"
         "    return tab_strip_->IsRectInWindowCaption(\n"
         "        gfx::ToEnclosingRect(rect_in_target_coords_f));\n"
         "  }",
         mode="replace", required=False)

    # 8. Selection changes from keyboard shortcuts, session restore, or scripts
    #    must reveal the active tab even when no wheel event has occurred.
    edit(TAB_STRIP_CC,
         "  // Notify all tabs whose selected state changed.\n"
         "  for (auto tab_index :\n"
         "       base::STLSetUnion<ui::ListSelectionModel::SelectedIndices>(\n"
         "           no_longer_selected, newly_selected)) {\n"
         "    tab_at(tab_index)->SelectedStateChanged();\n"
         "  }",
         "  // Notify all tabs whose selected state changed.\n"
         "  for (auto tab_index :\n"
         "       base::STLSetUnion<ui::ListSelectionModel::SelectedIndices>(\n"
         "           no_longer_selected, newly_selected)) {\n"
         "    tab_at(tab_index)->SelectedStateChanged();\n"
         "  }\n\n"
         "  new_active_tab->ScrollRectToVisible(new_active_tab->GetLocalBounds());",
         mode="replace")

    # 9. Do not create the Glic/Gemini tab-strip action container in this fork.
    #    It occupies the trailing/top-right tab-strip space users expect tabs to
    #    use. Leaving the local unique_ptr null makes the later AddChildView
    #    block a no-op without touching unrelated toolbar code.
    edit(RV_CC,
         "  // Add and configure the TabStripComboButton.\n"
         "  std::unique_ptr<TabStripActionContainer> tab_strip_action_container;\n"
         "  if (browser &&\n"
         "      (browser->GetType() == BrowserWindowInterface::Type::TYPE_NORMAL)) {\n"
         "    // The Glic button visibility is dynamic and depends on profile state\n"
         "    // (e.g., sign-in status, enterprise policies, recoverable errors).\n"
         "    // We instantiate the action container if the profile is eligible (even if\n"
         "    // the button is not currently shown, e.g. when signed out) so that it can\n"
         "    // dynamically update its visibility when the profile state changes.\n"
         "    if (glic::GlicEnabling::IsProfileEligible(profile())) {\n"
         "      tab_strip_action_container =\n"
         "          std::make_unique<TabStripActionContainer>(browser);\n"
         "      tab_strip_action_container->SetProperty(views::kCrossAxisAlignmentKey,\n"
         "                                              views::LayoutAlignment::kStart);\n"
         "    }\n"
         "  }",
         "  // This fork gives the horizontal tab strip the trailing space instead of\n"
         "  // instantiating the Glic/Gemini action container there.\n"
         "  std::unique_ptr<TabStripActionContainer> tab_strip_action_container;",
         mode="replace",
         required=False)

    print(">> base edits done")


# The construction-block replacement needs a multi-line payload; do it directly.
def replace_construction():
    path = os.path.join(SRC, RV_CC)
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if "scroll_container_ = AddChildView(" in text:
        print("  skip  region-view construction: already wired")
        return
    anchor = "tab_strip_ = AddChildView(CreateTabStrip(this, browser_view));"
    if anchor not in text:
        raise Abort(f"construction anchor not found in {RV_CC}")
    payload = (
        "{\n"
        "    auto tab_strip = CreateTabStrip(this, browser_view);\n"
        "    tab_strip_ = tab_strip.get();\n"
        "    if (base::FeatureList::IsEnabled(tabs::kHorizontalTabScrolling)) {\n"
        "      scroll_container_ = AddChildView(\n"
        "          std::make_unique<HorizontalTabScrollContainer>(\n"
        "              std::move(tab_strip)));\n"
        "      // Report the full, unclipped tab-row width so tabs keep their\n"
        "      // size and overflow the viewport rather than shrinking.\n"
        "      tab_strip_->SetAvailableWidthCallback(base::BindRepeating(\n"
        "          &HorizontalTabScrollContainer::GetUnclippedTabStripWidth,\n"
        "          base::Unretained(scroll_container_)));\n"
        "    } else {\n"
        "      tab_strip_ = AddChildView(std::move(tab_strip));\n"
        "    }\n"
        "  }"
    )
    text = text.replace(anchor, payload, 1)

    # With tab scrolling enabled, do not reserve a trailing grab-handle block
    # between the tab strip and the window controls. That empty region is what
    # makes tabs stop before the right edge even after removing the action
    # container. Keep upstream behavior when the feature is disabled.
    grab_anchor = (
        "  reserved_grab_handle_space_ =\n"
        "      AddChildView(std::make_unique<FrameGrabHandle>());\n"
        "  reserved_grab_handle_space_->SetProperty(\n"
        "      views::kFlexBehaviorKey,\n"
        "      views::FlexSpecification(views::MinimumFlexSizeRule::kPreferred,\n"
        "                               views::MaximumFlexSizeRule::kUnbounded)\n"
        "          .WithOrder(3));"
    )
    if grab_anchor in text:
        grab_payload = (
            "  if (!base::FeatureList::IsEnabled(tabs::kHorizontalTabScrolling)) {\n"
            "    reserved_grab_handle_space_ =\n"
            "        AddChildView(std::make_unique<FrameGrabHandle>());\n"
            "    reserved_grab_handle_space_->SetProperty(\n"
            "        views::kFlexBehaviorKey,\n"
            "        views::FlexSpecification(views::MinimumFlexSizeRule::kPreferred,\n"
            "                                 views::MaximumFlexSizeRule::kUnbounded)\n"
            "            .WithOrder(3));\n"
            "  }")
        text = text.replace(grab_anchor, grab_payload, 1)
    else:
        print(f"  WARN  grab-handle reservation anchor not found in {RV_CC}; "
              "verify trailing tab-strip space")

    # Apply the flex spec to whichever view is the FlexLayout child.
    flex_anchor = ("tab_strip_->SetProperty(views::kFlexBehaviorKey, "
                   "tab_strip_flex_spec);")
    if flex_anchor in text:
        flex_payload = (
            "views::View* tab_strip_flex_child =\n"
            "      scroll_container_ ? static_cast<views::View*>(scroll_container_)\n"
            "                        : static_cast<views::View*>(tab_strip_);\n"
            "  tab_strip_flex_child->SetProperty(views::kFlexBehaviorKey, "
            "tab_strip_flex_spec);")
        text = text.replace(flex_anchor, flex_payload, 1)
    else:
        print(f"  WARN  flex-spec anchor not found in {RV_CC}; set it by hand")

    # Best-effort: anchor the new-tab button to the outer flex child, not the
    # (now nested) tab strip. Safe no-op if the layout math changed upstream.
    ntb_anchor = "tab_strip_->bounds().right()"
    if ntb_anchor in text:
        text = text.replace(
            ntb_anchor,
            "(scroll_container_ ? scroll_container_->bounds().right()\n"
            "                            : tab_strip_->bounds().right())")
    else:
        print("  WARN  new-tab-button anchor (tab_strip_->bounds().right()) not "
              "found; verify NTB placement under scrolling")

    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  ok    {RV_CC}: construction wired")


if __name__ == "__main__":
    try:
        main()
        replace_construction()
    except Abort as e:
        print(f"ABORT: {e}", file=sys.stderr)
        sys.exit(1)
