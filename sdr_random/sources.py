"""RTL-SDR hardware and replay sources. Hardware dependency loads lazily."""
from contextlib import AbstractContextManager
import math
from pathlib import Path
from .core import SourceError, positive_int


class IQFileSource(AbstractContextManager):
    """Replay headerless, interleaved unsigned 8-bit I/Q. Never loops input."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._file = self.path.open('rb')

    def read(self, size: int) -> bytes:
        positive_int(size, 'size')
        data = self._file.read(size)
        if len(data) != size:
            raise SourceError('Archivo I/Q agotado o bloque final incompleto')
        return data

    def close(self) -> None:
        self._file.close()

    def __exit__(self, *args):
        self.close()


class RTLSDRSource(AbstractContextManager):
    """Read real I/Q through pyrtlsdr/librtlsdr, with hardware test mode off."""
    def __init__(self, frequency_hz: float, sample_rate: float = 2048000,
                 gain: str | float = 'auto', device_index: int = 0,
                 block_bytes: int = 65536):
        positive_int(block_bytes, 'block_bytes')
        if block_bytes % 512:
            raise ValueError('block_bytes debe ser múltiplo de 512')
        for value in (frequency_hz, sample_rate):
            if not math.isfinite(value) or value <= 0:
                raise ValueError('Frecuencia y sample rate deben ser positivos y finitos')
        if isinstance(device_index, bool) or not isinstance(device_index, int) or device_index < 0:
            raise ValueError('device_index debe ser un entero no negativo')
        if gain != 'auto':
            gain = float(gain)
            if not math.isfinite(gain):
                raise ValueError('gain debe ser auto o un número finito')
        try:
            from rtlsdr import RtlSdr
        except (ImportError, OSError) as exc:
            raise SourceError('Instalar sdr-random[rtl], librtlsdr y controlador USB; '
                              f'consultar docs/RTL_SDR.md. Detalle: {exc}') from exc
        self._sdr = None
        try:
            self._sdr = RtlSdr(device_index=device_index, test_mode_enabled=False)
            self._sdr.sample_rate = sample_rate
            self._sdr.center_freq = frequency_hz
            self._sdr.gain = gain
            self.read(block_bytes)  # Discard one stabilization block.
            self.settings = dict(frequency_hz=self._sdr.center_freq,
                                 sample_rate_hz=self._sdr.sample_rate,
                                 gain_db=self._sdr.gain, device_index=device_index,
                                 discarded_blocks=1, test_mode=False)
        except BaseException:
            self.close()
            raise

    def read(self, size: int) -> bytes:
        positive_int(size, 'size')
        if size % 512:
            raise ValueError('La lectura RTL-SDR debe ser múltiplo de 512')
        if self._sdr is None:
            raise SourceError('RTL-SDR cerrado')
        try:
            data = bytes(self._sdr.read_bytes(size))
        except Exception as exc:
            raise SourceError(f'Error leyendo RTL-SDR: {exc}') from exc
        if len(data) != size:
            raise SourceError('Lectura RTL-SDR incompleta')
        return data

    def close(self) -> None:
        if self._sdr is not None:
            device, self._sdr = self._sdr, None
            device.close()

    def __exit__(self, *args):
        self.close()
