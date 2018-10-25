# MUSCIMarker

Tool for annotating objects in musical scores.

[![Documentation Status](https://readthedocs.org/projects/muscimarker/badge/?version=latest)](http://muscimarker.readthedocs.io/en/latest/)

## Tutorial

...is in the documentation:  http://muscimarker.readthedocs.io/en/latest/tutorial.html

*This work is supported by the Czech Science Foundation, grant number P103/12/G084.*

## Build the distributable binary for Windows

Basically follow the tutorial from the [Kivy website](https://kivy.org/docs/guide/packaging-windows.html):

- Make sure you have all dependencies installed
- From within `[GIT_ROOT]/MUSCIMarker/MUSCIMarker` run `python -m PyInstaller --name MUSCIMarker main.py`
- Navigate to the `MUSCIMarker.spec` file and add `from kivy.deps import sdl2, glew` to the top and the following two statements to the COLLECT or EXE script:
    - `Tree('[GIT_ROOT]/MUSCIMarker/MUSCIMarker')`
    - `*[Tree(p) for p in (sdl2.dep_bins + glew.dep_bins)]`
- Run `python -m PyInstaller MUSCIMarker.spec`