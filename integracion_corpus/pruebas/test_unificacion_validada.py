"""Pruebas sin conexión ni alteraciones sobre los datos de las fuentes."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalizacion import normalizar_titulo_unicode, normalizar_fila
from unificacion_validada import AgrupadorSeguro, id_estable


def reg(fuente, ident):
    return {'fuente':fuente, 'registro_uid':f'{fuente}::{ident}'}


class TestUnificacionHumana(unittest.TestCase):
    def test_unicode_preserva_cirilico_coreano_y_japones(self):
        titulos=['Системы диспетчеризации карьерных самосвалов',
                 '노천광산 보조 작업 차량의 최적 이동경로 분석',
                 '露天掘り鉱山における発破規格及び岩盤状態']
        for titulo in titulos:
            with self.subTest(titulo=titulo):
                self.assertTrue(normalizar_titulo_unicode(titulo))

    def test_normalizacion_unicode_no_cambia_titulo_original(self):
        texto='Моделирование мультиагентной системы управления'
        r=normalizar_fila({'openalex_id':'W1','title':texto},'OpenAlex',2,'unicode_v2')
        self.assertEqual(r['titulo'],texto)
        self.assertTrue(r['titulo_normalizado'])

    def test_mismo_grupo_dos_fuentes_permitido(self):
        uf=AgrupadorSeguro([reg('OpenAlex','A'),reg('Scopus','B')], [])
        self.assertTrue(uf.fusionar(0,1)[0])
        self.assertEqual(len(uf.grupos()),1)

    def test_misma_fuente_solo_tras_aprobacion(self):
        uf=AgrupadorSeguro([reg('WoS','A'),reg('WoS','B')], [])
        self.assertEqual(uf.fusionar(0,1),(False,'MISMA_FUENTE_SIN_AUTORIZACION'))
        self.assertTrue(uf.fusionar(0,1,aprobado=True)[0])

    def test_bloqueo_indirecto_no_se_puede_evitar(self):
        rows=[reg('OpenAlex','A'), reg('Scopus','B'), reg('WoS','C')]
        uf=AgrupadorSeguro(rows, [(0,2)])
        self.assertTrue(uf.fusionar(0,1,aprobado=True)[0])
        self.assertEqual(uf.fusionar(1,2,aprobado=True),(False,'SEPARACION_O_CASO_PENDIENTE'))

    def test_bloqueo_directo_impide_automatismo_y_aprobacion(self):
        rows=[reg('OpenAlex','A'),reg('Scopus','B')]
        uf=AgrupadorSeguro(rows,[(0,1)])
        self.assertFalse(uf.fusionar(0,1)[0])
        self.assertFalse(uf.fusionar(0,1,aprobado=True)[0])

    def test_id_estable_no_depende_del_orden(self):
        self.assertEqual(id_estable(['WoS::X','OpenAlex::Y']),id_estable(['OpenAlex::Y','WoS::X']))
        self.assertNotEqual(id_estable(['WoS::X']),id_estable(['WoS::Y']))

    def test_sin_duplicaciones_por_fuente_despues_de_aprobacion(self):
        rows=[reg('OpenAlex','A'),reg('Scopus','B'),reg('Scopus','C')]
        uf=AgrupadorSeguro(rows,[])
        uf.fusionar(0,1,aprobado=True)
        self.assertEqual(uf.fusionar(0,2,aprobado=False)[1], 'MISMA_FUENTE_SIN_AUTORIZACION')

    def test_cierre_0111_0500_0529_no_fusionar_transitivamente(self):
        from reproducir_revision_bibliografica import auditar
        import tempfile
        import csv
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            auditar(salida=Path(temp))
            with (Path(temp)/'03_restricciones_no_fusionar.csv').open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f))
            got={r['id_alerta'] for r in rows}
            self.assertTrue({'ALERTA-0111','ALERTA-0500','ALERTA-0529','ALERTA-0467','ALERTA-0519'} <= got)

    def test_cierre_0534_fusion_explicita(self):
        from reproducir_revision_bibliografica import auditar
        import tempfile
        import csv
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            auditar(salida=Path(temp))
            with (Path(temp)/'02_aristas_fusion_aprobadas_NO_APLICAR.csv').open(encoding='utf-8-sig',newline='') as f:
                rows=list(csv.DictReader(f))
            fusion=[r for r in rows if r['id_alerta']=='ALERTA-0534']
            self.assertEqual(len(fusion),1)
            self.assertEqual({fusion[0]['registro_uid_a'],fusion[0]['registro_uid_b']},
                             {'Scopus::31344461922','WoS::WOS:000235196700009'})

if __name__=='__main__':
    unittest.main()
