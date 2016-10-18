.. All the ways of controlling MUSCIMarker

.. include:: shortcuts

.. _controls:

Controlling MUSCIMarker
=======================

Here is an overview of all the things you can do with MUSCIMarker.

We'll organize this description into some groups:

#. Control the application using fixed interface elements (mostly buttons)
#. Move and zoom the annotated image
#. Use tools to create annotations
#. Interact with annotations


Fixed interface elements
------------------------

Interface actions mainly consist of pressing buttons. As you know from
the :ref:`tutorial`, the MUSCIMarker interface has three parts that
expose ways of controlling the application: the *command sidebar* on the right,
the *tool selection* sidebar on the left, and the *action bar* on the bottom.

.. note::
    We call these control elements "fixed", because no matter what the state
    of the annotation, they don't change.

Command sidebar
^^^^^^^^^^^^^^^

This sidebar generally controls the annotation inputs and outputs: what
image you are annotating, saving & loading the annotation, selecting
the MLClass that should be annotated, hiding/showing the current annotation,
etc.

Going from the top down:

**Select MLClassList** The MLClass list is where we define what the symbol
classes are. This button shows a file loading dialog where you can choose
which set of symbol classes to use.

.. warning::

    Changing the MLClassList invalidates all of the current annotation!
    Do not do this unless explicitly instructed to. MUSCIMarker ships with
    a default MLClassList file that should be good enough.

**Select Grammar** The grammar defines what symbol relationships are
possible. This button shows a file loading dialog where you can choose
which set of rules to use.

.. warning::

    Changing the grammar invalidates all the current relationships between
    the annotated objects! Do not do this unless explicitly instructed to.
    MUSCIMarker ships with a default grammar that should be good enough.


