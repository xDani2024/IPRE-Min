"""Descarga Scopus por cursor. La reproducción local no requiere ejecutar este archivo."""
from pathlib import Path
from getpass import getpass
import argparse, os
import scopus_fase1 as motor
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--salida',type=Path,default=Path(__file__).resolve().parent/'descarga_nueva')
p.add_argument('--modo',choices=['PILOTO','COMPLETO'],default='PILOTO')
a=p.parse_args()
key=os.environ.get('SCOPUS_API_KEY') or getpass('API Key de Scopus: ')
if not key.strip(): p.error('Falta API Key.')
motor.diagnosticar(key,estilo='EXACTA',count=5)
motor.descargar(key,a.salida,modo=a.modo,estilo='EXACTA',confirmar_completo=a.modo=='COMPLETO')
