from django import forms
from django.forms import inlineformset_factory
from .models import Pessoas, Classificacao, MovimentoContas, ParcelasContas


class PessoaForm(forms.ModelForm):
    class Meta:
        model = Pessoas
        fields = ['tipo', 'razaosocial', 'fantasia', 'documento']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'razaosocial': forms.TextInput(attrs={'class': 'form-control'}),
            'fantasia': forms.TextInput(attrs={'class': 'form-control'}),
            'documento': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ClassificacaoForm(forms.ModelForm):
    class Meta:
        model = Classificacao
        fields = ['tipo', 'descricao']
        widgets = {
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
        }


class MovimentoReceberForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fornecedor'].queryset = Pessoas.objects.filter(tipo='CLIENTE', status='ATIVO')
        self.fields['fornecedor'].label = 'Cliente'
        self.fields['classificacoes'].queryset = Classificacao.objects.filter(tipo='RECEITA', status='ATIVO')
        self.fields['classificacoes'].widget = forms.SelectMultiple(attrs={'class': 'form-control'})

    class Meta:
        model = MovimentoContas
        fields = ['fornecedor', 'numeronotafiscal', 'dataemissao', 'descricao', 'classificacoes']
        widgets = {
            'fornecedor': forms.Select(attrs={'class': 'form-control'}),
            'numeronotafiscal': forms.TextInput(attrs={'class': 'form-control'}),
            'dataemissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ParcelaForm(forms.ModelForm):
    class Meta:
        model = ParcelasContas
        fields = ['identificacao', 'datavencimento', 'valorparcela']
        widgets = {
            'identificacao': forms.TextInput(attrs={'class': 'form-control'}),
            'datavencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valorparcela': forms.NumberInput(attrs={'class': 'form-control'}),
        }


ParcelasReceberFormSet = inlineformset_factory(
    MovimentoContas,
    ParcelasContas,
    form=ParcelaForm,
    extra=1,
    can_delete=True
)
