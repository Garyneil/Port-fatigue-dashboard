"""The existing live model's causal 50 Hz, three-band preprocessing."""
import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi


def filter_bank(x):
    out = []
    for low, high in ((.5, 4.), (4., 8.), (8., 13.)):
        sos = butter(4, [low, high], btype='bandpass', fs=50, output='sos')
        zi = sosfilt_zi(sos)[:, None, :] * x[None, :, 0, None]
        y, _ = sosfilt(sos, x, axis=-1, zi=zi)
        out.append(y)
    return np.asarray(out)
