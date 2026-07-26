# Performance Defaults

Build-time baseline:

```bash
cp config/args.gn "$CHROMIUM_SRC/out/Default/args.gn"
```

Runtime baseline:

```bash
./scripts/print-flags.sh base performance
```

Principles:

- Avoid background services that make the browser feel noisy while idle.
- Avoid component/network warmups in the performance profile.
- Avoid AI/model downloads unless explicitly enabled.
- Keep horizontal tab scrolling enabled.
- Preserve normal web compatibility unless the privacy profile is explicitly
  selected.
