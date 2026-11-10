"""Compara hashes SHA-256 de dos ejecuciones de la unificación validada.

Uso: python integracion_corpus/verificar_reproduccion.py --referencia DIR1 --nueva DIR2
Las carpetas DIR1 y DIR2 contienen universo/ y base_amplia/.
"""
import argparse
import hashlib
import sys
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for bloque in iter(lambda:f.read(1024*1024),b''):
            h.update(bloque)
    return h.hexdigest()


def verificar(referencia,nueva):
    ref,nueva=Path(referencia),Path(nueva)
    errores=[]
    for etapa in ('universo','base_amplia'):
        rf,nf=ref/etapa,nueva/etapa
        archivos=sorted(p.name for p in rf.glob('*') if p.is_file() and p.suffix in ('.csv','.json'))
        nuevos=sorted(p.name for p in nf.glob('*') if p.is_file() and p.suffix in ('.csv','.json'))
        if archivos!=nuevos:
            errores.append(f'{etapa}: archivos diferentes: {set(archivos)^set(nuevos)}')
        for nombre in sorted(set(archivos)&set(nuevos)):
            if sha(rf/nombre)!=sha(nf/nombre):
                errores.append(f'{etapa}/{nombre}: SHA-256 distinto')
        print(f'{etapa}: {len(archivos)} archivos de referencia comprobados')
    if errores:
        raise ValueError('\n'.join(errores))
    print('OK: ambas ejecuciones producen archivos byte a byte idénticos')
    return True


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--referencia',type=Path,required=True)
    p.add_argument('--nueva',type=Path,required=True)
    a=p.parse_args()
    try: verificar(a.referencia,a.nueva)
    except (ValueError,OSError) as e:
        print('ERROR reproducibilidad:',e,file=sys.stderr)
        sys.exit(1)

if __name__=='__main__': main()
