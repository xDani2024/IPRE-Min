"""Recuenta las etiquetas congeladas de la base amplia y del núcleo v9.

Las etiquetas son menciones automáticas no excluyentes, no foco central
verificado. No altera las propuestas. No consulta OpenAlex.
"""
from pathlib import Path
from collections import Counter
import csv,json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
from matplotlib.ticker import FuncFormatter

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
FIG=HERE/'graficos';FIG.mkdir(exist_ok=True)
SOURCE=ROOT/'04_cierre_v9/salida/Matriz_4735_con_cierre_v9.csv'
with SOURCE.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
core=[r for r in rows if r['decision_nucleo_v9_propuesta']=='IN']
assert len(rows)==4735 and len(core)==419
NAVY='#29475F';GREEN='#356859';GRAY='#B7C0C9';GOLD='#D7AE59';LILAC='#8B7AA8'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
 'axes.spines.right':False,'axes.labelsize':10,'figure.facecolor':'white','savefig.facecolor':'white'})
fmt=lambda n:f'{int(n):,}'.replace(',','.')
def tags(rs,key):
 c=Counter()
 for r in rs:c.update(set(x.strip() for x in r[key].split(';') if x.strip()))
 return dict(c.most_common())
def desc(rs):
 y=Counter(int(r['year']) for r in rs if r['year'].isdigit())
 return {'N':len(rs),'por_ano':dict(sorted(y.items())),
  'antes_2000':sum(n for a,n in y.items() if a<2000),'2000_2025':sum(y[a] for a in range(2000,2026)),
  '2026_incompleto':y[2026],'sin_ano':sum(not r['year'].isdigit() for r in rs),
  **{key:tags(rs,key) for key in ['auto_process_tags','auto_equipment_tags','equipment_title_tags','auto_focus_tags']}}
data={'fecha':'2026-10-08','sha256_matriz_v9':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
 'base_amplia':desc(rows),'nucleo_propuesto_v9':desc(core),
 'v6':dict(Counter('IN' if r['decision_final_propuesta'].startswith('IN') else 'TC' if r['decision_final_propuesta']=='DUDOSO' else 'OUT' for r in rows)),
 'v7':dict(Counter(r['decision_nucleo_v7'] for r in rows)),
 'v8':dict(Counter(r['decision_nucleo_v8_propuesta'] for r in rows)),
 'v9':dict(Counter(r['decision_nucleo_v9_propuesta'] for r in rows)),
 'TC_cierre':dict(Counter(r['disposicion_documental_v9'] for r in rows if r['decision_nucleo_v8_propuesta']=='TC')),
 'metodo':'Un ID por registro; etiquetas no excluyentes heredadas, sin reclasificación de foco central.'}
(HERE/'Resultados_descriptivos_amplio_y_v9.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def save(fig,name):
 fig.savefig(FIG/(name+'.png'),dpi=230,bbox_inches='tight',pad_inches=.13);plt.close(fig)

fig,ax=plt.subplots(figsize=(7.4,3.8));ax.set_xlim(0,10);ax.set_ylim(0,6);ax.axis('off')
def box(x,y,w,h,t,fc='#F4F5F6'):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.05,rounding_size=.07',edgecolor='#9BA3A9',facecolor=fc,lw=.7))
 ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=10)
def arrow(a,b,style='-'):
 ax.add_patch(FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,lw=.8,color='#64717C',linestyle=style))
box(2.9,4.95,4.2,.85,'Universo de partida del análisis\n9.534 registros disponibles')
box(.4,2.35,4,.85,'Base amplia del estudio\n4.735 registros',fc='#EAF0F4')
box(5.6,2.35,4,.85,'Fuera del filtro amplio\n4.799 registros')
arrow((4.35,4.92),(2.4,3.23));arrow((5.65,4.92),(7.6,3.23))
box(.4,.62,4,.85,'Subconjunto de desempeño\n419 IN',fc='#E8F0EC')
box(5.6,.62,4,.85,'Fuera del núcleo propuesto\n4.316 OUT')
arrow((2.4,2.32),(2.4,1.5));arrow((3.55,2.32),(7.6,1.5))
ax.text(5,.07,'Los 419 IN y 4.316 OUT siguen dentro de la base amplia.',ha='center',fontsize=9)
save(fig,'01_flujo_del_estudio')

fig,ax=plt.subplots(figsize=(7.4,3.1))
fig.subplots_adjust(left=.27)
for i,key in enumerate(['v6','v7','v8','v9']):
 left=0
 for label,col in [('IN',GREEN),('OUT',GRAY),('TC',GOLD)]:
  n=data[key].get(label,0);ax.barh(i,n,left=left,height=.52,color=col,label=label if i==0 else None)
  if n:ax.text(left+n/2,i,fmt(n),ha='center',va='center',fontsize=10,color='white' if label=='IN' else '#172027')
  left+=n
ax.set_yticks(range(4),['Primer cribado','Revisión de dudosos','Criterio ajustado','Última revisión']);ax.invert_yaxis()
ax.set_xlim(0,4735);ax.xaxis.set_major_formatter(FuncFormatter(lambda x,p:fmt(x)))
ax.set_xlabel('Propuestas sobre los mismos 4.735 registros');ax.grid(axis='x',color='#DDDDDD',lw=.5);ax.set_axisbelow(True)
ax.legend(ncol=3,frameon=False,loc='upper center',bbox_to_anchor=(.52,-.30));save(fig,'02_versiones_del_cribado')

fig,ax=plt.subplots(figsize=(7.4,2.7))
fig.subplots_adjust(left=.28)
labels=['IN con evidencia','IN humano previo','OUT por foco','OUT documental'];vals=[56,1,616,1726]
ax.barh(range(4),vals,color=[GREEN,LILAC,GRAY,GOLD],height=.6);ax.set_yticks(range(4),labels);ax.invert_yaxis();ax.set_xlim(0,1930)
for i,n in enumerate(vals):ax.text(n+18,i,fmt(n),va='center',fontsize=10)
ax.set_xlabel('Disposición propuesta de los 2.399 antiguos TC');ax.grid(axis='x',color='#DDDDDD',lw=.5);ax.set_axisbelow(True);save(fig,'03_cierre_de_TC')

fig,axes=plt.subplots(2,1,figsize=(7.4,4.05),sharex=True,gridspec_kw={'hspace':.42})
for ax,key,title,col in zip(axes,['base_amplia','nucleo_propuesto_v9'],['Base amplia  |  N total = 4.735','Subconjunto de desempeño  |  N total = 419'],[NAVY,GREEN]):
 d=data[key];ys=list(range(2000,2026));ns=[d['por_ano'].get(y,0) for y in ys]
 ax.bar(ys,ns,color=col,width=.8);ax.set_title(title,loc='left',fontsize=10.5);ax.set_ylabel('Registros');ax.grid(axis='y',color='#DDDDDD',lw=.5);ax.set_axisbelow(True)
 ax.text(2025,ns[-1]+max(ns)*.04,str(ns[-1]),ha='center',fontsize=9);ax.set_ylim(0,max(ns)*1.23)
axes[-1].set_xticks([2000,2005,2010,2015,2020,2025]);axes[-1].set_xlabel('Año de publicación  |  2026 se informa por separado');axes[-1].set_xlim(1999.2,2025.8);save(fig,'04_publicaciones_por_ano')

PROCESS={'caracterizacion_topografia_geomecanica':'Geotecnia y caracterización','tronadura':'Tronadura','perforacion':'Perforación','transporte_acarreo':'Transporte y acarreo','planificacion_programacion':'Planificación y programación','desague_drenaje':'Desagüe y drenaje','carguio':'Carguío','regadio_control_polvo':'Riego y control de polvo','descarga_chancado_botadero':'Descarga y botadero','caminos_pisos_frentes':'Caminos pisos y frentes','mantenimiento_equipos':'Mantenimiento de equipos','limpieza_apoyo_movimiento_material':'Limpieza y apoyo','senalizacion_transito':'Señalización y tránsito','soporte_personal':'Soporte al personal','alimentacion_electrica_cables':'Electricidad y cables'}
keys=list(data['base_amplia']['auto_process_tags']);fig,axes=plt.subplots(1,2,figsize=(7.4,4.25),sharey=True,gridspec_kw={'wspace':.30})
fig.subplots_adjust(left=.34,right=.98)
for ax,which,col,label in zip(axes,['base_amplia','nucleo_propuesto_v9'],[NAVY,GREEN],['Base amplia N = 4.735','Subconjunto N = 419']):
 vals=[data[which]['auto_process_tags'].get(k,0) for k in keys];ax.barh(range(len(keys)),vals,color=col,height=.65);ax.set_title(label,loc='left',fontsize=9.8);ax.set_xlim(0,max(vals)*1.22)
 for i,n in enumerate(vals):ax.text(n+max(vals)*.025,i,fmt(n),va='center',fontsize=8.7)
 ax.grid(axis='x',color='#DDDDDD',lw=.5);ax.set_axisbelow(True);ax.set_xlabel('IDs con etiqueta')
axes[0].set_yticks(range(len(keys)),[PROCESS.get(k,k) for k in keys],fontsize=9);axes[0].invert_yaxis();save(fig,'05_menciones_de_procesos')

EQUIP={'chancador_correa':'Chancador o correa','camion_extraccion':'Camión de extracción','pala_excavadora':'Pala o excavadora','dragalina':'Dragalina','cargador_lhd':'Cargador o LHD','perforadora':'Perforadora','bulldozer':'Bulldozer','surface_miner':'Surface miner','scraper_compactador':'Scraper o compactador','motoniveladora':'Motoniveladora','camion_aljibe':'Camión aljibe','camion_servicio_combustible':'Camión de combustible','bomba_desague':'Bomba de desagüe','wheeldozer':'Wheeldozer'}
keys=list(data['base_amplia']['auto_equipment_tags']);fig,axes=plt.subplots(1,2,figsize=(7.4,4.05),sharey=True,gridspec_kw={'wspace':.28})
fig.subplots_adjust(left=.33,right=.98)
for ax,which,col,title in zip(axes,['base_amplia','nucleo_propuesto_v9'],[NAVY,GREEN],['Base amplia N = 4.735','Subconjunto N = 419']):
 vals=[data[which]['auto_equipment_tags'].get(k,0) for k in keys];ax.barh(range(len(keys)),vals,color=col,height=.65);ax.set_title(title,loc='left',fontsize=9.8);ax.set_xlim(0,max(vals)*1.24)
 for i,n in enumerate(vals):ax.text(n+max(vals)*.025,i,fmt(n),va='center',fontsize=8.7)
 ax.grid(axis='x',color='#DDDDDD',lw=.5);ax.set_axisbelow(True);ax.set_xlabel('IDs con etiqueta')
axes[0].set_yticks(range(len(keys)),[EQUIP.get(k,k) for k in keys],fontsize=9);axes[0].invert_yaxis();save(fig,'06_menciones_de_equipos')

FOCUS={'diseno_planificacion':'Diseño y planificación','desempeno_operacional':'Desempeño operacional','seguridad':'Seguridad','automatizacion_datos':'Automatización y datos','mantenimiento_confiabilidad':'Mantenimiento y confiabilidad','asignacion_programacion_despacho':'Asignación programación y despacho'}
keys=list(data['base_amplia']['auto_focus_tags']);fig,ax=plt.subplots(figsize=(7.4,2.9));ys=list(range(len(keys)))
fig.subplots_adjust(left=.36,right=.98)
for offset,which,col,title in [(-.18,'base_amplia',NAVY,'Base amplia N = 4.735'),(.18,'nucleo_propuesto_v9',GREEN,'Subconjunto N = 419')]:
 vals=[100*data[which]['auto_focus_tags'].get(k,0)/data[which]['N'] for k in keys];ax.barh([y+offset for y in ys],vals,height=.31,color=col,label=title)
 for y,n in zip(ys,vals):ax.text(n+.5,y+offset,f'{n:.1f}'.replace('.',',')+' %',va='center',fontsize=8.5)
ax.set_yticks(ys,[FOCUS.get(k,k).replace('Asignación programación y despacho','Asignación programación\ny despacho') for k in keys],fontsize=9);ax.invert_yaxis();ax.set_xlim(0,79);ax.set_xlabel('Porcentaje con etiqueta dentro de cada base');ax.grid(axis='x',color='#DDDDDD',lw=.5);ax.set_axisbelow(True);ax.legend(loc='upper center',bbox_to_anchor=(.5,-.28),ncol=2,frameon=False,fontsize=9);save(fig,'07_focos_en_cada_base')

hum=json.loads((ROOT/'04_cierre_v9/entrada/decisiones_humanas_conservadas.json').read_text());fig,ax=plt.subplots(figsize=(7.4,2.35))
fig.subplots_adjust(left=.29,right=.98)
for i,prefix in enumerate(['P','H']):
 c=Counter(r['decision_humana'] for r in hum if r['codigo'].startswith(prefix));left=0
 for label,col in [('IN',GREEN),('OUT',GRAY),('TC',GOLD)]:
  n=c.get(label,0);ax.barh(i,n,left=left,height=.50,color=col,label=label if i==0 else None)
  if n:ax.text(left+n/2,i,str(n),ha='center',va='center',fontsize=10,color='white' if label=='IN' else '#172027')
  left+=n
ax.set_yticks([0,1],['Primer piloto actualizado','Segundo lote revisado']);ax.invert_yaxis();ax.set_xlim(0,20);ax.set_xticks([0,5,10,15,20]);ax.set_xlabel('Respuestas humanas históricas con sugerencias visibles');ax.legend(ncol=3,frameon=False,loc='upper center',bbox_to_anchor=(.5,-.38));ax.grid(axis='x',color='#DDDDDD',lw=.5);ax.set_axisbelow(True);save(fig,'08_calibracion_humana')
print('Recuentos y ocho gráficos generados. Base amplia:',len(rows),'| núcleo propuesto:',len(core))
