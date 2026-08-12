import time

from core.orchestrator import Orchestrator


# ============================================================
# JARVIS
# ============================================================

VERSION = "0.3"


def print_banner(jarvis):

    print()
    print("=" * 70)
    print("                         J A R V I S")
    print("=" * 70)
    print("                 PERSONAL AI ASSISTANT")
    print("=" * 70)
    print()
    print(f"Versión : {VERSION}")
    print(f"Modelo  : {jarvis.provider.get_model()}")

    if jarvis.provider.is_available():
        print("Estado  : ONLINE")
    else:
        print("Estado  : OFFLINE")

    print()
    print("Comandos:")
    print("  /help")
    print("  /clear")
    print("  /status")
    print("  /model")
    print("  /exit")
    print()


def show_help():

    print()
    print("COMANDOS DE JARVIS")
    print("-" * 40)
    print("/help    Mostrar ayuda")
    print("/clear   Borrar conversación")
    print("/status  Mostrar estado")
    print("/model   Mostrar modelo")
    print("/exit    Salir")
    print()
    print("También puedes hablar normalmente con JARVIS.")
    print()


def show_status(jarvis):

    print()
    print("ESTADO")
    print("-" * 40)
    print("Estado  : ONLINE")
    print("Modelo  :", jarvis.provider.get_model())
    print(
        "Mensajes:",
        len(jarvis.messages) - 1,
    )
    print("Agente  : ACTIVO")
    print("Tools   : ACTIVO")
    print()


def main():

    jarvis = Orchestrator()

    print_banner(jarvis)

    while True:

        try:

            user_input = input("Tú: ").strip()

            if not user_input:
                continue

            command = user_input.lower()

            # ------------------------------------------------
            # EXIT
            # ------------------------------------------------

            if command in (
                "/exit",
                "/salir",
                "salir",
            ):

                print()
                print("JARVIS: Cerrando sistema.")
                print()

                break

            # ------------------------------------------------
            # HELP
            # ------------------------------------------------

            if command == "/help":

                show_help()
                continue

            # ------------------------------------------------
            # CLEAR
            # ------------------------------------------------

            if command == "/clear":

                jarvis.reset()

                print()
                print(
                    "JARVIS: Conversación borrada."
                )
                print()

                continue

            # ------------------------------------------------
            # STATUS
            # ------------------------------------------------

            if command == "/status":

                show_status(jarvis)
                continue

            # ------------------------------------------------
            # MODEL
            # ------------------------------------------------

            if command == "/model":

                print()
                print(
                    "Modelo actual:",
                    jarvis.provider.get_model(),
                )
                print()

                continue

            # ------------------------------------------------
            # CHAT
            # ------------------------------------------------

            start = time.perf_counter()

            try:

                response = jarvis.chat(
                    user_input
                )

                elapsed = (
                    time.perf_counter()
                    - start
                )

                print()
                print("JARVIS:", response)
                print()
                print(
                    f"[{elapsed:.1f}s]"
                )
                print()

            except Exception as error:

                print()
                print(
                    "JARVIS: Encontré un error "
                    "al procesar la solicitud."
                )
                print()
                print(
                    "Error técnico:",
                    error,
                )
                print()

        except KeyboardInterrupt:

            print()
            print()
            print(
                "JARVIS: Sistema cerrado."
            )
            print()

            break

        except EOFError:

            print()
            print(
                "JARVIS: Sistema cerrado."
            )
            print()

            break


if __name__ == "__main__":
    main()