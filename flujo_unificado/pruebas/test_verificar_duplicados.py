"""Regresiones bibliográficas para las propuestas, sin acceso a internet."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from verificar_duplicados import comparar, normalizar_unicode, ejecutar


def r(id, title, year, doi='', source='OpenAlex', authors='Jane Smith', journal='Journal'):
    return dict(registro_uid=f'{source}::{id}',fuente=source,
                titulo=title,anio=str(year),doi_normalizado=doi,
                autores=authors,revista=journal)


class TestBibliografia(unittest.TestCase):
    def test_doi_title_subtitle(self):
        a=r('1','A greenfield in black coal',2001,'10.1108/00483480110386121')
        b=r('2','A greenfield in black coal: The Bengalla Open Cut mine',2001,
            '10.1108/00483480110386121',source='Scopus')
        self.assertEqual(comparar(a,b)['decision_sugerida'],'MISMA_PUBLICACION')
    def test_doi_same_but_different_work_review(self):
        a=r('1','A greenfield in black coal',2001,'10.1108/00483480110386121')
        b=r('2','Advanced robotics in medicine',2001,'10.1108/00483480110386121',source='Scopus')
        self.assertEqual(comparar(a,b)['decision_sugerida'],'REQUIERE_REVISION')
    def test_different_dois_comparable_title_review(self):
        a=r('1','Fleet management for mines',2016,'10.1111/1234567')
        b=r('2','Fleet management for mines',2016,'10.1111/xxxxxx',source='Scopus')
        self.assertEqual(comparar(a,b)['decision_sugerida'],'REQUIERE_REVISION')
    def test_different_dois_different_titles(self):
        a=r('1','Fleet management for mines',2001,'10.1111/1234567')
        b=r('2','Biochemistry of freshwater mammals',2021,'10.1111/xxxxxx',source='Scopus')
        self.assertEqual(comparar(a,b)['decision_sugerida'],'PUBLICACIONES_DIFERENTES')
    def test_nonlatin_preserved(self):
        self.assertTrue(normalizar_unicode('Методы и средства мониторинга'))
        self.assertTrue(normalizar_unicode('矿山运输优化'))
    def test_doi_year_gap_review(self):
        a=r('1','Advanced drilling reliability models',2010,'10.1111/1234567')
        b=r('2','Advanced drilling reliability models',2020,'10.1111/1234567',source='Scopus')
        self.assertEqual(comparar(a,b)['decision_sugerida'],'REQUIERE_REVISION')
    def test_internal_dup_review(self):
        a=r('1','Advanced drilling reliability models',2010,'10.1111/1234567')
        b=r('2','Advanced drilling reliability models',2010,'10.1111/1234567',source='OpenAlex')
        self.assertEqual(comparar(a,b)['decision_sugerida'],'REQUIERE_REVISION')
    def test_no_doi_title_year_author(self):
        a=r('1','Advanced drilling reliability models',2010,'')
        b=r('2','Advanced drilling reliability models',2010,'',source='Scopus')
        self.assertEqual(comparar(a,b)['decision_sugerida'],'MISMA_PUBLICACION')

if __name__=='__main__':
    unittest.main()
