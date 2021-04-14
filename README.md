# i3blocks-mpris

A persistent [i3blocks][i3blocks] blocklet for the [MPRIS][mpris-spec] D-Bus interface.

[![screenshot][screenshot]][screencast]

Click the image above to watch a [screencast][screencast].

This project was previously known as **i3blocks-spotify-persist**.


## Features

* near-immediate updates thanks to the event-driven model: the blocket is a constantly running process receiving D-Bus signals
* configurable output
* configurable mouse click actions (i3blocks [version 1.5][i3blocks-1.5] or later is required)


## Installation

**Python version 3.6 or later is required.**

The blocket can be installed from PyPI using `pip`:

```shell
python3 -m pip install [--user] i3blocks-mpris
```

Once the package is installed, there will be a blocket script named `i3blocks-mpris` somewhere depending on the presence of a `--user` pip flag (e.g., `/usr/local/bin/i3blocks-mpris` or `~/.local/bin/i3blocks-mpris`).

To avoid dependecy hell, [pipx][pipx] can be used:

```shell
pipx install i3blocks-mpris
```

In this case the blocket script will be placed in `~/.local/bin` directory.


## Dependencies

Required (installed automatically):
  * [PyGObject][pygobject]
  * [dbus-python][dbus-python]

Optional (installed manually):
  * [Font Awesome][font-awesome] (for status icons)


## Usage

Add the following lines to your i3blocks config:

```
[mpris]
command=/path/to/bin/i3blocks-mpris -c /path/to/config.json
interval=persist
```


## Configuration

The blocket can be configured using a JSON config file and/or command line arguments. The only required parameter is `player`. It must be specified using either the config or the command line argument. Other config parameters and the config itself are optional.

### Config parameters

#### player

*Type:* string

*Default value:* no default value, must be specified

A name of the player, either a full bus name — `org.mpris.MediaPlayer2.<player>[.<instance>]` — or its `<player>[.<instance>]` part.

Examples:

  * org.mpris.MediaPlayer2.spotify
  * org.mpris.MediaPlayer2.vlc.instance7389
  * spotify
  * vlc.instance7389

#### format

*Type:* string

*Default value:* `{status}: {artist} – {title}`

A template string with placeholders. Placeholder formats are `{field}` and `{field:filter}`.

Supported fields:

  * `status`, one of [enum][mpris-playbackstatus-type] values: `Playing`, `Paused`, `Stopped`
  * `artist`
  * `title`

Supported fitlers:

  * `upper` — converts a string to uppercase
  * `lower` — converts a string to lowercase
  * `capitalize` — converts the first character of a string to uppercase and the rest to lowercase
  * `icon` — for `status` field only: converts a textual status to an icon (see the `status_icons` option below)

#### markup_escape

*Type:* boolean

*Default value:* `false`

This option specifies whether to escape special characters (such as `<`, `>`, `&`) using corresponding XML entities. Set to `true` if Pango markup is used (`markup=pango` in your `i3blocks` config), `false` otherwise.

#### status_icons

*Type:* object

*Default value:* `{"Playing": "\uf04b", "Paused": "\uf04c", "Stopped": "\uf04d"}`

This option provides a mapping for the `icon` filter (see above). The default value uses icons from [Font Awesome][font-awesome].

#### mouse_buttons

*Type:* object

*Default value:* `{"1": "PlayPause"}`

This option provides a mapping of X11 mouse buttons numbers to [MPRIS methods][mpris-methods]. You can use the `xev` program to determine button numbers.

#### dedupe

*Type:* boolean

*Default value:* `true`

For some reason, the Spotify app emits several identical signals for one action/event (e.g., it produces **four** `PropertiesChanged` signals when a track is played or paused). If this option is set `true`, the blocklet will compare the updated message with the previous one and print it only if it has changed. There is no reason to turn off deduplication except for debugging.

### Config example

```json
{
    "player": "spotify",
    "format": "<span font_family='monospace' color='#ffa651' weight='bold'>{status:icon} {status:upper}</span> <span color='#72bf44' weight='bold'>{artist}</span><span color='#ffa651'>᛫</span><span color='#b2d235'>{title}</span>",
    "markup_escape": true,
    "status_icons": {
        "Playing": "|>",
        "Paused": "||",
        "Stopped": "[]"
    },
    "mouse_buttons": {
        "1": "PlayPause",
        "9": "Previous",
        "8": "Next"
    }
}

```


## Command line arguments

  * `-h`, `--help` — show all command line arguments and exit
  * `-c`, `--config` — a path to the config file (see above)

The following arguments override corresponding config options or defaults (that is, command line arguments have the highest precedence):

  * `-p`, `--player`
  * `--format`
  * `--markup-escape` / `--no-markup-escape`
  * `--dedupe` / `--no-dedupe`


## Changelog

See [CHANGELOG.md][changelog].


## License

The [MIT License][license].


[screenshot]: https://tinystash.undef.im/il/3wQUgnuCRyADYHZ4Vi6qN29p65njk1DdsjUu5WePUBNmUak7Z9y6CqNRnEzMN2pVBVsZvBDJ9GDyJUGGYd3Fgbqd.png
[screencast]: https://tinystash.undef.im/il/2Xscwkh3rAhw2iqSr9XxJ2Meph57eXiHwkkWiAgroiuGPXB9fYnPJqgdYR7nR4B9U5hHvxxGtr8Sc3QaquwjHT38.mp4
[license]: https://github.com/un-def/i3blocks-mpris/blob/master/LICENSE
[changelog]: https://github.com/un-def/i3blocks-mpris/blob/master/CHANGELOG.md
[i3blocks]: https://github.com/vivien/i3blocks
[i3blocks-1.5]: https://github.com/vivien/i3blocks/releases/tag/1.5
[dbus-python]: https://dbus.freedesktop.org/doc/dbus-python/
[pygobject]: https://pygobject.readthedocs.io/en/latest/
[font-awesome]: https://fontawesome.com/
[pipx]: https://pipxproject.github.io/pipx/
[mpris-spec]: https://specifications.freedesktop.org/mpris-spec/latest/
[mpris-playbackstatus-type]: https://specifications.freedesktop.org/mpris-spec/latest/Player_Interface.html#Enum:Playback_Status
[mpris-methods]: https://specifications.freedesktop.org/mpris-spec/latest/Player_Interface.html#methods
