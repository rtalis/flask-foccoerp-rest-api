import pytest
from io import BytesIO
from datetime import date
from flask import Flask
from flask.testing import FlaskClient
from app import create_app, db
from app.models import PurchaseOrder, PurchaseItem, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        # Criar usuário de teste
        test_user = User(
            username='test',
            email='test@example.com',
            password=generate_password_hash('test123')
        )
        db.session.add(test_user)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()

@pytest.fixture
def auth_client(client: FlaskClient) -> FlaskClient:
    client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'test123'
    })
    return client

def test_login(client: FlaskClient):
    response = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'test123'
    })
    assert response.status_code == 200
    assert b'Logged in successfully' in response.data

def test_protected_route_without_auth(client: FlaskClient):
    response = client.get('/api/purchases')
    assert response.status_code in (302, 401)

def test_import_xml(auth_client: FlaskClient):
    data = {
        'file': (BytesIO(b'<RCOT0300></RCOT0300>'), 'test_data.xml')
    }
    response = auth_client.post('/api/import', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    assert b'Data imported successfully' in response.data

def test_get_purchases(auth_client: FlaskClient):
    response = auth_client.get('/api/purchases')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_count_results(auth_client: FlaskClient):
    response = auth_client.get('/api/count_results', query_string={
        'query': 'test',
        'score_cutoff': 100,
        'searchByCodPedc': True,
        'searchByFornecedor': True,
        'searchByObservacao': True,
        'searchByItemId': True,
        'searchByDescricao': True,
        'selectedFuncName': 'todos'
    })
    assert response.status_code == 200
    assert 'count' in response.json
    assert 'estimated_pages' in response.json

def test_search_combined(auth_client: FlaskClient):
    response = auth_client.get('/api/search_combined', query_string={
        'query': 'test',
        'page': 1,
        'per_page': 10,
        'score_cutoff': 100,
        'searchByCodPedc': True,
        'searchByFornecedor': True,
        'searchByObservacao': True,
        'searchByItemId': True,
        'searchByDescricao': True,
        'selectedFuncName': 'todos'
    })
    assert response.status_code == 200
    assert 'purchases' in response.json
    assert 'total_pages' in response.json
    assert 'current_page' in response.json

def test_get_last_update(auth_client: FlaskClient):
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='LU-001',
            dt_emis=date(2024, 3, 1),
            fornecedor_id=1,
            fornecedor_descricao='Fornecedor Teste'
        )
        db.session.add(order)
        db.session.commit()

    response = auth_client.get('/api/last_update')
    assert response.status_code == 200

def test_get_purchasers(auth_client: FlaskClient):
    response = auth_client.get('/api/purchasers')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_get_item_details(auth_client: FlaskClient):
    # Primeiro, criar um item para testar
    order = PurchaseOrder(
        cod_pedc='TEST123',
        dt_emis=date(2024, 3, 19),
        fornecedor_id=1,
        fornecedor_descricao='Test Supplier'
    )
    db.session.add(order)
    db.session.flush()

    item = PurchaseItem(
        purchase_order_id=order.id,
        item_id='ITEM123',
        dt_emis=date(2024, 3, 19),
        cod_pedc='TEST123',
        descricao='Test Item',
        quantidade=1,
        preco_unitario=100,
        total=100
    )
    db.session.add(item)
    db.session.commit()

    response = auth_client.get(f'/api/item_details/{item.id}')
    assert response.status_code == 200
    assert 'item' in response.json
    assert 'priceHistory' in response.json

def test_logout(auth_client: FlaskClient):
    response = auth_client.post('/auth/logout')
    assert response.status_code == 200
    assert b'Logged out successfully' in response.data


def test_search_advanced_requires_query(auth_client: FlaskClient):
    response = auth_client.get('/api/search_advanced')
    assert response.status_code == 400


def test_search_advanced_multiterm(auth_client: FlaskClient):
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='PO-900',
            dt_emis=date(2024, 1, 5),
            fornecedor_id=42,
            fornecedor_descricao='Fornecedor Motor LTDA',
            observacao='Pedido urgente'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='MTR-123',
            dt_emis=date(2024, 1, 5),
            cod_pedc='PO-900',
            descricao='Motor industrial 123 fases',
            quantidade=2,
            preco_unitario=5000,
            total=10000
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'motor 123',
        'fields': 'descricao,cod_pedc',
        'per_page': 5
    })

    assert response.status_code == 200
    assert 'purchases' in response.json
    assert response.json['purchases']
    assert response.json['purchases'][0]['order']['cod_pedc'] == 'PO-900'


def test_search_advanced_suggestions(auth_client: FlaskClient):
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='PO-901',
            dt_emis=date(2024, 2, 10),
            fornecedor_id=43,
            fornecedor_descricao='Motores Brasil'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='MTR-999',
            dt_emis=date(2024, 2, 10),
            cod_pedc='PO-901',
            descricao='Motor elétrico trifásico',
            quantidade=1,
            preco_unitario=7000,
            total=7000
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/search_advanced/suggestions', query_string={'term': 'motor'})
    assert response.status_code == 200
    assert 'suggestions' in response.json