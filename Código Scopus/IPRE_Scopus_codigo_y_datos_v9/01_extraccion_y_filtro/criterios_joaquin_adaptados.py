"""Adaptación transparente del filtro amplio original de Joaquín (v3.0_final).

Fuente: 01_extraccion_y_filtro/02_filtrar_y_unificar.py de IPRE_codigo(1).zip.
Diccionarios, normalización y screen_record se conservan sin editar.
Solo las referencias a identificadores de OpenAlex en la deduplicación
se adaptan a identificadores de Scopus; no se finge que son IDs OpenAlex.
NO se heredan decisiones históricas de OpenAlex a un corpus distinto.
"""
from __future__ import annotations
from functools import lru_cache

@lru_cache(maxsize=50000)
def _similitud_equivalente(a, b):
    if a == b:
        return 1.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()
from typing import Any, Iterable
from functools import lru_cache
import difflib, re, unicodedata, json
OPEN_PIT_PHRASES = ['open pit mining', 'open-pit mining', 'open pit mine', 'open-pit mine', 'surface mining', 'surface mine', 'opencast mining', 'open-cast mining', 'open cut mining', 'open-cut mining', 'open cast mine', 'open-cut mine', 'open pit', 'open-pit', 'opencast', 'open cast', 'surface coal mine', 'tambang terbuka', 'mineria a cielo abierto', 'mina a cielo abierto', 'mina a ceu aberto']
PROCESS_TERMS = {'caracterizacion_topografia_geomecanica': ['mine surveying', 'mine survey', 'topographic survey', 'topography', 'geomechanic', 'geotechnical', 'blast hole sampling', 'blasthole sampling', 'geodetic surveying', 'geodetic survey', 'stockpile volume', 'volume determination', 'volumetric data', 'extracted volume'], 'planificacion_programacion': ['mine planning', 'production planning', 'short-term planning', 'short term planning', 'production scheduling', 'mine scheduling', 'final mining limit', 'mining limit', 'dynamic pit optimization', 'pit orientation', 'open pit orientation', 'open-pit orientation', 'inspection scheduling', 'uav inspection'], 'perforacion': ['drilling', 'drill hole', 'drillhole', 'blasthole', 'blast hole', 'pre-split drilling', 'presplit drilling', 'production drilling'], 'tronadura': ['blasting', 'blast design', 'rock blasting', 'fragmentation', 'blasting fragmentation', 'blast fragmentation', 'blast wave', 'seismic blast wave'], 'carguio': ['loading operation', 'ore loading', 'truck loading', 'loading cycle', 'load and haul', 'loading and hauling', 'shovel-truck', 'shovel truck'], 'transporte_acarreo': ['haulage', 'haul road', 'mine transport', 'ore transport', 'truck haulage', 'truck dispatch', 'fleet dispatch', 'dispatching'], 'descarga_chancado_botadero': ['crusher dumping', 'crusher discharge', 'truck dumping', 'waste dump', 'waste dumping', 'dump site', 'dumping point'], 'caminos_pisos_frentes': ['road maintenance', 'haul road maintenance', 'road construction', 'road condition', 'road quality', 'road grading', 'ramp construction', 'floor maintenance', 'working face preparation', 'loading face preparation'], 'limpieza_apoyo_movimiento_material': ['spill cleanup', 'spillage removal', 'bench cleanup', 'face cleanup', 'dozing', 'stockpile management', 'dump maintenance', 'transverse mining', 'longitudinal stripping'], 'regadio_control_polvo': ['road watering', 'mine watering', 'water spraying', 'dust suppression', 'haul road dust', 'dust control', 'dust concentration', 'dust-concentration', 'dust monitoring', 'dust prediction'], 'alimentacion_electrica_cables': ['mine power supply', 'electrical supply', 'trailing cable', 'cable handling', 'cable reel', 'cable reeler', 'cable management'], 'desague_drenaje': ['mine dewatering', 'pit dewatering', 'mine drainage', 'pit drainage', 'mine pumping', 'pump performance', 'pump shaft'], 'senalizacion_transito': ['mine signage', 'traffic signage', 'traffic management', 'traffic control'], 'mantenimiento_equipos': ['equipment maintenance', 'fleet maintenance', 'mobile equipment maintenance', 'field maintenance', 'equipment repair', 'maintenance management'], 'soporte_personal': ['personnel transport', 'crew transport', 'shift change', 'personnel carrier', 'worker transportation', 'mine catering', 'open pit ventilation', 'open-pit ventilation', 'quarry ventilation', 'quarry fans']}
EQUIPMENT_TERMS = {'perforadora': ['drill rig', 'drill rigs', 'drilling rig', 'drilling rigs', 'blasthole drill', 'blasthole drills', 'blast hole drill', 'blast hole drills', 'rotary drill', 'rotary drills', 'down-the-hole drill', 'down-the-hole drills', 'dth drill', 'dth drills'], 'pala_excavadora': ['shovel', 'shovels', 'mining shovel', 'mining shovels', 'electric rope shovel', 'electric rope shovels', 'rope shovel', 'rope shovels', 'hydraulic shovel', 'hydraulic shovels', 'excavator', 'excavators', 'hydraulic excavator', 'hydraulic excavators', 'mining excavator', 'mining excavators'], 'cargador_lhd': ['loader', 'loaders', 'wheel loader', 'wheel loaders', 'front-end loader', 'front-end loaders', 'front end loader', 'front end loaders', 'load-haul-dump', 'load-haul-dump vehicle', 'load haul dump', 'lhd', 'lhds'], 'camion_extraccion': ['truck', 'trucks', 'haul truck', 'haul trucks', 'mining truck', 'mining trucks', 'mine truck', 'mine trucks', 'off-highway truck', 'off-highway trucks', 'off highway truck', 'off highway trucks', 'rigid dump truck', 'rigid dump trucks', 'dump truck', 'dump trucks'], 'dragalina': ['dragline', 'draglines', 'walking dragline', 'walking draglines'], 'surface_miner': ['surface miner', 'surface miners', 'continuous surface miner'], 'bulldozer': ['bulldozer', 'bulldozers', 'dozer', 'dozers', 'crawler dozer', 'crawler dozers', 'track dozer', 'track dozers'], 'wheeldozer': ['wheel dozer', 'wheel dozers', 'wheeldozer', 'wheeldozers', 'wheeled dozer', 'wheeled dozers'], 'motoniveladora': ['grader', 'graders', 'motor grader', 'motor graders', 'road grader', 'road graders', 'mine grader', 'mine graders'], 'camion_aljibe': ['water truck', 'water trucks', 'water tanker', 'water tankers', 'water cart', 'water carts', 'water bowser', 'water bowsers'], 'equipo_cables': ['cable winder', 'cable winders', 'cable reel truck', 'cable reel trucks', 'cable reeler', 'cable reelers', 'cable handler', 'cable handlers'], 'camion_servicio_combustible': ['service truck', 'service trucks', 'mine service truck', 'mine service trucks', 'fuel truck', 'fuel trucks', 'lube truck', 'lube trucks', 'fuel and lube truck', 'fuel and lube trucks', 'fuel-lube truck', 'fuel-lube trucks'], 'manipulador_neumaticos': ['tire handler', 'tire handlers', 'tyre handler', 'tyre handlers'], 'iluminacion': ['lighting plant', 'lighting plants', 'light tower', 'light towers', 'mobile lighting tower', 'mobile lighting towers'], 'bomba_desague': ['dewatering pump', 'dewatering pumps', 'mine pump', 'mine pumps', 'pit pump', 'pit pumps'], 'unidad_carga_explosivos': ['explosives charging machine', 'explosive charging unit', 'mobile mixing unit', 'mobile manufacturing unit', 'bulk explosive truck'], 'transporte_personal': ['personnel carrier', 'personnel carriers', 'man carrier', 'man carriers', 'crew bus', 'crew buses', 'mine bus', 'mine buses', 'minibus', 'minibuses'], 'chancador_correa': ['crusher', 'crushers', 'mobile crusher', 'mobile crushers', 'crushing plant', 'crushing plants', 'conveyor', 'conveyors', 'belt conveyor', 'belt conveyors', 'in-pit crushing', 'ipcc'], 'scraper_compactador': ['scraper', 'scrapers', 'wheel tractor-scraper', 'wheel tractor-scrapers', 'compactor', 'compactors', 'road roller', 'road rollers']}
EQUIPMENT_QUERY_GROUPS = {'equipos_principales': ['truck', 'trucks', 'haul truck', 'haul trucks', 'dump truck', 'dump trucks', 'shovel', 'shovels', 'excavator', 'excavators', 'loader', 'loaders', 'drill rig', 'drill rigs', 'drilling rig', 'drilling rigs', 'blasthole drill', 'blasthole drills', 'dragline', 'draglines'], 'equipos_auxiliares': ['bulldozer', 'bulldozers', 'dozer', 'dozers', 'wheel dozer', 'wheel dozers', 'motor grader', 'motor graders', 'grader', 'graders', 'water truck', 'water trucks', 'water tanker', 'water tankers', 'cable handler', 'cable handlers', 'cable reeler', 'cable reelers', 'service truck', 'service trucks', 'fuel truck', 'fuel trucks', 'lube truck', 'lube trucks', 'tire handler', 'tire handlers', 'tyre handler', 'tyre handlers', 'light tower', 'light towers', 'dewatering pump', 'dewatering pumps', 'personnel carrier', 'personnel carriers', 'scraper', 'scrapers', 'compactor', 'compactors'], 'equipos_fijos_continuos': ['crusher', 'crushers', 'mobile crusher', 'mobile crushers', 'crushing plant', 'crushing plants', 'conveyor', 'conveyors', 'belt conveyor', 'belt conveyors', 'in-pit crushing', 'ipcc']}
PRINCIPAL_EQUIPMENT_TAGS = {'perforadora', 'pala_excavadora', 'cargador_lhd', 'camion_extraccion', 'surface_miner', 'dragalina'}
AUXILIARY_EQUIPMENT_TAGS = {'bulldozer', 'wheeldozer', 'motoniveladora', 'camion_aljibe', 'equipo_cables', 'camion_servicio_combustible', 'manipulador_neumaticos', 'iluminacion', 'bomba_desague', 'unidad_carga_explosivos', 'transporte_personal', 'scraper_compactador'}
FIXED_EQUIPMENT_TAGS = {'chancador_correa'}
FOCUS_TERMS = {'diseno_planificacion': ['design', 'planning', 'production plan', 'short-term plan', 'short term plan', 'scheduling', 'schedule optimization', 'strategic planning', 'tactical planning'], 'asignacion_programacion_despacho': ['assignment', 'allocation', 'dispatch', 'dispatching', 'fleet management', 'routing', 'task allocation', 'equipment allocation', 'fleet allocation'], 'mantenimiento_confiabilidad': ['maintenance', 'reliability', 'failure', 'breakdown', 'downtime', 'condition monitoring', 'predictive maintenance', 'preventive maintenance'], 'desempeno_operacional': ['operational performance', 'equipment performance', 'productivity', 'efficiency', 'utilization', 'availability', 'overall equipment effectiveness', ' oee ', 'cycle time', 'delay', 'operating time', 'idle time', 'production loss'], 'automatizacion_datos': ['automation', 'autonomous', 'digital twin', 'machine learning', 'artificial intelligence', 'real-time monitoring', 'real time monitoring'], 'seguridad': ['safety', 'collision avoidance', 'fatigue', 'accident', 'risk assessment', 'cold stress', 'thermal stress', 'occupational health']}
OPERATIONAL_SCOPE_TERMS = {'planificacion_diseno': ['open pit', 'open-pit', 'opencast', 'open cast', 'open-cut', 'open cut', 'mine planning', 'open pit design', 'open-pit design', 'pit optimization', 'ultimate pit', 'pit limit', 'production scheduling', 'extraction sequence', 'grade control', 'ore grade', 'copper grade', 'grade changeability', 'grade prediction', 'mining engineering', 'mining operations', 'mine operation', 'optimal depth'], 'geotecnia_monitoreo': ['pit slope', 'mine slope', 'open-pit slope', 'open pit slope', 'pit wall', 'slope stability', 'slope monitoring', 'slope radar', 'ground-based radar', 'insar', 'geotechnical monitoring', 'rock mass deformation', 'backbreak', 'mine slopes', 'coal mine slope', 'open pit wall', 'scarp slope', 'goaf-induced slope subsidence'], 'perforacion_tronadura': ['drilling and blasting', 'drill and blast', 'blast design', 'rock blasting', 'blast-induced', 'blasthole', 'blast hole', 'rock fragmentation'], 'carguio_transporte': ['loading and hauling', 'load and haul', 'truck-shovel', 'shovel-truck', 'haulage', 'haul road', 'truck dispatch', 'fleet dispatch', 'haul fleet', 'material transport cycle', 'truck cycle', 'loading operation', 'loading operations', 'disposal area', 'dozer operation'], 'chancado_transporte_continuo': ['in-pit crushing', 'ipcc', 'crushing and conveying', 'belt conveyor', 'mobile crushing plant', 'cyclical-and-continuous', 'cyclic-flow technology'], 'botaderos_manejo_materiales': ['waste dump', 'internal dump', 'dump stability', 'dumping operation', 'stockpile', 'overburden removal', 'waste rock transportation'], 'agua_polvo_caminos': ['mine dewatering', 'pit dewatering', 'sump dewatering', 'dewatering operations', 'dust suppression', 'haul road dust', 'dust exposure', 'road watering', 'haul road maintenance', 'traffic management'], 'mantenimiento_desempeno': ['equipment maintenance', 'predictive maintenance', 'preventive maintenance', 'equipment reliability', 'equipment availability', 'equipment performance', 'fleet productivity', 'cycle time', 'operational efficiency'], 'automatizacion_seguridad': ['autonomous mining', 'autonomous truck', 'unmanned mining', 'robotic mining', 'fleet management system', 'collision avoidance', 'proximity warning', 'operator safety', 'occupational safety', 'workplace injury', 'respiratory health', 'whole-body vibration', 'intelligent driving', 'open-pit mining adas', 'cyclical-streaming technology', 'mining truck emissions', 'dump truck emissions', 'diesel engine emissions']}
DIRECT_OPERATIONAL_TERMS = {'planificacion_diseno': ['mine planning', 'mine design', 'open pit design', 'open-pit design', 'pit optimization', 'ultimate pit', 'pit limit', 'mining boundary', 'deep mining boundary', 'production scheduling', 'extraction sequence', 'mining method selection', 'surface mine evaluation', 'mine evaluation', 'contract versus owner mining', 'owner mining', 'deferred stripping', 'operational cost', 'operating cost', 'mining cost', 'production cost', 'mine depth', 'optimal depth', 'final side-slope angle', 'final mining limit', 'mining limit', 'dynamic pit optimization', 'pit orientation', 'open pit orientation', 'open-pit orientation', 'open pit to underground', 'open-pit to underground', 'turn open pit mine into underground', 'transition from open pit', 'transition from open-pit'], 'geotecnia_monitoreo': ['pit wall', 'open pit wall', 'open-pit wall', 'pit slope', 'mine slope', 'open pit slope', 'open-pit slope', 'slope stability', 'bench stability', 'slope monitoring', 'slope radar', 'ground-based radar', 'geotechnical monitoring', 'rock mass deformation', 'backbreak', 'pit walls', 'open pit walls', 'open-pit walls', 'mine walls monitoring', 'slope subsidence', 'surface subsidence', 'highwall mining', 'mine slopes', 'coal mine slopes', 'shear-strength degradation', 'mapping and monitoring of open-pit', 'mapping and monitoring of open pit'], 'perforacion_tronadura': ['drilling and blasting', 'drill and blast', 'blast design', 'rock blasting', 'blast-induced', 'blasthole', 'blast hole', 'rock fragmentation', 'blasting vibration', 'flyrock', 'cast blasting', 'blasting fragmentation', 'blast fragmentation', 'blast wave', 'seismic blast wave', 'blasting wave'], 'carguio_transporte': ['loading and hauling', 'load and haul', 'truck-shovel', 'shovel-truck', 'haulage', 'haul road', 'truck dispatch', 'truck dispatching', 'fleet dispatch', 'fleet sizing', 'haul fleet', 'material transport cycle', 'truck cycle', 'loading operation', 'dumping operation', 'dozer operation', 'loading operations', 'material transport cycles', 'transportation process', 'haul rate', 'coal handling system', 'mine transport parameters', 'transverse mining', 'longitudinal stripping', 'stripping method'], 'equipos_mantenimiento': ['surface mining machine', 'surface mining machines', 'opencast mining machine', 'opencast mining machines', 'mining equipment', 'equipment selection', 'equipment maintenance', 'machine diagnosis', 'machines diagnosis', 'predictive maintenance', 'preventive maintenance', 'equipment reliability', 'equipment availability', 'equipment performance', 'fleet productivity', 'equipment effectiveness', 'machines on the production', 'mine facility', 'mine distribution system', 'mechanized complexes', 'mining machines', 'bucket wheel excavator', 'bucket wheel reclaimer', 'bucket-wheel excavator', 'bucket-wheel reclaimer', 'mine spreader', 'opencast mining machine', 'machine of the opencast mining'], 'automatizacion_seguridad': ['autonomous mining', 'autonomous equipment', 'autonomous truck', 'remotely operated equipment', 'unmanned mining', 'robotic mining', 'fleet management system', 'collision avoidance', 'proximity warning', 'safety assessment', 'safety challenge', 'safety training', 'occupational safety', 'occupational risk', 'occupational accident', 'heat stress', 'workplace injury', 'respiratory health', 'whole-body vibration', 'safe control', 'safety performance', 'intelligent driving', 'automatic driving', 'unmanned intelligent transportation', 'mining adas', 'occupational physiology', 'occupational health'], 'agua_polvo_infraestructura': ['mine dewatering', 'pit dewatering', 'sump dewatering', 'mine drainage', 'sediment control', 'dust prevention', 'dust suppression', 'haul road dust', 'road watering', 'haul road maintenance', 'traffic management', 'dust control', 'mine haul roads', 'surface-mine haul roads', 'dust concentration', 'dust-concentration', 'dust monitoring', 'dust prediction', 'mine pumping', 'pump performance', 'pump shaft', 'pump improvement', 'open pit ventilation', 'open-pit ventilation', 'quarry ventilation', 'quarry fans', 'pit ventilation'], 'operacion_general': ['mining operations', 'mine operation', 'open pit operation', 'open-pit operation', 'opencast operation', 'surface mining operation', 'open pit mining technology', 'open-pit mining technology', 'open pit mining technologies', 'open-pit mining technologies', 'mechanization in the mining operations', 'operational efficiency', 'open-pit mining problem', 'open pit mining problem', 'mine mapping', 'mine areas monitoring', 'intelligent open-pit', 'intelligent open pit', 'grade changeability', 'grade control', 'design of open-pit', 'design of open pit', 'mining system', 'process flow diagrams', 'production target', 'semantic segmentation of open-pit', 'semantic segmentation of open pit', 'open pit development', 'open-pit development', 'develop an open pit mine', 'cavity detection', 'detection method for shallow complicated cavities', 'geodetic surveying', 'geodetic survey', 'stockpile volume', 'volume determination', 'volumetric data', 'extracted volume', 'cold stress testing', 'hand cold stress', 'cold stress', 'uav inspection', 'mine inspection', 'inspection scheduling', 'inspection framework', 'open-pit orientation', 'open pit orientation']}
EXCLUSION_OVERRIDE_TITLE_TERMS = ['contract versus owner mining', 'owner mining', 'mining method selection', 'block method of mining', 'surface mining machines diagnosis', 'truck dispatch', 'automatic truck dispatching', 'operational cost data', 'mechanization in the mining operations', 'large tractor dozers', 'open pit mining technologies', 'open-pit mining technologies', 'equipment operation', 'equipment maintenance', 'mine planning', 'mine design', 'pit optimization', 'production scheduling', 'hybrid open pit/underground', 'hybrid open-pit/underground']
HARD_EXCLUSION_TITLE_TERMS = ['longwall', 'block cave', 'block caving', 'cave envelope', 'underground mining', 'underground mobile mining equipment', 'substation', 'sunken bulldozer', 'waste tire', 'waste tires', 'waste tyre', 'waste tyres', 'abandoned underground coal mine', 'abandoned underground coal mines', 'hard-to-recover georesources', 'rheumatoid arthritis']
EXCLUSION_TITLE_TERMS = ['reclamation', 'reclaimed', 'reklamasi', 'revegetasi', 'restoration', 'restore ecosystem', 'earthworm', 'earthworms', 'ecosystem services', 'rebuilding soils', 'native forests', 'native forest', 'post-mining', 'post mining', 'after mine closure', 'pit lake', 'pit lakes', 'forest', 'forestry', 'vegetation', 'ecological', 'ecology', 'biodiversity', 'wildlife', 'habitat', 'soil properties', 'soil degradation', 'mine soil', 'land use', 'land-use', 'land cover', 'watershed', 'water quality', 'sediment yield', 'taxation', 'constitutional', 'social media', 'extractivism', 'leadership', 'community conservation', 'environmental costs', 'environmental impact', 'environmental impacts', 'environmental aspects', 'mitigation measures', 'geology of', 'contract versus owner mining', 'sunken bulldozer', 'soil reconstruction', 'reconstructing soil', 'waste tire', 'waste tires', 'waste tyre', 'waste tyres', 'mine to metal', 'metal accounting', 'trace gases', 'volatile organic compounds', 'processed overburden sand', 'fine aggregate', 'concrete incorporating', '4th industrial revolution', 'fourth industrial revolution', 'labor productivity', 'construction plant', 'science and mining industry', 'hybrid open pit/underground', 'hybrid open-pit/underground', 'substation', 'licensing', 'coal combustion residues', 'nickel laterites', 'fluvial channel', 'prime agricultural land', 'methane sources', 'source apportionment', 'migratory bird', 'hydrologic alteration', 'geoecological', 'legality', 'policy implications', 'tax claims', 'ground truth collection', 'remining to reclaim', 'industry news and products', 'scarp slopes', 'slope mass rating-qslope', 'slope mass rating–qslope', 'co2 emissions', 'environmental degradation', 'pb isotope', 'clean, efficient utilization', 'sample collection, preparation', 'harmful effects of coal mining', "state of miners' health", 'work accidents and economy', 'deep tillage', 'erodibilities', 'survival and growth of hardwoods', "l'environnement", 'analisis lingkungan pengendapan', 'economics of alternative coal transportation', 'reforesting appalachian', 'a is for ark population', 'atmospheric dustfall', 'resource-based city', 'educational concept', 'study program', 'training professional talent', 'curriculum', 'teaching method', 'thesis viva voce']
FINAL_OPERATIONAL_TERMS = ['slope stability', 'bench stability', 'highwall stability', 'pitwall stability', 'pit wall stability', 'slope monitoring', 'probability of failure', 'limit equilibrium', 'kestabilan lereng', 'runoff coefficient', 'mine water balance', 'inpit dump', 'in-pit dump', 'internal dumping', 'dump stability', 'mine simulation', 'mine-system simulation', 'mine system simulation', 'transportation cost', 'transport cost', 'optimal transportation', 'optimal pit', 'block model', 'resource estimation', 'stockpile volume', 'volume stockpile', 'safe thickness of surface mine bench', 'uav', 'ground control point', 'digital surface model', 'dsm', 'remote sensing pre-survey', 'mine pre-survey', 'boulder delineation', 'mine efficiency', 'surface mine efficiency', 'production efficiency', 'air quality index', 'dust segmentation', 'wind field', 'flow field', 'acoustic wave', 'blasting vibration', 'blast-induced', 'flyrock', 'rock fragmentation', 'stripping ratio', 'stripping plan', 'mine sequence', 'production scheduling', 'truck dispatch', 'fleet dispatch', 'haul road', 'haulage', 'loading and hauling', 'ore blending', 'grade control', 'mine dewatering', 'pit dewatering', 'mine drainage', 'pit drainage', 'surface miner', 'mining equipment', 'equipment maintenance', 'equipment reliability', 'equipment performance', 'equipment addition', 'opencast mining technology', 'visualization technique', 'technological system for exploitation', 'railroad tracks', 'windbreak', 'alat gali muat', 'alat angkut', 'target produksi', 'groundwater inflow', 'status of surface mining', 'production capability', 'motor transport', 'prevention countermeasures', 'wall-slope', 'open mining technology', 'open development', 'transfer from open pit mining to underground', 'combined open cast and underground mining', 'belt conveyor', 'in-pit crushing', 'crushing and conveying', 'ipcc']
FINAL_PERIPHERAL_TITLE_TERMS = ['educational concept', 'study program', 'training professional talent', 'curriculum', 'teaching method', 'thesis viva voce', 'air-gas power plant', 'recovery of explosives from military', 'trace gases', 'volatile organic compounds', 'volcano', 'ionospheric', 'pumped storage hydropower', 'tax claims', 'portable water supplies', 'surface mine spoils', 'law review', 'environmental law', 'mine acid water', 'lithosphere sources', 'aerosol contamination', 'riparian wetland', 'acid mine drainage', 'microbial community', 'microbial communities', 'subsidence control regulatory', 'mine drainage quality', 'snow pollution']

@lru_cache(maxsize=60000)
def _normalize_cached(text: str) -> str:
    text = unicodedata.normalize('NFKD', text)
    text = ''.join((ch for ch in text if not unicodedata.combining(ch)))
    text = text.translate(str.maketrans({'‐': '-', '‑': '-', '‒': '-', '–': '-', '—': '-', '−': '-'}))
    return re.sub('\\s+', ' ', text.lower()).strip()

def normalize(text: Any) -> str:
    if text is None:
        return ''
    return _normalize_cached(str(text))

@lru_cache(maxsize=5000)
def term_pattern(term: str) -> re.Pattern[str]:
    normalized_term = normalize(term)
    return re.compile(f'(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])')

def matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    normalized_text = normalize(text)
    matches = []
    for term in terms:
        if normalize(term) in normalized_text and term_pattern(term).search(normalized_text):
            matches.append(term.strip())
    return sorted(set(matches))

def tag_categories(text: str, dictionary: dict[str, list[str]]) -> list[str]:
    return [category for category, terms in dictionary.items() if matched_terms(text, terms)]

def screen_record(record: dict[str, Any], equipment_group: str | None=None) -> tuple[bool, dict[str, Any]]:
    """Clasifica alcance operacional sin ocultar la evidencia del descarte."""
    annotated = dict(record)
    title = str(record.get('title') or '')
    abstract = str(record.get('abstract') or '')
    keywords = str(record.get('keywords') or '')
    topics = str(record.get('topics') or '')
    concepts = str(record.get('concepts') or '')
    context_text = ' '.join([title, abstract])
    tag_text = ' '.join([title, abstract, keywords, topics])
    full_text = ' '.join([title, abstract, keywords, topics, concepts])
    title_exclusions = matched_terms(title, EXCLUSION_TITLE_TERMS)
    hard_title_exclusions = matched_terms(title, HARD_EXCLUSION_TITLE_TERMS)
    hard_exclusion_override = matched_terms(title, ['hybrid open pit/underground', 'hybrid open-pit/underground', 'open pit to underground', 'open-pit to underground', 'transition from open pit', 'transition from open-pit', 'open pit and underground mining', 'open-pit and underground mining', 'open and underground mining', 'surface mining combined with underground', 'open pit mining to underground', 'open-pit mining to underground', 'opencast mining into underground', 'combined open cast and underground', 'transferring open-pit mining to underground', 'underground mining on open pit mining', 'surface mining to underground mining', 'underground mining turned to surface mining', 'transferred from open-pit mining', 'transfer from open pit mining', 'hybrid opencast/underground'])
    title_scope = tag_categories(title, OPERATIONAL_SCOPE_TERMS)
    full_scope = tag_categories(full_text, OPERATIONAL_SCOPE_TERMS)
    title_direct = tag_categories(title, DIRECT_OPERATIONAL_TERMS)
    full_direct = tag_categories(full_text, DIRECT_OPERATIONAL_TERMS)
    title_process = tag_categories(title, PROCESS_TERMS)
    full_process = tag_categories(full_text, PROCESS_TERMS)
    title_equipment = tag_categories(title, EQUIPMENT_TERMS)
    full_equipment = tag_categories(full_text, EQUIPMENT_TERMS)
    title_focus = tag_categories(title, FOCUS_TERMS)
    full_focus = tag_categories(full_text, FOCUS_TERMS)
    title_final = matched_terms(title, FINAL_OPERATIONAL_TERMS)
    full_final = matched_terms(context_text, FINAL_OPERATIONAL_TERMS)
    peripheral_title = matched_terms(title, FINAL_PERIPHERAL_TITLE_TERMS)
    signal_categories = sorted(set(title_scope + full_scope + title_direct + full_direct + title_process + full_process + title_equipment + full_equipment + title_focus + full_focus + title_final + full_final))
    reasons: list[str] = []
    exclusion_override = matched_terms(title, EXCLUSION_OVERRIDE_TITLE_TERMS)
    title_has_context = bool(matched_terms(title, OPEN_PIT_PHRASES))
    has_title_signal = bool(title_direct or title_equipment or title_final or (title_has_context and (title_process or title_focus)))
    has_context = bool(matched_terms(full_text, OPEN_PIT_PHRASES))
    from_equipment_branch = any((group in str(record.get('retrieval_branches') or '') for group in EQUIPMENT_QUERY_GROUPS))
    has_combined_signal = has_context and bool(full_direct or full_final or (full_equipment and (full_process or full_focus)) or (from_equipment_branch and full_equipment))
    has_multiple_direct_signals = len(set(full_direct)) >= 2
    if hard_title_exclusions and (not hard_exclusion_override):
        reasons.append('metodo_subterraneo_fuera_de_alcance:' + '|'.join(hard_title_exclusions))
    if peripheral_title:
        reasons.append('tema_periferico_en_titulo:' + '|'.join(peripheral_title))
    operational_title_override = bool(exclusion_override or title_direct or title_equipment or title_final)
    if title_exclusions and (not operational_title_override):
        reasons.append('tema_excluido_en_titulo:' + '|'.join(title_exclusions))
    if not (has_title_signal or has_combined_signal or has_multiple_direct_signals):
        reasons.append('sin_foco_operacional_suficiente')
    if equipment_group:
        group_terms = EQUIPMENT_QUERY_GROUPS[equipment_group]
        title_group_terms = matched_terms(title, group_terms)
        body_group_terms = matched_terms(abstract, group_terms)
        if not title_group_terms and (not body_group_terms):
            reasons.append('equipo_objetivo_no_central')
    include = not reasons
    annotated['auto_screen_status'] = 'include' if include else 'exclude'
    annotated['auto_screen_reasons'] = '; '.join(reasons)
    annotated['operational_signals'] = '; '.join(signal_categories)
    annotated['matched_open_pit_phrases'] = '; '.join(matched_terms(full_text, OPEN_PIT_PHRASES))
    annotated['auto_process_tags'] = '; '.join(full_process)
    annotated['auto_equipment_tags'] = '; '.join(full_equipment)
    annotated['equipment_title_tags'] = '; '.join(title_equipment)
    annotated['equipment_mention_level'] = 'titulo' if title_equipment else 'resumen_o_palabras_clave' if full_equipment else 'sin_equipo'
    annotated['auto_focus_tags'] = '; '.join(full_focus)
    return (include, annotated)

def screen_records(records: list[dict[str, Any]], equipment_group: str | None=None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for record in records:
        include, annotated = screen_record(record, equipment_group)
        (included if include else excluded).append(annotated)
    return (included, excluded)

def canonical_doi(value: Any) -> str:
    doi = normalize(value)
    doi = re.sub('^https?://(?:dx\\.)?doi\\.org/', '', doi)
    return doi.strip()

@lru_cache(maxsize=50000)
def canonical_title(value: Any) -> str:
    title = normalize(value)
    title = re.sub('[^a-z0-9]+', ' ', title).strip()
    return title if len(title) >= 20 else ''

@lru_cache(maxsize=50000)
def compact_title(value: Any) -> str:
    """Firma conservadora que también detecta espacios/puntuación inconsistentes."""
    title = canonical_title(value)
    compact = re.sub('[^a-z0-9]+', '', title)
    return compact if len(compact) >= 20 else ''

@lru_cache(maxsize=50000)
def canonical_abstract(value: Any) -> str:
    abstract = normalize(value)
    abstract = re.sub('[^a-z0-9]+', ' ', abstract).strip()
    return abstract if len(abstract) >= 250 else ''

def first_author(value: Any) -> str:
    return normalize(str(value or '').split(';')[0])

def record_keys(record: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    doi = canonical_doi(record.get('doi'))
    scopus_id = normalize(record.get('scopus_id'))
    title = canonical_title(record.get('title'))
    title_compact = compact_title(record.get('title'))
    if doi:
        keys.add('doi:' + doi)
    if scopus_id:
        keys.add('scopus:' + scopus_id)
    if title:
        keys.add('title:' + title)
    if title_compact:
        keys.add('title_compact:' + title_compact)
    return keys

def doi_values(value: Any) -> list[str]:
    """Lee listas JSON sin fragmentar los puntos y coma internos de un DOI."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or '').strip()
    if not text:
        return []
    if text.startswith('['):
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError('Se esperaba una lista de DOI')
        return doi_values(parsed)
    return [item.strip() for item in re.split(';\\s*(?=(?:https?://(?:dx\\.)?doi\\.org/)?10\\.\\d{4,9}/)', text, flags=re.I) if item.strip()]

def _split_values(value: Any) -> list[str]:
    return [item.strip() for item in str(value or '').split(';') if item.strip()]

def _merge_record_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(group[0])
    for record in group[1:]:
        for field, value in record.items():
            if not merged.get(field) and value not in (None, ''):
                merged[field] = value
        merged['cited_by'] = max(int(merged.get('cited_by') or 0), int(record.get('cited_by') or 0))
    branches = sorted({item for record in group for item in _split_values(record.get('retrieval_branches'))})
    ids = list(dict.fromkeys((item for record in group for item in _split_values(record.get('merged_scopus_ids') or record.get('scopus_id')))))
    dois = list(dict.fromkeys((item for record in group for item in doi_values(record.get('merged_dois') or record.get('doi')))))
    merged['retrieval_branches'] = '; '.join(branches)
    merged['duplicate_count'] = len(group)
    methods: set[str] = set()
    if len(group) > 1:
        for left_index, left in enumerate(group):
            for right in group[left_index + 1:]:
                if normalize(left.get('scopus_id')) == normalize(right.get('scopus_id')):
                    methods.add('scopus_id')
                if canonical_doi(left.get('doi')) and canonical_doi(left.get('doi')) == canonical_doi(right.get('doi')):
                    methods.add('doi')
                if canonical_title(left.get('title')) and canonical_title(left.get('title')) == canonical_title(right.get('title')):
                    methods.add('normalized_title')
                if compact_title(left.get('title')) and compact_title(left.get('title')) == compact_title(right.get('title')):
                    methods.add('compact_title')
                left_abstract = canonical_abstract(left.get('abstract'))
                right_abstract = canonical_abstract(right.get('abstract'))
                if left_abstract and right_abstract:
                    similarity = _similitud_equivalente(left_abstract, right_abstract)
                    if similarity >= 0.985:
                        methods.add('abstract_similarity')
    flags = sorted({item for record in group for item in _split_values(record.get('quality_flags'))})
    shared_abstract_ids = sorted({item for record in group for item in _split_values(record.get('shared_abstract_scopus_ids'))})
    merged['deduplication_methods'] = '; '.join(sorted(methods))
    merged['quality_flags'] = '; '.join(flags)
    merged['shared_abstract_scopus_ids'] = '; '.join(shared_abstract_ids)
    merged['merged_scopus_ids'] = '; '.join(ids)
    merged['merged_dois'] = json.dumps(dois, ensure_ascii=False)
    return merged

def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Agrupa duplicados por IDs y similitud conservadora de título/resumen."""
    if not records:
        return []
    working = [dict(record) for record in records]
    parent = list(range(len(working)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root, right_root = (find(left), find(right))
        if left_root != right_root:
            parent[right_root] = left_root
    key_owner: dict[str, int] = {}
    for index, record in enumerate(working):
        keys = record_keys(record)
        if not keys:
            continue
        for key in keys:
            if key in key_owner:
                union(index, key_owner[key])
            else:
                key_owner[key] = index
    author_year_groups: dict[tuple[str, str], list[int]] = {}
    for index, record in enumerate(working):
        author = first_author(record.get('authors'))
        year = normalize(record.get('year'))
        if author and year and canonical_abstract(record.get('abstract')):
            author_year_groups.setdefault((author, year), []).append(index)
    for indices in author_year_groups.values():
        for position, left_index in enumerate(indices):
            left = working[left_index]
            left_title = canonical_title(left.get('title'))
            left_abstract = canonical_abstract(left.get('abstract'))
            for right_index in indices[position + 1:]:
                right = working[right_index]
                right_title = canonical_title(right.get('title'))
                right_abstract = canonical_abstract(right.get('abstract'))
                if not (left_title and right_title and left_abstract and right_abstract):
                    continue
                title_similarity = _similitud_equivalente(left_title, right_title)
                abstract_similarity = _similitud_equivalente(left_abstract, right_abstract) if title_similarity >= 0.80 else 0.0
                if title_similarity >= 0.8 and abstract_similarity >= 0.985:
                    union(left_index, right_index)
    abstract_groups: dict[str, list[int]] = {}
    for index, record in enumerate(working):
        abstract = canonical_abstract(record.get('abstract'))
        if abstract:
            abstract_groups.setdefault(abstract, []).append(index)
    for indices in abstract_groups.values():
        if len(indices) < 2:
            continue
        titles = [canonical_title(working[index].get('title')) for index in indices]
        if all((_similitud_equivalente(left, right) >= 0.8 for position, left in enumerate(titles) for right in titles[position + 1:])):
            continue
        shared_ids = sorted({str(working[index].get('scopus_id') or '') for index in indices if working[index].get('scopus_id')})
        for index in indices:
            flags = set(_split_values(working[index].get('quality_flags')))
            flags.add('resumen_compartido_con_titulo_incompatible')
            working[index]['quality_flags'] = '; '.join(sorted(flags))
            working[index]['shared_abstract_scopus_ids'] = '; '.join(shared_ids)
    groups: dict[int, list[dict[str, Any]]] = {}
    order: list[int] = []
    for index, record in enumerate(working):
        root = find(index)
        if root not in groups:
            groups[root] = []
            order.append(root)
        groups[root].append(record)
    return [_merge_record_group(groups[root]) for root in order]
