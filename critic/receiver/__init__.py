"""Experimental auditory components. No production encoder registration."""

VERSION = "auditory-receiver-v2-lab1"


def require_validated_receiver():
    """Fail closed until healthy mechanics and neural coupling have evidence."""
    raise RuntimeError(
        "Receiver v2 is not validated for poem simulations: sound-transfer and "
        "force-to-channel source models exist, but acoustic-force and "
        "channel-to-FlyBrain current calibration remain unresolved. "
        "Use the explicitly labeled legacy rms-jon-v1 receiver."
    )
