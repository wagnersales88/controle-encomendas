[app]

title = Controle de Encomendas
package.name = controleencomendas
package.domain = org.controleencomendas

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json

version = 1.0

requirements = python3,kivy

orientation = portrait
fullscreen = 0

android.api = 35
android.minapi = 24
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions = CAMERA


[buildozer]

log_level = 2
warn_on_root = 1
