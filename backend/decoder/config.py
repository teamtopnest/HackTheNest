"""Numbers shared by training and live scoring.

A model trained with one set of these values only scores epochs built
with the same values. The headset path has to keep them too.
"""

FS = 250
BAND = (0.5, 30.0)
PRE = 0.1
POST = 0.7
DOWN = 10
CHUNK_SAMPLES = 32
CHARACTER_GAP_S = 0.4
CHANNELS = ("Fz", "Cz", "P3", "Pz", "P4", "PO7", "PO8", "Oz")
