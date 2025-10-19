from .base_repository import BaseRepository


class ClassificacaoRepository(BaseRepository):

    def find_by_descricao(self, descricao):
        query = """SELECT id FROM "Classificacao" WHERE descricao = %s AND tipo = 'DESPESA'"""
        result = self._execute_query(query, [descricao], fetch='one')
        return result[0] if result else None

    def create(self, tipo, descricao):
        query = """
            INSERT INTO "Classificacao" (tipo, descricao, status) 
            VALUES (%s, %s, 'ATIVO') RETURNING id
        """
        return self._execute_query(query, [tipo, descricao])

    def list_all(self):
        query = """
            SELECT id, descricao, tipo, status 
            FROM "Classificacao" ORDER BY descricao
        """
        return self._execute_query(query, fetch="all")

    def find_by_id(self, pk):
        query = """
            SELECT id, tipo, descricao 
            FROM "Classificacao" WHERE id = %s
        """
        return self._execute_query(query, [pk], fetch="one")

    def update(self, pk, tipo, descricao):
        query = """
            UPDATE "Classificacao" SET tipo=%s, descricao=%s WHERE id=%s
        """
        self._execute_query(query, [tipo, descricao, pk])

    def toggle_status(self, pk):
        query = """
            UPDATE "Classificacao" 
            SET status = CASE WHEN status = 'ATIVO' THEN 'INATIVO' ELSE 'ATIVO' END
            WHERE id = %s
        """
        self._execute_query(query, [pk])

    def list_active_receitas(self):
        query = """
            SELECT id, descricao FROM "Classificacao"
            WHERE tipo = 'RECEITA' AND status = 'ATIVO' ORDER BY descricao
        """
        return self._execute_query(query, fetch="all")
