"""Ejecutar desde integracion_corpus: python -m unittest discover -s pruebas -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalizacion import normalizar_doi, normalizar_titulo, normalizar_fila
from deduplicacion import vincular


def fila(source, sid, doi, title, year='2022'):
    idn = {'OpenAlex': 'openalex_id', 'Scopus': 'scopus_id', 'WoS': 'wos_id'}[source]
    return normalizar_fila({idn: sid, 'doi': doi, 'title': title, 'year': year}, source, 2)


class TestCorpus(unittest.TestCase):
    def test_doi_y_titulo_normalizados(self):
        self.assertEqual(normalizar_doi('https://doi.org/10.1234/ABC.2020'), '10.1234/abc.2020')
        self.assertEqual(normalizar_doi('doi: 10.5678/XY!'), '10.5678/xy!')
        self.assertEqual(normalizar_doi('no es DOI'), '')
        self.assertEqual(normalizar_titulo('Optimización: Minería (A Cielo Abierto)'),
                         'optimizacion mineria a cielo abierto')

    def test_igual_doi_titulo_equivalente(self):
        rows = [fila('OpenAlex', 'a', '10.1234/abc', 'Operational performance of mining trucks'),
                fila('Scopus', 'b', 'https://doi.org/10.1234/abc', 'Operational performance of mining trucks')]
        groups, warnings, _ = vincular(rows)
        self.assertEqual(len(groups), 1)

    def test_titulo_anio_sin_doi(self):
        rows = [fila('OpenAlex', 'a', '', 'Operational performance of mining trucks'),
                fila('WoS', 'b', '10.1234/abc', 'Operational performance of mining trucks')]
        groups, _, _ = vincular(rows)
        self.assertEqual(len(groups), 1)

    def test_mismo_titulo_doi_conflictivo_no_se_fusiona(self):
        title = 'Operational performance of mining trucks'
        rows = [fila('Scopus', 'a', '10.1234/abc', title),
                fila('WoS', 'b', '10.5678/def', title)]
        groups, alerts, _ = vincular(rows)
        self.assertEqual(len(groups), 2)
        self.assertIn('TITULO_ANIO_DOI_CONFLICTIVOS', {a['tipo'] for a in alerts})

    def test_mismo_doi_titulo_distinto_no_se_fusiona(self):
        rows = [fila('Scopus', 'a', '10.1234/abc', 'Road maintenance using graders'),
                fila('WoS', 'b', '10.1234/abc', 'A separate paper about dental hygiene')]
        groups, alerts, _ = vincular(rows)
        self.assertEqual(len(groups), 2)
        self.assertIn('DOI_TITULOS_O_ANIOS_DIVERGENTES', {a['tipo'] for a in alerts})

    def test_titulo_ano_diferente_no_se_fusiona(self):
        title = 'Operational performance of mining trucks'
        rows = [fila('Scopus', 'a', '', title, '2024'), fila('WoS', 'b', '', title, '2025')]
        groups, alerts, _ = vincular(rows)
        self.assertEqual(len(groups), 2)
        self.assertIn('TITULO_CON_ANIOS_DISTINTOS', {a['tipo'] for a in alerts})

    def test_dos_ids_una_misma_fuente_requieren_revision(self):
        title = 'Operational performance of mining trucks'
        rows = [fila('WoS', 'WOS:1', '10.1234/abc', title),
                fila('WoS', 'WOS:2', '10.1234/abc', title)]
        groups, alerts, _ = vincular(rows)
        self.assertEqual(len(groups), 2)
        self.assertIn('MULTIPLES_IDS_MISMA_FUENTE_REVISAR', {a['tipo'] for a in alerts})

    def test_no_traspasar_etiquetas_fuente(self):
        row = normalizar_fila({'openalex_id': 'x', 'title': 'An interesting research paper',
                               'auto_process_tags': 'perforación'}, 'OpenAlex', 2)
        self.assertEqual(row['etiquetas_proceso_fuente'], 'perforación')
        self.assertEqual(row['estado_filtro_fuente'], '')


if __name__ == '__main__':
    unittest.main()
