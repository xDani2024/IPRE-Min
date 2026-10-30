"""Reproduce la cohorte Scopus desde páginas JSON guardadas, sin red ni API key."""
from pathlib import Path
import argparse,csv,hashlib,json,os,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--salida',type=Path,default=ROOT/'reproduccion_local')
    p.add_argument('--descriptivos',action='store_true')
    a=p.parse_args();dest=a.salida.resolve()
    if dest.exists() and any(dest.iterdir()):p.error('La salida contiene archivos. Elija una carpeta nueva.')
    refpath=ROOT/'REFERENCIAS_REPRODUCCION.json'
    refs=json.loads(refpath.read_text(encoding='utf-8'))
    for rel,h in refs['codigo_sha256'].items():
        if sha(ROOT/rel)!=h:raise ValueError('Código modificado respecto de la versión verificada: '+rel)
    dest.mkdir(parents=True,exist_ok=True);logs=dest/'bitacoras';logs.mkdir()
    checks=[]
    def run(rel,*args):
        script=ROOT/rel;log=logs/(script.stem+'.txt')
        print('Ejecutando',script.name,flush=True)
        env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1'}
        with log.open('w',encoding='utf-8') as f:
            result=subprocess.run([sys.executable,str(script),*map(str,args)],stdout=f,stderr=subprocess.STDOUT,env=env)
        if result.returncode:raise RuntimeError(f'Falló {script.name} (código {result.returncode}). Consulte {log}')
    def cotejar(etapa,folder):
        expected=refs['etapas'][etapa]
        if set(expected)!={p.name for p in folder.glob('*.csv')}:raise ValueError('Lista de salidas diferente en '+etapa)
        for name,h in expected.items():
            actual=sha(folder/name)
            if actual!=h:raise ValueError('La reproducción difiere: '+etapa+'/'+name)
            checks.append({'etapa':etapa,'archivo':name,'sha256':actual,'reproducido_identico':True})
    broad=dest/'filtro_amplio';v6=dest/'motores/v6/codigo/salida';v7=dest/'motores/v8/entrada/v7/salida';v8=dest/'motores/v8/salida';v9=dest/'motores/v9/salida'
    run('01_extraccion_y_filtro/02_filtrar_y_unificar.py','--entrada',ROOT/'01_extraccion_y_filtro/datos_reconstruidos','--salida',broad);cotejar('fase01',broad)
    run('02_cribado_v6/codigo/06_screening_multidimensional.py','--entrada',broad,'--salida',v6);cotejar('v6',v6)
    run('03_cribado_v8/entrada/v7/11_resolver_dudosos.py','--entrada',v6/'screening_operacional_scopus_fase02.csv','--salida',v7);cotejar('v7',v7)
    run('03_cribado_v8/15_aplicar_criterio_calibrado.py','--entrada',v7,'--entrada-v6',v6/'screening_operacional_scopus_fase02.csv','--salida',v8);cotejar('v8',v8)
    run('04_cierre_v9/22_cerrar_TC.py','--entrada',v8,'--salida',v9)
    run('04_cierre_v9/23_verificar_cierre.py','--entrada',v8,'--salida',v9);cotejar('v9',v9)
    final=dest/'resultado_v9';shutil.copytree(v9,final)
    if a.descriptivos:run('05_descriptivos/25_generar_avance.py','--entrada',v9,'--salida',dest/'05_descriptivos')
    counts=json.loads((final/'Resumen_y_manifest_v9_scopus.json').read_text(encoding='utf-8'))['v9_propuesta_computacional_total']
    report={'estado':'REPRODUCCION_TECNICA_VERIFICADA','fuente':'Scopus','consulta_api':False,'api_key_necesaria':False,'base_amplia':len(read(broad/'corpus_general_aceptado_provisional.csv')),'conteos_v9':counts,'cotejos':checks,'validacion_humana_completada':False,'descriptivos_generados':a.descriptivos}
    (dest/'VERIFICACION_REPRODUCCION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Reproducción completada. IN:',counts.get('IN',0),'| OUT:',counts.get('OUT',0),'| TC: 0 | Validación humana pendiente.',flush=True)
    print('Resultados:',final)
if __name__=='__main__':main()
