.. MUSCIMarker musical notation primitives annotation guidelines.

.. include:: shortcuts

.. _instructionss:

Annotation Instructions
=======================

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

.. note::

    The following changes have been made to the original instructions,
    based on the testing round:

    **New symbols for articulation.** Turns out we missed symbols like
    *tenuto*, accents, etc. -- they have now been added to the class
    list.


Guiding principles
------------------

Thee are a few things to understand first, before we dive into
the specifics.

**Pixels matter.** Although you only see rectangles on the screen
when you annotate objects, in the background, the exact objects
are recorded: each pixel within the colored rectangle that you see
has a Belongs/Doesn't Belong label, based on how you traced the
edges of the symbol.

**Background does not matter.** In black-and-white images, only
the white pixels are ever recorded as belonging to a symbol.

**All pixels in a symbol should be marked.** So if you get intersections,
such as between a stem and a beam, the intersection pixels just belong
to both symbols. Belonging to one symbol does not exclude a pixel
from belonging to another symbol. Intersections happen all the time.

.. image:: images/guidelines/intersections.png

**Not all non-background pixels are part of a symbol.** There may be
non-background pixels that are a result of the writer's mistake,
or artifacts of the input mode (e.g. stylus on a tablet - sometimes,
the tablet software might have preferred to make 90-degree corners
or straight lines where it's obvious there should be a curve...).
It's perfectly fine to leave these extra pixels out of the symbols
you are marking. In fact, including such extra pixels would be
a mistake.

.. image:: images/guidelines/spurious_pixels.png

**Layered annotation.** Sometimes (e.g. text, key signatures),
you will be asked to annotated the same thing with more markings.
For instance, a correct annotation of the  key signature for A major
has three ``sharp`` annotations and a ``key_signature`` annotation
that covers all these symbols. This is because musical notation has
several layers at which it needs to be annotated: we need to know,
at the same time, that the symbols for key signatures are sharps,
and that these praticular sharps are part of a key signature.

.. image:: images/guidelines/layered_annotation.png

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

We now give the instructions for individual symbol classes. Make sure
you understand these. If you don't, ask! (``hajicj@ufal.mff.cuni.cz``)


Notes
-----

**Primitives and note symbols.** The first part of annotating notes
is marking the notation primitives: notehead, stem, flags/beams.
Then, mark the entire note using the appropriate category: ``solitary_note``,
``solitary_chord``, ``beamed_group``, ``grace_note``, ``grace_beamed_group``,
or ``other_note`` for cases that do not fall into either of these
three categories.

.. image:: images/guidelines/note_primitives_and_complex.png

**What constitutes an entire note?** (Or, a beamed group?)
In the previous paragraph, you were instructed to assign a label
to an "entire note". However, this needs further clarification.

*Attached* to a note means a symbol that pertains specifically
to the given note. So, ledger lines are attached to a note. Duration
dots are attached to a note. A flat or a sharp is attached to a note
(although this is more of a technical definition, because commonly
the sharp affects the rest of the notes on that pitch within the
measure, we still consider sharps and flats attached to their respective
notes). However, ties and slurs are not attached to notes. Crescendo
and decrescendo hairpins are not. Tuple signs, volta signs, texts, clefs,
key signatures -- these symbols are *not* attached to notes.

.. image:: images/guidelines/note_attachment.png

So, we want the symbols attached to a note to be a part of the complex
``note`` symbol (whichever category applies). The logic behind this decision
is this: all the components of the complex note symbol are marked
individually. So, if we later want the complex note to *not* include some
symbols like staccato dots or ledger lines, we can "subtract" them
from the complex note. But if they are *not* a part of the complex note,
adding them is a much harder problem: we would have to decide to which
complex note they should be attached, etc.

**Beams and beamed groups.** A ``beam`` is just one line connecting the stems
to give note type information. A group of four 16th notes with beams will
consist of four ``notehead_full`` symbols, four ``stem`` symbols and two
``beam`` symbols. With a dotted note in a beamed group, the very short
beam "hook" on the shorter note of the dotted pair is also a ``beam``.

.. image:: images/guidelines/beamed_group.png

**Rests** have their own set of primitives (``quarter_rest``, ``half_rest``,
etc.). Individual rests should not be marked with complex symbols, but
rests that are inside a beamed group are marked as a part of the
``beamed_group``. (Again, the logic is, we can filter them out, and
the beamed group should consist of all the duration it spans
in the given voice.)

**Grace notes** are marked like regular notes (notehead, stem and flags
or beams), but there are two extra actions. First, if the grace note
has a strikethrough (like *acacciatura* in early music), this strikethrough
is marked with the ``grace-strikethrough`` symbol. Second, the entire
grace note (or group, in case of beamed grace note groups) is marked
with the ``grace_note`` (or ``grace_beamed_group``) symbol.

**Grace notes are also attached to their complex note!** So, a grace note
belongs to two complex notes: its ``grace`` category, and the ``solitary_note``,
``beamed_group`` or whatever it is attached to.

.. image:: images/guidelines/grace_notes.png

**Other complex notes.** Sometimes, there may be notes in non-playing
contexts, such as in tempo markings or proportional tempo transitions.
These are still annotated the same way (notehead, stem, dot, etc.), but
their complex class is ``other_solitary_note`` or ``other_beamed_group``.

**Ossia.** If there is an *ossia*, annotate it as if it were regular
notation, and then mark it all as ``ossia``.

Other Notations
---------------

**Key signatures** The sharps or flats are marked as ``sharp`` or ``flat``,
just as if the symbols are next to notes. However, the symbols making
up the key signature should all be marked as a part of a ``key_signature``
symbol.

.. image:: images/guidelines/key_signature.png

**Time signatures** The time signatures consisting of numerals are marked
as the given numerals; then, the numeral-based time signatures should be
marked as a symbol of the ``time_signature`` class.
The "whole" time signature (a "C" symbol), the
*alla breve* (a "C" with a vertical line) and other time signature symbols
have their own distinct categories; they should *not* be marked
as ``time_signature`` on top of these.

.. image:: images/guidelines/time_signature.png

**F-clef** now gets no special marking rules.

**Ties and slurs.** Please do mark ties as ties and slurs as slurs.
(This is contrary to the original instructions we had in mind, but
nevertheless, we have determined that a more detailed annotation
is better than a less detailed one, no excuses.) If you are not sure,
make a guess.


Handling text
-------------

**Text** is marked as individual letters. Upper-case letters and lower-case
letters are not the same. Numerals (including time signatures) will have
the same fate. As with key signatures or notes, texts are composite symbols;
the letters are the "text primitives" and there are classes of texts.

**Text boxes** join letters together to make sensible wholes. For instance,
a "dolce" expressive instruction should be annotated as ``letter_d``, ``letter_o``,
``letter_l``, ``letter_c``, ``letter_e``, and then the whole region
of the letters should be marked as a ``text_box``.

**Dynamics text** is also annotated as letters, for instance a *pianissimo*
sign (*pp*) is annotated as ``letter_p`` and ``letter_p``, but instead
of ``text_box``, the marking is annotated as ``text_dynamics``.

