import argparse
import html
import json
import os
import string
import sys
from copy import deepcopy

import dbus
from dbus.mainloop.glib import DBusGMainLoop, threads_init
from gi.repository import Gio, GLib


__version__ = '1.2.0'
__author__ = 'un.def <me@undef.im>'


class Formatter(string.Formatter):

    _FORMAT_FUNCS = {
        'upper': str.upper,
        'lower': str.lower,
        'capitalize': str.capitalize,
        'icon': 'status_icon',
    }

    def __init__(self, format_string, status_icons=None, markup_escape=True):
        self._format_string = format_string
        if status_icons is not None:
            self._status_icons = status_icons.copy()
        else:
            self._status_icons = {}
        self._markup_escape = markup_escape

    def __call__(self, *args, **kwargs):
        return self.format(self._format_string, *args, **kwargs)

    def format_field(self, value, format_spec):
        if format_spec:
            format_func = self._FORMAT_FUNCS[format_spec]
            if isinstance(format_func, str):
                format_func = getattr(self, '_format_func__' + format_func)
            value = format_func(value)
        if self._markup_escape:
            value = html.escape(value)
        return value

    def _format_func__status_icon(self, status):
        return self._status_icons.get(status, '?')


class SpotifyBlocklet:

    DEFAULT_CONFIG = {
        # Format: {field} or {field:filter}
        # Fields: status, artist, title
        # Filters: icon (from status only), upper, lower, capitalize
        'format': '{status}: {artist} – {title}',
        # Escape special characters (such as `<>&`) for Pango markup
        'markup_escape': False,
        # MPRIS `PlaybackStatus` property to icon mapping
        'status_icons': {
            'Playing': '\uf04b',   # 
            'Paused': '\uf04c',   # 
            'Stopped': '\uf04d',   # 
        },
        # X11 mouse button number to MPRIS method mapping
        'mouse_buttons': {
            '1': 'PlayPause',
        },
        # Do not print the same info multiple times if True
        'dedupe': True,
    }

    BUS_NAME = 'org.mpris.MediaPlayer2.spotify'
    OBJECT_PATH = '/org/mpris/MediaPlayer2'
    PLAYER_INTERFACE = 'org.mpris.MediaPlayer2.Player'
    PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'

    _loop = None
    _stdin_stream = None
    _bus = None
    _spotify = None

    def __init__(self, config=None):
        _config = deepcopy(self.DEFAULT_CONFIG)
        if config:
            for key, value in config.items():
                if isinstance(value, dict):
                    _config[key].update(value)
                else:
                    _config[key] = value
        self._formatter = Formatter(
            format_string=_config['format'],
            status_icons=_config['status_icons'],
            markup_escape=_config['markup_escape'],
        )
        self._mouse_buttons = _config['mouse_buttons']
        self._dedupe = _config['dedupe']
        self._prev_info = None

    @classmethod
    def create_loop(cls):
        loop = GLib.MainLoop()
        # See: https://dbus.freedesktop.org/doc/dbus-python/
        # dbus.mainloop.html?highlight=thread#dbus.mainloop.glib.threads_init
        threads_init()
        DBusGMainLoop(set_as_default=True)
        return loop

    def init_bus(self):
        self._bus = dbus.SessionBus()

    def run(self, *, loop=None, read_stdin=True, nowait=False):
        if loop is None:
            self._loop = self.create_loop()
        else:
            self._loop = loop
        self.init_bus()
        try:
            self.init_spotify()
        except dbus.exceptions.DBusException:
            if nowait:
                return
        if read_stdin:
            self.start_stdin_read_loop()
        self.connect_to_name_owner_changed_signal()
        try:
            self._loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            if read_stdin:
                self.stop_stdin_read_loop()

    def start_stdin_read_loop(self):
        self._stdin_stream = Gio.DataInputStream.new(
            Gio.UnixInputStream.new(sys.stdin.fileno(), False))
        self._stdin_stream.set_close_base_stream(True)
        self._read_stdin_once()

    def stop_stdin_read_loop(self):
        self._stdin_stream.close_async(
            io_priority=GLib.PRIORITY_DEFAULT,
            callback=lambda *args: self._loop.quit(),
        )
        self._loop.run()
        self._stdin_stream = None

    def _read_stdin_once(self):
        self._stdin_stream.read_line_async(
            io_priority=GLib.PRIORITY_DEFAULT, callback=self._on_stdin_line)

    def _on_stdin_line(self, stream, task):
        try:
            result = stream.read_line_finish(task)
        except GLib.Error:
            return
        try:
            button = result[0].decode()
        except ValueError:
            button = None
        if button and self._spotify:
            method_name = self._mouse_buttons.get(button)
            if method_name:
                getattr(self._spotify, method_name)(
                    dbus_interface=self.PLAYER_INTERFACE)
        self._read_stdin_once()

    def init_spotify(self):
        self._spotify = self._bus.get_object(
            bus_name=self.BUS_NAME,
            object_path=self.OBJECT_PATH,
            follow_name_owner_changes=True,
        )
        self.connect_to_properties_changed_signal()
        self.show_initial_info()

    def connect_to_properties_changed_signal(self):
        self._spotify.connect_to_signal(
            signal_name='PropertiesChanged',
            handler_function=self._on_properties_changed,
            dbus_interface=self.PROPERTIES_INTERFACE,
        )

    def _on_properties_changed(self, interface_name, changed_properties, _):
        """Show updated info when playback status or track is changed"""
        self.show_info(
            status=changed_properties['PlaybackStatus'],
            metadata=changed_properties['Metadata'],
            only_if_changed=self._dedupe,
        )

    def connect_to_name_owner_changed_signal(self):
        self._bus.get_object(
            bus_name='org.freedesktop.DBus',
            object_path='/org/freedesktop/DBus',
        ).connect_to_signal(
            signal_name='NameOwnerChanged',
            handler_function=self._on_name_owner_changed,
            dbus_interface='org.freedesktop.DBus',
            arg0=self.BUS_NAME,
        )

    def _on_name_owner_changed(self, name, old_owner, new_owner):
        """
        Get Spotify object when Spotify is started or clear info when
        Spotify is closed
        """
        if not old_owner and new_owner and not self._spotify:
            self.init_spotify()
        elif old_owner and not new_owner:
            print(flush=True)
            self._prev_info = None

    def get_property(self, property_name):
        return self._spotify.Get(
            self.PLAYER_INTERFACE, property_name,
            dbus_interface=self.PROPERTIES_INTERFACE,
        )

    def show_initial_info(self):
        self.show_info(
            status=self.get_property('PlaybackStatus'),
            metadata=self.get_property('Metadata'),
        )

    def show_info(self, status, metadata, only_if_changed=False):
        artist = ', '.join(metadata['xesam:artist'])
        title = metadata['xesam:title']
        info = self._formatter(
            status=status,
            artist=artist,
            title=title,
        )
        if not only_if_changed or self._prev_info != info:
            print(info, flush=True)
            self._prev_info = info


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    parser.add_argument('-f', '--format')
    markup_escape_group = parser.add_mutually_exclusive_group()
    markup_escape_group.add_argument(
        '--markup-escape',
        action='store_true', default=None, dest='markup_escape',
    )
    markup_escape_group.add_argument(
        '--no-markup-escape',
        action='store_false', default=None, dest='markup_escape',
    )
    dedupe_group = parser.add_mutually_exclusive_group()
    dedupe_group.add_argument(
        '--dedupe',
        action='store_true', default=None, dest='dedupe',
    )
    dedupe_group.add_argument(
        '--no-dedupe',
        action='store_false', default=None, dest='dedupe',
    )
    parser.add_argument('--version', action='version', version=__version__)
    args = parser.parse_args()
    return args


def _main():
    args = _parse_args()
    if args.config:
        with open(os.path.abspath(args.config)) as fp:
            config = json.load(fp)
    else:
        config = {}
    for key in ['format', 'markup_escape', 'dedupe']:
        value = getattr(args, key)
        if value is not None:
            config[key] = value
    SpotifyBlocklet(config=config).run()


if __name__ == '__main__':
    _main()
