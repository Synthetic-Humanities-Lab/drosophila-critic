"""Curated functional associations, separate from measurements and subjective claims."""

ROLES = {
    "JO-A/B input": {
        "label": "Sensing vibration",
        "role": "These antennal sensory neurons respond to vibration and participate in hearing in living flies.",
        "limit": "We stimulate these neurons directly. Their increase checks the input bridge; it does not demonstrate recognition, attention or enjoyment.",
        "source": "https://www.frontiersin.org/journals/neural-circuits/articles/10.3389/fncir.2017.00046/full",
    },
    "direct JON postsynaptic partners": {
        "label": "Beyond the sensory input",
        "role": "These neurons receive direct connections from the stimulated JONs in the connectome. This is a structural group with potentially mixed functions.",
        "limit": "A change here shows that activity differs beyond the injected neurons. It does not by itself establish a specific percept or behavioral response.",
        "source": "https://github.com/alextitonis/fly.ai/tree/5e931b8dc4856550565c5fa129d3d0c055af3dd1",
    },
    "descending_neuron": {
        "label": "Signals toward motor circuits",
        "role": "Descending neurons link the brain with motor circuits in the ventral nerve cord. They support many different actions.",
        "limit": "A whole-group mean cannot identify an action. Opposing, lateralized or brief signals may disappear when averaged together.",
        "source": "https://www.nature.com/articles/s41586-024-07523-9",
    },
    "DNa02": {
        "label": "Steering-related circuit",
        "role": "DNa02 belongs to descending circuitry associated with steering during walking.",
        "limit": "The pooled mean does not resolve left-right steering or establish that a turn would occur.",
        "source": "https://www.nature.com/articles/s41586-024-07523-9",
    },
    "DNp01": {
        "label": "Escape take-off circuit",
        "role": "DNp01 is the giant-fiber descending neuron associated with rapid escape take-off.",
        "limit": "A change in this model is an escape-circuit change, not evidence of fear or a predicted jump. No behavioral activation threshold is calibrated here.",
        "source": "https://www.nature.com/articles/s41586-024-07523-9",
    },
    "MDN": {
        "label": "Backward-walking circuit",
        "role": "Moonwalker descending neurons can recruit the motor circuitry for backward walking in living flies.",
        "limit": "A rate difference does not establish retreat, avoidance or a subjective wish to get away.",
        "source": "https://pubmed.ncbi.nlm.nih.gov/33268800/",
    },
    "pIP10": {
        "label": "Courtship-song production circuit",
        "role": "pIP10 descending neurons participate in driving the wing movements that produce courtship song.",
        "limit": "Activity here is not evidence of attraction, pleasure, or an actual song. Social context and cooperating circuits matter.",
        "source": "https://www.nature.com/articles/s41593-024-01738-9",
    },
}
