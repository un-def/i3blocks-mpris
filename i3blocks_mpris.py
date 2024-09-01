from __future__ import annotations

import argparse
import enum
import html
import json
import os
import re
import string
import sys
import unicodedata
from copy import deepcopy

import dbus
from dbus.mainloop.glib import DBusGMainLoop, threads_init
from gi.repository import Gio, GLib


__version__ = '2.2.0.dev0'
__author__ = 'Dmitry Meyer <me@undef.im>'


class MatchMode(enum.Enum):
    UNKNOWN = 0
    EXACT = 1
    PREFIX = 2


class Formatter(string.Formatter):

    _FORMAT_FUNCS = {
        'upper': str.upper,
        'lower': str.lower,
        'capitalize': str.capitalize,
        'title': str.title,
        'icon': 'status_icon',
    }

    _TRUNCATE_STR_WITH_SUFFIX_REGEX = re.compile(
        r'^(?P<base_truncate>\.\d+),(?P<suffix>.+)$'
    )

    @classmethod
    def truncate_with_suffix_func_generator(cls, format_spec):
        truncate_match = cls._TRUNCATE_STR_WITH_SUFFIX_REGEX.fullmatch(format_spec)
        if truncate_match is None:
            return None

        def inner(value):
            base_truncate = truncate_match.group('base_truncate')
            suffix = truncate_match.group('suffix')
            truncated = f'{value:{base_truncate}}'
            if len(truncated) < len(value):
                return truncated + suffix
            return truncated

        return inner

    def __init__(
        self, status_icons: dict[str, str] | None = None,
        markup_escape: bool = False, sanitize_unicode: bool = True,
    ):
        self._status_icons = status_icons.copy() if status_icons else dict()
        self._markup_escape = markup_escape
        self._sanitize_unicode = sanitize_unicode

    def format_field(self, value, format_spec: str):
        if self._sanitize_unicode and isinstance(value, str):
            value = self._do_sanitize_unicode(value)
        format_func = self._FORMAT_FUNCS.get(format_spec)
        if not format_func and isinstance(value, str):
            format_func = self.truncate_with_suffix_func_generator(format_spec)
        if format_func:
            if isinstance(format_func, str):
                format_func = getattr(self, '_format_func__' + format_func)
            value = format_func(value)
        else:
            value = super().format_field(value, format_spec)
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

    def _format_func__status_icon(self, status) -> str:
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

    MPRIS_BUS_NAME_PREFIX = 'org.mpris.MediaPlayer2.'
    MPRIS_OBJECT_PATH = '/org/mpris/MediaPlayer2'
    MPRIS_PLAYER_INTERFACE = 'org.mpris.MediaPlayer2.Player'

    DBUS_BUS_NAME = 'org.freedesktop.DBus'
    DBUS_OBJECT_PATH = '/org/freedesktop/DBus'
    DBUS_ROOT_INTERFACE = 'org.freedesktop.DBus'
    DBUS_PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'

    _loop = None
    _stdin_stream = None
    _bus = None
    _properties_changed_signal_match = None
    _specific_name_owner_changed_signal_match = None
    _any_name_owner_changed_signal_match = None
    _player_connected = False
    _match_mode: MatchMode

    def __init__(self, bus_name, config=None):
        if not bus_name.startswith(self.MPRIS_BUS_NAME_PREFIX):
            bus_name = f'{self.MPRIS_BUS_NAME_PREFIX}{bus_name}'
        # the current bus name; may be changed if the player allow multiple
        # instances and the user specified only the player name part without
        # the specific instance suffix
        self._bus_name = bus_name
        # for single-instance players or multi-instance players when the
        # user specified the exact instance, this is actually the full name;
        # for multi-instance players when the user provided only the non-unique
        # player name without the instance, this is the bus name without
        # the instance suffix
        self._bus_name_prefix = bus_name
        _config = deepcopy(self.DEFAULT_CONFIG)
        if config:
            for key, value in config.items():
                if isinstance(value, dict):
                    _config[key].update(value)
                else:
                    _config[key] = value
        self._formatter = Formatter(
            status_icons=_config['status_icons'],
            markup_escape=_config['markup_escape'],
            sanitize_unicode=_config['sanitize_unicode'],
        )
        self._format_string=_config['format']
        self._mouse_buttons = _config['mouse_buttons']
        self._dedupe = _config['dedupe']
        self._last_info = None
        self._last_status = None
        self._last_metadata = None
        # a dict used as an ordered set, keys — well-known names with unique
        # instance suffixes, values — True
        self._instances = {}

    @classmethod
    def create_loop(cls):
        loop = GLib.MainLoop()
        # See: https://dbus.freedesktop.org/doc/dbus-python/
        # dbus.mainloop.html?highlight=thread#dbus.mainloop.glib.threads_init
        threads_init()
        DBusGMainLoop(set_as_default=True)
        return loop

    def bus_name_has_owner(self, bus_name=None):
        if not bus_name:
            bus_name = self._bus_name
        return self._bus.name_has_owner(bus_name)

    def init_bus(self):
        self._bus = dbus.SessionBus()

    def _connect_to_player(self):
        self._player_connected = True
        self._connect_to_properties_changed_signal()
        self._connect_to_specific_name_owner_changed_signal()
        self.show_initial_info()

    def _disconnect_from_player(self):
        self._player_connected = False
        if self._match_mode != MatchMode.EXACT:
            # _bus_name is volatile since it contains unique instance suffix,
            # we need to connect to each instance each time
            self._disconnect_from_properties_changed_signal()
            self._disconnect_from_specific_name_owner_changed_signal()

    def run(self, *, loop=None, read_stdin=True, nowait=False):
        if loop is None:
            self._loop = self.create_loop()
        else:
            self._loop = loop
        self.init_bus()
        # initially, we don't know which match mode to use
        match_mode = MatchMode.UNKNOWN
        player_found = False
        if self.bus_name_has_owner():
            # either the player don't allow multiple instance, e.g.,
            # `org.mpris.MediaPlayer2.spotify`, or the user specified the
            # exact instance, e.g., `org.mpris.MediaPlayer2.chromium.instance2`
            # in both cases, the exact name match is used
            match_mode = MatchMode.EXACT
            player_found = True
        else:
            self._find_instances()
            instance_bus_name = self._pick_instance()
            if instance_bus_name:
                player_found = True
                match_mode = MatchMode.PREFIX
                self._bus_name = instance_bus_name
        if not player_found and nowait:
            return
        self._match_mode = match_mode
        if player_found:
            self._connect_to_player()
        if match_mode != MatchMode.EXACT:
            self._connect_to_any_name_owner_changed_signal()
        if read_stdin:
            self.start_stdin_read_loop()
        try:
            self._loop.run()
        except KeyboardInterrupt:
            pass
        finally:
            if read_stdin:
                self.stop_stdin_read_loop()

    def _find_instances(self) -> None:
        for name in self._bus.list_names():
            self._maybe_add_instance(name)

    def _maybe_add_instance(self, name: str) -> bool:
        name_prefix = self._bus_name_prefix
        if not name.startswith(name_prefix):
            return False
        maybe_prefix, _, _ = name.rpartition('.')
        if maybe_prefix != name_prefix:
            return False
        self._instances[name] = True
        return True

    def _maybe_remove_instance(self, name: str) -> None:
        name_prefix = self._bus_name_prefix
        if not name.startswith(name_prefix):
            return
        maybe_prefix, _, _ = name.rpartition('.')
        if maybe_prefix == name_prefix:
            self._instances.pop(name, None)

    def _pick_instance(self) -> str | None:
        for bus_name in reversed(tuple(self._instances)):
            if self.bus_name_has_owner(bus_name):
                return bus_name
            del self._instances[bus_name]
        return None

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
        if button and self._player_connected:
            method_name = self._mouse_buttons.get(button)
            if method_name:
                self._bus.call_async(
                    bus_name=self._bus_name,
                    object_path=self.MPRIS_OBJECT_PATH,
                    dbus_interface=self.MPRIS_PLAYER_INTERFACE,
                    method=method_name, signature='', args=[],
                    reply_handler=None, error_handler=None,
                )
        self._read_stdin_once()

    def _connect_to_properties_changed_signal(self):
        if self._properties_changed_signal_match:
            return
        self._properties_changed_signal_match = self._bus.add_signal_receiver(
            bus_name=self._bus_name,
            dbus_interface=self.DBUS_PROPERTIES_INTERFACE,
            signal_name='PropertiesChanged',
            handler_function=self._on_properties_changed,
        )

    def _on_properties_changed(self, interface_name, changed_properties, _):
        self.show_info(
            status=changed_properties.get('PlaybackStatus'),
            metadata=changed_properties.get('Metadata'),
            only_if_changed=self._dedupe,
        )

    def _disconnect_from_properties_changed_signal(self):
        if self._properties_changed_signal_match:
            self._properties_changed_signal_match.remove()
            self._properties_changed_signal_match = None

    def _connect_to_specific_name_owner_changed_signal(self):
        if self._specific_name_owner_changed_signal_match:
            return
        signal_match = self._bus.add_signal_receiver(
            bus_name=self.DBUS_BUS_NAME,
            path=self.DBUS_OBJECT_PATH,
            dbus_interface=self.DBUS_ROOT_INTERFACE,
            signal_name='NameOwnerChanged',
            arg0=self._bus_name,
            handler_function=self._on_specific_name_owner_changed,
        )
        self._specific_name_owner_changed_signal_match = signal_match

    def _on_specific_name_owner_changed(self, name, old_owner, new_owner):
        if not old_owner and new_owner:
            if not self._player_connected:
                self._connect_to_player()
        elif old_owner and not new_owner:
            self._disconnect_from_player()
            next_instance_bus_name: str | None = None
            if self._match_mode == MatchMode.PREFIX:
                next_instance_bus_name = self._pick_instance()
            if next_instance_bus_name:
                self._bus_name = next_instance_bus_name
                self._connect_to_player()
            else:
                print(flush=True)
                self._last_info = None

    def _disconnect_from_specific_name_owner_changed_signal(self):
        if self._specific_name_owner_changed_signal_match:
            self._specific_name_owner_changed_signal_match.remove()
            self._specific_name_owner_changed_signal_match = None

    def _connect_to_any_name_owner_changed_signal(self):
        if self._any_name_owner_changed_signal_match:
            return
        signal_match = self._bus.add_signal_receiver(
            bus_name=self.DBUS_BUS_NAME,
            path=self.DBUS_OBJECT_PATH,
            dbus_interface=self.DBUS_ROOT_INTERFACE,
            signal_name='NameOwnerChanged',
            handler_function=self._on_any_name_owner_changed,
        )
        self._any_name_owner_changed_signal_match = signal_match

    def _on_any_name_owner_changed(self, name, old_owner, new_owner):
        if not old_owner and new_owner:
            if name == self._bus_name_prefix:
                self._match_mode = MatchMode.EXACT
                self._bus_name = name
                self._disconnect_from_any_name_owner_changed_signal()
                self._connect_to_player()
            else:
                instance_added = self._maybe_add_instance(name)
                if instance_added:
                    self._match_mode = MatchMode.PREFIX
                    if not self._player_connected:
                        self._bus_name = name
                        self._connect_to_player()
        elif old_owner and not new_owner:
            self._maybe_remove_instance(name)

    def _disconnect_from_any_name_owner_changed_signal(self):
        if self._any_name_owner_changed_signal_match:
            self._any_name_owner_changed_signal_match.remove()
            self._any_name_owner_changed_signal_match = None

    def get_property(self, property_name):
        return self._bus.call_blocking(
            bus_name=self._bus_name,
            object_path=self.MPRIS_OBJECT_PATH,
            dbus_interface=self.DBUS_PROPERTIES_INTERFACE,
            method='Get', signature='ss',
            args=[self.MPRIS_PLAYER_INTERFACE, property_name],
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
        info = self._formatter.format(
            self._format_string,
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
