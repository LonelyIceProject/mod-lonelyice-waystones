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

None besides the core. Translocation is a spell of its own, described in `data/patches.json`: the installer of
[LonelyIce](https://github.com/LonelyIceProject/lonelyice) gives it a free spell id, adds it to the server (`spell_dbc`)
and builds the client patch from your own client, so no game data is shipped here.

## Install

This module is written for [LonelyIceProject/azerothcore-wotlk](https://github.com/LonelyIceProject/azerothcore-wotlk),
a fork of AzerothCore with runtime plugins, and builds in two ways.

**As a plugin** (the core built with `-DWITH_DYNAMIC_LINKING=ON`):

```
cmake -S azerothcore-wotlk -B build -DWITH_DYNAMIC_LINKING=ON -DWITH_PLAYERBOTS_HOOKS=ON ^
      -DAC_PLUGIN_ABI=lonelyice-ac-2 "-DAC_PLUGIN_SOURCE_DIRS=<path>/mod-playerbots;<path>/mod-lonelyice-waystones"
cmake --build build --config RelWithDebInfo
```

The plugin is laid out in `bin/<config>/plugins/lonelyice.waystones/`. Copy that folder into the server's `plugins` folder
(`PluginsDir` in worldserver.conf); [LonelyIce](https://github.com/LonelyIceProject/lonelyice) does this for you.

**As a classic static module**: clone into `modules/mod-lonelyice-waystones` of the core and rebuild.
## Client files

- `client/addons/KirinTorWaystones` goes into `Interface/AddOns`.
- `tools/make_waystones.py` regenerates the crystal spawns (`data/sql/db-world`) and the addon data from the
  world database and the client DBCs. It reads
  `WOW_CLIENT` (game folder), `WOW_SERVER_DATA` (server data folder) and `WOW_WORLD_DB` (world.sqlite), and
  need StormLib for MPQ access.
## Support

LonelyIce is free, with no ads and no paid features. If it is useful to you, you can
[buy me a coffee](https://buymeacoffee.com/darthgelum): it pays for the server, code signing and development time.

<a href="https://buymeacoffee.com/darthgelum"><img src=".github/buy-me-a-coffee.png" alt="Buy me a coffee" width="303"></a>

## License

GNU General Public License v2.0 or later, see [LICENSE](LICENSE). Part of the
[LonelyIce](https://github.com/LonelyIceProject/lonelyice) single-player project.

### Blizzard Entertainment

World of Warcraft®, Warcraft®, Wrath of the Lich King® and Blizzard Entertainment® are trademarks or registered
trademarks of Blizzard Entertainment, Inc. in the U.S. and/or other countries.

The game and everything in it belong to Blizzard Entertainment, Inc.: the game client and its program files, data
files and archives, maps and terrain, models, textures, art, animations, interface, music, sounds, voices, texts,
names, lore, characters, creatures, spells, items, quests and every other part of the game. All of it remains
Blizzard's property wherever it appears, including the data a server extracts from your client on your own computer
(game tables, maps, collision and navigation data).

LonelyIce is an unofficial, non-commercial fan project. It is not affiliated with, endorsed, sponsored, approved or
supported by Blizzard Entertainment, Inc. Blizzard's names are used only to say which game client the project works
with.

This repository contains no files from the game client, and LonelyIce neither distributes nor downloads any. It works
only with a copy of the game you already own. Keep the data extracted from your client to yourself: it is Blizzard's
property and is not ours or yours to share.

The license above covers only the code and files of this project and the works it is based on. It grants no rights
to anything that belongs to Blizzard Entertainment, Inc. All other trademarks belong to their respective owners.
