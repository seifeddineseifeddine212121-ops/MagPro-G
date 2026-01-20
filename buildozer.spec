[app]
title = MagPro
package.name = MagPro
package.domain = org.magpro
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 7.1.0
requirements = python3,kivy,kivymd,requests,urllib3,pillow,arabic-reshaper,python-bidi==0.4.2,six,future,certifi,chardet,idna,pyzbar,libzbar,android,jnius,plyer
icon.filename = apk_icon.png
orientation = portrait
fullscreen = 0
android.permissions = INTERNET, ACCESS_NETWORK_STATE, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, BLUETOOTH_SCAN, ACCESS_COARSE_LOCATION, ACCESS_FINE_LOCATION, CAMERA, WAKE_LOCK, FOREGROUND_SERVICE, FOREGROUND_SERVICE_LOCATION
android.api = 34
android.minapi = 21
android.enable_androidx = True
android.gradle_dependencies = androidx.core:core:1.10.1
android.accept_sdk_license = True
android.skip_update = False
android.logcat_filters = *:S python:D
android.archs = arm64-v8a
android.allow_backup = True
android.debug_artifact = apk
android.manifest.application_attributes = android:usesCleartextTraffic="true"

[buildozer]
log_level = 2
warn_on_root = 1
