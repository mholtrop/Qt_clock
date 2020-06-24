#!/usr/bin/env python3
#
from datetime import datetime
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
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QTextEdit, QPlainTextEdit, QPushButton
from PySide2.QtGui import QFont, QColor, QPixmap, QCursor
from PySide2.QtCore import QFile, Slot, QRect, QCoreApplication, QTimer

from clock_widget import Clock_widget
import qt_clock_rc

import signal


class weather_info_icon(QPushButton):
    """Small helper class for one day weather icon with temperature."""

    def __init__(self, idx, parent):
        """Initalize with a position (x,y) for top left corner."""
        super(weather_info_icon, self).__init__(parent)
        self.setObjectName("wicon")
        self.parent = parent
        self.index = idx
        self.setGeometry(0, 0, 96, 120)
        self.label = QLabel(self)
        self.label.setObjectName("wlabel")
        self.label.setGeometry(5, 0, 86, 16)
        self.label.setText(u"Tue")
        self.pix_url = None
        self.pix = QLabel(self)
        self.pix.setObjectName("wpix")
        self.pix.setGeometry(5, 16, 86, 86)

        self.temp = QLabel(self)
        self.temp.setObjectName("wtemp")
        self.temp.setGeometry(5, 104, 86, 16)
        self.temp.setText(u"XX.X C")
        QWeather.set_temp_color(self.temp, 0, False, True)

        self.set_weather_icon()
        self.hide()
        self.clicked.connect(self.click)

    def set_day_label(self, new):
        """Set the label to the new text"""
        self.label.setText(new)

    def set_weather_icon(self, url=None):
        """Get the weather icon raw data from the url"""

        if url is not None and url != self.pix_url:
            req = requests.get(url)
            icon = QPixmap()
            icon.loadFromData(req.content)
            self.pix.setPixmap(icon)
            self.pix_url = url

    def set_temperature(self, temp, unit="C"):
        """Set the expected temperature."""
        if unit == "F":
            temp = (temp - 32) * 5./9.
        self.temp.setText(u"{:4.1f} C".format(temp))
        QWeather.set_temp_color(self.temp, temp, False, False)

    def set_weather_from_dict(self, dat):
        """Set the weather icon from the dat info."""
        self.set_day_label(dat['name'])
        self.set_weather_icon(dat['icon'])
        self.set_temperature(dat['temperature'], unit=dat['temperatureUnit'])

    @Slot()
    def click(self):
        self.parent.icon_click(self.index)


class QWeather(QMainWindow):
    """Simple Weather reporter window."""
    Weather_gov_url = "https://api.weather.gov/points/"
    GEO_Point_Yarmouth = (43.8365, -70.1635)  # Yarmouth
    GEO_Point_Portland_Airport = (43.64222, -70.30444)  # Portland Airport weather station

    def __init__(self, frameless=False):
        super(QWeather, self).__init__()

        self.temp_update_interval = 60
        self.n_updates = 0

        self.w_update_interval = 60*60  # Once per hour.
        self.w_update = 0

        self.w_text_index = 0
        self.w_period_offset = 0

        self.time_zone = tz.gettz('America/New_York')
        self.fc = None   # Stores the dict of the weather forecast.
        self.fc_time = None  # Stores the forecast time

        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REQ)
        self.zmq_socket.connect("tcp://10.0.0.130:5555")
        self.zmq_request_made = False
        self.zqm_poll = zmq.Poller()
        self.zqm_poll.register(self.zmq_socket, zmq.POLLIN)

        self.setupUi()
        self.update_temperatures()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)


    def setupUi(self):
        # Setup the UI

        self.weather = self
        self.label_inside = QLabel(self.weather)
        self.label_inside.setObjectName(u"label_inside")
        self.label_inside.setGeometry(QRect(10, 10, 58, 16))
        self.label_inside.setText(u"Inside:")
        self.label_inside.setStyleSheet(u"color: #005555")
        self.inside_temp_2 = QLabel(self.weather)
        self.inside_temp_2.setObjectName(u"temp")
        self.inside_temp_2.setText(u"20.5 C - 36%")
        self.inside_temp_2.setGeometry(QRect(10, 30, 241, 31))
        self.inside_temp_2.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.inside_temp_2.setScaledContents(True)
        self.pressure_2 = QLabel(self.weather)
        self.pressure_2.setObjectName(u"press")
        self.pressure_2.setText(u"1005.5 mbar")
        self.pressure_2.setGeometry(QRect(10, 60, 241, 31))
        self.pressure_2.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.pressure_2.setScaledContents(True)
        self.outside_temp_2 = QLabel(self.weather)
        self.outside_temp_2.setObjectName(u"temp")
        self.outside_temp_2.setText(u"20.5 C - 36%")
        self.outside_temp_2.setGeometry(QRect(260, 30, 241, 31))
        self.outside_temp_2.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.outside_temp_2.setScaledContents(True)
        self.label_outside = QLabel(self.weather)
        self.label_outside.setObjectName(u"label_outside")
        self.label_outside.setText(QCoreApplication.translate("Clock", u"Outside:", None))
        self.label_outside.setGeometry(QRect(260, 10, 58, 16))
        self.label_outside.setStyleSheet(u"color: #005555")
        self.pressure_3 = QLabel(self.weather)
        self.pressure_3.setObjectName(u"press")
        self.pressure_3.setText(u"1005.5 mbar")
        self.pressure_3.setGeometry(QRect(260, 60, 241, 31))
        self.pressure_3.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.pressure_3.setScaledContents(True)
        self.label_closet = QLabel(self.weather)
        self.label_closet.setObjectName(u"label_closet")
        self.label_closet.setText(u"Closet:")
        self.label_closet.setGeometry(QRect(530, 10, 58, 16))
        self.label_closet.setStyleSheet(u"color: #005555")
        self.closet_temp = QLabel(self.weather)
        self.closet_temp.setObjectName(u"temp")
        self.closet_temp.setText(u"20.5 C - 36%")
        self.closet_temp.setGeometry(QRect(530, 30, 241, 31))
        self.closet_temp.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.closet_temp.setScaledContents(True)

        self.weather_icons = []
        for i in range(14):
            self.weather_icons.append(weather_info_icon(i, self.weather))

        self.next_button = QPushButton(self.weather)
        self.next_button.setObjectName("next")
        self.next_button.setGeometry(800-10-20, 150, 10, 120)
        self.next_button.clicked.connect(self.shift_weather_icons_right)

        self.prev_button = QPushButton(self.weather)
        self.prev_button.setObjectName("prev")
        self.prev_button.setGeometry(1-10, 150, 10, 120)
        self.prev_button.clicked.connect(self.shift_weather_icons_left)

        self.weather_text = QPlainTextEdit(self.weather)
        self.weather_text.setObjectName("weather_text")
        self.weather_text.setGeometry(QRect(5, 300, 800-10, 480-20-300))
        self.weather_text.setReadOnly(True)
        self.weather_text.insertPlainText("This is a description of the weather for the day that"
                                          "was chosen by clicking on the icon above.")

    def get_weather_json(self, point):
        """Get the top level weather JSOn from the weather.gov website for GEO location point"""
        url = self.Weather_gov_url + "{:.4f},{:.4f}".format(point[0], point[1])
        js = requests.get(url).json()
        return js

    def get_weather_forecast(self, point=None, top_level_json=None, kind=None):
        """Get the forecast information from weather.gov as a json. No parsing.
        The kind of forecasts are: kind = {"forecast", "hourly", "detailed_temps"} """
        if top_level_json is None:
            if point is not None:
                top_level_json = self.get_weather_json(point)
            else:
                return None

        url = ""
        if kind is None or kind == "forecast":
            url = top_level_json['properties']['forecast']
        elif kind == "forecastHourly" or kind == "hourly":
            url = top_level_json['properties']['forecastHourly']
        elif kind == "temps" or kind == "detailed_temps" or kind == 'forecastGridData':
            url = top_level_json['properties']['forecastGridData']
        else:
            print("I do not know about the forecast kind=", kind)
            return None

        js = requests.get(url).json()
        return js

    def update_weather_text(self):
        """Update the weather text area."""
        text = self.fc['periods'][self.w_text_index]['name'] + ":\n" + \
               self.fc['periods'][self.w_text_index]['detailedForecast']
        self.weather_text.clear()
        self.weather_text.insertPlainText(text)

    def update_weather(self):
        """Update the weather forecast from weather.gov """
        self.w_update -= 1
        if self.w_update <= 0:
            self.w_update = self.w_update_interval
            fc_dict = self.get_weather_forecast(self.GEO_Point_Yarmouth, kind="forecast")
            self.fc = fc_dict['properties']
            self.fc_time = datetime.fromisoformat(fc_dict['properties']['updateTime']).astimezone(self.time_zone)
            self.update_weather_icons()
            self.draw_weather_icons()
            self.update_weather_text()

    def update_weather_icons(self):
        """Update the weather icon contents. (slow!)"""
        for i in range(len(self.weather_icons)):
            self.weather_icons[i].set_weather_from_dict(self.fc['periods'][i + self.w_period_offset])

    def draw_weather_icons(self):
        """Draw the weather icons that should be visible in the correct location. """
        for i in range(len(self.weather_icons)):
            self.weather_icons[i].hide()

        for i in range(8):
            self.weather_icons[i+self.w_period_offset].setGeometry(16+i*96, 150, 96, 120)
            self.weather_icons[i+self.w_period_offset].show()
            # (16+i*96, 150)

    @Slot()
    def shift_weather_icons_right(self):
        """Called for shifting the days of the icons right."""
        # print("Shift: {} < {}".format(self.w_period_offset, len(self.fc['periods'])-8))
        if self.w_period_offset < len(self.fc['periods'])-8:
            self.w_period_offset += 1
            self.draw_weather_icons()
            if self.w_text_index < self.w_period_offset:
                self.w_text_index = self.w_period_offset
                self.update_weather_text()

    @Slot()
    def shift_weather_icons_left(self):
        """Called for shifting the days of the icons left."""
        #  print("Shift: {} < {}".format(self.w_period_offset, len(self.fc['periods'])-8))
        if self.w_period_offset > 0:
            self.w_period_offset -= 1
            self.draw_weather_icons()
            if self.w_text_index > self.w_period_offset+8:
                self.w_text_index = self.w_period_offset+8
                self.update_weather_text()


    @Slot()
    def icon_click(self, idx):
        """Called when a weather icon is clicked."""
        self.w_text_index = idx + self.w_period_offset
        self.update_weather_text()

    @Slot()
    def update(self):
        """Update all the weather info, if on the correct tick."""
        self.update_weather()
        self.update_temperatures()

    @Slot()
    def update_temperatures(self):
        """Get a new set of temperatures from bbb1 using zmq and display them."""
        self.n_updates = self.n_updates - 1

        def smart_float(d):
            try:
                r = float(d)
            except:
                r = d.replace('"', '')
            return r


        if self.n_updates <= 1:  # We take two updates to complete this, so start at 1

            if not self.zmq_request_made:
                self.zmq_socket.send(b'a')
                self.zmq_request_made = True
            else:
                pass

        if self.zmq_request_made:
            socks = dict(self.zqm_poll.poll(2))
            if self.zmq_socket in socks and socks[self.zmq_socket] == zmq.POLLIN:
                mess = self.zmq_socket.recv(zmq.DONTWAIT)
                self.temp_data = list(map(smart_float, mess[1:-1].decode().split(',')))
                self.n_updates = self.temp_update_interval
                self.zmq_request_made = False
                # print(" data: ", self.temp_data)

                self.inside_temp_2.setText("{:5.2f} C  {:5.1f} %".format(self.temp_data[1], self.temp_data[3]))
                self.set_temp_color(self.inside_temp_2, self.temp_data[1], True)

                self.outside_temp_2.setText("{:5.2f} C  {:5.1f} %".format(self.temp_data[5], self.temp_data[7]))
                self.set_temp_color(self.outside_temp_2, self.temp_data[5], True)

                self.closet_temp.setText("{:5.2f} C  {:5.1f} %".format(self.temp_data[10], self.temp_data[9]))
                self.set_temp_color(self.closet_temp, self.temp_data[10], True)

                self.pressure_2.setText("{:7.2f} mbar".format(self.temp_data[2]))
                self.set_pressure_color(self.pressure_2, self.temp_data[2])
                self.pressure_3.setText("{:7.2f} mbar".format(self.temp_data[6]))
                self.set_pressure_color(self.pressure_3, self.temp_data[6])

    @staticmethod
    def set_pressure_color(obj, press, valid = True):
        """Set the color of obj according to the pressure. """
        pressures = (900., 950., 1000., 1020., 1040.)
        colors = (0, 60, 120, 240, 300)
        if valid:
            if press < pressures[0]:
                press = pressures[0] + 0.0001
            if press > pressures[-1]:
                press = pressures[-1] - 0.0001

            i=0
            while press > pressures[i]:
                i += 1
            hue = int(((press - pressures[i-1])/(pressures[i] - pressures[i-1]))*(colors[i]-colors[i-1]) +
                      colors[i-1])
            color = QColor.fromHsv(hue, 255, 120, 255)
            obj.setStyleSheet("color: rgba({},{},{},255)".format(color.red(), color.green(), color.blue()))

    @staticmethod
    def set_temp_color(obj, temp, inside=True, invalid=False):
        """Set the color of obj depending on the temperature displayed by obj."""
        temps = (-15., 16., 28., 40.)
        colors = (270, 145, 60, 0)

        if inside:
            temps = (12., 20., 25., 32.)

        if invalid:
            obj.setStyleSheet("color: rgba(100,100,100,100)")
        else:
            if temp < temps[0]:
                temp = temps[0] + 0.0001
            if temp > temps[-1]:
                temp = temps[-1] - 0.0001

            i = 0
            while temp > temps[i]:
                i += 1
            hue = int(((temp - temps[i-1])/(temps[i] - temps[i-1]))*(colors[i] - colors[i-1]) + colors[i-1])
            color = QColor.fromHsv(hue, 255, 150, 255)

            obj.setStyleSheet("color: rgba({},{},{},255)".format(color.red(), color.green(), color.blue()))



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

if __name__ == '__main__':
    import sys
    import os
    import argparse


    setup_interrupt_handling()

    app = QApplication(sys.argv)

    parser = argparse.ArgumentParser("Qt based Clock program for Raspberry Pi")
    parser.add_argument("--debug", "-d", action="count", help="Increase debug level.", default=0)
    parser.add_argument("--style", "-s", type=str, help="Use specified style sheet.", default=None)
    parser.add_argument("--frameless", "-fl", action="store_true", help="Make a frameless window.")

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

    weather = QWeather()
    weather.resize(800, 460)
    weather.show()
    sys.exit(app.exec_())
