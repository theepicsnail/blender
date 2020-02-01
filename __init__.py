bl_info = {
    "name": "Snail",
    "category": "Object",
    'blender': (2, 80, 0),
}

import os, sys

file_dir = os.path.dirname(__file__)
if file_dir not in sys.path:
    sys.path.append(file_dir)

import FixQuads
import FixQuadStrip
import SelectLinkedQuads
import RemoteDebugger
import StarPoints
import ZigZagSelect


def register():
    FixQuads.register()
    FixQuadStrip.register()
    SelectLinkedQuads.register()
    RemoteDebugger.register()
    StarPoints.register()
    ZigZagSelect.register()


def unregister():
    FixQuads.unregister()
    FixQuadStrip.unregister()
    SelectLinkedQuads.unregister()
    RemoteDebugger.unregister()
    StarPoints.unregister()
    ZigZagSelect.unregister()
