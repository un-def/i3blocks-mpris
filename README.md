i3blocks-spotify-persist
========================

Persistent (daemonized) [i3blocks][i3blocks] blocklet for Spotify desktop app.

[![screenshot][screenshot]][screencast]

Click image above to watch [screencast][screencast].


**NOTE**: Mouse click event is now supported thanks to [i3blocks 1.5][i3blocks-1.5].


### Requirements

* Python 3
* [PyGObject][pygobject]
* [dbus-python][dbus-python]
* Font Awesome (for status icons, optional)


### Usage

Add the following lines to your i3blocks config:

```
[spotify]
command=/path/to/i3blocks-spotify-persist/spotify [-c /path/to/config.json]
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


[screenshot]: https://tinystash.undef.im/il/AU5kR3crkLj8DR3ktsYfSDjheg8boJp3GtYDRsHctmns.png
[screencast]: https://tinystash.undef.im/il/7oosxeZ2TK2EmuV4MbvbTXtZocXnK7fy9DLnhRs89gmq.webm
[i3blocks]: https://github.com/vivien/i3blocks
[i3blocks-1.5]: https://github.com/vivien/i3blocks/releases/tag/1.5
[dbus-python]: https://pypi.org/project/dbus-python/
[pygobject]: https://pygobject.readthedocs.io/en/latest/
[playerctl]: https://github.com/acrisci/playerctl
[reddit-playerctl-examples]: https://reddit.com/comments/82ybqj/_/dvf7z5x/
