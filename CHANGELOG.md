# Changelog

## 2.2.0

### Features

  * Multi-instance player support. It's now possible to specify a player by its non-unique name prefix only, without the unique instance suffix, e.g., `-p firefox` instead of `-p firefox.instance_1_34`. The blocklet monitors all instances and pick the new one when the previous disappears.
  * Improved formatter by [@tellezhector](https://github.com/tellezhector):
    - Added fallback to built-in `Formatter` format specs. See [Python Docs](https://docs.python.org/3.8/library/string.html#format-examples).
    - Added a format_spec for truncating strings and adding a suffix `{string:.<max_length>,<suffix>}`.
  * Added a placeholder message displayed when there is no player.

### Changes

  * The blocket no longer handles `SIGINT`. See [PR #14](https://github.com/un-def/i3blocks-mpris/pull/14) for an explanation.

## 2.1.0

### Changes

  * Dropped Python 3.6 and 3.7 support.

### Features

  * Added Python 3.12 support.
  * Added `sanitize_unicode` option (enabled by default) to remove some non-printable unicode characters (see [#9](https://github.com/un-def/i3blocks-mpris/issues/9)).
  * Added `title` filter.

### Internal Changes

  * All `Formatter` constructor/initializer arguments are now required (no default values) and keyword-only.

## 2.0.1

### Fixes

  * An empty string is now used as a fallback for missing metadata fields (artist, title). Previously, an exception would be raised if any of the required fields were missing.

## 2.0.0

### Changes

  * The blocklet now works with any media player that supports the MPRIS D-Bus interface, not only the Spotify app. A new required parameter `player` was introduced. To indicate this change, the blocklet was renamed from `i3blocks-spotify-persist` to `i3blocks-mpris`.
  * The minimum Python version was bumped to 3.6.

### Fixes

  * The `PlaybackStatus` and `Metadata` properties is now cached to properly handle the `PropertiesChanged` signal. There was no issue with the Spotify app purely by chance.
  * Fixed erroneous `init_player()` logic.

## 1.2.0

### Fixes

  * Fixed an issue where the blocklet would hang up hugging CPU when Spotify app was not running for a while (https://github.com/un-def/i3blocks-mpris/issues/6).

### Internal Changes

  * The `NameOwnerChanged` signal is now used instead of `time.sleep(1)` polling to get the `Spotify` object. This change provides a fix for the issue mentioned above.
  * The `stdin` input thread was replaced with GIO `InputStream` async (callback-based) reads.
  * Some “public” methods and a constructor of the `SpotifyBlocket` class were changed. Although these changes are actually breaking from a “public” API point of view, there was only a minor (not major) version bump since it's unlikely that the blocket is used as a Python library by anyone.

## 1.1.0

### Features

  * Added support for command line arguments.
  * Deduplication of messages — the updated message will be printed only if it differs from the previous one.

### Changes

  * The default format now uses a textual status instead of an icon.
  * Pango markup escape is now disabled by default.

## 1.0.0

The first public release.
