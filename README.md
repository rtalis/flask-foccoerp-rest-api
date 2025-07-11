# Flask REST API

Este projeto é uma API REST desenvolvida com Flask que permite o recebimento de arquivos XML exportados do foccoERP e armazena os dados em um banco de dados PostgreSQL. A API é projetada para gerenciar ordens de compra e itens associados, utilizando SQLAlchemy para a manipulação do banco de dados e Marshmallow para a validação dos dados. Com o frontend, existem diversas opções que farão a busca pelos dados disponíveis mais fáceis. 

## Estrutura do Projeto

```
flask-rest-api
├── app
│   ├── __init__.py          # Inicializa a aplicação Flask e configura o banco de dados
│   ├── models.py            # Define os modelos de dados para purchase_orders e purchase_items
│   ├── routes.py            # Contém as rotas da API
│   ├── schemas.py           # Define os esquemas de validação para os dados
│   └── utils.py             # Funções utilitárias para processar arquivos XML
├── migrations                # Arquivos de migração gerados pelo Alembic
├── tests
│   ├── __init__.py          # Inicializa o pacote de testes
│   ├── test_routes.py       # Testes para as rotas da API
│   └── test_models.py       # Testes para os modelos de dados
├── .env                      # Variáveis de ambiente
├── .gitignore                # Arquivos e diretórios a serem ignorados pelo Git
├── config.py                # Configurações da aplicação
├── Dockerfile                # Instruções para construir a imagem Docker
├── docker-compose.yml        # Define os serviços necessários para executar a aplicação
└── requirements.txt          # Dependências do projeto
```

## Instalação

1. Clone o repositório:
   ```
   git clone <URL_DO_REPOSITORIO>
   cd flask-rest-api
   ```

2. Crie um ambiente virtual e ative-o:
   ```
   python -m venv venv
   source venv/bin/activate  # Para Linux/Mac
   venv\Scripts\activate     # Para Windows
   ```

3. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

4. Configure as variáveis de ambiente no arquivo `.env`, pode utilizar como base o arquivo .env.example.

5. Execute as migrações do banco de dados:
   ```
   flask db upgrade
   ```

6. Inicie a aplicação:
   ```
   flask run
   ```

## Uso

A API possui um endpoint para receber arquivos XML. Os dados contidos no arquivo serão processados e armazenados nas tabelas correspondentes no banco de dados.

## Contribuição

Contribuições são bem-vindas! Sinta-se à vontade para abrir um pull request ou relatar problemas.

## Licença

Este projeto está licenciado sob a MIT License. Veja o arquivo LICENSE para mais detalhes.