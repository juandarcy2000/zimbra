#!/usr/bin/env python3
import re
from collections import Counter

LOG_PATH = '/opt/zimbra/log/mailbox.log'

# Regex para extraer fecha y hora al inicio de línea
regex_datetime = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})')

# Regex para invalid password y account lockout (captura name y oip)
regex_general = re.compile(
    r'\[name=([^;\]]+).*?oip=(\d+\.\d+\.\d+\.\d+)',
    re.IGNORECASE
)
VIOLETA = '\033[95m'
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

# Regex para account not found: captura correo tras 'authentication failed for [correo]'
regex_account_not_found = re.compile(
    r'authentication failed for \[([^\]]+)\]',
    re.IGNORECASE
)

# Regex para capturar cualquier IP (oip o ip) en la línea
regex_ip = re.compile(
    r'\[(?:oip|ip)=(\d+\.\d+\.\d+\.\d+)',
    re.IGNORECASE
)

def analizar_logs(path):
    invalid_password = Counter()
    account_lockout = Counter()
    account_not_found = Counter()

    # Para guardar hora y conteo, usaremos diccionarios
    invalid_password_times = {}
    account_lockout_times = {}
    account_not_found_times = {}

    try:
        with open(path, 'r') as f:
            for linea in f:
                linea_lower = linea.lower()
                if 'authentication failed' in linea_lower:
                    # Extraer fecha y hora
                    dt_match = regex_datetime.search(linea)
                    datetime_str = dt_match.group(1) if dt_match else "Fecha no encontrada"

                    if 'invalid password' in linea_lower or 'account lockout' in linea_lower:
                        match = regex_general.search(linea)
                        if match:
                            correo = match.group(1).strip()
                            ip = match.group(2).strip()
                            clave = f"{correo} | {ip}"
                            if 'invalid password' in linea_lower:
                                invalid_password[clave] += 1
                                invalid_password_times[clave] = datetime_str
                            else:
                                account_lockout[clave] += 1
                                account_lockout_times[clave] = datetime_str

                    elif 'account not found' in linea_lower:
                        match_correo = regex_account_not_found.search(linea)
                        match_ip = regex_ip.search(linea)
                        if match_correo:
                            correo_nf = match_correo.group(1).strip()
                            ip_nf = match_ip.group(1).strip() if match_ip else "IP no encontrada"
                            clave_nf = f"{correo_nf} | {ip_nf}"
                            account_not_found[clave_nf] += 1
                            account_not_found_times[clave_nf] = datetime_str

        # Mostrar resultados con la hora del último intento registrado
        def imprimir_resultados(titulo, contador, tiempos):
            print(f"\n{titulo}:")
            if contador:
                for clave, cantidad in contador.most_common():
                    hora = tiempos.get(clave, "Fecha no encontrada")
                    print(f"{CYAN}{clave}{RESET} → {VIOLETA}{cantidad} intentos{RESET} (último intento: {GREEN}{hora}{RESET})")
            else:
                print("⚠️ No se encontraron datos.")

        imprimir_resultados("Intentos fallidos por 'invalid password'", invalid_password, invalid_password_times)
        imprimir_resultados("Intentos de 'account lockout'", account_lockout, account_lockout_times)
        imprimir_resultados("Intentos con cuentas no existentes ('account not found')", account_not_found, account_not_found_times)

    except FileNotFoundError:
        print(f"Archivo no encontrado: {path}")
    except Exception as e:
        print(f"⚠️ Error al procesar el log: {e}")

if __name__ == '__main__':
    analizar_logs(LOG_PATH)

