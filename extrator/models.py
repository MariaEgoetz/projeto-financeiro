from django.db import models


class Pessoas(models.Model):
    TIPO_PESSOA_CHOICES = [('FORNECEDOR', 'Fornecedor'), ('CLIENTE', 'Cliente'), ('FATURADO', 'Faturado')]
    tipo = models.CharField(max_length=45, choices=TIPO_PESSOA_CHOICES)
    razaosocial = models.CharField(max_length=150)
    fantasia = models.CharField(max_length=150, null=True, blank=True)
    documento = models.CharField(max_length=45, unique=True)
    status = models.CharField(max_length=45, default='ATIVO')

    class Meta:
        db_table = 'Pessoas'


class Classificacao(models.Model):
    TIPO_CLASSIFICACAO_CHOICES = [('DESPESA', 'Despesa'), ('RECEITA', 'Receita')]
    tipo = models.CharField(max_length=45, choices=TIPO_CLASSIFICACAO_CHOICES)
    descricao = models.CharField(max_length=150, unique=True)
    status = models.CharField(max_length=45, default='ATIVO')

    class Meta:
        db_table = 'Classificacao'


class MovimentoContas(models.Model):
    TIPO_MOVIMENTO_CHOICES = [('PAGAR', 'A Pagar'), ('RECEBER', 'A Receber')]
    tipo = models.CharField(max_length=45, choices=TIPO_MOVIMENTO_CHOICES)
    numeronotafiscal = models.CharField(max_length=45)
    dataemissao = models.DateField()
    descricao = models.CharField(max_length=300, null=True, blank=True)
    valortotal = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=45, default='PENDENTE')
    fornecedor = models.ForeignKey(Pessoas, on_delete=models.PROTECT, related_name='movimentos_fornecedor', db_column='Pessoas_idFornecedorCliente')
    faturado = models.ForeignKey(Pessoas, on_delete=models.PROTECT, related_name='movimentos_faturado', db_column='Pessoas_idFaturado')
    classificacoes = models.ManyToManyField(Classificacao, through='MovimentoContasHasClassificacao')

    class Meta:
        db_table = 'MovimentoContas'


class ParcelasContas(models.Model):
    movimento = models.ForeignKey(MovimentoContas, on_delete=models.CASCADE, related_name='parcelas', db_column='MovimentoContas_idMovimentoContas')
    identificacao = models.CharField(max_length=45)
    datavencimento = models.DateField()
    valorparcela = models.DecimalField(max_digits=10, decimal_places=2)
    valorpago = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    valorsaldo = models.DecimalField(max_digits=10, decimal_places=2)
    statusparcela = models.CharField(max_length=45, default='PENDENTE')

    class Meta:
        db_table = 'ParcelasContas'


class MovimentoContasHasClassificacao(models.Model):
    movimentocontas = models.ForeignKey(MovimentoContas, on_delete=models.CASCADE, db_column='MovimentoContas_idMovimentoContas')
    classificacao = models.ForeignKey(Classificacao, on_delete=models.CASCADE, db_column='Classificacao_idClassificacao')

    class Meta:
        db_table = 'MovimentoContas_has_Classificacao'
        unique_together = (('movimentocontas', 'classificacao'),)
