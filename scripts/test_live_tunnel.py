import httpx
import time
import json

def main():
    url = "https://repackage-remarry-reviving.ngrok-free.dev/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
        "User-Agent": "VotoSeguro-Test/2.0",
    }
    payload = {
        "model": "votoseguro-lfm3",
        "messages": [
            {
                "role": "user",
                "content": (
                    "Tarea: Extrae campos de la cédula: "
                    "ESTADO PLURINACIONAL DE BOLIVIA CEDULA DE IDENTIDAD N° 8001002 SC "
                    "NOMBRES: JUAN CARLOS APELLIDOS: PEREZ GOMEZ FECHA DE NACIMIENTO: 14/05/2001. "
                    "Devuelve solo un JSON válido con las llaves: ci, nombres, apellidos, fecha_nacimiento."
                ),
            }
        ],
        "temperature": 0.0,
    }

    print(f"Connecting to live static ngrok tunnel: {url} ...")
    t0 = time.time()
    resp = httpx.post(url, json=payload, headers=headers, timeout=25.0)
    latency_ms = (time.time() - t0) * 1000

    print(f"Response status: {resp.status_code}")
    print(f"Latency: {latency_ms:.1f} ms")

    if resp.status_code == 200:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print("Raw Content:")
        print(content)
        try:
            parsed = json.loads(content)
            print("\nParsed JSON:")
            print(json.dumps(parsed, indent=2))
            print("\nSUCCESS: Live neural inference via static ngrok tunnel completed successfully!")
        except Exception as e:
            print(f"JSON parse error: {e}")
    else:
        print(f"Error body: {resp.text}")

if __name__ == "__main__":
    main()
