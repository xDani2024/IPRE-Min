"""Pruebas de regresión de las decisiones bibliográficas verificadas en chat."""
from __future__ import annotations
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'flujo_unificado'))
sys.path.insert(0,str(ROOT/'integracion_corpus'))
from reproducir_revision_bibliografica import auditar
from normalizacion import normalizar_titulo,normalizar_titulo_unicode


def leer(path):
    with open(path,encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))


class TestRevisionHumanaReproducible(unittest.TestCase):
    def test_normalizacion_original_y_unicode_versionada(self):
        titulo='Современные методы управления'
        self.assertEqual(normalizar_titulo(titulo),'')
        self.assertIn('современные',normalizar_titulo_unicode(titulo))
        self.assertTrue(normalizar_titulo_unicode('露天掘り鉱山'))
        self.assertTrue(normalizar_titulo_unicode('휴리스틱 외판원'))
        self.assertNotEqual(normalizar_titulo_unicode('май'),normalizar_titulo_unicode('маи'))
        self.assertEqual(normalizar_titulo_unicode('Open-pit mining 2025'),'open pit mining 2025')

    def test_reproduccion_completa_sin_aplicar_decisiones(self):
        with tempfile.TemporaryDirectory() as tmp:
            reporte=auditar(salida=Path(tmp))
            self.assertEqual(reporte['alertas_totales'],791)
            self.assertEqual(reporte['n_unicode_aprobados'],249)
            self.assertEqual(reporte['n_cobertura_excluidos_filtro_original_sin_reincorporar'],105)
            self.assertEqual(reporte['n_prioritarios_cribado_pendiente'],15)
            self.assertEqual(reporte['n_seguimientos_especiales'],3)
            self.assertEqual(reporte['alertas_sin_dictamen'],[])
            self.assertEqual(reporte['n_decisiones_cierre_aprobadas'],6)
            self.assertFalse(reporte['fusiones_aplicadas'])
            self.assertFalse(reporte['reincorporaciones_automaticas'])
            self.assertFalse(reporte['criterios_tematicos_modificados'])
            self.assertEqual(len(leer(Path(tmp)/'01_decisiones_bibliograficas.csv')),791)
            grupos=leer(Path(tmp)/'04_grupos_fusion_aprobados_NO_APLICAR.csv')
            mapa={uid:r['grupo_estable'] for r in grupos for uid in r['registros_uid'].split('|')}
            # La edición 1995 se fusiona, las anteriores permanecen fuera.
            self.assertEqual(mapa['OpenAlex::https://openalex.org/W1593269834'],mapa['WoS::WOS:A1995QV54300005'])
            self.assertNotIn('WoS::WOS:A1988R375300004', mapa)
            self.assertNotIn('WoS::WOS:A1983RV47600002', mapa)
            # 2026 no se une a los registros 2025 de la alerta 0519.
            self.assertEqual(mapa['OpenAlex::https://openalex.org/W7128946536'],mapa['WoS::WOS:001755932400016'])
            self.assertNotIn('WoS::WOS:001892639000034',mapa)
            # Alerta 0384 fusiona OpenAlex y WoS, no Scopus.
            self.assertEqual(mapa['OpenAlex::https://openalex.org/W4312395089'],mapa['WoS::WOS:000885016000017'])
            self.assertNotIn('Scopus::85153721041',mapa)
            self.assertEqual(len(leer(Path(tmp)/'09_prioritarios_15_PENDIENTES_CRIBADO.csv')),15)
            self.assertEqual(mapa['Scopus::31344461922'],mapa['WoS::WOS:000235196700009'])
            self.assertEqual(len(leer(Path(tmp)/'10_pendientes_bibliograficos.csv')),0)
            self.assertEqual(len(leer(Path(tmp)/'13_decisiones_cierre_aprobadas.csv')),6)
            # El manifiesto de salida debe poder auditar el conjunto completo.
            self.assertIn('universo_OpenAlex',reporte['huellas_sha256_entradas'])
            self.assertIn('universo_Scopus',reporte['huellas_sha256_entradas'])
            self.assertIn('universo_WoS',reporte['huellas_sha256_entradas'])


if __name__=='__main__':unittest.main()
