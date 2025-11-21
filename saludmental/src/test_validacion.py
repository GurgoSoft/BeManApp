#!/usr/bin/env python
"""
Script de prueba para validar la lógica de fecha y precio
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pytz
from django.utils import timezone

print("=" * 60)
print("PRUEBA DE VALIDACIÓN DE FECHA")
print("=" * 60)

# Hora actual
tz_colombia = pytz.timezone('America/Bogota')
ahora_utc = timezone.now()
ahora_colombia = ahora_utc.astimezone(tz_colombia)

print(f"\n📅 Hora actual UTC: {ahora_utc}")
print(f"📅 Hora actual Colombia: {ahora_colombia}")
print(f"📅 Fecha actual Colombia: {ahora_colombia.date()}")

# Simular fecha a las 11:08 AM (como en tu captura)
fecha_input = ahora_colombia.replace(hour=11, minute=8, second=0, microsecond=0)
print(f"\n🕐 Fecha seleccionada: {fecha_input}")
print(f"🕐 Mismo día? {fecha_input.date() == ahora_colombia.date()}")

# Calcular diferencia
diferencia_minutos = (fecha_input - ahora_colombia).total_seconds() / 60
print(f"\n⏱️  Diferencia: {diferencia_minutos:.1f} minutos ({diferencia_minutos/60:.2f} horas)")

# Validar según regla
if fecha_input.date() == ahora_colombia.date():
    minimo_minutos = 120
    print(f"✅ Es mismo día, se requieren {minimo_minutos} minutos (2 horas)")
    if diferencia_minutos < minimo_minutos:
        horas_faltantes = (minimo_minutos - diferencia_minutos) / 60
        print(f"❌ RECHAZADO: Te faltan {horas_faltantes:.1f} horas")
    else:
        print(f"✅ ACEPTADO: Cumple con las 2 horas mínimas")
else:
    print(f"✅ Es otro día, se requieren 5 minutos")
    if diferencia_minutos >= 5:
        print(f"✅ ACEPTADO")
    else:
        print(f"❌ RECHAZADO: Te faltan {5 - diferencia_minutos:.1f} minutos")

print("\n" + "=" * 60)
print("PRUEBA DE VALIDACIÓN DE PRECIO")
print("=" * 60)

test_precios = ["50.000", "70.000", "1.000.000", "0", ""]

for precio_str in test_precios:
    print(f"\n💰 Probando: '{precio_str}'")
    
    # Simular lógica de clean_precio
    if precio_str:
        digits = precio_str.replace('.', '').replace(',', '').strip()
        digits = ''.join(ch for ch in digits if ch.isdigit())
        if digits == '':
            digits = '0'
        valor = int(digits)
        print(f"   → Resultado: {valor} COP")
    else:
        print(f"   → Vacío, se convierte a 0")

print("\n" + "=" * 60)
