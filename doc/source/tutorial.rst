.. _tutorial:

.. include:: shortcuts

Tutorial
--------

Welcome to the MUSCIMarker tutorial! Here, you will learn
how to use MUSCIMarker to annotate symbols in a musical score.

.. note:: The app is in its alpha stage. There are inconveniencies,
          bugs, weird behavior, etc. -- we'd be happy if you report
          these to |contact_email|.

Start MUSCIMarker
^^^^^^^^^^^^^^^^^

If you have MUSCIMarker in a virtual environment, activate the environment.
Navigate to the folder that contains the ``main.py`` file in the console
and run::

  python main.py

A window with the app will appear:

.. image:: images/screenshots/first_startup_screen.png

Let's walk through the interface.
The main part in the middle is occupied by the image that we annotate:

.. image:: images/screenshots/ui_overview_image.png

For marking the symbols in the score, you'll use a bunch of tools:

.. image:: images/screenshots/ui_overview_toolkit.png

To load an image, export the annotation, or to import a different
annotation, use the commands on the right-hand side:

.. image:: images/screenshots/ui_overview_commands.png

There are some convenience commands along the bottom of the screen,
such as centering the image, backing up your work, or accessing
the app settings:

.. image:: images/screenshots/ui_overview_morecommands.png

And that includes the all-important Exit button!

.. image:: images/screenshots/ui_overview_exit.png


Exploring the image
^^^^^^^^^^^^^^^^^^^

You can zoom and move the image around. MUSCIMarker works both on a desktop
and on a smartphone or tablet, but the usage is a little different.

.. warning:: There is currently no tested implementation of keyboard shortcuts
             on mobile platforms!

On a tablet, the image responds to the usual touch commands: drag to move
and pinch to zoom. On a desktop, you can drag & drop to move the image around
as usual. For zooming, we'll need to "simulate" one finger by right-clicking
anywhere on the image. A red dot should appear:

.. image:: images/screenshots/ui_moving_rightclick.png

Dragging now zooms the image, instead of moving.

.. image:: images/screenshots/ui_moving_clickanddrag.png

...

.. image:: images/screenshots/ui_moving_zoomed.png

The red dot is like having one finger pressed against that point in the image,
and dragging with the mouse works like the second
finger in the pinch-to-zoom gesture.
Play around with the desktop zoom for a bit, you'll get the hang of it soon!

Once you're done zooming, just left-click the red dot -- the "fake finger" --
to exit zooming mode.

.. image:: images/screenshots/ui_moving_stopzooming.png

If you get lost -- hey, it happens -- or anytime you want to jump
back to the original scale, use the CENTER command on the bottom pane.

.. image:: images/screenshots/ui_moving_center.png

The annotated image will scale back to its original size and center
itself in the editor window.

You'll probably be spending most of your time with MUSCIMarker zoomed
in, so spend a minute getting used to navigating the image before we
proceed to the next step: annotating.


Annotating
^^^^^^^^^^
