# Idioma da interface

`pt-BR.json` concentra todo texto da interface (cidadã, advogado, verificação), organizado por tela (`ch`, `c0`…`c6`,
`a0`…`a4`, `p1`) e por grupos comuns (`banner`, `common`, `status`). Placeholders no formato `{firstName}`.

Uso previsto no Next.js: `next-intl` com `pt-BR` como único locale na V1 (mensagens carregadas de `messages/pt-BR.json`);
ou import direto do JSON com uma função `t(key, vars)` de 10 linhas até haver segundo idioma.

Regras: sentence case; verbo + resultado nos botões; frases ≤ 15 palavras; palavras proibidas em telas da cidadã:
"errado", "incorreto", "reprovado", "nota", "teste", "prova", "quiz". Toda mudança de copy entra aqui, nunca no componente.
