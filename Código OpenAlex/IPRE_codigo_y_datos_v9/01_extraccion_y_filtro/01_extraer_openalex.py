#!/usr/bin/env python3
"""Extrae desde OpenAlex y guarda el universo deduplicado antes de cribado temático.

Consulta y deduplicación proceden de v2.4. No excluye por pertinencia temática.
El resultado alimenta el segundo código sin perder ningún registro del universo.
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
from pathlib import Path
from typing import Any, Iterable


OPENALEX_URL = "https://api.openalex.org/works"
OPENALEX_API_KEY_ENV = "OPENALEX_API_KEY"
SEED = 42
QUERY_VERSION = "2.4"
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
    "sediment yield", "regulation", "taxation", "constitutional", "social media",
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
]


RAW_FIELDS = [
    "retrieval_branches", "openalex_id", "doi", "title", "year", "publication_date", "type", "language",
    "cited_by", "source", "authors", "institutions", "countries", "keywords",
    "topics", "concepts", "matched_open_pit_phrases", "auto_process_tags",
    "auto_equipment_tags", "auto_focus_tags", "auto_screen_status",
    "auto_screen_reasons", "operational_signals", "duplicate_count",
    "deduplication_methods", "quality_flags", "shared_abstract_openalex_ids",
    "merged_openalex_ids", "merged_dois", "abstract",
]

REVIEW_FIELDS = [
    "sample_stratum", "retrieval_branches", "openalex_id", "doi", "title", "year", "publication_date",
    "type", "language", "cited_by", "source", "authors", "keywords", "topics",
    "matched_open_pit_phrases", "auto_process_tags", "auto_equipment_tags",
    "auto_focus_tags", "auto_screen_status", "auto_screen_reasons",
    "operational_signals", "duplicate_count", "merged_openalex_ids", "merged_dois",
    "deduplication_methods", "quality_flags", "shared_abstract_openalex_ids",
    "abstract", "manual_relevant", "manual_exclusion_reason",
    "manual_process_family", "manual_process_detail", "manual_equipment_family",
    "manual_equipment_detail", "manual_focus", "manual_notes",
]


def normalize(text: Any) -> str:
    if text is None:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.translate(str.maketrans({
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
    }))
    return re.sub(r"\s+", " ", text.lower()).strip()


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    tokens = sorted(
        ((position, word) for word, positions in inverted_index.items() for position in positions),
        key=lambda item: item[0],
    )
    return " ".join(word for _, word in tokens)


def matched_terms(text: str, terms: Iterable[str]) -> list[str]:
    padded = f" {normalize(text)} "
    matches = []
    for term in terms:
        normalized_term = normalize(term)
        pattern = rf"(?<![a-z0-9]){re.escape(normalized_term)}(?![a-z0-9])"
        if re.search(pattern, padded):
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
        "auto_equipment_tags": "; ".join(tag_categories(text_for_tags, EQUIPMENT_TERMS)),
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
    full_text = " ".join([title, abstract, keywords, topics, concepts])

    title_exclusions = matched_terms(title, EXCLUSION_TITLE_TERMS)
    hard_title_exclusions = matched_terms(title, HARD_EXCLUSION_TITLE_TERMS)
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

    signal_categories = sorted(
        set(
            title_scope + full_scope + title_direct + full_direct
            + title_process + full_process + full_equipment + title_focus + full_focus
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
        or (title_has_context and (title_process or title_focus))
    )
    has_context = bool(matched_terms(full_text, OPEN_PIT_PHRASES))
    from_equipment_branch = any(
        group in str(record.get("retrieval_branches") or "")
        for group in EQUIPMENT_QUERY_GROUPS
    )
    has_combined_signal = has_context and bool(
        full_direct
        or (full_equipment and (full_process or full_focus))
        or (from_equipment_branch and full_equipment)
    )
    has_multiple_direct_signals = len(set(full_direct)) >= 2

    if hard_title_exclusions:
        reasons.append(
            "metodo_subterraneo_fuera_de_alcance:" + "|".join(hard_title_exclusions)
        )

    # Una exclusión temática se puede revertir si el propio título demuestra
    # que el artículo estudia un proceso o equipo operacional. Esto evita, por
    # ejemplo, descartar trabajos de dozers que también tratan reclamación.
    if title_exclusions and not exclusion_override:
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
) -> tuple[list[dict[str, Any]], str | None, int, int]:
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
    saved = state.get("saved_records")
    if saved is not None:
        if len(records) < int(saved):
            raise RuntimeError("El checkpoint tiene menos registros que su estado guardado.")
        extra_rows = len(records) > int(saved)
        records = records[:int(saved)]
        if extra_rows:
            with checkpoint_path.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return (
        records,
        state.get("next_cursor"),
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
    saved_records: int,
) -> None:
    temporary_path = state_path.with_suffix(".tmp")
    temporary_path.write_text(
        json.dumps(
            {
                "query_version": QUERY_VERSION,
                "next_cursor": cursor,
                "reported_total": reported_total,
                "next_page": next_page,
                "saved_records": saved_records,
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
        _write_state(state_path, cursor, reported_total, page + 1, len(parsed_records))
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
    if doi:
        keys.add("doi:" + doi)
    if openalex_id:
        keys.add("openalex:" + openalex_id)
    if title:
        keys.add("title:" + title)
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


# Nuevo flujo de extracción pura: se detiene antes del filtro temático v2.4.
import hashlib

def hash_archivo(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def extraer():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path,
                        default=Path(__file__).resolve().parent / 'datos_openalex')
    parser.add_argument('--mailto', default=None)
    parser.add_argument('--delay', type=float, default=1.0)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    existentes = {item.name for item in output.iterdir()} if output.exists() else set()
    temporales = {'.open_pit_download_checkpoint.jsonl', '.open_pit_download_state.json'}
    if existentes - temporales:
        parser.error('El directorio de salida ya contiene resultados; utiliza uno nuevo.')
    if existentes and existentes != temporales:
        parser.error('El punto de reanudación está incompleto; revisa los dos archivos temporales.')
    output.mkdir(parents=True, exist_ok=True)
    key = re.sub(r'[\x00-\x20\x7f]', '', os.environ.get(OPENALEX_API_KEY_ENV, '')).strip('"\'')
    if not key:
        parser.error('Define OPENALEX_API_KEY para realizar una descarga nueva')
    raw, reported = download_full_records(output, None, args.mailto, key, max(args.delay, 0.0))
    raw_path = output / 'descarga_sin_deduplicar.jsonl'
    with raw_path.open('w', encoding='utf-8') as f:
        for row in raw:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')
    unique = deduplicate(raw)
    if len({str(r.get('openalex_id') or '') for r in unique}) != len(unique):
        raise RuntimeError('Quedan IDs OpenAlex repetidos; resolver antes del segundo filtro')
    corpus_path = output / 'universo_openalex.csv'
    write_csv(corpus_path, unique, RAW_FIELDS)
    metadata = {
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'query_version': QUERY_VERSION,
        'source': 'OpenAlex API',
        'endpoint': OPENALEX_URL,
        'general_api_filter': build_filter(),
        'technical_filters': TECHNICAL_FILTERS,
        'openalex_reported_total': reported,
        'retrieved_before_deduplication': len(raw),
        'duplicates_removed': len(raw) - len(unique),
        'records_after_dedup_before_screening': len(unique),
        'thematic_screening_applied': False,
        'doi_required': False,
        'api_key_used': True,
        'sha256_raw_jsonl': hash_archivo(raw_path),
        'sha256_universe_csv': hash_archivo(corpus_path),
        'note': 'Instantánea nueva; no se espera que reproduzca los 9.611 históricos.'
    }
    (output / 'open_pit_extraction_metadata.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Filas descargadas: {len(raw)} | únicas antes del filtro temático: {len(unique)}')
    print('Universo para la segunda etapa:', corpus_path)


if __name__ == '__main__':
    extraer()
