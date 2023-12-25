from __future__ import annotations

import argparse
import html
import json
import os
import string
import sys
import unicodedata
from copy import deepcopy

import dbus
from dbus.mainloop.glib import DBusGMainLoop, threads_init
from gi.repository import Gio, GLib


__version__ = '2.1.0'
__author__ = 'Dmitry Meyer <me@undef.im>'


class Formatter(string.Formatter):

    _FORMAT_FUNCS = {
        'upper': str.upper,
        'lower': str.lower,
        'capitalize': str.capitalize,
        'title': str.title,
        'icon': 'status_icon',
    }

    def __init__(
        self, *, format_string: str, status_icons: dict[str, str],
        markup_escape: bool, sanitize_unicode: bool,
    ):
        self._format_string = format_string
        self._status_icons = status_icons.copy()
        self._markup_escape = markup_escape
        self._sanitize_unicode = sanitize_unicode

    def __call__(self, *args, **kwargs):
        return self.format(self._format_string, *args, **kwargs)

    def format_field(self, value, format_spec):
        if self._sanitize_unicode:
            value = self._do_sanitize_unicode(value)
        if format_spec:
            format_func = self._FORMAT_FUNCS[format_spec]
            if isinstance(format_func, str):
                format_func = getattr(self, '_format_func__' + format_func)
            value = format_func(value)
        if self._markup_escape:
            value = html.escape(value)
        return value

    def _do_sanitize_unicode(self, value: str) -> str:
        """Removes all characters belonging to the `C` (“other”) categories
        save for the `Cf` (“format”) category.
        """
        return ''.join(
            char for char in value
            if unicodedata.category(char) not in {'Cc', 'Cs', 'Co', 'Cn'}
        )

    def _format_func__status_icon(self, status):
        return self._status_icons.get(status, '?')


class MPRISBlocklet:

    DEFAULT_CONFIG = {
        # Format: {field} or {field:filter}
        # Fields: status, artist, title
        # Filters: icon (from status only), upper, lower, capitalize, title
        'format': '{status}: {artist} – {title}',
        # Escape special characters (such as `<>&`) for Pango markup
        'markup_escape': False,
        # Remove `C` category unicode characters (except for `Cf`)
        'sanitize_unicode': True,
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

    BUS_NAME_PREFIX = 'org.mpris.MediaPlayer2.'
    OBJECT_PATH = '/org/mpris/MediaPlayer2'
    PLAYER_INTERFACE = 'org.mpris.MediaPlayer2.Player'
    PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'

    _loop = None
    _stdin_stream = None
    _bus = None
    _player = None

    def __init__(self, bus_name, config=None):
        if not bus_name.startswith(self.BUS_NAME_PREFIX):
            bus_name = f'{self.BUS_NAME_PREFIX}{bus_name}'
        self._bus_name = bus_name
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
            sanitize_unicode=_config['sanitize_unicode'],
        )
        self._mouse_buttons = _config['mouse_buttons']
        self._dedupe = _config['dedupe']
        self._last_info = None
        self._last_status = None
        self._last_metadata = None

    @classmethod
    def create_loop(cls):
        loop = GLib.MainLoop()
        # See: https://dbus.freedesktop.org/doc/dbus-python/
        # dbus.mainloop.html?highlight=thread#dbus.mainloop.glib.threads_init
        threads_init()
        DBusGMainLoop(set_as_default=True)
        return loop

    @property
    def name_has_owner(self):
        return self._bus.name_has_owner(self._bus_name)

    def init_bus(self):
        self._bus = dbus.SessionBus()

    def init_player(self):
        self._player = self._bus.get_object(
            bus_name=self._bus_name,
            object_path=self.OBJECT_PATH,
            follow_name_owner_changes=True,
        )
        self.connect_to_properties_changed_signal()

    def run(self, *, loop=None, read_stdin=True, nowait=False):
        if loop is None:
            self._loop = self.create_loop()
        else:
            self._loop = loop
        self.init_bus()
        if self.name_has_owner:
            self.init_player()
            self.show_initial_info()
        elif nowait:
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
        if button and self._player:
            method_name = self._mouse_buttons.get(button)
            if method_name:
                self._player.get_dbus_method(
                    method_name, dbus_interface=self.PLAYER_INTERFACE)()
        self._read_stdin_once()

    def connect_to_properties_changed_signal(self):
        self._player.connect_to_signal(
            signal_name='PropertiesChanged',
            handler_function=self._on_properties_changed,
            dbus_interface=self.PROPERTIES_INTERFACE,
        )

    def _on_properties_changed(self, interface_name, changed_properties, _):
        """Show updated info when playback status or track is changed"""
        self.show_info(
            status=changed_properties.get('PlaybackStatus'),
            metadata=changed_properties.get('Metadata'),
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
            arg0=self._bus_name,
        )

    def _on_name_owner_changed(self, name, old_owner, new_owner):
        """
        Get the player and show the initial info when the player is started
        or clear the info when the player is closed
        """
        if not old_owner and new_owner:
            if not self._player:
                self.init_player()
            self.show_initial_info()
        elif old_owner and not new_owner:
            print(flush=True)
            self._last_info = None

    def get_property(self, property_name):
        return self._player.Get(
            self.PLAYER_INTERFACE, property_name,
            dbus_interface=self.PROPERTIES_INTERFACE,
        )

    def show_initial_info(self):
        self.show_info(
            status=self.get_property('PlaybackStatus'),
            metadata=self.get_property('Metadata'),
        )

    def show_info(self, status=None, metadata=None, *, only_if_changed=False):
        if status is None:
            status = self._last_status
        else:
            self._last_status = status
        if metadata is None:
            metadata = self._last_metadata
        else:
            self._last_metadata = metadata
        if status is None or metadata is None:
            return
        artist = ', '.join(metadata.get('xesam:artist', ()))
        title = metadata.get('xesam:title', '')
        info = self._formatter(
            status=status,
            artist=artist,
            title=title,
        )
        if not only_if_changed or self._last_info != info:
            print(info, flush=True)
            self._last_info = info


def _add_boolean_flag_group(
    parser: argparse.ArgumentParser, name: str, dest: str | None = None,
) -> None:
    if dest is None:
        dest = name.replace('-', '_')
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        f'--{name}', action='store_true', default=None, dest=dest)
    group.add_argument(
        f'--no-{name}', action='store_false', default=None, dest=dest)


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config')
    parser.add_argument('-p', '--player')
    parser.add_argument('-f', '--format')
    _add_boolean_flag_group(parser, 'markup-escape')
    _add_boolean_flag_group(parser, 'sanitize-unicode')
    _add_boolean_flag_group(parser, 'dedupe')
    parser.add_argument('--version', action='version', version=__version__)
    args = parser.parse_args()
    return args


def _main():
    args = _parse_args()
    if args.config:
        with open(os.path.abspath(args.config)) as fp:
            config = json.load(fp)
        player_from_config = config.pop('player', None)
    else:
        config = {}
        player_from_config = None
    player = args.player or player_from_config
    if not player:
        sys.exit('player is not specified')
    for key, value in vars(args).items():
        if key not in ['config', 'player'] and value is not None:
            config[key] = value
    MPRISBlocklet(bus_name=player, config=config).run()


if __name__ == '__main__':
    _main()
