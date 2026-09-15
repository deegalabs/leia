## O que muda

<!-- Uma frase. O que passa a ser verdade depois deste merge. -->

Fecha #

## Como verificar

<!-- Os comandos que alguém roda para ver isso funcionando, ou a tela e o caminho até ela. -->

```bash
```

## Antes de pedir revisão

- [ ] O teste foi escrito antes da correção e foi visto falhando pelo motivo certo.
- [ ] `pytest -q tests_leia.py tests_v3.py` passa, quando o serviço mudou.
- [ ] `pnpm test && pnpm lint && pnpm build` passa, quando a aplicação mudou.
- [ ] Nenhuma chave, senha, token ou documento de pessoa real entrou no diff.
- [ ] Texto de interface em português simples, sem juridiquês e sem travessão.
- [ ] Nenhuma afirmação nova sobre o documento sem o trecho literal que a sustenta.

## O que isso quebra

<!-- Mudança de rota, de contrato da API, de formato do registro ou de variável de ambiente.
     Escreva "nada" se for o caso, e não deixe em branco. -->
