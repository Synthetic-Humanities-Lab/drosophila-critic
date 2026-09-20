"""An explicitly situated theoretical reading of a text-blind response summary."""


def interpret_affect(s):
    position = (
        "early"
        if s.peak_time < s.duration / 3
        else "late"
        if s.peak_time > 2 * s.duration / 3
        else "midway"
    )
    direction = "raises" if s.delta_hz_per_neuron >= 0 else "lowers"
    if abs(s.peak_delta_hz_per_neuron) < 1e-12:
        text = (
            "This encounter leaves no global separation from matched silence. "
            "An affective reading cannot manufacture a disturbance where this measurement finds none; "
            "nor can this global measure settle everything that happened within the network."
        )
    else:
        text = (
            f"This sounding {direction} mean network activity relative to its matched silence. "
            f"Its strongest global departure arrives {position}, at {s.peak_time:.2f} seconds. "
            "Through an affect-theory lens, these differences invite attention to how an encounter "
            "alters an ongoing system: where a disturbance gathers force, travels, and leaves a remainder. "
            f"The recorded aftermath differs from silence by {s.tail_delta_hz_per_neuron:+.3f} Hz per neuron. "
            "We read the trajectory as a relation made and altered in time, rather than assigning the fly "
            "a human emotion. A changed firing rate is evidence of perturbation; a changed capacity to act "
            "would require further experiments."
        )
    return {
        "provider": "response-only-affect-lens-v1",
        "text": text,
        "scope": "A situated critical interpretation, not an affect detector. Removing semantics by design does not prove affect is independent of meaning.",
        "sources": [
            {
                "title": "Massumi — Parables for the Virtual",
                "url": "https://www.dukeupress.edu/parables-for-the-virtual-twentieth-anniversary-edition",
            },
            {
                "title": "Leys and interlocutors — Affect: An Exchange",
                "url": "https://criticalinquiry.uchicago.edu/affect_an_exchange/",
            },
            {
                "title": "Hayles — Unthought",
                "url": "https://press.uchicago.edu/ucp/books/book/chicago/U/bo25861765.html",
            },
        ],
    }
