# Listening, performance, and affect

The fly listens; the human participants read, perform, model, and interpret. The
working title *The Drosophila Critic* names the apparatus, not a newly discovered
literary faculty. The more precise subtitle is **A fruit fly listens to poetry.**

The strongest research question is not whether a fly shares a human response to
Blake. It is what becomes of a poem when a performance passes through an explicitly
constructed, nonhuman-sensitive instrument—and what our translations omit.

## Affect as a critical lens

A Spinozist–Deleuzian–Massumian approach directs attention toward encounters,
intensities, temporal changes, and capacities to affect and be affected. It is
productive here as a question: where does an input make a difference, how does that
difference propagate, and what persists after it stops? It is not a warrant for
renaming spike rate “affect” or treating more activity as more feeling. A capacity
to act requires a repertoire of possible responses and interventions that test it;
this prototype currently measures a trajectory under one input, not that repertoire.
See [Massumi, *Parables for the Virtual*](https://www.dukeupress.edu/parables-for-the-virtual-twentieth-anniversary-edition).

Keep a critical counter-reading available. We removed semantic access by design;
we cannot then present the result as empirical proof that affect precedes or escapes
meaning. The dispute around that move is part of the work, not an inconvenient
footnote. [Leys and interlocutors, “Affect: An Exchange”](https://criticalinquiry.uchicago.edu/affect_an_exchange/)
provides a useful point of departure. An affect lens should remain visibly authored,
revisable, and distinguishable from the measurements that occasion it.

Formal analysis can be more exact than assigning moods: pauses, repetitions,
rhythmic clustering, duration, silence, and aftereffects. [Brinkema, *The Forms of
the Affects*](https://www.dukeupress.edu/the-forms-of-the-affects) is a productive
companion for making form central rather than treating intensity as an unstructured
substance. These are proposed applications, not claims that the simulation validates
a theorist.

## Priorities for a stronger humanities project

1. **Make a comparative performance edition.** Keep the poem fixed and vary the
   performer. Preserve credit, source, recording conditions, edits, timing, and
   normalization. Let a visitor compare the sounding, trajectory, and interpretation
   without mistaking one performance for the poem itself. The fixed synthetic voice
   remains a reference condition; the human recording introduces a deliberate new
   variable. We should eventually commission two contrasting readings from the same
   performer with the same microphone to reduce recording-condition confounds.

2. **Test what the instrument can distinguish.** Run several matched seeds; compare
   intact speech, reversed audio, reordered phrases, and non-speech sounds matched
   to the same envelope. Our current encoder discards almost everything except
   20 ms RMS amplitude. Two different sounds with identical encoded envelopes must
   produce identical seeded responses. This equivalence is both a test and a strong
   exhibit: the machine's deafness to some differences matters as much as its response
   to others. Pitch, timbre and phonemes cannot be credited for effects this encoder
   cannot separately represent.

3. **Put mediation onstage.** The relevant unit is poet, performer, microphone or
   synthesizer, normalizer, transducer, connectome, model, visual display, critic,
   and visitor. A [Hayles-inspired account of cognitive assemblages](https://press.uchicago.edu/ucp/books/book/chicago/U/bo25861765.html)
   helps frame the distributed work, but it does not establish cognition in every
   component. Show what each operation adds and removes. The literary interpretation
   belongs to the human-designed apparatus, not to the fly alone.

4. **Treat embodiment as an open problem.** This is a frozen connectome under a LIF
   model, without a behaving body, normal antennal mechanics, an environment, or a
   closed sensory–motor loop. The body mesh is a female exemplar; the connectome is
   male. A plausible next model would test a small, validated auditory–motor relation
   with feedback, rather than animating an invented emotional response. Missing
   embodiment should affect the argument, not merely appear in a disclaimer.

5. **Separate three interpreters.** Offer response-only circuit and affect readings;
   add a separately labeled human literary commentary that may see Blake's words;
   and invite the visitor's own account. Do not let the text-aware commentary leak
   into the response-only generator. Disagreement between these readings can be the
   artwork's outcome. Avoid collapsing it into a single confidence score.

6. **Return Blake's material and ethical form.** Bring in an appropriately sourced
   illuminated page alongside the performance. The speaker's “thoughtless hand,”
   the fly's vulnerability, and the human's power to frame another creature's life
   make the asymmetry of this experiment unusually pertinent. This is a human close
   reading of Blake, not an interpretation extracted from spikes. The interface
   should ask who gets to call the encounter a reading—and who controls the terms.

7. **Study the audience's affect separately.** Dramatic light, a fragile fly body,
   a human voice, and a neural animation can make viewers feel concern or agency.
   Compare display conditions in an opt-in audience study before attributing those
   effects to the fly. The visualization helps produce the human encounter; it is
   not a transparent window into an animal's interiority.

The next deliverable should be a small critical edition with two or three carefully
sourced performances and a transparent comparative protocol, not a general engine
for declaring what animals feel about literature.

## What the first comparison actually shows

The synthetic reference lasts 26.165 s; the Sayers excerpt lasts 45.10 s. Their
mean global departures from their respective matched silences are +0.011446 and
+0.000949 Hz/neuron, respectively. Each is one seed, not a robust estimate of a
performance effect. The common normalization rule produces different actual RMS
levels (0.0943 versus 0.0519), because the peak ceiling constrains the human recording
more strongly. This is an important confound, disclosed in the interface: these
records compare two processed performances, not dramatic delivery at equal loudness.
A useful next comparison would match both to the lower achievable RMS without
clipping, preserve their timing, and repeat across seeds. A stronger response should
never be sold as a better poem, better performance, or more affect.
