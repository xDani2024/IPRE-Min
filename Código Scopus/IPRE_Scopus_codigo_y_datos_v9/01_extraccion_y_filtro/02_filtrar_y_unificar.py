from pathlib import Path
import argparse
ROOT = next(p for p in Path(__file__).resolve().parents if (p/'PROCEDENCIA_DEL_PAQUETE.json').is_file())
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--entrada',type=Path,default=ROOT/'01_extraccion_y_filtro/datos_reconstruidos')
parser.add_argument('--salida',type=Path,default=ROOT/'01_extraccion_y_filtro/salida')

args=parser.parse_args()
if args.salida.exists() and any(args.salida.iterdir()):
    parser.error('La salida contiene archivos. Elija una carpeta nueva con --salida.')
args.salida.mkdir(parents=True,exist_ok=True)

import shutil
import scopus_fase1 as motor
# El motor original escribe en destino/resultados. Copiar solo las páginas/configuración
# a un espacio de trabajo temporal evita alterar la instantánea de entrada.
from tempfile import TemporaryDirectory
with TemporaryDirectory() as temp:
    trabajo=Path(temp)/'descarga'
    trabajo.mkdir()
    shutil.copy2(args.entrada/'configuracion.json',trabajo/'configuracion.json')
    shutil.copytree(args.entrada/'paginas',trabajo/'paginas')
    motor.filtrar_y_exportar(trabajo)
    for archivo in (trabajo/'resultados').iterdir():
        shutil.copy2(archivo,args.salida/archivo.name)
