#!/usr/bin/python
# -*- coding: utf-8 -*-
"""Provide a socket."""

from logging import debug
import socket

from pipython import GCSError, gcserror
from pipython.interfaces.pigateway import PIGateway

__signature__ = 0x65de574dbfa6dfb3c7cdc8631fb99ef9


class PISocket(PIGateway):
    """Provide a socket, can be used as context manager."""

    def __init__(self, host='localhost', port=50000):
        """Provide a connected socket.
        @param host : IP address as string, defaults to "localhost".
        @param port : IP port to use as integer, defaults to 50000.
        """
        debug('create an instance of PISocket(host=%s, port=%s)', host, port)
        self._timeout = 7000  # milliseconds
        self._host = host
        self._port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.connect((self._host, self._port))
        self._socket.setblocking(0)
        self._connected = True
        self.flush()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __str__(self):
        return 'PISocket(host=%s, port=%s)' % (self._host, self._port)

    @property
    def timeout(self):
        """Return timeout in milliseconds."""
        return self._timeout

    def settimeout(self, value):
        """Set timeout to 'value' in milliseconds."""
        self._timeout = value

    @property
    def connected(self):
        """Return True if a device is connected."""
        return self._connected

    @property
    def connectionid(self):
        """Return 0 as ID of current connection."""
        return 0

    def send(self, msg):
        """Send 'msg' to the socket.
        @param msg : String to send.
        """
        debug('PISocket.send: %r', msg)
        if self._socket.send(msg.encode('cp1252')) != len(msg):
            raise GCSError(gcserror.E_2_SEND_ERROR)

    def read(self):
        """Return the answer to a GCS query command.
        @return : Answer as string.
        """
        try:
            received = self._socket.recv(2048)
            debug('PISocket.read: %r', received)
        except IOError:
            return u''
        return received

    def flush(self):
        """Flush input buffer."""
        debug('PISocket.flush()')
        while True:
            try:
                self._socket.recv(2048)
            except IOError:
                break

    def close(self):
        """Close socket."""
        debug('PISocket.close: close connection to %s:%s', self._host, self._port)
        self._connected = False
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket.close()
