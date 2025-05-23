from colorama import init, Fore, Style

init(autoreset=True)


class BurstCalculator:
    """
    Clase para manejar los cálculos relacionados con burst_time y ráfaga.
    """

    def __init__(self, max_limit):
        self.max_limit = max_limit

    def validar_parametros(self, burst_limit, burst_threshold, burst_time=None):
        """
        Validación estricta de parámetros para asegurar coherencia
        y evitar errores en el cálculo.
        """
        if burst_limit <= self.max_limit:
            raise ValueError(
                f"burst_limit ({burst_limit}) debe ser mayor que max_limit ({self.max_limit}).")
        if burst_threshold <= 0:
            raise ValueError(
                "burst_threshold debe ser un valor positivo y mayor que cero.")
        if burst_time is not None and burst_time <= 0:
            raise ValueError(
                "burst_time debe ser un entero positivo mayor que cero.")

    def calcular_burst_time(self, burst_time, burst_limit, burst_threshold):
        """
        Cálculo del intervalo temporal ajustado de burst_time basado en
        la relación entre burst_limit y burst_threshold.
        """
        self.validar_parametros(burst_limit, burst_threshold, burst_time)
        tiempo_asignado = burst_time * burst_limit / burst_threshold
        return tiempo_asignado

    def calcular_rafaga(self, burst_time, burst_threshold, burst_limit):
        """
        Cálculo del tiempo permitido para ráfaga antes de evaluar limitación,
        basado en burst_time, burst_threshold y burst_limit.
        """
        if burst_limit == 0:
            raise ZeroDivisionError(
                "burst_limit no puede ser cero para este cálculo.")
        self.validar_parametros(burst_limit, burst_threshold, burst_time)
        tiempo_permitido = burst_time * burst_threshold / burst_limit
        return tiempo_permitido


def solicitar_int(mensaje):
    """
    Función para solicitar un entero positivo al usuario,
    con manejo robusto de errores y reintentos.
    """
    while True:
        try:
            valor = int(input(Fore.YELLOW + mensaje))
            if valor <= 0:
                print(
                    Fore.RED + "Error: El valor debe ser un entero positivo mayor que cero.")
                continue
            return valor
        except ValueError:
            print(
                Fore.RED + "Error: Entrada inválida. Introduzca un número entero válido.")


def mostrar_explicacion_burst_time():
    print(Fore.MAGENTA + Style.BRIGHT +
          "\n=== CONCEPTUALIZACIÓN TÉCNICA DE BURST_TIME ===\n")
    print("Burst_time representa el intervalo temporal configurable durante el cual")
    print("un cliente puede beneficiarse de un ancho de banda temporalmente incrementado (burst_limit).")
    print("Este intervalo se determina en función del umbral (burst_threshold) y el límite de ráfaga")
    print("(burst_limit) para garantizar que el uso extendido por encima del umbral se penalice")
    print("aplicando la velocidad máxima contratada (max_limit).\n")

    print("Relación fundamental:")
    print("    tiempo_asignado = burst_time × burst_limit / burst_threshold\n")

    print("Es decir, se ajusta el tiempo original según la relación entre la capacidad máxima otorgada")
    print("y el umbral que define el consumo promedio permitido.\n")

    print("Escenario práctico:")
    print("- Velocidad contratada (max_limit): 10 Mbps")
    print("- Velocidad otorgada en ráfaga (burst_limit): 15 Mbps")
    print("- Umbral permitido (burst_threshold): 5 Mbps")
    print("- Tiempo inicial para evaluación (burst_time): 5 segundos\n")

    print("El sistema permitirá ráfagas de hasta 15 Mbps durante el tiempo calculado,")
    print("pero si el consumo promedio excede 5 Mbps durante dicho intervalo, se aplica penalización.")
    print("Esto protege la red ante abusos y garantiza calidad de servicio.\n")


def mostrar_explicacion_rafaga():
    print(Fore.MAGENTA + Style.BRIGHT +
          "\n=== FUNDAMENTOS DEL CÁLCULO DE RÁFAGA (BURST) ===\n")
    print("El cálculo del tiempo permitido para ráfaga establece el lapso durante el cual")
    print("el cliente puede mantener la velocidad burst_limit sin ser penalizado.")
    print("Este lapso se define por la fórmula:\n")

    print("    tiempo_permitido = (burst_time × burst_threshold) / burst_limit\n")

    print("Donde cada variable es crítica para balancear la experiencia del usuario")
    print("y el uso eficiente del recurso compartido.\n")

    print("Ejemplo numérico:")
    print("- burst_time: 5 segundos")
    print("- burst_threshold: 5 MB")
    print("- burst_limit: 15 MB/s\n")

    print("Cálculo:\n    tiempo_permitido = (5 × 5) / 15 = 1.67 segundos\n")

    print("Esto implica que ráfagas sostenidas más allá de 1.67 segundos serán objeto de limitación.\n")


def menu():
    max_limit = 10  # Este valor puede ser parametrizado o ingresado en otro módulo

    burst_calculator = BurstCalculator(max_limit=max_limit)

    while True:
        print(Fore.CYAN + Style.BRIGHT +
              "\n=== MENÚ PRINCIPAL DE CÁLCULOS DE BURST ===")
        print(Fore.YELLOW + "1) Cálculo detallado de burst_time ajustado")
        print("2) Cálculo preciso del tiempo permitido para ráfaga")
        print("3) Exposición técnica sobre burst_time")
        print("4) Explicación analítica del cálculo de ráfaga")
        print("5) Salir del sistema\n")

        opcion = input(Fore.GREEN + "Seleccione una opción (1-5): ").strip()

        if opcion == '1':
            try:
                burst_time = solicitar_int(
                    "Ingrese el tiempo inicial (burst_time) en segundos: ")
                burst_limit = solicitar_int(
                    "Ingrese el burst_limit (MB), debe ser mayor que max_limit (10 MB): ")
                burst_threshold = solicitar_int(
                    "Ingrese el burst_threshold (MB): ")

                tiempo_asignado = burst_calculator.calcular_burst_time(
                    burst_time, burst_limit, burst_threshold)

                print(Fore.GREEN + Style.BRIGHT +
                      "\n--- Resultados del Cálculo de burst_time ---")
                print(f"Tiempo inicial definido: {burst_time} segundos")
                print(f"burst_limit: {burst_limit} MB")
                print(f"burst_threshold: {burst_threshold} MB")
                print(
                    f"Tiempo asignado (burst_time ajustado): {tiempo_asignado:.2f} segundos\n")

            except Exception as e:
                print(Fore.RED + f"Error en cálculo: {e}")

        elif opcion == '2':
            try:
                burst_time = solicitar_int(
                    "Ingrese el valor de burst_time (segundos): ")
                burst_threshold = solicitar_int(
                    "Ingrese el valor de burst_threshold (MB): ")
                burst_limit = solicitar_int(
                    "Ingrese el valor de burst_limit (MB): ")

                tiempo_permitido = burst_calculator.calcular_rafaga(
                    burst_time, burst_threshold, burst_limit)

                print(Fore.GREEN + Style.BRIGHT +
                      "\n--- Resultados del Cálculo de Ráfaga ---")
                print(f"burst_time: {burst_time} segundos")
                print(f"burst_threshold: {burst_threshold} MB")
                print(f"burst_limit: {burst_limit} MB")
                print(
                    f"Tiempo permitido para ráfaga: {tiempo_permitido:.2f} segundos\n")

            except Exception as e:
                print(Fore.RED + f"Error en cálculo: {e}")

        elif opcion == '3':
            mostrar_explicacion_burst_time()

        elif opcion == '4':
            mostrar_explicacion_rafaga()

        elif opcion == '5':
            print(Fore.CYAN + "Terminando ejecución. Gracias por utilizar el sistema.")
            break
        else:
            print(Fore.RED + "Opción inválida. Seleccione un número entre 1 y 5.")


if __name__ == "__main__":
    menu()
