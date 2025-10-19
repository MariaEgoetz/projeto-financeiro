from django.db import transaction
from .base_repository import BaseRepository


class MovimentoRepository(BaseRepository):

    @transaction.atomic
    def create_completo(self, movimento_data, parcelas_data, fornecedor_id, faturado_id, classificacao_ids):
        query_mov = """
            INSERT INTO "MovimentoContas" (tipo, numeronotafiscal, dataemissao, descricao, valortotal, status, "Pessoas_idFornecedorCliente", "Pessoas_idFaturado")
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """
        movimento_id = self._execute_query(query_mov, [
            'PAGAR',
            movimento_data['numero_nota_fiscal'],
            movimento_data['data_emissao'],
            ', '.join(movimento_data['descricao_produtos']),
            sum(p['valor_total'] for p in parcelas_data),
            'PENDENTE',
            fornecedor_id,
            faturado_id
        ])

        query_m2m = 'INSERT INTO "MovimentoContas_has_Classificacao" ("MovimentoContas_idMovimentoContas", "Classificacao_idClassificacao") VALUES (%s, %s)'
        for class_id in classificacao_ids:
            self._execute_query(query_m2m, [movimento_id, class_id])

        query_par = """
            INSERT INTO "ParcelasContas"
            (identificacao, datavencimento, valorparcela, valorpago, valorsaldo, statusparcela, "MovimentoContas_idMovimentoContas")
            VALUES (%s, %s, %s, 0.0, %s, 'PENDENTE', %s)
        """
        for i, p_data in enumerate(parcelas_data):
            self._execute_query(query_par, [
                f"{i + 1}/{len(parcelas_data)}",
                p_data['data_vencimento'],
                p_data['valor_total'],
                p_data['valor_total'],
                movimento_id
            ])

        return movimento_id

    @transaction.atomic
    def create_recebimento(self, movimento_data, parcelas_data, cliente_id, classificacoes_ids):
        query_mov = """
                INSERT INTO "MovimentoContas" (tipo, numeronotafiscal, dataemissao, descricao, valortotal, status, "Pessoas_idFornecedorCliente", "Pessoas_idFaturado")
                VALUES ('RECEBER', %s, %s, %s, %s, 'PENDENTE', %s, %s) RETURNING id
            """
        total_parcelas = sum(p['valorparcela'] for p in parcelas_data)

        movimento_id = self._execute_query(query_mov, [
            movimento_data['numeronotafiscal'],
            movimento_data['dataemissao'],
            movimento_data['descricao'],
            total_parcelas,
            cliente_id,
            cliente_id
        ])

        query_m2m = 'INSERT INTO "MovimentoContas_has_Classificacao" ("MovimentoContas_idMovimentoContas", "Classificacao_idClassificacao") VALUES (%s, %s)'
        for class_id in classificacoes_ids:
            self._execute_query(query_m2m, [movimento_id, class_id])

        query_par = """
                INSERT INTO "ParcelasContas"
                (identificacao, datavencimento, valorparcela, valorpago, valorsaldo, statusparcela, "MovimentoContas_idMovimentoContas")
                VALUES (%s, %s, %s, 0.0, %s, 'PENDENTE', %s)
            """
        for p_data in parcelas_data:
            self._execute_query(query_par, [
                p_data['identificacao'],
                p_data['datavencimento'],
                p_data['valorparcela'],
                p_data['valorparcela'],
                movimento_id
            ])

        return movimento_id

    def list_all_movements(self):
        query = """
            SELECT
                mc.id,
                mc.dataemissao,
                mc.numeronotafiscal,
                mc.tipo,
                p_fc.razaosocial AS fornecedor_cliente,
                p_f.razaosocial AS faturado,
                mc.valortotal,
                mc.status
            FROM "MovimentoContas" mc
            JOIN "Pessoas" p_fc ON mc."Pessoas_idFornecedorCliente" = p_fc.id
            JOIN "Pessoas" p_f ON mc."Pessoas_idFaturado" = p_f.id
            ORDER BY mc.dataemissao DESC, mc.id DESC
        """
        return self._execute_query(query, fetch="all")
