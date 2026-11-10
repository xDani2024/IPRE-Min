"""Pruebas del cruce auditable sin heredar la etiqueta v9 en el cribado nuevo."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cruce_historico_v9 import ejecutar, diagnostico


def guardar(p,rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


class TestCruceHistorico(unittest.TestCase):
    def test_priorizar_conflictos(self):
        self.assertEqual(diagnostico(['IN','OUT'],'CANDIDATO'),('CONTRADICCION_V9_ENTRE_FUENTES','ALTA'))
        self.assertEqual(diagnostico(['IN'],'PENDIENTE_REVISION'),('V9_IN_ACTUAL_PENDIENTE_O_PRIORITARIA','ALTA'))
        self.assertEqual(diagnostico(['IN'],'EXCLUSION_PROPUESTA'),('V9_IN_ACTUAL_EXCLUSION_PROPUESTA','ALTA'))
        self.assertEqual(diagnostico(['OUT'],'CANDIDATO'),('V9_OUT_ACTUAL_CANDIDATO','MEDIA'))
        self.assertEqual(diagnostico([], 'CANDIDATO'),('SIN_DECISION_V9','NORMAL'))

    def test_union_por_id_sin_transferir_v9(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d); b=d/'resultados'/'02_integracion_y_deduplicacion'
            c=d/'resultados'/'03_cribado_comun'
            i=d/'hist'
            guardar(b/'03_correspondencias_procedencia.csv',[
                {'registro_uid':'OpenAlex::OA1','id_publicacion':'P1'},
                {'registro_uid':'Scopus::SC1','id_publicacion':'P1'},
                {'registro_uid':'WoS::W1','id_publicacion':'P2'}])
            guardar(b/'02_corpus_consolidado_provisional.csv',[
                {'id_publicacion':'P1','titulo':'A','doi':'10.1000/a','anio_referencia':'2020','fuentes':'OpenAlex|Scopus','numero_fuentes':'2'},
                {'id_publicacion':'P2','titulo':'B','doi':'10.1000/b','anio_referencia':'2021','fuentes':'WoS','numero_fuentes':'1'}])
            guardar(b/'01_registros_normalizados.csv',[
                {'registro_uid':'OpenAlex::OA1','titulo':'A','titulo_normalizado':'a','anio':'2020','doi_normalizado':'10.1000/a'},
                {'registro_uid':'Scopus::SC1','titulo':'A','titulo_normalizado':'a','anio':'2020','doi_normalizado':'10.1000/a'},
                {'registro_uid':'WoS::W1','titulo':'B','titulo_normalizado':'b','anio':'2021','doi_normalizado':'10.1000/b'}])
            guardar(b/'04_alertas_revision.csv',[{'tipo':'TITULO_CON_ANIOS_DISTINTOS','registro_a':'OpenAlex::OA1','registro_b':'Scopus::SC1','detalle':'2020|2021'}])
            guardar(c/'01_matriz_cribado_automatico.csv',[
                {'id_publicacion':'P1','cribado_automatico':'CANDIDATO'},
                {'id_publicacion':'P2','cribado_automatico':'PENDIENTE_REVISION'}])
            rows = {'OpenAlex':[('OA1','10.1000/a','A','2020','IN')],
                    'Scopus':[('SC1','10.1000/a','A','2020','OUT')],
                    'WoS':[('W1','10.1000/b','B','2021','IN')]}
            for src, vals in rows.items():
                guardar(i/(src.lower()+'_v9.csv'),[
                    {'fuente':src,'id_fuente':a,'doi_original':b,'titulo_original':c,'anio_original':e,
                     'decision_v9_propuesta':f,'decision_humana_historica':'','validacion_humana_reportada':''}
                    for a,b,c,e,f in vals])
            report = ejecutar(d/'resultados',d/'salida', {src:i/(src.lower()+'_v9.csv') for src in rows})
            self.assertEqual(report['n_registros_provenientes_de_v9'],3)
            self.assertEqual(report['registros_v9_sin_correspondencia'],0)
            self.assertEqual(report['publicaciones_unicas_con_al_menos_un_in_v9'],2)
            self.assertEqual(report['publicaciones_unicas_con_in_v9_y_out_v9'],1)
            self.assertEqual(report['alertas_deduplicacion_para_revisar'],1)
            with (d/'salida'/'02_cruce_por_publicacion.csv').open(encoding='utf-8-sig') as f:
                x=list(csv.DictReader(f))
            self.assertEqual(x[0]['cribado_unificado_v1_1'],'CANDIDATO')
            self.assertEqual(x[0]['diagnostico_cruce'],'CONTRADICCION_V9_ENTRE_FUENTES')

if __name__ == '__main__': unittest.main()
