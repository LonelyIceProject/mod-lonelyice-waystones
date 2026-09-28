<p align="center"><img src="logo.png" width="128" alt="logo"></p>

# mod-lonelyice-waystones

Kirin Tor waycrystals: a teleport network in the spirit of Final Fantasy XIV aetherytes.

## Features

- A waycrystal floats next to every inn and flight master of the four continents.
- Walking up to a crystal attunes the character to it for good.
- Talking to any crystal offers a translocation to every attuned one; the *KirinTorWaystones* addon also shows
  the crystals on the world map and translocates from anywhere by a click.
- Translocation is a 5 s cast that movement, combat and damage interrupt.

## Requirements

None besides the core. The translocation spell looks right in the client only with the client patch built by
`tools/make_client_patch.py` from your own client (game data is never shipped here).
## Install

This module is written for [LonelyIceProject/azerothcore-wotlk](https://github.com/LonelyIceProject/azerothcore-wotlk),
a fork of AzerothCore with runtime plugins, and builds in two ways.

**As a plugin** (the core built with `-DWITH_DYNAMIC_LINKING=ON`):

```
cmake -S azerothcore-wotlk -B build -DWITH_DYNAMIC_LINKING=ON -DWITH_PLAYERBOTS_HOOKS=ON ^
      -DAC_PLUGIN_ABI=lonelyice-ac-1 "-DAC_PLUGIN_SOURCE_DIRS=<path>/mod-playerbots;<path>/mod-lonelyice-waystones"
cmake --build build --config RelWithDebInfo
```

The plugin is laid out in `bin/<config>/plugins/lonelyice.waystones/`. Copy that folder into the server's `plugins` folder
(`PluginsDir` in worldserver.conf); [LonelyIce](https://github.com/LonelyIceProject/lonelyice) does this for you.

**As a classic static module**: clone into `modules/mod-lonelyice-waystones` of the core and rebuild.
## Client files

- `client/addons/KirinTorWaystones` goes into `Interface/AddOns`.
- `tools/make_waystones.py` regenerates the crystal spawns (`data/sql/db-world`) and the addon data from the
  world database and the client DBCs; `tools/make_client_patch.py` builds the client patch. Both read
  `WOW_CLIENT` (game folder), `WOW_SERVER_DATA` (server data folder) and `WOW_WORLD_DB` (world.sqlite), and
  need StormLib for MPQ access.
## License

GNU General Public License v2.0 or later, see [LICENSE](LICENSE). Part of the
[LonelyIce](https://github.com/LonelyIceProject/lonelyice) single-player project.
