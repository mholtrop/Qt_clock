#
# clock_widget
#
# The "Clock_widget" is actually the main component for the
# qt_clock application. It is not only the clock component.
#
#
import os
import zmq
from PySide2.QtWidgets import QMainWindow, QSizePolicy, QTabWidget, QWidget, QLabel, QPushButton, QTimeEdit, \
    QLCDNumber, QSlider, QCheckBox, QSpinBox
from PySide2.QtGui import QColor, QFont, QPainter, QPolygon
from PySide2.QtCore import Qt, Slot, QTimer, QDateTime, QTime, QRect, QCoreApplication, QPoint

from weather import QWeather, QTempMiniPanel, QWeatherIcon
from moon import QMoon
from tides import QHiLoTide

class Clock_widget(QMainWindow):

    def __init__(self, frameless=False, web=False, debug=0):
        super(Clock_widget, self).__init__()

        self.debug = debug
        self.frameless = frameless
        self.web = web
        self.analog = None
        self.bedtime = QTime(20, 15, 00)
        self.bedtime_grace_period = 10
        self.LEDBall_state = 0
        self.temp_update_interval = 10
        self.n_updates = 0

        self.temp_data = ['i', 0, 0, 0, 'o', 0, 0, 0, 'c', 0, 0]
        self.LCD_brightness = 150

        self.resize(800, 460)
        self.setupUi(self)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

    def setupUi(self, parent):
        """Setup the interfaces for the clock."""

        if not self.objectName():
            self.setObjectName(u"Clock")

        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(parent.sizePolicy().hasHeightForWidth())
        parent.setSizePolicy(sizePolicy)
        parent.setAutoFillBackground(True)

        parent.setWindowFlag(Qt.Widget, True)
        if os.uname().sysname == "Linux" or self.frameless:
            parent.setWindowFlag(Qt.FramelessWindowHint, True)
    
        self.tabWidget = QTabWidget(parent)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setGeometry(QRect(0, 0, 800, 460))
        # This works for Mac, but seems to not work with Linux/Arm/RPi
        # tabbar = self.tabWidget.tabBar()
        # tabbar.setMinimumSize(50, 24)
        # tabfont = QFont()
        # tabfont.setBold(True)
        # tabfont.setItalic(True)
        # tabfont.setPointSize(32)
        # tabbar.setFont(tabfont)

        # Setup the TABS
        self.clock = QWidget()
        self.clock.setObjectName(u"clock")
        self.tabWidget.addTab(self.clock, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.clock), "Clock")

        self.weather = QWeather(parent=None, debug=self.debug)
        self.tabWidget.addTab(self.weather, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.weather), "Weather")

        self.settings = QWidget()
        self.settings.setObjectName(u"settings")
        self.tabWidget.addTab(self.settings, "")
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.settings), "Settings")

        self.tabWidget.setCurrentIndex(0)

        #################################################################################################
        # Setup Clock Page
        #################################################################################################

        self.analog = AnalogClock(self.clock)

        # DIGITAL clock in "clock" tab
        self.Digital = QLabel(self.clock)
        self.Digital.setObjectName(u"Digital")
        self.Digital.setGeometry(QRect(0, 5, 765, 71))
        self.Digital.setAutoFillBackground(False)
        self.Digital.setStyleSheet(u"")
        self.Digital.setText(u"Current Time - Date + time")

        # Weather Icon
        self.weathericon = QWeatherIcon((480, 5), self.weather, parent=self.clock)
        self.weather.weather_updated.connect(self.weathericon.update)

        # Weather info on the Clock page.
        self.minipanel = QTempMiniPanel((475, 105), self.weather, parent=self.clock)
        self.weather.temp_updated.connect(self.minipanel.update)

        self.hilo = QHiLoTide((580, 5), parent=self.clock, debug=self.debug)


        # Moon phase
        self.moon = QMoon(pos=(450, 210), parent=self.clock, size=216, web=self.web)

        # Push buttons in "clock tab.
        push_button_width = 111
        push_button_height = 40
        push_button_x = 670
        push_button_y = 220

        self.ledball_off = QPushButton(self.clock)
        self.ledball_off.setObjectName(u"ledball_off")
        self.ledball_off.setText(u"LED off")
        self.ledball_off.setGeometry(QRect(push_button_x, push_button_y, push_button_width, push_button_height))

        self.ledball_on = QPushButton(self.clock)
        self.ledball_on.setObjectName(u"ledball_on")
        self.ledball_on.setText(u"LED on ")
        self.ledball_on.setGeometry(QRect(push_button_x, push_button_y+push_button_height, push_button_width, push_button_height))

        self.ledball_on2 = QPushButton(self.clock)
        self.ledball_on2.setObjectName(u"ledball_on2")
        self.ledball_on2.setText(u"LED on 2")
        self.ledball_on2.setGeometry(QRect(push_button_x, push_button_y+push_button_height*2, push_button_width, push_button_height))

        self.sleep = QPushButton(self.clock)
        self.sleep.setObjectName(u"sleep")
        self.sleep.setText(u"Sleep")
        self.sleep.setGeometry(QRect(push_button_x, push_button_y+push_button_height*3+10, push_button_width, push_button_height))

        #################################################################################################
        # Setup Weather Page
        #################################################################################################

        #################################################################################################
        # Setup Setting Page
        #################################################################################################
        self.timeEdit = QTimeEdit(self.settings)
        self.timeEdit.setObjectName(u"timeEdit")
        self.timeEdit.setDisplayFormat(u"h:mm AP")
        self.timeEdit.setGeometry(QRect(200, 30, 191, 41))
        font8 = QFont()
        font8.setFamily(u"Gill Sans")
        font8.setPointSize(16)
        font8.setBold(False)
        font8.setItalic(False)
        font8.setWeight(50)
        self.timeEdit.setFont(font8)
        self.timeEdit.setAutoFillBackground(True)
        self.timeEdit.setTime(self.bedtime)
        self.bedtime_label = QLabel(self.settings)
        self.bedtime_label.setObjectName(u"bedtime_label")
        self.bedtime_label.setText(u"Set Bedtime:")
        self.bedtime_label.setGeometry(QRect(200, 0, 151, 31))
        self.bedtime_label.setFont(font8)
        self.bedtime_label.setAutoFillBackground(True)
        self.Brightness_Value = QLCDNumber(self.settings)
        self.Brightness_Value.setObjectName(u"Brightness_Value")
        self.Brightness_Value.setGeometry(QRect(20, 120, 61, 31))
        self.Brightness_Value.setStyleSheet(u"color: \"White\";\n"
                                            "margin:0px;\n"
                                            "border:0px;background:\"transparent\";")
        self.Brightness_Value.setDigitCount(3)
        self.Brightness_Value.setProperty("value", 180.000000000000000)
        self.Brightness = QSlider(self.settings)
        self.Brightness.setObjectName(u"Brightness")
        self.Brightness.setGeometry(QRect(30, 160, 51, 261))
        self.Brightness.setAutoFillBackground(False)
        self.Brightness.setMaximum(255)
        self.Brightness.setValue(self.LCD_brightness)
        self.Brightness.setOrientation(Qt.Vertical)
        self.Brightness_label = QLabel(self.settings)
        self.Brightness_label.setObjectName(u"Brightness_label")
        self.Brightness_label.setText(u"Brightness")
        self.Brightness_label.setGeometry(QRect(20, 70, 101, 41))
        font10 = QFont()
        font10.setFamily(u"Arial Black")
        font10.setPointSize(12)
        font10.setBold(True)
        font10.setWeight(75)
        self.Brightness_label.setFont(font10)
        self.temp_test = QLabel(self.settings)
        self.temp_test.setObjectName(u"temp_test")
        self.temp_test.setText(u"T20.5 C")
        self.temp_test.setFont(font8)
        self.temp_test.setGeometry(QRect(630, 60, 141, 51))
        # self.temp_test.setFont(font_bold_20)
        self.temp_test_slide = QSlider(self.settings)
        self.temp_test_slide.setObjectName(u"temp_test_slide")
        self.temp_test_slide.setGeometry(QRect(660, 150, 51, 271))
        self.temp_test_slide.setAutoFillBackground(False)
        self.temp_test_slide.setMinimum(-250)
        self.temp_test_slide.setMaximum(450)
        self.temp_test_slide.setSingleStep(5)
        self.temp_test_slide.setPageStep(25)
        self.temp_test_slide.setValue(38)
        self.temp_test_slide.setOrientation(Qt.Vertical)
        self.temp_check_outside = QCheckBox(self.settings)
        self.temp_check_outside.setObjectName(u"temp_check_outside")
        self.temp_check_outside.setText(u"Outside")
        self.temp_check_outside.setGeometry(QRect(640, 110, 86, 20))
        self.grace_period = QSpinBox(self.settings)
        self.grace_period.setObjectName(u"grace_period")
        self.grace_period.setGeometry(QRect(411, 31, 111, 41))
        self.grace_period.setFont(font8)
        self.grace_period.setMinimum(1)
        self.grace_period.setMaximum(60)
        self.grace_period.setValue(self.bedtime_grace_period)
        self.grace_period.setDisplayIntegerBase(10)
        self.grace_period_label = QLabel(self.settings)
        self.grace_period_label.setObjectName(u"grace_period_label")
        self.grace_period_label.setText(u"Grace period:")
        self.grace_period_label.setGeometry(QRect(410, 10, 111, 16))
        self.grace_period_label.setFont(font8)

        #################################################################################################
        # SET ALL LABEL TEXTS
        #################################################################################################

        # if QT_CONFIG(tooltip)
        self.sleep.setToolTip(u"Put display to sleep")
        self.ledball_on2.setToolTip(u"Turn on the LED Ball, mode 2")
        self.ledball_on.setToolTip(u"Turn on the LED Ball.")
        self.ledball_off.setToolTip(u"Turn off the LED Ball.")
        # endif // QT_CONFIG(tooltip)

        #################################################################################################
        # Make the Connections.
        #################################################################################################

        self.temp_test_slide.valueChanged.connect(self.test_temp_update)
        self.temp_check_outside.clicked.connect(self.test_temp_update)

        self.ledball_off.clicked.connect(self.set_ledball_off)
        self.ledball_on.clicked.connect(self.set_ledball_on)
        self.ledball_on2.clicked.connect(self.set_ledball_on2)
        self.sleep.clicked.connect(self.set_sleep)

        self.timeEdit.timeChanged.connect(self.set_bedtime)
        self.grace_period.valueChanged.connect(self.set_grace_period)
        self.Brightness.valueChanged.connect(self.set_screen_brightness)
        self.Brightness.valueChanged.connect(self.Brightness_Value.display)

    def setup_from_json(self, json):
        """Set settings from the json dictionary passed."""

        if "BedTime" in json:
            new_bedtime = QTime.fromString(json["BedTime"], "hh:mm:ss")
            if not new_bedtime.isValid():
                new_bedtime = QTime.fromString(json["BedTime"], "hh:mm")

            if new_bedtime.isValid():
                self.bedtime = new_bedtime
                self.timeEdit.setTime(self.bedtime)
            else:
                print("Could not set bedtime to {}".format(str(new_bedtime)))

        if "GracePeriod" in json:
            self.bedtime_grace_period = int(json["GracePeriod"])
            self.grace_period.setValue(self.bedtime_grace_period)

        if "Brightness" in json:
            self.LCD_brightness = int(json["Brightness"])
            self.Brightness.setValue(self.LCD_brightness)

    @Slot()
    def update(self):
        """This is called every second to perform the clock functions."""
        AnalogClock.update(self)

        dtime = QDateTime.currentDateTime()
        text = dtime.toString("ddd MMM dd hh:mm:ss")
        self.Digital.setText(text)

        time = dtime.time()
        if self.bedtime < time < self.bedtime.addSecs(self.bedtime_grace_period * 60):
            self.Digital.setStyleSheet("color: rgba(200,100,0,200)")
            self.Digital.setText(text + " Bedtime")

        if self.bedtime < time < self.bedtime.addSecs(1) and self.LEDBall_state > 0:
            self.set_ledball_ready_for_bed()

        if self.bedtime.addSecs(self.bedtime_grace_period*60) < time < \
                self.bedtime.addSecs(self.bedtime_grace_period*60 + 1):
            self.Digital.setStyleSheet("")
            self.set_ledball_off()
            self.turn_off_lcd()


    @Slot()
    def set_ledball_off(self):
        """Turn off the LED ball."""
        if self.debug > 0:
            print("Set LED ball off.")

        os.system("ssh bbb1 \"./LEDBall_off.py\" >/dev/null")
        self.LEDBall_state = 0

    @Slot()
    def set_ledball_ready_for_bed(self):
        """Set LED ball to very red."""
        if self.LEDBall_state != 3:
            if self.debug > 0:
                print("Set LED ball to ready for bed.")
            os.system("ssh bbb1 \"./LEDBall_off.py && ./matrix.py 200 5.\" >/dev/null ")
            self.LEDBall_state = 3

    @Slot()
    def set_ledball_on(self):
        """Turn LED ball to normal on"""
        if self.debug > 0:
            print("Set LED ball on.")

        os.system("(ssh bbb1 \"./LEDBall_off.py && ./matrix.py 200\" >/dev/null)")
        self.LEDBall_state = 1

    @Slot()
    def set_ledball_on2(self):
        """Turn LED ball to alternate on"""
        if self.debug > 0:
            print("Set LED ball alternate on.")

        os.system("(ssh bbb1 \"./LEDBall_off.py && ./matrix.py 300 3. 50\" >/dev/null)");
        self.LEDBall_state = 2

    @Slot()
    def set_sleep(self):
        self.set_ledball_off()
        self.turn_off_lcd()

    def turn_off_lcd(self):
        """Turn the LCD off with the DPMS."""
        if os.uname().sysname == "Linux":
            os.system("/usr/bin/xset dpms force off");

    def set_pressure_color(selfs, obj, press, valid = True):
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


    def set_temp_color(self, obj, temp, inside=True, invalid=False):
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

    @Slot()
    def test_temp_update(self, val=None):
        """Update the temperature on the test slider."""

        if val is None or type(val) is bool:
            val = self.temp_test_slide.value()

        temp = val*0.1
        text = "{:6.2f} C".format(temp)
        self.temp_test.setText(text)
        self.set_temp_color(self.temp_test, temp, not self.temp_check_outside.isChecked(), False)

    @Slot()
    def set_bedtime(self, ntime):
        """Set the bedtime to a new time"""
        self.bedtime = ntime

    @Slot()
    def set_grace_period(self, grace):
        """Set the grace period to a new delta time"""
        self.bedtime_grace_period = grace

    @Slot()
    def set_screen_brightness(self, value):
        """Set the brightness of the screen on Raspberry Pi"""
        self.LCD_brightness = value

        if os.uname().sysname == "Linux":
            try:
                f = open("/sys/class/backlight/rpi_backlight/brightness", "w")
                f.write(str(value))
                f.close()
            except Exception as e:
                print("Issue with opening brightness file \n",e)


class AnalogClock(QWidget):

    hourHand = QPolygon([
        QPoint(7, 8),
        QPoint(-7, 8),
        QPoint(0, -40)
    ])

    minuteHand = QPolygon([
        QPoint(7, 8),
        QPoint(-7, 8),
        QPoint(0, -70)
    ])

    secondHand  = QPolygon([
        QPoint(2, 4),
        QPoint(-2, 4),
        QPoint(0, -75)
    ])

    hourColor = QColor(200, 0, 200)
    minuteColor = QColor(0, 200, 200, 191)
    secondColor = QColor(200, 200, 200, 100)

    def __init__(self, clock):

        super(AnalogClock, self).__init__(clock)
        self.setObjectName(u"analogClock")
        self.setGeometry(QRect(20, 80, 350, 350))
        # self.setAutoFillBackground(True)


    def paintEvent(self, event):
        """Update the clock by re-painting it."""

        side = min(self.width(), self.height())
        time = QTime.currentTime()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(side / 200.0, side / 200.0)

        painter.setPen(Qt.NoPen)
        painter.setBrush(AnalogClock.hourColor)

        painter.save()
        painter.rotate(30.0 * ((time.hour() + time.minute() / 60.0)))
        painter.drawConvexPolygon(AnalogClock.hourHand)
        painter.restore()

        painter.setPen(AnalogClock.hourColor)

        for i in range(12):
            painter.drawLine(88, 0, 96, 0)
            painter.rotate(30.0)

        painter.setPen(Qt.NoPen)
        painter.setBrush(AnalogClock.minuteColor)

        painter.save()
        painter.rotate(6.0 * (time.minute() + time.second() / 60.0))
        painter.drawConvexPolygon(AnalogClock.minuteHand)
        painter.restore()

        painter.setPen(AnalogClock.minuteColor)

        for j in range(60):
            if (j % 5) != 0:
                painter.drawLine(92, 0, 96, 0)
            painter.rotate(6.0)

        painter.setPen(Qt.NoPen)
        painter.setBrush(AnalogClock.secondColor)

        painter.save()
        painter.rotate(6.0*time.second())
        painter.drawConvexPolygon(AnalogClock.secondHand)
        painter.restore()
