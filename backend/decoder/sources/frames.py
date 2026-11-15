"""The only object a source is allowed to yield."""

from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Flash:
    """One intensification.

    sample_index counts from the start of the stream.
    stimulus_id is "row-2" or "col-4" when the speller UI logged the flash.
    The g.tec files have no stimulus id, only is_target.
    is_target is known during calibration and unknown while spelling.
    """

    sample_index: int
    stimulus_id: str | None = None
    is_target: bool | None = None


@dataclass
class Frame:
    """A raw chunk. data is samples x channels, still unfiltered."""

    data: np.ndarray
    flashes: list[Flash] = field(default_factory=list)
