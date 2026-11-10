#!/usr/bin/env python3
"""Pipeline integrado y reproducible de corpus minero.

Modo congelado: 9.611 filas v2.4 archivadas, reglas amplias v3, historial
de cribado específico, diferencias y muestra humana nueva.
Modo openalex: extracción nueva opcional, documentada como cohorte distinta.
Las etiquetas automáticas no representan elegibilidad humana final.
"""



from __future__ import annotations

import argparse
import csv
import difflib
import json
import os
import random
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


OPENALEX_URL = "https://api.openalex.org/works"
OPENALEX_API_KEY_ENV = "OPENALEX_API_KEY"
SEED = 42
QUERY_VERSION = "3.0_final"
PILOT_OVERSAMPLE_FACTOR = 4

OPEN_PIT_PHRASES = [
    "open pit mining",
    "open-pit mining",
    "open pit mine",
    "open-pit mine",
    "surface mining",
    "surface mine",
    "opencast mining",
    "open-cast mining",
    "open cut mining",
    "open-cut mining",
    "open cast mine",
    "open-cut mine",
    "open pit",
    "open-pit",
    "opencast",
    "open cast",
    "surface coal mine",
    "tambang terbuka",
    "mineria a cielo abierto",
    "mina a cielo abierto",
    "mina a ceu aberto",
]

TECHNICAL_FILTERS = [
    "type:article|review",
    "has_abstract:true",
    "is_retracted:false",
    "is_paratext:false",
]

SELECT_FIELDS = [
    "id",
    "doi",
    "title",
    "publication_year",
    "publication_date",
    "type",
    "language",
    "cited_by_count",
    "abstract_inverted_index",
    "authorships",
    "primary_location",
    "keywords",
    "topics",
    "concepts",
]

# Diccionarios v0.2 construidos desde el informe exploratorio, el mapa SIPOC
# y la revisión del primer piloto de 400 registros.
PROCESS_TERMS = {
    "caracterizacion_topografia_geomecanica": [
        "mine surveying", "mine survey", "topographic survey", "topography",
        "geomechanic", "geotechnical", "blast hole sampling", "blasthole sampling",
        "geodetic surveying", "geodetic survey", "stockpile volume",
        "volume determination", "volumetric data", "extracted volume",
    ],
    "planificacion_programacion": [
        "mine planning", "production planning", "short-term planning",
        "short term planning", "production scheduling", "mine scheduling",
        "final mining limit", "mining limit", "dynamic pit optimization",
        "pit orientation", "open pit orientation", "open-pit orientation",
        "inspection scheduling", "uav inspection",
    ],
    "perforacion": [
        "drilling", "drill hole", "drillhole", "blasthole", "blast hole",
        "pre-split drilling", "presplit drilling", "production drilling",
    ],
    "tronadura": [
        "blasting", "blast design", "rock blasting", "fragmentation",
        "blasting fragmentation", "blast fragmentation", "blast wave",
        "seismic blast wave",
    ],
    "carguio": [
        "loading operation", "ore loading", "truck loading", "loading cycle",
        "load and haul", "loading and hauling", "shovel-truck", "shovel truck",
    ],
    "transporte_acarreo": [
        "haulage", "haul road", "mine transport", "ore transport",
        "truck haulage", "truck dispatch", "fleet dispatch", "dispatching",
    ],
    "descarga_chancado_botadero": [
        "crusher dumping", "crusher discharge", "truck dumping",
        "waste dump", "waste dumping", "dump site", "dumping point",
    ],
    "caminos_pisos_frentes": [
        "road maintenance", "haul road maintenance", "road construction",
        "road condition", "road quality", "road grading", "ramp construction",
        "floor maintenance", "working face preparation", "loading face preparation",
    ],
    "limpieza_apoyo_movimiento_material": [
        "spill cleanup", "spillage removal", "bench cleanup", "face cleanup",
        "dozing", "stockpile management", "dump maintenance",
        "transverse mining", "longitudinal stripping",
    ],
    "regadio_control_polvo": [
        "road watering", "mine watering", "water spraying", "dust suppression",
        "haul road dust", "dust control", "dust concentration", "dust-concentration",
        "dust monitoring",
        "dust prediction",
    ],
    "alimentacion_electrica_cables": [
        "mine power supply", "electrical supply", "trailing cable",
        "cable handling", "cable reel", "cable reeler", "cable management",
    ],
    "desague_drenaje": [
        "mine dewatering", "pit dewatering", "mine drainage", "pit drainage",
        "mine pumping", "pump performance", "pump shaft",
    ],
    "senalizacion_transito": [
        "mine signage", "traffic signage", "traffic management", "traffic control",
    ],
    "mantenimiento_equipos": [
        "equipment maintenance", "fleet maintenance", "mobile equipment maintenance",
        "field maintenance", "equipment repair", "maintenance management",
    ],
    "soporte_personal": [
        "personnel transport", "crew transport", "shift change", "personnel carrier",
        "worker transportation", "mine catering", "open pit ventilation",
        "open-pit ventilation", "quarry ventilation", "quarry fans",
    ],
}

EQUIPMENT_TERMS = {
    "perforadora": [
        "drill rig", "drill rigs", "drilling rig", "drilling rigs",
        "blasthole drill", "blasthole drills", "blast hole drill",
        "blast hole drills", "rotary drill", "rotary drills",
        "down-the-hole drill", "down-the-hole drills", "dth drill", "dth drills",
    ],
    "pala_excavadora": [
        "shovel", "shovels", "mining shovel", "mining shovels",
        "electric rope shovel", "electric rope shovels", "rope shovel",
        "rope shovels", "hydraulic shovel", "hydraulic shovels",
        "excavator", "excavators", "hydraulic excavator",
        "hydraulic excavators", "mining excavator", "mining excavators",
    ],
    "cargador_lhd": [
        "loader", "loaders", "wheel loader", "wheel loaders",
        "front-end loader", "front-end loaders", "front end loader",
        "front end loaders", "load-haul-dump", "load-haul-dump vehicle",
        "load haul dump", "lhd", "lhds",
    ],
    "camion_extraccion": [
        "truck", "trucks", "haul truck", "haul trucks", "mining truck",
        "mining trucks", "mine truck", "mine trucks", "off-highway truck",
        "off-highway trucks", "off highway truck", "off highway trucks",
        "rigid dump truck", "rigid dump trucks", "dump truck", "dump trucks",
    ],
    "dragalina": ["dragline", "draglines", "walking dragline", "walking draglines"],
    "surface_miner": [
        "surface miner", "surface miners", "continuous surface miner",
    ],
    "bulldozer": [
        "bulldozer", "bulldozers", "dozer", "dozers", "crawler dozer",
        "crawler dozers", "track dozer", "track dozers",
    ],
    "wheeldozer": [
        "wheel dozer", "wheel dozers", "wheeldozer", "wheeldozers",
        "wheeled dozer", "wheeled dozers",
    ],
    "motoniveladora": [
        "grader", "graders", "motor grader", "motor graders", "road grader",
        "road graders", "mine grader", "mine graders",
    ],
    "camion_aljibe": [
        "water truck", "water trucks", "water tanker", "water tankers",
        "water cart", "water carts", "water bowser", "water bowsers",
    ],
    "equipo_cables": [
        "cable winder", "cable winders", "cable reel truck", "cable reel trucks",
        "cable reeler", "cable reelers", "cable handler", "cable handlers",
    ],
    "camion_servicio_combustible": [
        "service truck", "service trucks", "mine service truck",
        "mine service trucks", "fuel truck", "fuel trucks", "lube truck",
        "lube trucks", "fuel and lube truck", "fuel and lube trucks",
        "fuel-lube truck", "fuel-lube trucks",
    ],
    "manipulador_neumaticos": [
        "tire handler", "tire handlers", "tyre handler", "tyre handlers",
    ],
    "iluminacion": [
        "lighting plant", "lighting plants", "light tower", "light towers",
        "mobile lighting tower", "mobile lighting towers",
    ],
    "bomba_desague": [
        "dewatering pump", "dewatering pumps", "mine pump", "mine pumps",
        "pit pump", "pit pumps",
    ],
    "unidad_carga_explosivos": [
        "explosives charging machine", "explosive charging unit",
        "mobile mixing unit", "mobile manufacturing unit", "bulk explosive truck",
    ],
    "transporte_personal": [
        "personnel carrier", "personnel carriers", "man carrier", "man carriers",
        "crew bus", "crew buses", "mine bus", "mine buses", "minibus", "minibuses",
    ],
    "chancador_correa": [
        "crusher", "crushers", "mobile crusher", "mobile crushers",
        "crushing plant", "crushing plants", "conveyor", "conveyors",
        "belt conveyor", "belt conveyors", "in-pit crushing", "ipcc",
    ],
    "scraper_compactador": [
        "scraper", "scrapers", "wheel tractor-scraper", "wheel tractor-scrapers",
        "compactor", "compactors", "road roller", "road rollers",
    ],
}

# Se consultan por separado para medir cobertura sin sesgar la muestra global.
EQUIPMENT_QUERY_GROUPS = {
    "equipos_principales": [
        "truck", "trucks", "haul truck", "haul trucks", "dump truck", "dump trucks",
        "shovel", "shovels", "excavator", "excavators", "loader", "loaders",
        "drill rig", "drill rigs", "drilling rig", "drilling rigs",
        "blasthole drill", "blasthole drills", "dragline", "draglines",
    ],
    "equipos_auxiliares": [
        "bulldozer", "bulldozers", "dozer", "dozers", "wheel dozer",
        "wheel dozers", "motor grader", "motor graders", "grader", "graders",
        "water truck", "water trucks", "water tanker", "water tankers",
        "cable handler", "cable handlers", "cable reeler", "cable reelers",
        "service truck", "service trucks", "fuel truck", "fuel trucks",
        "lube truck", "lube trucks", "tire handler", "tire handlers",
        "tyre handler", "tyre handlers", "light tower", "light towers",
        "dewatering pump", "dewatering pumps", "personnel carrier",
        "personnel carriers", "scraper", "scrapers", "compactor", "compactors",
    ],
    "equipos_fijos_continuos": [
        "crusher", "crushers", "mobile crusher", "mobile crushers",
        "crushing plant", "crushing plants", "conveyor", "conveyors",
        "belt conveyor", "belt conveyors", "in-pit crushing", "ipcc",
    ],
}

PRINCIPAL_EQUIPMENT_TAGS = {
    "perforadora", "pala_excavadora", "cargador_lhd", "camion_extraccion",
    "surface_miner", "dragalina",
}
AUXILIARY_EQUIPMENT_TAGS = {
    "bulldozer", "wheeldozer", "motoniveladora", "camion_aljibe",
    "equipo_cables", "camion_servicio_combustible", "manipulador_neumaticos",
    "iluminacion", "bomba_desague", "unidad_carga_explosivos",
    "transporte_personal", "scraper_compactador",
}
FIXED_EQUIPMENT_TAGS = {"chancador_correa"}

FOCUS_TERMS = {
    "diseno_planificacion": [
        "design", "planning", "production plan", "short-term plan", "short term plan",
        "scheduling", "schedule optimization", "strategic planning", "tactical planning",
    ],
    "asignacion_programacion_despacho": [
        "assignment", "allocation", "dispatch", "dispatching", "fleet management",
        "routing", "task allocation", "equipment allocation", "fleet allocation",
    ],
    "mantenimiento_confiabilidad": [
        "maintenance", "reliability", "failure", "breakdown", "downtime",
        "condition monitoring", "predictive maintenance", "preventive maintenance",
    ],
    "desempeno_operacional": [
        "operational performance", "equipment performance", "productivity",
        "efficiency", "utilization", "availability", "overall equipment effectiveness",
        " oee ", "cycle time", "delay", "operating time", "idle time", "production loss",
    ],
    "automatizacion_datos": [
        "automation", "autonomous", "digital twin", "machine learning",
        "artificial intelligence", "real-time monitoring", "real time monitoring",
    ],
    "seguridad": [
        "safety", "collision avoidance", "fatigue", "accident", "risk assessment",
        "cold stress", "thermal stress", "occupational health",
    ],
}


# Señales que vinculan el trabajo con procesos operacionales de una mina a
# cielo abierto. Se aplican después de recuperar los registros: la consulta de
# OpenAlex se mantiene amplia para no sacrificar cobertura y cada exclusión
# queda registrada de forma auditable.
OPERATIONAL_SCOPE_TERMS = {
    "planificacion_diseno": [
        "open pit", "open-pit", "opencast", "open cast", "open-cut", "open cut",
        "mine planning", "open pit design", "open-pit design", "pit optimization",
        "ultimate pit", "pit limit", "production scheduling", "extraction sequence",
        "grade control", "ore grade", "copper grade", "grade changeability",
        "grade prediction", "mining engineering",
        "mining operations", "mine operation", "optimal depth",
    ],
    "geotecnia_monitoreo": [
        "pit slope", "mine slope", "open-pit slope", "open pit slope", "pit wall",
        "slope stability", "slope monitoring", "slope radar", "ground-based radar",
        "insar", "geotechnical monitoring", "rock mass deformation", "backbreak",
        "mine slopes", "coal mine slope", "open pit wall", "scarp slope",
        "goaf-induced slope subsidence",
    ],
    "perforacion_tronadura": [
        "drilling and blasting", "drill and blast", "blast design", "rock blasting",
        "blast-induced", "blasthole", "blast hole", "rock fragmentation",
    ],
    "carguio_transporte": [
        "loading and hauling", "load and haul", "truck-shovel", "shovel-truck",
        "haulage", "haul road", "truck dispatch", "fleet dispatch", "haul fleet",
        "material transport cycle", "truck cycle", "loading operation",
        "loading operations", "disposal area", "dozer operation",
    ],
    "chancado_transporte_continuo": [
        "in-pit crushing", "ipcc", "crushing and conveying", "belt conveyor",
        "mobile crushing plant", "cyclical-and-continuous", "cyclic-flow technology",
    ],
    "botaderos_manejo_materiales": [
        "waste dump", "internal dump", "dump stability", "dumping operation",
        "stockpile", "overburden removal", "waste rock transportation",
    ],
    "agua_polvo_caminos": [
        "mine dewatering", "pit dewatering", "sump dewatering", "dewatering operations",
        "dust suppression", "haul road dust", "dust exposure",
        "road watering", "haul road maintenance", "traffic management",
    ],
    "mantenimiento_desempeno": [
        "equipment maintenance", "predictive maintenance", "preventive maintenance",
        "equipment reliability", "equipment availability", "equipment performance",
        "fleet productivity", "cycle time", "operational efficiency",
    ],
    "automatizacion_seguridad": [
        "autonomous mining", "autonomous truck", "unmanned mining", "robotic mining",
        "fleet management system", "collision avoidance", "proximity warning",
        "operator safety", "occupational safety", "workplace injury",
        "respiratory health", "whole-body vibration", "intelligent driving",
        "open-pit mining adas", "cyclical-streaming technology",
        "mining truck emissions", "dump truck emissions", "diesel engine emissions",
    ],
}

# Señales más discriminantes que la sola aparición de "open pit" o "surface
# mining". Permiten rescatar trabajos operacionales y, al mismo tiempo, evitar
# que una mención incidental al método de explotación vuelva relevante un
# estudio ambiental, geológico o regulatorio.
DIRECT_OPERATIONAL_TERMS = {
    "planificacion_diseno": [
        "mine planning", "mine design", "open pit design", "open-pit design",
        "pit optimization", "ultimate pit", "pit limit", "mining boundary",
        "deep mining boundary", "production scheduling", "extraction sequence",
        "mining method selection", "surface mine evaluation", "mine evaluation",
        "contract versus owner mining", "owner mining", "deferred stripping",
        "operational cost", "operating cost", "mining cost", "production cost",
        "mine depth", "optimal depth", "final side-slope angle",
        "final mining limit", "mining limit", "dynamic pit optimization",
        "pit orientation", "open pit orientation", "open-pit orientation",
        "open pit to underground", "open-pit to underground",
        "turn open pit mine into underground", "transition from open pit",
        "transition from open-pit",
    ],
    "geotecnia_monitoreo": [
        "pit wall", "open pit wall", "open-pit wall", "pit slope", "mine slope",
        "open pit slope", "open-pit slope", "slope stability", "bench stability",
        "slope monitoring", "slope radar", "ground-based radar",
        "geotechnical monitoring", "rock mass deformation", "backbreak",
        "pit walls", "open pit walls", "open-pit walls", "mine walls monitoring",
        "slope subsidence", "surface subsidence", "highwall mining",
        "mine slopes", "coal mine slopes", "shear-strength degradation",
        "mapping and monitoring of open-pit", "mapping and monitoring of open pit",
    ],
    "perforacion_tronadura": [
        "drilling and blasting", "drill and blast", "blast design", "rock blasting",
        "blast-induced", "blasthole", "blast hole", "rock fragmentation",
        "blasting vibration", "flyrock", "cast blasting",
        "blasting fragmentation", "blast fragmentation", "blast wave",
        "seismic blast wave", "blasting wave",
    ],
    "carguio_transporte": [
        "loading and hauling", "load and haul", "truck-shovel", "shovel-truck",
        "haulage", "haul road", "truck dispatch", "truck dispatching",
        "fleet dispatch", "fleet sizing", "haul fleet", "material transport cycle",
        "truck cycle", "loading operation", "dumping operation", "dozer operation",
        "loading operations", "material transport cycles", "transportation process",
        "haul rate", "coal handling system", "mine transport parameters",
        "transverse mining", "longitudinal stripping", "stripping method",
    ],
    "equipos_mantenimiento": [
        "surface mining machine", "surface mining machines", "opencast mining machine",
        "opencast mining machines", "mining equipment", "equipment selection",
        "equipment maintenance", "machine diagnosis", "machines diagnosis",
        "predictive maintenance", "preventive maintenance", "equipment reliability",
        "equipment availability", "equipment performance", "fleet productivity",
        "equipment effectiveness", "machines on the production", "mine facility",
        "mine distribution system", "mechanized complexes", "mining machines",
        "bucket wheel excavator", "bucket wheel reclaimer", "bucket-wheel excavator",
        "bucket-wheel reclaimer", "mine spreader", "opencast mining machine",
        "machine of the opencast mining",
    ],
    "automatizacion_seguridad": [
        "autonomous mining", "autonomous equipment", "autonomous truck",
        "remotely operated equipment", "unmanned mining", "robotic mining",
        "fleet management system", "collision avoidance", "proximity warning",
        "safety assessment", "safety challenge", "safety training",
        "occupational safety", "occupational risk", "occupational accident",
        "heat stress", "workplace injury", "respiratory health",
        "whole-body vibration", "safe control",
        "safety performance", "intelligent driving", "automatic driving",
        "unmanned intelligent transportation", "mining adas",
        "occupational physiology", "occupational health",
    ],
    "agua_polvo_infraestructura": [
        "mine dewatering", "pit dewatering", "sump dewatering", "mine drainage",
        "sediment control", "dust prevention", "dust suppression", "haul road dust",
        "road watering", "haul road maintenance", "traffic management",
        "dust control", "mine haul roads", "surface-mine haul roads",
        "dust concentration", "dust-concentration", "dust monitoring", "dust prediction",
        "mine pumping", "pump performance", "pump shaft", "pump improvement",
        "open pit ventilation", "open-pit ventilation", "quarry ventilation",
        "quarry fans", "pit ventilation",
    ],
    "operacion_general": [
        "mining operations", "mine operation", "open pit operation",
        "open-pit operation", "opencast operation", "surface mining operation",
        "open pit mining technology", "open-pit mining technology",
        "open pit mining technologies", "open-pit mining technologies",
        "mechanization in the mining operations", "operational efficiency",
        "open-pit mining problem", "open pit mining problem", "mine mapping",
        "mine areas monitoring", "intelligent open-pit", "intelligent open pit",
        "grade changeability", "grade control", "design of open-pit",
        "design of open pit", "mining system", "process flow diagrams",
        "production target", "semantic segmentation of open-pit",
        "semantic segmentation of open pit",
        "open pit development", "open-pit development", "develop an open pit mine",
        "cavity detection", "detection method for shallow complicated cavities",
        "geodetic surveying", "geodetic survey", "stockpile volume",
        "volume determination", "volumetric data", "extracted volume",
        "cold stress testing", "hand cold stress", "cold stress",
        "uav inspection", "mine inspection", "inspection scheduling",
        "inspection framework", "open-pit orientation", "open pit orientation",
    ],
}

# Expresiones suficientemente específicas para mantener un estudio aunque el
# título también mencione reclamación, ambiente u otra temática secundaria.
EXCLUSION_OVERRIDE_TITLE_TERMS = [
    "contract versus owner mining", "owner mining", "mining method selection",
    "block method of mining", "surface mining machines diagnosis",
    "truck dispatch", "automatic truck dispatching", "operational cost data",
    "mechanization in the mining operations", "large tractor dozers",
    "open pit mining technologies", "open-pit mining technologies",
    "equipment operation", "equipment maintenance", "mine planning",
    "mine design", "pit optimization", "production scheduling",
    "hybrid open pit/underground", "hybrid open-pit/underground",
]

# Estos métodos son inequívocamente subterráneos para el alcance del corpus.
# Se mantienen como exclusiones duras aun cuando contengan vocabulario de
# planificación o geotecnia.
HARD_EXCLUSION_TITLE_TERMS = [
    "longwall", "block cave", "block caving", "cave envelope",
    "underground mining", "underground mobile mining equipment",
    "substation", "sunken bulldozer", "waste tire", "waste tires",
    "waste tyre", "waste tyres", "abandoned underground coal mine",
    "abandoned underground coal mines",
    "hard-to-recover georesources", "rheumatoid arthritis",
]

# Temas que el piloto 2.0 identificó como principales fuentes de ruido. Solo se
# aplican al título, de modo que una mención ambiental dentro de un estudio
# operacional no lo descarte automáticamente.
EXCLUSION_TITLE_TERMS = [
    "reclamation", "reclaimed", "reklamasi", "revegetasi", "restoration",
    "restore ecosystem", "earthworm", "earthworms", "ecosystem services",
    "rebuilding soils", "native forests", "native forest",
    "post-mining", "post mining", "after mine closure", "pit lake", "pit lakes",
    "forest", "forestry", "vegetation", "ecological", "ecology", "biodiversity",
    "wildlife", "habitat", "soil properties", "soil degradation", "mine soil",
    "land use", "land-use", "land cover", "watershed", "water quality",
    "sediment yield", "taxation", "constitutional", "social media",
    "extractivism", "leadership", "community conservation", "environmental costs",
    "environmental impact", "environmental impacts", "environmental aspects",
    "mitigation measures", "geology of", "contract versus owner mining",
    "sunken bulldozer", "soil reconstruction", "reconstructing soil",
    "waste tire", "waste tires", "waste tyre", "waste tyres", "mine to metal",
    "metal accounting", "trace gases", "volatile organic compounds",
    "processed overburden sand", "fine aggregate", "concrete incorporating",
    "4th industrial revolution", "fourth industrial revolution",
    "labor productivity", "construction plant", "science and mining industry",
    "hybrid open pit/underground", "hybrid open-pit/underground",
    "substation",
    "licensing", "coal combustion residues", "nickel laterites",
    "fluvial channel", "prime agricultural land", "methane sources",
    "source apportionment", "migratory bird", "hydrologic alteration",
    "geoecological", "legality", "policy implications",
    "tax claims", "ground truth collection", "remining to reclaim",
    "industry news and products",
    "scarp slopes", "slope mass rating-qslope", "slope mass rating–qslope",
    "co2 emissions", "environmental degradation", "pb isotope",
    "clean, efficient utilization", "sample collection, preparation",
    "harmful effects of coal mining", "state of miners' health",
    "work accidents and economy", "deep tillage", "erodibilities",
    "survival and growth of hardwoods", "l'environnement",
    "analisis lingkungan pengendapan",
    "economics of alternative coal transportation", "reforesting appalachian",
    "a is for ark population", "atmospheric dustfall", "resource-based city",
    "educational concept", "study program", "training professional talent",
    "curriculum", "teaching method", "thesis viva voce",
]

# Señales operacionales de alta confianza incorporadas después de auditar las
# muestras v2.4 y v2.5. Estas expresiones rescatan trabajos sobre el ciclo
# productivo, infraestructura y control de una mina a cielo abierto que antes
# quedaban fuera por no usar el vocabulario inglés más frecuente.
FINAL_OPERATIONAL_TERMS = [
    "slope stability", "bench stability", "highwall stability", "pitwall stability",
    "pit wall stability", "slope monitoring", "probability of failure",
    "limit equilibrium", "kestabilan lereng", "runoff coefficient", "mine water balance",
    "inpit dump", "in-pit dump", "internal dumping", "dump stability",
    "mine simulation", "mine-system simulation", "mine system simulation",
    "transportation cost", "transport cost", "optimal transportation",
    "optimal pit", "block model", "resource estimation", "stockpile volume",
    "volume stockpile", "safe thickness of surface mine bench",
    "uav", "ground control point", "digital surface model", "dsm",
    "remote sensing pre-survey", "mine pre-survey", "boulder delineation",
    "mine efficiency", "surface mine efficiency", "production efficiency",
    "air quality index", "dust segmentation", "wind field", "flow field",
    "acoustic wave", "blasting vibration", "blast-induced", "flyrock",
    "rock fragmentation", "stripping ratio", "stripping plan", "mine sequence",
    "production scheduling", "truck dispatch", "fleet dispatch", "haul road",
    "haulage", "loading and hauling", "ore blending", "grade control",
    "mine dewatering", "pit dewatering", "mine drainage", "pit drainage",
    "surface miner", "mining equipment", "equipment maintenance",
    "equipment reliability", "equipment performance", "equipment addition",
    "opencast mining technology", "visualization technique",
    "technological system for exploitation", "railroad tracks", "windbreak",
    "alat gali muat", "alat angkut", "target produksi", "groundwater inflow",
    "status of surface mining", "production capability", "motor transport",
    "prevention countermeasures", "wall-slope", "open mining technology",
    "open development",
    "transfer from open pit mining to underground", "combined open cast and underground mining",
    "belt conveyor",
    "in-pit crushing", "crushing and conveying", "ipcc",
]

# Estudios claramente periféricos aunque mencionen una aplicación minera.
FINAL_PERIPHERAL_TITLE_TERMS = [
    "educational concept", "study program", "training professional talent",
    "curriculum", "teaching method", "thesis viva voce",
    "air-gas power plant", "recovery of explosives from military",
    "trace gases", "volatile organic compounds", "volcano", "ionospheric",
    "pumped storage hydropower", "tax claims", "portable water supplies",
    "surface mine spoils", "law review", "environmental law",
    "mine acid water", "lithosphere sources", "aerosol contamination",
    "riparian wetland", "acid mine drainage", "microbial community",
    "microbial communities", "subsidence control regulatory",
    "mine drainage quality", "snow pollution",
]


RAW_FIELDS = [
    "retrieval_branches", "openalex_id", "doi", "title", "year", "publication_date", "type", "language",
    "cited_by", "source", "authors", "institutions", "countries", "keywords",
    "topics", "concepts", "matched_open_pit_phrases", "auto_process_tags",
    "auto_equipment_tags", "equipment_title_tags", "equipment_mention_level",
    "auto_focus_tags", "auto_screen_status",
    "auto_screen_reasons", "operational_signals", "duplicate_count",
    "deduplication_methods", "quality_flags", "shared_abstract_openalex_ids",
    "merged_openalex_ids", "merged_dois", "abstract",
]

REVIEW_FIELDS = [
    "sample_stratum", "retrieval_branches", "openalex_id", "doi", "title", "year", "publication_date",
    "type", "language", "cited_by", "source", "authors", "keywords", "topics",
    "matched_open_pit_phrases", "auto_process_tags", "auto_equipment_tags",
    "equipment_title_tags", "equipment_mention_level",
    "auto_focus_tags", "auto_screen_status", "auto_screen_reasons",
    "operational_signals", "duplicate_count", "merged_openalex_ids", "merged_dois",
    "deduplication_methods", "quality_flags", "shared_abstract_openalex_ids",
    "abstract", "manual_relevant", "manual_exclusion_reason",
    "manual_process_family", "manual_process_detail", "manual_equipment_family",
    "manual_equipment_detail", "manual_focus", "manual_notes",
]

CHANGE_FIELDS = [
    "openalex_id", "doi", "title", "year", "previous_status", "new_status",
    "change_type", "previous_reasons", "new_reasons",
]


@lru_cache(maxsize=60000)
def _normalize_cached(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.translate(str.maketrans({
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    }))
    return re.sub(r"\s+", " ", text.lower()).strip()


def normalize(text: Any) -> str:
    if text is None:
        return ""
    return _normalize_cached(str(text))


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    tokens = sorted(
        ((position, word) for word, positions in inverted_index.items() for position in positions),
        key=lambda item: item[0],
    )
    return " ".join(word for _, word in tokens)


@lru_cache(maxsize=5000)
def term_pattern(term: str) -> re.Pattern[str]:
    normalized_term = normalize(term)
    return re.compile(rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])")


def matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    normalized_text = normalize(text)
    matches = []
    for term in terms:
        if term_pattern(term).search(normalized_text):
            matches.append(term.strip())
    return sorted(set(matches))


def tag_categories(text: str, dictionary: dict[str, list[str]]) -> list[str]:
    return [category for category, terms in dictionary.items() if matched_terms(text, terms)]


def _names(items: list[dict[str, Any]] | None, field: str = "display_name") -> list[str]:
    return [str(item.get(field)) for item in (items or []) if item.get(field)]


def parse_work(work: dict[str, Any]) -> dict[str, Any]:
    abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
    title = work.get("title") or ""
    keywords = _names(work.get("keywords"))
    topics = _names(work.get("topics"))
    concepts = _names(work.get("concepts"))
    text_for_tags = " ".join([title, abstract, *keywords, *topics])

    authors = []
    institutions = []
    countries = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") or {}
        if author.get("display_name"):
            authors.append(author["display_name"])
        for institution in authorship.get("institutions") or []:
            if institution.get("display_name"):
                institutions.append(institution["display_name"])
            if institution.get("country_code"):
                countries.append(institution["country_code"])

    location = work.get("primary_location") or {}
    source = location.get("source") or {}

    title_equipment_tags = tag_categories(title, EQUIPMENT_TERMS)
    all_equipment_tags = tag_categories(text_for_tags, EQUIPMENT_TERMS)
    return {
        "openalex_id": work.get("id") or "",
        "doi": work.get("doi") or "",
        "title": title,
        "year": work.get("publication_year") or "",
        "publication_date": work.get("publication_date") or "",
        "type": work.get("type") or "",
        "language": work.get("language") or "",
        "cited_by": int(work.get("cited_by_count") or 0),
        "source": source.get("display_name") or "",
        "authors": "; ".join(dict.fromkeys(authors)),
        "institutions": "; ".join(dict.fromkeys(institutions)),
        "countries": "; ".join(dict.fromkeys(countries)),
        "keywords": "; ".join(keywords),
        "topics": "; ".join(topics),
        "concepts": "; ".join(concepts),
        "matched_open_pit_phrases": "; ".join(matched_terms(f"{title} {abstract}", OPEN_PIT_PHRASES)),
        "auto_process_tags": "; ".join(tag_categories(text_for_tags, PROCESS_TERMS)),
        "auto_equipment_tags": "; ".join(all_equipment_tags),
        "equipment_title_tags": "; ".join(title_equipment_tags),
        "equipment_mention_level": (
            "titulo" if title_equipment_tags
            else "resumen_o_palabras_clave" if all_equipment_tags
            else "sin_equipo"
        ),
        "auto_focus_tags": "; ".join(tag_categories(text_for_tags, FOCUS_TERMS)),
        "auto_screen_status": "",
        "auto_screen_reasons": "",
        "operational_signals": "",
        "duplicate_count": 1,
        "deduplication_methods": "",
        "quality_flags": "",
        "shared_abstract_openalex_ids": "",
        "merged_openalex_ids": work.get("id") or "",
        "merged_dois": work.get("doi") or "",
        "abstract": abstract,
    }


def screen_record(
    record: dict[str, Any],
    equipment_group: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Clasifica alcance operacional sin ocultar la evidencia del descarte."""
    annotated = dict(record)
    title = str(record.get("title") or "")
    abstract = str(record.get("abstract") or "")
    keywords = str(record.get("keywords") or "")
    topics = str(record.get("topics") or "")
    concepts = str(record.get("concepts") or "")
    context_text = " ".join([title, abstract])
    tag_text = " ".join([title, abstract, keywords, topics])
    full_text = " ".join([title, abstract, keywords, topics, concepts])

    title_exclusions = matched_terms(title, EXCLUSION_TITLE_TERMS)
    hard_title_exclusions = matched_terms(title, HARD_EXCLUSION_TITLE_TERMS)
    hard_exclusion_override = matched_terms(title, [
        "hybrid open pit/underground", "hybrid open-pit/underground",
        "open pit to underground", "open-pit to underground",
        "transition from open pit", "transition from open-pit",
        "open pit and underground mining", "open-pit and underground mining",
        "open and underground mining", "surface mining combined with underground",
        "open pit mining to underground", "open-pit mining to underground",
        "opencast mining into underground", "combined open cast and underground",
        "transferring open-pit mining to underground",
        "underground mining on open pit mining", "surface mining to underground mining",
        "underground mining turned to surface mining",
        "transferred from open-pit mining", "transfer from open pit mining",
        "hybrid opencast/underground",
    ])
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

    signal_categories = sorted(
        set(
            title_scope + full_scope + title_direct + full_direct
            + title_process + full_process + title_equipment + full_equipment
            + title_focus + full_focus + title_final + full_final
        )
    )
    reasons: list[str] = []

    exclusion_override = matched_terms(title, EXCLUSION_OVERRIDE_TITLE_TERMS)
    title_has_context = bool(matched_terms(title, OPEN_PIT_PHRASES))
    # En títulos que nombran explícitamente minería a cielo abierto, una señal
    # de proceso o foco (p. ej. scheduling, inspection o safety) es suficiente.
    # Esto mejora la recuperación sin aceptar títulos genéricos que solo
    # mencionan una técnica fuera del contexto minero.
    has_title_signal = bool(
        title_direct
        or title_equipment
        or title_final
        or (title_has_context and (title_process or title_focus))
    )
    has_context = bool(matched_terms(full_text, OPEN_PIT_PHRASES))
    from_equipment_branch = any(
        group in str(record.get("retrieval_branches") or "")
        for group in EQUIPMENT_QUERY_GROUPS
    )
    has_combined_signal = has_context and bool(
        full_direct
        or full_final
        or (full_equipment and (full_process or full_focus))
        or (from_equipment_branch and full_equipment)
    )
    has_multiple_direct_signals = len(set(full_direct)) >= 2

    if hard_title_exclusions and not hard_exclusion_override:
        reasons.append(
            "metodo_subterraneo_fuera_de_alcance:" + "|".join(hard_title_exclusions)
        )

    # Una exclusión temática se puede revertir si el propio título demuestra
    # que el artículo estudia un proceso o equipo operacional. Esto evita, por
    # ejemplo, descartar trabajos de dozers que también tratan reclamación.
    if peripheral_title:
        reasons.append("tema_periferico_en_titulo:" + "|".join(peripheral_title))

    operational_title_override = bool(
        exclusion_override or title_direct or title_equipment or title_final
    )
    if title_exclusions and not operational_title_override:
        reasons.append("tema_excluido_en_titulo:" + "|".join(title_exclusions))

    if not (has_title_signal or has_combined_signal or has_multiple_direct_signals):
        reasons.append("sin_foco_operacional_suficiente")

    if equipment_group:
        group_terms = EQUIPMENT_QUERY_GROUPS[equipment_group]
        title_group_terms = matched_terms(title, group_terms)
        body_group_terms = matched_terms(abstract, group_terms)
        if not title_group_terms and not body_group_terms:
            reasons.append("equipo_objetivo_no_central")

    include = not reasons
    annotated["auto_screen_status"] = "include" if include else "exclude"
    annotated["auto_screen_reasons"] = "; ".join(reasons)
    annotated["operational_signals"] = "; ".join(signal_categories)
    annotated["matched_open_pit_phrases"] = "; ".join(
        matched_terms(full_text, OPEN_PIT_PHRASES)
    )
    annotated["auto_process_tags"] = "; ".join(full_process)
    annotated["auto_equipment_tags"] = "; ".join(full_equipment)
    annotated["equipment_title_tags"] = "; ".join(title_equipment)
    annotated["equipment_mention_level"] = (
        "titulo" if title_equipment
        else "resumen_o_palabras_clave" if full_equipment
        else "sin_equipo"
    )
    annotated["auto_focus_tags"] = "; ".join(full_focus)
    return include, annotated


def screen_records(
    records: list[dict[str, Any]],
    equipment_group: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for record in records:
        include, annotated = screen_record(record, equipment_group)
        (included if include else excluded).append(annotated)
    return included, excluded


def build_context_filter() -> str:
    return "title_and_abstract.search.exact:" + "|".join(
        f'"{phrase}"' for phrase in OPEN_PIT_PHRASES
    )


def build_filter() -> str:
    return ",".join([build_context_filter(), *TECHNICAL_FILTERS])


def build_equipment_filter(group: str) -> str:
    terms = EQUIPMENT_QUERY_GROUPS[group]
    equipment_filter = "title_and_abstract.search.exact:" + "|".join(
        f'"{term}"' for term in terms
    )
    return ",".join([build_context_filter(), equipment_filter, *TECHNICAL_FILTERS])


def request_json(url: str, retries: int = 12) -> dict[str, Any]:
    headers = {"User-Agent": f"IPRE-open-pit-corpus/{QUERY_VERSION}"}
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise RuntimeError(
                    "OpenAlex rechazó la API key. Cárgala nuevamente en OPENALEX_API_KEY."
                ) from None
            if exc.code not in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"OpenAlex respondió HTTP {exc.code}.") from None
            if attempt == retries - 1:
                raise RuntimeError(
                    f"OpenAlex siguió respondiendo HTTP {exc.code} después de {retries} intentos."
                ) from None
            wait_seconds = min(2 ** attempt, 30)
            print(f"  OpenAlex respondió {exc.code}; reintento en {wait_seconds}s")
            time.sleep(wait_seconds)
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError("No fue posible conectar con OpenAlex.") from exc
            wait_seconds = min(2 ** attempt, 30)
            print(f"  Error de conexión; reintento en {wait_seconds}s")
            time.sleep(wait_seconds)
    raise RuntimeError("No fue posible obtener una respuesta de OpenAlex")


def build_url(
    params: dict[str, Any],
    mailto: str | None,
    api_key: str | None,
) -> str:
    final_params = dict(params)
    if mailto:
        final_params["mailto"] = mailto
    if api_key:
        final_params["api_key"] = api_key
    return f"{OPENALEX_URL}?{urllib.parse.urlencode(final_params)}"


def fetch_count(
    filter_value: str,
    mailto: str | None,
    api_key: str | None,
) -> int:
    url = build_url(
        {"filter": filter_value, "per_page": 1, "select": "id"},
        mailto,
        api_key,
    )
    payload = request_json(url)
    return int((payload.get("meta") or {}).get("count") or 0)


def fetch_basic_records(
    filter_value: str,
    limit: int,
    branch: str,
    mailto: str | None,
    api_key: str | None,
    delay_seconds: float,
    sort: str | None = None,
    sample_seed: int | None = None,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    records: list[dict[str, Any]] = []
    page = 1
    while len(records) < limit:
        params: dict[str, Any] = {
            "filter": filter_value,
            "select": ",".join(SELECT_FIELDS),
            "per_page": 100,
            "page": page,
        }
        if sort:
            params["sort"] = sort
        if sample_seed is not None:
            params["sample"] = limit
            params["seed"] = sample_seed
        payload = request_json(build_url(params, mailto, api_key))
        results = payload.get("results") or []
        if not results:
            break
        for work in results:
            parsed = parse_work(work)
            parsed["retrieval_branches"] = branch
            records.append(parsed)
        print(f"  {branch}: {min(len(records), limit)} / {limit}")
        if len(results) < 100 or len(records) >= limit:
            break
        page += 1
        time.sleep(delay_seconds)
    return records[:limit]


def _load_checkpoint(
    checkpoint_path: Path,
    state_path: Path,
) -> tuple[list[dict[str, Any]], str, int, int]:
    if not checkpoint_path.exists() or not state_path.exists():
        return [], "*", 0, 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("query_version") != QUERY_VERSION:
        raise RuntimeError(
            "El directorio contiene un checkpoint de otra versión. Usa un directorio de salida nuevo."
        )
    records = []
    with checkpoint_path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                records.append(json.loads(line))
    return (
        records,
        state.get("next_cursor") or "*",
        int(state.get("reported_total") or 0),
        int(state.get("next_page") or 1),
    )


def _append_checkpoint(checkpoint_path: Path, records: list[dict[str, Any]]) -> None:
    with checkpoint_path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_state(
    state_path: Path,
    cursor: str | None,
    reported_total: int,
    next_page: int,
) -> None:
    temporary_path = state_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(
            {
                "query_version": QUERY_VERSION,
                "next_cursor": cursor,
                "reported_total": reported_total,
                "next_page": next_page,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary_path.replace(state_path)


def download_full_records(
    output_dir: Path,
    max_records: int | None,
    mailto: str | None,
    api_key: str | None,
    delay_seconds: float,
) -> tuple[list[dict[str, Any]], int]:
    checkpoint_path = output_dir / ".open_pit_download_checkpoint.jsonl"
    state_path = output_dir / ".open_pit_download_state.json"
    parsed_records, cursor, reported_total, page = _load_checkpoint(checkpoint_path, state_path)
    if parsed_records:
        print(f"  Reanudando descarga completa: {len(parsed_records)} registros")

    while cursor:
        params = {
            "filter": build_filter(),
            "select": ",".join(SELECT_FIELDS),
            "per_page": 100,
            "cursor": cursor,
        }
        payload = request_json(build_url(params, mailto, api_key))
        reported_total = int((payload.get("meta") or {}).get("count") or reported_total)
        results = payload.get("results") or []
        if not results:
            break
        page_records = []
        for work in results:
            parsed = parse_work(work)
            parsed["retrieval_branches"] = "general_full"
            page_records.append(parsed)
        parsed_records.extend(page_records)
        print(f"  Página {page:>3} | descargados: {len(parsed_records):>5} / {reported_total}")
        if max_records and len(parsed_records) >= max_records:
            parsed_records = parsed_records[:max_records]
            break
        cursor = (payload.get("meta") or {}).get("next_cursor")
        _append_checkpoint(checkpoint_path, page_records)
        _write_state(state_path, cursor, reported_total, page + 1)
        page += 1
        time.sleep(delay_seconds)
    return parsed_records, reported_total


def canonical_doi(value: Any) -> str:
    doi = normalize(value)
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    return doi.strip()


def canonical_title(value: Any) -> str:
    title = normalize(value)
    title = re.sub(r"[^a-z0-9]+", " ", title).strip()
    return title if len(title) >= 20 else ""


def compact_title(value: Any) -> str:
    """Firma conservadora que también detecta espacios/puntuación inconsistentes."""
    title = canonical_title(value)
    compact = re.sub(r"[^a-z0-9]+", "", title)
    return compact if len(compact) >= 20 else ""


def canonical_abstract(value: Any) -> str:
    abstract = normalize(value)
    abstract = re.sub(r"[^a-z0-9]+", " ", abstract).strip()
    return abstract if len(abstract) >= 250 else ""


def first_author(value: Any) -> str:
    return normalize(str(value or "").split(";")[0])


def record_keys(record: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    doi = canonical_doi(record.get("doi"))
    openalex_id = normalize(record.get("openalex_id"))
    title = canonical_title(record.get("title"))
    title_compact = compact_title(record.get("title"))
    if doi:
        keys.add("doi:" + doi)
    if openalex_id:
        keys.add("openalex:" + openalex_id)
    if title:
        keys.add("title:" + title)
    if title_compact:
        keys.add("title_compact:" + title_compact)
    return keys


def _split_values(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def _merge_record_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    merged = dict(group[0])
    for record in group[1:]:
        for field, value in record.items():
            if not merged.get(field) and value not in (None, ""):
                merged[field] = value
        merged["cited_by"] = max(
            int(merged.get("cited_by") or 0), int(record.get("cited_by") or 0)
        )

    branches = sorted({item for record in group for item in _split_values(record.get("retrieval_branches"))})
    ids = list(dict.fromkeys(
        item for record in group
        for item in _split_values(record.get("merged_openalex_ids") or record.get("openalex_id"))
    ))
    dois = list(dict.fromkeys(
        item for record in group
        for item in _split_values(record.get("merged_dois") or record.get("doi"))
    ))
    merged["retrieval_branches"] = "; ".join(branches)
    merged["duplicate_count"] = len(group)
    methods: set[str] = set()
    if len(group) > 1:
        for left_index, left in enumerate(group):
            for right in group[left_index + 1:]:
                if normalize(left.get("openalex_id")) == normalize(right.get("openalex_id")):
                    methods.add("openalex_id")
                if canonical_doi(left.get("doi")) and canonical_doi(left.get("doi")) == canonical_doi(right.get("doi")):
                    methods.add("doi")
                if canonical_title(left.get("title")) and canonical_title(left.get("title")) == canonical_title(right.get("title")):
                    methods.add("normalized_title")
                if compact_title(left.get("title")) and compact_title(left.get("title")) == compact_title(right.get("title")):
                    methods.add("compact_title")
                left_abstract = canonical_abstract(left.get("abstract"))
                right_abstract = canonical_abstract(right.get("abstract"))
                if left_abstract and right_abstract:
                    similarity = difflib.SequenceMatcher(
                        None, left_abstract, right_abstract, autojunk=False
                    ).ratio()
                    if similarity >= 0.985:
                        methods.add("abstract_similarity")

    flags = sorted({
        item for record in group for item in _split_values(record.get("quality_flags"))
    })
    shared_abstract_ids = sorted({
        item
        for record in group
        for item in _split_values(record.get("shared_abstract_openalex_ids"))
    })
    merged["deduplication_methods"] = "; ".join(sorted(methods))
    merged["quality_flags"] = "; ".join(flags)
    merged["shared_abstract_openalex_ids"] = "; ".join(shared_abstract_ids)
    merged["merged_openalex_ids"] = "; ".join(ids)
    merged["merged_dois"] = "; ".join(dois)
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
        left_root, right_root = find(left), find(right)
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

    # Duplicados sin DOI suelen aparecer como informe y artículo con títulos
    # ligeramente distintos. Solo se unen cuando coinciden año y primer autor,
    # los resúmenes son casi idénticos y los títulos mantienen alta similitud.
    author_year_groups: dict[tuple[str, str], list[int]] = {}
    for index, record in enumerate(working):
        author = first_author(record.get("authors"))
        year = normalize(record.get("year"))
        if author and year and canonical_abstract(record.get("abstract")):
            author_year_groups.setdefault((author, year), []).append(index)

    for indices in author_year_groups.values():
        for position, left_index in enumerate(indices):
            left = working[left_index]
            left_title = canonical_title(left.get("title"))
            left_abstract = canonical_abstract(left.get("abstract"))
            for right_index in indices[position + 1:]:
                right = working[right_index]
                right_title = canonical_title(right.get("title"))
                right_abstract = canonical_abstract(right.get("abstract"))
                if not (left_title and right_title and left_abstract and right_abstract):
                    continue
                title_similarity = difflib.SequenceMatcher(
                    None, left_title, right_title, autojunk=False
                ).ratio()
                abstract_similarity = difflib.SequenceMatcher(
                    None, left_abstract, right_abstract, autojunk=False
                ).ratio()
                if title_similarity >= 0.80 and abstract_similarity >= 0.985:
                    union(left_index, right_index)

    # Un mismo resumen asociado a títulos incompatibles se marca para revisión,
    # pero no se fusiona automáticamente: puede ser un error de metadatos.
    abstract_groups: dict[str, list[int]] = {}
    for index, record in enumerate(working):
        abstract = canonical_abstract(record.get("abstract"))
        if abstract:
            abstract_groups.setdefault(abstract, []).append(index)
    for indices in abstract_groups.values():
        if len(indices) < 2:
            continue
        titles = [canonical_title(working[index].get("title")) for index in indices]
        if all(
            difflib.SequenceMatcher(None, left, right, autojunk=False).ratio() >= 0.80
            for position, left in enumerate(titles)
            for right in titles[position + 1:]
        ):
            continue
        shared_ids = sorted({
            str(working[index].get("openalex_id") or "")
            for index in indices if working[index].get("openalex_id")
        })
        for index in indices:
            flags = set(_split_values(working[index].get("quality_flags")))
            flags.add("resumen_compartido_con_titulo_incompatible")
            working[index]["quality_flags"] = "; ".join(sorted(flags))
            working[index]["shared_abstract_openalex_ids"] = "; ".join(shared_ids)

    groups: dict[int, list[dict[str, Any]]] = {}
    order: list[int] = []
    for index, record in enumerate(working):
        root = find(index)
        if root not in groups:
            groups[root] = []
            order.append(root)
        groups[root].append(record)
    return [_merge_record_group(groups[root]) for root in order]


def take_unique(
    records: list[dict[str, Any]],
    target: int,
    seen: set[str],
    stratum: str,
) -> list[dict[str, Any]]:
    selected = []
    for record in records:
        keys = record_keys(record)
        if not keys or keys & seen:
            continue
        seen.update(keys)
        selected.append({"sample_stratum": stratum, **record})
        if len(selected) >= target:
            break
    return selected


def sample_targets(sample_size: int) -> tuple[int, int, int]:
    top = sample_size // 4
    recent = sample_size // 4
    random_target = sample_size - top - recent
    return top, recent, random_target


def build_global_review_sample(
    top_records: list[dict[str, Any]],
    recent_records: list[dict[str, Any]],
    random_records: list[dict[str, Any]],
    sample_size: int,
) -> list[dict[str, Any]]:
    top_target, recent_target, random_target = sample_targets(sample_size)
    seen: set[str] = set()
    output = []
    output.extend(take_unique(top_records, top_target, seen, "mas_citados_global"))
    output.extend(take_unique(recent_records, recent_target, seen, "mas_recientes_global"))
    output.extend(take_unique(random_records, random_target, seen, "aleatorios_global"))
    if len(output) < sample_size:
        filler = deduplicate([*random_records, *recent_records, *top_records])
        output.extend(take_unique(filler, sample_size - len(output), seen, "relleno_global"))
    return output


def build_global_sample_from_corpus(
    included: list[dict[str, Any]], sample_size: int
) -> list[dict[str, Any]]:
    """Construye la muestra directamente desde el corpus final."""
    top = sorted(included, key=lambda row: int(row.get("cited_by") or 0), reverse=True)
    recent = sorted(
        included,
        key=lambda row: (str(row.get("publication_date") or ""), str(row.get("year") or "")),
        reverse=True,
    )
    random_records = list(included)
    random.Random(SEED).shuffle(random_records)
    return build_global_review_sample(top, recent, random_records, sample_size)


def _split_tag_values(value: Any) -> set[str]:
    return {item.strip() for item in str(value or "").split(";") if item.strip()}


def _record_equipment_groups(record: dict[str, Any]) -> set[str]:
    tags = _split_tag_values(record.get("auto_equipment_tags"))
    groups: set[str] = set()
    if tags & PRINCIPAL_EQUIPMENT_TAGS:
        groups.add("equipos_principales")
    if tags & AUXILIARY_EQUIPMENT_TAGS:
        groups.add("equipos_auxiliares")
    if tags & FIXED_EQUIPMENT_TAGS:
        groups.add("equipos_fijos_continuos")
    return groups


def build_equipment_sample_from_corpus(
    included: list[dict[str, Any]], sample_size: int
) -> list[dict[str, Any]]:
    """Sobremuestra equipos y distingue menciones centrales de secundarias."""
    allocations = equipment_allocations(sample_size)
    rng = random.Random(SEED + 1)
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for group in ["equipos_auxiliares", "equipos_principales", "equipos_fijos_continuos"]:
        candidates = [row for row in included if group in _record_equipment_groups(row)]
        rng.shuffle(candidates)
        candidates.sort(
            key=lambda row: (
                str(row.get("equipment_mention_level")) == "titulo",
                int(row.get("cited_by") or 0),
            ),
            reverse=True,
        )
        selected = take_unique(candidates, allocations[group], seen, group)
        for row in selected:
            level = row.get("equipment_mention_level") or "sin_equipo"
            row["sample_stratum"] = f"{group}_{level}"
        output.extend(selected)
    if len(output) < sample_size:
        filler = [row for row in included if _record_equipment_groups(row)]
        rng.shuffle(filler)
        output.extend(take_unique(filler, sample_size - len(output), seen, "relleno_equipos"))
    return output[:sample_size]


def equipment_allocations(total: int) -> dict[str, int]:
    main = int(round(total * 0.4))
    auxiliary = int(round(total * 0.4))
    fixed = max(total - main - auxiliary, 0)
    return {
        "equipos_principales": main,
        "equipos_auxiliares": auxiliary,
        "equipos_fijos_continuos": fixed,
    }


def build_equipment_validation_sample(
    records_by_group: dict[str, list[dict[str, Any]]],
    sample_size: int,
) -> list[dict[str, Any]]:
    allocations = equipment_allocations(sample_size)
    seen: set[str] = set()
    output = []
    # Se prioriza el estrato auxiliar porque fue el menos representado en el primer piloto.
    priority = ["equipos_auxiliares", "equipos_principales", "equipos_fijos_continuos"]
    for group in priority:
        output.extend(take_unique(records_by_group[group], allocations[group], seen, group))
    if len(output) < sample_size:
        filler = deduplicate(
            [record for group in priority for record in records_by_group[group]]
        )
        output.extend(take_unique(filler, sample_size - len(output), seen, "relleno_equipos"))
    return output


def build_excluded_review_sample(
    excluded_records: list[dict[str, Any]],
    sample_size: int,
) -> list[dict[str, Any]]:
    """Muestrea exclusiones por motivo para estimar falsos negativos."""
    if sample_size <= 0:
        return []
    buckets = {
        "metodo_subterraneo": [],
        "tema_excluido": [],
        "sin_foco_operacional": [],
        "otras_exclusiones": [],
    }
    for record in excluded_records:
        reasons = str(record.get("auto_screen_reasons") or "")
        if "metodo_subterraneo_fuera_de_alcance" in reasons:
            bucket = "metodo_subterraneo"
        elif "tema_excluido_en_titulo" in reasons:
            bucket = "tema_excluido"
        elif "sin_foco_operacional_suficiente" in reasons:
            bucket = "sin_foco_operacional"
        else:
            bucket = "otras_exclusiones"
        buckets[bucket].append(record)

    rng = random.Random(SEED)
    for records in buckets.values():
        rng.shuffle(records)

    nonempty = [name for name, records in buckets.items() if records]
    base_target = sample_size // max(len(nonempty), 1)
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for name in nonempty:
        output.extend(take_unique(buckets[name], base_target, seen, name))

    if len(output) < sample_size:
        filler = [record for name in nonempty for record in buckets[name]]
        rng.shuffle(filler)
        output.extend(
            take_unique(filler, sample_size - len(output), seen, "relleno_exclusiones")
        )
    return output[:sample_size]


def fetch_global_sample_components(
    sample_size: int,
    general_random_size: int,
    mailto: str | None,
    api_key: str | None,
    delay_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    top_target, recent_target, random_target = sample_targets(sample_size)
    top = fetch_basic_records(
        build_filter(), max(top_target * PILOT_OVERSAMPLE_FACTOR, top_target), "global_top_cited",
        mailto, api_key, delay_seconds, sort="cited_by_count:desc",
    )
    recent = fetch_basic_records(
        build_filter(), max(recent_target * PILOT_OVERSAMPLE_FACTOR, recent_target), "global_recent",
        mailto, api_key, delay_seconds, sort="publication_date:desc",
    )
    random_records = fetch_basic_records(
        build_filter(),
        max(general_random_size * PILOT_OVERSAMPLE_FACTOR, random_target * PILOT_OVERSAMPLE_FACTOR),
        "global_random",
        mailto, api_key, delay_seconds, sample_seed=SEED,
    )
    return top, recent, random_records


def fetch_equipment_records(
    total: int,
    mailto: str | None,
    api_key: str | None,
    delay_seconds: float,
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, int],
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    allocations = equipment_allocations(total)
    records_by_group: dict[str, list[dict[str, Any]]] = {}
    excluded_by_group: dict[str, list[dict[str, Any]]] = {}
    raw_by_group: dict[str, list[dict[str, Any]]] = {}
    totals: dict[str, int] = {}
    for offset, group in enumerate(EQUIPMENT_QUERY_GROUPS):
        filter_value = build_equipment_filter(group)
        totals[group] = fetch_count(filter_value, mailto, api_key)
        retrieved = fetch_basic_records(
            filter_value,
            allocations[group],
            group,
            mailto,
            api_key,
            delay_seconds,
            sample_seed=SEED + offset + 1,
        )
        included, excluded = screen_records(deduplicate(retrieved), group)
        raw_by_group[group] = retrieved
        records_by_group[group] = included
        excluded_by_group[group] = excluded
        print(
            f"  filtro {group}: {len(included)} incluidos, "
            f"{len(excluded)} excluidos"
        )
    return records_by_group, totals, excluded_by_group, raw_by_group


def write_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_local_records(input_dir: Path) -> list[dict[str, Any]]:
    candidate_pairs = [
        ("open_pit_corpus_raw.csv", "open_pit_excluded_records.csv"),
        ("open_pit_corpus_final.csv", "open_pit_excluded_records_final.csv"),
    ]
    for included_name, excluded_name in candidate_pairs:
        included_path = input_dir / included_name
        excluded_path = input_dir / excluded_name
        if included_path.exists() and excluded_path.exists():
            return [*read_csv(included_path), *read_csv(excluded_path)]
    expected = " o ".join(f"{a} + {b}" for a, b in candidate_pairs)
    raise FileNotFoundError(f"No se encontraron los archivos esperados en {input_dir}: {expected}")


# Flujo integrado v1.0: las funciones y diccionarios anteriores son los de v3.0.
import hashlib
import difflib
import unicodedata
from collections import Counter

VERSION_INTEGRADA = '1.1_2026_09_28'
RAIZ = Path(__file__).resolve().parent
FRASES_CONSULTA_ORIGINAL = OPEN_PIT_PHRASES[:10]
CUPOS = {'I': 40, 'Q': 60, 'G': 128, 'PENDIENTE_NUEVO': 12}


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def por_id(rows, nombre):
    indexed = {str(r.get('openalex_id') or ''): r for r in rows}
    if len(indexed) != len(rows) or '' in indexed:
        raise ValueError(f'ID OpenAlex vacío o repetido en {nombre}')
    return indexed


def texto_comparable(value):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', str(value or '')).casefold()))


def doi_comparable(value):
    return re.sub(r'^https?://(?:dx\.)?doi\.org/', '', str(value or '').casefold()).strip()


def reconciliar_ids(accepted_rows, previous, ids_de_entrada):
    """Une IDs cambiados solo ante coincidencia bibliográfica suficientemente fuerte.

    Conserva ambos identificadores; no equipara solo títulos ni textos cortos.
    """
    ausentes = [r for identity, r in previous.items() if identity not in ids_de_entrada]
    por_doi = {}
    por_titulo = {}
    por_resumen = {}
    for old in ausentes:
        d = doi_comparable(old.get('doi'))
        t = texto_comparable(old.get('title'))
        if d:
            por_doi.setdefault(d, []).append(old)
        if t:
            por_titulo.setdefault(t, []).append(old)
        abstract = texto_comparable(old.get('abstract'))
        if len(abstract) >= 100:
            por_resumen.setdefault(abstract, []).append(old)
    matches = {}
    used_old = set()
    for new in sorted(accepted_rows, key=lambda r: r['openalex_id']):
        identity = new['openalex_id']
        if identity in previous:
            continue
        d = doi_comparable(new.get('doi'))
        t = texto_comparable(new.get('title'))
        method = ''
        candidates = por_doi.get(d, []) if d else []
        if len(candidates) == 1 and t:
            old_title = texto_comparable(candidates[0].get('title'))
            if old_title and difflib.SequenceMatcher(None, t, old_title).ratio() >= 0.80:
                method = 'doi_y_titulo'
        if not method:
            candidates = []
            for old in por_titulo.get(t, []) if t else []:
                if str(new.get('year')) != str(old.get('year')):
                    continue
                a, b = texto_comparable(new.get('abstract')), texto_comparable(old.get('abstract'))
                if len(a) >= 100 and len(b) >= 100 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.90:
                    candidates.append(old)
            if len(candidates) == 1:
                method = 'titulo_ano_resumen'
        if not method:
            abstract = texto_comparable(new.get('abstract'))
            candidates = [old for old in por_resumen.get(abstract, [])
                          if str(new.get('year')) == str(old.get('year'))
                          and t and difflib.SequenceMatcher(
                              None, t, texto_comparable(old.get('title'))).ratio() >= 0.90]
            if len(candidates) == 1:
                method = 'resumen_ano_titulo_similar'
        if method and len(candidates) == 1:
            old = candidates[0]
            old_id = old['openalex_id']
            if old_id not in used_old:
                matches[identity] = (old, method)
                used_old.add(old_id)
    return matches


def nueva_muestra(rows, destino):
    """Diseño estratificado sin reemplazo; la clave queda separada de la planilla ciega."""
    pools = {s: [] for s in CUPOS}
    for r in rows:
        pools[r['estado_cribado_especifico']].append(r)
    n = {s: min(CUPOS[s], len(pools[s])) for s in CUPOS}
    missing = min(240, len(rows)) - sum(n.values())
    while missing:
        for s in ('G', 'Q', 'I', 'PENDIENTE_NUEVO'):
            if missing and n[s] < len(pools[s]):
                n[s] += 1
                missing -= 1
    rng = random.Random(20260928)
    selected = []
    for s, records in pools.items():
        selected.extend((s, r) for r in rng.sample(
            sorted(records, key=lambda r: r['openalex_id']), n[s]))
    rng.shuffle(selected)
    blind, key = [], []
    for i, (s, r) in enumerate(selected, 1):
        code = f'U-{i:03d}'
        blind.append({'codigo': code, 'title': r.get('title', ''),
                      'abstract': r.get('abstract', ''), 'doi': r.get('doi', ''),
                      'year': r.get('year', '')})
        N = len(pools[s])
        key.append({'codigo': code, 'openalex_id': r['openalex_id'], 'estrato': s,
                    'N': N, 'n': n[s], 'probabilidad_n_sobre_N': f'{n[s]/N:.10f}',
                    'peso_N_sobre_n': f'{N/n[s]:.10f}', 'etiqueta_antes_de_revision': s})
    write_csv(destino / 'muestra_ciega_240.csv', blind,
              ['codigo', 'title', 'abstract', 'doi', 'year',
               'decision_revisor_1_I_Q_G', 'motivo_revisor_1',
               'decision_revisor_2_I_Q_G', 'motivo_revisor_2',
               'consenso_I_Q_G', 'motivo_consenso', 'texto_completo_consultado', 'fecha'])
    write_csv(destino / 'clave_muestra_240_NO_ENTREGAR_A_REVISORES.csv', key,
              ['codigo', 'openalex_id', 'estrato', 'N', 'n', 'probabilidad_n_sobre_N',
               'peso_N_sobre_n', 'etiqueta_antes_de_revision'])
    return {s: {'N': len(pools[s]), 'n': n[s]} for s in CUPOS}


def muestra_exclusiones_amplias(rows, destino, size=80):
    """Control independiente de pérdidas del primer filtro, por motivo principal."""
    groups = {}
    for r in rows:
        reason = str(r.get('auto_screen_reasons') or 'sin_motivo').split(';')[0].split(':')[0].strip()
        groups.setdefault(reason, []).append(r)
    n = {s: 1 for s in groups}
    total = sum(len(g) for g in groups.values())
    remaining = min(size, total) - sum(n.values())
    while remaining:
        eligible = [s for s in groups if n[s] < len(groups[s])]
        s = max(eligible, key=lambda k: (size * len(groups[k]) / total - n[k], k))
        n[s] += 1
        remaining -= 1
    rng = random.Random(20260929)
    chosen = []
    for s, pool in sorted(groups.items()):
        chosen.extend((s, r) for r in rng.sample(
            sorted(pool, key=lambda r: r['openalex_id']), n[s]))
    rng.shuffle(chosen)
    blind, key = [], []
    for i, (s, r) in enumerate(chosen, 1):
        code = f'EA-{i:03d}'
        blind.append({'codigo': code, 'title': r.get('title', ''),
                      'abstract': r.get('abstract', ''), 'doi': r.get('doi', ''),
                      'year': r.get('year', '')})
        N = len(groups[s])
        key.append({'codigo': code, 'openalex_id': r['openalex_id'],
                    'motivo_principal': s, 'N': N, 'n': n[s],
                    'probabilidad_n_sobre_N': f'{n[s]/N:.10f}',
                    'peso_N_sobre_n': f'{N/n[s]:.10f}'})
    write_csv(destino / 'muestra_ciega_exclusiones_amplias_80.csv', blind,
              ['codigo', 'title', 'abstract', 'doi', 'year',
               'recuperar_revisor_1_si_no_duda', 'motivo_revisor_1',
               'recuperar_revisor_2_si_no_duda', 'motivo_revisor_2',
               'consenso_si_no_duda', 'motivo_consenso'])
    write_csv(destino / 'clave_exclusiones_amplias_NO_ENTREGAR_A_REVISORES.csv', key,
              ['codigo', 'openalex_id', 'motivo_principal', 'N', 'n',
               'probabilidad_n_sobre_N', 'peso_N_sobre_n'])
    return {s: {'N': len(groups[s]), 'n': n[s]} for s in groups}


def main_integrado():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fuente', choices=['congelada', 'archivos_nuevos'], default='archivos_nuevos')
    parser.add_argument('--entrada', type=Path, default=None)
    parser.add_argument('--historial', type=Path, default=RAIZ / 'cribado_anterior_4773.csv')
    parser.add_argument('--referencia', type=Path, default=RAIZ / 'referencia_historica_v3_4769.csv')
    parser.add_argument('--salida', type=Path, default=RAIZ / 'resultados_cribado')
    args = parser.parse_args()
    if args.entrada is None:
        args.entrada = RAIZ / ('datos_originales_v2_4' if args.fuente == 'congelada' else 'datos_openalex')
    output = args.salida.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error(f'La carpeta de salida contiene archivos: {output}. Elige otra.')

    if args.fuente == 'congelada':
        universe = args.entrada / 'universo_openalex_9611.csv'
        expected = json.loads((RAIZ / 'manifest_sha256.json').read_text(encoding='utf-8'))
        if not universe.is_file() or sha256(universe) != expected['universo_deduplicado_9611']:
            parser.error(f'Archivo congelado ausente o modificado: {universe}')
        raw = read_csv(universe)
        if len(raw) != 9611:
            parser.error('La entrada congelada debe tener 9.611 filas')
        source_paths = [universe]
        original_metadata = json.loads((args.entrada / 'open_pit_run_metadata_v2_4.json')
                                       .read_text(encoding='utf-8'))
        reported = original_metadata['openalex_reported_total']
        api_filter = original_metadata['general_api_filter']
    elif args.fuente == 'archivos_nuevos':
        universe = args.entrada / 'universo_openalex.csv'
        if not universe.is_file():
            parser.error('Falta universo_openalex.csv del primer código')
        raw = read_csv(universe)
        source_paths = [universe]
        meta_file = args.entrada / 'open_pit_extraction_metadata.json'
        if not meta_file.is_file():
            parser.error('Falta open_pit_extraction_metadata.json de la extracción nueva')
        source_paths.append(meta_file)
        original_metadata = json.loads(meta_file.read_text(encoding='utf-8'))
        reported = original_metadata['openalex_reported_total']
        api_filter = original_metadata['general_api_filter']

    previous = por_id(read_csv(args.historial), 'historial')
    output.mkdir(parents=True, exist_ok=True)
    print(f'Entrada: {len(raw)}. Deduplicando...', flush=True)
    unique = deduplicate(raw)
    print(f'Únicos: {len(unique)}. Aplicando filtro amplio...', flush=True)
    accepted_rows, rejected_rows = screen_records(unique)
    accepted = por_id(accepted_rows, 'incluidos amplios')
    rejected = por_id(rejected_rows, 'excluidos amplios')
    if accepted.keys() & rejected.keys():
        raise RuntimeError('Un ID aparece en las dos salidas')
    if args.fuente == 'congelada' and (len(unique), len(accepted), len(rejected)) != (9604, 4769, 4835):
        raise RuntimeError('No se reprodujeron los recuentos originales')
    write_csv(output / 'corpus_general_aceptado.csv', accepted_rows, RAW_FIELDS)
    write_csv(output / 'excluidos_amplios_con_motivo.csv', rejected_rows, RAW_FIELDS)

    historic_match = None
    if args.fuente == 'congelada':
        historic = por_id(read_csv(args.referencia), 'referencia v3 histórica')
        historic_match = accepted.keys() == historic.keys()
        if not historic_match:
            raise RuntimeError('Los IDs no coinciden con la referencia v3 histórica')

    ids_de_entrada = {str(r.get('openalex_id') or '') for r in raw}
    correspondencias = reconciliar_ids(accepted_rows, previous, ids_de_entrada)
    extra_fields = ['estado_cribado_especifico', 'procedencia_decision_especifica',
                    'motivo_decision_especifica', 'estatus_validacion',
                    'openalex_id_anterior_equivalente', 'metodo_reconciliacion_id']
    joined = []
    for r in accepted_rows:
        alias = correspondencias.get(r['openalex_id'])
        prior = previous.get(r['openalex_id']) or (alias[0] if alias else {})
        joined.append({**r,
                       'estado_cribado_especifico': prior.get('decision_provisional_v2') or 'PENDIENTE_NUEVO',
                       'procedencia_decision_especifica': ('heredado_por_correspondencia_bibliografica' if alias
                           else prior.get('procedencia_decision_v2') or 'sin_juicio_previo'),
                       'motivo_decision_especifica': prior.get('motivo_decision_v2', ''),
                       'estatus_validacion': 'pendiente_validacion_humana',
                       'openalex_id_anterior_equivalente': prior['openalex_id'] if alias else '',
                       'metodo_reconciliacion_id': alias[1] if alias else ''})
    main_path = output / 'corpus_unificado_con_historial.csv'
    write_csv(main_path, joined, [*RAW_FIELDS, *extra_fields])

    alias_path = output / 'correspondencias_ids_openalex.csv'
    write_csv(alias_path, [{
        'openalex_id_actual': new_id, 'openalex_id_anterior': old['openalex_id'],
        'metodo': method, 'titulo_actual': accepted[new_id].get('title', ''),
        'titulo_anterior': old.get('title', ''), 'doi_actual': accepted[new_id].get('doi', ''),
        'doi_anterior': old.get('doi', ''), 'etiqueta_provisional_heredada': old.get('decision_provisional_v2', '')
    } for new_id, (old, method) in sorted(correspondencias.items())],
        ['openalex_id_actual', 'openalex_id_anterior', 'metodo', 'titulo_actual',
         'titulo_anterior', 'doi_actual', 'doi_anterior', 'etiqueta_provisional_heredada'])

    diff = []
    for identity in sorted(accepted.keys() - previous.keys()):
        r = accepted[identity]
        diff.append({'openalex_id': identity, 'title': r.get('title', ''), 'doi': r.get('doi', ''),
                     'tipo': 'nuevo_incluido', 'motivo_filtro_amplio': '', 'etiqueta_anterior': ''})
    for identity in sorted(previous.keys() - accepted.keys()):
        r = previous[identity]
        excluded = rejected.get(identity)
        diff.append({'openalex_id': identity, 'title': r.get('title', ''), 'doi': r.get('doi', ''),
                     'tipo': 'sale_del_corpus_amplio' if identity in ids_de_entrada else 'no_recuperado_en_nueva_cohorte',
                     'motivo_filtro_amplio': excluded.get('auto_screen_reasons', '') if excluded else
                     ('fusionado_en_deduplicacion' if identity in ids_de_entrada else 'fuera_de_la_consulta_actual'),
                     'etiqueta_anterior': r.get('decision_provisional_v2', '')})
    diff_path = output / 'diferencias_con_corpus_anterior.csv'
    write_csv(diff_path, diff,
              ['openalex_id', 'title', 'doi', 'tipo', 'motivo_filtro_amplio', 'etiqueta_anterior'])
    sample = nueva_muestra(joined, output)
    excluded_sample = muestra_exclusiones_amplias(rejected_rows, output)

    metadata = {
        'version': VERSION_INTEGRADA, 'fecha_utc': datetime.now(timezone.utc).isoformat(),
        'fuente': args.fuente, 'consulta_api_en_esta_ejecucion': False,
        'consulta_documentada': api_filter, 'conteo_api_reportado': reported,
        'metadatos_primera_etapa': ({key: original_metadata.get(key) for key in
            ['generated_at_utc', 'openalex_reported_total', 'retrieved_before_deduplication',
             'duplicates_removed', 'records_after_dedup_before_screening']}
            if original_metadata else None),
        'filas_entrada': len(raw), 'tras_deduplicacion': len(unique),
        'duplicados_retirados': len(raw)-len(unique),
        'incluidos_amplios': len(accepted), 'excluidos_amplios': len(rejected),
        'coincidencia_ids_historicos': historic_match,
        'etiquetas_especificas': dict(Counter(r['estado_cribado_especifico'] for r in joined)),
        'diferencias': dict(Counter(r['tipo'] for r in diff)),
        'reconciliacion_ids': {
            'correspondencias_bibliograficas': len(correspondencias),
            'nuevos_sin_historial_tras_reconciliacion': len(accepted.keys() - previous.keys()) - len(correspondencias),
            'no_recuperados_tras_reconciliacion': len(previous.keys() - ids_de_entrada) - len(correspondencias),
            'archivo': alias_path.name,
            'nota': 'El cuadro de diferencias conserva los conteos brutos por ID; no sumar los pares como obras distintas.'},
        'muestra': sample, 'control_exclusiones_amplias': excluded_sample,
        'sha256_codigo': sha256(Path(__file__)),
        'sha256_entradas': {p.name: sha256(p) for p in [*source_paths, args.historial]},
        'sha256_resultados': {p.name: sha256(p) for p in sorted(output.glob('*.csv'))},
        'nota': 'I/Q/G son provisionales y no equivalen a validación humana; la muestra nueva requiere evaluación ciega.'}
    (output / 'metadatos_y_flujo.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: metadata[k] for k in ['filas_entrada', 'tras_deduplicacion',
          'incluidos_amplios', 'excluidos_amplios', 'etiquetas_especificas',
          'diferencias', 'muestra', 'control_exclusiones_amplias']}, ensure_ascii=False, indent=2))
    print(f'Resultados: {output}')


if __name__ == '__main__':
    main_integrado()
