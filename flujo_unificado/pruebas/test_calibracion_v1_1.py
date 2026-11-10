"""Regresiones de reglas verificadas sobre títulos/resúmenes del corpus entregado.

Los casos centinela verifican comportamientos concretos, no la calidad global.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cribado import evaluar, VERSION_CRIBADO


def paper(titulo, resumen, **campos):
    return {'titulo':titulo, 'resumen':resumen, 'tipo_documento':'Article', **campos}


class TestCalibracion(unittest.TestCase):
    def test_vehiculos_auxiliares_rutas(self):
        p=paper('Optimal Routes Analysis of Vehicles for Auxiliary Operations in Open-pit Mines using a Heuristic Algorithm for the Traveling Salesman Problem',
                'This study analyzed the optimal routes of auxiliary vehicles in an open-pit mine, reducing travel time for 25 points.')
        self.assertEqual(evaluar(p)['cribado_automatico'], 'CANDIDATO')

    def test_perforacion_indice(self):
        p=paper('Computerized design of blasting parameters based on drillability index of jointed rock mass in roller bit drilling in open pit mines',
                'This article examines rates of roller bit drilling and drillability indices for open pit mining.')
        self.assertEqual(evaluar(p)['cribado_automatico'], 'CANDIDATO')

    def test_perforacion_titulo_con_errata_del_corpus(self):
        p=paper('IMPROVING THE EFFICIENCY OF DRILLING IN OPEN-PIPE MINING BASED ON DIGITAL TECHNOLOGY',
                'A method for shift productivity of a drilling machine during open-pit mining based on automation.')
        self.assertEqual(evaluar(p)['cribado_automatico'], 'CANDIDATO')

    def test_feria_industrial_no_es_estudio(self):
        p=paper('1969 HANOVER FAIR,',
                'Annual Industrial Fair; underground and surface mining equipment was displayed.')
        r=evaluar(p)
        self.assertEqual(r['cribado_automatico'], 'EXCLUSION_PROPUESTA')
        self.assertIn('publicacion_de_evento',r['motivos_cribado'])

    def test_misma_decision_para_todas_fuentes(self):
        p=paper('Reliability of bulldozers in open-pit mines',
                'This paper analyzes operational breakdowns and maintenance.')
        self.assertEqual(evaluar({**p, 'fuentes':'Scopus'}),
                         evaluar({**p, 'fuentes':'OpenAlex|WoS'}))

    def test_tematica_sin_contexto_no_suficiente(self):
        p=paper('Optimization of routing in a city',
                'A study of urban traffic for bus operators.')
        self.assertEqual(evaluar(p)['cribado_automatico'], 'EXCLUSION_PROPUESTA')

    def test_equipo_minero_sin_contexto_es_revisable(self):
        p=paper('Wheel dozer operational efficiency in the mining industry',
                'Condition monitoring and reliability in an industrial operation.')
        self.assertEqual(evaluar(p)['cribado_automatico'], 'REVISION_PRIORITARIA')

    def test_contexto_con_tematica_parcial_es_revisable(self):
        p=paper('Peculiar properties of open-pit mines',
                'The study surveys general attributes of mining operations.')
        self.assertEqual(evaluar(p)['cribado_automatico'], 'PENDIENTE_REVISION')

    def test_no_titulo_revisable(self):
        self.assertEqual(evaluar(paper('', 'reliability of dozers in open pit mining'))['cribado_automatico'],'PENDIENTE_REVISION')

    def test_sin_resumen_revisable(self):
        self.assertEqual(evaluar(paper('Maintenance of graders in open-pit mines',''))['cribado_automatico'],'PENDIENTE_REVISION')

    def test_titulo_explicito_no_sujeto_campo_de_etiquetas(self):
        p=paper('Water truck productivity in open-pit mining', 'Route analysis of mine haul roads.')
        a=evaluar(p)
        b=evaluar({**p,'etiquetas_originales_por_fuente_json':'[]','clasificacion_tematica_consolidada':'no'})
        self.assertEqual(a,b)
        self.assertTrue(a['version_cribado'].startswith('1.1.0'))

if __name__ == '__main__':
    unittest.main()
