.. MUSCIMarker musical notation primitives annotation guidelines.

.. include:: shortcuts

.. _guidelines:

Annotation Guidelines
=====================

We learned in the :ref:`tutorial` how to control the MUSCIMarker
application and use it to annotate objects in images. Now, we will
talk about how to specifically annotate musical notation, so that
the data you are creating will be useful for optical music recognition
experiments.

.. note::

    Whereas the rest of the MUSCIMarker documentation technically applies
    to any ``MLClassList`` you might annotate, this section is specifically
    designed to cover how to properly annotate the musical notation primitives
    supplied with the annotation packages: ``mff-muscima-mlclasses-primitives.xml``.

**Accurate annotation is absolutely critical to the success of our research.**
Therefore, you are expected to understand these guidelines fully.
Mistakes may happen, of course, but if they happen at a frequency
above some reasonable rate, you are going to see that reflected
in your compensation.

**If you do not understand something, please ask!**
Questions, requests for clarifications (especially accompanied
by pictures of the problematic area) and generally communicating
with us will never be discouraged. The e-mail address to direct
questions to is ``hajicj@ufal.mff.cuni.cz``


Guiding principles
------------------

Thee are a few things to understand first, before we dive into
the specifics.

**Pixels matter.** Although you only see rectangles on the screen
when you annotate objects, in the background, the exact objects
are recorded: each pixel within the colored rectangle that you see
has a Belongs/Doesn't Belong label.

**Background does not matter.** In black-and-white images, only
the white pixels are ever recorded as belonging to a symbol.

**All pixels in a symbol should be marked.** So if you get intersections,
such as between a stem and a beam, the intersection pixels just belong
to both symbols. Belonging to one symbol does not exclude a pixel
from belonging to another symbol. Intersections happen all the time.

**Not all non-background pixels are part of a symbol.** There may be
non-background pixels that are a result of the writer's mistake,
or artifacts of the input mode (e.g. stylus on a tablet - sometimes,
the tablet software might have preferred to make 90-degree corners
or straight lines where it's obvious there should be a curve...).
It's perfectly fine to leave these extra pixels out of the symbols
you are marking. In fact, including such extra pixels would be
a mistake.

**Layered annotation.** Sometimes (e.g. grace notes, key signatures),
you will be asked to annotated the same thing with more markings.
For instance, a correct annotation of the  key signature for A major
has three ``sharp`` annotations and a ``key_signature`` annotation
that covers all these symbols. This is because musical notation has
several layers at which it needs to be annotated: we need to know,
at the same time, that the symbols for key signatures are sharps,
and that these praticular sharps are part of a key signature.

**Use your judgement.** By definition, we cannot really enumerate
all the rules for annotating, as you will always encounter a new
situation with handwriting. Stick to the guiding principles, your
understanding of what the annotations should achieve (accurate markings
of the notation primitives that together form the musical score
you're presented with), and it should help you decide what the appropriate
action is for most situations. If you really are not sure, even after
thinking about it and reviewing these guidelines, then send us an email
to ``hajicj@ufal.mff.cuni.cz``!


Specific symbol rules
---------------------

**Text** is marked as individual letters. Upper-case letters and lower-case
letters are not the same. Numerals (including time signatures) will have
the same fate.

**Text boxes** join letters together to make sensible wholes. For instance,
a "dolce" expressive instruction should be annotated as ``letter_d``, ``letter_o``,
``letter_l``, ``letter_c``, ``letter_e``, and then the whole region
of the letters should be marked as a ``text_box``.

**Dynamics text** is also annotated as letters, for instance a *pianissimo*
sign (*pp*) is annotated as ``letter_p`` and ``letter_p``, but instead
of ``text_box``, the marking is annotated as ``text_dynamics``.

**Grace notes** are marked like regular notes (notehead, stem and flags
or beams), but there are two extra actions. First, if the grace note
has a strikethrough (like *acacciatura* in early music), this strikethrough
is marked with the ``PRIM__grace-strikethrough`` symbol. Second, the entire
grace note (or group, in case of beamed grace note groups) is marked
with the ``PRIM__grace-note`` symbol.

**F-clef** gets marked twice. There are two Dots, the F-clef curve
to the left of the dots (``PRIM__F-clef``), and then please mark
the entire F-clef symbol again with the ``PRIM__F-clef`` symbol.
This is a technical operation; we haven't yet determined fully how
to deal with "composite primitives" such as the F-clef.

**Ties and slurs.** Please do mark ties as ties and slurs as slurs.
(This is contrary to the original instructions we had in mind, but
nevertheless, we have determined that a more detailed annotation
is better than a less detailed one, no excuses.)