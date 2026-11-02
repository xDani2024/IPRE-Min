"""Gráficos descriptivos del cribado WoS. No modifica clasificaciones ni decisiones.

Uso desde raíz del proyecto:
  py -3 05_descriptivos/24_generar_graficos.py --resultados resultados_cribado_wos_nueva
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib.ticker import FuncFormatter

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
BLUE='#28475D';GREEN='#34715D';GRAY='#A5B2BB';AMBER='#DAA74C';PURPLE='#78658E'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9.5,
  'axes.spines.top':False,'axes.spines.right':False,
  'figure.facecolor':'white','savefig.facecolor':'white'})

def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def fmt(n):return f'{int(n):,}'.replace(',','.')

def tags(rows,key):
    c=Counter()
    for row in rows:
        c.update(set(v.strip() for v in row.get(key,'').split(';') if v.strip()))
    return dict(c.most_common())

def desc(rows):
    years=Counter(int(r['year']) for r in rows if r.get('year','').isdigit())
    return {'N':len(rows),'por_ano':dict(sorted(years.items())),
        'antes_2000':sum(v for k,v in years.items() if k<2000),
        '2000_2025':sum(v for k,v in years.items() if 2000<=k<=2025),
        '2026_parcial':years[2026],
        'sin_ano':sum(not r.get('year','').isdigit() for r in rows),
        **{k:tags(rows,k) for k in ['auto_process_tags','auto_equipment_tags','equipment_title_tags','auto_focus_tags']}}

def main():
    p=argparse.ArgumentParser(description='Genera los 8 gráficos descriptivos y resumen JSON WoS.')
    p.add_argument('--resultados',default='resultados_cribado_wos',help='Carpeta de resultados (relativa a raíz o absoluta).')
    p.add_argument('--salida',default=None,help='Destino opcional (por defecto, 05_descriptivos).')
    a=p.parse_args()
    folder=Path(a.resultados);folder=folder if folder.is_absolute() else ROOT/folder
    dest=Path(a.salida) if a.salida else HERE
    if not dest.is_absolute(): dest=ROOT/dest
    figdir=dest/'graficos';figdir.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((folder/'RESUMEN_FLUJO_WOS.json').read_text(encoding='utf-8'))
    source=folder/'04_v9_preliminar/matriz_completa_v9_preliminar.csv'
    records=read_csv(source)
    baseline=read_csv(ROOT/'entrada_fase01/01_registros_unicos_normalizados.csv')
    candidates=read_csv(ROOT/'entrada_fase01/04_base_amplia_provisional.csv')
    core=[r for r in records if r['decision_nucleo_v9_propuesta']=='IN']
    ids=[r['wos_id'] for r in records]
    if len(ids)!=len(set(ids)) or {r['wos_id'] for r in candidates}!=set(ids):
        raise ValueError('Los UID WoS de la matriz v9 no coinciden con la base amplia.')
    phases=['v6','v7','v8','v9_solo_reglas']
    if any(sum(manifest[stage].values())!=len(records) for stage in phases):
        raise ValueError('Conteos de las cuatro etapas no suman la misma población.')
    if len(baseline)!=sum(manifest['conteos_fase01'][k] for k in ('sin_resumen','excluidos_filtro_amplio','elegibles_filtro_amplio')):
        raise ValueError('Partición de Fase 1 incoherente.')
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if manifest.get('sha256_matrices',{}).get('v9') != sha:
        raise ValueError('SHA-256 de matriz v9 distinto del manifiesto. Revise la fuente.')
    tc=[r for r in records if r.get('decision_nucleo_v8_propuesta')=='TC']
    tc_counts=dict(Counter(r['disposicion_documental_v9'] for r in tc))
    data={
       'fecha_generacion_utc':datetime.now(timezone.utc).isoformat(),
       'fuente':'Web of Science Core Collection',
       'tipo_resultados':'propuesta automatica sin calibracion humana WoS',
       'carpeta_resultados':folder.name,'sha256_matriz_v9':sha,
       'fase01':manifest['conteos_fase01'],'v6':manifest['v6'],'v7':manifest['v7'],
       'v8':manifest['v8'],'v9_solo_reglas':manifest['v9_solo_reglas'],
       'base_amplia':desc(records),'in_propuestos_computacionalmente':desc(core),
       'tc_v8_resueltos_solo_reglas':tc_counts,
       'muestra_ciega_v6':manifest.get('muestra_ciega_v6'),
       'muestra_distribucion_estimada':{'IN_v6':50,'OUT_v6':50,'DUDOSO_v6':30},
       'alertas_documentales':manifest.get('alertas_documentales',0),
       'grupos_posibles_duplicados':manifest.get('alertas_deduplicacion_grupos',0),
       'revision_humana_realizada':False,
       'advertencias':[
         'Los IN/OUT v9 son propuestas computacionales, NO decisiones definitivas ni revisión humana.',
         'El clasificador v9 resolvió TC por reglas y no por lectura semántica independiente.',
         'Las etiquetas de procesos, equipos y focos son coincidencias no excluyentes; no confirman tema central.',
         'Las fechas editoriales y Early Access pueden diferir; 2026 es un año incompleto.',
         'El gráfico 08 resume únicamente el diseño de la muestra humana, todavía no su calibración.'
       ]}
    (dest/'Resultados_descriptivos_amplio_y_v9_WoS.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    def save(fig,name):
        fig.savefig(figdir/(name+'.png'),dpi=210,bbox_inches='tight',pad_inches=.17)
        plt.close(fig)
    def common(ax):
        ax.grid(axis='x',color='#E3E7EA',lw=.6);ax.set_axisbelow(True)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:fmt(x)))

    # 01: universo y partición, sin sumar subconjuntos como cohortes distintas.
    f,ax=plt.subplots(figsize=(8.1,5.2));ax.axis('off');ax.set_xlim(0,12);ax.set_ylim(0,7.8)
    def node(x,y,w,h,txt,fill):
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.08,rounding_size=.12',
             facecolor=fill,edgecolor='#9AA7B2',linewidth=.9))
        ax.text(x+w/2,y+h/2,txt,ha='center',va='center',fontsize=10,linespacing=1.5)
    def arrow(a,b):ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=13,color='#687784',lw=1))
    n=manifest['conteos_fase01'];node(3.7,6.8,4.6,.7,f"WoS · registros únicos\n{fmt(len(baseline))}",'#E7EDF2')
    node(.1,4.1,3.4,.9,f"Sin resumen\n{fmt(n['sin_resumen'])}",'#F5F6F7')
    node(4.3,4.1,3.4,.9,f"Excluidos filtro amplio\n{fmt(n['excluidos_filtro_amplio'])}",'#F5F6F7')
    node(8.5,4.1,3.4,.9,f"Base amplia\n{fmt(n['elegibles_filtro_amplio'])}",'#E5F0EA')
    for ex in [1.8,6,10.2]:arrow((6,6.75),(ex,5.05))
    node(6.0,1.7,2.8,1,f"Propuesta IN v9\n{fmt(len(core))}",'#DEEFE6')
    node(9.05,1.7,2.8,1,f"Propuesta OUT v9\n{fmt(len(records)-len(core))}",'#EDF0F2')
    arrow((10.2,4.06),(7.4,2.75));arrow((10.2,4.06),(10.45,2.75))
    ax.text(6,.5,'IN y OUT son subdivisiones de la base amplia, todavía sin revisión humana en WoS.',
         ha='center',fontsize=8.9,color='#394B58')
    save(f,'01_flujo_del_estudio')

    # 02: distribución de cada versión sobre los mismos 2.238 registros.
    group={
      'v6':{'IN':manifest['v6'].get('IN_FUERTE',0)+manifest['v6'].get('IN_SECUNDARIO',0),'OUT':manifest['v6'].get('OUT',0),'TC':manifest['v6'].get('DUDOSO',0)},
      'v7':{'IN':manifest['v7'].get('IN',0),'OUT':manifest['v7'].get('OUT',0),'TC':0},
      'v8':{'IN':manifest['v8'].get('IN',0),'OUT':manifest['v8'].get('OUT',0),'TC':manifest['v8'].get('TC',0)},
      'v9':{'IN':manifest['v9_solo_reglas'].get('IN',0),'OUT':manifest['v9_solo_reglas'].get('OUT',0),'TC':0},
    }
    f,ax=plt.subplots(figsize=(9,3.75));f.subplots_adjust(left=.26,bottom=.3)
    for i,(label,phase) in enumerate([('v6 · primer cribado','v6'),('v7 · dudosos','v7'),('v8 · criterio','v8'),('v9 · solo reglas','v9')]):
        pos=0
        for status,col in [('IN',GREEN),('OUT',GRAY),('TC',AMBER)]:
            val=group[phase][status];ax.barh(i,val,left=pos,height=.56,color=col,label=status if i==0 else None)
            if val>50:ax.text(pos+val/2,i,fmt(val),va='center',ha='center',fontsize=9.5,color='white' if status=='IN' else '#15212A')
            pos+=val
    ax.set_yticks(range(4),['v6 · primer cribado','v7 · dudosos','v8 · criterio','v9 · solo reglas']);ax.invert_yaxis()
    ax.set_xlim(0,len(records));common(ax);ax.set_xlabel(f'Registros clasificados en cada etapa (N = {fmt(len(records))})')
    ax.legend(ncol=3,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.26));save(f,'02_versiones_del_cribado')

    # 03: desglose exacto y verificable de antiguos TC.
    labels=[('inclusion_con_evidencia','IN según reglas',GREEN),
            ('exclusion_por_foco','OUT por foco',GRAY),
            ('exclusion_documental','OUT documental',AMBER)]
    f,ax=plt.subplots(figsize=(8.4,3));f.subplots_adjust(left=.28,right=.89,bottom=.22)
    maxv=max([tc_counts.get(k,0) for k,_,_ in labels] or [1]);
    for i,(key,label,color) in enumerate(labels):
        value=tc_counts.get(key,0);ax.barh(i,value,height=.62,color=color);ax.text(value+maxv*.02,i,fmt(value),va='center')
    ax.set_yticks(range(3),[a[1] for a in labels]);ax.invert_yaxis();ax.set_xlim(0,maxv*1.19)
    ax.set_xlabel(f'Disposición automática de los {fmt(len(tc))} casos TC en v8');common(ax)
    save(f,'03_cierre_de_TC')

    # 04: años de publicación según year (no fecha Early Access).
    ybase=data['base_amplia']['por_ano'];ycore=data['in_propuestos_computacionalmente']['por_ano']
    f,axes=plt.subplots(2,1,figsize=(8.4,4.9),sharex=True,gridspec_kw={'hspace':.45})
    years=list(range(2000,2026))
    for ax,series,name,color in [(axes[0],ybase,f'Base amplia · N = {fmt(len(records))}',BLUE),
                                  (axes[1],ycore,f'Propuesta IN v9 · N = {fmt(len(core))}',GREEN)]:
        values=[series.get(y,series.get(str(y),0)) for y in years]
        ax.bar(years,values,width=.8,color=color);ax.set_title(name,loc='left',fontsize=10.2)
        ax.set_ylabel('Registros');ax.grid(axis='y',color='#E4E8E9');ax.set_axisbelow(True)
        ax.set_ylim(0,max(values+[1])*1.17)
    axes[1].set_xticks([2000,2005,2010,2015,2020,2025]);axes[1].set_xlim(1999.4,2025.6)
    axes[1].set_xlabel('Año editorial; 2026 parcial y antes de 2000 se reportan aparte')
    save(f,'04_publicaciones_por_ano')

    def side_chart(filename,field,label_map,title,limit=14):
        base_tags=data['base_amplia'][field]
        chosen=list(base_tags)[:limit]
        if not chosen: return
        f,axes=plt.subplots(1,2,figsize=(10, max(3, 1.0+len(chosen)*.36)),sharey=True,gridspec_kw={'wspace':.22})
        f.subplots_adjust(left=.31,right=.94,top=.90,bottom=.14)
        ymax=max(max(base_tags.values(),default=1),1)
        for ax,subset,col,head in zip(axes,[data['base_amplia'],data['in_propuestos_computacionalmente']],
                 [BLUE,GREEN],[f'Base amplia · {fmt(len(records))}',f'IN propuestos · {fmt(len(core))}']):
            values=[subset[field].get(k,0) for k in chosen]
            ax.barh(range(len(chosen)),values,color=col,height=.66)
            ax.set_title(head,loc='left',fontsize=9.6)
            maxv=max(values+[1]);ax.set_xlim(0,maxv*1.35)
            for i,v in enumerate(values):
                if v:ax.text(v+maxv*.022,i,fmt(v),va='center',fontsize=8.6)
            common(ax);ax.set_xlabel('N.º de registros etiquetados')
        axes[0].set_yticks(range(len(chosen)),[label_map.get(k,k.replace('_',' ')) for k in chosen],fontsize=9)
        axes[0].invert_yaxis();f.suptitle(title,fontsize=10.4,y=.995)
        save(f,filename)
    processes={
       'caracterizacion_topografia_geomecanica':'Geotecnia y caracterización',
       'tronadura':'Tronadura','perforacion':'Perforación','transporte_acarreo':'Transporte y acarreo',
       'planificacion_programacion':'Planificación y programación','desague_drenaje':'Desagüe y drenaje',
       'carguio':'Carguío','regadio_control_polvo':'Regadío y control de polvo',
       'descarga_chancado_botadero':'Descarga y chancado','caminos_pisos_frentes':'Caminos, pisos y frentes',
       'mantenimiento_equipos':'Mantenimiento de equipos',
       'limpieza_apoyo_movimiento_material':'Limpieza y apoyo','senalizacion_transito':'Señalización y tránsito',
       'soporte_personal':'Apoyo al personal','alimentacion_electrica_cables':'Electricidad y cables'}
    equipments={'camion_extraccion':'Camión de extracción','pala_excavadora':'Pala o excavadora',
         'chancador_correa':'Chancador o correa','cargador_lhd':'Cargador o LHD','dragalina':'Dragalina',
         'bulldozer':'Bulldozer','perforadora':'Perforadora','surface_miner':'Surface miner',
         'motoniveladora':'Motoniveladora','camion_servicio_combustible':'Camión de combustible',
         'scraper_compactador':'Scraper/compactador','camion_aljibe':'Camión aljibe',
         'bomba_desague':'Bomba de desagüe','wheeldozer':'Wheeldozer'}
    side_chart('05_menciones_de_procesos','auto_process_tags',processes,
         'Menciones automáticas no excluyentes de procesos')
    side_chart('06_menciones_de_equipos','auto_equipment_tags',equipments,
         'Menciones automáticas no excluyentes de equipos')

    # 07: proporciones dentro de cada grupo (pueden superar 100% en conjunto).
    focus={'diseno_planificacion':'Diseño y planificación','desempeno_operacional':'Desempeño operacional',
           'seguridad':'Seguridad','automatizacion_datos':'Automatización y datos',
           'mantenimiento_confiabilidad':'Mantenimiento y confiabilidad',
           'asignacion_programacion_despacho':'Asignación y despacho'}
    keys=list(data['base_amplia']['auto_focus_tags']);f,ax=plt.subplots(figsize=(9.7,3.5))
    f.subplots_adjust(left=.30,right=.94,bottom=.29,top=.91)
    for off,subset,col,label in [(-.18,data['base_amplia'],BLUE,'Base amplia'),(.18,data['in_propuestos_computacionalmente'],GREEN,'IN propuesto')]:
        values=[100*subset['auto_focus_tags'].get(k,0)/max(subset['N'],1) for k in keys]
        ax.barh([i+off for i in range(len(keys))],values,height=.32,color=col,label=label)
        for i,v in enumerate(values):ax.text(v+.7,i+off,f'{v:.1f} %'.replace('.',','),va='center',fontsize=8.3)
    ax.set_yticks(range(len(keys)),[focus.get(k,k) for k in keys]);ax.invert_yaxis()
    ax.set_xlim(0,max([100*data['base_amplia']['auto_focus_tags'].get(k,0)/len(records) for k in keys]+[0])+24)
    ax.set_xlabel('Porcentaje de registros con la etiqueta en cada conjunto')
    ax.grid(axis='x',color='#E3E7EA');ax.set_axisbelow(True)
    ax.legend(frameon=False,loc='upper center',bbox_to_anchor=(.5,-.26),ncol=2)
    save(f,'07_focos_en_cada_base')

    # 08: NO simula revisión realizada; solo composición prevista de la muestra.
    samplecounts=data['muestra_distribucion_estimada'];f,ax=plt.subplots(figsize=(8.2,3.1))
    f.subplots_adjust(left=.31,right=.92,bottom=.22)
    labels=[('IN_v6','Candidatos IN',GREEN),('OUT_v6','Candidatos OUT',GRAY),
            ('DUDOSO_v6','Dudosos de v6',AMBER)]
    for i,(key,label,col) in enumerate(labels):
        v=samplecounts[key];ax.barh(i,v,color=col,height=.62);ax.text(v+1,i,str(v),va='center')
    ax.set_yticks(range(3),[v[1] for v in labels]);ax.invert_yaxis();ax.set_xlim(0,65)
    ax.set_xlabel(f'Muestra propuesta: {fmt(sum(samplecounts.values()))} registros · sin decisiones humanas registradas')
    common(ax);save(f,'08_muestra_pendiente_revision_humana')
    print(json.dumps({'carpeta_resultados':folder.name,'registros':len(records),'IN_preliminar':len(core),
       'graficos':len(list(figdir.glob('*.png'))),'resumen':str(dest/'Resultados_descriptivos_amplio_y_v9_WoS.json')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
