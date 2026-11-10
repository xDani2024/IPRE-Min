#!/usr/bin/env python3
"""Resumen de discrepancias entre cribado automático y decisiones humanas.

Completar 'decision_humana' con INCLUIR, EXCLUIR o DUDOSO en la muestra.
No modifica originales ni reemplaza juicio académico.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

DECISIONES={'INCLUIR','EXCLUIR','DUDOSO'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--muestra',type=Path,required=True)
    p.add_argument('--salida',type=Path,default=None)
    a=p.parse_args()
    with a.muestra.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    if not rows:
        raise ValueError('Muestra vacía')
    salida=a.salida or a.muestra.parent/'reporte_revision_humana.json'
    n=Counter(); observados=Counter(); discrep=[]
    for row in rows:
        estado=row.get('cribado_automatico','')
        decision=row.get('decision_humana','').strip().upper()
        n[estado]+=1
        if decision and decision not in DECISIONES:
            raise ValueError(f"Decisión no reconocida para {row.get('id_publicacion')}: {decision}")
        if not decision:
            continue
        observados[(estado,decision)]+=1
        if ((estado=='EXCLUSION_PROPUESTA' and decision=='INCLUIR') or
            (estado=='CANDIDATO' and decision=='EXCLUIR')):
            discrep.append(row)
    informe={
        'tamano_muestra':len(rows), 'evaluados':sum(observados.values()),
        'distribucion_muestra':dict(sorted(n.items())),
        'decisiones_por_estado':[{'estado':e,'decision':d,'cantidad':c} for (e,d),c in sorted(observados.items())],
        'discrepancias_claras':len(discrep),
        'advertencia':'La muestra contiene casos centinela y está estratificada por estado. No estimar precisión global sin ponderación y sin revisión independiente.',
    }
    salida.parent.mkdir(parents=True,exist_ok=True)
    salida.write_text(json.dumps(informe,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    if discrep:
        path=salida.with_name('discrepancias_revision_humana.csv')
        with path.open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction='ignore')
            w.writeheader();w.writerows(discrep)
    print('Revisados:', informe['evaluados'],'de', informe['tamano_muestra'])
    print('Diferencias claras:',len(discrep))
    print('Informe:', salida)

if __name__ == '__main__':main()
