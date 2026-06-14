[app]
title = MAGAPLANT
package.name = magaplant
package.domain = org.magaplant

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf

version = 1.0

requirements = python3,kivy,pillow,pyjnius

orientation = portrait

fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.api = 34
android.minapi = 23
android.ndk = 25b

presplash.filename = %(source.dir)s/data/presplash.png
icon.filename = %(source.dir)s/data/icon.png

android.archs = arm64-v8a, armeabi-v7a

android.enable_androidx = True

#p4a.branch = master

log_level = 2

android.accept_sdk_license = True