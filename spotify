#!/usr/bin/env python3
import sys
import html
import time

import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib


class SpotifyBlocklet:

    BUS_NAME = 'org.mpris.MediaPlayer2.spotify'
    OBJECT_PATH = '/org/mpris/MediaPlayer2'
    PLAYER_INTERFACE = 'org.mpris.MediaPlayer2.Player'
    PROPERTIES_INTERFACE = 'org.freedesktop.DBus.Properties'

    STATUS_TO_ICON = {
        'Playing': '',
        'Paused': '',
        'Stopped': '',
    }

    def __init__(self):
        self.loop = GLib.MainLoop()
        DBusGMainLoop(set_as_default=True)

    def run(self):
        self.bus = dbus.SessionBus()
        self.spotify = self.bus.get_object(
            bus_name=self.BUS_NAME,
            object_path=self.OBJECT_PATH,
            follow_name_owner_changes=True,
        )
        self.connect_to_dbus_signals()
        self.show_initial_info()
        self.loop.run()

    def run_forever(self):
        while True:
            try:
                self.run()
            except dbus.exceptions.DBusException:
                time.sleep(1)
            except KeyboardInterrupt:
                break

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
        )

    def on_name_owner_changed(self, name, old_owner, new_owner):
        """Clear info when Spotify is closed"""
        if old_owner and not new_owner:
            print(' ')
            sys.stdout.flush()

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

    def show_info(self, status, metadata):
        status_icon = self.STATUS_TO_ICON.get(status, '?')
        artist = ', '.join(metadata['xesam:artist'])
        title = metadata['xesam:title']
        info = '{status_icon} {artist} — {title}'.format(
            status_icon=status_icon,
            artist=artist,
            title=title,
        )
        print(html.escape(info))
        sys.stdout.flush()


if __name__ == '__main__':
    SpotifyBlocklet().run_forever()
