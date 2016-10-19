.. All the ways of controlling MUSCIMarker

.. include:: shortcuts

.. _controls:

Controlling MUSCIMarker
=======================

Here is an overview of all the things you can do with MUSCIMarker.

We'll organize this description into some groups:

#. :ref:`controls_fixed`: Control the application using fixed interface
   elements (mostly buttons)
#. :ref:`controls_navigation`: Move and zoom the annotated image
#. :ref:`controls_tools`: Use tools to create and edit annotations
#. :ref:`controls_editing`: Interact with annotations


.. note::

    **Quick Refresher**

    There are two kinds of annotations in MUSCIMarker: *objects* (CropObjects,
    displayed as colored rectangles) and *relationships* (displayed as lines
    connecting the CropObjects). Relationships connect objects.

    The annotations can be *selected*. If an object is selected, it looks
    brighter. If a relationship is selected, it gets emphasized.


.. _controls_fixed:

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


.. _controls_action_bar:

Action Bar
^^^^^^^^^^

The *Action bar* on the bottom provides some convenience commands that do not
interact with the state of the annotation. Going from left to right:

**Center** If you get lost while zooming around the image, this button
will center the image and scale it back to its initial size.

**Backup** Manually create a snapshot of the current state of the application.
Backups happen automatically in the background every 20 seconds (you can change
that in the Settings).

.. warning::

    **This is not a substitute for saving your work!** Backup and Recover
    are here to help with application crashes. There is only ever one snapshot
    saved deep among the internal files of MUSCIMarker, so it's not a poor
    man's Undo, either!

**Recover** Load the annotation state from the snapshot. Try to do this when
you re-open MUSCIMarker after a crash - it might help you not lose some work
you didn't save using the "Export CropObjectList file" dialog. However,
there is no guarantee that this will work! Perhaps the auto-snapshot was
being saved while MUSCIMarker was crashing, so it can't be recovered!
**The Backup/Recover mechanism is not a substitute for saving your work.**

**Settings** Opens the Settings panel. Currently, you do not ever need to go
there.

**Exit** This is the correct way of exiting the application.


.. _controls_tools:

Tools
^^^^^

The *Tool sidebar* lists the available annotation tools. Tools allow you
to add objects and relationships and other interaction with the image
and annotations.

.. tip::

    If you are not sure how a tool works from the description,
    experiment with it on the default image.

Only one tool can be selected at a time. If there are no selected annotations,
pressing "Escape" unselects the current tool.

We will now describe the available tools. Going from the top down:

**Trimmed Lasso** Draw a lasso around an object in the image. Once you release,
adds the selection as a new CropObject annotation. Ignores background (black):
you do *not* have to accurately trace around an object's border with
the background. However, you need to be accurate when objects overlap.
See the :ref:`guidelines`.

**Connected Component** Draw a rectangle. Upon release, will add a CropObject
that consists of all "connected components" of the foreground: contignuous
non-black segments. This allows quickly adding CropObjects when the visual
object that you want to mark does not overlap any other visual objects
in the image. If it does overlap, however, you will need to use the Trimmed
Lasso tool, because the object needs to be accurately marked in the overlapping
part.

.. note::

    When you first use this tool after loading an image, it will take
    a while to pre-compute where the connected components are. Subsequent
    uses, however, will be quick.

**Object Selection** Draw a rectangle and select all CropObjects that overlap
this rectangle. Handy for adding relationships: quickly select groups
of CropObjects with this tool and press "p" to create relationships.

**Relationship Selection** Draw a rectangle, find all CropObjects that overlap
this rectangle (like the Object Selection tool), and select their *Relationships*.
This is useful for mass-editing Relationships.

.. note::

    It's not quite perfect: this way, it only allows you to select either
    *all* the relationships of an object, or *none* of them.



.. _controls_selection:

Selecting annotations
---------------------

**Click an annotation.** This is the basic operation that applies to both
objects and relationships. Clicking toggles whether an annotation is selected
(clicking a not-selected annotation selects it, clicking a selected annotation
unselects it).

.. note::

    As the objects are heaped one on top of the other, sometimes
    you cannot click an object because it is entirely hidden by another
    one. However, if you select the top annotation and pres "b", it gets sent
    to the bottom and you will be able to click the annotation you want.

    If *relationships* are what makes the annotation un-clickable, you can
    hide them with the "Hide Relationships" button in the command sidebar.


**Tools for selecting.** The "Obj. Select" and "Rel. Select" tools are good
for mass-selecting objects and relationships in a given region.

**Deselecting** Press "Escape" to deselect all annotations. (Pressing it again
will attempt to unselect the current tool as well.)


.. _controls_editing:

Editing selectied annotations
-----------------------------

Once you are happy with which annotations are selected, you can use some
keyboard shortcuts that act on the selected annotations. Some keyboard
shortcuts only work on *objects*, and some only work on *relationships*.
A few work on both:


=============      ===========================================================
**Escape**         De-select everything in the selection.
**Backspace**      Delete the selected annotations. (Careful! No Undo!)


.. note::

    Deleting an object also deletes all its relationships.


.. _controls_selection_shortcuts_cropobjects:

Editing a selection of objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following keyboard shortcuts work on selected objects:

===========         ===========================================================
**p**               Find all possible relationships among the selected objects.
**alt+Backspace**   Delete all relationships of selected objects.


.. _controls_selection_shortcuts_graph:

Editing a selection of Attachments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

