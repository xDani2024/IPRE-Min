"""Pruebas del módulo común sin acceder a APIs."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from importar_wos import exportar
from cribado import evaluar

class TestFlujo(unittest.TestCase):
    def test_cribado_independiente_fuente(self):
        articulo={'titulo':'Operational performance of haul trucks in open pit mining',
                  'resumen':'This study examines operational efficiency of hauling and scheduling.',
                  'tipo_documento':'article'}
        resultado=evaluar(articulo)
        self.assertEqual(resultado, evaluar({**articulo,'fuentes':'Scopus|WoS'}))
        self.assertEqual(resultado['cribado_automatico'],'CANDIDATO')
        self.assertEqual(resultado['decision_humana'],'')

    def test_pendiente_sin_resumen(self):
        r=evaluar({'titulo':'Open pit mining truck dispatch','resumen':'','tipo_documento':'article'})
        self.assertEqual(r['cribado_automatico'],'PENDIENTE_REVISION')
        self.assertEqual(r['motivos_cribado'],'sin_resumen')

    def test_etiquetas_referenciales_no_determinan_decision(self):
        a={'titulo':'Studying distant planets','resumen':'A telescope survey.', 'tipo_documento':'article'}
        self.assertEqual(evaluar(a),evaluar({**a,'etiquetas_originales_por_fuente_json':'[{"filtro":"include"}]'}))

    def test_importacion_wos_manual_csv(self):
        with tempfile.TemporaryDirectory() as td:
            entrada=Path(td)/'manual';entrada.mkdir()
            with (entrada/'lote1.csv').open('w',encoding='utf-8-sig',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=['UT','Article Title','Abstract','Publication Year','DOI','Document Type'])
                writer.writeheader()
                writer.writerow({'UT':'WOS:123','Article Title':'Road maintenance in open pit mining','Abstract':'Dozer work',
                                 'Publication Year':'2024','DOI':'10.1234/abc','Document Type':'Article'})
            salida=Path(td)/'consolidado'/'universo_wos.csv'
            r=exportar(entrada,salida)
            self.assertEqual(r['filas_importadas'],1)
            with salida.open(encoding='utf-8-sig',newline='') as f:
                row=next(csv.DictReader(f))
            self.assertEqual(row['wos_id'],'WOS:123')
            self.assertEqual(row['source_files'],'lote1.csv')

    def test_wos_rechaza_uid_repetido(self):
        with tempfile.TemporaryDirectory() as td:
            e=Path(td)/'manual';e.mkdir()
            for i in (1,2):
                (e/f'lote{i}.csv').write_text('UT,Article Title\nWOS:1,Duplicated paper\n',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'repetidos'):
                exportar(e,Path(td)/'out.csv')

if __name__=='__main__':unittest.main()
