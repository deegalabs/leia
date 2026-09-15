# Como contribuir

Este repositório é público e aceita contribuição. A regra é curta: ninguém escreve direto na `main`, toda mudança
passa por pull request e todo pull request precisa de uma aprovação e da integração contínua verde.

## O caminho de uma mudança

1. **Issue primeiro.** Use o modelo de [erro](../.github/ISSUE_TEMPLATE/erro.yml) ou de
   [melhoria](../.github/ISSUE_TEMPLATE/melhoria.yml). Espere a issue ser aceita antes de escrever código.
   Isso evita trabalho jogado fora quando a proposta esbarra em um limite do produto.
2. **Branch a partir da `main`**, nomeada pelo tipo e pelo número da issue.
   ```bash
   git switch main && git pull
   git switch -c fix/123-comprovante-sem-carimbo
   ```
   Prefixos: `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`, `test/`.
3. **Teste antes da correção.** Escreva o teste, rode, veja falhar pelo motivo certo, e só então mude o código.
   Um teste que já nasce passando não prova nada e não deve entrar.
4. **Commits em inglês**, [Conventional Commits](https://www.conventionalcommits.org/pt-br/), escopo no nome do app.
   ```
   fix(service): stop serving the answer key before the citizen answers
   feat(web): let the citizen claim the document explicitly
   docs: describe the review gate
   ```
   Sem linha de coautor. Commits pequenos, um assunto por commit.
5. **Pull request** com o modelo preenchido, escrevendo `Closes #123` para a issue que ele fecha. A palavra-chave
   precisa ser em inglês, porque é só assim que o GitHub fecha a issue no merge. A integração contínua roda sozinha e
   a Vercel publica uma prévia da aplicação no próprio pull request.
6. **Revisão.** Uma aprovação libera o merge. Depois do merge na `main`, aplicação e serviço sobem em produção
   automaticamente.

## Rodar e testar

```bash
# serviço
cd apps/llm-service
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q

# aplicação
cd apps/web
pnpm install
pnpm test && pnpm lint && pnpm build
```

Sem chave de modelo dá para trabalhar na interface inteira: `pnpm dev` sozinho usa o mock em `apps/web/app/api/*`,
e o serviço tem um mock equivalente em `uvicorn mock.app:app --port 8000`.

## Estrutura

```
apps/web/           aplicação Next.js: jornada do cidadão, painel do advogado, comprovante, verificação, docs
apps/llm-service/   serviço FastAPI: API v3, pipeline de LLM, registro público, carimbo de tempo
docs/               documentação do produto; docs/brand é a marca, docs/design são as telas
prompts/            prompts do produto, versionados
examples/           PDFs fictícios para rodar sem dado de ninguém
evidence/           evidências das entregas do hackathon, histórico, não se mexe
scripts/            utilitários, entre eles a conferência de um registro fora do serviço
```

## Regras que não são preferência

- **Idioma.** Interface e documentação em português simples, sem juridiquês e sem travessão. Código,
  identificadores, nomes de arquivo, mensagens de commit e prompts em inglês.
- **Nada de dado pessoal real.** Nem em `examples/`, nem em `evidence/`, nem em teste, nem em issue. Os PDFs
  do repositório são fictícios.
- **Segredo nunca entra no repositório.** Só variável de ambiente, com o modelo em `.env.example` e valor vazio.
- **Afirmação sempre com trecho.** Nenhuma frase nova sobre o documento pode existir sem o trecho literal que a
  sustenta. Pergunta fora do documento recebe recusa explícita.
- **Nada pessoal no registro público.** O payload publicado carrega hashes, não texto.
- **A plataforma não aconselha.** Não interpreta o caso concreto, não recomenda aceitar ou recusar, não substitui
  o advogado. Ver [POSITIONING.md](POSITIONING.md).
- **Arquivo gerado não carrega metadado de ferramenta.** Vale para o comprovante em PDF e para qualquer imagem.
- **Acessibilidade é requisito.** Alvo de toque grande, contraste medido, foco visível, movimento reduzido
  respeitado. O piso é um celular básico, não um aparelho potente.

## Segurança

Falha que exponha dado ou permita produzir comprovante indevido não vira issue pública.
Use o [relato privado](https://github.com/deegalabs/leia/security/advisories/new). O escopo está em
[SECURITY.md](../.github/SECURITY.md).

## Histórico

O projeto nasceu no Hackathon da Cidadania OAB-PR, 6ª edição, em 12 e 13 de setembro de 2026. As entregas do evento
estão registradas em [DELIVERIES.md](DELIVERIES.md), no [CHANGELOG.md](../CHANGELOG.md) e na pasta `evidence/`,
com a tag `token-economy/v0.1.0` marcando a primeira delas. Esse material é registro do que aconteceu e fica como
está; o desenvolvimento seguiu a partir da versão `v1.0.0`.
