## Plugins

Plugins live under `nofal-panel/plugins/<plugin_name>/`.

Each plugin should contain:
- `manifest.json`
- `plugin.py` (must expose `get_router()` and optionally `register(event_bus)`)

Plugins are mounted automatically under `/plugins/<plugin_name>` when enabled in DB.

