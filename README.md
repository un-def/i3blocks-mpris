i3blocks-spotify-persist
========================

Persistent (daemonized) [i3blocks][i3blocks] blocklet for Spotify desktop app.

[![screenshot][screenshot]][screencast]

Click image above to watch [screencast][screencast].


**NOTE**: running the blocklet as a daemon allows us to update status/track information instantly, but due to [i3blocks limitation][i3blocks-issue] we can not handle mouse click events 😞 You can use [playerctl][playerctl] to control Spotify app, see [this Reddit comment][reddit-playerctl-examples] for examples.


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
[i3blocks-issue]: https://github.com/vivien/i3blocks/issues/228
[dbus-python]: https://pypi.org/project/dbus-python/
[pygobject]: https://pygobject.readthedocs.io/en/latest/
[playerctl]: https://github.com/acrisci/playerctl
[reddit-playerctl-examples]: https://reddit.com/comments/82ybqj/_/dvf7z5x/
