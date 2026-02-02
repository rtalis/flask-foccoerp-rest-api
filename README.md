# Flask FoccoERP REST API

![Search Feature](frontend/public/search.png)

Este projeto é uma API REST desenvolvida com Flask que permite o recebimento de arquivos XML exportados do foccoERP e armazena os dados em um banco de dados PostgreSQL. A API é projetada para gerenciar ordens de compra e itens associados, utilizando SQLAlchemy para a manipulação do banco de dados e Marshmallow para a validação dos dados. Com o frontend, existem diversas opções que farão a busca pelos dados disponíveis mais fáceis. 

## Estrutura do Projeto

```
flask-foccoerp-rest-api/
├── app/                      # Código principal da aplicação Flask
│   ├── __init__.py          # Inicializa a aplicação Flask e configura o banco de dados
│   ├── models.py            # Define os modelos de dados para purchase_orders e purchase_items
│   ├── schemas.py           # Define os esquemas de validação para os dados
│   ├── timer.py             # Gerenciamento de timers
│   ├── utils.py             # Funções utilitárias para processar arquivos XML
│   ├── routes/              # Rotas da API
│   │   ├── auth.py          # Rotas de autenticação
│   │   └── routes.py        # Rotas principais da API
│   └── tasks/               # Tarefas assíncronas
│       ├── sync_nfe.py      # Sincronização de NFEs
│       └── match_purchases_nfe.py  # Correspondência de compras com NFEs
├── frontend/                # Aplicação React
│   ├── src/                 # Código-fonte da aplicação
│   │   ├── components/      # Componentes React
│   │   ├── utils/           # Funções utilitárias
│   │   ├── assets/          # Recursos estáticos
│   │   └── App.js           # Componente principal
│   ├── public/              # Arquivos públicos
│   │   └── search.png       # Imagem da interface de busca
│   └── package.json         # Dependências do frontend
├── migrations/              # Arquivos de migração gerados pelo Alembic
├── tests/                   # Testes da aplicação
│   ├── __init__.py
│   └── test_routes.py       # Testes para as rotas da API
├── config.py                # Configurações da aplicação
├── main.py                  # Ponto de entrada da aplicação
├── docker-compose.yml       # Define os serviços necessários para executar a aplicação
├── requirements.txt         # Dependências do projeto Python
└── README.md                # Este arquivo
```

## Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/rtalis/flask-foccoerp-rest-api.git
   cd flask-foccoerp-rest-api
   ```

2. Crie um ambiente virtual e ative-o:
   ```
   python -m venv env
   source env/bin/activate  # Para Linux/Mac
   env\Scripts\activate     # Para Windows
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
