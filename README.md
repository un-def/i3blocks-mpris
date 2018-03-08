i3blocks-spotify-persist
========================

[![screenshot][screenshot]][screenshot]

Persistent (daemonized) [i3blocks][i3blocks] blocklet for Spotify desktop app.

**NOTE**: running the blocklet as a daemon allows us to update status/track information instantly, but due to [i3blocks limitation][i3blocks-issue] we can not handle mouse click events 😞


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
[i3blocks]: https://github.com/vivien/i3blocks
[i3blocks-issue]: https://github.com/vivien/i3blocks/issues/228
[dbus-python]: https://pypi.org/project/dbus-python/
[pygobject]: https://pygobject.readthedocs.io/en/latest/
