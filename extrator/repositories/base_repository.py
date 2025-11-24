from django.db import connection

class BaseRepository:

    def _execute_query(self, query, params=None, fetch=None):
        with connection.cursor() as cursor:
            cursor.execute(query, params or [])
            if fetch == 'one':
                return cursor.fetchone()
            if fetch == 'all':
                return cursor.fetchall()
            if 'RETURNING' in query.upper():
                return cursor.fetchone()[0] if cursor.rowcount > 0 else None
            return None

    def _get_ilike_operator(self):
        """
        Retorna 'ILIKE' para PostgreSQL e 'LIKE' para SQLite.
        Garante compatibilidade entre ambientes.
        """
        if connection.vendor == 'postgresql':
            return 'ILIKE'
        return 'LIKE'