"""Importa de forma trazable exportaciones MANUALES de Web of Science.

Permite CSV UTF-8/UTF-8 BOM, XLSX y XLS (XLS requiere xlrd).
No invoca WoS ni altera las exportaciones originales.
"""
from __future__ import annotations
import csv
import hashlib
import json
import unicodedata
from pathlib import Path

COLUMNAS = {
    'wos_id': ('wos_id','ut','accession number','wos accession number','unique article identifier','unique wos id'),
    'doi': ('doi','di'),
    'title': ('title','article title','ti','document title'),
    'abstract': ('abstract','ab'),
    'year': ('year','publication year','py'),
    'document_type': ('document_type','document type','dt','type'),
    'authors': ('authors','author full names','au','af'),
    'language': ('language','la'),
    'keywords': ('keywords','author keywords','de'),
    'source_title': ('source_title','source title','publication title','so','journal'),
    'publication_date': ('publication_date','publication date','pd'),
}

def key(text):
    x = unicodedata.normalize('NFKD', str(text or '').strip().lower())
    return ' '.join(''.join(c for c in x if not unicodedata.combining(c)).replace('_',' ').split())


def iter_filas(ruta):
    ext = ruta.suffix.lower()
    if ext == '.csv':
        with ruta.open(encoding='utf-8-sig',newline='') as f:
            yield from csv.DictReader(f)
    elif ext in {'.xlsx','.xlsm'}:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError('Para leer XLSX: pip install openpyxl') from exc
        book = load_workbook(ruta,read_only=True,data_only=True)
        try:
            for ws in book.worksheets:
                iterator=ws.iter_rows(values_only=True)
                encabezados=next(iterator,None)
                if not encabezados:
                    continue
                encabezados=[str(x or '').strip() for x in encabezados]
                for vals in iterator:
                    if any(v is not None for v in vals):
                        yield dict(zip(encabezados,(str(v or '') for v in vals)))
        finally:
            book.close()
    elif ext == '.xls':
        try:
            import xlrd
        except ImportError as exc:
            raise RuntimeError('Para importar archivos WoS .xls, instale xlrd: pip install xlrd. También puede exportarlos como CSV UTF-8.') from exc
        libro=xlrd.open_workbook(str(ruta))
        for hoja in libro.sheets():
            if hoja.nrows < 2: continue
            encabezados=[str(x).strip() for x in hoja.row_values(0)]
            for i in range(1,hoja.nrows):
                yield dict(zip(encabezados,(str(v) if v not in ('',None) else '' for v in hoja.row_values(i))))
    else:
        raise ValueError(f'Formato manual no admitido: {ruta}')


def exportar(carpeta: Path, destino: Path):
    carpeta = Path(carpeta).resolve()
    destino = Path(destino).resolve()
    if not carpeta.is_dir():
        raise NotADirectoryError(carpeta)
    archivos = sorted(p for p in carpeta.iterdir() if p.is_file() and p.suffix.lower() in {'.csv','.xlsx','.xls','.xlsm'})
    if not archivos: raise ValueError('No se encontraron CSV/XLS/XLSX en la carpeta WoS.')
    salida=[]
    huellas=[]
    for path in archivos:
        if path == destino: raise ValueError('La salida no puede utilizarse como entrada.')
        huellas.append({'archivo':path.name, 'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        for indice, original in enumerate(iter_filas(path),2):
            by_key={key(k): str(v or '').strip() for k,v in original.items()}
            row={campo:next((by_key.get(key(opcion), '') for opcion in opciones if by_key.get(key(opcion))), '')
                 for campo,opciones in COLUMNAS.items()}
            if not row['title']:
                raise ValueError(f'{path.name}, fila {indice}: no se identifica el título (revise las columnas).')
            if not row['wos_id']:
                # Se conserva un ID técnico, NO se inventa un UID propio de WoS.
                huella=hashlib.sha256(json.dumps(original,ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:20]
                row['wos_id']=f'IMPORTADO_SIN_UID:{path.name}:{indice}:{huella}'
                row['observaciones_importacion']='ID WoS no disponible: verificar antes del cierre'
            else:
                row['observaciones_importacion']=''
            row['source_files']=path.name
            row['fila_archivo_origen']=str(indice)
            salida.append(row)
    claves=[r['wos_id'] for r in salida]
    if len(claves)!=len(set(claves)):
        raise ValueError('Existen IDs repetidos entre exportaciones de WoS. Revise si son exportaciones solapadas; no se fusionan silenciosamente.')
    destino.parent.mkdir(parents=True,exist_ok=True)
    campos=list(COLUMNAS)+['source_files','fila_archivo_origen','observaciones_importacion']
    with destino.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=campos);w.writeheader();w.writerows(salida)
    reporte={'fuente':'WoS','metodo':'exportacion_manual','archivos':huellas,'filas_importadas':len(salida),
             'sin_uid_nativo':sum(x['wos_id'].startswith('IMPORTADO_SIN_UID:') for x in salida),
             'advertencia':'No equivale a extracción API. Registrar consultas, fecha, filtros y cobertura de cada exportación manual.'}
    (destino.parent/'manifiesto_importacion_wos.json').write_text(json.dumps(reporte,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return reporte
