import argparse
import html
import json
import os
import string
import sys
import threading
import time
from copy import deepcopy

import dbus
from dbus.mainloop.glib import DBusGMainLoop, threads_init
from gi.repository import GLib


__version__ = '1.1.0'
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

    loop = None

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
        self._handle_input_thread = threading.Thread(
            target=self.handle_input, daemon=True)

    def handle_input(self):
        while True:
            button = sys.stdin.readline().strip()
            method_name = self._mouse_buttons.get(button)
            if method_name:
                getattr(self.spotify, method_name)(
                    dbus_interface=self.PLAYER_INTERFACE)

    def init_loop(self):
        self.loop = GLib.MainLoop()
        # See: https://dbus.freedesktop.org/doc/dbus-python/
        # dbus.mainloop.html?highlight=thread#dbus.mainloop.glib.threads_init
        threads_init()
        DBusGMainLoop(set_as_default=True)

    def _run(self):
        self.bus = dbus.SessionBus()
        self.spotify = self.bus.get_object(
            bus_name=self.BUS_NAME,
            object_path=self.OBJECT_PATH,
            follow_name_owner_changes=True,
        )
        self.connect_to_dbus_signals()
        self.show_initial_info()
        self.loop.run()

    def run(self, *, init_loop=False, forever=False):
        if init_loop:
            self.init_loop()
        elif self.loop is None:
            raise RuntimeError(
                'Loop is not initialized; call init_loop() first.')
        self._handle_input_thread.start()
        while True:
            try:
                self._run()
            except dbus.exceptions.DBusException:
                time.sleep(1)
            except KeyboardInterrupt:
                break
            finally:
                if not forever:
                    break
        self.loop.quit()

    def connect_to_dbus_signals(self):
        self.spotify.connect_to_signal(
            signal_name='PropertiesChanged',
            handler_function=self.on_properties_changed,
            dbus_interface=self.PROPERTIES_INTERFACE,
        )
        self.bus.get_object(
            bus_name='org.freedesktop.DBus',
            object_path='/org/freedesktop/DBus',
        ).connect_to_signal(
            signal_name='NameOwnerChanged',
            handler_function=self.on_name_owner_changed,
            dbus_interface='org.freedesktop.DBus',
            arg0=self.BUS_NAME,
        )

    def on_properties_changed(self, interface_name, changed_properties, _):
        """Show updated info when playback status or track is changed"""
        self.show_info(
            status=changed_properties['PlaybackStatus'],
            metadata=changed_properties['Metadata'],
            only_if_changed=self._dedupe,
        )

    def on_name_owner_changed(self, name, old_owner, new_owner):
        """Clear info when Spotify is closed"""
        if old_owner and not new_owner:
            print(flush=True)
            self._prev_info = None

    def get_property(self, property_name):
        return self.spotify.Get(
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
    SpotifyBlocklet(config=config).run(init_loop=True, forever=True)


if __name__ == '__main__':
    _main()
