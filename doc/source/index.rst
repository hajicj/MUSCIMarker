.. MUSCIMarker documentation master file, created by
   sphinx-quickstart on Wed Sep 21 12:04:51 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. include:: shortcuts


MUSCIMarker
===========

MUSCIMarker is an app that marks object locations on the page.
The name stands for "MUsical SCore Image Marker": the primary
purpose of the app is to mark locations of notation symbols
in images of musical scores. (Although it can in principle support
any kind of 2-D object marking.)

.. todo:: Fancy screenshot

Installation
------------

.. note:: As it stands now, we don't have installation packages that would
          work for people who don't have Python. We're working on it, though.

.. note:: You need Python 2.7 -- although most of MUSCIMarker should
          be compatible with Python 3, we haven't yet tested this.

You will need the following Python packages for MUSCIMarker to run:

* |Kivy|_ (The GUI toolkit that MUSCIMarker was built with)
* |lxml|_ (Parsing, writing and manipulating XML files)
* |numpy|_ (Fast math for Python)
* |scikit-image|_ (Image manipulation and rendering)

..  todo::
   Because installing all these yourself is tedious, we have prepared
   a virtual environment that you can use with |conda|_. (If you're not
   using |conda| yet, we recommend that you start using it!)

Installing on Windows
^^^^^^^^^^^^^^^^^^^^^

.. warning:: Proposed; needs testing.

We strongly recommend installing the |Anaconda|_ distribution.

To install Kivy, follow the Windows installation instruction.


What now?
---------

Once you install MUSCIMarker, go through the :ref:`tutorial`.
It will teach you how to use MUSCIMarker, and introduce the most
important concepts.

The `User Manual`_ then contains details.

Contact
-------

MUSCIMarker is developed at the |UFAL|_.
Usage questions should be addressed to ``hajicj@ufal.mff.cuni.cz``
and bugs/crashes should be reported through the project's
|GitHub|_ issue tracker.



Contents:
---------

.. toctree::
   :maxdepth: 2
   :numbered:
   :titlesonly:

   Tutorial <tutorial>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

