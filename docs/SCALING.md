# Escala: 1, 100 e 1.000 usuários

Princípio que muda tudo: **o trabalho caro de IA é por documento, não por cidadão.** A explicação, as citações,
o juiz e as perguntas são gerados uma vez por documento e aprovados pelo advogado; o cidadão consome conteúdo
pronto. Por cidadão só existem chamadas curtas: avaliar 2 a 3 respostas abertas e, se houver, dúvidas livres.
Áudio é gerado por sentença e reaproveitado por todos os cidadãos do mesmo documento.

| Dimensão | 1 usuário (demo, auditoria) | 100 usuários (piloto: um escritório, uma Defensoria) | 1.000 usuários (seccional) |
|---|---|---|---|
| Interface | Next.js em um servidor | igual; páginas do cidadão estáticas + chamadas de API | CDN; várias réplicas; sem estado no servidor |
| Serviço FastAPI | 1 processo `uvicorn` | `uvicorn` com workers; chamadas de LLM assíncronas (I/O) | réplicas atrás de balanceador; fila (Redis) para gerar explicações e ancorar |
| Banco | SQLite | Postgres gerenciado (escritas concorrentes) | Postgres com réplica de leitura; tabela `events` particionada por mês |
| Arquivos (PDF, áudio) | disco local | armazenamento de objetos (S3 ou equivalente), URL assinada | igual, com ciclo de vida (retenção) |
| LLM: geração por documento | 1 chamada de cada tipo por upload | igual; limite passa a ser a cota do provedor (requisições e tokens por minuto): conferir o tier | fila com concorrência limitada; **cache por hash do PDF**: contratos padrão repetem, mesma explicação para todos |
| LLM: por cidadão | 2 a 3 avaliações + dúvidas | igual | igual; modelo menor para avaliação se a rubrica se mantiver |
| Voz | TTS por sentença ao vivo | TTS pré-gerado no upload e guardado por documento | igual; cache elimina custo marginal por cidadão |
| Registro público | 1 transação por consentimento | 1 por consentimento; fila serial no relayer (nonce) | **lote**: raiz Merkle de N consentimentos por transação (a cada minuto); cada comprovante leva a prova Merkle; custo on-chain fixo por lote |
| OpenTimestamps | 1 carimbo por consentimento | igual (gratuito, agrega por natureza) | igual |
| Custo marginal por consentimento (estimativa, preços de 11/09) | < R$ 2 (documento novo: explicação + juiz + perguntas ≈ R$ 1 a 1,50; avaliação ≈ R$ 0,10; registro R$ 0,01) | ≈ R$ 0,20 a 0,50 quando o documento já foi explicado | ≈ R$ 0,10 a 0,30 com cache por hash e lote no registro |
| Risco principal | chave de API e RPC no dia | cota do provedor; SQLite travando em escrita | vazamento entre escritórios (multi-tenant); custo de tokens sem cache |

## O que a V1 já faz certo para escalar
- Conteúdo pré-gerado e aprovado: o cidadão nunca dispara a chamada cara.
- Estado da sessão no servidor, não no navegador: várias sessões simultâneas por link.
- Prompts versionados: trocar de modelo ou de fornecedor sem mudar a interface.
- Hash canônico e verificação pública independentes do fornecedor de IA.

## O que fica para depois do evento
- Fila e cache por hash do PDF (100+).
- Lote Merkle no `ConsentRegistry` (`anchorRoot(bytes32 root)` + prova no comprovante) (1.000+).
- Multi-tenant por escritório, retenção configurável, observabilidade de tokens por consentimento.
