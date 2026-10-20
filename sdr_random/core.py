"""SHA-256 conditioning and rejection-based decimal extraction."""
from collections import deque
from dataclasses import dataclass
import hashlib
from typing import Callable, Iterator, Protocol


class SourceError(RuntimeError):
    """Incomplete input, hardware error, or failed basic health check."""


class ByteSource(Protocol):
    def read(self, size: int) -> bytes:
        """Return exactly size fresh bytes, or raise SourceError."""


def positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f'{name} debe ser un entero positivo')
    return value


def decimal_digits(digest: bytes) -> str:
    """Accept hexadecimal nibbles 0..9; reject a..f (never modulo 10)."""
    return ''.join(c for c in digest.hex() if c in '0123456789')


@dataclass(frozen=True)
class Block:
    index: int
    raw: bytes
    sha256: str
    accepted: str


@dataclass(frozen=True)
class Number:
    text: str
    start_block: int
    start_hex: int
    end_block: int
    end_hex: int


class SDRRandom:
    """Stateful decimal generator; the caller owns/closes its byte source.

    Not thread-safe. Basic checks are not an entropy assessment. No OS entropy,
    counters or timestamps are mixed into SHA-256. Reusing input repeats output.
    """

    def __init__(self, source: ByteSource, block_bytes: int = 65536,
                 on_block: Callable[[Block], None] | None = None):
        positive_int(block_bytes, 'block_bytes')
        if block_bytes % 512:
            raise ValueError('block_bytes debe ser múltiplo de 512')
        self.source = source
        self.block_bytes = block_bytes
        self.on_block = on_block
        self.blocks = 0
        self._seen: set[str] = set()
        self._digits: deque[tuple[str, int, int]] = deque()
        self._failed = False

    def _refill(self) -> None:
        if self._failed:
            raise SourceError('Generador detenido por un error anterior; crear otra instancia')
        try:
            raw = bytes(self.source.read(self.block_bytes))
            if len(raw) != self.block_bytes:
                raise SourceError('Entrada agotada o lectura incompleta')
            if len(set(raw)) < 4:
                raise SourceError('Bloque casi constante: menos de 4 valores de byte')
            digest = hashlib.sha256(raw).hexdigest()
            if digest in self._seen:
                raise SourceError('Captura repetida en esta instancia')
            self._seen.add(digest)
            self.blocks += 1
            block = Block(self.blocks, raw, digest, decimal_digits(bytes.fromhex(digest)))
            if self.on_block:
                self.on_block(block)
            for position, char in enumerate(digest):
                if char in '0123456789':
                    self._digits.append((char, self.blocks, position))
        except BaseException:
            self._failed = True
            self._digits.clear()
            raise

    def number_record(self, digits: int = 1) -> Number:
        """Return a fixed-width string plus inclusive hexadecimal positions."""
        positive_int(digits, 'digits')
        if self._failed:
            raise SourceError('Generador detenido por un error anterior; crear otra instancia')
        selected = []
        while len(selected) < digits:
            if not self._digits:
                self._refill()
                continue
            selected.append(self._digits.popleft())
        return Number(''.join(x[0] for x in selected), selected[0][1],
                      selected[0][2], selected[-1][1], selected[-1][2])

    def number(self, digits: int = 1) -> str:
        """Return 0..9, 00..99, 000..999, etc., preserving leading zeros."""
        return self.number_record(digits).text

    def numbers(self, count: int, digits: int = 1) -> Iterator[str]:
        positive_int(count, 'count')
        positive_int(digits, 'digits')
        return (self.number(digits) for _ in range(count))
