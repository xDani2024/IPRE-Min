from pathlib import Path
import argparse
ROOT = next(p for p in Path(__file__).resolve().parents if (p/'PROCEDENCIA_DEL_PAQUETE.json').is_file())
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--entrada',type=Path,default=ROOT/'04_cierre_v9/salida')
parser.add_argument('--salida',type=Path,default=ROOT/'05_descriptivos/salida')

args=parser.parse_args()
if args.salida.exists() and any(args.salida.iterdir()):
    parser.error('La salida contiene archivos. Elija una carpeta nueva con --salida.')
args.salida.mkdir(parents=True,exist_ok=True)

exec(compile((Path(__file__).parent/'_descriptivos.py').read_text(encoding='utf-8'),str(Path(__file__).parent/'_descriptivos.py'),'exec'))
