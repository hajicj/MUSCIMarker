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
the *tool sidebar* on the left, and the *action bar* on the bottom.

.. note::
    We call these control elements "fixed", because no matter what the state
    of the annotation, they don't change.

.. _controls_command_sidebar:

Command sidebar
^^^^^^^^^^^^^^^

This sidebar generally controls the annotation inputs and outputs: what
image you are annotating, saving & loading the annotation, selecting
the MLClass that should be annotated, hiding/showing the current annotation,
etc.

.. note::

    All file loading dialogues will be opened by default to pointing
    to the directory where the corresponding currently loaded file is
    (so, if you are loading an image, the loading dialog will show
    you images from the same directory as the image you are annotating).

We now list what the individual elements of the command sidebar do.
Going from the top down:

**Select MLClassList** The MLClass list is where we define what the symbol
classes are. This button shows a file loading dialog where you can choose
which set of symbol classes to use. (The name of the last loaded MLClass list
file is displayed in grey beneath the topmost buttons.)

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


**Select MLClass** Under the "Select MLClass" label, the name of the current
class is set. New CropObjects that you add to the annotation will belong
to the current class. Clicking on the button with the class name will open
a list of available classes. (You can scroll or click+drag the list.)

Selecting from this list is *not* the only way to set the current class.
You can also *clone* the class of a selected CropObject -- take something
you already annotated and set *its* class as the current class
(see :ref:`controls_selection_shortcuts`).

**Select image file** If you want to change the image that you are annotating,
click this button. A file loading dialog will appear; navigate to the desired
image and select Load (or double-click the filename).

.. warning::

    Loading a new image will clear all current annotations. Make sure
    you have exported your work!

**Import CropObjectList file** The CropObject list file is an XML file that
contains the current state of the annotations: all the selected objects
and relationships between them. This button opens a file loading dialog
that allows you to import a CropObject list file; navigate to the desired
file and select Load (or double-click the filename).

.. note:: **This is the way to load your previous work.**

The name of the last loaded MLClass list file is displayed in grey beneath
the CropObjectList import/export buttons.

.. warning::

    Loading a new CropObject list will clear all current annotations. Make
    sure you have exported your work!

**Export CropObjectList file** Save the current state of the annotation
to a CropObject list file (see the explanation for Import CropObjectList file).
A file save dialog will appear. A file name is suggested automatically
(in the white text input field, bottom of the dialog), to correspond to the
filename of the current image.

.. note:: **This is the way to save your work.** Do this often.


**Counters.** Next, you see how may objects and relationships between
objects (Attachments) are currently annotated. If you're not sure that
your action actually added or deleted some object or reltionship, take
a look at the numbers.


**Clear CropObjects.** Delete all current annotations. A confirmation dialog
will pop up, so that you don't click this by accident. This cannot be undone!


**Hide/Show CropObjects.** Hiding CropObjects means that you will not see
them and won't be able to interact with the annotations. You will, however,
still be able to interact with the relationships. This may be useful when
there is a lot of CropObjects and you interact with them accidentally.

**Hide/Show Relationships.** Just like the previous buttons, but operates
on the relationships. Useful if the Relationships get in the way of working
with CropObjects.


.. _control_tools:

Tools
^^^^^

The *Tool sidebar* lists the available annotation tools. Tools allow you
to add objects and relationships and other interaction with the image
and annotations.

We will now describe the available tools.




.. _controls_selection:

Selecting annotations
^^^^^^^^^^^^^^^^^^^^^


.. _controls_selection_shortcuts_cropobjects:

Editing a selection of CropObjects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^



.. _controls_selection_shortcuts_graph:

Editing a selection of Attachments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

