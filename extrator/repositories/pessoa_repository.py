from .base_repository import BaseRepository


class PessoaRepository(BaseRepository):

    def find_by_documento(self, documento):
        query = """SELECT id FROM "Pessoas" WHERE documento = %s"""
        result = self._execute_query(query, [documento], fetch="one")
        return result[0] if result else None

    def create(self, tipo, detail):
        query = """
            INSERT INTO "Pessoas" (tipo, razaosocial, fantasia, documento, status)
            VALUES (%s, %s, %s, %s, 'ATIVO') RETURNING id
        """
        params = [
            tipo,
            detail.get('razaosocial') or detail.get('razao_social') or detail.get('nome_completo'),
            detail.get('fantasia'),
            detail.get('documento') or detail.get('cnpj') or detail.get('cpf/cnpj')
        ]
        return self._execute_query(query, params)

    def list_all(self):
        query = """
            SELECT id, razaosocial, documento, tipo, status 
            FROM "Pessoas" ORDER BY razaosocial
        """
        return self._execute_query(query, fetch="all")

    def find_by_id(self, pk):
        query = """
            SELECT id, tipo, razaosocial, fantasia, documento 
            FROM "Pessoas" WHERE id = %s
        """
        return self._execute_query(query, [pk], fetch="one")

    def update(self, pk, tipo, razaosocial, fantasia, documento):
        query = """
            UPDATE "Pessoas" SET tipo=%s, razaosocial=%s, fantasia=%s, documento=%s
            WHERE id=%s
        """
        params = [tipo, razaosocial, fantasia, documento, pk]
        self._execute_query(query, params)

    def toggle_status(self, pk):
        query = """
            UPDATE "Pessoas" 
            SET status = CASE WHEN status = 'ATIVO' THEN 'INATIVO' ELSE 'ATIVO' END
            WHERE id = %s
        """
        self._execute_query(query, [pk])

    def list_active_clients(self):
        query = """
            SELECT id, razaosocial FROM "Pessoas" 
            WHERE tipo = 'CLIENTE' AND status = 'ATIVO' ORDER BY razaosocial
        """
        return self._execute_query(query, fetch="all")
