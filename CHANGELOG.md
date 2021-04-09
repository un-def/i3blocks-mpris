# Changelog

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
