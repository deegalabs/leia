# apps/llm-service

Serviço cognitivo (FastAPI) do LeIA. O código do serviço é do Carlos e entra nesta pasta quando for enviado. O que já
está aqui é o que a interface acrescenta e funciona sozinho com um mock:

```
leia/registry.py            comprovante, verificação pública, JSON canônico + SHA-256, OpenTimestamps, QR, PDF sem metadados
templates/leia/cliente.html página da cidadã (boas-vindas, um ponto por vez com trecho literal, dúvida, perguntas, resultado)
templates/leia/comprovante.html, verify.html
static/                     leia-theme.css, leia-icons.svg, logos, leia-api.js (cliente das rotas do serviço)
mock/app.py                 rotas do serviço com dados de exemplo (examples/fixture-honorarios.json)
tests_leia.py               testes de fumaça (gabarito fora do HTML, quiz, comprovante, verificação, recusa no chat)
requirements-leia.txt       qrcode, pypdf, opentimestamps-client
```

## Rodar o mock (sem o serviço)
```bash
python -m venv .venv && . .venv/bin/activate
pip install fastapi uvicorn jinja2 -r requirements-leia.txt
uvicorn mock.app:app --reload --port 8000      # abre http://localhost:8000 (redireciona para /t/demo)
python -m pytest -q tests_leia.py               # precisa de httpx2 e pytest
```
O mock responde às mesmas rotas do serviço (`/t/{hash}`, `/api/t/{hash}/quiz`, `/api/t/{hash}/chat`) e às rotas do
comprovante. Aprovar a tentativa carimba o hash no OpenTimestamps (desligue com `OTS_ENABLED=false`).

## Integrar no serviço real (10 minutos)
1. Copiar o código do serviço para esta pasta (sem `.env`, `.venv`, `__pycache__`, banco).
2. `pip install -r requirements-leia.txt`.
3. Em cada template do serviço, depois do `<style>` existente: `<link rel="stylesheet" href="/static/leia-theme.css">`.
   Na página da cidadã, `<body class="leia-citizen">`. Ou trocar a página da cidadã por `templates/leia/cliente.html`,
   que usa o mesmo contexto (`tarefa`, `resumo_md`, `questoes`, `ultima_tentativa`, opcional `topicos`).
4. Textos: `python ../../scripts/apply_copy.py templates --write` aplica a tabela `docs/brand/copy-replacements.json`.
5. Comprovante e verificação, no arquivo principal do serviço:
   ```python
   from leia.registry import build_router, build_payload, payload_hash, ots_stamp
   app.include_router(build_router(get_attempt, templates))   # get_attempt(hash_imutavel) -> dict | None
   ```
   Ao aprovar uma tentativa: `ots = ots_stamp(payload_hash(build_payload(attempt))[1])` e gravar `ots` e `salt` na tentativa.
6. Variáveis: copiar `../../.env.example` para `.env` (`BASE_URL` entra no QR).
7. Conferir: `/t/{hash}` sem `correta` no HTML (`curl -s .../t/X | grep -c correta` deve dar 0), `/t/{hash_imutavel}/comprovante`
   abre com QR, `/verify/{hash_imutavel}?format=json` devolve o hash. `scripts/verify_cli.py` recalcula o hash a partir do JSON.

## Servir a interface em outra origem
`static/leia-api.js` lê `window.LEIA_API_BASE`. Defina-a antes do script para apontar para a URL do serviço e libere CORS
nele para a origem da interface. Por padrão a interface roda dentro do próprio serviço, sem CORS.
