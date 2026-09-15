# Changelog

Versões do produto, da mais recente para a mais antiga. As entregas do hackathon que deu origem ao projeto estão
no fim, com as evidências em `evidence/` e o índice em [docs/DELIVERIES.md](docs/DELIVERIES.md).

## v1.0.0 · 2026-09-15 · primeira versão pública

Repositório aberto sob licença MIT, em produção em https://leia-snowy.vercel.app.

### Produto
- Jornada do cidadão: explicação em linguagem simples com o trecho original ao lado, um tópico por vez, dúvidas
  respondidas só com o que está no documento, conferência de compreensão com rubrica e ponto a rever quando erra.
- Painel do advogado: envio do documento, revisão do resumo estruturado e aprovação, que é o que libera o link.
- Comprovante com QR e página pública de verificação, conferível por terceiro sem depender do serviço.
- Documentação navegável em `/docs`, gerada a partir do markdown do repositório, com diagramas em tela cheia.
- Aplicação instalável, responsiva do celular ao computador.

### Segurança e privacidade
- O registro público deixou de carregar o link do documento do cidadão. Passou a identificá-lo por um hash
  (`documentRef`), sem o `salt` decorativo que não protegia nada.
- O hash da tentativa virou reprodutível a partir do que fica gravado, sem endereço de rede nem navegador.
- Teto de tentativas na conferência, para o registro não sair por tentativa e erro.
- O comprovante em PDF deixou de afirmar o que não prova e de imprimir endereço de rede e navegador.
- A casca HTML antiga do serviço saiu inteira: dez rotas, sete templates, e com elas o gabarito que ficava
  visível no HTML e o PDF acessível sem autenticação.
- Rotas de bastidor restritas ao papel de fornecedor.
- Abrir o link deixou de vincular o documento a quem abriu; o vínculo virou um ato explícito.
- O markdown da documentação deixou de renderizar HTML bruto, fechando a injeção por pull request de documentação.
- Prova de carimbo que não corresponde ao registro é refeita em vez de bloquear o carimbo.

### Infraestrutura
- Integração contínua nos dois lados a cada pull request, com `main` protegida: pull request obrigatório,
  uma aprovação e verificação verde.
- Sinal de vida em `GET /health` no serviço, que é o que autoriza uma versão nova a assumir.

## Hackathon da Cidadania OAB-PR · 12 e 13 de setembro de 2026

Equipe Token Economy, categoria Inovação Aberta e Cidadania. O produto nasceu aqui, com o nome definido durante
o evento: LeIA, de Lei mais IA, antes ConsentChain e Ciente.

- **Entrega 1, Canvas** (`token-economy/v0.1.0`, sáb 12h): canvas transcrito em `docs/CANVAS.md`, mais
  posicionamento, arquitetura, contrato da API, personas, casos de uso, telas, escopo por entrega, roadmap,
  escala e plano de testes.
- **Entregas 2 e 3** (V1 com testes internos, V2 com testes externos): aconteceram no evento e estão no histórico
  do git, sem tag e sem arquivo em `evidence/`. O que foi testado está em `docs/INTERNAL-TESTS.md`.
- **Entrega 4, produto e auditoria**: 20 arquivos em `evidence/04-product/`.
- **Entrega 5, slides**: apresentação e guia de defesa em `evidence/05-slides/`.

O código de cada entrega está no histórico do git entre a tag da Entrega 1 e a `v1.0.0`. As pastas
`evidence/01-canvas/`, `02-internal-tests/` e `03-external-tests/` ficaram vazias.
