# Pokémon Pink

> Port of jcferggy's *Pokémon Pink Version: Special Clefairy Edition*, made with
> his permission. The original is on [PokéCommunity](https://www.pokecommunity.com/threads/pok%C3%A9mon-pink-version-special-clefairy-edition-ue.542531/).

A custom cart for the LOVE2D Pokemon engine: a pinned mod setup that plays as
its own game on top of `yellow`. It ships no code -- every mod named here is
published separately, and the cart pins each one to an exact build.

## Files

- `cart.json` - identity, base game, seal, and one pin per mod
- `label.png` - the cart label art the launcher draws
- `.github/workflows/release.yml` - packs and publishes on a `v*` tag

## Beta

This is **0.1.0-beta.2**, a work-in-progress beta. Testers can compare what
they see against the
[beta walkthrough](https://github.com/ElvieBlooms/pokepink-g1r/blob/main/docs/WALKTHROUGH.md)
and report anything that doesn't match.

## The Pink mods

All eleven come from release `v0.3.1` of `ElvieBlooms/pokepink-g1r`, so
they share a version. `load_order` runs `pink_partner` first and the other
Pink mods after it, then `recomp_achievements` before `pink_achievements`,
and `facets` before `pink_look_picker`, so PRISM exists when Oak offers it.

To move pins to new releases, reading each release's `sha256sums.txt` (or
downloading the zip and hashing it when there isn't one), with only Python 3:

```sh
python3 tools/repin.py                              # every GitHub pin to its latest release
python3 tools/repin.py pokepink-g1r=0.3.1           # one repo or mod id to a set version
python3 tools/repin.py --add ElvieBlooms/name_tags  # pin another mod
python3 tools/repin.py --cart-version 0.1.0-beta.3 --dry-run
```

## The other mods and their starting settings

The cart is `open`: pinned options are where a player starts, and the
player's own choices in the Mods manager win over them (a sealed cart would
freeze them). Open also lets players add mods of their own.

Besides the Pink mods (including `pink_look_picker`, which has Oak offer
PRISM at NEW GAME, and `pink_achievements`, Pink's own achievement list),
the cart pins:

| Mod | Starting settings |
|---|---|
| `recomp_achievements` (pinned at 2.8.0) | `classicMenu=true` (the CLASSIC MENU look), `menuTheme=gruvbox_light`, `popupStyle=corner`; it plays Pink's own list on this cart, on the `pokepink` board |
| `facets` (pinned at 1.2.4, which has the PINK and PINK WOOD window sets) | `classicMons=gb_crystal` (Crystal's animated Pokemon), `animMode=loop`, `classicIcons=minidex`, `classicWindows=pink:3` (PINK BLUSH), `classicTextBox=pinkwood:1` (PINK WOOD ROSE), `classicClefairy=pink` (GAME: Pink's own Clefairy) |
| `emerald_lens` (pinned at 1.1.1) | `characterGb1=DAWN`, `lookGb1_DAWN=dawn_hikari` (Dawn, HIKARI look) |

These are the settings from Elvie's own playtest. Facets' other rows (COLORS,
YOUR SIDE, SCENE COLOURS, BORDERS) were on their defaults, so they aren't
pinned.

```sh
python3 tools/cartkit.py pin . ElvieBlooms/facets@X.Y.Z --option classicMons=gb_crystal --option animMode=loop --option classicIcons=minidex --option classicWindows=pink:3 --option classicTextBox=pinkwood:1 --option classicClefairy=pink
python3 tools/cartkit.py pin . ElvieBlooms/emerald_lens@X.Y.Z --option characterGb1=DAWN --option lookGb1_DAWN=dawn_hikari
python3 tools/cartkit.py pin . ElvieBlooms/recomp_achievements@X.Y.Z --option classicMenu=true --option menuTheme=gruvbox_light --option popupStyle=corner
```

Pink's Super Game Boy border isn't part of the cart: a cart can't carry a
skin, so `pink_sgb_border.zip` from the Pink mods' release goes beside it,
installed from the launcher's SKINS tab.

Crystal's pictures come from the player's own Crystal, Gold or Silver
import; without one, those Pokemon keep the game's own pictures.

## Loop

Every command below is `tools/cartkit.py` from a gen1recomp checkout, pointed
at this directory.

1. pin a mod:

   ```sh
   python3 tools/cartkit.py pin . owner/repo@1.2.3
   python3 tools/cartkit.py pin . https://gamebanana.com/mods/546899
   ```

2. freeze an option the player inherits:

   ```sh
   python3 tools/cartkit.py pin . owner/repo@1.2.3 --option difficulty=hard
   ```

3. check it, hashes and all:

   ```sh
   python3 tools/cartkit.py validate . --online
   ```

4. build the bundle players load:

   ```sh
   python3 tools/cartkit.py pack .
   ```

`seal` is `open`: the player can add mods on top, and their own option
choices win over the pins. A sealed cart would load exactly the pinned mods
and freeze their options.

## Releasing

Bump `version` in `cart.json`, tag it `v<version>`, and push the tag. The
workflow validates, packs, and attaches `pokepink-<version>.g1rcart` to the
release.

## License

[MIT](LICENSE) for this cart's own files. The pinned mods and the Pokémon Pink
content they recreate carry their own credits; see
[pokepink-g1r](https://github.com/ElvieBlooms/pokepink-g1r).
