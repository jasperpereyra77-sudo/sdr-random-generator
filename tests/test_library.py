import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from sdr_random import SDRRandom, IQFileSource, RTLSDRSource, SourceError, decimal_digits


def fixture(blocks=16, size=512):
    # Deterministic test data, deliberately not presented as physical entropy.
    return b''.join(hashlib.shake_256(f'fixture-{i}'.encode()).digest(size)
                    for i in range(blocks))


class GeneratorTests(unittest.TestCase):
    def test_rejection_exhaustive_nibbles(self):
        self.assertEqual(decimal_digits(bytes.fromhex('0123456789abcdef')), '0123456789')
        self.assertEqual(decimal_digits(bytes.fromhex('abcdef')), '')

    def test_matches_independent_reference_across_hashes(self):
        raw = fixture()
        expected = ''.join(c for i in range(0, len(raw), 512)
                           for c in hashlib.sha256(raw[i:i+512]).hexdigest()
                           if c in '0123456789')
        rng = SDRRandom(io.BytesIO(raw), 512)
        self.assertEqual(''.join(rng.numbers(5, 80)), expected[:400])
        self.assertGreater(rng.blocks, 1)

    def test_widths_and_leading_zero(self):
        rng = SDRRandom(io.BytesIO(fixture()), 512)
        values = list(rng.numbers(200, 3))
        self.assertTrue(all(len(v) == 3 and v.isdecimal() for v in values))
        self.assertTrue(any(v.startswith('0') for v in values))

    def test_buffer_survives_calls_and_width_changes(self):
        raw = fixture()
        a, b = (SDRRandom(io.BytesIO(raw), 512) for _ in range(2))
        self.assertEqual(a.number(1) + a.number(2) + a.number(3), b.number(6))

    def test_positions_include_cross_block(self):
        records = []
        rng = SDRRandom(io.BytesIO(fixture()), 512, records.append)
        n = rng.number_record(80)
        self.assertGreater(n.end_block, n.start_block)
        recovered = ''
        for block in records:
            start = n.start_hex if block.index == n.start_block else 0
            end = n.end_hex + 1 if block.index == n.end_block else 64
            recovered += ''.join(c for c in block.sha256[start:end] if c in '0123456789')
        self.assertEqual(n.text, recovered)

    def test_constant_short_and_repeated_input(self):
        for data, width in [(b'\x00' * 512, 1), (b'abc', 1),
                            (fixture(1) * 2, 80)]:
            with self.subTest(width=width, size=len(data)):
                rng = SDRRandom(io.BytesIO(data), 512)
                with self.assertRaises(SourceError):
                    rng.number(width)
                with self.assertRaises(SourceError):
                    rng.number()

    def test_invalid_parameters(self):
        for size in [0, -1, 513, True, 512.0]:
            with self.assertRaises(ValueError):
                SDRRandom(io.BytesIO(), size)
        rng = SDRRandom(io.BytesIO(fixture()), 512)
        for width in [0, -1, True, 1.5]:
            with self.assertRaises(ValueError):
                rng.number(width)
        with self.assertRaises(ValueError):
            rng.numbers(0)

    def test_file_replay_and_eof(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'capture.iq'
            p.write_bytes(fixture(1))
            with IQFileSource(p) as src:
                self.assertEqual(src.read(512), fixture(1))
                with self.assertRaises(SourceError):
                    src.read(512)

    def test_callback_failure_is_terminal(self):
        def fail(block):
            raise OSError('disk full')
        rng = SDRRandom(io.BytesIO(fixture()), 512, fail)
        with self.assertRaises(OSError):
            rng.number()
        with self.assertRaises(SourceError):
            rng.number()


class HardwareAdapterTests(unittest.TestCase):
    def fake(self, bad_setting=False):
        class Device:
            def __init__(self, **kwargs):
                self.kwargs = kwargs
                self.calls = []
                self.closed = False
                devices.append(self)
            def read_bytes(self, size):
                self.calls.append(size)
                if bad_setting:
                    raise OSError('USB failure')
                return fixture(1, size)
            def close(self):
                self.closed = True
        devices = []
        return types.SimpleNamespace(RtlSdr=Device), devices

    def test_rtl_configuration_discard_and_close(self):
        module, devices = self.fake()
        with patch.dict(sys.modules, rtlsdr=module):
            with RTLSDRSource(100e6, gain=10, block_bytes=512) as src:
                self.assertEqual(len(src.read(512)), 512)
                self.assertFalse(devices[0].kwargs['test_mode_enabled'])
                self.assertEqual(devices[0].calls, [512, 512])
                self.assertEqual(devices[0].center_freq, 100e6)
            self.assertTrue(devices[0].closed)
            with self.assertRaises(SourceError):
                src.read(512)

    def test_rtl_closes_on_initial_read_failure(self):
        module, devices = self.fake(True)
        with patch.dict(sys.modules, rtlsdr=module):
            with self.assertRaises(SourceError):
                RTLSDRSource(100e6, block_bytes=512)
        self.assertTrue(devices[0].closed)

    def test_invalid_hardware_settings(self):
        for kwargs in [dict(frequency_hz=float('nan')), dict(frequency_hz=-1),
                       dict(frequency_hz=1e8, sample_rate=0),
                       dict(frequency_hz=1e8, device_index=-1),
                       dict(frequency_hz=1e8, gain='nan')]:
            with self.assertRaises(ValueError):
                RTLSDRSource(**kwargs)


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, '-m', 'sdr_random', *map(str, args)],
                              capture_output=True, text=True)

    def test_cli_widths_and_audit(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'capture.iq'
            path.write_bytes(fixture())
            for width in [1, 2, 3, 80]:
                out = Path(d) / f'out-{width}'
                result = self.run_cli(f'-{width}', '--cantidad', 3, '--iq-file', path,
                                      '--bloque-bytes', 512, '--salida', out)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual([len(x) for x in result.stdout.splitlines()], [width]*3)
                meta = json.loads((out / 'metadata.json').read_text())
                self.assertEqual(meta['state'], 'complete')
                self.assertEqual(meta['generated'], 3)
                self.assertTrue((out / 'numeros.csv').is_file())
                self.assertTrue(list((out / 'capturas').glob('*.iq')))

    def test_partial_results_and_existing_directory(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'capture.iq'
            path.write_bytes(fixture(1))
            out = Path(d) / 'output'
            args = ['--digitos', 3, '--cantidad', 100, '--iq-file', path,
                    '--bloque-bytes', 512, '--salida', out]
            result = self.run_cli(*args)
            self.assertEqual(result.returncode, 1)
            before = (out / 'metadata.json').read_bytes()
            self.assertEqual(json.loads(before)['state'], 'error')
            self.assertGreater(len(result.stdout.splitlines()), 0)
            self.assertEqual(self.run_cli(*args).returncode, 1)
            self.assertEqual((out / 'metadata.json').read_bytes(), before)

    def test_requires_source_and_valid_width(self):
        for args in [[], ['-0', '--iq-file', 'unused'],
                     ['-2', '--digitos', '3', '--iq-file', 'unused']]:
            self.assertEqual(self.run_cli(*args).returncode, 2)


if __name__ == '__main__':
    unittest.main()
