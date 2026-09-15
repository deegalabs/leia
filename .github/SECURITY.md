# Segurança

## Como relatar

Não abra issue pública. Use o [relato privado de segurança](https://github.com/deegalabs/leia/security/advisories/new)
do próprio GitHub. A resposta sai em até cinco dias úteis.

Diga o que é possível fazer com a falha, não só onde ela está. Se houver prova de conceito, descreva os passos
sem anexar documento, token ou dado de pessoa real.

## O que tratamos como falha grave

- Acesso ao documento de alguém sem ser a pessoa que o recebeu ou o advogado que o enviou.
- Gabarito das perguntas de compreensão visível antes da resposta.
- Registro público que permita chegar ao documento, ao link da pessoa ou a qualquer dado pessoal.
- Comprovante que possa ser produzido sem a leitura e a conferência terem acontecido.
- Execução de código de terceiro na origem da aplicação, inclusive por markdown de documentação.
- Rota de bastidor acessível sem a credencial do fornecedor.

## O que está fora do escopo

Relatório automático de varredura sem impacto demonstrado, ausência de cabeçalho que não leve a nada,
e falha em dependência de terceiro sem caminho de exploração neste código.

## Versões

O produto é publicado continuamente a partir da `main`. Só a versão em produção recebe correção.
