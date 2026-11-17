# Design (canvas UI)

- `canvas/` – the artboards of the design canvas (desktop + mobile, `.dc.html`) and `canvas.json` layout.
- `source/` – the generator: `kit.py` (shared CSS, haptic logic, icons, blocks) and `build.py` (all screens).

Rebuild after changing the kit or data:

```bash
cd design/source && python3 build.py ../canvas
```

All brand, hospital and community names / numbers in the design are illustrative (fictional).
