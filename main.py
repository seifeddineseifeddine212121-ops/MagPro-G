import arabic_reshaper
import hashlib
import json
import logging
import math
import os
import random
import re
import socket
import sys
import textwrap
import threading
import time
# ==========================================
DEBUG = True
if DEBUG:
    os.environ['KIVY_LOG_LEVEL'] = 'info'
    os.environ['KIVY_NO_CONSOLELOG'] = '0'
else:
    os.environ['KIVY_LOG_LEVEL'] = 'error'
    os.environ['KIVY_NO_CONSOLELOG'] = '1'
# ==========================================
from PIL import Image, ImageDraw, ImageFont
from bidi.algorithm import get_display
from datetime import datetime, timedelta
from kivy.clock import Clock, mainthread
from kivy.config import Config
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics.context_instructions import PushMatrix, PopMatrix, Rotate
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.network.urlrequest import UrlRequest
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, ListProperty, BooleanProperty, ColorProperty
from kivy.storage.jsonstore import JsonStore
from kivy.uix.behaviors import ButtonBehavior as KivyButtonBehavior
from kivy.uix.camera import Camera
from kivy.uix.modalview import ModalView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.utils import platform
from kivymd import fonts_path
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDIconButton, MDFillRoundFlatButton, MDFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.fitimage import FitImage
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.list import MDList, OneLineListItem, TwoLineAvatarIconListItem, ThreeLineAvatarIconListItem, IconLeftWidget, IconRightWidget, IRightBodyTouch, ILeftBody
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar
# ==========================================
if DEBUG:
    Config.set('kivy', 'log_level', 'info')
    Config.set('kivy', 'log_enable', 1)
else:
    Config.set('kivy', 'log_level', 'error')
    Config.set('kivy', 'log_enable', 0)
Config.write()
try:
    from pyzbar.pyzbar import decode
    from PIL import Image as PILImage
except ImportError:
    decode = None
    if DEBUG:
        print('[WARNING] pyzbar library not found. Barcode scanning will be disabled.')
# ==========================================
NativeLocationListener = None
PythonActivity = None
Context = None
LocationManager = None
Looper = None
if platform == 'android':
    try:
        from jnius import autoclass, java_method, PythonJavaClass
        from android.permissions import request_permissions, Permission
        Context = autoclass('android.content.Context')
        LocationManager = autoclass('android.location.LocationManager')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Looper = autoclass('android.os.Looper')

        class NativeLocationListener(PythonJavaClass):
            __javainterfaces__ = ['android/location/LocationListener']

            def __init__(self, callback):
                super().__init__()
                self.callback = callback

            @java_method('(Ljava/util/List;)V')
            @java_method('(Landroid/location/Location;)V')
            def onLocationChanged(self, args):
                try:
                    is_list = False
                    try:
                        if args and hasattr(args, 'size') and (args.size() >= 0):
                            is_list = True
                    except:
                        is_list = False
                    if is_list:
                        if args.size() > 0:
                            location = args.get(args.size() - 1)
                            self.callback(location)
                    else:
                        self.callback(args)
                except Exception as e:
                    print(f'GPS Error parsing location: {e}')

            @java_method('(Ljava/lang/String;)V')
            def onProviderEnabled(self, provider):
                pass

            @java_method('(Ljava/lang/String;)V')
            def onProviderDisabled(self, provider):
                pass

            @java_method('(Ljava/lang/String;ILandroid/os/Bundle;)V')
            def onStatusChanged(self, provider, status, extras):
                pass
    except Exception as e:
        print(f'[ERROR] Loading Native GPS classes: {e}')
# ==========================================
if platform == 'android':
    try:
        from jnius import autoclass
        BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
        BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
        UUID = autoclass('java.util.UUID')
        PowerManager = autoclass('android.os.PowerManager')
        AudioManager = autoclass('android.media.AudioManager')
        ToneGenerator = autoclass('android.media.ToneGenerator')
    except Exception as e:
        if DEBUG:
            print(f'[ERROR] Android libraries failed to load: {e}')
# ==========================================
app_dir = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(app_dir, 'font.ttf')
custom_font_loaded = False
try:
    if os.path.exists(FONT_FILE) and os.path.isfile(FONT_FILE):
        if DEBUG:
            print(f'[INFO] Found custom font at: {FONT_FILE}')
        LabelBase.register(name='ArabicFont', fn_regular=FONT_FILE, fn_bold=FONT_FILE)
        LabelBase.register(name='Roboto', fn_regular=FONT_FILE, fn_bold=FONT_FILE)
        LabelBase.register(name='RobotoMedium', fn_regular=FONT_FILE, fn_bold=FONT_FILE)
        LabelBase.register(name='RobotoBold', fn_regular=FONT_FILE, fn_bold=FONT_FILE)
        custom_font_loaded = True
    elif DEBUG:
        print('[WARNING] Custom font file NOT found. Using fallback.')
except Exception as e:
    print(f'[ERROR] Critical error loading custom font: {e}')
if not custom_font_loaded:
    fallback_regular = os.path.join(fonts_path, 'Roboto-Regular.ttf')
    fallback_bold = os.path.join(fonts_path, 'Roboto-Bold.ttf')
    try:
        LabelBase.register(name='ArabicFont', fn_regular=fallback_regular, fn_bold=fallback_bold)
    except Exception:
        LabelBase.register(name='ArabicFont', fn_regular=None, fn_bold=None)
# ==========================================
reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': True, 'support_ligatures': True, 'use_unshaped_instead_of_isolated': True})
# ==========================================
DEFAULT_PORT = '5000'
# ==========================================
KV_BUILDER = '\n<LeftButtonsContainer>:\n    adaptive_width: True\n    spacing: "4dp"\n    padding: "4dp"\n    pos_hint: {"center_y": .5}\n\n<RightButtonsContainer>:\n    adaptive_width: True\n    spacing: "8dp"\n    pos_hint: {"center_y": .5}\n\n<CustomHistoryItem>:\n    orientation: "horizontal"\n    size_hint_y: None\n    height: dp(80)\n    padding: dp(10)\n    spacing: dp(5)\n    radius: [10]\n    elevation: 1\n    ripple_behavior: True\n    md_bg_color: root.bg_color\n    on_release: root.on_tap_action()\n    \n    MDIcon:\n        icon: root.icon\n        theme_text_color: "Custom"\n        text_color: root.icon_color\n        pos_hint: {"center_y": .5}\n        font_size: "32sp"\n        size_hint_x: None\n        width: dp(40)\n        \n    MDBoxLayout:\n        orientation: "vertical"\n        pos_hint: {"center_y": .5}\n        spacing: dp(4)\n        size_hint_x: 0.5\n        \n        MDLabel:\n            text: root.text\n            bold: True\n            font_style: "Subtitle1"\n            font_size: "16sp"\n            theme_text_color: "Primary"\n            shorten: True\n            shorten_from: \'right\'\n            font_name: \'ArabicFont\'\n            markup: True\n            \n        MDLabel:\n            text: root.secondary_text\n            font_style: "Caption"\n            theme_text_color: "Secondary"\n            font_name: \'ArabicFont\'\n            \n    MDLabel:\n        text: root.right_text\n        halign: "right"\n        pos_hint: {"center_y": .5}\n        font_style: "Subtitle2"\n        bold: True\n        theme_text_color: "Custom"\n        text_color: root.icon_color\n        size_hint_x: 0.3\n        font_name: \'ArabicFont\'\n\n    MDIconButton:\n        icon: "pencil"\n        theme_text_color: "Custom"\n        text_color: (0, 0.5, 0.8, 1)\n        pos_hint: {"center_y": .5}\n        on_release: root.on_edit_action()\n\n<ProductRecycleItem>:\n    orientation: \'vertical\'\n    size_hint_y: None\n    height: dp(90)\n    padding: 0\n    spacing: 0\n    \n    MDCard:\n        orientation: \'horizontal\'\n        padding: dp(10)\n        spacing: dp(10)\n        radius: [8]\n        elevation: 1\n        ripple_behavior: True\n        on_release: root.on_tap()\n        md_bg_color: (1, 1, 1, 1)\n        \n        # --- قسم الصورة والأيقونة ---\n        MDCard:\n            size_hint: None, None\n            size: dp(50), dp(50)\n            radius: [5]\n            elevation: 0\n            md_bg_color: (0, 0, 0, 0)\n            pos_hint: {\'center_y\': .5}\n            ripple_behavior: True\n            on_release: root.on_image_tap()\n            \n            MDFloatLayout:\n                # تظهر الأيقونة فقط في حالة عدم وجود صورة\n                MDIcon:\n                    icon: root.icon_name\n                    theme_text_color: "Custom"\n                    text_color: root.icon_color\n                    pos_hint: {\'center_x\': .5, \'center_y\': .5}\n                    font_size: \'32sp\'\n                    opacity: 1 if not root.image_source else 0\n\n                # تظهر الصورة وتخفي الأيقونة\n                FitImage:\n                    source: root.image_source\n                    radius: [5]\n                    pos_hint: {\'center_x\': .5, \'center_y\': .5}\n                    opacity: 1 if root.image_source else 0\n        # ---------------------------\n\n        MDBoxLayout:\n            orientation: \'vertical\'\n            pos_hint: {\'center_y\': .5}\n            spacing: dp(5)\n            \n            MDLabel:\n                text: root.text_name\n                font_style: "Subtitle1"\n                bold: True\n                text_size: self.width, None\n                max_lines: 2\n                halign: \'left\'\n                font_size: \'17sp\'\n                theme_text_color: "Custom"\n                text_color: (0.1, 0.1, 0.1, 1)\n                font_name: \'ArabicFont\'\n            \n            MDBoxLayout:\n                orientation: \'horizontal\'\n                spacing: dp(10)\n                \n                MDLabel:\n                    text: root.text_price\n                    font_style: "H6"\n                    theme_text_color: "Custom"\n                    text_color: root.price_color\n                    bold: True\n                    size_hint_x: 0.6\n                    font_size: \'20sp\'\n                    font_name: \'ArabicFont\'\n                \n                MDLabel:\n                    text: root.text_stock\n                    theme_text_color: "Custom"\n                    text_color: (0.1, 0.1, 0.1, 1)\n                    halign: \'right\'\n                    size_hint_x: 0.4\n                    bold: True\n                    font_size: \'16sp\'\n                    font_name: \'ArabicFont\'\n\n<ProductRecycleView>:\n    viewclass: \'ProductRecycleItem\'\n    RecycleBoxLayout:\n        default_size: None, dp(95)\n        default_size_hint: 1, None\n        size_hint_y: None\n        height: self.minimum_height\n        orientation: \'vertical\'\n        spacing: dp(4)\n        padding: dp(5)\n\n<HistoryRecycleItem>:\n    orientation: "vertical"\n    size_hint_y: None\n    height: dp(135)\n    padding: dp(12)\n    spacing: dp(8)\n    radius: [15]\n    elevation: 2\n    ripple_behavior: True\n    md_bg_color: root.bg_color\n    on_release: root.on_tap()\n\n    # --- السطر الأول: الأيقونة + النوع + رقم الوصل ---\n    MDBoxLayout:\n        orientation: "horizontal"\n        size_hint_y: None\n        height: dp(40)\n        spacing: dp(10)\n\n        # خلفية دائرية للأيقونة\n        MDCard:\n            size_hint: None, None\n            size: dp(40), dp(40)\n            radius: [20]\n            md_bg_color: (0.95, 0.95, 0.95, 1)\n            elevation: 0\n            pos_hint: {"center_y": .5}\n            \n            MDIcon:\n                icon: root.icon_name\n                theme_text_color: "Custom"\n                text_color: root.icon_color\n                pos_hint: {"center_x": .5, "center_y": .5}\n                font_size: "24sp"\n\n        MDBoxLayout:\n            orientation: "vertical"\n            spacing: dp(2)\n            pos_hint: {"center_y": .5}\n\n            # 1. نوع العملية\n            MDLabel:\n                text: root.text_type\n                bold: True\n                font_style: "Subtitle1"\n                theme_text_color: "Primary"\n                font_name: \'ArabicFont\'\n                halign: "left"\n                valign: "bottom"\n\n            # 2. رقم الوصل - المستخدم\n            MDLabel:\n                text: root.text_ref\n                font_style: "Caption"\n                theme_text_color: "Secondary"\n                font_name: \'ArabicFont\'\n                halign: "left"\n                valign: "top"\n\n    # --- السطر الثاني: الاسم (يسمح بالالتفاف) ---\n    # 3. الاسم\n    MDLabel:\n        text: root.text_entity\n        font_style: "H6"\n        font_size: "17sp"\n        bold: True\n        theme_text_color: "Custom"\n        text_color: (0.1, 0.1, 0.1, 1)\n        font_name: \'ArabicFont\'\n        size_hint_y: None\n        height: self.texture_size[1]\n        text_size: self.width, None\n        max_lines: 2\n        halign: "left"\n\n    # مساحة مرنة\n    MDBoxLayout:\n        size_hint_y: 1\n\n    # --- السطر الثالث: الوقت + السعر ---\n    MDBoxLayout:\n        orientation: "horizontal"\n        size_hint_y: None\n        height: dp(25)\n        \n        # 5. الوقت\n        MDLabel:\n            text: root.text_date\n            font_style: "Caption"\n            theme_text_color: "Hint"\n            halign: "left"\n            valign: "center"\n            size_hint_x: 0.4\n            font_name: \'ArabicFont\'\n\n        # 4. السعر\n        MDLabel:\n            text: root.text_amount\n            font_style: "Subtitle1"\n            bold: True\n            theme_text_color: "Custom"\n            text_color: root.icon_color\n            halign: "right"\n            valign: "center"\n            font_size: "18sp"\n            size_hint_x: 0.6\n            font_name: \'ArabicFont\'\n\n<HistoryRecycleView>:\n    viewclass: \'HistoryRecycleItem\'\n    RecycleBoxLayout:\n        default_size: None, dp(140)\n        default_size_hint: 1, None\n        size_hint_y: None\n        height: self.minimum_height\n        orientation: \'vertical\'\n        spacing: dp(5)\n        padding: dp(5)\n\n<EntityRecycleItem>:\n    orientation: "horizontal"\n    size_hint_y: None\n    height: dp(80)\n    padding: dp(10)\n    spacing: dp(15)\n    ripple_behavior: True\n    md_bg_color: (1, 1, 1, 1)\n    radius: [0]\n    on_release: root.on_tap()\n\n    MDIcon:\n        icon: root.icon_name\n        theme_text_color: "Custom"\n        text_color: root.icon_color\n        pos_hint: {"center_y": .5}\n        font_size: "32sp"\n        size_hint_x: None\n        width: dp(40)\n\n    MDBoxLayout:\n        orientation: "vertical"\n        pos_hint: {"center_y": .5}\n        size_hint_x: 1\n        spacing: dp(4)\n\n        MDLabel:\n            text: root.text_name\n            bold: True\n            font_style: "Subtitle1"\n            font_name: \'ArabicFont\'\n            theme_text_color: "Custom"\n            text_color: (0.1, 0.1, 0.1, 1)\n            shorten: True\n            shorten_from: \'right\'\n            valign: \'center\'\n\n        MDLabel:\n            text: root.text_balance\n            font_style: "Caption"\n            font_name: \'ArabicFont\'\n            markup: True\n            theme_text_color: "Secondary"\n            valign: \'top\'\n\n<EntityRecycleView>:\n    viewclass: \'EntityRecycleItem\'\n    RecycleBoxLayout:\n        default_size: None, dp(80)\n        default_size_hint: 1, None\n        size_hint_y: None\n        height: self.minimum_height\n        orientation: \'vertical\'\n        spacing: dp(2)\n        padding: dp(0)\n\n<MgmtEntityRecycleItem>:\n    orientation: "horizontal"\n    size_hint_y: None\n    height: dp(80)\n    padding: dp(10)\n    spacing: dp(5)\n    ripple_behavior: True\n    md_bg_color: (1, 1, 1, 1)\n    on_release: root.on_pay()\n\n    MDIcon:\n        icon: "account-circle"\n        theme_text_color: "Custom"\n        text_color: (0.5, 0.5, 0.5, 1)\n        pos_hint: {"center_y": .5}\n        font_size: "32sp"\n        size_hint_x: None\n        width: dp(40)\n\n    MDBoxLayout:\n        orientation: "vertical"\n        pos_hint: {"center_y": .5}\n        size_hint_x: 1\n        spacing: dp(2)\n        padding: [dp(10), 0, 0, 0]\n\n        MDLabel:\n            text: root.text_name\n            bold: True\n            font_style: "Subtitle1"\n            font_name: \'ArabicFont\'\n            theme_text_color: "Custom"\n            text_color: (0.1, 0.1, 0.1, 1)\n            shorten: True\n            shorten_from: \'right\'\n            halign: "left"\n\n        MDLabel:\n            text: root.text_balance\n            font_style: "Caption"\n            font_name: \'ArabicFont\'\n            markup: True\n            theme_text_color: "Secondary"\n            halign: "left"\n\n    MDIconButton:\n        icon: "clock-time-eight-outline"\n        theme_text_color: "Custom"\n        text_color: (0, 0.5, 0.5, 1)\n        pos_hint: {"center_y": .5}\n        on_release: root.on_history()\n\n<MgmtEntityRecycleView>:\n    viewclass: \'MgmtEntityRecycleItem\'\n    RecycleBoxLayout:\n        default_size: None, dp(80)\n        default_size_hint: 1, None\n        size_hint_y: None\n        height: self.minimum_height\n        orientation: \'vertical\'\n        spacing: dp(2)\n        padding: dp(0)\n\n<CartRecycleItem>:\n    orientation: "horizontal"\n    size_hint_y: None\n    height: dp(85)\n    padding: [dp(15), 0, 0, 0]\n    md_bg_color: 1, 1, 1, 1\n    radius: [0]\n    ripple_behavior: True\n    on_release: root.on_tap()\n\n    MDBoxLayout:\n        orientation: "vertical"\n        pos_hint: {"center_y": .5}\n        adaptive_height: True\n        spacing: dp(4)\n\n        MDLabel:\n            text: root.text_name\n            font_style: "Subtitle1"\n            bold: True\n            theme_text_color: "Primary"\n            adaptive_height: True\n            font_name: \'ArabicFont\'\n\n        MDLabel:\n            text: root.text_details\n            font_size: "16sp"\n            theme_text_color: "Custom"\n            text_color: root.details_color\n            bold: True\n            adaptive_height: True\n            font_name: \'ArabicFont\'\n\n    MDIconButton:\n        icon: "delete"\n        theme_text_color: "Custom"\n        text_color: (0.9, 0, 0, 1)\n        pos_hint: {"center_y": .5}\n        icon_size: "24sp"\n        on_release: root.on_delete()\n\n<CartRecycleView>:\n    viewclass: \'CartRecycleItem\'\n    RecycleBoxLayout:\n        default_size: None, dp(85)\n        default_size_hint: 1, None\n        size_hint_y: None\n        height: self.minimum_height\n        orientation: \'vertical\'\n        spacing: dp(1)\n'
# ==========================================
class KalmanLatLon:

    def __init__(self, Q_metres_per_second):
        self.Q_metres_per_second = Q_metres_per_second
        self.TimeStamp_milliseconds = 0
        self.lat = 0
        self.lon = 0
        self.variance = -1

    def process(self, lat_measurement, lon_measurement, accuracy, time_stamp_ms):
        if self.variance < 0:
            self.TimeStamp_milliseconds = time_stamp_ms
            self.lat = lat_measurement
            self.lon = lon_measurement
            self.variance = accuracy * accuracy
        else:
            time_inc_ms = time_stamp_ms - self.TimeStamp_milliseconds
            if time_inc_ms > 0:
                self.variance += time_inc_ms * self.Q_metres_per_second * self.Q_metres_per_second / 1000
                self.TimeStamp_milliseconds = time_stamp_ms
            K = self.variance / (self.variance + accuracy * accuracy)
            self.lat += K * (lat_measurement - self.lat)
            self.lon += K * (lon_measurement - self.lon)
            self.variance = (1 - K) * self.variance
        return (self.lat, self.lon)

class CartRecycleItem(RecycleDataViewBehavior, MDCard):
    text_name = StringProperty('')
    text_details = StringProperty('')
    details_color = ListProperty([0.4, 0.4, 0.4, 1])
    raw_data = ObjectProperty(None)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        app = MDApp.get_running_app()
        self.text_name = app.fix_text(data.get('name', ''))
        self.text_details = data.get('details', '')
        self.details_color = data.get('d_color', [0.4, 0.4, 0.4, 1])
        self.raw_data = data.get('raw_item')
        return super().refresh_view_attrs(rv, index, data)

    def on_tap(self):
        MDApp.get_running_app().edit_cart_item(self.raw_data)

    def on_delete(self):
        MDApp.get_running_app().remove_from_cart(self.raw_data)

class CartRecycleView(RecycleView):

    def __init__(self, **kwargs):
        super(CartRecycleView, self).__init__(**kwargs)
        self.data = []

class NoMenuTextField(MDTextField):

    def _show_cut_copy_paste(self, pos, selection, mode=None):
        pass

    def on_double_tap(self):
        pass

class DataValidator:

    @staticmethod
    def validate_ip(ip_address):
        if not ip_address or not isinstance(ip_address, str):
            return False
        return len(ip_address) > 3

class SmartTextField(MDTextField):

    def __init__(self, **kwargs):
        self._raw_text = ''
        self.base_direction = 'ltr'
        self.halign = 'left'
        self._input_reshaper = arabic_reshaper.ArabicReshaper(configuration={'delete_harakat': True, 'support_ligatures': False, 'use_unshaped_instead_of_isolated': True})
        super().__init__(**kwargs)
        self.font_name = 'ArabicFont'
        self.font_name_hint_text = 'ArabicFont'
        self.keyboard_suggestions = False
        if self.text:
            self._raw_text = self.text
            self._update_display()

    def insert_text(self, substring, from_undo=False):
        self._raw_text += substring
        self._update_display()

    def do_backspace(self, from_undo=False, mode='bkspc'):
        if not self._raw_text:
            return
        self._raw_text = self._raw_text[:-1]
        self._update_display()

    def _update_display(self):
        if self._raw_text:
            try:
                reshaped = self._input_reshaper.reshape(self._raw_text)
                bidi_text = get_display(reshaped)
                self.text = bidi_text
            except Exception:
                self.text = self._raw_text
        else:
            self.text = ''
        self._update_alignment(self._raw_text)
        Clock.schedule_once(self._set_cursor_to_end, 0)

    def _set_cursor_to_end(self, dt):
        self.cursor = (len(self.text), 0)

    def _update_alignment(self, text):
        if not text:
            self.halign = 'left'
            self.base_direction = 'ltr'
            return
        has_arabic = any(('\u0600' <= c <= 'ۿ' or 'ݐ' <= c <= 'ݿ' or 'ﭐ' <= c <= 'ﰿ' or ('ﹰ' <= c <= '\ufeff') for c in text))
        if has_arabic:
            self.halign = 'right'
            self.base_direction = 'rtl'
        else:
            self.halign = 'left'
            self.base_direction = 'ltr'

    def get_value(self):
        if not self._raw_text and self.text:
            return self.text
        return self._raw_text

    def on_text(self, instance, value):
        if value == '' and self._raw_text != '':
            self._raw_text = ''
        pass

class LeftButtonsContainer(ILeftBody, MDBoxLayout):
    adaptive_width = True

class RightButtonsContainer(IRightBodyTouch, MDBoxLayout):
    adaptive_width = True

class ClickableBox(KivyButtonBehavior, MDBoxLayout):
    pass

class ProductRecycleItem(RecycleDataViewBehavior, MDBoxLayout):
    index = None
    text_name = StringProperty('')
    text_category = StringProperty('')
    text_price = StringProperty('')
    text_stock = StringProperty('')
    icon_name = StringProperty('package-variant')
    icon_color = ListProperty([0, 0, 0, 1])
    price_color = ListProperty([0, 0, 0, 1])
    image_source = StringProperty('')
    product_data = ObjectProperty(None)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        self.text_name = data.get('name', '')
        self.text_category = data.get('category', '')
        self.text_price = data.get('price_text', '')
        self.text_stock = data.get('stock_text', '')
        self.icon_name = data.get('icon', 'package-variant')
        self.icon_color = data.get('icon_color', [0, 0, 0, 1])
        self.price_color = data.get('price_color', [0, 0, 0, 1])
        self.image_source = data.get('image_url', '')
        self.product_data = data.get('raw_data')
        return super().refresh_view_attrs(rv, index, data)

    def on_tap(self):
        app = MDApp.get_running_app()
        if self.product_data:
            app.open_add_to_cart_dialog(self.product_data, app.current_mode)

    def on_image_tap(self):
        if self.image_source:
            app = MDApp.get_running_app()
            app.show_zoomed_image(self.image_source, self.text_name)

class HistoryRecycleItem(RecycleDataViewBehavior, MDCard):
    index = None
    text_type = StringProperty('')
    text_ref = StringProperty('')
    text_entity = StringProperty('')
    text_date = StringProperty('')
    text_amount = StringProperty('')
    icon_name = StringProperty('file')
    icon_color = ColorProperty([0, 0, 0, 1])
    bg_color = ColorProperty([1, 1, 1, 1])
    item_data = ObjectProperty(None, allownone=True)
    is_local = BooleanProperty(False)
    key = StringProperty('')

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        app = MDApp.get_running_app()
        self.text_type = app.fix_text(data.get('type_str', ''))
        self.text_ref = app.fix_text(data.get('ref_str', ''))
        self.text_entity = app.fix_text(data.get('entity_str', ''))
        self.text_date = data.get('date_str', '')
        self.text_amount = data.get('amount_text', '')
        self.icon_name = data.get('icon', 'file')
        self.icon_color = data.get('icon_color', [0, 0, 0, 1])
        self.bg_color = data.get('bg_color', [1, 1, 1, 1])
        self.item_data = data.get('raw_data')
        self.is_local = data.get('is_local', False)
        self.key = data.get('key', '')
        return super().refresh_view_attrs(rv, index, data)

    def on_tap(self):
        app = MDApp.get_running_app()
        if self.is_local:
            app.handle_pending_item(self.key, False)
        elif self.item_data:
            app.handle_server_history_item(self.item_data)

class MgmtEntityRecycleItem(RecycleDataViewBehavior, MDCard):
    index = None
    text_name = StringProperty('')
    text_balance = StringProperty('')
    entity_data = ObjectProperty(None, allownone=True)
    _long_press_event = None
    _is_long_press = False
    _start_pos = (0, 0)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        app = MDApp.get_running_app()
        raw_name = data.get('raw_name', '')
        self.text_name = app.fix_text(raw_name) if app else raw_name
        self.text_balance = data.get('balance_text', '')
        self.entity_data = data.get('raw_data')
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._is_long_press = False
            self._start_pos = touch.pos
            self._long_press_event = Clock.schedule_once(lambda dt: self._trigger_long_press(), 0.5)
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self._long_press_event:
            diff_x = abs(touch.x - self._start_pos[0])
            diff_y = abs(touch.y - self._start_pos[1])
            if diff_x > dp(20) or diff_y > dp(20):
                self._long_press_event.cancel()
                self._long_press_event = None
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self._long_press_event:
            self._long_press_event.cancel()
            self._long_press_event = None
        if self._is_long_press:
            return True
        return super().on_touch_up(touch)

    def _trigger_long_press(self):
        self._is_long_press = True
        self.on_menu()

    def on_pay(self):
        if self._is_long_press:
            return
        app = MDApp.get_running_app()
        if self.entity_data:
            app.start_direct_payment_from_manager(self.entity_data)

    def on_menu(self):
        app = MDApp.get_running_app()
        if self.entity_data:
            app.open_entity_edit_menu(self.entity_data)

    def on_history(self):
        app = MDApp.get_running_app()
        if self.entity_data:
            app.open_entity_history_dialog(self.entity_data)

    def on_edit(self):
        pass

class EntityRecycleItem(RecycleDataViewBehavior, MDCard):
    index = None
    text_name = StringProperty('')
    text_balance = StringProperty('')
    icon_name = StringProperty('account')
    icon_color = ListProperty([0, 0, 0, 1])
    entity_data = ObjectProperty(None, allownone=True)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        app = MDApp.get_running_app()
        raw_name = data.get('raw_name', '')
        self.text_name = app.fix_text(raw_name) if app else raw_name
        self.text_balance = data.get('balance_text', '')
        self.icon_name = data.get('icon', 'account')
        self.icon_color = data.get('icon_color', [0, 0, 0, 1])
        self.entity_data = data.get('raw_data')
        return super().refresh_view_attrs(rv, index, data)

    def on_tap(self):
        app = MDApp.get_running_app()
        if self.entity_data:
            app.select_entity_from_rv(self.entity_data)

class HistoryRecycleView(RecycleView):

    def __init__(self, **kwargs):
        super(HistoryRecycleView, self).__init__(**kwargs)
        self.data = []

class MgmtEntityRecycleView(RecycleView):

    def __init__(self, **kwargs):
        super(MgmtEntityRecycleView, self).__init__(**kwargs)
        self.data = []

class EntityRecycleView(RecycleView):

    def __init__(self, **kwargs):
        super(EntityRecycleView, self).__init__(**kwargs)
        self.data = []

class ProductRecycleView(RecycleView):
    loading_lock = False

    def __init__(self, **kwargs):
        super(ProductRecycleView, self).__init__(**kwargs)
        self.data = []

    def on_scroll_y(self, instance, value):
        if value <= 0.2 and (not self.loading_lock) and (not MDApp.get_running_app().is_loading_more):
            app = MDApp.get_running_app()
            if app and app.current_page_offset < len(app.current_product_list_source):
                self.loading_lock = True
                app.load_more_products()

class StockApp(MDApp):
    cart = []
    all_products_raw = []
    all_clients = []
    all_suppliers = []
    last_ping = 0
    current_mode = 'sale'
    local_server_ip = '192.168.1.100'
    external_server_ip = ''
    active_server_ip = '192.168.1.100'
    current_user_name = 'ADMIN'
    is_server_reachable = False
    is_offline_mode = False
    sync_paused = False
    is_seller_mode = BooleanProperty(False)
    selected_location = 'store'
    selected_entity = None
    editing_transaction_key = None
    current_editing_server_id = None
    editing_payment_amount = None
    offline_store = None
    cache_store = None
    store = None
    stats_store = None
    dialog = None
    status_bar_label = None
    status_bar_bg = None
    rv_products = None
    _notify_event = None
    _heartbeat_event = None
    _ready_timer = None
    entity_list_layout = None
    history_list_layout = None
    pending_dialog = None
    action_dialog = None
    srv_dialog = None
    stat_sales_today = NumericProperty(0)
    stat_purchases_today = NumericProperty(0)
    stat_client_payments = NumericProperty(0)
    stat_supplier_payments = NumericProperty(0)
    stat_net_total = NumericProperty(0)
    buttons_container = None
    stats_container = None
    cart_list_layout = None
    lbl_cart_count = None
    lbl_cart_total = None
    lbl_total_title = None
    current_entity_type_mgmt = 'account'
    DOC_TRANSLATIONS = {'BV': 'Bon de Vente', 'BA': "Bon d'Achat", 'FC': 'Facture Vente', 'FF': 'Facture Achat', 'RC': 'Retour Client', 'RF': 'Retour Fournisseur', 'TR': 'Transfert de Stock', 'FP': 'Facture Proforma', 'DP': 'Bon de Commande', 'BI': 'Bon Initial'}
    current_product_list_source = []
    current_page_offset = 0
    batch_size = 50
    is_loading_more = False

    def set_screen_keep_alive(self, active):
        self.store.put('screen_config', keep_on=active)
        if platform == 'android':
            from jnius import autoclass
            from android.runnable import run_on_ui_thread

            @run_on_ui_thread
            def update_android_flag(keep_on):
                try:
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    activity = PythonActivity.mActivity
                    window = activity.getWindow()
                    if keep_on:
                        window.addFlags(128)
                    else:
                        window.clearFlags(128)
                except Exception as e:
                    print(f'Erreur Screen Flag: {e}')
            update_android_flag(active)

    def on_pause(self):
        return True

    def fix_text(self, text):
        if not text or not isinstance(text, str):
            return str(text) if text is not None else ''
        if any(('\u0600' <= c <= 'ۿ' for c in text)):
            try:
                reshaped_text = reshaper.reshape(text)
                return get_display(reshaped_text)
            except Exception:
                return text
        return text

    def prepare_products_for_rv(self, products_list):
        self.current_product_list_source = products_list
        self.current_page_offset = 0
        self.is_loading_more = False
        if self.rv_products:
            if not self.rv_products.data:
                self.rv_products.refresh_from_data()
        self.load_more_products(reset=True)

    def load_more_products(self, reset=False):
        if self.is_loading_more and (not reset):
            return
        if reset:
            self.current_page_offset = 0
            self.is_loading_more = False
            if self.rv_products:
                self.rv_products.scroll_y = 1.0
                self.rv_products.data = []
        total_items = len(self.current_product_list_source)
        if self.current_page_offset >= total_items:
            return
        self.is_loading_more = True
        start = self.current_page_offset
        end = min(start + 30, total_items)
        batch = self.current_product_list_source[start:end]
        threading.Thread(target=self._process_batch_data, args=(batch, reset), daemon=True).start()

    def get_cached_image_url(self, image_path_from_server):
        if not image_path_from_server:
            return ''
        filename = os.path.basename(image_path_from_server.replace('\\', '/'))
        local_path = os.path.join(self.image_cache_dir, filename)
        if os.path.exists(local_path):
            return local_path
        base_url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/images/'
        import urllib.parse
        clean_path = image_path_from_server.replace('\\', '/')
        encoded_path = urllib.parse.quote(clean_path)
        server_url = f'{base_url}{encoded_path}'
        self._cache_image_background(server_url, local_path)
        return server_url

    def _cache_image_background(self, url, local_path):

        def on_success(req, result):
            try:
                with open(local_path, 'wb') as f:
                    f.write(result)
            except:
                pass
        UrlRequest(url, on_success=on_success)

    def open_image_selector(self, instance):
        if platform == 'android':
            from android.permissions import request_permissions, Permission

            def on_perm(permissions, grants):
                if grants and grants[0]:
                    self._open_file_chooser()
                else:
                    self.notify('Permission refusée', 'error')
            request_permissions([Permission.READ_EXTERNAL_STORAGE], on_perm)
        else:
            self._open_file_chooser()

    def _open_file_chooser(self):
        try:
            if platform == 'android':
                from plyer import filechooser
                filechooser.open_file(on_selection=self._on_image_selected, filters=['*.png', '*.jpg', '*.jpeg'])
            else:
                try:
                    from plyer import filechooser
                    filechooser.open_file(on_selection=self._on_image_selected, filters=['*.png', '*.jpg', '*.jpeg'])
                except:
                    self.notify('Sélecteur de fichiers non supporté sur ce système', 'error')
        except Exception as e:
            self.notify(f'Erreur sélecteur: {e}', 'error')

    def _on_image_selected(self, selection):
        if not selection:
            return
        try:
            image_path = selection[0]
            ext = os.path.splitext(image_path)[1].lower()
            if ext not in ['.png', '.jpg', '.jpeg']:
                self.notify('Format non supporté', 'error')
                return
            self.temp_selected_image_path = image_path
            self.remove_image_order = False
            if hasattr(self, 'lbl_image_status'):
                self.lbl_image_status.text = f'Image: {os.path.basename(image_path)}'
                self.lbl_image_status.text_color = (0, 0.6, 0, 1)
            self.notify('Image sélectionnée', 'success')
        except Exception as e:
            self.notify(f'Erreur image: {e}', 'error')

    def _process_batch_data(self, batch, reset=False):
        rv_data = []
        is_sale = self.current_mode in ['sale', 'return_sale', 'invoice_sale', 'proforma']
        is_transfer = self.current_mode == 'transfer'
        allowed_autre_modes = ['sale', 'invoice_sale', 'proforma', 'order_purchase', 'return_sale']

        def fmt_qty(val):
            try:
                val = float(val)
                if val.is_integer():
                    return str(int(val))
                return str(val)
            except:
                return '0'
        for p in batch:
            try:
                name = self.fix_text(str(p.get('name', '')))
                if str(p.get('name', '')).lower().startswith('autre article'):
                    if self.current_mode not in allowed_autre_modes:
                        continue
                    if getattr(self, 'user_sales_mode', 'store') == 'truck':
                        continue
                s_store = float(p.get('stock', 0) or 0)
                s_wh = float(p.get('stock_warehouse', 0) or 0)
                total_stock = s_store + s_wh
                if is_transfer:
                    if s_store <= -900000 or s_wh <= -900000 or total_stock < 0:
                        continue
                raw_cat = str(p.get('category', ''))
                if raw_cat.lower() == 'none':
                    category = ''
                else:
                    category = self.fix_text(raw_cat)
                image_path_raw = p.get('image', '')
                final_image_source = self.get_cached_image_url(image_path_raw)
                if is_transfer:
                    price_fmt = f'Qnt Tot: {fmt_qty(total_stock)}'
                    p_color = [0.2, 0.2, 0.8, 1]
                elif is_sale:
                    price = float(p.get('price', 0) or 0)
                    price_fmt = f'{price:.2f} DA'
                    p_color = [0, 0.6, 0, 1] if not p.get('has_promo') else [0.5, 0, 0.5, 1]
                else:
                    p_price = p.get('purchase_price')
                    if p_price is None:
                        p_price = p.get('price', 0)
                    price = float(p_price or 0)
                    price_fmt = f'{price:.2f} DA'
                    p_color = [0.9, 0.5, 0, 1]
                stock_text = ''
                if is_transfer:
                    stock_text = f'Mag: {fmt_qty(s_store)} | Dép: {fmt_qty(s_wh)}'
                elif s_store <= -900000 or s_wh <= -900000:
                    stock_text = 'Illimité'
                elif s_wh != 0:
                    stock_text = f'Qté: {fmt_qty(s_store)} | Dép: {fmt_qty(s_wh)}'
                else:
                    stock_text = f'Qté: {fmt_qty(s_store)}'
                icon_name = 'package-variant' if total_stock > 0 or s_store <= -900000 or s_wh <= -900000 else 'package-variant-closed'
                icon_color = [0, 0.6, 0, 1] if total_stock > 0 or s_store <= -900000 else [0.8, 0, 0, 1]
                rv_data.append({'text_name': name, 'text_category': category, 'text_price': price_fmt, 'text_stock': stock_text, 'icon_name': icon_name, 'icon_color': icon_color, 'price_color': p_color, 'image_url': final_image_source, 'raw_data': p})
            except Exception as e:
                print(f'Error processing item: {e}')
                continue
        self._append_to_rv(rv_data, reset)

    @mainthread
    def _append_to_rv(self, new_data, reset=False):
        if self.rv_products:
            if reset:
                self.rv_products.data = new_data
                self.rv_products.scroll_y = 1.0
                self.current_page_offset = len(new_data)
            else:
                self.rv_products.data.extend(new_data)
                self.current_page_offset += len(new_data)
            self.rv_products.refresh_from_data()
        if self.rv_products:
            self.rv_products.loading_lock = False
        self.is_loading_more = False

    def filter_products(self, instance, text):
        query = instance.get_value() if hasattr(instance, 'get_value') else text
        if self._search_event:
            self._search_event.cancel()
        self._search_event = Clock.schedule_once(lambda dt: self._start_background_search(query), 0.3)

    def _start_background_search(self, query):
        threading.Thread(target=self._search_worker, args=(query,), daemon=True).start()

    def _search_worker(self, query):
        if not query:
            self._prepare_and_send_data(self.all_products_raw[:50])
            return
        query_clean = query.lower().strip()
        tokens = query_clean.split()
        filtered = [p for p in self.all_products_raw if all((token in str(p.get('name', '')).lower() for token in tokens)) or query_clean in str(p.get('barcode', '')).lower() or query_clean in str(p.get('product_ref', '')).lower()]
        self._prepare_and_send_data(filtered[:50])

    def _prepare_and_send_data(self, products_list):
        rv_data = []
        is_sale = self.current_mode in ['sale', 'return_sale', 'invoice_sale', 'proforma']
        is_transfer = self.current_mode == 'transfer'
        allowed_autre_modes = ['sale', 'invoice_sale', 'proforma', 'order_purchase', 'return_sale']

        def fmt_qty(val):
            try:
                val = float(val)
                if val.is_integer():
                    return str(int(val))
                return str(val)
            except:
                return '0'
        try:
            for p in products_list:
                prod_name_lower = str(p.get('name', '')).lower()
                if prod_name_lower.startswith('autre article'):
                    if self.current_mode not in allowed_autre_modes:
                        continue
                    if getattr(self, 'user_sales_mode', 'store') == 'truck':
                        continue
                s_store = float(p.get('stock', 0) or 0)
                s_wh = float(p.get('stock_warehouse', 0) or 0)
                total_stock = s_store + s_wh
                if is_transfer:
                    if s_store <= -900000 or s_wh <= -900000 or total_stock < 0:
                        continue
                price_fmt = ''
                price_color = [0, 0, 0, 1]
                stock_text = ''
                if is_transfer:
                    price_fmt = f'Qnt Tot: {fmt_qty(total_stock)}'
                    price_color = [0.2, 0.2, 0.8, 1]
                    stock_text = f'Mag: {fmt_qty(s_store)} | Dép: {fmt_qty(s_wh)}'
                else:
                    if is_sale:
                        price = float(p.get('price', 0) or 0)
                        price_fmt = f'{price:.2f} DA'
                        price_color = [0, 0.6, 0, 1]
                    else:
                        p_price = p.get('purchase_price')
                        if p_price is None:
                            p_price = p.get('price', 0)
                        price = float(p_price or 0)
                        price_fmt = f'{price:.2f} DA'
                        price_color = [0.9, 0.5, 0, 1]
                    if s_store <= -900000 or s_wh <= -900000:
                        stock_text = 'Illimité'
                    elif s_wh != 0:
                        stock_text = f'Qté: {fmt_qty(s_store)} | Dép: {fmt_qty(s_wh)}'
                    else:
                        stock_text = f'Qté: {fmt_qty(s_store)}'
                icon = 'package-variant' if total_stock > 0 or s_store <= -900000 or s_wh <= -900000 else 'package-variant-closed'
                icon_col = [0, 0.6, 0, 1] if total_stock > 0 or s_store <= -900000 or s_wh <= -900000 else [0.8, 0, 0, 1]
                raw_name = str(p.get('name', 'Inconnu'))
                display_name = self.fix_text(raw_name)
                image_path_raw = p.get('image', '')
                final_image_source = self.get_cached_image_url(image_path_raw)
                rv_data.append({'text_name': display_name, 'text_category': self.fix_text(str(p.get('category', ''))), 'text_price': price_fmt, 'text_stock': stock_text, 'icon_name': icon, 'icon_color': icon_col, 'price_color': price_color, 'image_url': final_image_source, 'raw_data': p})
        except Exception as e:
            print(f'Data Prep Error: {e}')
        self._apply_search_results(rv_data)

    def play_sound(self, type_):
        if platform == 'android' and hasattr(self, 'tone_gen') and self.tone_gen:
            try:
                if type_ == 'success':
                    self.tone_gen.startTone(24, 150)
                elif type_ == 'error':
                    self.tone_gen.startTone(97, 300)
                elif type_ == 'duplicate':
                    self.tone_gen.startTone(29, 150)
            except:
                pass

    def play_beep(self):
        if platform == 'android' and hasattr(self, 'tone_gen') and self.tone_gen:
            try:
                self.tone_gen.startTone(24, 150)
            except:
                pass

    @mainthread
    def _apply_search_results(self, rv_data):
        if self.rv_products:
            self.rv_products.data = rv_data
            self.rv_products.refresh_from_data()

    def open_bluetooth_selector(self, instance):
        if platform != 'android':
            self.notify('Fonction disponible uniquement sur Android', 'error')
            return
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self.notify('Bluetooth désactivé !', 'error')
                return
            paired_devices = adapter.getBondedDevices().toArray()
            content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(400))
            scroll = MDScrollView()
            list_layout = MDList()
            if not paired_devices:
                list_layout.add_widget(OneLineListItem(text='Aucun appareil associé (Paired)'))
            else:
                for device in paired_devices:
                    d_name = device.getName()
                    d_mac = device.getAddress()
                    item = TwoLineAvatarIconListItem(text=d_name, secondary_text=d_mac, on_release=lambda x, name=d_name, mac=d_mac: self.select_printer(name, mac))
                    item.add_widget(IconLeftWidget(icon='printer-wireless'))
                    list_layout.add_widget(item)
            scroll.add_widget(list_layout)
            content.add_widget(scroll)
            self.bt_dialog = MDDialog(title='Choisir Imprimante', type='custom', content_cls=content, buttons=[MDFlatButton(text='ANNULER', on_release=lambda x: self.bt_dialog.dismiss())])
            self.bt_dialog.open()
        except Exception as e:
            self.notify(f'Erreur Bluetooth: {e}', 'error')

    def select_printer(self, name, mac):
        current_auto = False
        if self.store.exists('printer_config'):
            current_auto = self.store.get('printer_config').get('auto', False)
        self.store.put('printer_config', name=name, mac=mac, auto=current_auto)
        self.temp_selected_mac = mac
        if hasattr(self, 'printer_name_field') and self.printer_name_field:
            self.printer_name_field.text = name
            self.printer_name_field.helper_text = f'ID: {mac}'
        if self.bt_dialog:
            self.bt_dialog.dismiss()
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.dismiss()
            self.open_ip_settings()
        self.notify(f'تم حفظ الطابعة: {name}', 'success')

    def clear_printer_selection(self, instance):
        self.store.put('printer_config', name='', mac='', auto=False)
        self.temp_selected_mac = ''
        if hasattr(self, 'printer_name_field') and self.printer_name_field:
            self.printer_name_field.text = ''
            self.printer_name_field.helper_text = 'Imprimante non définie'
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.dismiss()
            self.open_ip_settings()
        self.notify('تم حذف الطابعة', 'info')

    def print_ticket_bluetooth(self, transaction_data):
        if platform != 'android':
            return
        if not self.store.exists('printer_config'):
            self.notify('Imprimante non configurée', 'error')
            return
        config = self.store.get('printer_config')
        target_mac = config.get('mac', '').strip()
        if not target_mac:
            return
        socket = None
        try:
            adapter = BluetoothAdapter.getDefaultAdapter()
            if not adapter or not adapter.isEnabled():
                self.notify('Bluetooth OFF', 'error')
                return
            device = adapter.getRemoteDevice(target_mac)
            uuid = UUID.fromString('00001101-0000-1000-8000-00805F9B34FB')
            img = self.create_receipt_image(transaction_data)
            raster_data = self.get_image_raster_data(img)
            socket = device.createRfcommSocketToServiceRecord(uuid)
            socket.connect()
            time.sleep(0.2)
            output_stream = socket.getOutputStream()
            ESC = b'\x1b'
            GS = b'\x1d'
            INIT = ESC + b'@'
            CUT = GS + b'V\x00'
            output_stream.write(INIT)
            output_stream.flush()
            time.sleep(0.1)
            chunk_size = 1024
            for i in range(0, len(raster_data), chunk_size):
                output_stream.write(raster_data[i:i + chunk_size])
                output_stream.flush()
                time.sleep(0.03)
            output_stream.write(b'\n\n')
            output_stream.write(CUT)
            output_stream.flush()
            time.sleep(0.5)
            socket.close()
        except Exception as e:
            try:
                if socket:
                    socket.close()
            except:
                pass
            print(f'Print Image Error: {e}')

    def get_wrapped_text(self, text, font, max_width):
        lines = []
        if not text:
            return lines
        words = text.split(' ')
        current_line = []
        for word in words:
            current_line.append(word)
            line_str = ' '.join(current_line)
            bbox = font.getbbox(line_str)
            w = bbox[2] - bbox[0]
            if w > max_width:
                if len(current_line) == 1:
                    lines.append(current_line[0])
                    current_line = []
                else:
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        return lines

    def create_receipt_image(self, transaction_data):
        PAPER_WIDTH = 576
        margin = 10
        img_height = 4500
        image = Image.new('RGB', (PAPER_WIDTH, img_height), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        try:
            font_size_reg = 24
            font_size_large = 40
            font_size_med = 28
            font_reg = ImageFont.truetype(FONT_FILE, font_size_reg)
            font_bold = ImageFont.truetype(FONT_FILE, font_size_reg)
            font_large = ImageFont.truetype(FONT_FILE, font_size_large)
            font_med = ImageFont.truetype(FONT_FILE, font_size_med)
        except:
            font_reg = ImageFont.load_default()
            font_bold = font_reg
            font_large = font_reg
            font_med = font_reg

        def proc_ar(text):
            if not text:
                return ''
            try:
                text = str(text)
                reshaped_text = reshaper.reshape(text)
                bidi_text = get_display(reshaped_text)
                return bidi_text
            except:
                return str(text)

        def draw_text_line(text, y_pos, font_obj, align='left', color=(0, 0, 0)):
            if not text:
                return y_pos
            bidi_text = proc_ar(text)
            bbox = font_obj.getbbox(bidi_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x_pos = margin
            if align == 'center':
                x_pos = (PAPER_WIDTH - text_width) // 2
            elif align == 'right':
                x_pos = PAPER_WIDTH - text_width - margin
            draw.text((x_pos, y_pos), bidi_text, font=font_obj, fill=color)
            return y_pos + text_height + 8

        def draw_separator(curr_y):
            draw.line([(margin, curr_y), (PAPER_WIDTH - margin, curr_y)], fill=(0, 0, 0), width=2)
            return curr_y + 10

        def draw_lr(left, right, font, y_pos, is_bold=False):
            l = proc_ar(left)
            r = proc_ar(right)
            bbox_r = font.getbbox(r)
            bbox_l = font.getbbox(l)
            w_r = bbox_r[2] - bbox_r[0]
            x_r = PAPER_WIDTH - w_r - margin
            draw.text((margin, y_pos), l, font=font, fill=(0, 0, 0))
            draw.text((x_r, y_pos), r, font=font, fill=(0, 0, 0))
            if is_bold:
                draw.text((margin + 1, y_pos), l, font=font, fill=(0, 0, 0))
                draw.text((x_r + 1, y_pos), r, font=font, fill=(0, 0, 0))
            return max(bbox_r[3] - bbox_r[1], bbox_l[3] - bbox_l[1], 30) + 8

        def calculate_timbre_local(amount):
            try:
                val = float(amount)
            except:
                return 0.0
            if val <= 300:
                return 0.0
            import math
            units = math.ceil(val / 100.0)
            if val <= 30000:
                duty = units * 1.0
            elif val <= 100000:
                duty = units * 1.5
            else:
                duty = units * 2.0
            return max(5.0, math.ceil(duty))
        doc_type_raw = str(transaction_data.get('doc_type', '')).strip()
        items = transaction_data.get('items', [])
        try:
            amount_val = float(transaction_data.get('amount', 0))
        except:
            amount_val = 0.0
        is_simple = transaction_data.get('is_simple_payment', False)
        if doc_type_raw in ['Ve', 'Cr', 'Re', 'Vr', 'Dr'] or (not items and amount_val != 0):
            is_simple = True
        is_supplier = False
        if doc_type_raw in ['BA', 'FF', 'RF', 'DP', 'BI']:
            is_supplier = True
        if is_simple:
            pay_type = transaction_data.get('type', '')
            desc_text = str(transaction_data.get('desc', '')).lower()
            if pay_type == 'supplier_pay':
                is_supplier = True
            elif 'règlement' in desc_text or 'reglement' in desc_text or 'supplier' in desc_text:
                is_supplier = True
        if is_simple:
            c_label = transaction_data.get('custom_label', '')
            if c_label:
                c_upper = c_label.upper()
                if 'VERSEMENT' in c_upper or 'REGLEMENT' in c_upper or 'RÈGLEMENT' in c_upper:
                    doc_title = 'REGLEMENT' if is_supplier else 'VERSEMENT'
                elif 'CREDIT' in c_upper or 'CRÉDIT' in c_upper:
                    doc_title = 'CREDIT'
                else:
                    doc_title = c_upper
            elif amount_val < 0:
                if is_supplier:
                    doc_title = 'REGLEMENT'
                else:
                    doc_title = 'VERSEMENT'
            else:
                doc_title = 'CREDIT'
        else:
            labels = {'BV': 'BON DE VENTE', 'BA': "BON D'ACHAT", 'FC': 'FACTURE', 'FF': 'FACTURE ACHAT', 'RC': 'RETOUR CLIENT', 'RF': 'RETOUR FOURN.', 'TR': 'TRANSFERT', 'FP': 'PROFORMA', 'DP': 'COMMANDE', 'BI': 'BON INITIAL'}
            doc_title = labels.get(doc_type_raw, doc_type_raw)
            if doc_title == 'Ve':
                doc_title = 'VERSEMENT'
            if doc_title == 'Cr':
                doc_title = 'CREDIT'
        y = 10
        store_name = 'MagPro Store'
        store_address = ''
        store_phone = ''
        if self.store.exists('print_header'):
            header_conf = self.store.get('print_header')
            store_name = header_conf.get('name', store_name)
            store_address = header_conf.get('address', '')
            store_phone = header_conf.get('phone', '')
        y = draw_text_line(store_name, y, font_large, 'center')
        if store_address:
            y = draw_text_line(store_address, y, font_reg, 'center')
        if store_phone:
            y = draw_text_line(f'Tel: {store_phone}', y, font_reg, 'center')
        y += 5
        y = draw_separator(y)
        y = draw_text_line(doc_title, y, font_large, 'center')
        y += 5
        y = draw_separator(y)
        ref_text = ''
        if transaction_data.get('invoice_number'):
            ref_text = str(transaction_data.get('invoice_number'))
        elif transaction_data.get('description'):
            ref_text = str(transaction_data.get('description'))
        elif transaction_data.get('desc'):
            ref_text = str(transaction_data.get('desc'))
        elif transaction_data.get('server_id'):
            ref_text = str(transaction_data.get('server_id'))
        elif transaction_data.get('id'):
            ref_text = str(transaction_data.get('id'))
        if not is_simple and ref_text and (ref_text != 'None'):
            y = draw_text_line(f'Bon N°: {ref_text}', y, font_med, 'left')
        ts_str = transaction_data.get('timestamp', '')
        if not ts_str:
            ts_str = datetime.now().strftime('%Y-%m-%d %H:%M')
        else:
            ts_str = str(ts_str)[:16]
        user_str = transaction_data.get('user_name', self.current_user_name)
        entity_name_raw = None
        if transaction_data.get('entity_name'):
            entity_name_raw = transaction_data.get('entity_name')
        elif transaction_data.get('entity'):
            entity_name_raw = transaction_data.get('entity')
        if not entity_name_raw and transaction_data.get('entity_id'):
            ent_id = transaction_data.get('entity_id')
            found = next((c for c in self.all_clients if str(c['id']) == str(ent_id)), None)
            if not found:
                found = next((s for s in self.all_suppliers if str(s['id']) == str(ent_id)), None)
            if found:
                entity_name_raw = found.get('name')
        if not entity_name_raw:
            if doc_type_raw == 'TR':
                loc = transaction_data.get('purchase_location')
                if not loc:
                    loc = transaction_data.get('location', 'store')
                if loc == 'store':
                    entity_name_raw = 'Magasin -> Dépôt'
                else:
                    entity_name_raw = 'Dépôt -> Magasin'
            else:
                entity_name_raw = 'Passager'
        y = draw_text_line(f'Date: {ts_str}', y, font_reg, 'left')
        y = draw_text_line(f'User: {user_str}', y, font_reg, 'left')
        if doc_type_raw == 'TR':
            clean_name = str(entity_name_raw)
            clean_name = clean_name.replace('Mag', 'Magasin').replace('Dép', 'Dépôt').replace('Dep', 'Dépôt')
            if 'Magasin' in clean_name and 'Dépôt' in clean_name:
                if clean_name.find('Magasin') < clean_name.find('Dépôt'):
                    clean_name = 'Magasin -> Dépôt'
                else:
                    clean_name = 'Dépôt -> Magasin'
            else:
                clean_name = clean_name.replace('➔', ' -> ').replace('[]', ' -> ')
            y = draw_text_line(clean_name, y, font_med, 'left')
        else:
            label_entity = 'Fournisseur' if is_supplier else 'Client'
            y = draw_text_line(f'{label_entity}: {entity_name_raw}', y, font_med, 'left')
        y += 5
        y = draw_separator(y)
        if is_simple:
            y += 20
            y = draw_text_line('MONTANT', y, font_large, 'center')
            abs_amount = abs(amount_val)
            y = draw_text_line(f'{abs_amount:.2f} DA', y, font_large, 'center')
            y += 25
            draw.line([(margin + 100, y), (PAPER_WIDTH - margin - 100, y)], fill=(0, 0, 0), width=1)
            y += 15
            y = draw_text_line('Merci de votre Fidélité !', y, font_med, 'center')
            y += 120
            final_image = image.crop((0, 0, PAPER_WIDTH, y))
            return final_image
        calc_total_ht = 0.0
        calc_total_tva = 0.0
        for item in items:
            raw_prod = item.get('name', 'Article')
            qty = float(item.get('qty', 0))
            price = float(item.get('price', 0))
            tva_rate = float(item.get('tva', 0))
            prod_lines = self.get_wrapped_text(raw_prod, font_bold, PAPER_WIDTH - 2 * margin)
            for line in prod_lines:
                y = draw_text_line(line, y, font_bold, 'right')
            qty_str = str(int(qty)) if qty.is_integer() else str(qty)
            if doc_type_raw == 'TR':
                qty_display = f'Qté : {qty_str}'
                y = draw_text_line(qty_display, y, font_large, 'center', color=(0, 0, 0))
                draw.line([(margin + 50, y - 2), (PAPER_WIDTH - margin - 50, y - 2)], fill=(200, 200, 200), width=1)
                y += 10
                continue
            price_str = f'{price:.2f} DA'
            line_ht = self._round_num(qty * price)
            line_tva = self._round_num(line_ht * (tva_rate / 100.0))
            line_ttc = line_ht + line_tva
            calc_total_ht += line_ht
            calc_total_tva += line_tva
            if tva_rate > 0:
                line_calc = f'{qty_str} x {price_str} (TVA {int(tva_rate)}%)'
            else:
                line_calc = f'{qty_str} x {price_str}'
            line_total = f'= {line_ttc:.2f} DA'
            y += draw_lr(line_calc, line_total, font_reg, y)
            draw.line([(margin + 50, y - 2), (PAPER_WIDTH - margin - 50, y - 2)], fill=(200, 200, 200), width=1)
            y += 5
        y += 10
        y = draw_separator(y)
        if doc_type_raw != 'TR':
            payment_info = transaction_data.get('payment_info', {})
            saved_paid = 0.0
            if 'amount' in payment_info:
                try:
                    saved_paid = float(payment_info['amount'])
                except:
                    pass
            elif 'paid_amount' in transaction_data:
                try:
                    saved_paid = float(transaction_data['paid_amount'])
                except:
                    pass
            pay_method = transaction_data.get('payment_method', '')
            if not pay_method and 'method' in payment_info:
                pay_method = payment_info.get('method')
            is_cash = False
            pm_str = str(pay_method).lower()
            if pay_method and any((k in pm_str for k in ['espèce', 'espece', 'نقد', 'cash', 'دفع نقدًا'])):
                is_cash = True
            saved_timbre = float(payment_info.get('timbre', 0))
            final_timbre = 0.0
            if doc_type_raw == 'FC' and is_cash:
                if saved_timbre > 0:
                    final_timbre = saved_timbre
                else:
                    base = calc_total_ht + calc_total_tva
                    final_timbre = calculate_timbre_local(base)
            total_net = calc_total_ht + calc_total_tva + final_timbre
            if calc_total_tva > 0:
                y += draw_lr('Total HT:', f'{calc_total_ht:.2f} DA', font_med, y)
                y += draw_lr('Total TVA:', f'{calc_total_tva:.2f} DA', font_med, y)
            if final_timbre > 0:
                y += draw_lr('Droit Timbre:', f'{final_timbre:.2f} DA', font_med, y)
            if calc_total_tva > 0 or final_timbre > 0:
                y += 5
                draw.line([(margin, y), (PAPER_WIDTH - margin, y)], fill=(0, 0, 0), width=1)
                y += 5
            y += 10
            y += draw_lr('TOTAL:', f'{total_net:.2f} DA', font_large, y, True)
            y += 10
            is_comptoir_client = False
            check_name = str(entity_name_raw).lower().strip()
            comptoir_aliases = ['comptoir', 'passager', 'زبون افتراضي', 'مورد افتراضي', 'client', 'fournisseur']
            if any((x in check_name for x in comptoir_aliases)):
                is_comptoir_client = True
            if not is_comptoir_client:
                reste = self._round_num(total_net - saved_paid)
                if reste > 0.05:
                    y += draw_lr('VERSEMENT:', f'{saved_paid:.2f} DA', font_med, y)
                    y += draw_lr('RESTE:', f'{abs(reste):.2f} DA', font_med, y, True)
        y += 25
        draw.line([(margin + 100, y), (PAPER_WIDTH - margin - 100, y)], fill=(0, 0, 0), width=1)
        y += 15
        y = draw_text_line('Merci de votre Fidélité !', y, font_med, 'center')
        y += 120
        final_image = image.crop((0, 0, PAPER_WIDTH, y))
        return final_image

    def get_image_raster_data(self, image):
        max_width = 576
        if image.width > max_width:
            ratio = max_width / float(image.width)
            new_height = int(image.height * ratio)
            image = image.resize((max_width, new_height), Image.Resampling.LANCZOS)
        if image.width % 8 != 0:
            target_width = image.width // 8 * 8
            image = image.crop((0, 0, target_width, image.height))
        image = image.convert('1')
        width, height = image.size
        xL = width // 8 % 256
        xH = width // 8 // 256
        yL = height % 256
        yH = height // 256
        cmd = b'\x1dv0\x00' + bytes([xL, xH, yL, yH])
        raw_bytes = image.tobytes()
        inverted_bytes = bytearray([b ^ 255 for b in raw_bytes])
        return cmd + inverted_bytes

    def _round_num(self, value):
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return 0.0

    def calculate_cart_totals(self, cart_items, is_invoice_mode):
        total_ht = 0.0
        total_tva = 0.0
        for item in cart_items:
            try:
                p = float(item.get('price', 0))
                q = float(item.get('qty', 0))
                p, q = (max(0, p), max(0, q))
                line_ht = round(p * q, 2)
                total_ht += line_ht
                if is_invoice_mode:
                    t_rate = float(item.get('tva', 0))
                    total_tva += round(line_ht * (t_rate / 100.0), 2)
            except (ValueError, TypeError):
                continue
        return (round(total_ht, 2), round(total_tva, 2))

    def build(self):
        Builder.load_string(KV_BUILDER)
        self.title = 'MagPro Gestion de Stock'
        self._search_event = None
        self._entity_search_event = None
        self.theme_cls.primary_palette = 'Blue'
        self.theme_cls.accent_palette = 'Amber'
        self.theme_cls.theme_style = 'Light'
        self.theme_cls.font_styles['H4'] = ['ArabicFont', 34, False, 0.25]
        self.theme_cls.font_styles['H5'] = ['ArabicFont', 24, False, 0]
        self.theme_cls.font_styles['H6'] = ['ArabicFont', 20, False, 0.15]
        self.theme_cls.font_styles['Subtitle1'] = ['ArabicFont', 16, False, 0.15]
        self.theme_cls.font_styles['Subtitle2'] = ['ArabicFont', 14, False, 0.1]
        self.theme_cls.font_styles['Body1'] = ['ArabicFont', 16, False, 0.5]
        self.theme_cls.font_styles['Body2'] = ['ArabicFont', 14, False, 0.25]
        self.theme_cls.font_styles['Button'] = ['ArabicFont', 14, True, 1.25]
        self.theme_cls.font_styles['Caption'] = ['ArabicFont', 12, False, 0.4]
        self.data_dir = self.user_data_dir

        def load_safe_store(filename):
            path = os.path.join(self.data_dir, filename)
            try:
                return JsonStore(path)
            except Exception as e:
                print(f'[CORRUPTION DETECTED] Resetting {filename} due to error: {e}')
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except:
                    pass
                return JsonStore(path)
        self.offline_store = load_safe_store('stock_pending_orders.json')
        self.cache_store = load_safe_store('stock_cache.json')
        self.stats_store = load_safe_store('local_stats.json')
        self.store = load_safe_store('app_settings.json')
        self.gps_store = load_safe_store('gps_logs.json')
        self.cleanup_old_gps_logs()
        if self.store.exists('config'):
            conf = self.store.get('config')
            self.local_server_ip = conf.get('ip', '192.168.1.100')
            self.external_server_ip = conf.get('ext_ip', '')
            self.is_seller_mode = conf.get('seller_mode', False)
            self.active_server_ip = self.local_server_ip
        self.root_box = MDBoxLayout(orientation='vertical')
        self.sm = MDScreenManager()
        self.sm.add_widget(self._build_login_screen())
        self.sm.add_widget(self._build_dashboard_screen())
        self.sm.add_widget(self._build_products_screen())
        self.sm.add_widget(self._build_cart_screen())
        self.root_box.add_widget(self.sm)
        self.status_bar_bg = MDCard(size_hint_y=None, height=dp(40), radius=[0], md_bg_color=(0.2, 0.2, 0.2, 1), elevation=0)
        self.status_bar_label = MDLabel(text='Initialisation...', halign='center', theme_text_color='Custom', text_color=(1, 1, 1, 1), font_style='Caption', bold=True)
        self.status_bar_bg.add_widget(self.status_bar_label)
        self.root_box.add_widget(self.status_bar_bg)
        self._heartbeat_event = Clock.schedule_interval(self.check_server_heartbeat, 5)
        self.maps_enabled = False
        return self.root_box

    def get_device_id(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                content_resolver = PythonActivity.mActivity.getContentResolver()
                Secure = autoclass('android.provider.Settings$Secure')
                android_id = Secure.getString(content_resolver, Secure.ANDROID_ID)
                return str(android_id) if android_id else 'ANDROID_UNKNOWN'
            except Exception:
                return 'ANDROID_ERR_ID'
        elif platform == 'win':
            return 'PC_DEBUG_ID_12345'
        return 'UNKNOWN_DEVICE_ID'

    def check_license_validity(self):
        import hashlib
        try:
            if not self.store.exists('license'):
                print('DEBUG: License file not found.')
                return False
            data = self.store.get('license')
            stored_key = data.get('activ_key')
            if not stored_key:
                print('DEBUG: No key in license file.')
                return False
            device_id = self.get_device_id()
            salt = f'magpro_mobile_v6_{device_id}_secure_key'
            expected_key = hashlib.sha256(salt.encode()).hexdigest()
            is_valid = stored_key == expected_key
            print(f'DEBUG: License check result: {is_valid}')
            return is_valid
        except Exception as e:
            print(f'DEBUG: Error checking license: {e}')
            return False

    def copy_to_clipboard(self, text):
        from kivy.core.clipboard import Clipboard
        Clipboard.copy(text)
        self.notify('ID copié dans le presse-papiers', 'success')

    def validate_activation(self, key_input, dialog_ref):
        try:
            device_id = self.get_device_id()
            salt = f'magpro_mobile_v6_{device_id}_secure_key'
            expected_key = hashlib.sha256(salt.encode()).hexdigest()
            if key_input.strip() == expected_key:
                self.store.put('license', activ_key=expected_key)
                self.notify('Activation réussie ! Bienvenue.', 'success')
                if dialog_ref:
                    dialog_ref.dismiss()
                Clock.schedule_once(self._deferred_start, 0.5)
            else:
                self.notify('Clé invalide. Veuillez vérifier.', 'error')
        except Exception as e:
            self.notify(f'Erreur: {e}', 'error')

    def show_activation_dialog(self):
        from kivy.core.clipboard import Clipboard
        device_id = self.get_device_id()
        content = MDBoxLayout(orientation='vertical', spacing='12dp', size_hint_y=None, adaptive_height=True, padding=['20dp', '20dp', '20dp', '10dp'])
        content.add_widget(MDIcon(icon='shield-check', halign='center', font_size='64sp', theme_text_color='Custom', text_color=self.theme_cls.primary_color, pos_hint={'center_x': 0.5}))
        content.add_widget(MDLabel(text='Activation Requise', halign='center', font_style='H5', bold=True, theme_text_color='Primary', adaptive_height=True))
        id_card = MDCard(orientation='vertical', radius=[10], padding=['15dp', '12dp', '15dp', '12dp'], md_bg_color=(0.96, 0.96, 0.96, 1), elevation=0, size_hint_y=None, adaptive_height=True, spacing='5dp')
        id_card.add_widget(MDLabel(text="ID d'appareil :", halign='left', font_style='Caption', theme_text_color='Secondary', adaptive_height=True))
        id_row = MDBoxLayout(orientation='horizontal', spacing='10dp', adaptive_height=True)
        field_id = MDTextField(text=device_id, readonly=True, font_size='16sp', mode='line', active_line=False, size_hint_x=0.85, pos_hint={'center_y': 0.5})
        btn_copy = MDIconButton(icon='content-copy', theme_text_color='Custom', text_color=self.theme_cls.primary_color, on_release=lambda x: Clipboard.copy(device_id), pos_hint={'center_y': 0.5}, icon_size='22sp')
        id_row.add_widget(field_id)
        id_row.add_widget(btn_copy)
        id_card.add_widget(id_row)
        content.add_widget(id_card)
        key_row = MDBoxLayout(orientation='horizontal', spacing='10dp', adaptive_height=True)
        self.field_key = NoMenuTextField(hint_text='Saisir la clé de licence', mode='rectangle', size_hint_x=0.85, pos_hint={'center_y': 0.5})
        btn_paste = MDIconButton(icon='content-paste', theme_text_color='Custom', text_color=self.theme_cls.primary_color, on_release=lambda x: setattr(self.field_key, 'text', Clipboard.paste()), pos_hint={'center_y': 0.5}, icon_size='22sp')
        key_row.add_widget(self.field_key)
        key_row.add_widget(btn_paste)
        content.add_widget(key_row)
        btn_activate = MDRaisedButton(text="ACTIVER L'APPLICATION", md_bg_color=(0, 0.7, 0, 1), font_size='16sp', elevation=1, size_hint_x=1, size_hint_y=None, height='52dp', on_release=lambda x: self.validate_activation(self.field_key.text, self.activation_dialog_ref))
        content.add_widget(btn_activate)
        self.activation_dialog_ref = MDDialog(title='', type='custom', content_cls=content, size_hint=(0.9, None), auto_dismiss=False, radius=[16, 16, 16, 16])
        self.activation_dialog_ref.open()

    def on_start(self):
        print('--- DEBUG: APP STARTING (on_start) ---')
        Window.bind(on_keyboard=self.on_keyboard)
        self.image_cache_dir = os.path.join(self.user_data_dir, 'img_cache')
        if not os.path.exists(self.image_cache_dir):
            try:
                os.makedirs(self.image_cache_dir)
            except Exception as e:
                print(f'Error creating cache dir: {e}')
        if platform == 'android':
            self.request_android_permissions()
            try:
                self.tone_gen = ToneGenerator(3, 100)
            except Exception as e:
                self.tone_gen = None
        keep_screen_on = True
        if self.store.exists('screen_config'):
            keep_screen_on = self.store.get('screen_config').get('keep_on', True)
        Clock.schedule_once(lambda dt: self.set_screen_keep_alive(keep_screen_on), 1)
        if self.check_license_validity():
            print('--- DEBUG: License Valid. Starting... ---')
            Clock.schedule_once(self._deferred_start, 0.5)
        else:
            print('--- DEBUG: License Invalid. Showing Dialog... ---')
            Clock.schedule_once(lambda dt: self.show_activation_dialog(), 0.5)

    def request_android_permissions(self):
        if platform != 'android':
            return
        try:
            from android.permissions import request_permissions, Permission
            from jnius import autoclass

            def callback(permissions, results):
                pass
            Build = autoclass('android.os.Build')
            VERSION = autoclass('android.os.Build$VERSION')
            permissions_list = [Permission.BLUETOOTH, Permission.BLUETOOTH_ADMIN, Permission.ACCESS_COARSE_LOCATION, Permission.ACCESS_FINE_LOCATION, Permission.INTERNET, Permission.CAMERA, Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
            if VERSION.SDK_INT >= 31:
                permissions_list.extend(['android.permission.BLUETOOTH_CONNECT', 'android.permission.BLUETOOTH_SCAN'])
            request_permissions(permissions_list, callback)
        except Exception as e:
            print(f'Permissions Error: {e}')

    def _deferred_start(self, dt):
        self.cleanup_old_synced_data()
        self._auto_login_check(0)
        self.check_and_load_stats()
        self.update_dashboard_layout()

    def cleanup_old_synced_data(self):
        try:
            keys = list(self.offline_store.keys())
            now = time.time()
            count = 0
            retention_period = 172800
            for key in keys:
                item = self.offline_store.get(key)
                if item.get('synced', False):
                    sync_time = item.get('sync_timestamp', 0)
                    if now - sync_time > retention_period:
                        self.offline_store.delete(key)
                        count += 1
            if count > 0:
                print(f'Cleaned {count} old synced items.')
        except Exception as e:
            print(f'Cleanup Error: {e}')

    def select_entity_from_rv(self, entity_data):
        server_default_names = ['Comptoir', 'Fournisseur', 'زبون افتراضي', 'مورد افتراضي']
        final_name = entity_data.get('name', '')
        if final_name in server_default_names:
            final_name = 'COMPTOIR'
        self.selected_entity = {'id': entity_data['id'], 'name': final_name, 'category': entity_data.get('price_category', 'تجزئة')}
        if hasattr(self, 'btn_ent_screen'):
            self.btn_ent_screen.text = self.fix_text(final_name)[:15]
            if self.current_mode in ['sale', 'return_sale', 'client_payment', 'invoice_sale', 'proforma']:
                self.btn_ent_screen.md_bg_color = (0, 0.6, 0.6, 1)
            else:
                self.btn_ent_screen.md_bg_color = (0.8, 0.4, 0, 1)
        self.recalculate_cart_prices()
        if hasattr(self, 'entity_dialog') and self.entity_dialog:
            self.entity_dialog.dismiss()
        if hasattr(self, 'pending_entity_next_action') and self.pending_entity_next_action:
            self.pending_entity_next_action()
            self.pending_entity_next_action = None

    def check_and_load_stats(self):
        today_str = str(datetime.now().date())
        if self.stats_store.exists('daily_data'):
            data = self.stats_store.get('daily_data')
            if data.get('date') == today_str:
                self.stat_sales_today = data.get('sales', 0)
                self.stat_purchases_today = data.get('purchases', 0)
                self.stat_client_payments = data.get('c_pay', 0)
                self.stat_supplier_payments = data.get('s_pay', 0)
            else:
                self.reset_local_stats()
        else:
            self.reset_local_stats()
        self.calculate_net_total()

    def open_history_date_picker(self, instance):
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.on_history_date_save)
        date_dialog.open()

    def on_history_date_save(self, instance, value, date_range):
        self.btn_hist_date.text = str(value)
        self.filter_history_list(specific_date=value)

    def reset_local_stats(self):
        self.stat_sales_today = 0
        self.stat_purchases_today = 0
        self.stat_client_payments = 0
        self.stat_supplier_payments = 0
        self.save_local_stats()

    def save_local_stats(self):
        today_str = str(datetime.now().date())
        self.stats_store.put('daily_data', date=today_str, sales=self.stat_sales_today, purchases=self.stat_purchases_today, c_pay=self.stat_client_payments, s_pay=self.stat_supplier_payments)

    def calculate_net_total(self):
        self.stat_net_total = self.stat_sales_today + self.stat_client_payments - (self.stat_purchases_today + self.stat_supplier_payments)
        self.update_dashboard_labels()

    def update_local_entity_balance(self, entity_id, change_amount):
        if not entity_id:
            return
        target_entity = None
        is_client = False
        for c in self.all_clients:
            if c['id'] == entity_id:
                target_entity = c
                is_client = True
                break
        if not target_entity:
            for s in self.all_suppliers:
                if s['id'] == entity_id:
                    target_entity = s
                    is_client = False
                    break
        if target_entity:
            try:
                current_bal = float(target_entity.get('balance', 0))
                new_bal = current_bal + float(change_amount)
                target_entity['balance'] = new_bal
                key = 'clients' if is_client else 'suppliers'
                data_list = self.all_clients if is_client else self.all_suppliers
                self.cache_store.put(key, data=data_list)
            except Exception as e:
                pass

    def filter_entity_history_list(self, day_offset=None, specific_date=None):
        if not hasattr(self, 'rv_entity_history'):
            return
        inactive_color = (0.5, 0.5, 0.5, 1)
        active_color = self.theme_cls.primary_color
        target_date = None
        if specific_date:
            target_date = specific_date
            self.btn_ent_hist_today.md_bg_color = inactive_color
            self.btn_ent_hist_yesterday.md_bg_color = inactive_color
            self.btn_ent_hist_date.md_bg_color = active_color
        else:
            if day_offset is None:
                day_offset = 0
            target_date = datetime.now().date() - timedelta(days=day_offset)
            self.btn_ent_hist_today.md_bg_color = active_color if day_offset == 0 else inactive_color
            self.btn_ent_hist_yesterday.md_bg_color = active_color if day_offset == 1 else inactive_color
            self.btn_ent_hist_date.md_bg_color = inactive_color
            self.btn_ent_hist_date.text = 'CALENDRIER'
        self.rv_entity_history.data = [{'type_str': 'Chargement...', 'ref_str': '', 'entity_str': 'Veuillez patienter', 'date_str': '', 'amount_text': '', 'icon': 'timer-sand', 'icon_color': [0.5, 0.5, 0.5, 1], 'bg_color': [1, 1, 1, 1], 'is_local': False, 'raw_data': None}]

        def on_history_fetched(req, result):
            rv_data = []
            if not result:
                rv_data.append({'type_str': 'Info', 'ref_str': '', 'entity_str': 'Aucune opération trouvée.', 'date_str': '', 'amount_text': '', 'icon': 'information-outline', 'icon_color': [0.5, 0.5, 0.5, 1], 'bg_color': [1, 1, 1, 1], 'is_local': False, 'raw_data': None})
                self.rv_entity_history.data = rv_data
                return
            target_name = self.history_target_entity['name'].lower()
            main_doc_prefixes = ['BV', 'BA', 'FC', 'FF', 'RC', 'RF', 'FP', 'DP', 'BI', 'TR']
            manual_keywords = ['versement', 'règlement', 'reglement', 'crédit', 'credit', 'dette', 'سداد', 'دفعة', 'إيداع', 'rendu', 'versé', 'excédent', 'excedent', 'فائض']
            for item in result:
                if self.is_seller_mode:
                    item_user = str(item.get('user', '')).strip()
                    if item_user != self.current_user_name:
                        continue
                server_entity_name = str(item.get('entity', '')).lower()
                if target_name not in server_entity_name:
                    continue
                desc = item.get('desc', '')
                desc_lower = desc.lower()
                prefix = desc[:2].upper() if len(desc) >= 2 else ''
                amount = float(item.get('amount', 0))
                time_str = item.get('time', '')
                is_main_doc = prefix in main_doc_prefixes
                if 'دفعة من' in desc or 'Payment from' in desc:
                    is_excess = 'excédent' in desc_lower or 'excedent' in desc_lower or 'فائض' in desc_lower
                    if not is_excess:
                        continue
                if not is_main_doc:
                    is_manual_or_excess = any((k in desc_lower for k in manual_keywords))
                    if not is_manual_or_excess:
                        continue
                icon = 'file-document'
                color = (0.2, 0.2, 0.2, 1)
                amount_text = f'{abs(amount):.2f} DA'
                bg_color = (0.98, 0.98, 0.98, 1)
                final_desc = desc
                if not is_main_doc:
                    if amount < 0:
                        is_supplier_pay = 'règlement' in desc_lower or 'reglement' in desc_lower or 'supplier' in desc_lower or ('سداد' in desc_lower)
                        if is_supplier_pay:
                            icon = 'cash-refund'
                            color = (1, 0.6, 0, 1)
                            amount_text = f'+ {abs(amount):.2f} DA'
                            user_name = item.get('user', '')
                            final_desc = f'Règlement ({user_name})'
                        else:
                            icon = 'cash-plus'
                            color = (0, 0.7, 0, 1)
                            amount_text = f'+ {abs(amount):.2f} DA'
                            if 'excédent' in desc_lower or 'excedent' in desc_lower:
                                final_desc = f'Versement (Excédent)'
                            elif 'versement' in desc_lower:
                                final_desc = desc
                            else:
                                final_desc = f'Versement ({desc})'
                    else:
                        icon = 'notebook-edit'
                        color = (0.8, 0, 0, 1)
                        amount_text = f'- {abs(amount):.2f} DA'
                        if 'crédit' in desc.lower() or 'dette' in desc.lower():
                            final_desc = desc
                        else:
                            final_desc = f'Crédit ({desc})'
                elif prefix == 'BV':
                    icon = 'cart'
                    color = (0, 0.5, 0.8, 1)
                elif prefix == 'BA':
                    icon = 'truck'
                    color = (1, 0.6, 0, 1)
                elif prefix == 'FC':
                    icon = 'file-document'
                    color = (0, 0, 0.8, 1)
                elif prefix == 'RC':
                    icon = 'keyboard-return'
                    color = (0.8, 0, 0, 1)
                final_user_time = f"{time_str} • {item.get('user', '')}"
                rv_data.append({'type_str': 'Opération', 'ref_str': final_user_time, 'entity_str': final_desc, 'date_str': '', 'amount_text': amount_text, 'icon': icon, 'icon_color': color, 'bg_color': bg_color, 'is_local': False, 'raw_data': item, 'key': ''})
            if not rv_data:
                rv_data.append({'type_str': 'Info', 'ref_str': '', 'entity_str': 'Aucune transaction trouvée (Filtre).', 'date_str': '', 'amount_text': '', 'icon': 'filter-outline', 'icon_color': [0.5, 0.5, 0.5, 1], 'bg_color': [1, 1, 1, 1], 'is_local': False, 'raw_data': None})
            self.rv_entity_history.data = rv_data
            self.rv_entity_history.refresh_from_data()

        def on_fail(req, err):
            self.rv_entity_history.data = [{'type_str': 'Erreur', 'ref_str': '', 'entity_str': 'Erreur de connexion serveur.', 'date_str': '', 'amount_text': '', 'icon': 'wifi-off', 'icon_color': [0.8, 0, 0, 1], 'bg_color': [1, 1, 1, 1], 'is_local': False, 'raw_data': None}]
        if self.is_server_reachable:
            url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/history?date={target_date}'
            UrlRequest(url, on_success=on_history_fetched, on_failure=on_fail, on_error=on_fail)
        else:
            self.rv_entity_history.data = [{'type_str': 'Hors Ligne', 'ref_str': '', 'entity_str': "Impossible de voir l'historique", 'date_str': '', 'amount_text': '', 'icon': 'wifi-off', 'icon_color': [0.5, 0.5, 0.5, 1], 'bg_color': [1, 1, 1, 1], 'is_local': False, 'raw_data': None}]

    def fetch_and_edit_transaction(self, item_data):
        if self.is_seller_mode:
            try:
                item_date_str = str(item_data.get('time', '')).split(' ')[0]
                today_str = str(datetime.now().date())
                if item_date_str != today_str:
                    self.notify('Modification interdite (Date passée)', 'error')
                    return
            except Exception as e:
                print(f'Date check error: {e}')
                self.notify('Modification interdite', 'error')
                return
        self.notify('Chargement pour modification...', 'info')
        if hasattr(self, 'entity_hist_dialog'):
            self.entity_hist_dialog.dismiss()
        is_tr_str = 'true' if item_data.get('is_transfer') else 'false'
        url = f"http://{self.active_server_ip}:{DEFAULT_PORT}/api/get_transaction_details?id={item_data['id']}&is_transfer={is_tr_str}"

        def on_details_success(req, res):
            items = res.get('items', [])
            header_data = item_data.copy()
            if res.get('purchase_location'):
                header_data['purchase_location'] = res.get('purchase_location')
            if res.get('location'):
                header_data['location'] = res.get('location')
            if res.get('source_location'):
                header_data['source_location'] = res.get('source_location')
            if res.get('payment_method'):
                header_data['payment_method'] = res.get('payment_method')
            if hasattr(self, 'history_target_entity') and self.history_target_entity:
                header_data['entity_id'] = self.history_target_entity['id']
                header_data['entity'] = self.history_target_entity['name']
            if not items:
                self.current_mode = 'client_payment'
                if 'règlement' in header_data.get('desc', '').lower():
                    self.current_mode = 'supplier_payment'
                self.selected_entity = self.history_target_entity
                self.editing_transaction_key = 'SERVER_EDIT_MODE'
                self.current_editing_server_id = header_data['id']
                amount = abs(float(header_data.get('amount', 0)))
                self.show_simple_payment_dialog(amount=amount)
            else:
                self.load_server_transaction_for_edit(header_data, items)

        def on_details_fail(req, err):
            self.notify('Erreur chargement détails', 'error')
            if hasattr(self, 'entity_hist_dialog'):
                self.entity_hist_dialog.open()
        UrlRequest(url, on_success=on_details_success, on_failure=on_details_fail, on_error=on_details_fail)

    def open_entity_history_dialog(self, entity):
        self.history_target_entity = entity
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(550))
        tabs_box = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=5)
        self.btn_ent_hist_today = MDRaisedButton(text='AUJ.', size_hint_x=0.33, elevation=0, on_release=lambda x: self.filter_entity_history_list(day_offset=0))
        self.btn_ent_hist_yesterday = MDRaisedButton(text='HIER', size_hint_x=0.33, elevation=0, md_bg_color=(0.5, 0.5, 0.5, 1), on_release=lambda x: self.filter_entity_history_list(day_offset=1))
        self.btn_ent_hist_date = MDRaisedButton(text='CALENDRIER', size_hint_x=0.33, elevation=0, md_bg_color=(0.5, 0.5, 0.5, 1), on_release=self.open_entity_history_date_picker)
        tabs_box.add_widget(self.btn_ent_hist_today)
        tabs_box.add_widget(self.btn_ent_hist_yesterday)
        tabs_box.add_widget(self.btn_ent_hist_date)
        content.add_widget(tabs_box)
        self.rv_entity_history = HistoryRecycleView()
        content.add_widget(self.rv_entity_history)
        title_text = self.fix_text(f"Historique: {entity['name']}")
        self.entity_hist_dialog = MDDialog(title=title_text, type='custom', content_cls=content, size_hint=(0.95, 0.9))
        self.entity_hist_dialog.open()
        self.filter_entity_history_list(day_offset=0)

    def submit_simple_payment(self, x):
        current_time = time.time()
        if current_time - getattr(self, '_last_click_time', 0) < 1.0:
            return
        self._last_click_time = current_time
        if getattr(self, 'is_transaction_in_progress', False):
            return
        self.is_transaction_in_progress = True
        try:
            amount = float(self.txt_simple_amount.get_value())
        except:
            self.notify('Montant invalide', 'error')
            self.is_transaction_in_progress = False
            return
        if amount == 0:
            self.notify('Le montant ne peut pas être 0', 'error')
            self.is_transaction_in_progress = False
            return
        if self.simple_pay_dialog:
            self.simple_pay_dialog.dismiss()
        base_type = 'client_pay'
        if self.current_mode in ['client_payment', 'client_pay']:
            base_type = 'client_pay'
            self.stat_client_payments += amount
        elif self.current_mode in ['supplier_payment', 'supplier_pay']:
            base_type = 'supplier_pay'
            self.stat_supplier_payments += amount
        self.calculate_net_total()
        self.save_local_stats()
        custom_note = ''
        if base_type == 'supplier_pay':
            if amount >= 0:
                custom_note = 'Règlement'
            else:
                custom_note = 'Crédit'
        elif amount >= 0:
            custom_note = 'Versement'
        else:
            custom_note = 'Crédit'
        server_id_to_update = None
        if self.editing_transaction_key:
            if self.editing_transaction_key == 'SERVER_EDIT_MODE':
                server_id_to_update = self.current_editing_server_id
            elif self.offline_store.exists(self.editing_transaction_key):
                old_item = self.offline_store.get(self.editing_transaction_key)
                if old_item.get('synced') and old_item.get('order_data', {}).get('server_id'):
                    server_id_to_update = old_item['order_data']['server_id']
        final_timestamp = str(datetime.now())
        if server_id_to_update and hasattr(self, 'current_editing_date') and self.current_editing_date:
            final_timestamp = self.current_editing_date
        try:
            if '.' in final_timestamp:
                final_timestamp = final_timestamp.split('.')[0]
        except:
            pass
        final_note_to_send = self.current_user_name
        if hasattr(self, 'temp_note') and self.temp_note:
            final_note_to_send = self.temp_note
        data = {'entity_id': self.selected_entity['id'], 'amount': amount, 'type': base_type, 'custom_label': custom_note, 'user_name': self.current_user_name, 'note': final_note_to_send, 'is_simple_payment': True, 'timestamp': final_timestamp, 'server_id': server_id_to_update}
        self.current_editing_server_id = None
        self.current_editing_date = None

        def release_lock_and_finish(req=None, res=None):
            self.is_transaction_in_progress = False
            try:
                if self.store.exists('printer_config'):
                    conf = self.store.get('printer_config')
                    if conf.get('auto', False) and conf.get('mac', ''):
                        threading.Thread(target=self.print_ticket_bluetooth, args=(data,), daemon=True).start()
            except Exception as e:
                print(f'Auto print payment error: {e}')
        if self.is_server_reachable:

            def on_success(req, res):
                if res.get('server_id'):
                    data['server_id'] = res.get('server_id')
                if res.get('invoice_number'):
                    data['invoice_number'] = res.get('invoice_number')
                self.save_to_history(data, synced=True)
                self.notify('Enregistré' if not server_id_to_update else 'Modifié avec succès', 'success')
                entity_type_to_refresh = 'account' if base_type == 'client_pay' else 'supplier'
                self.fetch_entities(entity_type_to_refresh)
                release_lock_and_finish()
            UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/submit_payment', req_body=json.dumps(data), req_headers={'Content-type': 'application/json'}, method='POST', on_success=on_success, on_error=lambda r, e: [self.submit_simple_payment_offline(data), release_lock_and_finish()], on_failure=lambda r, e: [self.submit_simple_payment_offline(data), release_lock_and_finish()])
        else:
            self.submit_simple_payment_offline(data)
            release_lock_and_finish()

    def submit_simple_payment_offline(self, data):
        self.save_to_history(data, synced=False)
        change = -float(data['amount'])
        self.update_local_entity_balance(data['entity_id'], change)
        if hasattr(self, 'mgmt_dialog') and self.mgmt_dialog:
            target_list = self.all_clients if data['type'] == 'client_pay' else self.all_suppliers
            self.populate_entity_manager_list(target_list)
        self.notify('Enregistré (Offline & Cache Update)', 'warning')

    def update_dashboard_labels(self):
        try:
            if hasattr(self, 'lbl_stat_sales') and self.lbl_stat_sales:
                self.lbl_stat_sales.text = f'{self.stat_sales_today:.2f} DA'
            if hasattr(self, 'lbl_stat_purchases') and self.lbl_stat_purchases:
                self.lbl_stat_purchases.text = f'{self.stat_purchases_today:.2f} DA'
            if hasattr(self, 'lbl_stat_client_pay') and self.lbl_stat_client_pay:
                self.lbl_stat_client_pay.text = f'{self.stat_client_payments:.2f} DA'
            if hasattr(self, 'lbl_stat_supp_pay') and self.lbl_stat_supp_pay:
                self.lbl_stat_supp_pay.text = f'{self.stat_supplier_payments:.2f} DA'
            if hasattr(self, 'lbl_stat_net') and self.lbl_stat_net:
                self.lbl_stat_net.text = f'{self.stat_net_total:.2f} DA'
        except:
            pass

    def update_dashboard_layout(self):
        if not self.buttons_container or not self.stats_card_container:
            return
        self.buttons_container.clear_widgets()
        self.stats_card_container.clear_widgets()
        col_green = (0, 0.7, 0, 1)
        col_blue = (0, 0, 0.8, 1)
        col_purple = (0.5, 0, 0.5, 1)
        col_red = (0.8, 0, 0, 1)
        col_teal = (0, 0.5, 0.5, 1)
        col_orange = (1, 0.6, 0, 1)
        col_deep_orange = (1, 0.3, 0, 1)
        col_brown = (0.4, 0.2, 0.1, 1)
        col_cyan = (0, 0.6, 0.6, 1)
        bg_green = (0.9, 1, 0.9, 1)
        bg_blue = (0.9, 0.95, 1, 1)
        bg_purple = (0.95, 0.9, 1, 1)
        bg_red = (1, 0.9, 0.9, 1)
        bg_teal = (0.8, 1, 1, 1)
        bg_orange = (1, 0.95, 0.8, 1)
        bg_deep_orange = (1, 0.9, 0.8, 1)
        bg_brown = (1, 0.85, 0.85, 1)
        if self.is_seller_mode:
            self.buttons_container.add_widget(self._create_dash_btn('cart', 'VENTE (BV)', bg_green, col_green, lambda x: self.open_mode('sale')))
            grid = MDGridLayout(cols=2, spacing=dp(10), adaptive_height=True)
            grid.add_widget(self._create_dash_btn('keyboard-return', 'RETOUR CL.', bg_red, col_red, lambda x: self.open_mode('return_sale')))
            grid.add_widget(self._create_dash_btn('account-group', 'CLIENTS', bg_teal, col_teal, lambda x: self.open_entity_manager('account')))
            self.buttons_container.add_widget(grid)
        else:
            grid = MDGridLayout(cols=2, spacing=dp(10), adaptive_height=True)
            grid.add_widget(self._create_dash_btn('cart', 'VENTE (BV)', bg_green, col_green, lambda x: self.open_mode('sale')))
            grid.add_widget(self._create_dash_btn('truck', 'ACHAT (BA)', bg_orange, col_orange, lambda x: self.open_mode('purchase')))
            grid.add_widget(self._create_dash_btn('file-document', 'FACTURE (FC)', bg_blue, col_blue, lambda x: self.open_mode('invoice_sale')))
            grid.add_widget(self._create_dash_btn('file-document-edit', 'FACT. ACHAT (FF)', bg_deep_orange, col_deep_orange, lambda x: self.open_mode('invoice_purchase')))
            grid.add_widget(self._create_dash_btn('file-document-outline', 'PROFORMA (FP)', bg_purple, col_purple, lambda x: self.open_mode('proforma')))
            grid.add_widget(self._create_dash_btn('clipboard-list', 'COMMANDE (DP)', bg_teal, col_cyan, lambda x: self.open_mode('order_purchase')))
            grid.add_widget(self._create_dash_btn('keyboard-return', 'RETOUR CL.', bg_red, col_red, lambda x: self.open_mode('return_sale')))
            grid.add_widget(self._create_dash_btn('undo', 'RETOUR FR.', bg_blue, col_blue, lambda x: self.open_mode('return_purchase')))
            grid.add_widget(self._create_dash_btn('account-group', 'CLIENTS', bg_teal, col_teal, lambda x: self.open_entity_manager('account')))
            grid.add_widget(self._create_dash_btn('truck-delivery', 'FOURNISSEURS', bg_brown, col_brown, lambda x: self.open_entity_manager('supplier')))
            grid.add_widget(self._create_dash_btn('database-edit', 'PRODUITS', bg_blue, col_blue, lambda x: self.open_mode('manage_products')))
            grid.add_widget(self._create_dash_btn('transfer', 'TRANSFERT (TR)', bg_purple, col_purple, lambda x: self.open_mode('transfer')))
            self.buttons_container.add_widget(grid)
        self.stats_card_container.add_widget(MDLabel(text='Statistiques Journalières', font_style='Subtitle1', bold=True, halign='center', size_hint_y=None, height=dp(30)))
        stats_grid = MDGridLayout(cols=2, spacing=dp(10))
        stats_grid.add_widget(self._create_stat_item('Ventes (Espèce)', 'lbl_stat_sales', col_green))
        if not self.is_seller_mode:
            stats_grid.add_widget(self._create_stat_item('Achats', 'lbl_stat_purchases', col_orange))
        stats_grid.add_widget(self._create_stat_item('Encaissements', 'lbl_stat_client_pay', col_teal))
        if not self.is_seller_mode:
            stats_grid.add_widget(self._create_stat_item('Décaissements', 'lbl_stat_supp_pay', col_red))
        self.stats_card_container.add_widget(stats_grid)
        total_box = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(60), padding=[0, 10, 0, 0])
        total_box.add_widget(MDLabel(text='Total', font_style='Caption', halign='center'))
        self.lbl_stat_net = MDLabel(text='0.00 DA', font_style='H5', bold=True, halign='center', theme_text_color='Custom', text_color=(0.2, 0.2, 0.8, 1))
        total_box.add_widget(self.lbl_stat_net)
        self.stats_card_container.add_widget(total_box)
        self.update_dashboard_labels()

    def open_entity_history_date_picker(self, instance):
        date_dialog = MDDatePicker()
        date_dialog.bind(on_save=self.on_entity_history_date_save)
        date_dialog.open()

    def on_entity_history_date_save(self, instance, value, date_range):
        self.btn_ent_hist_date.text = str(value)
        self.filter_entity_history_list(specific_date=value)

    def open_entity_manager(self, entity_type):
        self.current_entity_type_mgmt = entity_type
        self.current_entity_sort = 'name'
        title_text = 'Gestion Clients' if entity_type == 'account' else 'Gestion Fournisseurs'
        if self.is_server_reachable:
            self.fetch_entities(entity_type)
        else:
            key = 'clients' if entity_type == 'account' else 'suppliers'
            if self.cache_store.exists(key):
                data = self.cache_store.get(key)['data']
                if entity_type == 'account':
                    self.all_clients = data
                else:
                    self.all_suppliers = data
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(600), spacing=dp(5))
        search_layout = MDBoxLayout(orientation='horizontal', spacing=dp(5), size_hint_y=None, height=dp(55))
        self.entity_search = SmartTextField(hint_text='Rechercher...', icon_right='magnify', size_hint_x=0.85)
        self.entity_search.bind(text=lambda instance, text: self.filter_entities_for_manager(text))
        self.btn_sort_entity = MDIconButton(icon='sort-alphabetical-variant', theme_text_color='Custom', text_color=(0.2, 0.2, 0.2, 1), md_bg_color=(0.95, 0.95, 0.95, 1), size_hint=(None, None), size=(dp(48), dp(48)), pos_hint={'center_y': 0.5}, on_release=self.toggle_entity_sort)
        search_layout.add_widget(self.entity_search)
        search_layout.add_widget(self.btn_sort_entity)
        content.add_widget(search_layout)
        self.rv_mgmt_entity = MgmtEntityRecycleView()
        content.add_widget(self.rv_mgmt_entity)
        btn_add = MDFillRoundFlatButton(text='AJOUTER NOUVEAU', size_hint_x=1, md_bg_color=(0, 0.7, 0, 1), on_release=lambda x: self.show_add_edit_entity_dialog(None))
        content.add_widget(btn_add)
        self.mgmt_dialog = MDDialog(title=title_text, type='custom', content_cls=content, size_hint=(0.95, 0.9))
        self.mgmt_dialog.open()
        source = self.all_clients if entity_type == 'account' else self.all_suppliers
        self.populate_entity_manager_list(source)

    def toggle_entity_sort(self, instance):
        if not hasattr(self, 'current_entity_sort'):
            self.current_entity_sort = 'name'
        if self.current_entity_sort == 'name':
            self.current_entity_sort = 'balance'
            instance.icon = 'sort-numeric-descending'
            instance.md_bg_color = (0.8, 0.9, 1, 1)
            self.notify('Tri: Par Solde (Décroissant)', 'info')
        else:
            self.current_entity_sort = 'name'
            instance.icon = 'sort-alphabetical-variant'
            instance.md_bg_color = (0.95, 0.95, 0.95, 1)
            self.notify('Tri: Alphabétique (A-Z)', 'info')
        current_text = self.entity_search.text if hasattr(self, 'entity_search') else ''
        self.filter_entities_for_manager(current_text)

    def filter_entities_for_manager(self, text_arg):
        query = ''
        if hasattr(self, 'entity_search'):
            query = self.entity_search.get_value()
        else:
            query = text_arg
        if self._entity_search_event:
            self._entity_search_event.cancel()
        self._entity_search_event = Clock.schedule_once(lambda dt: self._start_mgmt_background_search(query), 0.3)

    def _start_mgmt_background_search(self, text):
        threading.Thread(target=self._mgmt_search_worker, args=(text,), daemon=True).start()

    def _mgmt_search_worker(self, text):
        source = self.all_clients if self.current_entity_type_mgmt == 'account' else self.all_suppliers
        if not text:
            self.populate_entity_manager_list(source[:50])
            return
        txt = text.lower()
        filtered = [e for e in source if txt in str(e.get('name', '')).lower()]
        if not filtered:
            try:
                fixed_query = self.fix_text(txt)
                filtered = [e for e in source if fixed_query in self.fix_text(str(e.get('name', '')))]
            except Exception:
                pass
        if len(filtered) > 50:
            filtered = filtered[:50]
        self.populate_entity_manager_list(filtered)

    @mainthread
    def populate_entity_manager_list(self, entities):
        server_default_names = ['Comptoir', 'Fournisseur', 'زبون افتراضي', 'مورد افتراضي']
        sort_mode = getattr(self, 'current_entity_sort', 'name')
        if sort_mode == 'balance':
            sorted_entities = sorted(entities, key=lambda x: float(x.get('balance', 0)), reverse=True)
        else:
            sorted_entities = sorted(entities, key=lambda x: x.get('name', '').lower())
        rv_data = []
        for e in sorted_entities:
            name = e.get('name', '')
            if name in server_default_names:
                continue
            balance = float(e.get('balance', 0))
            bal_text = f'{balance:.2f} DA'
            col_hex = 'D50000' if balance > 0 else '00C853'
            balance_markup = f'Solde: [color={col_hex}][b]{bal_text}[/b][/color]'
            rv_data.append({'raw_name': name, 'balance_text': balance_markup, 'raw_data': e})
        if hasattr(self, 'rv_mgmt_entity'):
            self.rv_mgmt_entity.data = rv_data
            self.rv_mgmt_entity.refresh_from_data()

    def start_direct_payment_from_manager(self, entity):
        self.selected_entity = entity
        if self.current_entity_type_mgmt == 'account':
            self.current_mode = 'client_payment'
        else:
            self.current_mode = 'supplier_payment'
        self.show_simple_payment_dialog()

    def open_entity_edit_menu(self, entity):
        self.mgmt_selected_entity = entity
        title_text = self.fix_text(entity['name'])
        from kivymd.uix.button import MDFillRoundFlatIconButton, MDRoundFlatIconButton
        from kivymd.uix.card import MDSeparator
        content = MDBoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None, height=dp(160), padding=[dp(15), 0, dp(15), dp(10)])
        gps_data = entity.get('gps_location', '')
        map_bg_color = (0.1, 0.7, 0.3, 1) if gps_data else (0.8, 0.8, 0.8, 1)
        btn_map = MDFillRoundFlatIconButton(text='Localiser (Maps)', icon='google-maps', size_hint_x=1, height=dp(50), md_bg_color=map_bg_color, theme_text_color='Custom', text_color=(1, 1, 1, 1), icon_color=(1, 1, 1, 1), font_size='17sp', on_release=lambda x: [self.options_dialog.dismiss(), self.open_client_location(gps_data)])
        content.add_widget(btn_map)
        content.add_widget(MDSeparator(height=dp(1), color=(0.9, 0.9, 0.9, 1)))
        actions_row = MDBoxLayout(orientation='horizontal', spacing=dp(10), size_hint_y=None, height=dp(50))
        btn_edit = MDFillRoundFlatIconButton(text='Modifier', icon='pencil', size_hint_x=0.5, height=dp(48), md_bg_color=(0.15, 0.45, 0.8, 1), theme_text_color='Custom', text_color=(1, 1, 1, 1), icon_color=(1, 1, 1, 1), font_size='16sp', on_release=lambda x: [self.options_dialog.dismiss(), self.show_add_edit_entity_dialog(entity)])
        btn_del = MDRoundFlatIconButton(text='Supprimer', icon='delete', size_hint_x=0.5, height=dp(48), theme_text_color='Custom', text_color=(0.85, 0.1, 0.1, 1), icon_color=(0.85, 0.1, 0.1, 1), line_color=(0.85, 0.1, 0.1, 1), font_size='16sp', on_release=lambda x: self.confirm_delete_entity(entity))
        actions_row.add_widget(btn_edit)
        actions_row.add_widget(btn_del)
        content.add_widget(actions_row)
        self.options_dialog = MDDialog(title=title_text, type='custom', content_cls=content, size_hint=(0.95, None), radius=[16, 16, 16, 16])
        self.options_dialog.open()

    def open_client_location(self, location_data):
        if not location_data:
            self.notify('Aucune position GPS enregistrée', 'error')
            return
        loc = str(location_data).strip()
        if not loc:
            return
        import webbrowser
        from urllib.parse import quote
        if 'http' in loc or 'waze' in loc or 'geo:' in loc:
            url = loc
        else:
            url = f'https://www.google.com/maps/search/?api=1&query={quote(loc)}'
        try:
            webbrowser.open(url)
            self.notify('Ouverture de Google Maps...', 'info')
        except Exception as e:
            self.notify(f'Erreur: {e}', 'error')

    def show_add_edit_entity_dialog(self, entity=None):
        if not self.is_server_reachable:
            self.ae_dialog = MDDialog(title='Hors Ligne', text='Modification impossible en mode hors ligne.\nVeuillez vous connecter au serveur.', buttons=[MDFlatButton(text='OK', on_release=lambda x: self.ae_dialog.dismiss())])
            self.ae_dialog.open()
            return
        from kivy.core.clipboard import Clipboard
        is_edit = entity is not None
        title = 'Modifier Fiche' if is_edit else 'Ajouter Nouveau'
        val_name = entity.get('name', '') if is_edit else ''
        val_phone = entity.get('phone', '') if is_edit else ''
        val_address = entity.get('address', '') if is_edit else ''
        val_activity = entity.get('activity', '') if is_edit else ''
        val_email = entity.get('email', '') if is_edit else ''
        val_rc = entity.get('rc', '') if is_edit else ''
        val_nif = entity.get('nif', '') if is_edit else ''
        val_nis = entity.get('nis', '') if is_edit else ''
        val_nai = entity.get('nai', '') if is_edit else ''
        val_gps = entity.get('gps_location', '') if is_edit else ''
        old_lat = str(entity.get('lat', '')).strip() if is_edit else ''
        old_lon = str(entity.get('lon', '')).strip() if is_edit else ''
        raw_cat = str(entity.get('price_category', '')).strip() if is_edit else ''
        if raw_cat in ['Gros', 'جملة']:
            display_cat = 'Gros'
        elif raw_cat in ['Demi-Gros', 'نصف جملة']:
            display_cat = 'Demi-Gros'
        else:
            display_cat = 'Détail'
        scroll = MDScrollView(size_hint_y=None, height=dp(600))
        main_box = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(15), padding=[dp(10), dp(10), dp(10), dp(20)])
        card_info = MDCard(orientation='vertical', radius=[12], padding=dp(15), spacing=dp(10), elevation=1, adaptive_height=True, md_bg_color=(0.99, 0.99, 0.99, 1))
        header_info = MDBoxLayout(orientation='horizontal', spacing=dp(10), adaptive_height=True)
        header_info.add_widget(MDIcon(icon='account-box-outline', theme_text_color='Primary', font_size='22sp'))
        header_info.add_widget(MDLabel(text='Identité', bold=True, theme_text_color='Primary', font_style='Subtitle1'))
        card_info.add_widget(header_info)
        card_info.add_widget(MDBoxLayout(size_hint_y=None, height=dp(1), md_bg_color=(0.9, 0.9, 0.9, 1)))
        f_name = SmartTextField(text=val_name, hint_text='Nom Complet *', required=True, icon_right='account')
        f_activity = SmartTextField(text=val_activity, hint_text='Activité', icon_right='briefcase')
        card_info.add_widget(f_name)
        card_info.add_widget(f_activity)
        main_box.add_widget(card_info)
        card_contact = MDCard(orientation='vertical', radius=[12], padding=dp(15), spacing=dp(10), elevation=1, adaptive_height=True, md_bg_color=(0.96, 0.98, 1, 1))
        header_contact = MDBoxLayout(orientation='horizontal', spacing=dp(10), adaptive_height=True)
        header_contact.add_widget(MDIcon(icon='card-account-phone-outline', theme_text_color='Primary', font_size='22sp'))
        header_contact.add_widget(MDLabel(text='Coordonnées & GPS', bold=True, theme_text_color='Primary', font_style='Subtitle1'))
        card_contact.add_widget(header_contact)
        card_contact.add_widget(MDBoxLayout(size_hint_y=None, height=dp(1), md_bg_color=(0.9, 0.9, 0.9, 1)))
        f_phone = SmartTextField(text=val_phone, hint_text='Téléphone', input_filter='int', icon_right='phone')
        f_address = SmartTextField(text=val_address, hint_text='Adresse', icon_right='map-marker')
        f_email = SmartTextField(text=val_email, hint_text='Email', icon_right='email')
        gps_box = MDBoxLayout(orientation='horizontal', spacing=dp(5), adaptive_height=True)
        f_gps = SmartTextField(text=val_gps, hint_text='Lien GPS (Google Maps)', icon_right='google-maps', size_hint_x=0.85)
        btn_paste_gps = MDIconButton(icon='content-paste', theme_text_color='Custom', text_color=self.theme_cls.primary_color, pos_hint={'center_y': 0.5}, on_release=lambda x: setattr(f_gps, 'text', Clipboard.paste()))
        gps_box.add_widget(f_gps)
        gps_box.add_widget(btn_paste_gps)
        card_contact.add_widget(f_phone)
        card_contact.add_widget(f_address)
        card_contact.add_widget(gps_box)
        card_contact.add_widget(f_email)
        main_box.add_widget(card_contact)
        f_price_cat = MDTextField(text=display_cat, hint_text='Catégorie de Prix', readonly=True, icon_right='tag')

        def on_cat_touch(instance, touch):
            if instance.collide_point(*touch.pos):
                self.show_price_cat_selector(instance)
                return True
            return False
        f_price_cat.bind(on_touch_down=on_cat_touch)
        if self.current_entity_type_mgmt == 'account':
            card_comm = MDCard(orientation='vertical', radius=[12], padding=dp(15), spacing=dp(10), elevation=1, adaptive_height=True, md_bg_color=(1, 0.98, 0.96, 1))
            header_comm = MDBoxLayout(orientation='horizontal', spacing=dp(10), adaptive_height=True)
            header_comm.add_widget(MDIcon(icon='store-cog-outline', theme_text_color='Primary', font_size='22sp'))
            header_comm.add_widget(MDLabel(text='Commercial', bold=True, theme_text_color='Primary', font_style='Subtitle1'))
            card_comm.add_widget(header_comm)
            card_comm.add_widget(MDBoxLayout(size_hint_y=None, height=dp(1), md_bg_color=(0.9, 0.9, 0.9, 1)))
            card_comm.add_widget(f_price_cat)
            main_box.add_widget(card_comm)
        card_fisc = MDCard(orientation='vertical', radius=[12], padding=dp(15), spacing=dp(10), elevation=1, adaptive_height=True, md_bg_color=(0.95, 0.95, 0.95, 1))
        header_fisc = MDBoxLayout(orientation='horizontal', spacing=dp(10), adaptive_height=True)
        header_fisc.add_widget(MDIcon(icon='file-document-multiple-outline', theme_text_color='Primary', font_size='22sp'))
        header_fisc.add_widget(MDLabel(text='Information Fiscale', bold=True, theme_text_color='Primary', font_style='Subtitle1'))
        card_fisc.add_widget(header_fisc)
        card_fisc.add_widget(MDBoxLayout(size_hint_y=None, height=dp(1), md_bg_color=(0.9, 0.9, 0.9, 1)))
        f_rc = SmartTextField(text=val_rc, hint_text='N° RC')
        f_nif = SmartTextField(text=val_nif, hint_text='N.I.F')
        f_nis = SmartTextField(text=val_nis, hint_text='N.I.S')
        f_nai = SmartTextField(text=val_nai, hint_text='N.A.I')
        card_fisc.add_widget(f_rc)
        card_fisc.add_widget(f_nif)
        card_fisc.add_widget(f_nis)
        card_fisc.add_widget(f_nai)
        main_box.add_widget(card_fisc)

        def save(x):
            name_val = f_name.get_value().strip()
            if not name_val:
                f_name.error = True
                self.notify('Nom obligatoire', 'error')
                return
            cat_ar = 'تجزئة'
            if self.current_entity_type_mgmt == 'account':
                selected_cat_fr = f_price_cat.text
                if selected_cat_fr == 'Gros':
                    cat_ar = 'جملة'
                elif selected_cat_fr == 'Demi-Gros':
                    cat_ar = 'نصف جملة'
                else:
                    cat_ar = 'تجزئة'
            raw_gps_input = f_gps.get_value().strip()
            gps_txt = ''
            lat_val = ''
            lon_val = ''
            if raw_gps_input:
                gps_txt = raw_gps_input
                import re
                url_match = re.search('(https?://[^\\s]+)', raw_gps_input)
                if url_match:
                    gps_txt = url_match.group(1)
                if is_edit and raw_gps_input == val_gps and old_lat and old_lon:
                    lat_val = old_lat
                    lon_val = old_lon
            payload = {'action': 'update' if is_edit else 'add', 'type': self.current_entity_type_mgmt, 'name': name_val, 'phone': f_phone.get_value().strip(), 'address': f_address.get_value().strip(), 'gps_location': gps_txt, 'lat': lat_val, 'lon': lon_val, 'activity': f_activity.get_value().strip(), 'email': f_email.get_value().strip(), 'price_category': cat_ar, 'rc': f_rc.get_value().strip(), 'nif': f_nif.get_value().strip(), 'nis': f_nis.get_value().strip(), 'nai': f_nai.get_value().strip(), 'id': entity.get('id') if is_edit else None}
            if self.is_server_reachable:
                UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/manage_entity', req_body=json.dumps(payload), req_headers={'Content-type': 'application/json'}, method='POST', on_success=lambda r, s: [self.ae_dialog.dismiss(), self.notify('Succès', 'success'), self.fetch_entities(self.current_entity_type_mgmt)], on_failure=lambda r, e: self.notify(f'Erreur: {e}', 'error'))
            else:
                self.notify('Impossible: Mode Hors Ligne', 'error')
        footer_box = MDBoxLayout(orientation='vertical', spacing=dp(10), adaptive_height=True, padding=[0, dp(10), 0, 0])
        btn_save = MDRaisedButton(text='ENREGISTRER', md_bg_color=(0, 0.7, 0, 1), text_color=(1, 1, 1, 1), size_hint_x=1, height=dp(50), elevation=2, on_release=save)
        btn_cancel = MDRaisedButton(text='ANNULER', md_bg_color=(0.9, 0.9, 0.9, 1), text_color=(0.3, 0.3, 0.3, 1), size_hint_x=1, height=dp(50), elevation=0, on_release=lambda x: self.ae_dialog.dismiss())
        footer_box.add_widget(btn_save)
        footer_box.add_widget(btn_cancel)
        main_box.add_widget(footer_box)
        scroll.add_widget(main_box)
        self.ae_dialog = MDDialog(title=title, type='custom', content_cls=scroll, size_hint=(0.98, 0.96))
        self.ae_dialog.open()

    def show_price_cat_selector(self, text_field_instance):
        content = MDBoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=dp(160), padding=dp(10))

        def select(value):
            text_field_instance.text = value
            self.cat_dialog.dismiss()
        content.add_widget(MDRaisedButton(text='Détail', size_hint_x=1, md_bg_color=(0, 0.6, 0.6, 1), on_release=lambda x: select('Détail')))
        content.add_widget(MDRaisedButton(text='Demi-Gros', size_hint_x=1, md_bg_color=(0.9, 0.6, 0, 1), on_release=lambda x: select('Demi-Gros')))
        content.add_widget(MDRaisedButton(text='Gros', size_hint_x=1, md_bg_color=(0.5, 0, 0.5, 1), on_release=lambda x: select('Gros')))
        self.cat_dialog = MDDialog(title='Choisir Catégorie', type='custom', content_cls=content, size_hint=(0.8, None))
        self.cat_dialog.open()

    def confirm_delete_entity(self, entity):
        if not self.is_server_reachable:
            if hasattr(self, 'options_dialog') and self.options_dialog:
                self.options_dialog.dismiss()
            self.ae_dialog = MDDialog(title='Hors Ligne', text='Gestion des tiers impossible en mode hors ligne.\nVeuillez vous connecter au serveur.', buttons=[MDFlatButton(text='OK', on_release=lambda x: self.ae_dialog.dismiss())])
            self.ae_dialog.open()
            return
        if self.options_dialog:
            self.options_dialog.dismiss()

        def do_delete(x):
            if self.del_conf_dialog:
                self.del_conf_dialog.dismiss()
            payload = {'action': 'delete', 'id': entity['id'], 'type': self.current_entity_type_mgmt}
            if self.is_server_reachable:
                UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/manage_entity', req_body=json.dumps(payload), req_headers={'Content-type': 'application/json'}, method='POST', on_success=lambda r, s: [self.notify('Compte supprimé', 'success'), self.fetch_entities(self.current_entity_type_mgmt)], on_failure=lambda r, e: self.notify('Impossible (Contient des opérations)', 'error'))
            else:
                self.notify('Erreur connexion', 'error')
        name_display = self.fix_text(entity['name'])
        self.del_conf_dialog = MDDialog(title='Confirmation', text=f'Voulez-vous vraiment supprimer {name_display} ?\nCette action est irréversible.', buttons=[MDFlatButton(text='NON', on_release=lambda x: self.del_conf_dialog.dismiss()), MDRaisedButton(text='OUI, SUPPRIMER', md_bg_color=(1, 0, 0, 1), on_release=do_delete)])
        self.del_conf_dialog.open()

    def check_server_heartbeat(self, dt):
        if self.sync_paused:
            self.is_server_reachable = False
            if self.status_bar_label:
                self.status_bar_label.text = 'Synchronisation Arrêtée (PAUSE)'
                self.status_bar_bg.md_bg_color = (0.8, 0, 0, 1)
            return
        threading.Thread(target=self._run_socket_ping_logic, daemon=True).start()

    def _run_socket_ping_logic(self):
        ping_val = self._try_ping_host(self.local_server_ip)
        if ping_val is not None:
            self._finalize_ping_ui(True, ping_val, self.local_server_ip)
            return
        if self.external_server_ip:
            ping_val_ext = self._try_ping_host(self.external_server_ip)
            if ping_val_ext is not None:
                self._finalize_ping_ui(True, ping_val_ext, self.external_server_ip)
                return
        self._finalize_ping_ui(False, 0, None)

    def _try_ping_host(self, ip_address):
        if not ip_address:
            return None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            start_time = time.time()
            sock.connect((ip_address, int(DEFAULT_PORT)))
            sock.close()
            end_time = time.time()
            return int((end_time - start_time) * 1000)
        except:
            return None

    @mainthread
    def _finalize_ping_ui(self, success, ping_val, confirmed_ip):
        if success:
            self.last_ping = ping_val
            self.active_server_ip = confirmed_ip
            self._on_heartbeat_success()
        else:
            self._on_heartbeat_fail_final(None, 'Connection Failed')

    def _reset_notification_state(self, dt):
        if not self.status_bar_label:
            return
        self.status_bar_label.markup = True
        if self._ready_timer:
            self._ready_timer.cancel()
            self._ready_timer = None
        if self.sync_paused:
            self.status_bar_label.text = 'Synchronisation Arrêtée (PAUSE)'
            self.status_bar_bg.md_bg_color = (0.8, 0, 0, 1)
            return
        self._notify_event = None
        pending = len([k for k in self.offline_store.keys() if not self.offline_store.get(k).get('synced', False)])
        ping_display = ''
        bg_color = (0.4, 0.4, 0.4, 1)
        ping_val = getattr(self, 'last_ping', 0)
        if self.is_server_reachable:
            if ping_val < 100:
                bg_color = (0, 0.7, 0, 1)
            elif ping_val < 300:
                bg_color = (0.9, 0.5, 0, 1)
            else:
                bg_color = (0.8, 0, 0, 1)
            ping_display = f' • [color=FFFFFF][b][size=16sp]{ping_val}ms[/size][/b][/color]'
        if pending > 0:
            if self.is_server_reachable and ping_val >= 300:
                self.status_bar_bg.md_bg_color = (0.8, 0, 0, 1)
            else:
                self.status_bar_bg.md_bg_color = (0.9, 0.5, 0, 1)
            self.status_bar_label.text = f'En attente de sync: {pending}{ping_display}'
        elif self.is_server_reachable:
            net = 'Local' if self.active_server_ip == self.local_server_ip else 'Ext'
            self.status_bar_bg.md_bg_color = bg_color
            self.status_bar_label.text = f'Connecté ({net}){ping_display}'
        else:
            self.status_bar_label.text = 'Hors Ligne'
            self.status_bar_bg.md_bg_color = (0.4, 0.4, 0.4, 1)

    def fetch_store_info(self):
        if self.is_server_reachable:
            url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/store_info'
            UrlRequest(url, on_success=self.save_store_info_callback)

    def save_store_info_callback(self, req, res):
        if res:
            self.store.put('print_header', name=res.get('name', 'MagPro Store'), address=res.get('address', ''), phone=res.get('phone', ''))
            self.maps_enabled = res.get('maps_enabled', False)
            if DEBUG:
                print(f'[INFO] Maps Enabled on Server: {self.maps_enabled}')

    def _on_heartbeat_success(self):
        was_offline = not self.is_server_reachable
        self.is_server_reachable = True
        self.silent_user_check()
        unsynced_orders = [k for k in self.offline_store.keys() if not self.offline_store.get(k).get('synced', False)]
        if unsynced_orders:
            self.try_sync_offline_data()
        self.sync_gps_data()
        if self.is_offline_mode:
            self.is_offline_mode = False
            self.notify(f"Connexion Rétablie ({('Local' if self.active_server_ip == self.local_server_ip else 'Ext')})", 'success')
            self.fetch_products()
            self.fetch_categories()
            self.fetch_entities('account')
            self.fetch_entities('supplier')
            self.fetch_store_info()
        if hasattr(self, 'login_status_icon'):
            self.login_status_icon.text_color = (0, 0.8, 0, 1)
        if not self._notify_event:
            self._reset_notification_state(0)
        if not self.store.exists('print_header'):
            self.fetch_store_info()

    def silent_user_check(self):
        if not self.store.exists('credentials'):
            return
        creds = self.store.get('credentials')
        user = creds.get('username')
        pwd = creds.get('password')
        url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/login'
        body = json.dumps({'username': user, 'password': pwd})

        def on_silent_success(req, res):
            if res.get('status') == 'success':
                server_sales_mode = res.get('sales_mode', 'store')
                if getattr(self, 'user_sales_mode', '') != server_sales_mode:
                    self.user_sales_mode = server_sales_mode
                    self.store.put('credentials', username=user, password=pwd, sales_mode=server_sales_mode)
                    self.update_location_display()
                    self.notify(f'Mode Stock mis à jour: {server_sales_mode}', 'info')
                role = str(res.get('role', '')).lower()
                seller_roles = ['cashier', 'baye', 'vendeur', 'seller', 'بائع']
                should_be_seller = role in seller_roles
                if self.is_seller_mode != should_be_seller:
                    self.is_seller_mode = should_be_seller
                    self.store.put('config', ip=self.local_server_ip, ext_ip=self.external_server_ip, seller_mode=self.is_seller_mode)
                    self.update_dashboard_layout()
                    msg = 'Mode Vendeur Activé (Sync)' if should_be_seller else 'Mode Admin Activé (Sync)'
                    self.notify(msg, 'info')
        UrlRequest(url, req_body=body, req_headers={'Content-type': 'application/json'}, method='POST', on_success=on_silent_success)

    def _on_heartbeat_fail_final(self, req, err):
        if self.is_server_reachable:
            self.is_server_reachable = False
            self.is_offline_mode = True
            self.notify('Mode Hors Ligne (No Connection)', 'error')
        if hasattr(self, 'login_status_icon'):
            self.login_status_icon.text_color = (0.8, 0, 0, 1)
        if not self._notify_event:
            self._reset_notification_state(0)

    def try_sync_offline_data(self):
        if self.sync_paused:
            return
        if not self.is_server_reachable:
            return
        keys = list(self.offline_store.keys())
        unsynced = [k for k in keys if not self.offline_store.get(k).get('synced', False)]
        if not unsynced:
            self._reset_notification_state(0)
            return
        sorted_keys = sorted(unsynced, key=lambda x: int(x.split('_')[0]) if x.split('_')[0].isdigit() else 0)
        key = sorted_keys[0]
        try:
            item_data = self.offline_store.get(key)
            data = item_data['order_data']
            endpoint = '/api/submit_payment' if data.get('is_simple_payment') else '/api/submit_order'

            def next_step(*args):
                Clock.schedule_once(lambda d: self.try_sync_offline_data(), 0.5)

            def success(r, res):
                item_data['synced'] = True
                item_data['sync_timestamp'] = time.time()
                if res.get('server_id'):
                    item_data['order_data']['server_id'] = res.get('server_id')
                if res.get('invoice_number'):
                    item_data['order_data']['invoice_number'] = res.get('invoice_number')
                self.offline_store.put(key, **item_data)
                self.notify(f"Sync OK: {data.get('doc_type', 'Op')}", 'success')
                next_step()

            def failure(req, err):
                print(f'Sync Fail for {key}: {err}')
                next_step()
            UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}{endpoint}', req_body=json.dumps(data), req_headers={'Content-type': 'application/json'}, method='POST', on_success=success, on_failure=failure, on_error=failure, timeout=10)
        except Exception as e:
            print(f'Sync Logic Error: {e}')
            Clock.schedule_once(lambda d: self.try_sync_offline_data(), 1)

    def notify(self, text, type='info'):
        if not self.status_bar_label:
            return
        color_map = {'success': (0, 0.6, 0, 1), 'error': (0.8, 0.1, 0.1, 1), 'warning': (0.9, 0.5, 0, 1), 'info': (0.2, 0.2, 0.2, 1)}
        self.status_bar_label.text = text
        self.status_bar_bg.md_bg_color = color_map.get(type, (0.2, 0.2, 0.2, 1))
        if self._notify_event:
            self._notify_event.cancel()
        self._notify_event = Clock.schedule_once(self._reset_notification_state, 3)

    def change_status_to_ready(self, dt):
        pending = len([k for k in self.offline_store.keys() if not self.offline_store.get(k).get('synced', False)])
        if self.is_server_reachable and (not self.sync_paused) and (pending == 0):
            self.status_bar_label.text = 'Prêt'
            self.status_bar_bg.md_bg_color = (0.15, 0.5, 0.15, 1)

    def update_location_display(self):
        if hasattr(self, 'btn_loc_screen'):
            mode = getattr(self, 'user_sales_mode', 'store')
            if not mode:
                mode = 'store'
            if mode == 'truck':
                self.btn_loc_screen.text = 'VAN'
                self.btn_loc_screen.icon = 'truck'
                self.btn_loc_screen.md_bg_color = (0.6, 0.4, 0.2, 1)
                self.selected_location = 'store'
            elif self.selected_location == 'store':
                self.btn_loc_screen.text = 'MAGASIN'
                self.btn_loc_screen.icon = 'store'
                self.btn_loc_screen.md_bg_color = self.theme_cls.primary_color
            else:
                self.btn_loc_screen.text = 'DEPOT'
                self.btn_loc_screen.icon = 'warehouse'
                self.btn_loc_screen.md_bg_color = (0.8, 0.4, 0, 1)

    def _auto_login_check(self, dt):
        if self.store.exists('config'):
            config = self.store.get('config')
            self.is_seller_mode = config.get('seller_mode', False)
        if self.store.exists('credentials'):
            creds = self.store.get('credentials')
            saved_user = creds.get('username', '')
            saved_pass = creds.get('password', '')
            self.user_sales_mode = creds.get('sales_mode', 'store')
            self.username_field.text = saved_user
            self.password_field.text = saved_pass
            self.current_user_name = saved_user
            self.update_dashboard_layout()
            self.update_location_display()
            if self.username_field.text:
                self.do_login(None)

    def do_login(self, x):
        self.notify('Connexion...', 'info')
        url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/login'
        body = json.dumps({'username': self.username_field.get_value(), 'password': self.password_field.get_value()})
        UrlRequest(url, req_body=body, req_headers={'Content-type': 'application/json'}, method='POST', on_success=self.login_success, on_failure=self.login_fail, on_error=self.login_error, timeout=4)

    def login_success(self, req, res):
        if res.get('status') == 'success':
            self.current_user_name = self.username_field.get_value()
            server_sales_mode = res.get('sales_mode', 'store')
            self.user_sales_mode = server_sales_mode
            role = str(res.get('role', '')).lower()
            seller_roles = ['cashier', 'baye', 'vendeur', 'seller', 'بائع']
            if role in seller_roles:
                self.is_seller_mode = True
                self.notify(f'Mode Vendeur Activé', 'info')
            else:
                self.is_seller_mode = False
            self.store.put('credentials', username=self.current_user_name, password=self.password_field.get_value(), sales_mode=self.user_sales_mode)
            self.store.put('config', ip=self.local_server_ip, ext_ip=self.external_server_ip, seller_mode=self.is_seller_mode)
            self.store.put('last_login', username=self.current_user_name)
            self.is_offline_mode = False
            self.is_server_reachable = True
            self.sm.current = 'dashboard'
            self.fetch_products()
            self.fetch_entities('account')
            self.fetch_entities('supplier')
            self.fetch_store_info()
            self.check_and_load_stats()
            self.update_dashboard_layout()
            self.update_location_display()
            if platform == 'android':
                Clock.schedule_once(lambda dt: self.start_gps_service(), 1)
        else:
            self.notify('Identifiants incorrects', 'error')

    def login_fail(self, req, res):
        self.check_offline_access()

    def login_error(self, req, error):
        self.check_offline_access()

    def check_offline_access(self):
        if self.store.exists('credentials'):
            creds = self.store.get('credentials')
            if self.username_field.get_value() == creds.get('username', '') and self.password_field.get_value() == creds.get('password', ''):
                if self.cache_store.exists('products'):
                    self.notify('Mode Hors Ligne', 'warning')
                    self.is_offline_mode = True
                    self.current_user_name = self.username_field.get_value()
                    self.store.put('last_login', username=self.current_user_name)
                    self.sm.current = 'dashboard'
                    self.load_products_from_cache()
                    if self.cache_store.exists('clients'):
                        self.all_clients = self.cache_store.get('clients')['data']
                    if self.cache_store.exists('suppliers'):
                        self.all_suppliers = self.cache_store.get('suppliers')['data']
                    self.check_and_load_stats()
                else:
                    self.notify('Pas de données locales', 'error')
            else:
                self.notify('Erreur Login', 'error')
        else:
            self.notify('Serveur inaccessible', 'error')

    def logout(self):

        def perform_logout(x):
            if hasattr(self, 'logout_diag') and self.logout_diag:
                self.logout_diag.dismiss()
            if self.store.exists('credentials'):
                self.store.delete('credentials')
            self.password_field.text = ''
            self.sm.current = 'login'
        if not self.is_server_reachable:
            self.logout_diag = MDDialog(title='Attention : Hors Ligne', text="Le serveur est inaccessible !\nSi vous vous déconnectez maintenant, vous ne pourrez plus vous reconnecter tant que la liaison avec le serveur n'est pas rétablie.\n\nVoulez-vous vraiment continuer ?", buttons=[MDFlatButton(text='ANNULER', on_release=lambda x: self.logout_diag.dismiss()), MDRaisedButton(text='OUI, SE DÉCONNECTER', md_bg_color=(1, 0, 0, 1), on_release=perform_logout)])
            self.logout_diag.open()
        else:
            perform_logout(None)

    def _create_stat_item(self, title, ref_name, color):
        box = MDBoxLayout(orientation='vertical', padding=dp(5), md_bg_color=(1, 1, 1, 1), radius=[5])
        box.add_widget(MDLabel(text=title, font_style='Caption', halign='center'))
        val_lbl = MDLabel(text='0.00 DA', font_style='Subtitle2', bold=True, halign='center', theme_text_color='Custom', text_color=color)
        setattr(self, ref_name, val_lbl)
        box.add_widget(val_lbl)
        return box

    def _create_dash_btn(self, icon, text, bg_color, icon_color, action):
        card = MDCard(orientation='vertical', padding=dp(15), radius=[12], ripple_behavior=True, on_release=action, md_bg_color=bg_color, elevation=2, size_hint_y=None, height=dp(110))
        card.add_widget(MDIcon(icon=icon, font_size='38sp', pos_hint={'center_x': 0.5}, theme_text_color='Custom', text_color=icon_color))
        card.add_widget(MDLabel(text=text, halign='center', bold=True, font_style='Caption'))
        return card

    def _build_login_screen(self):
        screen = MDScreen(name='login')
        layout = MDFloatLayout()
        self.login_status_icon = MDIcon(icon='circle', font_size='15sp', pos_hint={'top': 0.96, 'right': 0.85}, theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1))
        layout.add_widget(self.login_status_icon)
        layout.add_widget(MDIconButton(icon='cog', pos_hint={'top': 0.98, 'right': 0.98}, on_release=self.open_ip_settings))
        card = MDCard(orientation='vertical', size_hint=(0.85, None), height=dp(340), pos_hint={'center_x': 0.5, 'center_y': 0.5}, padding=dp(20), spacing=dp(15), radius=[20], elevation=4)
        icon_box = MDFloatLayout(size_hint_y=None, height=dp(70))
        icon_box.add_widget(MDIcon(icon='store', font_size='60sp', pos_hint={'center_x': 0.5, 'center_y': 0.5}, theme_text_color='Primary'))
        card.add_widget(icon_box)
        card.add_widget(MDLabel(text='MagPro Gestion de Stock', halign='center', font_style='H5', bold=True))
        saved_user = 'ADMIN'
        if self.store.exists('credentials'):
            saved_user = self.store.get('credentials').get('username', 'ADMIN')
        elif self.store.exists('last_login'):
            saved_user = self.store.get('last_login').get('username', 'ADMIN')
        self.current_user_name = saved_user
        self.username_field = SmartTextField(hint_text='Utilisateur', text=self.current_user_name, icon_right='account')
        self.password_field = SmartTextField(hint_text='Mot de passe', password=True, icon_right='key')
        card.add_widget(self.username_field)
        card.add_widget(self.password_field)
        card.add_widget(MDFillRoundFlatButton(text='CONNEXION', font_size='18sp', size_hint_x=1, on_release=self.do_login))
        layout.add_widget(card)
        footer_label = MDLabel(text='MagPro v7.1.0 © 2026', halign='center', pos_hint={'center_x': 0.5, 'y': 0.02}, size_hint_y=None, height=dp(20), font_style='Caption', theme_text_color='Hint')
        layout.add_widget(footer_label)
        screen.add_widget(layout)
        return screen

    def open_delivery_map(self):
        if not self.is_server_reachable:
            self.notify('Serveur inaccessible (Hors Ligne)', 'error')
            return
        if not getattr(self, 'maps_enabled', False):
            self.notify("Cette fonctionnalité n'est pas activée sur le serveur (License requise)", 'error')
            return
        self.notify('Sécurisation du lien...', 'info')
        api_url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/get_secure_map_link'
        body = json.dumps({'username': self.current_user_name})
        headers = {'Content-type': 'application/json'}

        def on_token_received(req, result):
            token = result.get('token')
            if token:
                final_url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/delivery_map/{token}'
                self.notify('Ouverture de la carte...', 'success')
                import webbrowser
                try:
                    webbrowser.open(final_url)
                except Exception as e:
                    self.notify(f'Erreur navigateur: {e}', 'error')
            else:
                self.notify('Erreur: Token non reçu', 'error')

        def on_fail(req, err):
            self.notify(f'Erreur Map: {str(err)}', 'error')
        UrlRequest(api_url, req_body=body, req_headers=headers, method='POST', on_success=on_token_received, on_failure=on_fail, on_error=on_fail)

    def _build_dashboard_screen(self):
        screen = MDScreen(name='dashboard')
        layout = MDBoxLayout(orientation='vertical')
        self.dash_toolbar = MDTopAppBar(title='Accueil', left_action_items=[['clipboard-text-clock', lambda x: self.show_pending_dialog()]], right_action_items=[['map', lambda x: self.open_delivery_map()], ['logout', lambda x: self.logout()]])
        layout.add_widget(self.dash_toolbar)
        scroll = MDScrollView()
        self.main_dash_content = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(20), padding=dp(15))
        self.buttons_container = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(15))
        self.main_dash_content.add_widget(self.buttons_container)
        self.stats_card_container = MDCard(orientation='vertical', size_hint_y=None, height=dp(280), padding=dp(10), radius=[10], elevation=2, md_bg_color=(0.97, 0.97, 0.97, 1))
        scroll.add_widget(self.main_dash_content)
        layout.add_widget(scroll)
        screen.add_widget(layout)
        return screen

    def _build_products_screen(self):
        screen = MDScreen(name='products')
        root_layout = MDFloatLayout()
        self.rv_products = ProductRecycleView()
        self.rv_products.size_hint = (1, 1)
        self.rv_products.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        def set_rv_padding(dt):
            if hasattr(self.rv_products, 'layout_manager') and self.rv_products.layout_manager:
                self.rv_products.layout_manager.padding = [dp(5), dp(220), dp(5), dp(70)]
        Clock.schedule_once(set_rv_padding, 0.1)
        root_layout.add_widget(self.rv_products)
        header_container = MDBoxLayout(orientation='vertical', adaptive_height=True, md_bg_color=(1, 1, 1, 1))
        header_container.pos_hint = {'top': 1}
        self.prod_toolbar = MDTopAppBar(title='Produits', left_action_items=[['arrow-left', lambda x: self.go_back()]], elevation=2)
        header_container.add_widget(self.prod_toolbar)
        self.prod_search_layout = MDBoxLayout(orientation='horizontal', padding=[dp(10), dp(5), dp(10), dp(0)], spacing=dp(5), size_hint_y=None, height=dp(55), md_bg_color=(1, 1, 1, 1))
        self.search_field = SmartTextField(hint_text='Rechercher...', mode='rectangle', icon_right='magnify', size_hint_y=None, height=dp(40), pos_hint={'center_y': 0.5}, size_hint_x=1)
        self.search_field.bind(text=self.filter_products)
        self.prod_search_layout.add_widget(self.search_field)
        self.btn_scan_prod = MDIconButton(icon='barcode-scan', theme_text_color='Custom', text_color=(0.2, 0.2, 0.2, 1), pos_hint={'center_y': 0.5}, icon_size='28sp', on_release=self.open_barcode_scanner)
        self.prod_search_layout.add_widget(self.btn_scan_prod)
        self.btn_add_prod = MDIconButton(icon='plus-circle', theme_text_color='Custom', text_color=(0, 0.7, 0, 1), pos_hint={'center_y': 0.5}, icon_size='36sp', on_release=lambda x: self.show_manage_product_dialog(None))
        self.prod_search_layout.add_widget(self.btn_add_prod)
        header_container.add_widget(self.prod_search_layout)
        header_container.add_widget(MDBoxLayout(size_hint_y=None, height=dp(5)))
        self.selected_family_filter = 'TOUS'
        filter_box = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(50), padding=[dp(10), 0, dp(10), dp(5)])
        family_filter_card = MDCard(size_hint=(1, 1), radius=[5], md_bg_color=(0.96, 0.96, 0.96, 1), line_color=(0.6, 0.6, 0.6, 1), line_width=1, elevation=0, ripple_behavior=True, on_release=self.open_filter_menu)
        card_content = MDBoxLayout(orientation='horizontal', padding=[dp(15), 0])
        self.btn_main_family_filter = MDLabel(text='TOUS', theme_text_color='Custom', text_color=(0.15, 0.15, 0.15, 1), font_style='Subtitle1', bold=True, halign='left', valign='center')
        arrow_icon = MDIcon(icon='menu-down', pos_hint={'center_y': 0.5}, theme_text_color='Secondary')
        card_content.add_widget(self.btn_main_family_filter)
        card_content.add_widget(arrow_icon)
        family_filter_card.add_widget(card_content)
        filter_box.add_widget(family_filter_card)
        header_container.add_widget(filter_box)
        from kivymd.uix.card import MDSeparator
        header_container.add_widget(MDSeparator(height=dp(1), color=(0.9, 0.9, 0.9, 1)))
        root_layout.add_widget(header_container)
        self.cart_bar = MDCard(size_hint_y=None, height=dp(60), padding=[dp(15), dp(5)], md_bg_color=self.theme_cls.primary_color, radius=[15, 15, 0, 0], ripple_behavior=True, on_release=self.open_cart_screen, elevation=4, pos_hint={'bottom': 1})
        cart_box = MDBoxLayout(orientation='horizontal')
        self.lbl_cart_count = MDLabel(text='PANIER (0)', theme_text_color='Custom', text_color=(1, 1, 1, 1), bold=True, halign='left', size_hint_x=0.5, font_style='Subtitle1')
        self.lbl_cart_total = MDLabel(text='0.00 DA', theme_text_color='Custom', text_color=(1, 1, 1, 1), bold=True, halign='right', font_style='H6', size_hint_x=0.5)
        cart_box.add_widget(self.lbl_cart_count)
        cart_box.add_widget(self.lbl_cart_total)
        self.cart_bar.add_widget(cart_box)
        root_layout.add_widget(self.cart_bar)
        screen.add_widget(root_layout)
        return screen

    def open_filter_menu(self, instance):
        if not hasattr(self, 'all_categories') or not self.all_categories:
            self.all_categories = ['Tout']
            self.fetch_categories()
        full_list = self.all_categories
        if 'Tout' not in full_list:
            full_list.insert(0, 'Tout')
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, adaptive_height=True, padding=dp(0))
        scroll = MDScrollView(size_hint_y=None, height=dp(300))
        list_layout = MDBoxLayout(orientation='vertical', adaptive_height=True)
        for fam in full_list:
            btn = MDFlatButton(text=fam, theme_text_color='Custom', text_color=(0.2, 0.2, 0.2, 1), font_style='Subtitle1', size_hint_x=1, height=dp(50))
            btn.bind(on_release=lambda x, f=fam: self.apply_filter(f))
            list_layout.add_widget(btn)
            from kivymd.uix.card import MDSeparator
            list_layout.add_widget(MDSeparator(height=dp(1), color=(0.9, 0.9, 0.9, 1)))
        scroll.add_widget(list_layout)
        content.add_widget(scroll)
        self.filter_dialog = MDDialog(title='Filtrer par famille', type='custom', content_cls=content, size_hint=(0.85, None))
        self.filter_dialog.open()

    def apply_filter(self, category_name):
        self.selected_family_filter = category_name
        if hasattr(self, 'btn_main_family_filter'):
            self.btn_main_family_filter.text = category_name
        if hasattr(self, 'filter_dialog') and self.filter_dialog:
            self.filter_dialog.dismiss()
        self.notify(f'Filtre: {category_name}', 'info')
        if self.is_server_reachable:
            cat_param = category_name if category_name != 'Tout' else ''
            import urllib.parse
            encoded_cat = urllib.parse.quote(cat_param)
            url = f'http://{self.active_server_ip}:{5000}/api/products?category={encoded_cat}'
            from kivy.network.urlrequest import UrlRequest
            UrlRequest(url, on_success=self.on_products_loaded)
        else:
            if category_name == 'Tout' or category_name == 'TOUS':
                self.current_product_list_source = self.all_products_raw
            else:
                self.current_product_list_source = [p for p in self.all_products_raw if str(p.get('category', '')).strip() == category_name.strip()]
            self.load_more_products(reset=True)

    def _build_cart_screen(self):
        from kivymd.uix.button import MDFillRoundFlatIconButton, MDFillRoundFlatButton
        screen = MDScreen(name='cart')
        layout = MDBoxLayout(orientation='vertical')
        self.cart_toolbar = MDTopAppBar(title='Panier', left_action_items=[['arrow-left', lambda x: self.back_to_products()]])
        layout.add_widget(self.cart_toolbar)
        selectors = MDCard(orientation='horizontal', size_hint_y=None, height=dp(70), padding=dp(10), radius=0, md_bg_color=(0.95, 0.95, 0.95, 1))
        self.btn_ent_screen = MDFillRoundFlatButton(text='Client', size_hint_x=0.45, on_release=self.handle_entity_button_click)
        self.btn_loc_screen = MDFillRoundFlatIconButton(text='Magasin', icon='store', size_hint_x=0.45, on_release=self.toggle_location)
        selectors.add_widget(self.btn_ent_screen)
        selectors.add_widget(MDBoxLayout(size_hint_x=0.1))
        selectors.add_widget(self.btn_loc_screen)
        layout.add_widget(selectors)
        self.rv_cart = CartRecycleView()
        layout.add_widget(self.rv_cart)
        self.footer_card = MDCard(orientation='vertical', size_hint_y=None, height=dp(150), padding=dp(15), spacing=dp(10), radius=[20, 20, 0, 0], elevation=4)
        total_row = MDBoxLayout(orientation='horizontal')
        self.lbl_total_title = MDLabel(text='TOTAL:', bold=True, font_style='Subtitle1')
        self.lbl_cart_screen_total = MDLabel(text='0.00 DA', halign='right', font_style='H5', bold=True, theme_text_color='Primary')
        total_row.add_widget(self.lbl_total_title)
        total_row.add_widget(self.lbl_cart_screen_total)
        self.btn_validate_cart = MDFillRoundFlatButton(text='VALIDER LA COMMANDE', size_hint_x=1, height=dp(55), md_bg_color=(0, 0.7, 0, 1), on_release=self.open_payment_dialog)
        self.footer_card.add_widget(total_row)
        self.footer_card.add_widget(self.btn_validate_cart)
        layout.add_widget(self.footer_card)
        screen.add_widget(layout)
        return screen

    def open_cart_screen(self, x=None):
        if not self.cart:
            self.dialog = MDDialog(title='Panier vide', text='Veuillez ajouter au moins un produit pour continuer.', buttons=[MDFlatButton(text='OK', on_release=lambda x: self.dialog.dismiss())])
            self.dialog.open()
            return
        if self.current_mode != 'transfer' and self.selected_entity is None:
            self.show_entity_selection_dialog(None, next_action=lambda: self.open_cart_screen(None))
            return
        self.refresh_cart_screen_items()
        self.sm.transition.direction = 'left'
        self.sm.current = 'cart'

    def back_to_products(self):
        self.sm.transition.direction = 'right'
        self.sm.current = 'products'

    def handle_entity_button_click(self, instance):
        if self.current_mode == 'transfer':
            self.toggle_location(instance)
        else:
            self.show_entity_selection_dialog(instance)

    def refresh_cart_screen_items(self):
        is_invoice_mode = self.current_mode in ['invoice_sale', 'invoice_purchase', 'proforma']
        total_ht, total_tva = self.calculate_cart_totals(self.cart, is_invoice_mode)
        timbre = 0.0
        if self.current_mode == 'invoice_sale':
            method = getattr(self, 'editing_payment_method', '')
            if method in ['دفع نقدًا', 'Espèce', 'Cash']:
                timbre = self._calculate_stamp_duty(total_ht + total_tva)
        total_ttc = self._round_num(total_ht + total_tva + timbre)
        items_count = len(self.cart)
        if hasattr(self, 'cart_toolbar'):
            self.cart_toolbar.title = f'Panier ({items_count})'
        if hasattr(self, 'lbl_cart_screen_total'):
            self.lbl_cart_screen_total.text = f'{total_ttc:.2f} DA'
        if hasattr(self, 'lbl_total_title'):
            if timbre > 0:
                self.lbl_total_title.text = 'TOTAL (+Timbre):'
            else:
                self.lbl_total_title.text = 'TOTAL:'
        self.update_location_display()
        if hasattr(self, 'btn_ent_screen'):
            if self.current_mode == 'transfer':
                src = 'Magasin' if self.selected_location == 'store' else 'Dépôt'
                dst = 'Dépôt' if self.selected_location == 'store' else 'Magasin'
                self.btn_ent_screen.text = f'{src}  >>>  {dst}'
                self.btn_ent_screen.md_bg_color = (0.5, 0, 0.5, 1)
            else:
                if self.selected_entity:
                    self.btn_ent_screen.text = self.fix_text(self.selected_entity.get('name', 'Client'))[:15]
                color_bg = (0, 0.6, 0.6, 1) if self.current_mode in ['sale', 'invoice_sale'] else (0.8, 0.4, 0, 1)
                self.btn_ent_screen.md_bg_color = color_bg
        rv_data = []
        for item in self.cart:
            try:
                p = float(item.get('price', 0))
                q = float(item.get('qty', 0))
                t_rate = float(item.get('tva', 0)) if is_invoice_mode else 0.0
                line_ht = self._round_num(p * q)
                line_ttc = self._round_num(line_ht * (1 + t_rate / 100.0))
                q_disp = str(int(q)) if q.is_integer() else str(q)
                if self.current_mode == 'transfer':
                    details_text = f'Qté: {q_disp}'
                    d_color = [0.1, 0.4, 0.8, 1]
                else:
                    details_text = f'{p:.2f} DA x {q_disp}'
                    if t_rate > 0 and is_invoice_mode:
                        details_text += f' (+{int(t_rate)}% TVA)'
                    details_text += f' = {line_ttc:.2f} DA'
                    d_color = [0.4, 0.4, 0.4, 1]
                rv_data.append({'name': item.get('name', 'Produit'), 'details': details_text, 'd_color': d_color, 'raw_item': item})
            except Exception as e:
                print(f'Error processing cart item for RV: {e}')
        if hasattr(self, 'rv_cart'):
            self.rv_cart.data = rv_data
            self.rv_cart.refresh_from_data()
        if self.current_mode == 'transfer':
            if hasattr(self, 'total_bg_card'):
                self.total_bg_card.opacity = 0
            if hasattr(self, 'btn_validate_cart'):
                self.btn_validate_cart.text = 'VALIDER LE TRANSFERT'
        else:
            if hasattr(self, 'total_bg_card'):
                self.total_bg_card.opacity = 1
            if hasattr(self, 'btn_validate_cart'):
                self.btn_validate_cart.text = 'VALIDER LA COMMANDE'

    def edit_cart_item(self, item):

        def fmt_num(value):
            try:
                val_float = float(value)
                if val_float.is_integer():
                    return str(int(val_float))
                return str(val_float)
            except:
                return '0'
        is_invoice = self.current_mode in ['invoice_sale', 'invoice_purchase', 'proforma']
        dialog_height = dp(600) if is_invoice else dp(520)
        content = MDBoxLayout(orientation='vertical', spacing='10dp', size_hint_y=None, height=dialog_height, padding=[0, '5dp', 0, 0])
        self.active_edit_target = 'qty'
        self.input_reset_mode = True
        self.name_cleared_once = False

        def update_edit_colors():
            ACTIVE_BG = (0.9, 1, 0.9, 1)
            INACTIVE_BG = (0.95, 0.95, 0.95, 1)
            if hasattr(self, 'edit_qty_card'):
                if self.active_edit_target == 'qty':
                    self.edit_qty_card.md_bg_color = ACTIVE_BG
                    self.edit_qty_card.elevation = 3
                else:
                    self.edit_qty_card.md_bg_color = INACTIVE_BG
                    self.edit_qty_card.elevation = 0
            if hasattr(self, 'edit_price_card'):
                if self.active_edit_target == 'price':
                    self.edit_price_card.md_bg_color = ACTIVE_BG
                    self.edit_price_card.elevation = 3
                else:
                    self.edit_price_card.md_bg_color = INACTIVE_BG
                    self.edit_price_card.elevation = 0
            if hasattr(self, 'edit_tva_card'):
                if self.active_edit_target == 'tva':
                    self.edit_tva_card.md_bg_color = ACTIVE_BG
                    self.edit_tva_card.elevation = 3
                else:
                    self.edit_tva_card.md_bg_color = INACTIVE_BG
                    self.edit_tva_card.elevation = 0
            if hasattr(self, 'edit_name_card'):
                if self.active_edit_target == 'name':
                    self.edit_name_card.md_bg_color = ACTIVE_BG
                    self.edit_name_card.elevation = 3
                else:
                    self.edit_name_card.md_bg_color = INACTIVE_BG
                    self.edit_name_card.elevation = 0
        raw_name = item.get('name', 'Produit')
        is_autre_article = str(raw_name).startswith('Autre Article')
        if is_autre_article:
            self.edit_name_card = MDCard(size_hint_y=None, height='70dp', radius=[10], padding=[10, 0, 10, 0], elevation=0)
            self.edit_name_field = SmartTextField(text=self.fix_text(raw_name), hint_text="Nom de l'article", font_size='22sp', halign='center', mode='line', line_color_normal=(0, 0, 0, 0), line_color_focus=(0, 0, 0, 0), pos_hint={'center_y': 0.5})

            def on_name_touch(instance, touch):
                if instance.collide_point(*touch.pos):
                    self.active_edit_target = 'name'
                    update_edit_colors()
                    if not self.name_cleared_once:
                        instance.text = ''
                        if hasattr(instance, '_raw_text'):
                            instance._raw_text = ''
                        self.name_cleared_once = True
                    return False
                return False
            self.edit_name_field.bind(on_touch_down=on_name_touch)
            self.edit_name_card.add_widget(self.edit_name_field)
            name_row_container = MDBoxLayout(size_hint_y=None, height='75dp', padding=[20, 0, 20, 0])
            name_row_container.add_widget(self.edit_name_card)
            content.add_widget(name_row_container)
        else:
            product_name = self.fix_text(raw_name)
            lbl_prod = MDLabel(text=product_name, halign='center', bold=True, font_style='Subtitle1', theme_text_color='Primary', adaptive_height=True)
            content.add_widget(lbl_prod)
        if self.current_mode != 'transfer':
            price_val = item.get('price', 0)
            self.edit_price_card = MDCard(size_hint_y=None, height='70dp', radius=[10], padding=[10, 0, 10, 0], elevation=0)
            self.edit_price_field = NoMenuTextField(text=fmt_num(price_val), hint_text='Prix Unitaire (DA)', font_size='26sp', halign='center', mode='line', readonly=True, line_color_normal=(0, 0, 0, 0), line_color_focus=(0, 0, 0, 0), pos_hint={'center_y': 0.5})
            self.edit_price_field.theme_text_color = 'Custom'
            self.edit_price_field.text_color_normal = (0, 0, 0, 1)
            self.edit_price_field.text_color_focus = (0, 0, 0, 1)

            def on_price_touch(instance, touch):
                if instance.collide_point(*touch.pos):
                    if self.active_edit_target != 'price':
                        self.input_reset_mode = True
                    self.active_edit_target = 'price'
                    update_edit_colors()
                    return True
                return False
            self.edit_price_field.bind(on_touch_down=on_price_touch)
            self.edit_price_card.add_widget(self.edit_price_field)
            price_row_container = MDBoxLayout(size_hint_y=None, height='75dp', padding=[60, 0, 60, 0])
            price_row_container.add_widget(self.edit_price_card)
            content.add_widget(price_row_container)
        if is_invoice:
            tva_val = item.get('tva', 0)
            self.edit_tva_card = MDCard(size_hint_y=None, height='60dp', radius=[10], padding=[10, 0, 10, 0], elevation=0)
            self.edit_tva_field = NoMenuTextField(text=fmt_num(tva_val), hint_text='TVA %', font_size='24sp', halign='center', mode='line', readonly=True, line_color_normal=(0, 0, 0, 0), line_color_focus=(0, 0, 0, 0), pos_hint={'center_y': 0.5})
            self.edit_tva_field.theme_text_color = 'Custom'
            self.edit_tva_field.text_color_normal = (0, 0, 0, 1)
            self.edit_tva_field.text_color_focus = (0, 0, 0, 1)

            def on_tva_touch(instance, touch):
                if instance.collide_point(*touch.pos):
                    if self.active_edit_target != 'tva':
                        self.input_reset_mode = True
                    self.active_edit_target = 'tva'
                    update_edit_colors()
                    return True
                return False
            self.edit_tva_field.bind(on_touch_down=on_tva_touch)
            self.edit_tva_card.add_widget(self.edit_tva_field)
            tva_row = MDBoxLayout(size_hint_y=None, height='65dp', padding=[100, 0, 100, 0])
            tva_row.add_widget(self.edit_tva_card)
            content.add_widget(tva_row)
        qty_row = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='65dp', padding=[40, 0])
        btn_minus = MDIconButton(icon='minus', theme_text_color='Custom', text_color=(1, 1, 1, 1), md_bg_color=(0.9, 0.3, 0.3, 1), pos_hint={'center_y': 0.5}, icon_size='20sp')
        qty_val = item.get('qty', 1)
        self.edit_qty_card = MDCard(size_hint_x=1, size_hint_y=None, height='60dp', radius=[10], padding=[10, 0, 10, 0], elevation=0, pos_hint={'center_y': 0.5})
        self.edit_qty_field = NoMenuTextField(text=fmt_num(qty_val), hint_text='Qté', font_size='28sp', halign='center', readonly=True, mode='line', line_color_normal=(0, 0, 0, 0), line_color_focus=(0, 0, 0, 0), pos_hint={'center_y': 0.5})
        self.edit_qty_field.theme_text_color = 'Custom'
        self.edit_qty_field.text_color_normal = (0, 0, 0, 1)
        self.edit_qty_field.text_color_focus = (0, 0, 0, 1)

        def on_qty_touch(instance, touch):
            if instance.collide_point(*touch.pos):
                if self.active_edit_target != 'qty':
                    self.input_reset_mode = True
                self.active_edit_target = 'qty'
                update_edit_colors()
                return True
            return False
        self.edit_qty_field.bind(on_touch_down=on_qty_touch)
        self.edit_qty_card.add_widget(self.edit_qty_field)
        btn_plus = MDIconButton(icon='plus', theme_text_color='Custom', text_color=(1, 1, 1, 1), md_bg_color=(0.2, 0.7, 0.2, 1), pos_hint={'center_y': 0.5}, icon_size='20sp')
        qty_row.add_widget(btn_minus)
        qty_row.add_widget(self.edit_qty_card)
        qty_row.add_widget(btn_plus)
        content.add_widget(qty_row)
        self.btn_save_edit = MDRaisedButton(text='MODIFIER', md_bg_color=(0, 0.6, 0, 1), text_color=(1, 1, 1, 1), size_hint_x=0.7, size_hint_y=1, font_size='18sp', elevation=3)

        def update_calculations():
            try:
                q = float(self.edit_qty_field.text or 0)
            except:
                q = 0.0
            p = 0.0
            if hasattr(self, 'edit_price_field'):
                try:
                    p = float(self.edit_price_field.text or 0)
                except:
                    p = 0.0
            else:
                p = float(item.get('price', 0))
            tva = 0.0
            if hasattr(self, 'edit_tva_field'):
                try:
                    tva = float(self.edit_tva_field.text or 0)
                except:
                    tva = 0.0
            line_ht = self._round_num(q * p)
            total = self._round_num(line_ht * (1 + tva / 100.0))
            if self.current_mode != 'transfer':
                self.btn_save_edit.text = f'MODIFIER\n{total:.2f} DA'
            else:
                self.btn_save_edit.text = 'MODIFIER'

        def change_qty(amount):
            try:
                current = float(self.edit_qty_field.text or 0)
                new_val = current + amount
                if new_val < 1:
                    new_val = 1
                self.edit_qty_field.text = fmt_num(new_val)
                update_calculations()
            except:
                self.edit_qty_field.text = '1'
        btn_plus.bind(on_release=lambda x: change_qty(1))
        btn_minus.bind(on_release=lambda x: change_qty(-1))

        def get_active_field():
            if self.active_edit_target == 'name':
                return None
            if self.active_edit_target == 'price' and hasattr(self, 'edit_price_field'):
                return self.edit_price_field
            if self.active_edit_target == 'tva' and hasattr(self, 'edit_tva_field'):
                return self.edit_tva_field
            return self.edit_qty_field

        def add_digit(digit):
            field = get_active_field()
            if not field:
                return
            current = field.text
            if self.input_reset_mode:
                if digit == '.':
                    field.text = '0.'
                else:
                    field.text = str(digit)
                self.input_reset_mode = False
            elif digit == '.':
                if '.' in current:
                    return
                if not current:
                    field.text = '0.'
                else:
                    field.text = current + '.'
            elif current == '0':
                field.text = str(digit)
            else:
                field.text = current + str(digit)
            update_calculations()

        def backspace(x=None):
            field = get_active_field()
            if not field:
                return
            current = field.text
            self.input_reset_mode = False
            if len(current) > 0:
                field.text = current[:-1]
            update_calculations()
        grid = MDGridLayout(cols=3, spacing='8dp', size_hint_y=1, padding=[20, 0])
        keys = ['7', '8', '9', '4', '5', '6', '1', '2', '3', '.', '0', 'DEL']
        for key in keys:
            if key == 'DEL':
                btn = MDIconButton(icon='backspace-outline', theme_text_color='Custom', text_color=(0, 0, 0, 1), md_bg_color=(0.8, 0.8, 0.8, 1), size_hint=(1, 1), icon_size='22sp', on_release=backspace)
            else:
                btn = MDRaisedButton(text=key, md_bg_color=(0.95, 0.95, 0.95, 1), theme_text_color='Custom', text_color=(0, 0, 0, 1), font_size='22sp', size_hint=(1, 1), elevation=1, on_release=lambda x, k=key: add_digit(k))
            grid.add_widget(btn)
        content.add_widget(grid)
        content.add_widget(MDLabel(text='', size_hint_y=None, height='5dp'))
        buttons_box = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='60dp')
        btn_cancel = MDFlatButton(text='ANNULER', theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1), size_hint_x=0.3, on_release=lambda x: self.edit_dialog.dismiss())

        def save_changes(x):
            try:
                q_text = self.edit_qty_field.text or '0'
                new_q = float(q_text)
                if new_q <= 0:
                    raise ValueError
                if getattr(self, 'user_sales_mode', 'store') == 'truck' and self.current_mode in ['sale', 'invoice_sale', 'proforma']:
                    original_prod = None
                    if hasattr(self, 'all_products_raw'):
                        for p in self.all_products_raw:
                            if str(p['id']) == str(item['id']):
                                original_prod = p
                                break
                    if original_prod:
                        available_stock = float(original_prod.get('stock', 0) or 0)
                        if available_stock > -900000:
                            if new_q > available_stock:
                                self.notify(f'Stock VAN insuffisant ! Disponible : {int(available_stock)}', 'error')
                                return
                item['qty'] = new_q
                if self.current_mode in ['sale', 'return_sale', 'invoice_sale', 'proforma']:
                    specials = item.get('special_prices', [])
                    base_price = item.get('original_unit_price', item['price'])
                    new_price = base_price
                    if specials and (not item.get('has_promo', False)):
                        specials.sort(key=lambda x: x['qty'], reverse=True)
                        for sp in specials:
                            if new_q >= sp['qty']:
                                if sp['type'] == 'TOTAL':
                                    new_price = float(sp['price']) / new_q
                                else:
                                    new_price = float(sp['price'])
                                break
                    if hasattr(self, 'edit_price_field') and self.active_edit_target == 'price':
                        p_text = self.edit_price_field.text or '0'
                        item['price'] = float(p_text)
                    else:
                        item['price'] = new_price
                elif self.current_mode != 'transfer' and hasattr(self, 'edit_price_field'):
                    p_text = self.edit_price_field.text or '0'
                    new_p = float(p_text)
                    if new_p < 0:
                        raise ValueError
                    item['price'] = new_p
                if hasattr(self, 'edit_tva_field'):
                    tva_text = self.edit_tva_field.text or '0'
                    new_tva = float(tva_text)
                    if new_tva < 0:
                        new_tva = 0
                    item['tva'] = new_tva
                if hasattr(self, 'edit_name_field'):
                    new_name_val = self.edit_name_field.get_value().strip()
                    if new_name_val:
                        item['name'] = new_name_val
                self.refresh_cart_screen_items()
                self.update_cart_button()
                self.edit_dialog.dismiss()
            except Exception as e:
                print(e)
                self.notify('Valeurs invalides', 'error')
        self.btn_save_edit.bind(on_release=save_changes)
        buttons_box.add_widget(btn_cancel)
        buttons_box.add_widget(self.btn_save_edit)
        content.add_widget(buttons_box)
        update_edit_colors()
        update_calculations()
        self.edit_dialog = MDDialog(title='', type='custom', content_cls=content, buttons=[], size_hint=(0.85, None))
        self.edit_dialog.open()

    def open_ip_settings(self, instance=None):
        try:
            if hasattr(self, 'dialog') and self.dialog:
                self.dialog.dismiss()
            scroll_view = MDScrollView(size_hint_y=None, height=dp(550))
            content_list = MDList()

            def add_section(text):
                lbl = MDLabel(text=text, theme_text_color='Custom', text_color=self.theme_cls.primary_color, font_style='Subtitle2', bold=True, size_hint_y=None, height=dp(40), padding=(dp(20), dp(10)))
                content_list.add_widget(lbl)

            def add_option(title, details, icon_name, action_callback, icon_color=None):
                item = TwoLineAvatarIconListItem(text=title, secondary_text=details, on_release=action_callback)
                icon = IconLeftWidget(icon=icon_name)
                if icon_color:
                    icon.text_color = icon_color
                item.add_widget(icon)
                content_list.add_widget(item)
            if not self.is_seller_mode:
                add_section('CONNEXION SERVEUR')
                ip_desc = f'Local: {self.local_server_ip}'
                if self.external_server_ip:
                    ip_desc += f' | Ext: {self.external_server_ip}'
                add_option('Configuration IP', ip_desc, 'lan-connect', self.show_ip_config_dialog)
                add_section('IMPRIMANTE (Bluetooth)')
                printer_conf = {'name': 'Non configurée', 'mac': '', 'auto': False}
                if self.store.exists('printer_config'):
                    printer_conf = self.store.get('printer_config')
                p_name = printer_conf.get('name', 'Non configurée') or 'Non configurée'
                add_option('Choisir Imprimante', f'Actuelle: {p_name}', 'printer-wireless', lambda x: [self.dialog.dismiss(), self.open_bluetooth_selector(x)])
                add_option("Oublier l'imprimante", "Déconnecter l'appareil actuel", 'printer-off', lambda x: self.clear_printer_selection(x), icon_color=(0.8, 0, 0, 1))
                auto_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), padding=(dp(20), 0))
                lbl_auto = MDLabel(text='Impression Auto après validation', theme_text_color='Primary', size_hint_x=0.8)
                chk_auto = MDCheckbox(active=printer_conf.get('auto', False), size_hint=(None, None), size=(dp(40), dp(40)), pos_hint={'center_y': 0.5})
                chk_auto.bind(active=self.toggle_auto_print_setting)
                auto_layout.add_widget(lbl_auto)
                auto_layout.add_widget(chk_auto)
                content_list.add_widget(auto_layout)
                add_section('AFFICHAGE')
                current_screen_state = True
                if self.store.exists('screen_config'):
                    current_screen_state = self.store.get('screen_config').get('keep_on', True)
                screen_layout = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60), padding=(dp(20), 0))
                lbl_screen = MDLabel(text="Garder l'écran allumé\n(Requis pour le GPS)", theme_text_color='Primary', size_hint_x=0.8, font_style='Body1')
                chk_screen = MDCheckbox(active=current_screen_state, size_hint=(None, None), size=(dp(48), dp(48)), pos_hint={'center_y': 0.5})
                chk_screen.bind(active=lambda inst, val: self.set_screen_keep_alive(val))
                screen_layout.add_widget(lbl_screen)
                screen_layout.add_widget(chk_screen)
                content_list.add_widget(screen_layout)
            add_section('ADMINISTRATION')
            if not self.is_seller_mode:
                add_option('Activer Mode Vendeur', 'Verrouiller les paramètres', 'shield-account', lambda x: [self.dialog.dismiss(), self.open_seller_auth_dialog(x)])
            else:
                add_option('Quitter Mode Vendeur', 'Accès Admin requis', 'lock-open', lambda x: [self.dialog.dismiss(), self.open_seller_auth_dialog(x)])
            scroll_view.add_widget(content_list)
            self.dialog = MDDialog(title='Paramètres', type='custom', content_cls=scroll_view, buttons=[MDFlatButton(text='FERMER', theme_text_color='Custom', text_color=self.theme_cls.primary_color, on_release=lambda x: self.dialog.dismiss())], size_hint=(0.95, None))
            self.dialog.open()
        except Exception as e:
            self.notify(f'Erreur Menu: {e}', 'error')

    def show_ip_config_dialog(self, instance):
        if self.dialog:
            self.dialog.dismiss()
        content = MDBoxLayout(orientation='vertical', spacing='15dp', size_hint_y=None, height=dp(180), padding=[0, dp(10), 0, 0])
        self.field_local_ip = MDTextField(text=self.local_server_ip, hint_text='IP Locale (Wifi)', icon_right='router-wireless')
        self.field_ext_ip = MDTextField(text=self.external_server_ip, hint_text='IP Externe (Internet)', icon_right='web')
        content.add_widget(self.field_local_ip)
        content.add_widget(self.field_ext_ip)
        self.ip_dialog = MDDialog(title='Configuration Serveur', type='custom', content_cls=content, buttons=[MDFlatButton(text='ANNULER', on_release=lambda x: [self.ip_dialog.dismiss(), self.open_ip_settings()]), MDRaisedButton(text='SAUVEGARDER', md_bg_color=(0, 0.6, 0, 1), on_release=self.save_ip_new_logic)])
        self.ip_dialog.open()

    def save_ip_new_logic(self, instance):
        local_ip = self.field_local_ip.text.strip()
        ext_ip = self.field_ext_ip.text.strip()
        if DataValidator.validate_ip(local_ip):
            self.local_server_ip = local_ip
            self.external_server_ip = ext_ip
            self.active_server_ip = local_ip
            self.store.put('config', ip=self.local_server_ip, ext_ip=self.external_server_ip, seller_mode=self.is_seller_mode)
            self.ip_dialog.dismiss()
            self.notify('Paramètres IP enregistrés', 'success')
            self.check_server_heartbeat(0)
            self.open_ip_settings()
        else:
            self.notify('Adresse IP Locale invalide', 'error')
            self.field_local_ip.error = True

    def toggle_auto_print_setting(self, instance, value):
        name = ''
        mac = ''
        if self.store.exists('printer_config'):
            conf = self.store.get('printer_config')
            name = conf.get('name', '')
            mac = conf.get('mac', '')
        self.store.put('printer_config', name=name, mac=mac, auto=value)

    def open_seller_auth_dialog(self, x):
        if self.dialog:
            self.dialog.dismiss()
        has_pass = self.store.exists('seller_config')
        if has_pass:
            title = 'Accès Admin'
            height = dp(80)
        else:
            title = 'Créer Mot de Passe'
            height = dp(150)
        content = MDBoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=height)
        hint_1 = 'Mot de passe Admin' if has_pass else 'Nouveau mot de passe'
        self.seller_pass_field = MDTextField(hint_text=hint_1, password=True, halign='center')
        content.add_widget(self.seller_pass_field)
        self.seller_pass_confirm_field = None
        if not has_pass:
            self.seller_pass_confirm_field = MDTextField(hint_text='Confirmer le mot de passe', password=True, halign='center')
            content.add_widget(self.seller_pass_confirm_field)
        self.auth_dialog = MDDialog(title=title, type='custom', content_cls=content, buttons=[MDFlatButton(text='ANNULER', on_release=lambda x: self.auth_dialog.dismiss()), MDRaisedButton(text='OK', on_release=lambda x: self.check_create_seller_pass(has_pass))])
        self.auth_dialog.open()

    def check_create_seller_pass(self, exists):
        pwd = self.seller_pass_field.text
        if not pwd:
            return
        if exists:
            if pwd == self.store.get('seller_config')['password']:
                self.auth_dialog.dismiss()
                self.open_seller_toggle_dialog()
            else:
                self.notify('Mot de passe incorrect', 'error')
        else:
            self.store.put('seller_config', password=pwd)
            self.auth_dialog.dismiss()
            self.open_seller_toggle_dialog()

    def open_seller_toggle_dialog(self):
        content = MDBoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=dp(50), padding=[20, 0])
        content.add_widget(MDLabel(text='Mode Vendeur (Restreint)'))
        chk = MDCheckbox(active=self.is_seller_mode, size_hint=(None, None), size=(dp(48), dp(48)))
        chk.bind(active=self.on_seller_mode_switch)
        content.add_widget(chk)
        self.toggle_dialog = MDDialog(title='Configuration Mode', type='custom', content_cls=content, buttons=[MDFlatButton(text='FERMER', on_release=lambda x: self.toggle_dialog.dismiss())])
        self.toggle_dialog.open()

    def on_seller_mode_switch(self, instance, value):
        self.is_seller_mode = value
        self.store.put('config', ip=self.local_server_ip, ext_ip=self.external_server_ip, seller_mode=value)
        self.update_dashboard_layout()
        self.notify(f"Mode Vendeur: {('Activé' if value else 'Désactivé')}", 'info')

    def open_family_selector_dialog(self):
        if not hasattr(self, 'all_categories') or not self.all_categories:
            self.all_categories = ['Tout']
            self.fetch_categories()
        selectable_cats = [c for c in self.all_categories if c != 'Tout']
        if not selectable_cats:
            self.notify('Aucune famille disponible (Créer sur PC)', 'info')
            return
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(400))
        scroll = MDScrollView()
        list_layout = MDList()
        item_none = OneLineListItem(text='(Aucune)', on_release=lambda x: self._select_family('(Aucune)'))
        list_layout.add_widget(item_none)
        for cat in selectable_cats:
            item = OneLineListItem(text=cat, on_release=lambda x, c=cat: self._select_family(c))
            list_layout.add_widget(item)
        scroll.add_widget(list_layout)
        content.add_widget(scroll)
        self.family_dialog = MDDialog(title='Choisir une famille', type='custom', content_cls=content, size_hint=(0.8, None), buttons=[MDFlatButton(text='ANNULER', on_release=lambda x: self.family_dialog.dismiss())])
        self.family_dialog.open()

    def _select_family(self, category_name):
        if hasattr(self, 'btn_select_family'):
            self.btn_select_family.text = category_name
        if hasattr(self, 'family_dialog'):
            self.family_dialog.dismiss()

    def fetch_categories(self):
        if self.is_server_reachable:
            UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/categories', on_success=self.on_categories_loaded)

    def on_categories_loaded(self, req, res):
        self.all_categories = ['Tout'] + res if res else ['Tout']
        if hasattr(self, 'cat_menu') and self.cat_menu:
            self.cat_menu.items = [{'text': cat, 'viewclass': 'OneLineListItem', 'on_release': lambda x=cat: self.set_category_filter(x)} for cat in self.all_categories]

    def open_category_filter(self, button):
        from kivymd.uix.menu import MDDropdownMenu
        if not hasattr(self, 'all_categories') or not self.all_categories:
            self.all_categories = ['Tout']
            self.fetch_categories()
        menu_items = [{'text': cat, 'viewclass': 'OneLineListItem', 'on_release': lambda x=cat: self.set_category_filter(x)} for cat in self.all_categories]
        self.cat_menu = MDDropdownMenu(caller=button, items=menu_items, width_mult=4)
        self.cat_menu.open()

    def set_category_filter(self, category_name):
        if hasattr(self, 'cat_menu') and self.cat_menu:
            self.cat_menu.dismiss()
        self.notify(f'Filtre: {category_name}', 'info')
        if self.is_server_reachable:
            cat_param = category_name if category_name != 'Tout' else ''
            import urllib.parse
            encoded_cat = urllib.parse.quote(cat_param)
            url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/products?category={encoded_cat}'
            UrlRequest(url, on_success=self.on_products_loaded)
        else:
            if category_name == 'Tout':
                self.current_product_list_source = self.all_products_raw
            else:
                self.current_product_list_source = [p for p in self.all_products_raw if str(p.get('category', '')) == category_name]
            self.load_more_products(reset=True)

    def fetch_products(self):
        user_param = self.current_user_name
        import urllib.parse
        encoded_user = urllib.parse.quote(user_param)
        UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/products?username={encoded_user}', on_success=self.on_products_loaded)

    def on_products_loaded(self, req, res):
        try:
            self.all_products_raw = res
            Clock.schedule_once(lambda dt: self.cache_store.put('products', data=res), 0.1)
            self.prepare_products_for_rv(res)
        except Exception as e:
            print(f'Error loading products: {e}')

    def fetch_entities(self, type_):
        UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/entities?type={type_}', on_success=lambda r, x: self.on_entities_loaded(type_, x))

    def on_entities_loaded(self, type_, data):
        key = 'clients' if type_ == 'account' else 'suppliers'
        if type_ == 'account':
            self.all_clients = data
        else:
            self.all_suppliers = data
        Clock.schedule_once(lambda dt: self.cache_store.put(key, data=data), 0.1)
        if hasattr(self, 'mgmt_dialog') and self.mgmt_dialog:
            try:
                if self.current_entity_type_mgmt == type_:
                    self.filter_entities_for_manager('')
            except:
                pass

    def load_products_from_cache(self):
        if self.cache_store.exists('products'):
            self.all_products_raw = self.cache_store.get('products')['data']
            self.prepare_products_for_rv(self.all_products_raw)

    def filter_entities(self, instance, text=None):
        query = instance.get_value() if hasattr(instance, 'get_value') else text
        if self._entity_search_event:
            self._entity_search_event.cancel()
        self._entity_search_event = Clock.schedule_once(lambda dt: self._start_entity_background_search(query), 0.3)

    def _start_entity_background_search(self, query):
        threading.Thread(target=self._entity_search_worker, args=(query,), daemon=True).start()

    def _entity_search_worker(self, query):
        if not query:
            self.populate_entity_list(self.entities_source[:50])
            return
        txt = query.lower()
        filtered = [e for e in self.entities_source if txt in str(e.get('name', '')).lower() or txt in str(e.get('phone', '')).lower()]
        if not filtered:
            try:
                fixed_query = self.fix_text(txt)
                filtered = [e for e in self.entities_source if fixed_query in self.fix_text(str(e.get('name', '')))]
            except Exception:
                pass
        if len(filtered) > 50:
            filtered = filtered[:50]
        self.populate_entity_list(filtered)

    @mainthread
    def populate_entity_list(self, entities, next_action=None):
        server_default_names = ['Comptoir', 'Fournisseur', 'زبون افتراضي', 'مورد افتراضي']

        def is_default(name):
            return str(name).strip() in server_default_names
        defaults = [e for e in entities if is_default(e.get('name', ''))]
        others = [e for e in entities if not is_default(e.get('name', ''))]
        others.sort(key=lambda x: x.get('name', '').lower())
        if self.current_mode in ['client_payment', 'supplier_payment']:
            final_list = others
        else:
            final_list = defaults + others
        rv_data = []
        sales_modes = ['sale', 'return_sale', 'invoice_sale', 'proforma', 'client_payment']
        is_client_mode = self.current_mode in sales_modes
        bal_color_hex = '00C853' if is_client_mode else 'D50000'
        for e in final_list:
            raw_name = e.get('name', '')
            is_def_acc = is_default(raw_name)
            if is_def_acc:
                if is_client_mode:
                    display_name = 'CLIENT'
                else:
                    display_name = 'FOURNISSEUR'
                balance_markup = '[size=18sp][b][color=101010]COMPTOIR[/color][/b][/size]'
                icon_name = 'store'
                icon_col = [0, 0.4, 0.7, 1]
            else:
                display_name = raw_name
                balance = float(e.get('balance', 0))
                bal_text = f'{balance:.2f} DA'
                balance_markup = f'Solde: [color={bal_color_hex}][b]{bal_text}[/b][/color]'
                if balance <= 0:
                    icon_name = 'account-check'
                    icon_col = [0, 0.7, 0, 1]
                else:
                    icon_name = 'account-alert'
                    icon_col = [0.9, 0, 0, 1]
            rv_data.append({'raw_name': display_name, 'balance_text': balance_markup, 'icon': icon_name, 'icon_color': icon_col, 'raw_data': e})
        if hasattr(self, 'rv_entity'):
            self.rv_entity.data = rv_data
            self.rv_entity.refresh_from_data()

    def open_mode(self, mode, skip_dialog=False):
        self.current_mode = mode
        if not skip_dialog:
            self.cart = []
            self.selected_entity = None
        self.selected_location = 'store'
        self.update_cart_button()
        titles = {'sale': 'Vente', 'purchase': 'Achat', 'return_sale': 'Retour Client', 'return_purchase': 'Retour Frns', 'transfer': 'Transfert', 'manage_products': 'Gestion Produits', 'invoice_sale': 'Facture Vente', 'invoice_purchase': 'Facture Achat', 'proforma': 'Facture Proforma', 'order_purchase': 'Bon de Commande'}
        colors = {'sale': 'Green', 'purchase': 'Orange', 'return_sale': 'Red', 'return_purchase': 'Teal', 'transfer': 'Purple', 'manage_products': 'Blue', 'invoice_sale': 'Blue', 'invoice_purchase': 'DeepOrange', 'proforma': 'Purple', 'order_purchase': 'Teal'}
        self.prod_toolbar.title = titles.get(mode, 'Produits')
        self.theme_cls.primary_palette = colors.get(mode, 'Blue')
        self.prod_toolbar.right_action_items = []
        if mode == 'manage_products':
            if self.btn_add_prod not in self.prod_search_layout.children:
                self.prod_search_layout.add_widget(self.btn_add_prod)
            if hasattr(self, 'btn_scan_prod') and self.btn_scan_prod in self.prod_search_layout.children:
                self.prod_search_layout.remove_widget(self.btn_scan_prod)
            if self.cart_bar:
                self.cart_bar.height = 0
                self.cart_bar.opacity = 0
                self.cart_bar.disabled = True
        else:
            if self.btn_add_prod in self.prod_search_layout.children:
                self.prod_search_layout.remove_widget(self.btn_add_prod)
            if hasattr(self, 'btn_scan_prod') and self.btn_scan_prod not in self.prod_search_layout.children:
                self.prod_search_layout.add_widget(self.btn_scan_prod)
            if self.cart_bar:
                self.cart_bar.height = dp(60)
                self.cart_bar.opacity = 1
                self.cart_bar.disabled = False
        self.current_product_list_source = self.all_products_raw
        self.load_more_products(reset=True)

        def enter_products_screen():
            self.sm.current = 'products'
            if hasattr(self, 'search_field') and self.search_field:
                self.search_field.text = ''
                self.search_field.focus = False
            if self.is_server_reachable:
                self.fetch_products()
                if mode not in ['transfer', 'manage_products']:
                    e_type = 'supplier' if mode in ['purchase', 'return_purchase', 'invoice_purchase', 'order_purchase'] else 'account'
                    self.fetch_entities(e_type)
            elif not self.all_products_raw:
                self.load_products_from_cache()
        modes_requiring_entity = ['sale', 'purchase', 'return_sale', 'return_purchase', 'invoice_sale', 'invoice_purchase', 'proforma', 'order_purchase']
        if mode in modes_requiring_entity and (not skip_dialog):
            e_type = 'supplier' if mode in ['purchase', 'return_purchase', 'invoice_purchase', 'order_purchase'] else 'account'
            if self.is_server_reachable:
                self.fetch_entities(e_type)
            self.show_entity_selection_dialog(None, next_action=enter_products_screen)
        else:
            enter_products_screen()

    def open_add_to_cart_dialog(self, product, mode):
        if mode == 'manage_products':
            self.show_manage_product_dialog(product)
            return

        def fmt_num(value):
            if not value:
                return '0'
            try:
                val_float = float(value)
                if val_float.is_integer():
                    return str(int(val_float))
                return str(val_float)
            except:
                return str(value)
        is_transfer = mode == 'transfer'
        is_sale_context = mode in ['sale', 'return_sale', 'invoice_sale', 'proforma']
        curr_price = 0
        if is_sale_context:
            has_promo = product.get('has_promo', False)
            if has_promo:
                curr_price = float(product.get('price', 0))
            else:
                cat = ''
                if self.selected_entity:
                    cat = str(self.selected_entity.get('category', ''))
                if cat in ['Gros', 'جملة']:
                    curr_price = product.get('price_wholesale', 0)
                elif cat in ['Demi-Gros', 'نصف جملة']:
                    curr_price = product.get('price_semi', 0)
                if float(curr_price or 0) == 0:
                    curr_price = product.get('price', 0)
        else:
            curr_price = product.get('purchase_price', product.get('price', 0))
        prod_name = self.fix_text(product.get('name'))
        price_val_str = fmt_num(curr_price or 0)
        self.active_input_target = 'qty'
        self.input_reset_mode = True

        def update_field_colors():
            ACTIVE_BG = (0.9, 1, 0.9, 1)
            INACTIVE_BG = (0.95, 0.95, 0.95, 1)
            if hasattr(self, 'qty_card'):
                if self.active_input_target == 'qty':
                    self.qty_card.md_bg_color = ACTIVE_BG
                    self.qty_card.elevation = 3
                else:
                    self.qty_card.md_bg_color = INACTIVE_BG
                    self.qty_card.elevation = 0
            if hasattr(self, 'price_card'):
                if self.active_input_target == 'price':
                    self.price_card.md_bg_color = ACTIVE_BG
                    self.price_card.elevation = 3
                else:
                    self.price_card.md_bg_color = INACTIVE_BG
                    self.price_card.elevation = 0
        header_box = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing='5dp', padding=[0, 0, 0, '5dp'])
        lbl_prod = MDLabel(text=prod_name, halign='center', bold=True, font_style='Subtitle1', theme_text_color='Primary', adaptive_height=True)
        header_box.add_widget(lbl_prod)
        if is_sale_context and product.get('has_promo', False):
            promo_label = MDLabel(text='PROMOTION ACTIVÉE', halign='center', theme_text_color='Custom', text_color=(1, 0, 0, 1), font_style='Caption', bold=True, adaptive_height=True)
            header_box.add_widget(promo_label)
        dialog_height = dp(420) if is_transfer else dp(500)
        content = MDBoxLayout(orientation='vertical', spacing='8dp', size_hint_y=None, height=dialog_height, padding=[0, '5dp', 0, 0])
        content.add_widget(header_box)
        if not is_transfer:
            self.price_card = MDCard(size_hint_y=None, height='70dp', radius=[10], padding=[10, 0, 10, 0], elevation=0)
            self.price_field = NoMenuTextField(text=price_val_str, hint_text='Prix Unitaire (DA)', font_size='26sp', halign='center', mode='line', readonly=True, line_color_normal=(0, 0, 0, 0), line_color_focus=(0, 0, 0, 0), pos_hint={'center_y': 0.5})
            self.price_field.theme_text_color = 'Custom'
            self.price_field.text_color_normal = (0, 0, 0, 1)
            self.price_field.text_color_focus = (0, 0, 0, 1)

            def on_price_touch(instance, touch):
                if instance.collide_point(*touch.pos):
                    if self.active_input_target != 'price':
                        self.input_reset_mode = True
                    self.active_input_target = 'price'
                    update_field_colors()
                    return True
                return False
            self.price_field.bind(on_touch_down=on_price_touch)
            self.price_card.add_widget(self.price_field)
            price_row_container = MDBoxLayout(orientation='horizontal', size_hint_y=None, height='75dp', padding=[60, 0, 60, 0])
            price_row_container.add_widget(self.price_card)
            content.add_widget(price_row_container)
        qty_row = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='65dp', padding=[40, 0])
        btn_minus = MDIconButton(icon='minus', theme_text_color='Custom', text_color=(1, 1, 1, 1), md_bg_color=(0.9, 0.3, 0.3, 1), pos_hint={'center_y': 0.5}, icon_size='20sp')
        self.qty_card = MDCard(size_hint_x=1, size_hint_y=None, height='60dp', radius=[10], padding=[10, 0, 10, 0], elevation=0, pos_hint={'center_y': 0.5})
        self.qty_field = NoMenuTextField(text='1', hint_text='Qté', font_size='28sp', halign='center', readonly=True, mode='line', line_color_normal=(0, 0, 0, 0), line_color_focus=(0, 0, 0, 0), pos_hint={'center_y': 0.5})
        self.qty_field.theme_text_color = 'Custom'
        self.qty_field.text_color_normal = (0, 0, 0, 1)
        self.qty_field.text_color_focus = (0, 0, 0, 1)
        self.qty_field.get_value = lambda: self.qty_field.text

        def on_qty_touch(instance, touch):
            if instance.collide_point(*touch.pos):
                if self.active_input_target != 'qty':
                    self.input_reset_mode = True
                self.active_input_target = 'qty'
                update_field_colors()
                return True
            return False
        self.qty_field.bind(on_touch_down=on_qty_touch)
        self.qty_card.add_widget(self.qty_field)
        btn_plus = MDIconButton(icon='plus', theme_text_color='Custom', text_color=(1, 1, 1, 1), md_bg_color=(0.2, 0.7, 0.2, 1), pos_hint={'center_y': 0.5}, icon_size='20sp')
        qty_row.add_widget(btn_minus)
        qty_row.add_widget(self.qty_card)
        qty_row.add_widget(btn_plus)
        content.add_widget(qty_row)
        self.btn_add = MDRaisedButton(text='AJOUTER', md_bg_color=(0, 0.7, 0, 1), text_color=(1, 1, 1, 1), size_hint_x=0.7, size_hint_y=1, font_size='18sp', elevation=3)
        temp_product = product.copy()
        if is_sale_context and (not is_transfer):
            temp_product['price'] = float(curr_price or 0)

        def perform_add(x):
            try:
                q_text = self.qty_field.text
                if not q_text:
                    q_text = '1'
                req_qty = float(q_text)
                current_sales_mode = getattr(self, 'user_sales_mode', 'store')
                if current_sales_mode == 'truck' and self.current_mode in ['sale', 'invoice_sale', 'proforma']:
                    available_stock = float(product.get('stock', 0) or 0)
                    if available_stock > -900000:
                        in_cart_qty = 0
                        for item in self.cart:
                            if str(item['id']) == str(product['id']):
                                in_cart_qty += float(item.get('qty', 0))
                        if in_cart_qty + req_qty > available_stock:
                            self.notify(f'Stock VAN insuffisant ! Disponible : {int(available_stock)}', 'error')
                            return
                if not is_transfer and hasattr(self, 'price_field'):
                    p_text = self.price_field.text
                    if not p_text:
                        p_text = '0'
                    p_val = float(p_text)
                    temp_product['price'] = p_val
                self.qty_field.text = str(req_qty)
                self.add_to_cart(temp_product)
                if self.dialog:
                    self.dialog.dismiss()
            except ValueError:
                self.notify('Valeurs invalides', 'error')
        self.btn_add.bind(on_release=perform_add)

        def update_button_text():
            if is_transfer:
                self.btn_add.text = 'AJOUTER'
                return
            try:
                q = float(self.qty_field.text or 0)
            except:
                q = 1.0
            try:
                p = float(self.price_field.text or 0)
            except:
                p = 0.0
            total_line = q * p
            self.btn_add.text = f'AJOUTER\n{total_line:.2f} DA'

        def increase(x):
            try:
                v = float(self.qty_field.text or 0)
                self.qty_field.text = fmt_num(v + 1)
            except:
                self.qty_field.text = '1'
            update_button_text()

        def decrease(x):
            try:
                v = float(self.qty_field.text or 0)
                if v > 1:
                    self.qty_field.text = fmt_num(v - 1)
            except:
                self.qty_field.text = '1'
            update_button_text()
        btn_plus.bind(on_release=increase)
        btn_minus.bind(on_release=decrease)

        def get_active_field():
            if is_transfer:
                return self.qty_field
            return self.price_field if self.active_input_target == 'price' else self.qty_field

        def add_digit(digit):
            field = get_active_field()
            current = field.text
            if self.input_reset_mode:
                if digit == '.':
                    field.text = '0.'
                else:
                    field.text = str(digit)
                self.input_reset_mode = False
            elif digit == '.':
                if '.' in current:
                    return
                if not current:
                    field.text = '0.'
                else:
                    field.text = current + '.'
            elif current == '0':
                field.text = str(digit)
            else:
                field.text = current + str(digit)
            update_button_text()

        def backspace(instance=None):
            field = get_active_field()
            current = field.text
            self.input_reset_mode = False
            if len(current) > 0:
                field.text = current[:-1]
            update_button_text()
        grid = MDGridLayout(cols=3, spacing='8dp', size_hint_y=1, padding=[20, 0])
        keys = ['7', '8', '9', '4', '5', '6', '1', '2', '3', '.', '0', 'DEL']
        for key in keys:
            if key == 'DEL':
                btn = MDIconButton(icon='backspace-outline', theme_text_color='Custom', text_color=(0, 0, 0, 1), md_bg_color=(0.8, 0.8, 0.8, 1), size_hint=(1, 1), icon_size='20sp', on_release=backspace)
            else:
                btn = MDRaisedButton(text=key, md_bg_color=(0.95, 0.95, 0.95, 1), theme_text_color='Custom', text_color=(0, 0, 0, 1), font_size='22sp', size_hint=(1, 1), elevation=1, on_release=lambda x, k=key: add_digit(k))
            grid.add_widget(btn)
        content.add_widget(grid)
        content.add_widget(MDLabel(text='', size_hint_y=None, height='10dp'))
        buttons_box = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='60dp')
        btn_cancel = MDFlatButton(text='ANNULER', theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1), size_hint_x=0.3, on_release=lambda x: self.dialog.dismiss())
        buttons_box.add_widget(btn_cancel)
        buttons_box.add_widget(self.btn_add)
        content.add_widget(buttons_box)
        update_field_colors()
        update_button_text()
        self.dialog = MDDialog(title='', type='custom', content_cls=content, buttons=[], size_hint=(0.85, None))
        self.dialog.open()

    def show_manage_product_dialog(self, product, prefilled_barcode=None):
        try:
            if not self.is_server_reachable:
                self.dialog = MDDialog(title='Hors Ligne', text='Modification impossible hors ligne.', buttons=[MDFlatButton(text='OK', on_release=lambda x: self.dialog.dismiss())])
                self.dialog.open()
                return
            if product and product.get('name') == 'Autre Article':
                self.notify('Modification interdite (Système)', 'error')
                return
            is_edit = product is not None
            title = 'Fiche Produit' if is_edit else 'Nouveau Produit'
            val_name = product.get('name', '') if is_edit else ''
            val_barcode = product.get('barcode', '') if is_edit else prefilled_barcode if prefilled_barcode else ''
            val_reference = product.get('description', '') if is_edit else ''
            val_num_prod = str(product.get('product_ref') or product.get('ref') or '') if is_edit else ''
            if val_num_prod == 'None':
                val_num_prod = ''
            raw_fam = str(product.get('category', '')) if is_edit else ''
            val_family = raw_fam if raw_fam and raw_fam.lower() != 'none' else '(Aucune)'
            current_image = product.get('image', '') if is_edit else ''

            def fmt(v):
                try:
                    val = float(v)
                    return f'{val:.2f}' if val > 0 else ''
                except:
                    return ''

            def fmt_int(v):
                try:
                    val = float(v)
                    return str(int(val)) if val.is_integer() else str(val)
                except:
                    return '0'
            val_cost = fmt(product.get('purchase_price', 0)) if is_edit else ''
            val_p1 = fmt(product.get('price', 0)) if is_edit else ''
            val_p2 = fmt(product.get('price_semi', 0)) if is_edit else ''
            val_p3 = fmt(product.get('price_wholesale', 0)) if is_edit else ''
            raw_stock = float(product.get('stock', 0) or 0.0) if is_edit else 0.0
            is_unlimited = raw_stock <= -900000
            val_stock = '' if is_unlimited else fmt_int(raw_stock)
            has_movements = product.get('is_used', False) if is_edit else False
            scroll = MDScrollView(size_hint_y=None, height=dp(600))
            main_box = MDBoxLayout(orientation='vertical', adaptive_height=True, spacing=dp(15), padding=[dp(10), dp(10), dp(10), dp(20)])
            card_info = MDCard(orientation='vertical', radius=[12], padding=dp(15), spacing=dp(10), elevation=1, adaptive_height=True)
            self.field_num = MDTextField(text=val_num_prod, hint_text='N° Produit', size_hint_x=1, icon_right='pound')
            card_info.add_widget(self.field_num)
            box_bar = MDBoxLayout(orientation='horizontal', spacing=dp(5), adaptive_height=True)
            self.field_bar = MDTextField(text=val_barcode, hint_text='Code-Barres', size_hint_x=1, icon_right='barcode')

            def scan_into_field(x):
                self.target_scan_field = self.field_bar
                self.open_barcode_scanner(None)
            btn_scan_field = MDIconButton(icon='barcode-scan', on_release=scan_into_field)
            btn_gen = MDIconButton(icon='refresh', on_release=lambda x: setattr(self.field_bar, 'text', '7' + ''.join([str(random.randint(0, 9)) for _ in range(12)])))
            box_bar.add_widget(self.field_bar)
            box_bar.add_widget(btn_scan_field)
            box_bar.add_widget(btn_gen)
            card_info.add_widget(box_bar)
            self.field_name = SmartTextField(text=val_name, hint_text='Désignation*', required=True, icon_right='tag-text-outline')
            card_info.add_widget(self.field_name)
            self.field_reference = SmartTextField(text=val_reference, hint_text='Référence (Description)', icon_right='text')
            card_info.add_widget(self.field_reference)
            card_info.add_widget(MDLabel(text='Famille:', font_style='Caption', theme_text_color='Secondary'))
            self.btn_select_family = MDFlatButton(text=val_family, theme_text_color='Custom', text_color=(0.1, 0.1, 0.1, 1), size_hint_x=1, on_release=lambda x: self.open_family_selector_dialog())
            fam_box = MDCard(size_hint_y=None, height=dp(40), radius=[4], md_bg_color=(0.95, 0.95, 0.95, 1), elevation=0)
            fam_box.add_widget(self.btn_select_family)
            card_info.add_widget(fam_box)
            if current_image:
                img_status = 'Image disponible (PC)'
                img_color = (0, 0.6, 0, 1)
            else:
                img_status = 'Aucune image'
                img_color = (0.5, 0.5, 0.5, 1)
            box_img = MDBoxLayout(orientation='horizontal', spacing=dp(10), adaptive_height=True, padding=[0, dp(10), 0, 0])
            box_img.add_widget(MDIcon(icon='image', theme_text_color='Custom', text_color=img_color))
            box_img.add_widget(MDLabel(text=img_status, font_style='Caption', theme_text_color='Custom', text_color=img_color))
            card_info.add_widget(box_img)
            main_box.add_widget(card_info)
            card_stock = MDCard(orientation='vertical', radius=[12], padding=dp(15), spacing=dp(10), elevation=1, adaptive_height=True)
            row_stock = MDBoxLayout(orientation='horizontal', spacing=dp(15), adaptive_height=True)
            self.chk_unlimited = MDCheckbox(active=is_unlimited, size_hint=(None, None), size=(dp(40), dp(40)), disabled=has_movements)
            row_stock.add_widget(self.chk_unlimited)
            row_stock.add_widget(MDLabel(text='Illimité'))
            self.field_stock = MDTextField(text=val_stock, hint_text='Quantité', input_filter='float', size_hint_x=0.5)

            def on_chk(chk, val):
                self.field_stock.disabled = val or has_movements
            self.chk_unlimited.bind(active=on_chk)
            on_chk(None, is_unlimited)
            row_stock.add_widget(self.field_stock)
            if has_movements:
                card_stock.add_widget(MDLabel(text='* Quantité verrouillée (Produit utilisé)', theme_text_color='Error', font_style='Caption'))
            card_stock.add_widget(row_stock)
            main_box.add_widget(card_stock)
            card_price = MDCard(orientation='vertical', radius=[12], padding=dp(15), spacing=dp(10), elevation=1, adaptive_height=True)
            self.field_cost = MDTextField(text=val_cost, hint_text='Prix Achat', input_filter='float')
            self.field_p1 = MDTextField(text=val_p1, hint_text='Prix Détail', input_filter='float')
            self.field_p2 = MDTextField(text=val_p2, hint_text='Prix Demi-Gros', input_filter='float')
            self.field_p3 = MDTextField(text=val_p3, hint_text='Prix Gros', input_filter='float')
            card_price.add_widget(self.field_cost)
            card_price.add_widget(self.field_p1)
            card_price.add_widget(self.field_p2)
            card_price.add_widget(self.field_p3)
            main_box.add_widget(card_price)

            def save_product_action(x):
                name_val = self.field_name.get_value().strip()
                if not name_val:
                    return

                def sf(tf):
                    try:
                        return float(str(tf.text).replace(',', '.') or 0)
                    except:
                        return 0.0
                if has_movements:
                    stock_val = raw_stock
                else:
                    stock_val = -1000000.0 if self.chk_unlimited.active else sf(self.field_stock)
                fam_val = self.btn_select_family.text
                if fam_val == '(Aucune)' or fam_val == 'Tout':
                    fam_val = ''
                payload = {'action': 'update' if is_edit else 'add', 'id': product['id'] if is_edit else None, 'name': name_val, 'barcode': self.field_bar.text.strip(), 'description': self.field_reference.get_value().strip(), 'product_ref': self.field_num.text.strip(), 'category': fam_val, 'stock': stock_val, 'cost': sf(self.field_cost), 'price': sf(self.field_p1), 'price_semi': sf(self.field_p2), 'price_wholesale': sf(self.field_p3), 'image_path': current_image, 'user_name': self.current_user_name, 'unit': product.get('unit', '') if is_edit else '', 'tva': float(product.get('tva', 0) or 0) if is_edit else 0}
                endpoint = '/api/update_product' if is_edit else '/api/add_product'
                UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}{endpoint}', req_body=json.dumps(payload), req_headers={'Content-Type': 'application/json'}, method='POST', on_success=lambda r, s: [self.dialog.dismiss(), self.fetch_products(), self.notify('Succès', 'success')], on_failure=lambda r, e: self.notify('Erreur serveur', 'error'))
            footer = MDBoxLayout(orientation='vertical', spacing=dp(10), adaptive_height=True, padding=[0, dp(20), 0, 0])
            footer.add_widget(MDRaisedButton(text='ENREGISTRER', md_bg_color=(0, 0.7, 0, 1), size_hint_x=1, on_release=save_product_action))
            footer.add_widget(MDRaisedButton(text='FERMER', md_bg_color=(0.9, 0.9, 0.9, 1), text_color=(0.2, 0.2, 0.2, 1), size_hint_x=1, on_release=lambda x: self.dialog.dismiss()))
            main_box.add_widget(footer)
            scroll.add_widget(main_box)
            self.dialog = MDDialog(title=title, type='custom', content_cls=scroll, size_hint=(0.95, 0.9))
            self.dialog.open()
        except Exception as e:
            self.notify(f'Erreur UI: {e}', 'error')

    def add_to_cart(self, product):
        try:
            if hasattr(self.qty_field, 'get_value'):
                qty = float(self.qty_field.get_value())
            else:
                qty = float(self.qty_field.text)
            if qty <= 0:
                raise ValueError
        except:
            self.notify('Quantité invalide', 'error')
            return
        is_sale_context = self.current_mode in ['sale', 'return_sale', 'invoice_sale', 'proforma']
        original_unit_price = 0.0
        try:
            if is_sale_context:
                if product.get('has_promo', False):
                    original_unit_price = float(product.get('price', 0))
                else:
                    curr_price = float(product.get('price', 0))
                    if self.selected_entity:
                        cat = str(self.selected_entity.get('category', ''))
                        if cat in ['Gros', 'جملة']:
                            curr_price = float(product.get('price_wholesale', 0) or 0)
                        elif cat in ['Demi-Gros', 'نصف جملة']:
                            curr_price = float(product.get('price_semi', 0) or 0)
                        if curr_price == 0:
                            curr_price = float(product.get('price', 0))
                    original_unit_price = curr_price
            else:
                original_unit_price = float(product.get('purchase_price', product.get('price', 0)) or 0)
        except:
            original_unit_price = 0.0
        final_price = original_unit_price
        specials = product.get('special_prices', [])
        if is_sale_context and specials and (not product.get('has_promo', False)):
            specials.sort(key=lambda x: x['qty'], reverse=True)
            for sp in specials:
                if qty >= sp['qty']:
                    if sp['type'] == 'TOTAL':
                        final_price = float(sp['price']) / qty
                    else:
                        final_price = float(sp['price'])
                    break
        if product.get('name') == 'Autre Article':
            count = sum((1 for item in self.cart if str(item.get('name')).startswith('Autre Article')))
            new_name = f'Autre Article {count + 1}'
            self.cart.append({'id': product['id'], 'name': new_name, 'price': final_price, 'qty': qty, 'original_unit_price': final_price})
            if hasattr(self, 'dialog') and self.dialog:
                self.dialog.dismiss()
            self.update_cart_button()
            self.notify(f'Ajouté: {new_name}', 'success')
            if hasattr(self, 'search_field') and self.search_field:
                self.search_field.text = ''
                self.filter_products(None, '')
                Clock.schedule_once(lambda x: setattr(self.search_field, 'focus', True), 0.2)
            return
        found = False
        for item in self.cart:
            if item['id'] == product['id']:
                new_total_qty = item['qty'] + qty
                item['qty'] = new_total_qty
                new_item_price = item.get('original_unit_price', final_price)
                if is_sale_context and specials and (not product.get('has_promo', False)):
                    for sp in specials:
                        if new_total_qty >= sp['qty']:
                            if sp['type'] == 'TOTAL':
                                new_item_price = float(sp['price']) / new_total_qty
                            else:
                                new_item_price = float(sp['price'])
                            break
                item['price'] = new_item_price
                found = True
                break
        if not found:
            self.cart.append({'id': product['id'], 'name': product['name'], 'price': final_price, 'qty': qty, 'original_unit_price': original_unit_price, 'special_prices': specials, 'has_promo': product.get('has_promo', False)})
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.dismiss()
        self.update_cart_button()
        self.notify('Ajouté au panier', 'success')
        if hasattr(self, 'search_field') and self.search_field:
            self.search_field.text = ''
            self.filter_products(None, '')
            Clock.schedule_once(lambda x: setattr(self.search_field, 'focus', True), 0.2)

    def update_cart_button(self):
        try:
            count = len(self.cart)
            is_invoice_mode = self.current_mode in ['invoice_sale', 'invoice_purchase', 'proforma']
            total = sum((float(item['price'] or 0) * float(item['qty'] or 0) * (1 + (float(item.get('tva', 0)) if is_invoice_mode else 0) / 100) for item in self.cart))
            if self.lbl_cart_count:
                self.lbl_cart_count.text = f'PANIER ({count})'
            if self.current_mode == 'transfer':
                if self.lbl_cart_total:
                    self.lbl_cart_total.text = ''
            elif self.lbl_cart_total:
                self.lbl_cart_total.text = f'{total:.2f} DA'
        except:
            pass

    def remove_from_cart(self, item):
        if item in self.cart:
            self.cart.remove(item)
        self.refresh_cart_screen_items()
        self.update_cart_button()

    def start_payment_flow(self, mode):
        self.current_mode = mode
        entity_type = 'account' if mode == 'client_payment' else 'supplier'
        self.theme_cls.primary_palette = 'Teal' if mode == 'client_payment' else 'Brown'
        if self.is_server_reachable:
            self.fetch_entities(entity_type)
        else:
            key = 'clients' if entity_type == 'account' else 'suppliers'
            if self.cache_store.exists(key):
                if entity_type == 'account':
                    self.all_clients = self.cache_store.get('clients')['data']
                else:
                    self.all_suppliers = self.cache_store.get(key)['data']
        self.show_entity_selection_dialog(None, next_action=self.show_simple_payment_dialog)

    def show_simple_payment_dialog(self, amount=None):
        if not self.selected_entity:
            return
        self.temp_note = ''
        if self.current_mode == 'client_payment':
            title = 'Versement Client'
            theme_col = (0, 0.6, 0, 1)
        else:
            title = 'Règlement Fournisseur'
            theme_col = (0.8, 0.4, 0, 1)
        content = MDBoxLayout(orientation='vertical', spacing='12dp', size_hint_y=None, height=dp(560), padding=[0, '10dp', 0, 0])
        header_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=[0, 0, 0, '5dp'])
        ent_name = self.fix_text(self.selected_entity['name'])
        header_box.add_widget(MDLabel(text=ent_name, halign='center', font_style='H5', bold=True, theme_text_color='Primary', shorten=True, shorten_from='right'))
        content.add_widget(header_box)

        def backspace(x=None):
            current = self.txt_simple_amount.text
            if current:
                self.txt_simple_amount.text = current[:-1]
            if not self.txt_simple_amount.text:
                self.txt_simple_amount.text = ''

        def add_digit(digit):
            current = self.txt_simple_amount.text
            if digit == '.':
                if '.' in current:
                    return
                if not current:
                    self.txt_simple_amount.text = '0.'
                else:
                    self.txt_simple_amount.text = current + '.'
            elif digit == '-':
                if current.startswith('-'):
                    self.txt_simple_amount.text = current[1:]
                else:
                    self.txt_simple_amount.text = '-' + current
            elif current == '0':
                self.txt_simple_amount.text = str(digit)
            elif current == '-0':
                self.txt_simple_amount.text = '-' + str(digit)
            else:
                self.txt_simple_amount.text = current + str(digit)
        input_row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(110), spacing='10dp', padding=[dp(20), 0])
        val = ''
        if amount:
            try:
                f_val = float(amount)
                if f_val.is_integer():
                    val = str(int(f_val))
                else:
                    val = str(f_val)
            except:
                val = str(amount)
        self.txt_simple_amount = MDTextField(text=val, hint_text='Montant (DA)', font_size='45sp', halign='center', readonly=True, mode='fill', line_color_focus=theme_col, size_hint_x=0.7)
        self.txt_simple_amount.get_value = lambda: self.txt_simple_amount.text
        self.btn_note_icon = MDIconButton(icon='note-edit-outline', theme_text_color='Custom', text_color=(1, 1, 1, 1), md_bg_color=(0.2, 0.2, 0.2, 1), size_hint=(None, None), size=(dp(55), dp(55)), pos_hint={'center_y': 0.5}, on_release=self.open_note_input)
        btn_del = MDIconButton(icon='backspace-outline', theme_text_color='Custom', text_color=(1, 1, 1, 1), md_bg_color=(0.9, 0.1, 0.1, 1), size_hint=(None, None), size=(dp(55), dp(55)), pos_hint={'center_y': 0.5}, on_release=backspace)
        input_row.add_widget(self.txt_simple_amount)
        if not self.editing_transaction_key:
            input_row.add_widget(self.btn_note_icon)
        input_row.add_widget(btn_del)
        content.add_widget(input_row)
        grid = MDGridLayout(cols=3, spacing='10dp', size_hint_y=1, padding=[dp(20), dp(10)])
        keys = ['7', '8', '9', '4', '5', '6', '1', '2', '3', '-', '0', '.']
        for key in keys:
            btn = MDRaisedButton(text=key, md_bg_color=(0.96, 0.96, 0.96, 1), theme_text_color='Custom', text_color=(0.1, 0.1, 0.1, 1), font_size='28sp', elevation=1, size_hint=(1, 1), on_release=lambda x, k=key: add_digit(k))
            if key == '-':
                btn.font_size = '38sp'
                btn.text_color = (0, 0, 0, 1)
            grid.add_widget(btn)
        content.add_widget(grid)
        buttons_box = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='70dp', padding=[0, '10dp', 0, 0])
        btn_cancel = MDFlatButton(text='ANNULER', theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1), size_hint_x=0.25, on_release=lambda x: self.simple_pay_dialog.dismiss())
        btn_valid = MDRaisedButton(text='VALIDER', md_bg_color=theme_col, text_color=(1, 1, 1, 1), size_hint_x=0.75, size_hint_y=1, font_size='22sp', elevation=3, on_release=self.submit_simple_payment)
        buttons_box.add_widget(btn_cancel)
        buttons_box.add_widget(btn_valid)
        content.add_widget(buttons_box)
        self.simple_pay_dialog = MDDialog(title=title, type='custom', content_cls=content, size_hint=(0.92, None), buttons=[])
        self.simple_pay_dialog.open()

    def open_note_input(self, instance):
        content = MDBoxLayout(orientation='vertical', spacing='10dp', size_hint_y=None, height=dp(100), padding=dp(10))
        note_field = SmartTextField(text=self.temp_note, hint_text='Entrez une note (Optionnel)')
        content.add_widget(note_field)

        def save_note(x):
            self.temp_note = note_field.get_value().strip()
            if self.temp_note:
                self.btn_note_icon.md_bg_color = (0, 0.6, 0, 1)
            else:
                self.btn_note_icon.md_bg_color = (0.2, 0.2, 0.2, 1)
            note_dialog.dismiss()
        note_dialog = MDDialog(title='Ajouter une note', type='custom', content_cls=content, buttons=[MDFlatButton(text='ANNULER', on_release=lambda x: note_dialog.dismiss()), MDRaisedButton(text='OK', on_release=save_note)])
        note_dialog.open()

    def save_to_history(self, data, synced=False):
        if not synced:
            self.notify('Sauvegarde locale...', 'warning')
        key_name = None
        if self.editing_transaction_key:
            if self.editing_transaction_key != 'SERVER_EDIT_MODE':
                key_name = self.editing_transaction_key
                try:
                    if self.offline_store.exists(key_name):
                        old_item = self.offline_store.get(key_name)
                        old_data = old_item.get('order_data', {})
                        if old_data.get('entity_id'):
                            reversal_amount = 0
                            if old_data.get('is_simple_payment'):
                                reversal_amount = float(old_data.get('amount', 0))
                            else:
                                pass
                            if reversal_amount != 0:
                                self.update_local_entity_balance(old_data['entity_id'], -reversal_amount)
                except Exception as e:
                    print(f'History update error: {e}')
        if not key_name:
            timestamp_sec = int(time.time())
            unique_id = random.randint(1000, 9999)
            if data.get('is_simple_payment'):
                key_name = f'{timestamp_sec}_{unique_id}_PAY'
            else:
                doc_type = data.get('doc_type', 'BV')
                key_name = f'{timestamp_sec}_{unique_id}_{doc_type}'
        self.offline_store.put(key_name, order_data=data, synced=synced, sync_timestamp=time.time() if synced else 0)
        self.editing_transaction_key = None
        if not synced:
            try:
                if data.get('is_simple_payment') and data.get('entity_id'):
                    pass
            except:
                pass
            self._reset_notification_state(0)
            if self.pending_dialog:
                target_date = getattr(self, 'history_view_date', datetime.now().date())
                self.filter_history_list(specific_date=target_date)

    def toggle_location(self, x=None):
        mode = getattr(self, 'user_sales_mode', 'store')
        if mode == 'truck':
            self.notify('Mode VAN : Emplacement fixe', 'info')
            return
        self.selected_location = 'warehouse' if self.selected_location == 'store' else 'store'
        self.update_location_display()
        if self.current_mode == 'transfer' and hasattr(self, 'btn_ent_screen'):
            src = 'Magasin' if self.selected_location == 'store' else 'Dépôt'
            dst = 'Dépôt' if self.selected_location == 'store' else 'Magasin'
            self.btn_ent_screen.text = f'{src}  >>>  {dst}'

    def update_location_display(self):
        if hasattr(self, 'btn_loc_screen'):
            mode = getattr(self, 'user_sales_mode', None)
            if not mode and self.store.exists('credentials'):
                mode = self.store.get('credentials').get('sales_mode', 'store')
            if not mode:
                mode = 'store'
            if mode == 'truck':
                self.btn_loc_screen.text = 'VAN'
                self.btn_loc_screen.icon = 'truck'
                self.btn_loc_screen.md_bg_color = (0.6, 0.4, 0.2, 1)
                self.selected_location = 'store'
            elif self.selected_location == 'store':
                self.btn_loc_screen.text = 'MAGASIN'
                self.btn_loc_screen.icon = 'store'
                self.btn_loc_screen.md_bg_color = self.theme_cls.primary_color
            else:
                self.btn_loc_screen.text = 'DEPOT'
                self.btn_loc_screen.icon = 'warehouse'
                self.btn_loc_screen.md_bg_color = (0.8, 0.4, 0, 1)

    def show_entity_selection_dialog(self, x, next_action=None):
        self.pending_entity_next_action = next_action
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(600))
        self.entity_search = SmartTextField(hint_text='Rechercher...', icon_right='magnify')
        self.entity_search.bind(text=self.filter_entities)
        content.add_widget(self.entity_search)
        self.rv_entity = EntityRecycleView()
        content.add_widget(self.rv_entity)
        if self.current_mode in ['sale', 'return_sale', 'client_payment', 'invoice_sale', 'proforma']:
            self.entities_source = self.all_clients
            title_text = 'Choisir un Client'
        else:
            self.entities_source = self.all_suppliers
            title_text = 'Choisir un Fournisseur'
        self.populate_entity_list(self.entities_source)
        self.entity_dialog = MDDialog(title=title_text, type='custom', content_cls=content, size_hint=(0.9, 0.8))
        self.entity_dialog.open()

    def recalculate_cart_prices(self):
        if not self.cart or not self.selected_entity:
            return
        cat = str(self.selected_entity.get('category', ''))
        price_key = 'price'
        if cat in ['Gros', 'جملة']:
            price_key = 'price_wholesale'
        elif cat in ['Demi-Gros', 'نصف جملة']:
            price_key = 'price_semi'
        for item in self.cart:
            original_product = next((p for p in self.all_products_raw if p['id'] == item['id']), None)
            if original_product:
                new_price = float(original_product.get(price_key, 0))
                if new_price == 0:
                    new_price = float(original_product.get('price', 0))
                item['price'] = new_price
        self.update_cart_button()
        self.notify('Prix mis à jour selon le client', 'info')

    def _calculate_stamp_duty(self, amount):
        try:
            val = float(amount)
        except (ValueError, TypeError):
            return 0.0
        if val <= 300:
            return 0.0
        units = math.ceil(val / 100.0)
        if val <= 30000:
            duty = units * 1.0
        elif val <= 100000:
            duty = units * 1.5
        else:
            duty = units * 2.0
        final_duty = math.ceil(duty)
        return float(max(5.0, final_duty))

    def open_payment_dialog(self, x):
        current_time = time.time()
        if current_time - getattr(self, '_last_click_time', 0) < 1.0:
            return
        self._last_click_time = current_time
        if getattr(self, 'is_transaction_in_progress', False):
            return
        if not self.cart:
            self.dialog = MDDialog(title='Attention', text='Le panier est vide !', buttons=[MDFlatButton(text='OK', on_release=lambda x: self.dialog.dismiss())])
            self.dialog.open()
            return
        self.is_invoice_sale = self.current_mode == 'invoice_sale'
        is_invoice_mode = self.current_mode in ['invoice_sale', 'invoice_purchase', 'proforma']
        total_ht, total_tva = self.calculate_cart_totals(self.cart, is_invoice_mode)
        self.temp_total_ht = total_ht
        self.temp_total_tva = total_tva
        base_ttc = self._round_num(total_ht + total_tva)
        if self.current_mode in ['return_sale', 'return_purchase']:
            self.process_transaction(paid_amount=0.0, total_amount=base_ttc, method='')
            return
        is_zero_pay_mode = self.current_mode in ['transfer', 'proforma', 'order_purchase']
        server_default_names = ['COMPTOIR', 'Comptoir', 'زبون افتراضي', 'مورد افتراضي', 'DEFAULT_CUSTOMER', 'DEFAULT_SUPPLIER']
        ent_name = str(self.selected_entity.get('name', '')).strip() if self.selected_entity else ''
        is_comptoir_entity = ent_name in server_default_names or not self.selected_entity or ent_name == ''
        should_skip_dialog = False
        if is_zero_pay_mode:
            should_skip_dialog = True
        elif is_comptoir_entity:
            should_skip_dialog = True
        if should_skip_dialog:
            final_paid_amount = 0.0
            method_val = ''
            if is_zero_pay_mode:
                final_paid_amount = 0.0
            else:
                timbre = 0.0
                if self.is_invoice_sale:
                    if is_comptoir_entity:
                        method_val = ''
                        timbre = 0.0
                    else:
                        method_val = 'Espèce'
                        timbre = self._calculate_stamp_duty(base_ttc)
                elif self.current_mode == 'sale':
                    method_val = 'Espèce'
                else:
                    method_val = 'Espèce'
                final_paid_amount = self._round_num(base_ttc + timbre)
                if self.current_mode in ['return_sale', 'return_purchase']:
                    final_paid_amount = base_ttc
            self.process_transaction(final_paid_amount, base_ttc, method=method_val)
            return
        self.show_details = is_invoice_mode
        if self.is_invoice_sale:
            self.payment_methods = [{'label': 'Par défaut', 'value': ''}, {'label': 'Espèce', 'value': 'دفع نقدًا'}, {'label': 'Chèque', 'value': 'صك بنكي'}, {'label': 'Virement', 'value': 'تحويل بنكي'}, {'label': 'Versement', 'value': 'إيداع'}]
            self.current_method_index = 0
            if hasattr(self, 'editing_payment_method') and self.editing_payment_method:
                for idx, m in enumerate(self.payment_methods):
                    if m['value'] == self.editing_payment_method:
                        self.current_method_index = idx
                        break
        dialog_height = dp(640) if self.show_details else dp(580)
        content = MDBoxLayout(orientation='vertical', spacing='10dp', size_hint_y=None, height=dialog_height, padding=['10dp', '0dp', '10dp', '20dp'])
        header_box = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        lbl_title = MDLabel(text='Paiement', font_style='H5', bold=True, theme_text_color='Primary', valign='center')
        header_box.add_widget(lbl_title)
        if self.is_invoice_sale:
            self.btn_payment_method = MDRaisedButton(text=self.payment_methods[self.current_method_index]['label'], md_bg_color=(0.2, 0.2, 0.2, 1), elevation=2, pos_hint={'center_y': 0.5}, on_release=self._cycle_payment_method)
            header_box.add_widget(self.btn_payment_method)
        content.add_widget(header_box)
        card_height = dp(125) if self.show_details else dp(90)
        total_card = MDCard(orientation='vertical', size_hint_y=None, height=card_height, radius=[10], md_bg_color=(0.95, 0.95, 0.95, 1), elevation=1, padding='5dp')
        if self.show_details:
            details_box = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(25), padding=[dp(5), 0], spacing=dp(5))
            lbl_ht = MDLabel(text=f'HT: {self.temp_total_ht:.2f} DA', theme_text_color='Secondary', font_style='Caption', halign='left', bold=True, size_hint_x=0.33)
            details_box.add_widget(lbl_ht)
            self.lbl_timbre = MDLabel(text='', theme_text_color='Custom', text_color=(0.5, 0, 0.5, 1), font_style='Caption', halign='center', bold=True, size_hint_x=0.33)
            details_box.add_widget(self.lbl_timbre)
            lbl_tva = MDLabel(text=f'TVA: {self.temp_total_tva:.2f} DA', theme_text_color='Custom', text_color=(0.8, 0, 0, 1), font_style='Caption', halign='right', bold=True, size_hint_x=0.33)
            details_box.add_widget(lbl_tva)
            total_card.add_widget(details_box)
        else:
            self.lbl_timbre = MDLabel()
        total_box = MDBoxLayout(orientation='vertical', spacing=0)
        total_lbl_title = MDLabel(text='NET À PAYER', halign='center', font_style='Caption', theme_text_color='Secondary', size_hint_y=None, height=dp(20))
        self.lbl_final_total = MDLabel(text='', halign='center', font_style='H4', bold=True, theme_text_color='Primary')
        total_box.add_widget(total_lbl_title)
        total_box.add_widget(self.lbl_final_total)
        total_card.add_widget(total_box)
        content.add_widget(total_card)
        try:
            default_val = f'{float(self.editing_payment_amount or 0):.2f}'
        except:
            default_val = '0.00'
        self.txt_paid = MDTextField(text=default_val, hint_text='Montant Versé (DA)', font_size='40sp', halign='center', readonly=True, size_hint_y=None, height=dp(80), mode='fill', line_color_focus=(0, 0, 0, 0))
        self.txt_paid.get_value = lambda: self.txt_paid.text
        content.add_widget(self.txt_paid)
        self.lbl_rest = MDLabel(text='', halign='center', theme_text_color='Custom', font_style='H6', bold=True, size_hint_y=None, height=dp(30))
        content.add_widget(self.lbl_rest)
        grid = MDGridLayout(cols=3, spacing='10dp', size_hint_y=1)
        keys = ['7', '8', '9', '4', '5', '6', '1', '2', '3', '.', '0', 'DEL']

        def add_digit(digit):
            current = self.txt_paid.text
            if digit == '.':
                if '.' in current:
                    return
                if not current:
                    self.txt_paid.text = '0.'
                else:
                    self.txt_paid.text = current + '.'
            elif current == '0' or current == '0.00':
                self.txt_paid.text = str(digit)
            else:
                self.txt_paid.text = current + str(digit)
            self._recalc_ui_totals()

        def backspace(instance=None):
            current = self.txt_paid.text
            if len(current) > 0:
                self.txt_paid.text = current[:-1]
            if not self.txt_paid.text:
                self.txt_paid.text = '0'
            self._recalc_ui_totals()
        for key in keys:
            if key == 'DEL':
                btn = MDIconButton(icon='backspace', theme_text_color='Custom', text_color=(1, 1, 1, 1), md_bg_color=(0.4, 0.4, 0.4, 1), size_hint=(1, 1), icon_size='24sp', on_release=backspace)
            else:
                btn = MDRaisedButton(text=key, md_bg_color=(1, 1, 1, 1), theme_text_color='Custom', text_color=(0, 0, 0, 1), font_size='24sp', size_hint=(1, 1), elevation=1, on_release=lambda x, k=key: add_digit(k))
            grid.add_widget(btn)
        content.add_widget(grid)
        content.add_widget(MDBoxLayout(size_hint_y=None, height='15dp'))
        buttons_box = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='55dp')
        btn_cancel = MDFlatButton(text='ANNULER', theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1), size_hint_x=0.3, on_release=lambda x: self.pay_dialog.dismiss())
        btn_valid = MDRaisedButton(text='VALIDER', md_bg_color=(0, 0.7, 0, 1), text_color=(1, 1, 1, 1), size_hint_x=0.7, size_hint_y=1, font_size='20sp', elevation=2, on_release=lambda x: self.finalize_submission(self.current_final_total))
        buttons_box.add_widget(btn_cancel)
        buttons_box.add_widget(btn_valid)
        content.add_widget(buttons_box)
        self.pay_dialog = MDDialog(title='', type='custom', content_cls=content, buttons=[], size_hint=(0.94, 0.98))
        self._recalc_ui_totals()
        self.pay_dialog.open()

    def _recalc_ui_totals(self):
        base_ttc = self._round_num(self.temp_total_ht + self.temp_total_tva)
        timbre = 0.0
        if hasattr(self, 'is_invoice_sale') and self.is_invoice_sale:
            if hasattr(self, 'payment_methods') and self.payment_methods:
                idx = getattr(self, 'current_method_index', 0)
                if idx < len(self.payment_methods):
                    selected_val = self.payment_methods[idx]['value']
                    if selected_val in ['دفع نقدًا', 'Espèce']:
                        timbre = self._calculate_stamp_duty(base_ttc)
                        self.lbl_timbre.text = f'Timbre: {timbre:.2f} DA'
                        self.lbl_timbre.opacity = 1
                    else:
                        self.lbl_timbre.text = ''
                        self.lbl_timbre.opacity = 0
                else:
                    self.lbl_timbre.opacity = 0
        else:
            self.lbl_timbre.text = ''
            self.lbl_timbre.opacity = 0
        self.current_final_total = self._round_num(base_ttc + timbre)
        self.lbl_final_total.text = f'{self.current_final_total:.2f} DA'
        try:
            paid = float(self.txt_paid.text or 0)
        except:
            paid = 0.0
        diff = self._round_num(self.current_final_total - paid)
        if diff >= 0:
            self.lbl_rest.text = f'RESTE: {diff:.2f} DA'
            self.lbl_rest.text_color = (0.8, 0, 0, 1)
        else:
            self.lbl_rest.text = f'RENDU: {abs(diff):.2f} DA'
            self.lbl_rest.text_color = (0, 0.6, 0, 1)

    def finalize_submission(self, total_amount):
        current_time = time.time()
        if current_time - getattr(self, '_last_click_time', 0) < 1.0:
            return
        self._last_click_time = current_time
        if getattr(self, 'is_transaction_in_progress', False):
            return
        if self.pay_dialog:
            self.pay_dialog.dismiss()
        payment_method = ''
        if self.current_mode == 'invoice_sale':
            if hasattr(self, 'payment_methods') and hasattr(self, 'current_method_index'):
                try:
                    payment_method = self.payment_methods[self.current_method_index]['value']
                except:
                    payment_method = ''
        else:
            payment_method = ''
        if self.current_mode == 'transfer':
            paid_amount = 0
        else:
            try:
                paid_amount = float(self.txt_paid.get_value()) if self.txt_paid.get_value() else 0
            except:
                paid_amount = 0
            if paid_amount < total_amount:
                remaining = total_amount - paid_amount
                self.show_credit_warning(paid_amount, total_amount, remaining)
                return
            if paid_amount > total_amount and self.current_mode not in ['return_sale', 'return_purchase']:
                excess = paid_amount - total_amount
                self.show_overpayment_dialog(paid_amount, total_amount, excess)
                return
        Clock.schedule_once(lambda dt: self.process_transaction(paid_amount, total_amount, method=payment_method), 0.1)

    def _cycle_payment_method(self, instance):
        self.current_method_index = (self.current_method_index + 1) % len(self.payment_methods)
        new_label = self.payment_methods[self.current_method_index]['label']
        self.btn_payment_method.text = new_label
        self._recalc_ui_totals()

    def show_overpayment_dialog(self, paid, total, excess):
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, adaptive_height=True, spacing='15dp', padding=[0, '10dp', 0, 0])
        lbl_info = MDLabel(text=f'[b]Montant saisi:[/b] {paid:.2f} DA\n[b]Total:[/b] {total:.2f} DA', markup=True, halign='center', theme_text_color='Primary', font_style='Body1', size_hint_y=None, adaptive_height=True)
        content.add_widget(lbl_info)
        msg_text = ''
        if self.current_mode in ['return_sale', 'return_purchase']:
            msg_text = f"L'excédent [color=#00C853][b]({excess:.2f} DA)[/b][/color] sera déduit du solde."
        else:
            msg_text = f"L'excédent [color=#00C853][b]({excess:.2f} DA)[/b][/color] sera enregistré comme une opération séparée [b](VERSEMENT/RÈGLEMENT)[/b]."
        lbl_msg = MDLabel(text=msg_text, markup=True, halign='center', theme_text_color='Primary', font_style='Subtitle1', size_hint_y=None, adaptive_height=True)
        content.add_widget(lbl_msg)
        buttons = [MDFlatButton(text='CORRIGER', theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1), on_release=lambda x: [self.overpay_dialog.dismiss(), self.open_payment_dialog(None)]), MDRaisedButton(text='CONFIRMER', md_bg_color=(0, 0.7, 0, 1), text_color=(1, 1, 1, 1), elevation=2, on_release=lambda x: [self.overpay_dialog.dismiss(), self.process_transaction(paid, total)])]
        self.overpay_dialog = MDDialog(title="Création d'un Versement", type='custom', content_cls=content, buttons=buttons)
        self.overpay_dialog.open()

    def show_credit_warning(self, paid, total, remaining):
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, adaptive_height=True, spacing='15dp', padding=[0, '10dp', 0, 0])
        lbl_info = MDLabel(text=f'[b]Montant saisi:[/b] {paid:.2f} DA\n[b]Total:[/b] {total:.2f} DA', markup=True, halign='center', theme_text_color='Primary', font_style='Body1', size_hint_y=None, adaptive_height=True)
        content.add_widget(lbl_info)
        msg_text = ''
        if self.current_mode in ['return_sale', 'return_purchase']:
            msg_text = f'Vous rendez [b]{paid:.2f} DA[/b].\nLe reste [color=#D32F2F][b]({remaining:.2f} DA)[/b][/color] sera déduit de la dette du tiers.'
        else:
            msg_text = f'Le montant versé est insuffisant.\nLe reste [color=#D32F2F][b]({remaining:.2f} DA)[/b][/color] sera enregistré comme [b]CRÉDIT [/b].'
        lbl_msg = MDLabel(text=msg_text, markup=True, halign='center', theme_text_color='Primary', font_style='Subtitle1', size_hint_y=None, adaptive_height=True)
        content.add_widget(lbl_msg)
        buttons = [MDFlatButton(text='ANNULER', theme_text_color='Custom', text_color=(0.5, 0.5, 0.5, 1), on_release=lambda x: self.debt_dialog.dismiss()), MDRaisedButton(text='CONFIRMER', md_bg_color=(0.8, 0, 0, 1), text_color=(1, 1, 1, 1), elevation=2, on_release=lambda x: [self.debt_dialog.dismiss(), self.process_transaction(paid, total)])]
        self.debt_dialog = MDDialog(title='Attention: Crédit', type='custom', content_cls=content, buttons=buttons)
        self.debt_dialog.open()

    def process_transaction(self, paid_amount, total_amount, method=None):
        if getattr(self, 'is_transaction_in_progress', False):
            return
        self.is_transaction_in_progress = True
        try:
            doc_type_map = {'sale': 'BV', 'purchase': 'BA', 'return_sale': 'RC', 'return_purchase': 'RF', 'transfer': 'TR', 'invoice_sale': 'FC', 'invoice_purchase': 'FF', 'proforma': 'FP', 'order_purchase': 'DP'}
            doc_type = doc_type_map.get(self.current_mode, 'BV')
            if hasattr(self, 'original_doc_type') and self.original_doc_type == 'BI' and (self.current_mode == 'purchase'):
                doc_type = 'BI'
            is_invoice_mode = doc_type in ['FC', 'FF', 'FP']
            calc_ht, calc_tva = self.calculate_cart_totals(self.cart, is_invoice_mode)
            base_ttc = self._round_num(calc_ht + calc_tva)
            server_default_names = ['COMPTOIR', 'Comptoir', 'زبون افتراضي', 'مورد افتراضي', 'DEFAULT_CUSTOMER', 'DEFAULT_SUPPLIER']
            ent_name = str(self.selected_entity.get('name', '')).strip() if self.selected_entity else ''
            is_comptoir_entity = ent_name in server_default_names or not self.selected_entity or ent_name == ''
            timbre_amount = 0.0
            method_val = method
            if doc_type == 'FC' and is_comptoir_entity:
                method_val = ''
                timbre_amount = 0.0
            elif doc_type == 'FC':
                if not method_val and hasattr(self, 'payment_methods') and hasattr(self, 'current_method_index'):
                    try:
                        method_val = self.payment_methods[self.current_method_index]['value']
                    except:
                        method_val = ''
                if method_val in ['دفع نقدًا', 'Espèce']:
                    timbre_amount = self._calculate_stamp_duty(base_ttc)
            if not method_val:
                method_val = ''
            real_total_to_send = self._round_num(base_ttc + timbre_amount)
            excess_amount = 0.0
            invoice_paid_amount = paid_amount
            is_real_transaction = self.current_mode not in ['proforma', 'order_purchase', 'transfer']
            if is_real_transaction and self.current_mode in ['sale', 'purchase', 'invoice_sale', 'invoice_purchase']:
                if paid_amount > real_total_to_send:
                    excess_amount = self._round_num(paid_amount - real_total_to_send)
                    invoice_paid_amount = real_total_to_send
                else:
                    invoice_paid_amount = paid_amount
            if is_real_transaction:
                full_payment = invoice_paid_amount + excess_amount
                if self.current_mode in ['sale', 'invoice_sale']:
                    self.stat_sales_today += full_payment
                elif self.current_mode in ['purchase', 'invoice_purchase']:
                    self.stat_purchases_today += full_payment
                self.calculate_net_total()
                self.save_local_stats()
            ent_id = self.selected_entity['id'] if self.selected_entity else None
            payment_info = {'amount': invoice_paid_amount, 'total': real_total_to_send, 'method': method_val, 'timbre': timbre_amount}
            excess_data = None
            if excess_amount > 0 and ent_id:
                p_type = 'supplier_pay' if 'purchase' in self.current_mode or 'supplier' in self.current_mode else 'client_pay'
                if p_type == 'supplier_pay':
                    custom_label = 'Réglement'
                else:
                    custom_label = 'Versement'
                excess_data = {'entity_id': ent_id, 'amount': excess_amount, 'type': p_type, 'custom_label': custom_label, 'user_name': self.current_user_name, 'note': custom_label, 'is_simple_payment': True, 'timestamp': str(datetime.now())}
            server_id_to_update = None
            if self.editing_transaction_key:
                if self.editing_transaction_key == 'SERVER_EDIT_MODE':
                    server_id_to_update = self.current_editing_server_id
                elif self.offline_store.exists(self.editing_transaction_key):
                    old_item = self.offline_store.get(self.editing_transaction_key)
                    if old_item.get('synced') and old_item.get('order_data', {}).get('server_id'):
                        server_id_to_update = old_item['order_data']['server_id']
            final_timestamp = str(datetime.now())
            if server_id_to_update and hasattr(self, 'current_editing_date') and self.current_editing_date:
                final_timestamp = self.current_editing_date
            try:
                if '.' in final_timestamp:
                    final_timestamp = final_timestamp.split('.')[0]
            except:
                pass
            data = {'doc_type': doc_type, 'items': self.cart, 'user_name': self.current_user_name, 'timestamp': final_timestamp, 'purchase_location': self.selected_location, 'entity_id': ent_id, 'payment_info': payment_info, 'server_id': server_id_to_update}
            self.current_editing_server_id = None
            self.editing_payment_amount = None
            self.current_editing_date = None
            if hasattr(self, 'original_doc_type'):
                del self.original_doc_type

            def finalize_process(req=None, res=None):
                self.is_transaction_in_progress = False
                try:
                    printable_modes = ['sale', 'purchase', 'return_sale', 'return_purchase', 'transfer']
                    if self.current_mode in printable_modes:
                        if self.store.exists('printer_config'):
                            conf = self.store.get('printer_config')
                            if conf.get('auto', False) and conf.get('mac', ''):
                                threading.Thread(target=self.print_ticket_bluetooth, args=(data,), daemon=True).start()
                except Exception as e:
                    print(f'Auto print error: {e}')
                msg = 'Succès ✅'
                if excess_amount > 0:
                    msg = 'Succès (Facture + Excédent) ✅'
                self.notify(msg, 'success')
                self.cart = []
                self.selected_entity = None
                self.selected_location = 'store'
                self.update_cart_button()
                self.go_back()

            def on_fail(req, err):
                self.is_transaction_in_progress = False
                self.save_to_history(data, synced=False)
                if excess_data:
                    self.save_to_history(excess_data, synced=False)
                    self.update_local_entity_balance(excess_data['entity_id'], excess_data['amount'])
                try:
                    doc_type_local = data.get('doc_type', 'BV')
                    if doc_type_local not in ['TR', 'FP', 'DP', 'BI'] and data.get('entity_id'):
                        is_invoice_doc = doc_type_local in ['FC', 'FF']
                        ht, tva = self.calculate_cart_totals(data.get('items', []), is_invoice_doc)
                        total_amount_loc = self._round_num(ht + tva)
                        if is_invoice_doc:
                            p_info = data.get('payment_info', {})
                            total_amount_loc = self._round_num(total_amount_loc + float(p_info.get('timbre', 0)))
                        balance_sign = 1
                        if doc_type_local in ['RC', 'RF']:
                            balance_sign = -1
                        payment_info_loc = data.get('payment_info', {})
                        paid_amount_loc = float(payment_info_loc.get('amount', 0))
                        net_change = self._round_num(total_amount_loc * balance_sign - paid_amount_loc)
                        self.update_local_entity_balance(data['entity_id'], net_change)
                except Exception as e:
                    print(f'Error calculating offline balance update: {e}')
                try:
                    printable_modes = ['sale', 'purchase', 'return_sale', 'return_purchase', 'transfer']
                    if self.current_mode in printable_modes:
                        if self.store.exists('printer_config'):
                            conf = self.store.get('printer_config')
                            if conf.get('auto', False) and conf.get('mac', ''):
                                threading.Thread(target=self.print_ticket_bluetooth, args=(data,), daemon=True).start()
                except:
                    pass
                self.cart = []
                self.selected_entity = None
                self.selected_location = 'store'
                self.update_cart_button()
                self.go_back()
            if self.is_server_reachable:

                def on_invoice_success(req, res):
                    if res.get('server_id'):
                        data['server_id'] = res.get('server_id')
                    if res.get('invoice_number'):
                        data['invoice_number'] = res.get('invoice_number')
                    self.save_to_history(data, synced=True)
                    if excess_data:

                        def on_excess_success(req2, res2):
                            if res2.get('server_id'):
                                excess_data['server_id'] = res2.get('server_id')
                            self.save_to_history(excess_data, synced=True)
                            type_refresh = 'supplier' if excess_data['type'] == 'supplier_pay' else 'account'
                            self.fetch_entities(type_refresh)
                            finalize_process()
                        UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/submit_payment', req_body=json.dumps(excess_data), req_headers={'Content-type': 'application/json'}, method='POST', on_success=on_excess_success, on_failure=lambda r, e: [self.save_to_history(excess_data, synced=False), finalize_process()], on_error=lambda r, e: [self.save_to_history(excess_data, synced=False), finalize_process()])
                    else:
                        finalize_process()
                UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/submit_order', req_body=json.dumps(data), req_headers={'Content-type': 'application/json'}, method='POST', on_success=on_invoice_success, on_error=on_fail, on_failure=on_fail, timeout=10)
            else:
                on_fail(None, None)
        except Exception as e:
            self.is_transaction_in_progress = False
            self.notify(f'Erreur fatale: {e}', 'error')

    def on_submit_success_ui(self):
        self.notify('Succès ✅', 'success')
        self.cart = []
        self.selected_entity = None
        self.selected_location = 'store'
        self.update_cart_button()
        self.go_back()

    def save_offline_and_ui(self, data):
        self.save_to_history(data, synced=False)
        try:
            printable_modes = ['sale', 'purchase', 'return_sale', 'return_purchase', 'transfer']
            if self.current_mode in printable_modes:
                if self.store.exists('printer_config'):
                    conf = self.store.get('printer_config')
                    if conf.get('auto', False) and conf.get('mac', ''):
                        threading.Thread(target=self.print_ticket_bluetooth, args=(data,), daemon=True).start()
        except Exception as e:
            print(f'Offline Print Error: {e}')
        try:
            doc_type = data.get('doc_type', 'BV')
            if doc_type not in ['TR', 'FP', 'DP', 'BI'] and data.get('entity_id'):
                is_invoice_doc = doc_type in ['FC', 'FF']
                ht, tva = self.calculate_cart_totals(data.get('items', []), is_invoice_doc)
                total_amount = self._round_num(ht + tva)
                if is_invoice_doc:
                    payment_info = data.get('payment_info', {})
                    total_amount = self._round_num(total_amount + float(payment_info.get('timbre', 0)))
                balance_sign = -1 if doc_type in ['RC', 'RF'] else 1
                payment_info = data.get('payment_info', {})
                paid_amount = float(payment_info.get('amount', 0))
                net_change = self._round_num(total_amount * balance_sign - paid_amount)
                self.update_local_entity_balance(data['entity_id'], net_change)
        except Exception as e:
            print(f'Error calculating offline balance update: {e}')
        self.cart = []
        self.selected_entity = None
        self.selected_location = 'store'
        self.update_cart_button()
        self.go_back()

    def show_pending_dialog(self):
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(550))
        tabs_box = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=5)
        self.btn_hist_today = MDRaisedButton(text='AUJ.', size_hint_x=0.33, elevation=0, on_release=lambda x: self.filter_history_list(day_offset=0))
        self.btn_hist_yesterday = MDRaisedButton(text='HIER', size_hint_x=0.33, elevation=0, md_bg_color=(0.5, 0.5, 0.5, 1), on_release=lambda x: self.filter_history_list(day_offset=1))
        self.btn_hist_date = MDRaisedButton(text='CALENDRIER', size_hint_x=0.33, elevation=0, md_bg_color=(0.5, 0.5, 0.5, 1), on_release=self.open_history_date_picker)
        tabs_box.add_widget(self.btn_hist_today)
        tabs_box.add_widget(self.btn_hist_yesterday)
        tabs_box.add_widget(self.btn_hist_date)
        content.add_widget(tabs_box)
        self.rv_history = HistoryRecycleView()
        content.add_widget(self.rv_history)
        self.pending_dialog = MDDialog(title='Historique', type='custom', content_cls=content, size_hint=(0.98, 0.98))
        self.pending_dialog.open()
        self.filter_history_list(day_offset=0)

    def filter_history_list(self, day_offset=None, specific_date=None):
        if not hasattr(self, 'btn_hist_today') or not self.btn_hist_today:
            if specific_date:
                self.history_view_date = specific_date
            return
        inactive_color = (0.5, 0.5, 0.5, 1)
        active_color = self.theme_cls.primary_color
        target_date = None
        if specific_date:
            target_date = specific_date
            self.btn_hist_today.md_bg_color = inactive_color
            self.btn_hist_yesterday.md_bg_color = inactive_color
            self.btn_hist_date.md_bg_color = active_color
        else:
            if day_offset is None:
                day_offset = 0
            target_date = datetime.now().date() - timedelta(days=day_offset)
            self.btn_hist_today.md_bg_color = active_color if day_offset == 0 else inactive_color
            self.btn_hist_yesterday.md_bg_color = active_color if day_offset == 1 else inactive_color
            self.btn_hist_date.md_bg_color = inactive_color
            self.btn_hist_date.text = 'CALENDRIER'
        self.history_view_date = target_date
        self.history_rv_data = []
        keys = list(self.offline_store.keys())
        local_items = []
        for k in keys:
            try:
                item_store = self.offline_store.get(k)
                if item_store.get('synced', False):
                    continue
                data = item_store.get('order_data', {})
                if self.is_seller_mode:
                    local_user = str(data.get('user_name', '')).strip()
                    if local_user != self.current_user_name:
                        continue
                parts = k.split('_')
                if parts[0].isdigit():
                    ts_val = int(parts[0])
                    item_date = datetime.fromtimestamp(ts_val).date()
                    if item_date == target_date:
                        local_items.append((ts_val, k, item_store))
            except:
                continue
        local_items.sort(key=lambda x: x[0], reverse=True)
        for ts_val, k, item_store in local_items:
            data = item_store['order_data']
            doc_type = data.get('doc_type', 'BV')
            is_simple_payment = data.get('is_simple_payment', False)
            dt_str = datetime.fromtimestamp(ts_val).strftime('%H:%M')
            entity_name = 'Inconnu'
            ent_id = data.get('entity_id')
            if doc_type == 'TR':
                loc = data.get('purchase_location', 'store')
                if not loc:
                    loc = data.get('location', 'store')
                if loc == 'store':
                    entity_name = 'Magasin -> Dépôt'
                else:
                    entity_name = 'Dépôt -> Magasin'
            elif ent_id:
                found = next((c for c in self.all_clients if c['id'] == ent_id), None)
                if not found:
                    found = next((s for s in self.all_suppliers if s['id'] == ent_id), None)
                if found:
                    entity_name = found.get('name', 'Tiers')
            else:
                entity_name = 'COMPTOIR'
            amount = 0
            if is_simple_payment:
                amount = float(data.get('amount', 0))
            else:
                try:
                    ht, tva = self.calculate_cart_totals(data.get('items', []), doc_type in ['FC', 'FF'])
                    amount = ht + tva
                    if doc_type == 'FC':
                        pay_info = data.get('payment_info', {})
                        amount += float(pay_info.get('timbre', 0))
                except:
                    amount = 0
            full_doc_name = self.DOC_TRANSLATIONS.get(doc_type, doc_type)
            icon_name = 'file-document'
            icon_color = (0, 0.5, 0.8, 1)
            bg_col = (1, 1, 1, 1)
            amount_text = f'{amount:.2f} DA'
            if doc_type == 'RC':
                icon_name = 'keyboard-return'
                bg_col = (1, 0.9, 0.9, 1)
                icon_color = (0.8, 0, 0, 1)
                full_doc_name = 'Retour Client'
            elif doc_type == 'RF':
                icon_name = 'undo'
                bg_col = (0.9, 1, 1, 1)
                icon_color = (0, 0.6, 0.6, 1)
                full_doc_name = 'Retour Fournisseur'
            elif doc_type == 'TR':
                full_doc_name = 'Transfert Stock'
                icon_name = 'compare-horizontal'
                bg_col = (0.95, 0.9, 1, 1)
                icon_color = (0.5, 0, 0.5, 1)
                amount_text = 'Stock'
            elif is_simple_payment:
                p_type = data.get('type', 'client_pay')
                if amount >= 0:
                    custom_lbl = str(data.get('custom_label', '')).upper()
                    if p_type == 'supplier_pay' or 'REGLEMENT' in custom_lbl or 'RÈGLEMENT' in custom_lbl:
                        full_doc_name = 'Règlement'
                        icon_name = 'cash-refund'
                        icon_color = (1, 0.6, 0, 1)
                    else:
                        full_doc_name = 'Versement'
                        icon_name = 'cash-plus'
                        icon_color = (0, 0.7, 0, 1)
                    amount_text = f'+ {abs(amount):.2f} DA'
                else:
                    full_doc_name = 'Crédit / Dette'
                    icon_name = 'notebook-edit'
                    icon_color = (0.8, 0, 0, 1)
                    amount_text = f'- {abs(amount):.2f} DA'
            elif doc_type == 'BV':
                icon_name = 'cart'
                full_doc_name = 'Bon de Vente'
            elif doc_type == 'BA':
                icon_name = 'truck'
                full_doc_name = "Bon d'Achat"
                icon_color = (1, 0.6, 0, 1)
            elif doc_type == 'FC':
                icon_name = 'file-document'
                full_doc_name = 'Facture Vente'
                icon_color = (0, 0, 0.8, 1)
            elif doc_type == 'FF':
                icon_name = 'file-document-edit'
                full_doc_name = 'Facture Achat'
                icon_color = (1, 0.4, 0, 1)
            ref_str = f'Local • {self.current_user_name}'
            self.history_rv_data.append({'type_str': full_doc_name, 'ref_str': ref_str, 'entity_str': entity_name, 'date_str': dt_str, 'amount_text': amount_text, 'icon': icon_name, 'icon_color': icon_color, 'bg_color': bg_col, 'is_local': True, 'key': k, 'raw_data': None})
        self.rv_history.data = self.history_rv_data
        if self.is_server_reachable:
            url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/history?date={target_date}'
            UrlRequest(url, on_success=self.on_history_server_loaded, on_failure=self.on_history_fail)
        elif not self.history_rv_data:
            self.rv_history.data = []

    def on_history_server_loaded(self, req, result):
        if not result:
            if not any((item['is_local'] for item in self.history_rv_data)):
                pass
            return
        main_doc_prefixes = ['BV', 'BA', 'RC', 'RF', 'TR', 'FP', 'DP', 'BI', 'FC', 'FF']
        default_names = ['زبون افتراضي', 'مورد افتراضي', 'DEFAULT_CUSTOMER', 'DEFAULT_SUPPLIER', 'Comptoir', 'Fournisseur']
        for item in result:
            if self.is_seller_mode:
                item_user = str(item.get('user', '')).strip()
                if item_user != self.current_user_name:
                    continue
            desc = str(item.get('desc', '')).strip()
            prefix = desc[:2].upper() if len(desc) >= 2 else ''
            desc_lower = desc.lower()
            is_transfer = item.get('is_transfer', False)
            amount = float(item.get('amount', 0))
            raw_entity_name = str(item.get('entity', ''))
            entity_display = raw_entity_name.replace('➔', ' -> ').replace('\uf0e0', ' -> ').replace('\uf0da', ' -> ')
            if is_transfer:
                lower_raw = raw_entity_name.lower()
                if 'dép' in lower_raw and 'mag' in lower_raw:
                    if lower_raw.find('dép') < lower_raw.find('mag'):
                        entity_display = 'Dépôt -> Magasin'
                    else:
                        entity_display = 'Magasin -> Dépôt'
            if any((name.lower() in raw_entity_name.lower() for name in default_names)):
                entity_display = 'COMPTOIR'
            is_main_doc = prefix in main_doc_prefixes or is_transfer
            has_doc_ref = any((ref in desc for ref in main_doc_prefixes))
            if not is_main_doc and has_doc_ref:
                continue
            full_doc_name = self.DOC_TRANSLATIONS.get(prefix, desc)
            bg_col = (0.98, 0.98, 1, 1)
            icon_name = 'file-document'
            icon_color = (0, 0.5, 0.8, 1)
            amount_text = f'{abs(amount):.2f} DA'
            if is_transfer:
                full_doc_name = 'Transfert Stock'
                icon_name = 'compare-horizontal'
                bg_col = (0.96, 0.94, 1, 1)
                amount_text = 'Stock'
                icon_color = (0.5, 0, 0.5, 1)
            elif not is_main_doc:
                if amount < 0:
                    is_reglement_kw = any((k in desc_lower for k in ['règlement', 'reglement', 'سداد', 'supplier']))
                    if is_reglement_kw:
                        full_doc_name = 'Règlement'
                        icon_name = 'cash-refund'
                        icon_color = (1, 0.6, 0, 1)
                    else:
                        full_doc_name = 'Versement'
                        icon_name = 'cash-plus'
                        icon_color = (0, 0.7, 0, 1)
                    amount_text = f'+ {abs(amount):.2f} DA'
                else:
                    full_doc_name = 'Crédit / Dette'
                    icon_name = 'notebook-edit'
                    icon_color = (0.8, 0, 0, 1)
                    amount_text = f'- {abs(amount):.2f} DA'
            elif prefix == 'BV':
                icon_name = 'cart'
                full_doc_name = 'Bon de Vente'
            elif prefix == 'BA':
                icon_name = 'truck'
                icon_color = (1, 0.6, 0, 1)
            elif prefix == 'RC':
                icon_name = 'keyboard-return'
                bg_col = (1, 0.95, 0.95, 1)
                icon_color = (0.8, 0, 0, 1)
            elif prefix == 'RF':
                icon_name = 'undo'
                icon_color = (0, 0.6, 0.6, 1)
            elif prefix == 'FC':
                icon_name = 'file-document'
                full_doc_name = 'Facture Vente'
                icon_color = (0, 0, 0.8, 1)
            elif prefix == 'FP':
                icon_name = 'file-document-outline'
                icon_color = (0.5, 0, 0.5, 1)
                full_doc_name = 'Proforma'
            elif prefix == 'FF':
                icon_name = 'file-document-edit'
                icon_color = (1, 0.4, 0, 1)
                full_doc_name = 'Facture Achat'
            elif prefix == 'DP':
                icon_name = 'clipboard-list'
                icon_color = (0, 0.5, 0.5, 1)
                full_doc_name = 'Bon de Commande'
            elif prefix == 'BI':
                icon_name = 'database-plus'
                full_doc_name = 'Bon Initial'
            clean_desc = desc.replace('Versement (Excédent)', 'Versement').replace('Règlement (Excédent)', 'Règlement')
            ref_str = f"{clean_desc} • {item.get('user', '')}"
            time_str = item.get('time', '').split(' ')[1] if ' ' in item.get('time', '') else item.get('time', '')
            self.history_rv_data.append({'type_str': full_doc_name, 'ref_str': ref_str, 'entity_str': entity_display, 'date_str': time_str, 'amount_text': amount_text, 'icon': icon_name, 'icon_color': icon_color, 'bg_color': bg_col, 'is_local': False, 'key': '', 'raw_data': item})
        self.rv_history.data = self.history_rv_data
        self.rv_history.refresh_from_data()

    def on_history_fail(self, req, err):
        self.history_rv_data.append({'raw_text': 'Erreur chargement serveur.', 'raw_sec': str(err), 'amount_text': '', 'icon': 'alert-circle', 'icon_color': (0.8, 0, 0, 1), 'bg_color': (1, 1, 1, 1), 'is_local': False, 'key': '', 'raw_data': None})
        self.rv_history.data = self.history_rv_data
        self.rv_history.refresh_from_data()

    def handle_pending_item(self, key, is_synced):
        item_data = self.offline_store.get(key)
        data = item_data.get('order_data', {})
        doc_type = data.get('doc_type', 'BV')
        if self.is_seller_mode:
            try:
                ts_key = int(key.split('_')[0])
                item_date = datetime.fromtimestamp(ts_key).date()
                if item_date != datetime.now().date():
                    self.notify('Modification interdite (Date passée)', 'error')
                    return
            except:
                pass
        if self.pending_dialog:
            self.pending_dialog.dismiss()
        if is_synced and self.is_seller_mode:
            try:
                self.view_synced_transaction(data)
            except:
                self.notify('Erreur lecture', 'error')
            return

        def do_delete(x):
            if hasattr(self, 'confirm_del_dialog') and self.confirm_del_dialog:
                self.confirm_del_dialog.dismiss()
            if self.srv_dialog:
                self.srv_dialog.dismiss()
            if is_synced:
                server_id = data.get('server_id')
                is_tr = doc_type == 'TR'
                if server_id and self.is_server_reachable:
                    UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/delete_transaction', req_body=json.dumps({'server_id': server_id, 'is_transfer': is_tr}), req_headers={'Content-type': 'application/json'}, method='POST', on_success=lambda r, s: self.offline_store.delete(key) or self.notify('Supprimé du Serveur', 'success'), on_failure=lambda r, e: self.notify('Echec suppression serveur', 'error'))
                else:
                    self.offline_store.delete(key)
                    self.notify('Supprimé (Local)', 'info')
            else:
                self.offline_store.delete(key)
                self.notify('Supprimé (Local)', 'info')
            self._reset_notification_state(0)
            target_date = getattr(self, 'history_view_date', datetime.now().date())
            self.filter_history_list(specific_date=target_date)

        def show_confirmation(x):
            self.confirm_del_dialog = MDDialog(title='Confirmation', text='Voulez-vous vraiment supprimer cette opération ?\nCette action est irréversible.', buttons=[MDFlatButton(text='NON', on_release=lambda y: self.confirm_del_dialog.dismiss()), MDRaisedButton(text='OUI', md_bg_color=(0.8, 0, 0, 1), text_color=(1, 1, 1, 1), on_release=do_delete)])
            self.confirm_del_dialog.open()

        def do_load(x):
            if self.srv_dialog:
                self.srv_dialog.dismiss()
            try:
                self.editing_transaction_key = key
                self.current_editing_date = data.get('timestamp')
                self.current_editing_server_id = data.get('server_id')
                if data.get('is_simple_payment'):
                    self.current_mode = data.get('type')
                    saved_ent_id = data.get('entity_id')
                    found = next((c for c in self.all_clients if c['id'] == saved_ent_id), None)
                    if not found:
                        found = next((s for s in self.all_suppliers if s['id'] == saved_ent_id), None)
                    self.selected_entity = found if found else {'id': saved_ent_id, 'name': 'Inconnu'}
                    self.show_simple_payment_dialog(amount=abs(float(data.get('amount', 0))))
                    return
                self.original_doc_type = doc_type
                mode_map = {'BV': 'sale', 'BA': 'purchase', 'RC': 'return_sale', 'RF': 'return_purchase', 'TR': 'transfer', 'FC': 'invoice_sale', 'FP': 'proforma', 'FF': 'invoice_purchase', 'DP': 'order_purchase', 'BI': 'purchase'}
                self.open_mode(mode_map.get(doc_type, 'sale'), skip_dialog=True)
                raw_items = data.get('items', [])
                self.cart = []
                for item in raw_items:
                    item['tva'] = float(item.get('tva', 0))
                    self.cart.append(item)
                saved_loc = data.get('purchase_location') or data.get('location', 'store')
                self.selected_location = saved_loc
                saved_ent_id = data.get('entity_id')
                found_entity = None
                if saved_ent_id:
                    found_entity = next((c for c in self.all_clients if c['id'] == saved_ent_id), None)
                    if not found_entity:
                        found_entity = next((s for s in self.all_suppliers if s['id'] == saved_ent_id), None)
                    self.selected_entity = found_entity if found_entity else {'id': saved_ent_id, 'name': 'Client (Cache)'}
                else:
                    self.selected_entity = {'id': None, 'name': 'COMPTOIR'}
                self.update_location_display()
                if self.selected_entity and hasattr(self, 'btn_ent_screen'):
                    self.btn_ent_screen.text = self.fix_text(str(self.selected_entity.get('name', '')))[:15]
                    self.btn_ent_screen.disabled = False
                    if self.current_mode in ['sale', 'return_sale', 'client_payment', 'invoice_sale', 'proforma']:
                        self.btn_ent_screen.md_bg_color = (0, 0.6, 0.6, 1)
                    else:
                        self.btn_ent_screen.md_bg_color = (0.8, 0.4, 0, 1)
                payment_info = data.get('payment_info', {})
                try:
                    self.editing_payment_amount = float(payment_info.get('amount', 0))
                except:
                    self.editing_payment_amount = 0
                self.editing_payment_method = payment_info.get('method', '')
                self.update_cart_button()
                self.open_cart_screen(None)
            except Exception as e:
                self.notify(f'Erreur chargement: {e}', 'error')

        def do_print(x):
            try:
                threading.Thread(target=self.print_ticket_bluetooth, args=(data,), daemon=True).start()
                self.notify('Impression lancée...', 'info')
            except Exception as e:
                self.notify(f'Erreur Impression: {e}', 'error')
        ts_raw = data.get('timestamp')
        date_display = 'Inconnue'
        try:
            if isinstance(ts_raw, (int, float)):
                date_display = datetime.fromtimestamp(ts_raw).strftime('%Y-%m-%d %H:%M')
            else:
                dt_str = str(ts_raw).split('.')[0]
                if len(dt_str) >= 16:
                    date_display = dt_str[:16]
                else:
                    date_display = dt_str
        except:
            date_display = str(ts_raw)
        ent_id = data.get('entity_id')
        entity_name = 'COMPTOIR'
        if ent_id:
            found = next((c for c in self.all_clients if c['id'] == ent_id), None)
            if not found:
                found = next((s for s in self.all_suppliers if s['id'] == ent_id), None)
            if found:
                entity_name = found.get('name', 'Tiers')
        is_transfer = doc_type == 'TR'
        if is_transfer:
            loc = data.get('purchase_location') or data.get('location', 'store')
            if loc == 'store':
                entity_name = 'Magasin -> Dépôt'
            else:
                entity_name = 'Dépôt -> Magasin'
        items = data.get('items', [])
        total_items = 0.0
        for item in items:
            p = float(item.get('price', 0))
            q = float(item.get('qty', 0))
            t = float(item.get('tva', 0))
            total_items += p * q * (1 + t / 100)
        payment_info = data.get('payment_info', {})
        timbre = float(payment_info.get('timbre', 0))
        final_total = total_items + timbre
        paid_amount = float(payment_info.get('amount', 0)) if not is_transfer else 0
        full_doc_name = self.DOC_TRANSLATIONS.get(doc_type, doc_type)
        is_financial = data.get('is_simple_payment', False)
        if is_financial:
            amount = float(data.get('amount', 0))
            if amount >= 0:
                p_type = data.get('type', 'client_pay')
                if p_type == 'supplier_pay':
                    full_doc_name = 'Règlement'
                    amount_color = (1, 0.6, 0, 1)
                else:
                    full_doc_name = 'Versement'
                    amount_color = (0, 0.7, 0, 1)
                display_amount = f'+ {abs(amount):.2f} DA'
            else:
                full_doc_name = 'Crédit / Dette'
                amount_color = (0.8, 0, 0, 1)
                display_amount = f'- {abs(amount):.2f} DA'
            final_total = abs(amount)
        else:
            amount_color = (0, 0, 0, 1)
            display_amount = f'{final_total:.2f} DA'
        if is_transfer:
            full_doc_name = 'Transfert Stock'
            display_amount = 'Stock'
            amount_color = (0.5, 0, 0.5, 1)
        content = MDBoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=dp(550))
        header_box = MDCard(orientation='vertical', adaptive_height=True, padding=dp(10), md_bg_color=(0.95, 0.95, 0.95, 1), radius=[10])
        header_box.add_widget(MDLabel(text=self.fix_text(f'{full_doc_name} - {entity_name}'), bold=True, font_style='Subtitle1', adaptive_height=True))
        header_box.add_widget(MDLabel(text=f'Date: {date_display}', font_style='Caption', theme_text_color='Secondary', adaptive_height=True))
        header_box.add_widget(MDLabel(text=f'Montant: {display_amount}', theme_text_color='Custom', text_color=amount_color, bold=True, font_style='H5', adaptive_height=True))
        if not is_financial and (not is_transfer):
            if timbre > 0:
                header_box.add_widget(MDLabel(text=f'Timbre: {timbre:.2f} DA', font_style='Caption', theme_text_color='Custom', text_color=(0.5, 0, 0.5, 1), adaptive_height=True))
            diff = round(final_total - paid_amount, 2)
            if abs(diff) <= 0.05:
                pay_row = MDBoxLayout(orientation='horizontal', adaptive_height=True, spacing=dp(5))
                pay_row.add_widget(MDLabel(text='Payée', theme_text_color='Custom', text_color=(0, 0.6, 0, 1), bold=True, font_style='Subtitle1', adaptive_size=True))
                pay_row.add_widget(MDIcon(icon='check-circle', theme_text_color='Custom', text_color=(0, 0.6, 0, 1), font_size='20sp', pos_hint={'center_y': 0.5}))
                header_box.add_widget(pay_row)
            else:
                header_box.add_widget(MDLabel(text=f'Versé: {paid_amount:.2f} DA', theme_text_color='Custom', text_color=(0, 0.6, 0, 1), bold=True, font_style='Subtitle1', adaptive_height=True))
                header_box.add_widget(MDLabel(text=f'Reste: {diff:.2f} DA', theme_text_color='Custom', text_color=(0.8, 0, 0, 1), bold=True, font_style='Subtitle1', adaptive_height=True))
        content.add_widget(header_box)
        content.add_widget(MDLabel(text='Détails:', font_style='Caption', size_hint_y=None, height=dp(20)))
        scroll = MDScrollView()
        list_layout = MDList()
        if items and (not is_financial):
            for item in items:
                qty = float(item.get('qty', 0))
                qty_str = str(int(qty)) if qty.is_integer() else str(qty)
                price = float(item.get('price', 0))
                line_total = qty * price * (1 + float(item.get('tva', 0)) / 100)
                item_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=[dp(16), dp(8)], spacing=dp(4))
                lbl_name = MDLabel(text=self.fix_text(item.get('name', '')), theme_text_color='Primary', font_style='Subtitle1', bold=True, adaptive_height=True, shorten=False)
                if doc_type == 'TR':
                    lbl_details = MDLabel(text=f'Qté: {qty_str}', theme_text_color='Secondary', font_style='Body2', adaptive_height=True)
                    item_box.add_widget(lbl_name)
                    item_box.add_widget(lbl_details)
                else:
                    lbl_details = MDLabel(text=f'{qty_str} x {price:.2f} DA', theme_text_color='Secondary', font_style='Body2', adaptive_height=True)
                    lbl_total = MDLabel(text=f'Total: {line_total:.2f} DA', theme_text_color='Secondary', font_style='Body2', adaptive_height=True)
                    item_box.add_widget(lbl_name)
                    item_box.add_widget(lbl_details)
                    item_box.add_widget(lbl_total)
                list_layout.add_widget(item_box)
                list_layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(1), md_bg_color=(0.9, 0.9, 0.9, 1)))
        elif is_financial:
            list_layout.add_widget(OneLineListItem(text='Opération Financière (Caisse)'))
        else:
            list_layout.add_widget(OneLineListItem(text='Aucun article'))
        scroll.add_widget(list_layout)
        content.add_widget(scroll)
        actions_layout = MDBoxLayout(orientation='vertical', spacing='10dp', adaptive_height=True, padding=[0, '15dp', 0, 0])
        top_row = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='50dp')
        if doc_type not in ['FC', 'FP', 'FF', 'DP', 'BI']:
            btn_print = MDFillRoundFlatButton(text='IMPRIMER', md_bg_color=(0, 0.5, 0.8, 1), text_color=(1, 1, 1, 1), size_hint_x=0.5, on_release=do_print)
            top_row.add_widget(btn_print)
        btn_edit = MDFillRoundFlatButton(text='MODIFIER', md_bg_color=(0, 0.7, 0, 1), text_color=(1, 1, 1, 1), size_hint_x=0.5, on_release=do_load)
        top_row.add_widget(btn_edit)
        actions_layout.add_widget(top_row)
        btn_delete = MDFlatButton(text='SUPPRIMER (LOCAL)', theme_text_color='Custom', text_color=(0.9, 0, 0, 1), size_hint_x=1, on_release=show_confirmation)
        actions_layout.add_widget(btn_delete)
        content.add_widget(actions_layout)
        title_txt = 'Détails (Non Synchronisé)' + (' [Admin]' if is_synced else '')
        self.srv_dialog = MDDialog(title=title_txt, type='custom', content_cls=content, size_hint=(0.95, 0.95), buttons=[MDFlatButton(text='FERMER', on_release=lambda x: self.srv_dialog.dismiss())])
        self.srv_dialog.open()

    def view_synced_transaction(self, data):
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(500))
        if data.get('is_simple_payment'):
            typ = 'Versement' if data.get('type') == 'client_pay' else 'Règlement'
            amount = data.get('amount', 0)
            content.add_widget(MDLabel(text=f'TYPE: {typ}', halign='center', font_style='H6'))
            content.add_widget(MDLabel(text=f'MONTANT: {amount:.2f} DA', halign='center', font_style='H4', theme_text_color='Custom', text_color=(0, 0.6, 0, 1)))
            content.add_widget(MDBoxLayout(size_hint_y=1))
        else:
            scroll = MDScrollView()
            lst = MDList()
            items = data.get('items', [])
            total_items = 0.0
            doc_type = data.get('doc_type', 'BV')
            for item in items:
                p = float(item.get('price', 0))
                q = float(item.get('qty', 0))
                t = float(item.get('tva', 0))
                sub_ttc = p * q * (1 + t / 100)
                total_items += sub_ttc
                qty_disp = int(q) if q.is_integer() else q
                details = f'{p:.2f} DA x {qty_disp}'
                if t > 0 and doc_type in ['FC', 'FF', 'FP']:
                    details += f' [color=#FF0000](+{int(t)}% TVA)[/color]'
                li = ThreeLineAvatarIconListItem(text=item.get('name', 'Produit'), secondary_text=details, tertiary_text=f'Total: {sub_ttc:.2f} DA')
                li.add_widget(IconLeftWidget(icon='package-variant'))
                lst.add_widget(li)
            scroll.add_widget(lst)
            content.add_widget(scroll)
            payment_info = data.get('payment_info', {})
            method = payment_info.get('method', '')
            timbre = 0.0
            if doc_type == 'FC':
                if method in ['دفع نقدًا', 'Espèce']:
                    timbre = self._calculate_stamp_duty(total_items)
            final_total = total_items + timbre
            box_totals = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=[0, 10, 0, 0])
            box_totals.add_widget(MDLabel(text=f'Total Articles: {total_items:.2f} DA', halign='right', font_style='Subtitle1'))
            if timbre > 0:
                box_totals.add_widget(MDLabel(text=f'Droit de Timbre: {timbre:.2f} DA', halign='right', font_style='Caption', theme_text_color='Custom', text_color=(0.5, 0, 0.5, 1), bold=True))
            box_totals.add_widget(MDLabel(text=f'NET À PAYER: {final_total:.2f} DA', halign='center', font_style='H5', bold=True, theme_text_color='Primary'))
            content.add_widget(box_totals)

        def do_print(x):
            threading.Thread(target=self.print_ticket_bluetooth, args=(data,), daemon=True).start()
        doc_type = data.get('doc_type', 'BV')
        pdf_only_types = ['FC', 'FP', 'FF', 'DP', 'BI']
        buttons = []
        if doc_type not in pdf_only_types:
            buttons.append(MDRaisedButton(text='IMPRIMER', on_release=do_print))
        buttons.append(MDFlatButton(text='FERMER', on_release=lambda x: x.parent.parent.parent.parent.dismiss()))
        MDDialog(title='Détails (Synchronisé/Local)', type='custom', content_cls=content, size_hint=(0.95, 0.95), buttons=buttons).open()

    def handle_server_history_item(self, item_data):
        if self.pending_dialog:
            self.pending_dialog.dismiss()
        self.notify('Chargement des détails...', 'info')
        is_tr_str = 'true' if item_data.get('is_transfer') else 'false'
        url = f"http://{self.active_server_ip}:{DEFAULT_PORT}/api/get_transaction_details?id={item_data['id']}&is_transfer={is_tr_str}"

        def on_success_callback(req, res):
            if res.get('purchase_location'):
                item_data['purchase_location'] = res.get('purchase_location')
            if res.get('location'):
                item_data['location'] = res.get('location')
            if res.get('source_location'):
                item_data['source_location'] = res.get('source_location')
            self.show_server_transaction_details(item_data, res)
        UrlRequest(url, on_success=on_success_callback, on_failure=lambda r, e: self.notify('Erreur chargement détails', 'error'), on_error=lambda r, e: self.notify('Erreur connexion', 'error'))

    def show_server_transaction_details(self, header_data, result):
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.card import MDCard
        from kivymd.uix.button import MDFillRoundFlatButton, MDFlatButton
        from kivymd.uix.list import MDList, OneLineListItem
        items = result.get('items', [])
        real_paid_amount = result.get('paid_amount')
        if real_paid_amount is None:
            real_paid_amount = header_data.get('paid_amount', 0)
        header_data['paid_amount'] = real_paid_amount
        paid_val = float(real_paid_amount)
        is_transfer = header_data.get('is_transfer', False)
        raw_entity_name = str(header_data.get('entity', ''))
        entity_name = raw_entity_name.replace('➔', ' -> ').replace('\uf0e0', ' -> ').replace('\uf0da', ' -> ')
        if is_transfer:
            lower_raw = raw_entity_name.lower()
            if 'dép' in lower_raw and 'mag' in lower_raw:
                entity_name = 'Dépôt -> Magasin' if lower_raw.find('dép') < lower_raw.find('mag') else 'Magasin -> Dépôt'
            elif 'dép' in lower_raw:
                entity_name = 'Dépôt -> Magasin'
            elif 'mag' in lower_raw:
                entity_name = 'Magasin -> Dépôt'
        auto_pay_names = ['COMPTOIR', 'Comptoir', 'زبون افتراضي', 'مورد افتراضي', 'DEFAULT_CUSTOMER']
        is_comptoir = any((n in entity_name for n in auto_pay_names))
        content = MDBoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=dp(550))
        prefix = header_data['desc'][:2]
        full_desc = header_data.get('desc', '').lower()
        amount = float(header_data.get('amount', 0))
        calculated_items_total = 0.0
        for item in items:
            p = float(item.get('price', 0))
            q = float(item.get('qty', 0))
            t = float(item.get('tva', 0))
            line_ht = self._round_num(p * q)
            line_ttc = self._round_num(line_ht * (1 + t / 100.0))
            calculated_items_total += line_ttc
        calculated_items_total = self._round_num(calculated_items_total)
        diff_val = self._round_num(abs(amount) - calculated_items_total)
        timbre_to_show = 0.0
        if prefix in ['FC', 'FF'] and diff_val > 0.5:
            timbre_to_show = diff_val
        display_total = self._round_num(calculated_items_total + timbre_to_show)
        is_reglement_kw = any((k in full_desc for k in ['règlement', 'reglement', 'سداد']))
        main_docs = ['BV', 'BA', 'RC', 'RF', 'TR', 'FP', 'FC', 'FF', 'DP', 'BI']
        is_financial_op = False
        if not prefix in main_docs:
            if amount < 0:
                type_str = 'Règlement' if is_reglement_kw else 'Versement'
                amount_color = (0, 0.7, 0, 1)
                display_amount_str = f'+ {abs(amount):.2f} DA'
            else:
                type_str = 'Crédit / Dette'
                amount_color = (0.8, 0, 0, 1)
                display_amount_str = f'- {abs(amount):.2f} DA'
            is_financial_op = True
        else:
            type_str = self.DOC_TRANSLATIONS.get(prefix, 'Opération')
            amount_color = (0, 0, 0, 1)
            display_amount_str = f'{display_total:.2f} DA'
        header_box = MDCard(orientation='vertical', adaptive_height=True, padding=dp(10), md_bg_color=(0.95, 0.95, 0.95, 1), radius=[10])
        header_box.add_widget(MDLabel(text=self.fix_text(f'{type_str} - {entity_name}'), bold=True, font_style='Subtitle1', adaptive_height=True))
        header_box.add_widget(MDLabel(text=f"Date: {header_data.get('time', '')}", font_style='Caption', adaptive_height=True))
        if not is_transfer:
            header_box.add_widget(MDLabel(text=f'Montant: {display_amount_str}', theme_text_color='Custom', text_color=amount_color, bold=True, font_style='H5', adaptive_height=True))
            if timbre_to_show > 0:
                header_box.add_widget(MDLabel(text=f'Droit de Timbre: {timbre_to_show:.2f} DA', theme_text_color='Custom', text_color=(0.5, 0, 0.5, 1), bold=True, font_style='Caption', adaptive_height=True))
            if not is_financial_op and prefix not in ['FP', 'DP']:
                paid_float = paid_val if not is_comptoir else display_total
                diff = self._round_num(display_total - paid_float)
                if abs(diff) < 0.05:
                    pay_row = MDBoxLayout(orientation='horizontal', adaptive_height=True, spacing=dp(5))
                    pay_row.add_widget(MDLabel(text='Payée', theme_text_color='Custom', text_color=(0, 0.6, 0, 1), bold=True, font_style='Subtitle1', adaptive_size=True))
                    pay_row.add_widget(MDIcon(icon='check-circle', theme_text_color='Custom', text_color=(0, 0.6, 0, 1), font_size='20sp', pos_hint={'center_y': 0.5}))
                    header_box.add_widget(pay_row)
                else:
                    header_box.add_widget(MDLabel(text=f'Versé: {paid_float:.2f} DA', theme_text_color='Custom', text_color=(0, 0.6, 0, 1), bold=True, font_style='Subtitle1', adaptive_height=True))
                    if diff > 0.05:
                        header_box.add_widget(MDLabel(text=f'Crédit: {diff:.2f} DA', theme_text_color='Custom', text_color=(0.8, 0, 0, 1), bold=True, font_style='Subtitle1', adaptive_height=True))
        else:
            header_box.add_widget(MDLabel(text='Transfert de stock', font_style='Caption', theme_text_color='Hint', adaptive_height=True))
        content.add_widget(header_box)
        content.add_widget(MDLabel(text='Détails:', font_style='Caption', size_hint_y=None, height=dp(20)))
        scroll = MDScrollView()
        list_layout = MDList()
        if items:
            for item in items:
                qty = float(item.get('qty', 0))
                qty_str = str(int(qty)) if qty.is_integer() else str(qty)
                price = float(item.get('price', 0))
                total_line = qty * price
                item_box = MDBoxLayout(orientation='vertical', adaptive_height=True, padding=[dp(16), dp(8)], spacing=dp(4))
                lbl_name = MDLabel(text=self.fix_text(item.get('name', '')), theme_text_color='Primary', font_style='Subtitle1', bold=True, adaptive_height=True, shorten=False)
                if is_transfer:
                    lbl_details = MDLabel(text=f'Qté: {qty_str}', theme_text_color='Secondary', font_style='Body2', adaptive_height=True)
                    item_box.add_widget(lbl_name)
                    item_box.add_widget(lbl_details)
                else:
                    lbl_details = MDLabel(text=f'{qty_str} x {price:.2f} DA', theme_text_color='Secondary', font_style='Body2', adaptive_height=True)
                    lbl_total = MDLabel(text=f'Total: {total_line:.2f} DA', theme_text_color='Secondary', font_style='Body2', adaptive_height=True)
                    item_box.add_widget(lbl_name)
                    item_box.add_widget(lbl_details)
                    item_box.add_widget(lbl_total)
                list_layout.add_widget(item_box)
                list_layout.add_widget(MDBoxLayout(size_hint_y=None, height=dp(1), md_bg_color=(0.9, 0.9, 0.9, 1)))
        else:
            list_layout.add_widget(OneLineListItem(text='Aucun article ou opération financière'))
        scroll.add_widget(list_layout)
        content.add_widget(scroll)
        actions_layout = MDBoxLayout(orientation='vertical', spacing='10dp', adaptive_height=True, padding=[0, '15dp', 0, 0])
        top_row = MDBoxLayout(orientation='horizontal', spacing='10dp', size_hint_y=None, height='50dp')
        pdf_only_types = ['FC', 'FP', 'FF', 'DP', 'BI']
        mixed_types = ['BA', 'BV', 'TR', 'RC', 'RF']
        if prefix not in pdf_only_types:

            def do_print_bt(x):
                print_data = header_data.copy()
                print_data['items'] = items
                print_data['doc_type'] = prefix
                threading.Thread(target=self.print_ticket_bluetooth, args=(print_data,), daemon=True).start()
            btn_print = MDFillRoundFlatButton(text='IMPRIMER', md_bg_color=(0, 0.5, 0.8, 1), text_color=(1, 1, 1, 1), size_hint_x=1, on_release=do_print_bt)
            top_row.add_widget(btn_print)
        if prefix in pdf_only_types or prefix in mixed_types:
            btn_text = 'PDF' if prefix in mixed_types else 'TELECHARGER PDF'
            btn_pdf = MDFillRoundFlatButton(text=btn_text, md_bg_color=(0.8, 0.2, 0.2, 1), text_color=(1, 1, 1, 1), size_hint_x=1, on_release=lambda x: self.download_server_pdf(header_data.get('id'), prefix, header_data.get('desc', '')))
            top_row.add_widget(btn_pdf)
        try:
            today_str = str(datetime.now().date())
            is_today = str(header_data.get('time', '')).split(' ')[0] == today_str
        except:
            is_today = False
        can_edit = not self.is_seller_mode or is_today
        if can_edit and prefix != 'BI':
            btn_edit = MDFillRoundFlatButton(text='MODIFIER', md_bg_color=(0, 0.6, 0.4, 1), text_color=(1, 1, 1, 1), size_hint_x=1, on_release=lambda x: self.load_server_transaction_for_edit(header_data, items))
            top_row.add_widget(btn_edit)
        actions_layout.add_widget(top_row)
        if can_edit:
            btn_del = MDFlatButton(text='SUPPRIMER CETTE OPÉRATION', theme_text_color='Custom', text_color=(0.9, 0, 0, 1), size_hint_x=1, on_release=lambda x: self.confirm_delete_server_transaction(header_data))
            actions_layout.add_widget(btn_del)
        else:
            actions_layout.add_widget(MDLabel(text='Modification impossible (Date passée)', halign='center', theme_text_color='Error', font_style='Caption', adaptive_height=True))
        content.add_widget(actions_layout)
        self.srv_dialog = MDDialog(title='Détails', type='custom', content_cls=content, size_hint=(0.95, 0.95), buttons=[MDFlatButton(text='FERMER', on_release=lambda x: self.srv_dialog.dismiss())])
        self.srv_dialog.open()

    def download_server_pdf(self, trans_id, doc_type, file_name_hint):
        if not self.is_server_reachable:
            self.notify('Non connecté au serveur', 'error')
            return
        self.notify('Génération du PDF...', 'info')
        safe_name = str(file_name_hint).replace('/', '_').replace('\\', '_').replace(':', '-')
        url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/download_pdf?id={trans_id}&type={doc_type}'
        file_path = ''
        try:
            if platform == 'android':
                from android.storage import primary_external_storage_path
                dir_path = os.path.join(primary_external_storage_path(), 'Download')
            else:
                dir_path = os.path.join(os.environ['USERPROFILE'], 'Downloads')
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            file_path = os.path.join(dir_path, f'{safe_name}.pdf')
        except Exception as e:
            print(f'Path Error: {e}')
            self.notify('Erreur de chemin', 'error')
            return

        def on_success(req, result):
            try:
                with open(file_path, 'wb') as f:
                    f.write(result)
                self.pdf_success_dialog = MDDialog(title='Téléchargement Terminé', text=f'Le fichier PDF a été enregistré avec succès dans le dossier Téléchargements.', buttons=[MDRaisedButton(text='OK', md_bg_color=(0, 0.7, 0, 1), text_color=(1, 1, 1, 1), on_release=lambda x: self.pdf_success_dialog.dismiss())])
                self.pdf_success_dialog.open()
            except Exception as e:
                self.notify(f'Erreur sauvegarde: {e}', 'error')

        def on_fail(req, err):
            self.notify('Erreur téléchargement', 'error')
        UrlRequest(url, on_success=on_success, on_failure=on_fail, on_error=on_fail)

    def open_pdf_file(self, file_path):
        if platform != 'android':
            try:
                os.startfile(file_path)
            except:
                pass
            return
        try:
            from jnius import autoclass, cast
            from android import activity
            File = autoclass('java.io.File')
            Intent = autoclass('android.content.Intent')
            FileProvider = autoclass('androidx.core.content.FileProvider')
            Context = autoclass('android.content.Context')
            file_obj = File(file_path)
            package_name = activity.getPackageName()
            uri = FileProvider.getUriForFile(Context.getApplicationContext(), f'{package_name}.fileprovider', file_obj)
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(uri, 'application/pdf')
            intent.setFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            current_activity = cast('android.app.Activity', activity)
            current_activity.startActivity(intent)
        except Exception as e:
            print(f'PDF Open Error: {e}')
            self.notify("Impossible d'ouvrir le fichier PDF", 'error')

    def confirm_delete_server_transaction(self, item_data):
        is_transfer = item_data.get('is_transfer', False)
        msg = 'Êtes-vous sûr de vouloir supprimer cette opération ?\nLe stock et le solde seront ajustés.'
        if is_transfer:
            msg = "Supprimer ce transfert de stock ?\nLes quantités seront restituées à l'origine."
        confirm_dialog = MDDialog(title='Confirmer Suppression', text=msg, buttons=[MDFlatButton(text='NON', on_release=lambda x: confirm_dialog.dismiss()), MDRaisedButton(text='OUI', md_bg_color=(0.8, 0, 0, 1), on_release=lambda x: [confirm_dialog.dismiss(), self._execute_delete(item_data)])])
        confirm_dialog.open()

    def _execute_delete(self, item_data):
        if self.srv_dialog:
            self.srv_dialog.dismiss()
        self._do_delete_api(item_data)

    def _do_delete_api(self, item_data_or_id):
        if isinstance(item_data_or_id, dict):
            trans_id = item_data_or_id['id']
            is_transfer = item_data_or_id.get('is_transfer', False)
        else:
            trans_id = item_data_or_id
            is_transfer = False
        UrlRequest(f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/delete_transaction', req_body=json.dumps({'server_id': trans_id, 'is_transfer': is_transfer}), req_headers={'Content-type': 'application/json'}, method='POST', on_success=lambda r, s: self.notify('Supprimé avec succès', 'success') or self.filter_history_list(0), on_failure=lambda r, e: self.notify('Echec suppression', 'error'))

    def load_server_transaction_for_edit(self, header_data, items):
        if hasattr(self, 'srv_dialog') and self.srv_dialog:
            self.srv_dialog.dismiss()
        if hasattr(self, 'entity_hist_dialog') and self.entity_hist_dialog:
            self.entity_hist_dialog.dismiss()
        if hasattr(self, 'mgmt_dialog') and self.mgmt_dialog:
            self.mgmt_dialog.dismiss()
        if hasattr(self, 'pending_dialog') and self.pending_dialog:
            self.pending_dialog.dismiss()
        self.current_editing_date = header_data.get('time') or header_data.get('timestamp')
        found_entity = None
        search_name = header_data.get('entity', '').strip()
        search_id = header_data.get('entity_id')
        if search_id:
            found_entity = next((e for e in self.all_clients if e['id'] == search_id), None)
            if not found_entity:
                found_entity = next((e for e in self.all_suppliers if e['id'] == search_id), None)
        if not found_entity and search_name:
            found_entity = next((e for e in self.all_clients if e.get('name') == search_name), None)
            if not found_entity:
                found_entity = next((e for e in self.all_suppliers if e.get('name') == search_name), None)
        prefix = header_data['desc'][:2]
        mode_map = {'BV': 'sale', 'BA': 'purchase', 'RC': 'return_sale', 'RF': 'return_purchase', 'TR': 'transfer', 'FC': 'invoice_sale', 'FP': 'proforma', 'FF': 'invoice_purchase', 'DP': 'order_purchase', 'BI': 'purchase'}
        mode = mode_map.get(prefix)
        amount = float(header_data.get('amount', 0))
        full_desc = header_data.get('desc', '').lower()
        is_financial = False
        if not mode or not items:
            is_supplier_op = any((k in full_desc for k in ['règlement', 'reglement', 'سداد', 'fournisseur']))
            if found_entity:
                if any((s['id'] == found_entity['id'] for s in self.all_suppliers)):
                    is_supplier_op = True
            self.current_mode = 'supplier_payment' if is_supplier_op else 'client_payment'
            is_financial = True
        if is_financial:
            self.editing_transaction_key = 'SERVER_EDIT_MODE'
            self.current_editing_server_id = header_data['id']
            if found_entity:
                self.selected_entity = found_entity
            elif search_name:
                self.selected_entity = {'id': None, 'name': search_name}
            else:
                self.selected_entity = {'id': None, 'name': 'Client Inconnu'}
            if self.selected_entity and hasattr(self, 'btn_ent_screen'):
                self.btn_ent_screen.text = self.fix_text(str(self.selected_entity.get('name', 'Client')))[:15]
            self.show_simple_payment_dialog(amount=abs(amount))
            return
        if not mode:
            if 'Initial' in header_data.get('desc', '') or 'BI' in header_data.get('desc', ''):
                mode = 'purchase'
                self.original_doc_type = 'BI'
            else:
                self.notify("Type d'opération non modifiable", 'error')
                return
        self.open_mode(mode, skip_dialog=True)
        if prefix == 'BI':
            self.original_doc_type = 'BI'
        if found_entity:
            self.selected_entity = found_entity
        elif search_name:
            self.selected_entity = {'id': None, 'name': search_name}
        else:
            self.selected_entity = {'id': None, 'name': 'COMPTOIR'}
        if self.selected_entity and hasattr(self, 'btn_ent_screen'):
            self.btn_ent_screen.text = self.fix_text(str(self.selected_entity.get('name', 'Client')))[:15]
            self.btn_ent_screen.disabled = False
            if self.current_mode in ['sale', 'return_sale', 'client_payment', 'invoice_sale', 'proforma']:
                self.btn_ent_screen.md_bg_color = (0, 0.6, 0.6, 1)
            else:
                self.btn_ent_screen.md_bg_color = (0.8, 0.4, 0, 1)
        raw_loc = header_data.get('purchase_location')
        if not raw_loc:
            raw_loc = header_data.get('location')
        if not raw_loc and prefix == 'TR':
            raw_loc = header_data.get('source_location')
        target_loc = 'store'
        if raw_loc:
            loc_str = str(raw_loc).lower().strip()
            warehouse_keywords = ['warehouse', 'depot', 'dépôt', 'stock_warehouse']
            if any((k in loc_str for k in warehouse_keywords)):
                target_loc = 'warehouse'
        self.selected_location = target_loc
        self.update_location_display()
        if prefix == 'TR' and hasattr(self, 'btn_ent_screen'):
            src = 'Magasin' if self.selected_location == 'store' else 'Dépôt'
            dst = 'Dépôt' if self.selected_location == 'store' else 'Magasin'
            self.btn_ent_screen.text = f'{src}  >>>  {dst}'
        self.cart = []
        for item in items:
            self.cart.append({'id': item['id'], 'name': item['name'], 'price': float(item['price']), 'qty': float(item['qty']), 'tva': float(item.get('tva', 0))})
        self.editing_transaction_key = 'SERVER_EDIT_MODE'
        self.current_editing_server_id = header_data['id']
        try:
            self.editing_payment_amount = float(header_data.get('paid_amount', 0))
        except:
            self.editing_payment_amount = 0
        payment_info = header_data.get('payment_info', {})
        method = payment_info.get('method', '')
        if not method:
            method = header_data.get('payment_method', '')
        self.editing_payment_method = method
        self.update_cart_button()
        self.notify('Modification: Données chargées', 'success')
        self.open_cart_screen()

    def manual_sync(self):
        self.try_sync_offline_data()
        self.notify('Synchronisation...')

    def go_back(self):
        try:
            Window.release_all_keyboards()
            self.editing_transaction_key = None
            self.current_editing_server_id = None
            self.editing_payment_amount = None
            if hasattr(self, 'editing_payment_method'):
                del self.editing_payment_method
            if self.search_field:
                self.search_field.text = ''
            self.cart = []
            self.update_cart_button()
            self.sm.current = 'dashboard'
            self._reset_notification_state(0)
        except:
            self.sm.current = 'dashboard'

    def open_barcode_scanner(self, instance):
        self.temp_scanned_cart = []
        self.potential_code = None
        self.consecutive_frames = 0
        self.last_scan_time = 0
        if not hasattr(self, 'target_scan_field') or instance is not None:
            self.target_scan_field = None
        if not decode:
            self.notify('Erreur: Librairie pyzbar manquante', 'error')
            return
        if platform == 'android':
            from android.permissions import request_permissions, Permission

            def on_permission_result(permissions, grants):
                if grants and grants[0]:
                    Clock.schedule_once(lambda dt: self._launch_camera_widget(), 0.1)
                else:
                    self.notify('Permission Caméra Refusée', 'error')
            request_permissions([Permission.CAMERA], on_permission_result)
        else:
            self._launch_camera_widget()

    def _launch_camera_widget(self):
        self.scanner_start_time = time.time()
        try:
            from kivy.uix.camera import Camera
            self.camera_widget = Camera(play=True, index=0, resolution=(640, 480), allow_stretch=True, keep_ratio=False)
            with self.camera_widget.canvas.before:
                PushMatrix()
                self.rotation = Rotate(angle=-90, origin=self.camera_widget.center)
            with self.camera_widget.canvas.after:
                PopMatrix()
            self.camera_widget.bind(center=lambda instance, value: setattr(self.rotation, 'origin', instance.center))
        except Exception as e:
            self.notify('Erreur chargement caméra', 'error')
            return
        is_single_mode = hasattr(self, 'target_scan_field') and self.target_scan_field is not None
        root_layout = MDBoxLayout(orientation='vertical', spacing=0)
        cam_size = 1.0 if is_single_mode else 0.55
        camera_area = MDFloatLayout(size_hint_y=cam_size)
        self.camera_widget.size_hint = (1, 1)
        self.camera_widget.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
        camera_area.add_widget(self.camera_widget)
        close_btn = MDIconButton(icon='close', icon_size='36sp', md_bg_color=(0, 0, 0, 0.5), theme_text_color='Custom', text_color=(1, 1, 1, 1), pos_hint={'top': 0.96, 'right': 0.96}, on_release=self.close_barcode_scanner)
        camera_area.add_widget(close_btn)
        root_layout.add_widget(camera_area)
        if not is_single_mode:
            list_container = MDCard(orientation='vertical', size_hint_y=0.45, radius=[20, 20, 0, 0], md_bg_color=(1, 1, 1, 1), elevation=0)
            header = MDBoxLayout(size_hint_y=None, height=dp(40), padding=[dp(20), 0])
            self.lbl_scan_count = MDLabel(text='Total scannés: 0', bold=True, theme_text_color='Primary')
            header.add_widget(self.lbl_scan_count)
            list_container.add_widget(header)
            scroll = MDScrollView()
            self.scan_list_widget = MDList()
            scroll.add_widget(self.scan_list_widget)
            list_container.add_widget(scroll)
            btn_ok = MDRaisedButton(text='TERMINER', font_size='18sp', size_hint=(1, None), height=dp(55), md_bg_color=(0, 0.7, 0, 1), elevation=0, on_release=self.finish_continuous_scan)
            list_container.add_widget(btn_ok)
            root_layout.add_widget(list_container)
        self.scan_dialog = ModalView(size_hint=(1, 1), auto_dismiss=False, background_color=(0, 0, 0, 1))
        self.scan_dialog.add_widget(root_layout)
        self.scan_dialog.open()
        self.scan_event = Clock.schedule_interval(self.detect_barcode_frame, 1.0 / 20.0)

    def close_barcode_scanner(self, *args):
        if hasattr(self, 'scan_event') and self.scan_event:
            self.scan_event.cancel()
            self.scan_event = None
        if hasattr(self, 'camera_widget') and self.camera_widget:
            self.camera_widget.play = False
        if hasattr(self, 'scan_dialog') and self.scan_dialog:
            self.scan_dialog.dismiss()
            self.scan_dialog = None
        self.temp_scanned_cart = []
        self.target_scan_field = None

    def detect_barcode_frame(self, dt):
        if not hasattr(self, 'scan_dialog') or not self.scan_dialog or (not self.scan_dialog.parent):
            return
        if not hasattr(self, 'camera_widget') or not self.camera_widget.texture:
            return
        if time.time() - getattr(self, 'scanner_start_time', 0) < 1.2:
            return
        try:
            texture = self.camera_widget.texture
            img_data = PILImage.frombytes(mode='RGBA', size=texture.size, data=texture.pixels).convert('L')
            barcodes = decode(img_data)
            if barcodes:
                code = barcodes[0].data.decode('utf-8').strip()
                if code == self.potential_code:
                    self.consecutive_frames += 1
                else:
                    self.potential_code = code
                    self.consecutive_frames = 1
                if self.consecutive_frames >= 2:
                    if time.time() - self.last_scan_time > 1.5:
                        self.last_scan_time = time.time()
                        self.consecutive_frames = 0
                        self.potential_code = None
                        Clock.schedule_once(lambda dt: self.process_continuous_scan(code))
            else:
                self.consecutive_frames = 0
        except:
            pass

    def process_continuous_scan(self, code):
        if not hasattr(self, 'scan_dialog') or not self.scan_dialog.parent:
            return
        if hasattr(self, 'target_scan_field') and self.target_scan_field:
            self.target_scan_field.text = code
            self.play_sound('success')
            self.close_barcode_scanner()
            return
        prod = None
        for p in self.all_products_raw:
            p_code = str(p.get('barcode', '')).strip()
            if p_code == code:
                prod = p
                break
        if prod:
            for item in self.temp_scanned_cart:
                if str(item['id']) == str(prod['id']):
                    self.play_sound('duplicate')
                    self.show_duplicate_alert(prod.get('name', 'Article'))
                    return
            self.temp_scanned_cart.append(prod)
            self.update_scan_list_ui()
            self.play_sound('success')
        else:
            self.play_sound('error')
            self.show_not_found_alert(code)

    def update_scan_list_ui(self):
        from kivymd.uix.card import MDCard
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDIconButton
        self.scan_list_widget.clear_widgets()
        count = len(self.temp_scanned_cart)
        self.lbl_scan_count.text = f'Articles scannés: {count}'
        if count == 0:
            return
        customer_category = 'Détail'
        if self.selected_entity:
            customer_category = str(self.selected_entity.get('category', 'Détail')).strip()
        sales_modes = ['sale', 'return_sale', 'invoice_sale', 'proforma']
        is_sales_mode = self.current_mode in sales_modes
        for prod in reversed(self.temp_scanned_cart):
            raw_name = self.fix_text(prod.get('name', 'Inconnu'))
            raw_ref_text = str(prod.get('reference', '') or '').strip()
            display_text = raw_name
            if raw_ref_text:
                display_text += f' (Ref: {self.fix_text(raw_ref_text)})'
            final_price = 0.0
            if is_sales_mode:
                base_price = float(prod.get('price', 0) or 0)
                final_price = base_price
                if customer_category == 'Gros':
                    val = float(prod.get('price_wholesale', 0) or 0)
                    if val > 0:
                        final_price = val
                elif customer_category == 'Demi-Gros':
                    val = float(prod.get('price_semi', 0) or 0)
                    if val > 0:
                        final_price = val
                if prod.get('is_promo_active', 0) == 1:
                    promo_exp = str(prod.get('promo_expiry', '')).strip()
                    date_valid = True
                    if len(promo_exp) > 5:
                        try:
                            exp_date = datetime.strptime(promo_exp, '%Y-%m-%d').date()
                            if datetime.now().date() > exp_date:
                                date_valid = False
                        except:
                            pass
                    if date_valid:
                        p_type = prod.get('promo_type', 'fixed')
                        try:
                            p_val = float(prod.get('promo_value', 0))
                        except:
                            p_val = 0.0
                        if p_type == 'fixed':
                            if p_val > 0:
                                final_price = p_val
                        else:
                            final_price = base_price * (1 - p_val / 100)
            else:
                final_price = float(prod.get('purchase_price', prod.get('price', 0)) or 0)
            card = MDCard(orientation='horizontal', size_hint_y=None, height=dp(75), padding=[dp(15), 0, 0, 0], radius=[0], elevation=0, md_bg_color=(1, 1, 1, 1))
            text_box = MDBoxLayout(orientation='vertical', pos_hint={'center_y': 0.5}, adaptive_height=True, spacing=dp(4))
            lbl_name = MDLabel(text=display_text, font_style='Subtitle1', theme_text_color='Primary', shorten=False, max_lines=2, halign='left', adaptive_height=True)
            lbl_price = MDLabel(text=f'Prix: {final_price:.2f} DA', font_style='Caption', theme_text_color='Secondary', bold=True, halign='left', adaptive_height=True)
            text_box.add_widget(lbl_name)
            text_box.add_widget(lbl_price)
            del_btn = MDIconButton(icon='delete', theme_text_color='Custom', text_color=(0.9, 0, 0, 1), pos_hint={'center_y': 0.5}, icon_size='24sp', on_release=lambda x, p=prod: self.remove_temp_item(p))
            card.add_widget(text_box)
            card.add_widget(del_btn)
            sep = MDBoxLayout(size_hint_y=None, height=dp(1), md_bg_color=(0.95, 0.95, 0.95, 1))
            self.scan_list_widget.add_widget(card)
            self.scan_list_widget.add_widget(sep)

    def finish_continuous_scan(self, instance):
        if not hasattr(self, 'temp_scanned_cart') or not self.temp_scanned_cart:
            self.close_barcode_scanner()
            return
        items_to_add = list(self.temp_scanned_cart)
        self.close_barcode_scanner()
        count = 0
        for product in items_to_add:
            self.add_scanned_item_to_cart(product)
            count += 1
        if count > 0:
            self.notify(f'{count} Articles ajoutés au panier', 'success')
        self.temp_scanned_cart = []

    def add_scanned_item_to_cart(self, product):
        try:
            current_sales_mode = getattr(self, 'user_sales_mode', 'store')
            if current_sales_mode == 'truck' and self.current_mode in ['sale', 'invoice_sale', 'proforma']:
                available_stock = float(product.get('stock', 0) or 0)
                if available_stock > -900000:
                    in_cart_qty = 0
                    for item in self.cart:
                        if str(item['id']) == str(product['id']):
                            in_cart_qty += float(item.get('qty', 0))
                    if in_cart_qty + 1 > available_stock:
                        self.play_sound('error')
                        self.notify(f"Stock VAN insuffisant : {product.get('name')}", 'error')
                        return
            sales_modes = ['sale', 'return_sale', 'invoice_sale', 'proforma']
            is_sales_mode = self.current_mode in sales_modes
            final_price = 0.0
            if is_sales_mode:
                base_price = float(product.get('price', 0) or 0)
                final_price = base_price
                if self.selected_entity:
                    cat = str(self.selected_entity.get('category', 'Détail')).strip()
                    if cat == 'Gros':
                        w_price = float(product.get('price_wholesale', 0) or 0)
                        if w_price > 0:
                            final_price = w_price
                    elif cat == 'Demi-Gros':
                        s_price = float(product.get('price_semi', 0) or 0)
                        if s_price > 0:
                            final_price = s_price
                raw_active = product.get('is_promo_active', 0)
                is_promo = str(raw_active) == '1' or raw_active == 1
                if is_promo:
                    promo_exp = str(product.get('promo_expiry', '')).strip()
                    date_valid = True
                    if len(promo_exp) > 5:
                        try:
                            exp_date = datetime.strptime(promo_exp, '%Y-%m-%d').date()
                            if datetime.now().date() > exp_date:
                                date_valid = False
                        except:
                            pass
                    if date_valid:
                        try:
                            p_val = float(product.get('promo_value', 0))
                        except:
                            p_val = 0.0
                        p_type = str(product.get('promo_type', 'fixed'))
                        if p_type == 'fixed':
                            if p_val > 0:
                                final_price = p_val
                        else:
                            final_price = base_price * (1 - p_val / 100)
            else:
                cost_price = float(product.get('purchase_price', 0) or 0)
                if cost_price == 0:
                    cost_price = float(product.get('price', 0) or 0)
                final_price = cost_price
            qty_to_add = 1.0
            found = False
            for item in self.cart:
                if str(item['id']) == str(product['id']):
                    item['qty'] += qty_to_add
                    item['price'] = final_price
                    found = True
                    break
            if not found:
                new_item = {'id': product['id'], 'name': product['name'], 'price': final_price, 'qty': qty_to_add, 'original_unit_price': final_price, 'tva': 0, 'has_promo': False}
                if product.get('product_ref'):
                    new_item['product_ref'] = product.get('product_ref')
                self.cart.append(new_item)
            self.update_cart_button()
        except Exception as e:
            print(f'Add Cart Error: {e}')

    def remove_temp_item(self, product_to_remove):
        if product_to_remove in self.temp_scanned_cart:
            self.temp_scanned_cart.remove(product_to_remove)
            self.update_scan_list_ui()

    def show_duplicate_alert(self, product_name):
        if hasattr(self, 'is_showing_alert') and self.is_showing_alert:
            return
        self.is_showing_alert = True

        def close_alert(*args):
            self.dup_dialog.dismiss()
            self.is_showing_alert = False
        short_name = self.fix_text(product_name)[:30]
        self.dup_dialog = MDDialog(title='Déjà scanné !', text=f'Le produit:\n[b]{short_name}[/b]\n\nest déjà dans la liste.', buttons=[MDRaisedButton(text='OK', md_bg_color=(0.8, 0, 0, 1), on_release=close_alert)], size_hint=(0.85, None))
        self.dup_dialog.open()

    def show_not_found_alert(self, code):
        if hasattr(self, 'is_showing_alert') and self.is_showing_alert:
            return
        self.is_showing_alert = True

        def close(*args):
            self.not_found_dialog.dismiss()
            self.is_showing_alert = False
        self.not_found_dialog = MDDialog(title='Introuvable !', text=f"Le code-barres:\n[b]{code}[/b]\n\nn'existe pas dans la base de données.", buttons=[MDRaisedButton(text='OK', md_bg_color=(0.2, 0.2, 0.2, 1), on_release=close)], size_hint=(0.85, None))
        self.not_found_dialog.open()

    def show_zoomed_image(self, image_source, title_text='Image'):
        if not image_source:
            return
        content = MDFloatLayout(size_hint_y=None, height=dp(400))
        img = FitImage(source=image_source, pos_hint={'center_x': 0.5, 'center_y': 0.5}, radius=[15], size_hint=(1, 1))
        content.add_widget(img)
        close_btn = MDIconButton(icon='close-circle', theme_text_color='Custom', text_color=(1, 1, 1, 1), icon_size='40sp', pos_hint={'top': 1, 'right': 1}, on_release=lambda x: self.zoom_dialog.dismiss())
        content.add_widget(close_btn)
        self.zoom_dialog = MDDialog(title=title_text, type='custom', content_cls=content, size_hint=(0.9, None))
        self.zoom_dialog.open()

    def on_resume(self):
        if platform == 'android':
            self.start_gps_service()
        return True

    def on_stop(self):
        if platform == 'android' and hasattr(self, 'location_manager') and self.location_manager:
            try:
                if hasattr(self, 'location_listener') and self.location_listener:
                    self.location_manager.removeUpdates(self.location_listener)
            except:
                pass

    def start_gps_service(self):
        if platform != 'android':
            return
        if not hasattr(self, 'kalman_filter'):
            self.kalman_filter = KalmanLatLon(Q_metres_per_second=3)
        from android.permissions import request_permissions, Permission

        def _start_native_gps(permissions, grants):
            if not grants or not grants[0]:
                self.notify('Permission GPS refusée', 'error')
                return
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                LocationManager = autoclass('android.location.LocationManager')
                PowerManager = autoclass('android.os.PowerManager')
                activity = PythonActivity.mActivity
                self.location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
                if not hasattr(self, 'location_listener'):
                    self.location_listener = NativeLocationListener(self.on_native_location)
                self.location_manager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 3000, 5.0, self.location_listener)
                self.location_manager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 3000, 5.0, self.location_listener)
                power_manager = activity.getSystemService(Context.POWER_SERVICE)
                if not hasattr(self, 'wake_lock') or self.wake_lock is None:
                    self.wake_lock = power_manager.newWakeLock(1, 'MagPro:GPSLock')
                    self.wake_lock.acquire()
                print('[GPS] Service GPS natif démarré avec succès')
            except Exception as e:
                print(f'[GPS Error] Echec démarrage GPS natif: {e}')
                self.notify('Erreur initialisation GPS', 'error')
        request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION], _start_native_gps)

    def on_fused_location(self, location):
        try:
            if location.isFromMockProvider():
                return
            raw_lat = location.getLatitude()
            raw_lon = location.getLongitude()
            accuracy = location.getAccuracy()
            speed = location.getSpeed() * 3.6
            timestamp_ms = location.getTime()
            if accuracy > 40:
                return
            filtered_lat, filtered_lon = self.kalman_filter.process(raw_lat, raw_lon, accuracy, timestamp_ms)
            timestamp_sec = timestamp_ms / 1000.0
            date_str = str(datetime.now().date())
            key = f'{int(timestamp_sec)}_{random.randint(100, 999)}'
            self.gps_store.put(key, lat=filtered_lat, lon=filtered_lon, speed=speed, accuracy=accuracy, timestamp=timestamp_sec, date=date_str, synced=False, is_mock=False)
            self.sync_gps_data()
        except Exception as e:
            print(f'Error processing fused location: {e}')

    def on_native_location(self, location):
        try:
            if not self.is_better_location(location, getattr(self, 'current_best_location', None)):
                return
            self.current_best_location = location
            lat = location.getLatitude()
            lon = location.getLongitude()
            accuracy = location.getAccuracy()
            speed = location.getSpeed() * 3.6
            provider = location.getProvider()
            if accuracy > 50:
                return
            timestamp = time.time()
            date_str = str(datetime.now().date())
            key = f'{int(timestamp)}_{random.randint(100, 999)}'
            self.gps_store.put(key, lat=lat, lon=lon, speed=speed, accuracy=accuracy, timestamp=timestamp, date=date_str, synced=False)
            self.sync_gps_data()
        except Exception as e:
            print(f'Error parsing location: {e}')

    def sync_gps_data(self):
        if not self.is_server_reachable or self.sync_paused:
            return
        if getattr(self, 'is_gps_syncing', False):
            return
        if not self.current_user_name:
            if self.store.exists('credentials'):
                self.current_user_name = self.store.get('credentials').get('username')
            else:
                return
        unsynced_keys = [k for k in self.gps_store.keys() if not self.gps_store.get(k).get('synced', False)]
        if not unsynced_keys:
            return
        unsynced_keys.sort(key=lambda k: self.gps_store.get(k)['timestamp'])
        BATCH_SIZE = 50
        batch_keys = unsynced_keys[:BATCH_SIZE]
        batch_payload = []
        for key in batch_keys:
            item = self.gps_store.get(key)
            batch_payload.append({'username': self.current_user_name, 'lat': item['lat'], 'lon': item['lon'], 'speed': item.get('speed', 0), 'timestamp': item['timestamp'], 'key': key})
        self.is_gps_syncing = True
        url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/update_location'

        def on_success(req, res):
            for item in batch_payload:
                k = item['key']
                if self.gps_store.exists(k):
                    stored = self.gps_store.get(k)
                    stored['synced'] = True
                    self.gps_store.put(k, **stored)
            self.is_gps_syncing = False
            if len(unsynced_keys) > BATCH_SIZE:
                Clock.schedule_once(lambda dt: self.sync_gps_data(), 0.1)

        def on_fail(req, err):
            print(f'[GPS Batch] Sync failed: {err}')
            self.is_gps_syncing = False
        UrlRequest(url, req_body=json.dumps(batch_payload), req_headers={'Content-type': 'application/json'}, method='POST', on_success=on_success, on_failure=on_fail, on_error=on_fail, timeout=8)

    def is_better_location(self, location, current_best_location):
        if current_best_location is None:
            return True
        TIME_DELTA = 1000 * 60 * 2
        time_delta = location.getTime() - current_best_location.getTime()
        is_significantly_newer = time_delta > TIME_DELTA
        is_significantly_older = time_delta < -TIME_DELTA
        is_newer = time_delta > 0
        if is_significantly_newer:
            return True
        elif is_significantly_older:
            return False
        accuracy_delta = int(location.getAccuracy() - current_best_location.getAccuracy())
        is_less_accurate = accuracy_delta > 0
        is_more_accurate = accuracy_delta < 0
        is_significantly_less_accurate = accuracy_delta > 200
        is_from_same_provider = False
        if location.getProvider() and current_best_location.getProvider():
            is_from_same_provider = location.getProvider() == current_best_location.getProvider()
        if is_more_accurate:
            return True
        elif is_newer and (not is_less_accurate):
            return True
        elif is_newer and (not is_significantly_less_accurate) and is_from_same_provider:
            return True
        return False

    def sync_gps_single(self, key, lat, lon, speed, timestamp):
        if not self.is_server_reachable or self.sync_paused:
            return
        if not self.current_user_name:
            if self.store.exists('credentials'):
                self.current_user_name = self.store.get('credentials').get('username')
            else:
                return
        url = f'http://{self.active_server_ip}:{DEFAULT_PORT}/api/update_location'
        payload = {'username': self.current_user_name, 'lat': lat, 'lon': lon, 'speed': speed, 'timestamp': timestamp}

        def on_success(req, res):
            if self.gps_store.exists(key):
                item = self.gps_store.get(key)
                item['synced'] = True
                self.gps_store.put(key, **item)
        UrlRequest(url, req_body=json.dumps(payload), req_headers={'Content-type': 'application/json'}, method='POST', on_success=on_success, timeout=3)

    def on_keyboard(self, window, key, scancode, codepoint, modifier):
        if key == 27:
            self.handle_back_button()
            return True
        return False

    def handle_back_button(self):
        if hasattr(self, 'scan_dialog') and self.scan_dialog:
            self.close_barcode_scanner()
            return
        dialogs = ['dialog', 'ae_dialog', 'pay_dialog', 'entity_dialog', 'mgmt_dialog', 'srv_dialog', 'pending_dialog', 'bt_dialog', 'filter_dialog', 'options_dialog', 'cat_dialog', 'auth_dialog', 'toggle_dialog', 'logout_diag', 'stop_sync_dialog', 'confirm_del_dialog', 'overpay_dialog', 'debt_dialog']
        for d_name in dialogs:
            d = getattr(self, d_name, None)
            if d:
                d.dismiss()
                setattr(self, d_name, None)
                return
        current_screen = self.sm.current
        if current_screen == 'cart':
            self.back_to_products()
        elif current_screen == 'products':
            self.go_back()
        elif current_screen == 'dashboard' or current_screen == 'login':
            self.show_exit_confirmation()

    def show_exit_confirmation(self):
        self.exit_dialog = MDDialog(title='Attention', text="Voulez-vous vraiment quitter l'application ?", buttons=[MDFlatButton(text='NON', on_release=lambda x: self.exit_dialog.dismiss()), MDRaisedButton(text='OUI, QUITTER', md_bg_color=(0.8, 0, 0, 1), text_color=(1, 1, 1, 1), on_release=self.stop)])
        self.exit_dialog.open()

    def cleanup_old_gps_logs(self):
        try:
            today_str = str(datetime.now().date())
            keys_to_delete = []
            for key in self.gps_store.keys():
                item = self.gps_store.get(key)
                item_date = item.get('date')
                if item_date != today_str:
                    keys_to_delete.append(key)
            for k in keys_to_delete:
                self.gps_store.delete(k)
            if keys_to_delete:
                print(f'[GPS] Cleaned {len(keys_to_delete)} old points.')
        except Exception as e:
            print(f'[GPS] Cleanup Error: {e}')

if __name__ == '__main__':
    try:
        StockApp().run()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print('CRITICAL ERROR:', error_msg)
        try:
            with open('crash_log.txt', 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            files_dir = PythonActivity.mActivity.getExternalFilesDir(None).getAbsolutePath()
            log_path = os.path.join(files_dir, 'magpro_crash.txt')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(error_msg)
        except:
            pass
