# Extrator e Analisador de Notas Fiscais com IA

Este projeto é uma aplicação web completa que utiliza uma arquitetura de múltiplos agentes de IA para extrair, analisar e registrar dados de Notas Fiscais Eletrônicas (NF-e) em formato PDF. O sistema foi desenhado utilizando o padrão de projeto *Repository* para garantir um código limpo, seguro e de fácil manutenção.

## Arquitetura e Fluxo de Trabalho

O processo é orquestrado em um fluxo de trabalho inteligente e automatizado:

1.  **Upload e Extração (Agente 1 - Google Gemini):** O usuário faz o upload de um arquivo PDF. O primeiro agente, utilizando a API do Google Gemini, lê o documento, interpreta seu conteúdo e extrai as informações essenciais, estruturando-as em um formato JSON limpo e previsível.

2.  **Análise de Risco (Agente 2 - OpenAI):** O JSON extraído é imediatamente passado para o segundo agente, que atua como um auditor de IA. Utilizando a API da OpenAI, ele realiza uma análise de risco completa, procurando por:
    * **Inconsistências de Categoria:** Verifica se os produtos comprados condizem com a categoria da despesa (ex: "Pneus" não podem ser "Insumos de Escritório").
    * **Análise de Preços:** Compara os valores da nota com estimativas de mercado para sinalizar possíveis sobrepreços.
    * **Padrões Suspeitos:** Busca por anomalias que possam indicar fraudes, como valores "redondos" ou combinações incomuns de fornecedor e produto.

3.  **Validação e Decisão do Usuário:** A aplicação exibe os dados extraídos, o parecer do analista de risco (com uma nota de 0 a 10 e alertas claros) e uma validação de pré-cadastro no banco de dados. O usuário tem total visibilidade para decidir se aprova o lançamento.

4.  **Persistência (Camada de Repositório):** Após a confirmação do usuário, a aplicação aciona a camada de Repositório, que encapsula toda a comunicação com o banco de dados PostgreSQL. Utilizando queries parametrizadas, ela realiza o cadastro seguro das informações, garantindo a integridade dos dados.

## Tecnologias e Padrões

* **Backend:** Python 3.13, Django 5.2.7
* **Padrão de Arquitetura:** Repository Pattern
* **Banco de Dados:** PostgreSQL 15
* **Gerenciador de Interface de DB:** pgAdmin 4
* **Inteligência Artificial:** Google Gemini API, OpenAI API
* **Manipulação de PDF:** PyMuPDF (`fitz`)
* **Containerização:** Docker e Docker Compose

---

## Como Iniciar com Docker

Este projeto é totalmente containerizado, garantindo um ambiente de desenvolvimento rápido, consistente e isolado. Siga os passos abaixo para rodar a aplicação completa (Django, PostgreSQL e pgAdmin).

### Pré-requisitos

[Docker](https://www.docker.com/products/docker-desktop/) instalado e em execução na sua máquina.

### 1. Clone o Repositório

```bash
git clone https://github.com/Enildo-Martins/projeto_financeiro.git
cd projeto-financeiro
```

### 2. Configure as Variáveis de Ambiente

Crie uma cópia do arquivo de exemplo .env.example e renomeie-a para .env.

```bash
# No Windows (usando PowerShell ou cmd)
copy .env.example .env

# No macOS/Linux
cp .env.example .env
Agora, abra o arquivo .env e preencha com suas chaves de API e as configurações desejadas para o banco de dados e pgAdmin. Não é necessário alterar os valores de DB_ e PGADMIN_ se você não tiver preferência.

# .env
# Chaves das APIs
GEMINI_API_KEY=SUA_CHAVE_GEMINI_AQUI
OPENAI_API_KEY=SUA_CHAVE_OPENAI_AQUI

# Configurações do Banco de Dados PostgreSQL
DB_NAME=financeiro_db
DB_USER=admin
DB_PASSWORD=secret
DB_HOST=db
DB_PORT=5432

# Configurações do pgAdmin
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin
```

### 3. Construa e Inicie os Containers

Este único comando irá construir a imagem da sua aplicação Django, baixar as imagens do PostgreSQL e do pgAdmin, e iniciar todos os serviços em segundo plano.

```bash
docker-compose up --build -d
```

### 4. Execute as Migrações do Banco de Dados
Com os containers rodando, execute os seguintes comandos para criar as tabelas do projeto no banco de dados PostgreSQL pela primeira vez.

```bash
docker-compose exec web python manage.py makemigrations extrator

docker-compose exec web python manage.py migrate
```

### 5. Acesse os Serviços
Pronto! Seu ambiente completo está no ar.

* Aplicação Django: http://localhost:8000

* pgAdmin (Interface do Banco): http://localhost:5050

  * Login: admin@admin.com
  * Senha: admin

Ao acessar o pgAdmin, um servidor para o seu banco de dados já estará pré-configurado. Basta inserir a senha do banco (secret, conforme o .env) para se conectar e visualizar as tabelas.
