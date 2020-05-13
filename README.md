i3blocks-spotify-persist
========================

A persistent [i3blocks][i3blocks] blocklet for the Spotify desktop app

[![screenshot][screenshot]][screencast]

Click the image above to watch a [screencast][screencast].


## Features

* near-immediate updates thanks to the event-driven model: the blocket is a constantly running process receiving D-Bus signals
* configurable output
* configurable mouse click actions (i3blocks [version 1.5][i3blocks-1.5] or later is required)


## Installation

**Python version 3.5 or later is required.**

The blocket can be installed from PyPI using `pip`:

```shell
python3 -m pip install [--user] i3blocks-spotify-persist
```

Once the package is installed, there will be a blocket script named `i3blocks-spotify-persist` somewhere depending on the presence of a `--user` pip flag (e.g., `/usr/local/bin/i3blocks-spotify-persist` or `~/.local/bin/i3blocks-spotify-persist`).

To avoid dependecy hell, [pipx][pipx] can be used:

```shell
pipx install i3blocks-spotify-persist
```

In this case the blocket script will be placed in `~/.local/bin` directory.


### Dependencies

Required (installed automatically):
* [PyGObject][pygobject]
* [dbus-python][dbus-python]

Optional (installed manually):
* Font Awesome (for status icons)


### Usage

Add the following lines to your i3blocks config:

```
[spotify]
command=/path/to/bin/i3blocks-spotify-persist [-c /path/to/config.json]
interval=persist
...
```

### Config example

```json
{
    "format": "<span font_family='monospace' color='#ffa651' weight='bold'>{status:icon} {status:upper}</span> <span color='#72bf44' weight='bold'>{artist}</span><span color='#ffa651'>᛫</span><span color='#b2d235'>{title}</span>",
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

See blocket source code comments for all config options and their description.


[screenshot]: https://tinystash.undef.im/il/3wQUgnuCRyADYHZ4Vi6qN29p65njk1DdsjUu5WePUBNmUak7Z9y6CqNRnEzMN2pVBVsZvBDJ9GDyJUGGYd3Fgbqd.png
[screencast]: https://tinystash.undef.im/il/2Xscwkh3rAhw2iqSr9XxJ2Meph57eXiHwkkWiAgroiuGPXB9fYnPJqgdYR7nR4B9U5hHvxxGtr8Sc3QaquwjHT38.mp4
[i3blocks]: https://github.com/vivien/i3blocks
[i3blocks-1.5]: https://github.com/vivien/i3blocks/releases/tag/1.5
[dbus-python]: https://pypi.org/project/dbus-python/
[pygobject]: https://pygobject.readthedocs.io/en/latest/
[pipx]: https://pipxproject.github.io/pipx/
