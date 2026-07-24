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
RV_H = "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.h"
RV_CC = "chrome/browser/ui/views/frame/horizontal_tab_strip_region_view.cc"


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

    # 5. Region view impl construction wiring is a multi-line replacement handled
    #    by replace_construction() below.
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
