# Limites de API

## Limite por plano

O plano Mensal permite 60 requisicoes por minuto. O plano Pro permite 600
requisicoes por minuto. O plano Enterprise permite 6000 requisicoes por
minuto.

Nao existe plano com chamadas ilimitadas.

## Excedente

Ao ultrapassar o limite a API responde 429 com o cabecalho Retry-After. O
excedente e cobrado por pacote de mil requisicoes e nao e reembolsavel.
