#!/usr/bin/env python3
#
from datetime import datetime, timedelta
from dateutil import tz
import requests
import zmq
import json

# Note on the Weather.gov JSON.
#
# The times are all in UTC.
#
# Example conversion to datetime: datetime.fromisoformat(wjson['properties']['updateTime'])
#
from PySide6.QtWidgets import QApplication, QFrame, QTextEdit
from PySide6.QtCore import Qt, QFile, Slot, QTimer
import signal
import qt_clock_rc

class Tides:
    """Base class for getting the tides from NOAA. Used for other classes here."""
    def __init__(self):
        self.base_url = "https://tidesandcurrents.noaa.gov/api/datagetter"
        self.timezone = "lst_ldt"  # Local time.
        self.station_dict = {
            "portland": 8418150,
            "popham": 8417177,
            "old orchard": 8418557,
            "cousins": 8417997
        }
        self.request_headers = {
            'User-Agent': '(QtWeatherApp, holtrop@physics.unh.edu)',
            'From': 'holtrop@physics.unh.edu'
        }

    def get_json_data(self, begin_date, end_date, station="portland", product="hilo"):
        """Get the requested data from NOAA as a JSON dictionary"""
        if type(station) == str and station in self.station_dict:
            station = self.station_dict[station]
        else:
            print("Unknown station: {}".format(station))
            return {}

        payload = {}
        if product == "hilo":
            payload['station'] = station
            payload['begin_date'] = begin_date
            payload['end_date'] = end_date
            payload['product'] = "predictions"
            payload['datum'] = "MLLW"
            payload['time_zone'] = self.timezone
            payload['units'] = "metric"
            payload['interval'] = "hilo"
            payload['format'] = "json"
        else:
            print("NOT YET IMPLEMENTED.")

        js = requests.get(self.base_url, params=payload, headers=self.request_headers).json()
        if 'predictions' in js:
            return js['predictions']
        else:
            print("Error obtaining tide data: \n", js)
            return None

class QHiLoTide(QTextEdit):
    """Mini label with high and low tides for today from NOAA"""

    def __init__(self, pos, parent=None, debug=0):
        super(QHiLoTide, self).__init__(parent)
        self.setObjectName("hilo")
        self.debug = debug
        self.setReadOnly(True)
        self.setGeometry(pos[0], pos[1], 220, 60)
        self.setFrameStyle(QFrame.NoFrame)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(3*3600*1000)
        self.update()

 #       self.setStyleSheet("QTextEdit#hilo{ font-size: 8pt;}")

    @Slot()
    def update(self):
        """Update the panel"""
        self.clear()
        tides = Tides()
        now = datetime.now()
        begin = (now+timedelta(days=-0.25)).strftime("%Y%m%d %H:%m")
        end = (now + timedelta(days=+0.85)).strftime("%Y%m%d %H:%m")
        try:
            js = tides.get_json_data(begin, end, "portland", "hilo")
        except:
            js = None
        html_text = ""
        text = ""
        if js is not None:
            n = 0
            for tt in js:
                if tt['type'] == "H":
                    text += "High: "
                    html_text += '<span style="color:#AA5500">High:</span> '
                else:
                    text += "Low: "
                    html_text += '<span style="color:#0055AA">Low:</span> '
                text += "{}  ".format(tt['t'])
                html_text += "{}&nbsp;&nbsp; ".format(tt['t'].split()[1])
                if n == 1:
                    html_text += "<br>\n"
                n += 1
        else:
            text = "Error getting data."
            html_text = "Error getting data."

        if self.debug:
            print("Tides: ", now, " ", text)
        self.setText(html_text)

if __name__ == '__main__':
    import sys
    import os
    import argparse

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


    setup_interrupt_handling()

    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser("Qt based Clock program for Raspberry Pi")
    parser.add_argument("--debug", "-d", action="count", help="Increase debug level.", default=0)
    parser.add_argument("--style", "-s", type=str, help="Use specified style sheet.", default=None)
    parser.add_argument("--frameless", "-fl", action="store_true", help="Make a frameless window.")
    parser.add_argument("--icon", "-i", action="store_true", help="Show the weather icon.")

    args = parser.parse_args(sys.argv[1:])

    file = None
    if args.style is None:
        file = QFile("Clock.qss")
    else:
        file = QFile(args.style)

    file.open(QFile.ReadOnly)
    style_sheet = file.readAll()
    # print(style_sheet.data().decode("utf-8"))
    app.setStyleSheet(style_sheet.data().decode("utf-8"))

    if args.icon:
        pass
    else:
        tide = QHiLoTide((0, 0))
        tide.update()
        tide.show()

    sys.exit(app.exec_())
