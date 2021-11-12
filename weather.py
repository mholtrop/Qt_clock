#!/usr/bin/env python3
#
from datetime import datetime
from dateutil import tz
# import requests  ### Requests seems to get OLD versions!!!
import urllib3
import zmq
import re
import json

# Note on the Weather.gov JSON.
#
# The times are all in UTC.
#
# Example conversion to datetime: datetime.fromisoformat(wjson['properties']['updateTime'])
#
from PySide2.QtWidgets import QApplication, QMainWindow, QWidget, QLabel, QTextEdit, QTextEdit, QPushButton
from PySide2.QtGui import QFont, QColor, QPixmap, QCursor
from PySide2.QtCore import Qt, QObject, QFile, Signal, Slot, QRect, QCoreApplication, QTimer
from PySide2.QtSvg import QSvgWidget

import signal
import qt_clock_rc

class QWeatherInfoIcon(QPushButton):
    """Small helper class for one day weather icon with temperature."""

    def __init__(self, idx, parent):
        """Initalize with a position (x,y) for top left corner."""
        super(QWeatherInfoIcon, self).__init__(parent)
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
        self.request_headers = urllib3.make_headers(user_agent='(QtWeatherApp, holtrop@physics.unh.edu)',
                                                    disable_cache=True)
        self.http = urllib3.PoolManager()


    def set_day_label(self, new):
        """Set the label to the new text"""
        self.label.setText(new)

    def set_weather_icon(self, url=None):
        """Get the weather icon raw data from the url"""

        if url is not None and url != self.pix_url:
            req = self.http.request('GET', url, headers=self.request_headers)
            # print(f"request: {req.status}")
            icon = QPixmap()
            icon.loadFromData(req.data)
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


class QTempMiniPanel:
    """A small weather panel which uses the information from QWeather to display some information."""

    def __init__(self, pos, qweather, parent=None):
        """Setup a mini-panel which can be part of the clock page."""

        self.parent = parent
        self.weather = qweather

        # Weather information mini panel
        self.inside_temp = QLabel(self.parent)
        self.inside_temp.setObjectName(u"temp")
        self.inside_temp.setText(u"xx.x C - xx%")
        self.inside_temp.setGeometry(QRect(pos[0]+70, pos[1], 261, 31))
        self.inside_temp.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.inside_temp.setScaledContents(True)
        self.label_in = QLabel(self.parent)
        self.label_in.setObjectName(u"label")
        self.label_in.setText(QCoreApplication.translate("Clock", u"Inside:", None))
        self.label_in.setGeometry(QRect(pos[0], pos[1]+10, 58, 16))
        self.label_in.setStyleSheet(u"color: #005555")
        self.outside_temp = QLabel(self.parent)
        self.outside_temp.setObjectName(u"temp")
        self.outside_temp.setText(u"20.5 C - 36%")
        self.outside_temp.setGeometry(QRect(pos[0]+70, pos[1]+30, 261, 31))
        self.outside_temp.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.outside_temp.setScaledContents(True)
        self.label_out = QLabel(self.parent)
        self.label_out.setObjectName(u"label")
        self.label_out.setText(u"Outside:")
        self.label_out.setGeometry(QRect(pos[0], pos[1]+40, 58, 16))
        self.label_out.setStyleSheet(u"color: #005555")
        self.label_press = QLabel(self.parent)
        self.label_press.setObjectName(u"label_")
        self.label_press.setText(u"Pressure:")
        self.label_press.setGeometry(QRect(pos[0], pos[1]+70, 58, 16))
        self.label_press.setStyleSheet(u"color: #005555")
        self.pressure = QLabel(self.parent)
        self.pressure.setObjectName(u"press")
        self.pressure.setText(u"1xxx.x mbar")
        self.pressure.setGeometry(QRect(pos[0]+70, pos[1]+60, 261, 31))
        self.pressure.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.pressure.setScaledContents(True)

    @Slot()
    def update(self):
        """Update the mini panel."""
        if self.weather is None:
            print("ERROR - QWeatherMiniPanel not configured correctly.", type(self.weather))
            return

        try:
            self.inside_temp.setText("{:5.2f} C  {:5.1f} %".format(self.weather.temp_data[1],
                                                                   self.weather.temp_data[3]))
            QWeather.set_temp_color(self.inside_temp, self.weather.temp_data[1], True,
                                    not self.weather.temp_data_valid)
            self.outside_temp.setText("{:5.2f} C  {:5.1f} %".format(self.weather.temp_data[5],
                                                                    self.weather.temp_data[7]))
            QWeather.set_temp_color(self.outside_temp, self.weather.temp_data[5], False,
                                    not self.weather.temp_data_valid)
            self.pressure.setText("{:7.2f} mbar".format(self.weather.temp_data[2]))
            QWeather.set_pressure_color(self.pressure, self.weather.temp_data[2], self.weather.temp_data_valid)
        except Exception as e:
            print("Exception while updating minipanel.")

class QWeatherIcon(QSvgWidget):
    """A simple icon for indicating the weather."""

    WEATHER_ICONS = {
        "skc": ("sunny.svg", "Fair/clear"),
        "few": ("lightcloud.svg", "A few clouds"),
        "sct": ("lightcloud.svg", "Partly cloudy"),
        "bkn": ("cloud.svg", "Mostly cloudy"),
        "ovc": ("cloud.svg", "Overcast"),
        "wind_skc": ("wind.svg", "Fair/clear and windy"),
        "wind_few": ("wind.svg", "A few clouds and windy"),
        "wind_sct": ("windcloud.svg", "Partly cloudy and windy"),
        "wind_bkn": ("windcloud.svg", "Mostly cloudy and windy"),
        "wind_ovc": ("windcloud.svg", "Overcast and windy"),
        "snow": ("snow.svg", "Snow"),
        "rain_snow": ("snow.svg", "Rain/snow"),
        "rain_sleet": ("snow.svg", "Rain/sleet"),
        "snow_sleet": ("rainsnow.svg", "Snow/sleet"),
        "fzra": ("rainsnow.svg", "Freezing rain"),
        "rain_fzra": ("rainsnow.svg", "Rain/freezing rain"),
        "snow_fzra": ("rainsnow.svg", "Freezing rain/snow"),
        "sleet": ("rainsnow.svg", "Sleet"),
        "rain": ("rain.svg", "Rain"),
        "rain_showers": ("rain.svg", "Rain showers (high cloud cover)"),
        "rain_showers_hi": ("rain.svg", "Rain showers (low cloud cover)"),
        "tsra": ("thunder.svg", "Thunderstorm (high cloud cover)"),
        "tsra_sct": ("thunder.svg", "Thunderstorm (medium cloud cover)"),
        "tsra_hi": ("thunder.svg", "Thunderstorm (low cloud cover)"),
        "tornado": ("unknown.svg", "Tornado"),
        "hurricane": ("unknown.svg", "Hurricane conditions"),
        "tropical_storm": ("unknown.svg", "Tropical storm conditions"),
        "dust": ("unknown.svg", "Dust"),
        "smoke": ("unknown.svg", "Smoke"),
        "haze": ("haze.svg", "Haze"),
        "hot": ("hot.svg", "Hot"),
        "cold": ("unknown.svg", "Cold"),
        "blizzard": ("unknown.svg", "Blizzard"),
        "fog": ("fog.svg", "Fog/mist")
    }

    def __init__(self, pos, qweather, parent=None):
        super(QWeatherIcon, self).__init__(parent)
        self.pos = pos
        self.weather = qweather
        self.setGeometry(pos[0], pos[1], 100, 100)
        self.setStyleSheet("background-color: transparent;")

    @Slot()
    def update(self):
        """Update the icon to reflect current conditions."""
        if self.weather is not None and self.weather.fc is not None:
            condition = self.weather.fc['periods'][0]['shortForecast']
            icon_url = self.weather.fc['periods'][0]['icon']
            # icon_url is something like:
            # "https://api.weather.gov/icons/land/day/sct?size=medium"
            match = re.match("https://api\.weather\.gov/icons/(.*)/(.*)/([a-z_]*).*", icon_url)
            print(f"{datetime.now()} - Update icon for: '{condition}'  url: {icon_url}  match: {match.group(3)}")
            if not match or not match.group(3) in self.WEATHER_ICONS:
                print("Icon does not exist for match {} condition: {}".format(match.group(3), condition))
                icon_file = "icons/unknown.svg"
            else:
                # TODO: Refine this for night/day icons.
                icon_name = self.WEATHER_ICONS[match.group(3)][0]
                icon_file = "icons/" + icon_name
            self.load(icon_file)
            self.resize(100, 100)
        else:
            print("ERROR - QWeatherIcon - weather not initialized.")


class QWeather(QWidget, QObject):
    """Simple Weather reporter window."""
    Weather_gov_url = "https://api.weather.gov/points/"
    GEO_Point_Freeport = (43.8672, -70.0968)  # South Freeport
    GEO_Point_Yarmouth = (43.8365, -70.1635)  # Yarmouth
    GEO_Point_Portland_Airport = (43.64222, -70.30444)  # Portland Airport weather station

    # Signals we emit.
    temp_updated = Signal()
    weather_updated = Signal()

    def __init__(self, parent=None, debug=0):
        super(QWeather, self).__init__(parent)
        self.setObjectName(u"weather")

        if parent is not None:
            self.parent = parent
        else:
            self.parent = self

        self.debug = debug

        self.temp_update_interval = 60  # Once per minute
        self.n_updates = 1
        self.temp_data = [-99.9]*11
        self.temp_data_valid = False

        self.w_update_interval = 60*60  # Once per hour.
        self.w_update = 3

        self.w_text_index = 0
        self.w_period_offset = 0

        self.request_headers = {
            'User-Agent': '(QtWeatherApp, holtrop@physics.unh.edu)',
            'From': 'holtrop@physics.unh.edu',
            'Cache-Control': 'no-cache'
        }

        self.time_zone = tz.gettz('America/New_York')
        self.fc = None   # Stores the dict of the weather forecast.
        self.fc_time = None  # Stores the forecast time

        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.REQ)
        self.zmq_socket.connect("tcp://bbb1:5555")
        self.zmq_request_made = False
        self.zqm_poll = zmq.Poller()
        self.zqm_poll.register(self.zmq_socket, zmq.POLLIN)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

        # Setup the UI

        self.label_inside = QLabel(self.parent)
        self.label_inside.setObjectName(u"label_inside")
        self.label_inside.setGeometry(QRect(10, 10, 58, 16))
        self.label_inside.setText(u"Inside:")
        self.label_inside.setStyleSheet(u"color: #005555")
        self.inside_temp_2 = QLabel(self.parent)
        self.inside_temp_2.setObjectName(u"temp")
        self.inside_temp_2.setText(u"20.5 C - 36%")
        self.inside_temp_2.setGeometry(QRect(10, 30, 241, 31))
        self.inside_temp_2.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.inside_temp_2.setScaledContents(True)
        self.pressure_2 = QLabel(self.parent)
        self.pressure_2.setObjectName(u"press")
        self.pressure_2.setText(u"1005.5 mbar")
        self.pressure_2.setGeometry(QRect(10, 60, 241, 31))
        self.pressure_2.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.pressure_2.setScaledContents(True)
        self.outside_temp_2 = QLabel(self.parent)
        self.outside_temp_2.setObjectName(u"temp")
        self.outside_temp_2.setText(u"20.5 C - 36%")
        self.outside_temp_2.setGeometry(QRect(260, 30, 241, 31))
        self.outside_temp_2.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.outside_temp_2.setScaledContents(True)
        self.label_outside = QLabel(self.parent)
        self.label_outside.setObjectName(u"label_outside")
        self.label_outside.setText(QCoreApplication.translate("Clock", u"Outside:", None))
        self.label_outside.setGeometry(QRect(260, 10, 58, 16))
        self.label_outside.setStyleSheet(u"color: #005555")
        self.pressure_3 = QLabel(self.parent)
        self.pressure_3.setObjectName(u"press")
        self.pressure_3.setText(u"1005.5 mbar")
        self.pressure_3.setGeometry(QRect(260, 60, 241, 31))
        self.pressure_3.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.pressure_3.setScaledContents(True)
        self.label_closet = QLabel(self.parent)
        self.label_closet.setObjectName(u"label_closet")
        self.label_closet.setText(u"Closet:")
        self.label_closet.setGeometry(QRect(530, 10, 58, 16))
        self.label_closet.setStyleSheet(u"color: #005555")
        self.closet_temp = QLabel(self.parent)
        self.closet_temp.setObjectName(u"temp")
        self.closet_temp.setText(u"20.5 C - 36%")
        self.closet_temp.setGeometry(QRect(530, 30, 241, 31))
        self.closet_temp.setStyleSheet(u"color: rgba(40,40,40,100)")
        self.closet_temp.setScaledContents(True)

        self.weather_forecast_time = QLabel(self.parent)
        self.weather_forecast_time.setObjectName(u"forecast_time")
        self.weather_forecast_time.setText(u"Forecast: never")
        self.weather_forecast_time.setGeometry(QRect(10, 120, 300, 18))
        self.weather_forecast_time.setStyleSheet(u"color: #005555")

        self.weather_icons = []
        for i in range(14):
            self.weather_icons.append(QWeatherInfoIcon(i, self.parent))

        self.next_button = QPushButton(self.parent)
        self.next_button.setObjectName("next")
        self.next_button.setGeometry(800-15-12, 150, 10, 120)
        self.next_button.clicked.connect(self.shift_weather_icons_right)

        self.prev_button = QPushButton(self.parent)
        self.prev_button.setObjectName("prev")
        self.prev_button.setGeometry(QRect(2-5, 150, 10, 120))
        self.prev_button.clicked.connect(self.shift_weather_icons_left)

        self.weather_text = QTextEdit(self.parent)
        self.weather_text.setObjectName("weather_text")
        self.weather_text.setGeometry(QRect(5, 300, 800-10, 480-20-300))
        self.weather_text.setReadOnly(True)
        self.weather_text.insertPlainText("This is a description of the weather for the day that"
                                          "was chosen by clicking on the icon above.")

        # Signal Slot connections.
        self.temp_updated.connect(self.update_temperature_display)
        self.weather_updated.connect(self.update_weather_info)
        self.http = urllib3.PoolManager()

        if self.debug:
            print("QWeather.__init__() done.")

    def get_weather_json(self, point):
        """Get the top level weather JSOn from the weather.gov website for GEO location point"""
        url = self.Weather_gov_url + "{:.4f},{:.4f}".format(point[0], point[1])
        req = self.http.request('GET', url, headers=self.request_headers)
        js = json.loads(req.data.decode('utf-8'))  # requests.get(url, headers=self.request_headers).json()
        if js is None or 'properties' not in js:
            print("Did not get top level weather request.")
            return None

        return js

    def get_weather_forecast(self, point=None, top_level_json=None, kind=None):
        """Get the forecast information from weather.gov as a json. No parsing.
        The kind of forecasts are: kind = {"forecast", "hourly", "detailed_temps"} """
        if top_level_json is None:
            if point is not None:
                top_level_json = self.get_weather_json(point)
            else:
                top_level_json = self.get_weather_json(self.GEO_Point_Freeport)

        if top_level_json is None:
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

        if self.debug:
            print(f"Weather update url = {url}")

        payload = {"units": "si"}
        try:
            req = self.http.request('GET', url, fields=payload, headers=self.request_headers)
            js = json.loads(req.data.decode('utf-8'))
            # js = requests.get(url, params=payload, headers=self.request_headers).json()
        except Exception as e:
            print("Could not get the weather json:", datetime.now())
            print(e)
            return None

        if 'properties' not in js:
            print("Error getting weather information:", datetime.now())
            print(js['status'])
            return None
        else:
            if self.debug:
                print(f"Weather forecast from {js['properties']['updated']}")
                print(f"Weather generated at  {js['properties']['generatedAt']}")
            return js

    def update_weather_text(self):
        """Update the weather text area."""
        text = self.fc['periods'][self.w_text_index]['name'] + ": <b>" + \
               self.fc['periods'][self.w_text_index]['shortForecast']+"</b><br/>\n" + \
               self.fc['periods'][self.w_text_index]['detailedForecast']
        self.weather_text.clear()
#        self.weather_text.insertPlainText(text)
        self.weather_text.insertHtml(text)
        self.weather_forecast_time.setText(self.fc_time.strftime('Forecast: %Y-%m-%d %H:%M'))

    def update_weather(self):
        """Update the weather forecast from weather.gov """
        self.w_update -= 1

        old_fc = self.fc
        if self.w_update <= 0:
            self.w_update = self.w_update_interval
            new_fc = self.get_weather_forecast(self.GEO_Point_Freeport, kind="forecast")
            if new_fc is None:
                # Do not change the text and do not emit an "updated"
                self.w_update = 360  # Try again in 3 minutes.
                return

            try:

                self.fc = new_fc['properties']
                self.fc_time = datetime.fromisoformat(new_fc['properties']['updateTime']).astimezone(self.time_zone)
                if self.debug > 1:
                    print("Emit: weather_updated")
                self.weather_updated.emit()
            except Exception as e:
                print("Did not get the proper weather.", e)
                self.fc = old_fc
                self.fc['periods'][0]['name'] += "NOT UPDATED"

    def update_weather_icons(self):
        """Update the weather icon contents. (slow!)"""
        for i in range(len(self.weather_icons)):
            try:
                self.weather_icons[i].set_weather_from_dict(self.fc['periods'][i + self.w_period_offset])
            except Exception as e:
                print("===== ERROR =====")
                print("Updating weather icons, i=", i, " w_period_offset = ", self.w_period_offset)
                print("len(self.fc[periods])=", len(self.fc['periods']))
                print(e)



    def draw_weather_icons(self):
        """Draw the weather icons that should be visible in the correct location. """
        for i in range(len(self.weather_icons)):
            self.weather_icons[i].hide()

        for i in range(8):
            self.weather_icons[i+self.w_period_offset].setGeometry(16+i*96, 150, 96, 120)
            self.weather_icons[i+self.w_period_offset].show()
            # (16+i*96, 150)

    @Slot()
    def update_weather_info(self):
        if self.debug > 1:
            print(" -- update_weather_info() ")
        self.update_weather_icons()
        self.draw_weather_icons()
        self.update_weather_text()


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
            if self.w_text_index > self.w_period_offset+7:
                self.w_text_index = self.w_period_offset+7
                self.update_weather_text()


    @Slot()
    def icon_click(self, idx):
        """Called when a weather icon is clicked."""
        self.w_text_index = idx
        self.update_weather_text()

    @Slot()
    def update(self):
        """Update all the weather info, if on the correct tick."""
        self.update_weather()
        self.update_temperatures()

    @Slot()
    def update_temperatures(self):
        """Get a new set of temperatures from bbb1 using zmq."""
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
            if self.debug > 2:
                print("Polling, ")
            if self.zmq_socket in socks and socks[self.zmq_socket] == zmq.POLLIN:
                if self.debug > 2:
                    print("Got a poll reply.")
                mess = self.zmq_socket.recv(zmq.DONTWAIT)
                if self.debug > 2:
                    print(mess)
                self.temp_data = list(map(smart_float, mess[1:-1].decode().split(',')))
                self.n_updates = self.temp_update_interval
                self.temp_data_valid = True
                self.zmq_request_made = False
                if self.debug > 1:
                    print("temp_updated.emit()")
                self.temp_updated.emit()
            elif self.n_updates < -1:
                self.temp_data_valid = False
                if self.debug > 2:
                    print("nothing, n_updates = ", self.n_updates)
                self.temp_updated.emit()

    @Slot()
    def update_temperature_display(self):
        """Update the temperature display."""
        if self.debug > 1:
            print("update_temperature_display(). Data is valid = ", self.temp_data_valid)
        self.inside_temp_2.setText("{:5.2f} C  {:5.1f} %".format(self.temp_data[1], self.temp_data[3]))
        self.set_temp_color(self.inside_temp_2, self.temp_data[1], True, not self.temp_data_valid)

        self.outside_temp_2.setText("{:5.2f} C  {:5.1f} %".format(self.temp_data[5], self.temp_data[7]))
        self.set_temp_color(self.outside_temp_2, self.temp_data[5], False, not self.temp_data_valid)

        self.closet_temp.setText("{:5.2f} C  {:5.1f} %".format(self.temp_data[10], self.temp_data[9]))
        self.set_temp_color(self.closet_temp, self.temp_data[10], True, not self.temp_data_valid)

        self.pressure_2.setText("{:7.2f} mbar".format(self.temp_data[2]))
        self.set_pressure_color(self.pressure_2, self.temp_data[2], self.temp_data_valid)
        self.pressure_3.setText("{:7.2f} mbar".format(self.temp_data[6]))
        self.set_pressure_color(self.pressure_3, self.temp_data[6], self.temp_data_valid)

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
        else:
            obj.setStyleSheet("color: rgba({},{},{},255)".format(100, 100, 100))

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
        widget = QWidget()
        widget.resize(250, 200)
        weather = QWeather()
        weather.update_weather()
        # Weather info on the Clock page.
        minipanel = QTempMiniPanel((5, 100), weather, parent=widget)
        weather.temp_updated.connect(minipanel.update)

        icon = QWeatherIcon((5, 2), weather, parent=widget)
        weather.weather_updated.connect(icon.update)
        widget.show()
    else:
        weather = QWeather()
        weather.resize(800, 460)
        weather.debug = args.debug
        weather.show()

    sys.exit(app.exec_())
