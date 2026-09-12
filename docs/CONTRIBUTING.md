# Como trabalhar neste repositório

## Fonte da verdade e publicação
- **Fonte da verdade:** este repositório (`deegalabs/ciente` no GitHub), com histórico e uma tag por entrega.
- **Pasta oficial da OAB/PR:** recebe um **snapshot** a cada entrega (arquivos sem `.git`, mais `MANIFEST.md` apontando a
  tag e o commit). Comando, assim que a organização informar o repositório e o nome da pasta:
  ```bash
  # dentro do clone do repositório oficial, na pasta da equipe
  rsync -a --delete --exclude '.git' --exclude 'node_modules' --exclude '.venv' --exclude '.env' \
    /caminho/para/ciente/ ./equipes/token-economy/
  git add -A && git commit -m "team token-economy: v0.2.0 delivery" && git push
  ```
  Se o repositório oficial aceitar apenas pull requests, o mesmo snapshot vai por branch e PR.

## Estrutura e donos
```
apps/llm-service/   serviço FastAPI: API, workflow de LLM, hash e ancoragem; HTML de transição (Carlos)
apps/web/           interface Next.js: PWA da cidadã e painel do advogado (Daniel)
prompts/            prompts e workflows do produto (Carlos) e registro dos prompts da construção (todos)
docs/, evidence/    documentação e evidências (Vida, Camila, Caliane)
```

## Subir o serviço (Carlos)
```bash
git clone git@github.com:deegalabs/ciente.git && cd ciente
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
- Fechar entrega: `scripts/tag-delivery.sh vX.Y.0 "Entrega N: ..."` (ver `docs/DELIVERIES.md`).
