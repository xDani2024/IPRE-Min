"""Ejecuta los dos generadores descriptivos, sin repetir el cribado ni modificar matrices."""
import argparse
import subprocess
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser(description='Genera gráficos, estadísticas e informe Word para WoS.')
p.add_argument('--resultados',default='resultados_cribado_wos')
p.add_argument('--salida',default=None)
a=p.parse_args()
for script in ('24_generar_graficos.py','25_generar_avance.py'):
    cmd=[sys.executable,str(HERE/script),'--resultados',a.resultados]
    if a.salida:cmd+=['--salida',a.salida]
    subprocess.run(cmd,check=True)
