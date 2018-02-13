#!/usr/bin/python

import signal


class Timeout(Exception):
    pass


def start_timeout(sec):
    def alarm_handler(signum, data):
        raise Timeout

    signal.signal(signal.SIGALRM, alarm_handler)
    signal.alarm(sec)


def stop_timeout():
    # turn of timeout
    signal.signal(signal.SIGALRM, signal.SIG_DFL)
    signal.alarm(0)
