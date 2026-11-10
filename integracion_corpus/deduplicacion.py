"""Vinculación cautelosa. No fusiona DOI contradictorios ni títulos discordantes."""
from __future__ import annotations

from collections import defaultdict, Counter
from difflib import SequenceMatcher


class UF:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.sz = [1] * n

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def join(self, a: int, b: int) -> None:
        a, b = self.find(a), self.find(b)
        if a == b:
            return
        if self.sz[a] < self.sz[b]:
            a, b = b, a
        self.p[b] = a
        self.sz[a] += self.sz[b]


def compatibilidad_doi(a: dict, b: dict) -> bool:
    ta, tb = a['titulo_normalizado'], b['titulo_normalizado']
    if ta and tb and SequenceMatcher(None, ta, tb).ratio() < .82:
        return False
    ya, yb = a['anio'], b['anio']
    if ya and yb and abs(int(ya) - int(yb)) > 2:
        return False
    return True


def vincular(registros: list[dict]):
    """Retorna componentes, alertas y métodos, sin modificar las filas de entrada."""
    uf = UF(len(registros))
    por_doi = defaultdict(list)
    por_titulo = defaultdict(list)
    por_titulo_solo = defaultdict(list)
    alertas = []
    links = []
    fuentes_por_grupo = [{r['fuente']} for r in registros]

    def fusionar_si_procede(a: int, b: int, metodo: str) -> bool:
        pa, pb = uf.find(a), uf.find(b)
        if pa == pb:
            return True
        coincidencias = fuentes_por_grupo[pa] & fuentes_por_grupo[pb]
        if coincidencias:
            alertas.append({
                'tipo': 'MULTIPLES_IDS_MISMA_FUENTE_REVISAR',
                'registro_a': registros[a]['registro_uid'],
                'registro_b': registros[b]['registro_uid'],
                'detalle': '|'.join(sorted(coincidencias)),
            })
            return False
        fuentes = fuentes_por_grupo[pa] | fuentes_por_grupo[pb]
        uf.join(pa, pb)
        fuentes_por_grupo[uf.find(pa)] = fuentes
        links.append((a, b, metodo))
        return True

    for i, r in enumerate(registros):
        if r['doi_normalizado']:
            por_doi[r['doi_normalizado']].append(i)
        t, y = r['titulo_normalizado'], r['anio']
        if t and len(t) >= 18 and len(t.split()) >= 3:
            por_titulo_solo[t].append(i)
            if y:
                por_titulo[(t, y)].append(i)
        if r['doi_invalido']:
            alertas.append({'tipo': 'DOI_INVALIDO', 'registro_a': r['registro_uid'], 'registro_b': '',
                            'detalle': r['doi_original']})
        if not t:
            alertas.append({'tipo': 'TITULO_VACIO', 'registro_a': r['registro_uid'], 'registro_b': '', 'detalle': ''})

    # DOI fuerte, pero un DOI reutilizado para títulos muy distintos queda en revisión.
    for doi, indices in sorted(por_doi.items()):
        if len(indices) < 2:
            continue
        representatives = []
        for i in indices:
            compatibles = [j for j in representatives if compatibilidad_doi(registros[i], registros[j])]
            if compatibles:
                for j in compatibles:
                    fusionar_si_procede(i, j, 'doi')
            else:
                for j in representatives:
                    alertas.append({'tipo': 'DOI_TITULOS_O_ANIOS_DIVERGENTES',
                                    'registro_a': registros[j]['registro_uid'],
                                    'registro_b': registros[i]['registro_uid'], 'detalle': doi})
                representatives.append(i)

    # Título y año literalmente normalizados, sin DOI en conflicto.
    for (titulo, anio), indices in sorted(por_titulo.items()):
        if len(indices) < 2:
            continue
        dois = {registros[i]['doi_normalizado'] for i in indices if registros[i]['doi_normalizado']}
        if len(dois) > 1:
            alertas.append({'tipo': 'TITULO_ANIO_DOI_CONFLICTIVOS',
                            'registro_a': registros[indices[0]]['registro_uid'],
                            'registro_b': '|'.join(registros[i]['registro_uid'] for i in indices[1:]),
                            'detalle': '|'.join(sorted(dois))})
            continue
        if not any(not registros[i]['doi_normalizado'] for i in indices):
            # El emparejamiento DOI ya cubrió las referencias compatibles.
            continue
        for i in indices[1:]:
            fusionar_si_procede(indices[0], i, 'titulo_anio')

    # Mismo título, año distinto: solo alerta, nunca fusión por este criterio.
    for titulo, indices in por_titulo_solo.items():
        anios = {registros[i]['anio'] for i in indices if registros[i]['anio']}
        if len(anios) > 1:
            alertas.append({'tipo': 'TITULO_CON_ANIOS_DISTINTOS',
                            'registro_a': registros[indices[0]]['registro_uid'],
                            'registro_b': '|'.join(registros[i]['registro_uid'] for i in indices[1:]),
                            'detalle': '|'.join(sorted(anios))})

    grupos = defaultdict(list)
    for i in range(len(registros)):
        grupos[uf.find(i)].append(i)
    metodos = defaultdict(set)
    for a, b, metodo in links:
        metodos[uf.find(a)].add(metodo)
    return list(grupos.values()), alertas, metodos
