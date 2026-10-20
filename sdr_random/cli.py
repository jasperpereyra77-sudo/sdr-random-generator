"""Command-line example that consumes the public library API."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from . import IQFileSource, RTLSDRSource, SDRRandom


def _positive(text):
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError('Debe ser positivo')
    return value


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    width = None
    if argv and re.fullmatch(r'-\d+', argv[0]):
        width = int(argv.pop(0)[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digitos', type=_positive, default=1)
    parser.add_argument('--cantidad', type=_positive, default=1)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--frequency-mhz', type=float, help='Frecuencia elegida por el usuario en MHz')
    source.add_argument('--iq-file', type=Path, help='Reproducir I/Q u8 sin cabecera')
    parser.add_argument('--sample-rate', type=float, default=2048000)
    parser.add_argument('--gain', default='auto')
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--bloque-bytes', type=_positive, default=65536)
    parser.add_argument('--salida', type=Path, help='Directorio NUEVO para CSV, auditoría y capturas')
    args = parser.parse_args(argv)
    if width is not None:
        if width < 1:
            parser.error('Usar -1, -2, -3, etc.; no -0')
        if '--digitos' in argv or any(x.startswith('--digitos=') for x in argv):
            parser.error('Elegir -N o --digitos, no ambos')
        args.digitos = width
    if args.bloque_bytes % 512:
        parser.error('--bloque-bytes debe ser múltiplo de 512')
    destination = args.salida or Path('resultados_sdr_' + datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f'))
    metadata = dict(version='1.0.0', start_utc=datetime.now(timezone.utc).isoformat(),
                    digits=args.digitos, requested=args.cantidad, block_bytes=args.bloque_bytes,
                    generated=0, blocks=0, state='in_progress',
                    algorithm='SHA-256 -> aceptar nibbles 0..9 -> concatenar -> agrupar',
                    note='Controles básicos; fuente sin certificación de entropía')
    counts = Counter()
    created = False
    generator = None
    code = 0
    try:
        selected = (IQFileSource(args.iq_file) if args.iq_file else
                    RTLSDRSource(args.frequency_mhz * 1e6, args.sample_rate, args.gain,
                                 args.device, args.bloque_bytes))
        with selected:
            metadata['source'] = (dict(type='iq_replay', path=str(args.iq_file.resolve()))
                                  if args.iq_file else dict(type='rtl_sdr', **selected.settings))
            destination.mkdir(parents=True, exist_ok=False)
            created = True
            (destination / 'capturas').mkdir()
            (destination / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            with (destination / 'bloques.jsonl').open('w', encoding='utf-8') as log, \
                 (destination / 'numeros.csv').open('w', newline='', encoding='utf-8') as out:
                def audit(block):
                    name = f'capturas/bloque_{block.index:06d}.iq'
                    (destination / name).write_bytes(block.raw)
                    log.write(json.dumps(dict(block=block.index, file=name, sha256=block.sha256,
                                              accepted=block.accepted,
                                              rejected=64-len(block.accepted))) + '\n')
                    log.flush()
                generator = SDRRandom(selected, args.bloque_bytes, on_block=audit)
                writer = csv.writer(out)
                writer.writerow(['indice', 'numero_texto', 'bloque_inicio', 'posicion_hex_inicio',
                                 'bloque_fin', 'posicion_hex_fin'])
                for index in range(1, args.cantidad + 1):
                    record = generator.number_record(args.digitos)
                    writer.writerow([index, *asdict(record).values()])
                    out.flush()
                    metadata['generated'] = index
                    counts.update(record.text)
                    print(record.text, flush=True)
            metadata['state'] = 'complete'
    except KeyboardInterrupt:
        metadata.update(state='interrupted', error='KeyboardInterrupt')
        print('Interrumpido; se conservan resultados parciales.', file=sys.stderr)
        code = 130
    except Exception as exc:
        metadata.update(state='error', error=str(exc))
        print(f'Error: {exc}', file=sys.stderr)
        code = 1
    finally:
        if created:
            metadata.update(end_utc=datetime.now(timezone.utc).isoformat(),
                            blocks=generator.blocks if generator else 0,
                            digit_counts={str(i): counts[str(i)] for i in range(10)})
            try:
                (destination / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
            except OSError as exc:
                print(f'No se pudo actualizar metadata: {exc}', file=sys.stderr)
                code = 1
            print(f'Resultados: {destination.resolve()}', file=sys.stderr)
    return code
