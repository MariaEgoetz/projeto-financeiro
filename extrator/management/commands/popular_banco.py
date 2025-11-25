import random
from datetime import timedelta, date
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from extrator.models import Pessoas, Classificacao, MovimentoContas, ParcelasContas, MovimentoContasHasClassificacao

class Command(BaseCommand):
    help = 'Gera 200 registros falsos para teste de RAG e Interface'

    def handle(self, *args, **kwargs):
        self.stdout.write('Iniciando geração de dados...')
        faker = Faker('pt_BR') # Dados em Português

        try:
            with transaction.atomic():
                # 1. Classificações (10 itens)
                self.stdout.write('- Criando Classificações...')
                classificacoes = []
                lista = [
                    ('DESPESA', 'Insumos Agrícolas'), ('DESPESA', 'Manutenção'),
                    ('DESPESA', 'Energia Elétrica'), ('DESPESA', 'Folha de Pagamento'),
                    ('DESPESA', 'Impostos'), ('RECEITA', 'Venda de Soja'),
                    ('RECEITA', 'Venda de Milho'), ('RECEITA', 'Aluguel de Pasto'),
                    ('RECEITA', 'Serviços Prestados'), ('RECEITA', 'Investimentos')
                ]
                for tipo, desc in lista:
                    obj, _ = Classificacao.objects.get_or_create(descricao=desc, defaults={'tipo': tipo})
                    classificacoes.append(obj)

                # 2. Pessoas (30 registros)
                self.stdout.write('- Criando Pessoas...')
                pessoas = []
                for _ in range(30):
                    doc = faker.cnpj() if random.random() > 0.5 else faker.cpf()
                    # Evita duplicidade de documento
                    if not Pessoas.objects.filter(documento=doc).exists():
                        p = Pessoas.objects.create(
                            tipo=random.choice(['FORNECEDOR', 'CLIENTE', 'FATURADO']),
                            razaosocial=faker.company() if len(doc) > 14 else faker.name(),
                            documento=doc,
                            status='ATIVO'
                        )
                        pessoas.append(p)

                if not pessoas: 
                    self.stdout.write(self.style.ERROR('Erro: Nenhuma pessoa criada.'))
                    return

                # 3. Movimentos (160 registros)
                self.stdout.write('- Criando Movimentos...')
                for _ in range(160):
                    tipo = random.choice(['PAGAR', 'RECEBER'])
                    p1 = random.choice(pessoas)
                    p2 = random.choice(pessoas)
                    
                    mov = MovimentoContas.objects.create(
                        tipo=tipo,
                        numeronotafiscal=str(faker.random_number(digits=6)),
                        dataemissao=faker.date_between(start_date='-1y', end_date='today'),
                        descricao=faker.sentence(nb_words=6),
                        valortotal=round(random.uniform(100, 50000), 2),
                        status=random.choice(['PENDENTE', 'PAGO']),
                        fornecedor=p1,
                        faturado=p2
                    )
                    
                    # Vincula uma classificação
                    MovimentoContasHasClassificacao.objects.create(
                        movimentocontas=mov,
                        classificacao=random.choice(classificacoes)
                    )
                    
                    # Cria uma parcela única
                    ParcelasContas.objects.create(
                        movimento=mov,
                        identificacao="1/1",
                        datavencimento=mov.dataemissao + timedelta(days=30),
                        valorparcela=mov.valortotal,
                        valorsaldo=mov.valortotal,
                        statusparcela='PENDENTE'
                    )

            self.stdout.write(self.style.SUCCESS('Sucesso! 200 registros criados.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro: {str(e)}'))