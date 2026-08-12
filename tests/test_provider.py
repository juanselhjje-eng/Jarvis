from providers.ollama_provider import OllamaProvider


def main():
    provider = OllamaProvider("qwen3.5:4b")

    messages = [
        {
            "role": "user",
            "content": "Responde solamente: JARVIS funcionando."
        }
    ]

    print()
    print("=" * 60)
    print("PRUEBA DEL PROVEEDOR")
    print("=" * 60)
    print()
    print("Proveedor:", provider.name)
    print("Modelo:", provider.model)
    print()
    print("Respuesta:")
    print()

    response = provider.chat(messages)

    print(response)
    print()


if __name__ == "__main__":
    main()