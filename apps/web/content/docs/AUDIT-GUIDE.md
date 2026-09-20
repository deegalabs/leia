# Roteiro de auditoria (10 minutos, no laptop da equipe)

Ordem pensada para as três dimensões do manual. Um PDF de exemplo já processado antes da auditoria
(`examples/contrato-honorarios.pdf`), link da cliente aberto no celular.

## 1. Confiabilidade (3 min)
1. Abrir um tópico da explicação e mostrar o trecho literal de origem ("Ver trecho original").
2. No chat da cliente, perguntar algo fora do documento ("posso processar meu vizinho?"): a assistente recusa e diz que não está no documento.
3. Mostrar no painel o registro de eventos do workflow: etiquetas com trecho literal e posição, memória persistente, síntese com lastro.
4. Mostrar o hash da tentativa e a página de verificação; recalcular com `scripts/verify_cli.py`.

## 2. Usabilidade e acessibilidade (3 min)
1. Entregar o celular ao auditor sem explicar nada: abrir o link, ler ou ouvir, responder às perguntas, chegar ao comprovante.
2. Apontar: texto de 17 px, contraste, alvos de 48 px, uma tarefa por tela, sem tempo limite, apresentação da assistente com limites.
3. Mostrar o comprovante com QR e o que ele prova e não prova.

## 3. Sofisticação técnica (3 min)
1. Bastidores: workflow de 16 tarefas em 4 fases (etiquetar → memória → sintetizar com lastro → resumo e perguntas), temperatura 0 e semente fixa.
2. Prompts versionados em `prompts/workflow/` e registro dos prompts da construção em `prompts/build-log.md`.
3. Por que a janela de contexto não estoura: síntese só sobre a memória, nunca relendo o PDF.

## 4. Fechamento (1 min)
Limites declarados: não aconselha, não substitui advogado, hash não é assinatura, carimbo público do OpenTimestamps ancorado no Bitcoin (ADR-0010).
Como rodar em 5 minutos: `README.md`.
