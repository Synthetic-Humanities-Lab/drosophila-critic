"""Experimental auditory components. No production encoder registration."""

VERSION = "auditory-receiver-v2-lab1"


def require_validated_receiver():
    """Fail closed until healthy mechanics and neural coupling have evidence."""
    raise RuntimeError(
        "Receiver v2 is not validated for poem simulations: the published Stoop "
        "coefficients describe DMSO-induced oscillations; healthy forced-response "
        "parameters and receptor-to-FlyBrain coupling remain unresolved. "
        "Use the explicitly labeled legacy rms-jon-v1 receiver."
    )
