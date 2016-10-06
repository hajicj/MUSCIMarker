.. include:: shortcuts

.. _running:

Running MUSCIMarker
===================

When you want to run MUSCIMarker (assuming you followed the installation
instructions with Anaconda):

#. Open the command line.
#. Only if you made the special Python 2 conda environment: ``source activate py27``
#. ``cd MUSCIMarker``
#. ``git pull`` to update to the latest version.
#. ``cd MUSCIMarker`` again (there are two directories called
   ``MUSCIMarker``, one inside the other).
#. Run ``python main.py`` and the MUSCIMarker window should open.

If you are not sure that the ``git pull`` step finished successfully,
try running ``git pull`` again. If your MUSCIMarker is correctly
updated, it should tell you that it is ``already up to date``.

More generally
--------------

If the above doesn't apply because you installed MUSCIMarker in your own
way, we assume you know what you are doing. In that case, to run
MUSCIMarker, just run ``main.py`` from the ``MUSCIMarker/MUSCIMarker``
directory.