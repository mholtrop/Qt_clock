#!/usr/bin/env python3
#
# Python port of the Qt_clock C++ app.
#
#
from PySide2.QtWidgets import QApplication
from PySide2.QtCore import QFile, QJsonDocument

from clock_widget import Clock_widget
import qt_clock_rc

import signal

# Call this function in your main after creating the QApplication
def setup_interrupt_handling():
    """Setup handling of KeyboardInterrupt (Ctrl-C) for PyQt."""
    signal.signal(signal.SIGINT, _interrupt_handler)
    # Regularly run some (any) python code, so the signal handler gets a
    # chance to be executed:
    # safe_timer(50, lambda: None)


# Define this as a global function to make sure it is not garbage
# collected when going out of scope:
def _interrupt_handler(signum, frame):
    """Handle KeyboardInterrupt: quit application."""
    print("You interrupted me with a control-C. ")
    QApplication.quit()

# def safe_timer(timeout, func, *args, **kwargs):
#     """
#     Create a timer that is safe against garbage collection and overlapping
#     calls. See: http://ralsina.me/weblog/posts/BB974.html
#     """
#     def timer_event():
#         try:
#             func(*args, **kwargs)
#         finally:
#             QtCore.QTimer.singleShot(timeout, timer_event)
#     QtCore.QTimer.singleShot(timeout, timer_event)

if __name__ == '__main__':
    import sys
    import os
    import argparse

    if os.uname().sysname == "Linux":
        os.system("/usr/bin/xset dpms 28800 28800 36000")
        os.system("/usr/bin/xset s off")  # Also turn off screen saver.

    setup_interrupt_handling()

    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser("Qt based Clock program for Raspberry Pi")
    parser.add_argument("--debug", "-d", action="count", help="Increase debug level.", default=0)
    parser.add_argument("--style", "-s", type=str, help="Use specified style sheet.", default=None)
    parser.add_argument("--frameless", "-fl", action="store_true", help="Make a frameless window.")
    parser.add_argument("--web", action="store_true", help="Make get moon from web.")

    args = parser.parse_args(sys.argv[1:])

    if args.debug:
        print("Debug flag is set to:", args.debug)

    clock = Clock_widget(args.frameless, web=args.web, debug=args.debug)

    file = None
    if args.style is None:
#        file = QFile(":/Clock.qss")
        file = QFile("Clock.qss")
    else:
        file = QFile(args.style)

    file.open(QFile.ReadOnly)
    style_sheet = file.readAll()
    # print(style_sheet.data().decode("utf-8"))
    app.setStyleSheet(style_sheet.data().decode("utf-8"))

    if os.uname().sysname == "Linux":
        f = open("/sys/class/backlight/rpi_backlight/brightness")
        num = int(f.readline())
        f.close()
    else:
        num = 40

    clock.LCD_brightness = num
    clock.Brightness.setSliderPosition(num)

    setting_file = os.getenv("HOME") + "/.Qt_Clock"
    loadfile = QFile(setting_file)
    if not loadfile.open(QFile.ReadOnly):
        print("Could not open setting JSon file: {}".format(setting_file))
    else:
        data = loadfile.readAll()
        json = QJsonDocument.fromJson(data).object()
        clock.setup_from_json(json)

    clock.show()
    sys.exit(app.exec_())
