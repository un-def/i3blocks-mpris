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
* Font Awesome


### Usage

Add the following lines to your i3blocks config:

```
[spotify]
command=/path/to/i3blocks-spotify-persist/spotify
interval=persist
...
```


[screenshot]: https://tinystash.undef.im/il/AU5kR3crkLj8DR3ktsYfSDjheg8boJp3GtYDRsHctmns.png
[screencast]: https://tinystash.undef.im/il/7oosxeZ2TK2EmuV4MbvbTXtZocXnK7fy9DLnhRs89gmq.webm
[i3blocks]: https://github.com/vivien/i3blocks
[i3blocks-1.5]: https://github.com/vivien/i3blocks/releases/tag/1.5
[dbus-python]: https://pypi.org/project/dbus-python/
[pygobject]: https://pygobject.readthedocs.io/en/latest/
[playerctl]: https://github.com/acrisci/playerctl
[reddit-playerctl-examples]: https://reddit.com/comments/82ybqj/_/dvf7z5x/
