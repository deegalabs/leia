# Como trabalhar neste repositório

## Fonte da verdade e publicação
- **Regra do evento (Manual §2 e §5d; Regras do Jogo):** documentação e protótipo publicados **no repositório oficial da
  OAB/PR, em pasta por equipe**. Esse repositório é a fonte da verdade e o lugar das entregas. Não há repositório
  paralelo em outra organização.
- **Até a organização informar a URL e o nome da pasta:** o trabalho continua neste clone local, com commits normais.
  Quando o repositório oficial estiver disponível, o histórico entra inteiro na pasta da equipe com `git subtree`:
  ```bash
  git clone <URL do repositório oficial> oab && cd oab
  git subtree add --prefix=equipes/token-economy /caminho/para/ciente main   # ajustar o nome da pasta ao padrão da OAB
  git push
  ```
  Depois disso, todo mundo trabalha **dentro do clone do repositório oficial**, na pasta da equipe; o clone local antigo
  é descartado.
- **Tags de entrega** levam o prefixo da equipe para não colidir com outras equipes no mesmo repositório:
  `token-economy/v0.1.0`, `token-economy/v0.2.0`, ... Se a organização não permitir tags, o `MANIFEST.md` de cada
  pasta de evidência guarda o hash do commit da entrega, que é a referência estável.

## Estrutura e donos
```
apps/llm-service/   serviço FastAPI: API, workflow de LLM, hash e ancoragem; HTML de transição (Carlos)
apps/web/           interface Next.js: PWA da cidadã e painel do advogado (Daniel)
prompts/            prompts e workflows do produto (Carlos) e registro dos prompts da construção (todos)
docs/, evidence/    documentação e evidências (Vida, Camila, Caliane)
```

## Subir o serviço (Carlos)
```bash
git clone <URL do repositório oficial> oab && cd oab/equipes/token-economy    # ou o clone local até a URL existir
git checkout -b feat/llm-service
mkdir -p apps/llm-service && cp -r /seu/projeto/* apps/llm-service/    # sem .env, sem .venv, sem __pycache__
cp /seu/projeto/workflow.json prompts/workflow/v1-carlos.json          # toda versão nova do workflow entra aqui
git add -A && git commit -m "feat(llm-service): initial fastapi service with html prototype"
git push -u origin feat/llm-service
```
Depois: abrir pull request para `main` (ou avisar no grupo e fazer merge direto durante o evento). Obrigatório no
`apps/llm-service/README.md`: comando para instalar e rodar, porta, variáveis de ambiente (`.env.example` sem valores),
como testar com um PDF de `examples/`.

## Regras rápidas
- Commits pequenos, em inglês, Conventional Commits (`feat`, `fix`, `docs`, `chore`); nunca commitar `.env` ou chaves.
- Nada de dado pessoal real em `examples/` ou `evidence/`: PDFs anonimizados.
- Toda mudança de prompt ou workflow entra em `prompts/` com nome e versão; todo prompt usado na construção entra em
  `prompts/build-log.md`.
- Fechar entrega: `scripts/tag-delivery.sh token-economy/vX.Y.0 "Entrega N: ..."` (ver `docs/DELIVERIES.md`).
