# Ad Blocking And Extension Manifest Policy

This repo does not bundle blocklists or third-party extensions. It keeps the
browser overlay honest about extension-manifest compatibility and gives managed
installs a place to document policy choices.

Recommended paths:

- Use builds that still permit Manifest V2 only where legally and technically
  allowed.
- Prefer managed policy files when you control the install.
- Keep uBlock Origin Lite as the MV3-compatible baseline.
- For full uBlock Origin MV2 testing, use an unpacked extension profile and
  explicit compatibility flags.

Runtime profile:

```bash
./scripts/print-flags.sh adblock-friendly
```

Policy locations vary by distribution:

- Linux: `/etc/chromium/policies/managed/`
- macOS: app bundles vary; follow the policy docs for the exact Chromium build.
- Windows: registry or policy JSON, depending on distribution.

The toolkit checks syntax and drift. It does not promise that upstream Chromium
will continue honoring every MV2 compatibility path forever.
