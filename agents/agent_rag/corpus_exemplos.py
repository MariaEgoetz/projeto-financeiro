"""
Este arquivo contém o "Corpus de Conhecimento" para o Agente RAG.
São pares de "Pergunta" (em linguagem natural) e "Query" (em SQL)
que o agente usará como exemplos para aprender a consultar o banco.
"""

CORPUS_EXEMPLOS = [
    {
        "pergunta": "Quantos fornecedores eu tenho cadastrados?",
        "query": """SELECT count(*) FROM "Pessoas" WHERE UPPER(tipo) = 'FORNECEDOR';"""
    },
    {
        "pergunta": "Liste o nome e o documento de todos os clientes ativos.",
        "query": """SELECT razaosocial, documento FROM "Pessoas" WHERE UPPER(tipo) = 'CLIENTE' AND UPPER(status) = 'ATIVO';"""
    },
    {
        "pergunta": "Qual o valor total de todas as contas a pagar que estão pendentes?",
        "query": """SELECT SUM(valortotal) FROM "MovimentoContas" WHERE UPPER(tipo) = 'PAGAR' AND UPPER(status) = 'PENDENTE';"""
    },
    {
        "pergunta": "Quanto eu tenho para receber no total?",
        "query": """SELECT SUM(valortotal) FROM "MovimentoContas" WHERE UPPER(tipo) = 'RECEBER';"""
    },
    {
        "pergunta": "Quais são as classificações de despesa disponíveis?",
        "query": """SELECT descricao FROM "Classificacao" WHERE UPPER(tipo) = 'DESPESA';"""
    },
    {
        "pergunta": "Quantos movimentos (notas) foram registrados no total?",
        "query": """SELECT count(*) FROM "MovimentoContas";"""
    },
    {
        "pergunta": "Qual é o documento da pessoa com razaosocial 'Nome Exato da Pessoa'?",
        "query": """SELECT documento FROM "Pessoas" WHERE UPPER(razaosocial) = UPPER('Nome Exato da Pessoa');"""
    },
    {
        "pergunta": "Liste todas as parcelas pendentes, ordenadas por vencimento.",
        "query": """SELECT identificacao, valorparcela, datavencimento FROM "ParcelasContas" WHERE UPPER(statusparcela) = 'PENDENTE' ORDER BY datavencimento ASC;"""
    },
    {
        "pergunta": "Quais foram os últimos 5 movimentos do tipo 'PAGAR'?",
        "query": """SELECT numeronotafiscal, valortotal, dataemissao FROM "MovimentoContas" WHERE UPPER(tipo) = 'PAGAR' ORDER BY dataemissao DESC LIMIT 5;"""
    },
    {
        "pergunta": "Quem é o fornecedor da nota fiscal 'NF-123'?",
        "query": """SELECT T1.razaosocial FROM "Pessoas" T1 JOIN "MovimentoContas" T2 ON T1.id = T2."Pessoas_idFornecedorCliente" WHERE UPPER(T2.numeronotafiscal) = UPPER('NF-123');"""
    },
    {
        "pergunta": "Quem foi o faturado no movimento de ID 10?",
        "query": """SELECT T1.razaosocial FROM "Pessoas" T1 JOIN "MovimentoContas" T2 ON T1.id = T2."Pessoas_idFaturado" WHERE T2.id = 10;"""
    },
    {
        "pergunta": "Existem pessoas cadastradas como 'INATIVO'?",
        "query": """SELECT razaosocial, status FROM "Pessoas" WHERE UPPER(status) = 'INATIVO';"""
    },
    {
        "pergunta": "Qual o valor médio dos movimentos a pagar?",
        "query": """SELECT AVG(valortotal) FROM "MovimentoContas" WHERE UPPER(tipo) = 'PAGAR';"""
    },
    {
        "pergunta": "Quais as parcelas do movimento da nota 'NF-456'?",
        "query": """SELECT T1.identificacao, T1.valorparcela FROM "ParcelasContas" T1 JOIN "MovimentoContas" T2 ON T1."MovimentoContas_idMovimentoContas" = T2.id WHERE UPPER(T2.numeronotafiscal) = UPPER('NF-456');"""
    },
    {
        "pergunta": "Liste os movimentos emitidos em 30 de outubro de 2024.",
        "query": """SELECT numeronotafiscal, valortotal FROM "MovimentoContas" WHERE dataemissao = '2024-10-30';"""
    },
    {
        "pergunta": "Quais contas a receber foram emitidas em outubro de 2024?",
        "query": """SELECT numeronotafiscal, valortotal, dataemissao FROM "MovimentoContas" WHERE UPPER(tipo) = 'RECEBER' AND dataemissao BETWEEN '2024-10-01' AND '2024-10-31';"""
    },
    {
        "pergunta": "A quais classificações pertence o movimento de ID 15?",
        "query": """SELECT T2.descricao FROM "MovimentoContas_has_Classificacao" T1 JOIN "Classificacao" T2 ON T1."Classificacao_idClassificacao" = T2.id WHERE T1."MovimentoContas_idMovimentoContas" = 15;"""
    },
    {
        "pergunta": "Quais movimentos são da classificação 'INSUMOS AGRÍCOLAS'?",
        "query": """SELECT T2.id, T2.numeronotafiscal FROM "Classificacao" T1 JOIN "MovimentoContas_has_Classificacao" T_JOIN ON T1.id = T_JOIN."Classificacao_idClassificacao" JOIN "MovimentoContas" T2 ON T_JOIN."MovimentoContas_idMovimentoContas" = T2.id WHERE UPPER(T1.descricao) = UPPER('INSUMOS AGRÍCOLAS');"""
    },
    {
        "pergunta": "Temos parcelas vencidas que ainda estão pendentes?",
        "query": """SELECT identificacao, valorparcela, datavencimento FROM "ParcelasContas" WHERE UPPER(statusparcela) = 'PENDENTE' AND datavencimento < CURRENT_DATE;"""
    },
    {
        "pergunta": "Qual o maior valor de parcela única registrado?",
        "query": """SELECT MAX(valorparcela) FROM "ParcelasContas";"""
    }
]