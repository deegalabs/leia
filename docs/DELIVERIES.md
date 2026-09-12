# Entregas versionadas

Cada entrega do hackathon é uma **tag anotada** no git. Docs, arquitetura, prompts e código de cada entrega ficam
congelados na tag; o trabalho continua em `main`. A evidência de cada entrega vai na pasta correspondente em
`evidence/`, com um `MANIFEST.md` que aponta a tag e o commit.

| Entrega | Tag | Prazo | Evidência | O que a tag congela |
|---|---|---|---|---|
| 1. Canvas | `v0.1.0` | sáb 12h | `evidence/01-canvas/` | canvas, base documental, política de prompts |
| 2. V1 com testes internos | `v0.2.0` | sáb 15h30 | `evidence/02-internal-tests/` | primeiro código de `apps/`, `docs/INTERNAL-TESTS.md` preenchido, prompts v0.x |
| 3. V2 com testes externos | `v0.3.0` | sáb 17h30 | `evidence/03-external-tests/` | voz, ancoragem, verificação; planilha e depoimentos |
| 4. Produto e auditoria | `v0.4.0` | dom 10h30 | `evidence/04-product/` | README de execução, dados de exemplo, roteiro de auditoria, relatório adversarial |
| 5. Slides | `v0.5.0` | dom 14h30 | `evidence/05-slides/` | deck de 2 minutos e vídeo da demo |
| Pitch | `v1.0.0` | dom 16h30 | | estado apresentado à banca |

## Como fechar uma entrega
```bash
# 1. tudo commitado em main (Conventional Commits, inglês)
# 2. preencher a seção da versão em CHANGELOG.md (o script cria o esqueleto a partir dos commits)
scripts/tag-delivery.sh v0.2.0 "Entrega 2: V1 com testes internos"
# 3. escrever evidence/0N-.../MANIFEST.md com tag, commit, hora e lista dos arquivos de evidência
# 4. publicar na pasta da equipe no repositório oficial
```

## Como consultar
```bash
git tag -n9                          # lista as entregas com a mensagem
git checkout v0.2.0                  # estado exato da entrega 2
git diff v0.1.0..v0.2.0 --stat       # o que mudou entre a 1 e a 2
git diff v0.1.0..v0.2.0 -- docs/     # só a documentação
git log v0.1.0..v0.2.0 --oneline     # commits da entrega 2
```

## Versão nos documentos
Os documentos não carregam número de versão no texto: a versão é a tag. Um documento alterado depois de uma entrega
aparece no `git diff` entre tags. `CHANGELOG.md` resume, por entrega, o que mudou em docs, arquitetura, prompts e código.
