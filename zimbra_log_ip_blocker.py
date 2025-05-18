#!/usr/bin/env python3
import re
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
import os
#import geoip2.database
from dateutil import parser

# --- Configuración ---
BASE_DIR = '/'   # Directorio base donde están el script y los archivos JSON
log_path = '/var/log/maillog'  # Ruta al archivo de log del mail (donde buscar intentos fallidos)
blocked_json = os.path.join(BASE_DIR, 'ips_bloqueadas.json')  # Archivo JSON para IPs bloqueadas
unblocked_json = os.path.join(BASE_DIR, 'ips_desbloqueadas.json')  # Archivo JSON para IPs desbloqueadas
log_debug = os.path.join(BASE_DIR, 'bloqueo_debug.log')  # Archivo para registrar eventos/debug

#GEOIP_DB_PATH = '/usr/share/GeoIP/GeoLite2-Country.mmdb'  # Ruta base para GeoIP (comentada porque no se usa)

FAILED_ATTEMPTS_THRESHOLD = 2  # Número mínimo de intentos fallidos para bloquear una IP
BLOCK_DURATION = timedelta(hours=1)  # Tiempo que dura bloqueada una IP
REBLOCK_AFTER = timedelta(minutes=10)  # Tiempo de gracia tras desbloqueo antes de poder re-bloquear
whitelist_ips = {'127.0.0.1', '172.16.30.2'}  # IPs que nunca se bloquean (lista blanca)

# --- GeoIP ---
"""
Función comentada para obtener país a partir de IP usando GeoIP, no se usa actualmente.
def get_country(ip):
    try:
        with geoip2.database.Reader(GEOIP_DB_PATH) as reader:
            response = reader.country(ip)
            return response.country.iso_code or "Unknown"
    except Exception:
        return "Unknown"
"""

# --- Regex para capturar IP y timestamp de línea de log ---
log_pattern = re.compile(
    r'^(?P<month>\w{3})\s+(?P<day>\d{1,2})\s+(?P<time>\d{2}:\d{2}:\d{2}) .*?warning: unknown\[(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\]: SASL LOGIN authentication failed'
)
# Explicación regex:
# ^(mes abreviado) (día) (hora:minuto:segundo) ... warning: unknown[ip]: SASL LOGIN authentication failed

month_map = {
    'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4,
    'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8,
    'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
}  # Mapeo de meses abreviados a número para construir datetime

# --- Funciones para leer y guardar archivos JSON ---
def load_json(path):
    # Lee archivo JSON si existe y lo devuelve como lista/diccionario
    if os.path.exists(path):
        with open(path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []  # Si JSON corrupto devuelve lista vacía
    return []  # Si no existe archivo devuelve lista vacía

def save_json(path, data):
    # Guarda la data en JSON con formato legible (indentado)
    with open(path, 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- Leer estados previos desde JSON ---
blocked_data = load_json(blocked_json)  # Lista de IPs bloqueadas con fechas
unblocked_data = load_json(unblocked_json)  # Lista de IPs desbloqueadas con fechas

# Diccionarios para manejar IPs y sus fechas como datetime
blocked_ips = {}
for entry in blocked_data:
    try:
        bloqueado_hasta = parser.parse(entry['bloqueado_hasta'])  # Convierte string ISO a datetime
        blocked_ips[entry['ip']] = bloqueado_hasta
    except Exception as e:
        print(f"Error procesando entrada bloqueada: {entry} -> {e}")

unblocked_ips = {}
for entry in unblocked_data:
    try:
        desbloqueada = parser.parse(entry['desbloqueada'])  # Convierte string ISO a datetime
        unblocked_ips[entry['ip']] = desbloqueada
    except Exception as e:
        print(f"Error procesando entrada desbloqueada: {entry} -> {e}")

# --- Leer log para detectar intentos fallidos ---
current_year = datetime.now().year  # Año actual para completar timestamp (el log no tiene año)
ip_attempts = defaultdict(list)  # Diccionario donde clave=IP, valor=lista de timestamps de intentos fallidos

try:
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = log_pattern.search(line)  # Busca patrón en la línea
            if match:
                ip = match.group('ip')
                if ip in whitelist_ips:
                    continue  # Ignorar IPs en whitelist
                month = month_map[match.group('month')]
                day = int(match.group('day'))
                time_str = match.group('time')
                # Construir datetime completo con año actual
                timestamp = datetime.strptime(f"{current_year}-{month}-{day} {time_str}", "%Y-%m-%d %H:%M:%S")
                ip_attempts[ip].append(timestamp)  # Guardar intento fallido
except Exception as e:
    # Registrar errores al leer log
    with open(log_debug, 'a') as logf:
        logf.write(f"{datetime.now()} - Error leyendo log: {e}\n")

# --- Procesar bloqueos y desbloqueos ---
now = datetime.now()  # Tiempo actual para comparaciones
updated_blocked = []  # Lista actualizada de IPs bloqueadas para guardar
updated_unblocked = []  # Lista actualizada de IPs desbloqueadas para guardar

# Abrir archivo de debug para escribir eventos de bloqueo/desbloqueo
with open(log_debug, 'a') as logf:

    # Primero, desbloquear IPs cuyo tiempo de bloqueo expiró
    for ip in list(blocked_ips.keys()):
        if now >= blocked_ips[ip]:
            # Quitar regla de bloqueo iptables para la IP
            subprocess.run(['/usr/sbin/iptables', '-D', 'INPUT', '-s', ip, '-j', 'DROP'])
            logf.write(f"{now} - Desbloqueada IP: {ip}\n")  # Log de desbloqueo
            # Agregar registro de desbloqueo
            unblocked_data.append({
                "ip": ip,
                "desbloqueada": now.isoformat(),
#                "pais_origen": get_country(ip)  # Comentado porque la función está deshabilitada
            })
            unblocked_ips[ip] = now  # Actualizar diccionario de IPs desbloqueadas
            blocked_ips.pop(ip)  # Quitar IP de bloqueadas
            # Actualizar lista bloqueadas para eliminar esta IP
            blocked_data = [e for e in blocked_data if e['ip'] != ip]

    # Procesar cada IP con intentos registrados
    for ip, timestamps in ip_attempts.items():

        if ip in blocked_ips:
            # IP sigue bloqueada, conservar registro en la lista actualizada
            entry = next((e for e in blocked_data if e['ip'] == ip), None)
            if entry:
                updated_blocked.append(entry)

        elif ip in unblocked_ips:
            # IP está desbloqueada, verificar si se debe re-bloquear
            tiempo_desbloqueo = unblocked_ips[ip]
            if now - tiempo_desbloqueo > REBLOCK_AFTER:
                # Pasó tiempo de gracia, verificar intentos para bloquear
                if len(timestamps) >= FAILED_ATTEMPTS_THRESHOLD:
                    # Re-bloquear IP
                    subprocess.run(['/usr/sbin/iptables', '-I', 'INPUT', '-s', ip, '-j', 'DROP'])
                    bloqueado_hasta = now + BLOCK_DURATION
                    logf.write(f"{now} - Rebloqueada IP: {ip} tras seguir atacando\n")
                    new_entry = {
                        "ip": ip,
                        "bloqueado_desde": now.isoformat(),
                        "bloqueado_hasta": bloqueado_hasta.isoformat()
#                        "pais_origen": get_country(ip)
                    }
                    updated_blocked.append(new_entry)
                    blocked_ips[ip] = bloqueado_hasta
                    unblocked_ips.pop(ip)  # Quitar de desbloqueadas

                else:
                    # Sigue desbloqueada, conservar registro
                    updated_unblocked.append({
                        "ip": ip,
                        "desbloqueada": tiempo_desbloqueo.isoformat()
#                       "pais_origen": get_country(ip)
                    })
            else:
                # Todavía en tiempo de gracia, conservar registro desbloqueado
                updated_unblocked.append({
                    "ip": ip,
                    "desbloqueada": tiempo_desbloqueo.isoformat()
#                    "pais_origen": get_country(ip)
                })

        else:
            # IP nueva, nunca vista antes
            if len(timestamps) >= FAILED_ATTEMPTS_THRESHOLD:
                # Bloquear IP nueva con intentos suficientes
                bloqueado_desde = now
                bloqueado_hasta = bloqueado_desde + BLOCK_DURATION
                subprocess.run(['/usr/sbin/iptables', '-I', 'INPUT', '-s', ip, '-j', 'DROP'])
                logf.write(f"{now} - Bloqueada IP nueva: {ip} con {len(timestamps)} intentos fallidos\n")
                new_entry = {
                    "ip": ip,
                    "bloqueado_desde": bloqueado_desde.isoformat(),
                    "bloqueado_hasta": bloqueado_hasta.isoformat()
#                    "pais_origen": get_country(ip)
                }
                updated_blocked.append(new_entry)
                blocked_ips[ip] = bloqueado_hasta

    # Guardar estado actualizado de bloqueadas y desbloqueadas en archivos JSON
    save_json(blocked_json, updated_blocked)
    save_json(unblocked_json, updated_unblocked)

