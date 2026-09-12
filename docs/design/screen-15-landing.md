# Tela 15 · Landing page (`/`)

## Propósito
Explicar o LeIA em uma rolagem, para três leitores: a cidadã que recebeu um link e quer saber o que é isso, o advogado
que vai decidir usar, e o auditor ou jurado que quer entender o produto em 30 segundos. Página estática, sem login.

## Estrutura (ordem fixa)
1. **Abertura**: símbolo da marca + "LeIA"; título "Leia antes de assinar."; subtítulo "Um advogado envia o documento. Você entende cada parte, em linguagem simples e por voz. Depois fica registrado que você entendeu."; botões "Sou advogado: começar" (primário → `/lawyer/login`) e "Ver um exemplo" (secundário → sessão de demonstração).
2. **Como funciona**, 3 passos com ícone: (1) `FileText` "O advogado envia o documento e aprova a explicação"; (2) `Mic` "Você ouve, pergunta e responde com suas palavras"; (3) `BadgeCheck` "O advogado valida e você recebe o comprovante".
3. **Para quem**: cidadã (entender antes de assinar, em ambiente seguro), advogado (supervisionar e ter a prova do esclarecimento), instituições de acesso à justiça (Defensoria, dativos, Espaço OAB Cidadania).
4. **Por que confiar**, 4 itens curtos: cada explicação mostra o trecho original; o que não está no documento a assistente recusa; o advogado aprova antes e valida depois; o registro público guarda só um código, nunca seus dados.
5. **Código aberto**: "Feito no Hackathon da Cidadania OAB-PR 2026, equipe Token Economy. Código aberto, licença MIT." + link do repositório.
6. **Rodapé**: "A assistente explica o que está escrito. Não dá conselho jurídico e não substitui o advogado." + acessibilidade (símbolo, VLibras) + contato.

## Regras
- Mesma paleta e tipografia da jornada (paper, ink, teal de ação); abertura pode usar marinho com a logo.
- Frases ≤ 15 palavras; sem "blockchain", "token", "IA generativa" no texto principal (rodapé pode dizer "registro público com carimbo de tempo").
- Uma coluna no celular; imagens: nenhuma além do símbolo e dos ícones; sem carrossel.
- Acessibilidade: `lang="pt-BR"`, títulos em ordem, foco visível, símbolo de acessibilidade (LBI art. 63), VLibras.

## Estados
Só o padrão. Se a demonstração não estiver disponível, o botão "Ver um exemplo" some (nunca fica desabilitado).

## Entrega
Produto (dom 10h30). Não bloqueia V1 nem V2.
