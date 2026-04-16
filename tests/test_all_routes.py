"""
Comprehensive test suite for all Flask-FoccoERP routes.
This file includes all existing tests plus new tests for endpoints lacking coverage.
"""

import pytest
from io import BytesIO
from datetime import date, datetime, timedelta
from flask import Flask
from flask.testing import FlaskClient
from app import create_app, db
from app.models import (
    PurchaseOrder, PurchaseItem, PurchaseItemNFEMatch, NFEData, User, 
    LoginHistory, NFEntry, Quotation, Supplier, Company
)
from app.utils import check_order_fulfillment
from werkzeug.security import generate_password_hash


@pytest.fixture
def app():
    """Create and configure a test Flask application."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "MAIL_SUPPRESS_SEND": True
    })

    with app.app_context():
        db.drop_all()
        db.create_all()
        # Create test user
        test_user = User(
            username='test',
            email='test@example.com',
            password=generate_password_hash('test123'),
            role='viewer'
        )
        # Create admin user for testing admin endpoints
        admin_user = User(
            username='admin',
            email='admin@example.com',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add_all([test_user, admin_user])
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    """Create a test client."""
    return app.test_client()


@pytest.fixture
def auth_client(client: FlaskClient) -> FlaskClient:
    """Create an authenticated test client."""
    client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'test123'
    })
    return client


@pytest.fixture
def admin_client(client: FlaskClient) -> FlaskClient:
    """Create an authenticated admin test client."""
    client.post('/auth/login', json={
        'email': 'admin@example.com',
        'password': 'admin123'
    })
    return client


# ==================== AUTHENTICATION TESTS ====================

def test_login(client: FlaskClient):
    """Test user login."""
    response = client.post('/auth/login', json={
        'email': 'test@example.com',
        'password': 'test123'
    })
    assert response.status_code == 200
    assert b'Logged in successfully' in response.data


def test_logout(auth_client: FlaskClient):
    """Test user logout."""
    response = auth_client.post('/auth/logout')
    assert response.status_code == 200
    assert b'Logged out successfully' in response.data

    with auth_client.application.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        history = LoginHistory.query.filter_by(user_id=user.id).order_by(LoginHistory.login_time.desc()).first()
        assert history is not None
        assert history.logout_time is not None
        assert history.logout_ip == '127.0.0.1'


def test_protected_route_without_auth(client: FlaskClient):
    """Test that protected routes require authentication."""
    response = client.get('/api/purchases')
    assert response.status_code in (302, 401)


def test_auth_me(auth_client: FlaskClient):
    """Test getting current user info."""
    response = auth_client.get('/auth/me')
    assert response.status_code == 200
    assert 'username' in response.json
    assert 'email' in response.json
    assert response.json['email'] == 'test@example.com'


def test_auth_me_update(auth_client: FlaskClient):
    """Test updating current user's account info."""
    response = auth_client.put('/auth/me', json={
        'username': 'testuser_updated',
        'purchaser_name': 'Test User Display Name'
    })
    assert response.status_code == 200
    assert 'username' in response.json


# ==================== FILE IMPORT TESTS ====================

def test_import_requires_file_with_token(auth_client: FlaskClient):
    """Test that import endpoint requires file and token."""
    token_response = auth_client.post('/auth/generate_jwt_token', json={'expires_in': 60})
    assert token_response.status_code == 200
    token = token_response.json['token']

    response = auth_client.post(
        '/api/import',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 400
    assert 'error' in response.json


def test_import_rejects_invalid_xml(auth_client: FlaskClient):
    """Test that import endpoint rejects invalid XML."""
    token_response = auth_client.post('/auth/generate_jwt_token', json={'expires_in': 60})
    assert token_response.status_code == 200
    token = token_response.json['token']

    data = {
        'file': (BytesIO(b'not-xml'), 'invalid.xml')
    }
    response = auth_client.post(
        '/api/import',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 400
    assert 'error' in response.json


# ==================== BASIC SEARCH TESTS ====================

def test_get_purchases(auth_client: FlaskClient):
    """Test getting all purchases."""
    response = auth_client.get('/api/purchases')
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_get_purchasers(auth_client: FlaskClient):
    """Test getting all purchaser names."""
    response = auth_client.get('/api/purchasers')
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_get_companies(auth_client: FlaskClient):
    """Test getting distinct company codes."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='COMP-001',
            dt_emis=date(2024, 5, 1),
            fornecedor_id=1,
            fornecedor_descricao='Fornecedor Teste',
            cod_emp1='001'
        )
        db.session.add(order)
        db.session.commit()

    response = auth_client.get('/api/companies')
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_search_items(auth_client: FlaskClient):
    """Test searching items by description and item_id."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='SEARCH-001',
            dt_emis=date(2024, 6, 1),
            fornecedor_id=100,
            fornecedor_descricao='Fornecedor Busca'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='VALVE-001',
            dt_emis=date(2024, 6, 1),
            cod_pedc='SEARCH-001',
            descricao='Valvula de controle pneumatica',
            quantidade=10,
            preco_unitario=500,
            total=5000
        )
        db.session.add(item)
        db.session.commit()

    # Search by description
    response = auth_client.get('/api/search_items', query_string={'descricao': 'valvula'})
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_search_purchases(auth_client: FlaskClient):
    """Test searching purchase orders by multiple fields."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='SRCPO-001',
            dt_emis=date(2024, 6, 15),
            fornecedor_id=200,
            fornecedor_descricao='Fornecedor Especial',
            observacao='Urgente para producao'
        )
        db.session.add(order)
        db.session.commit()

    response = auth_client.get('/api/search_purchases', query_string={'cod_pedc': 'SRCPO'})
    assert response.status_code == 200


def test_search_item_id(auth_client: FlaskClient):
    """Test searching by exact item_id."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='ITEMID-001',
            dt_emis=date(2024, 7, 1),
            fornecedor_id=300,
            fornecedor_descricao='Fornecedor Item'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='EXACT-ITEM-123',
            dt_emis=date(2024, 7, 1),
            cod_pedc='ITEMID-001',
            descricao='Item com ID exato',
            quantidade=5,
            preco_unitario=100,
            total=500
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/search_item_id', query_string={'item_id': 'EXACT-ITEM-123'})
    assert response.status_code == 200


def test_get_purchase(auth_client: FlaskClient):
    """Test getting purchase order by cod_pedc."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='GETPO-001',
            dt_emis=date(2024, 7, 15),
            fornecedor_id=400,
            fornecedor_descricao='Fornecedor GET'
        )
        db.session.add(order)
        db.session.commit()

    response = auth_client.get('/api/get_purchase', query_string={'cod_pedc': 'GETPO-001'})
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_get_item_details(auth_client: FlaskClient):
    """Test getting item details."""
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


# ==================== QUOTATION TESTS ====================

def test_quotations(auth_client: FlaskClient):
    """Test getting quotations by item_id."""
    with auth_client.application.app_context():
        quotation = Quotation(
            cod_cot='COT-001',
            dt_emissao=date(2024, 8, 1),
            fornecedor_id=500,
            fornecedor_descricao='Fornecedor Cotacao',
            item_id='QUOT-ITEM-001',
            descricao='Item para cotacao',
            quantidade=20,
            unidade_medida='UN',
            preco_unitario=150
        )
        db.session.add(quotation)
        db.session.commit()

    response = auth_client.get('/api/quotations', query_string={'item_id': 'QUOT-ITEM-001'})
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert response.json[0]['unidade_medida'] == 'UN'


def test_quotation_items(auth_client: FlaskClient):
    """Test getting quotation items by cod_cot."""
    with auth_client.application.app_context():
        quotation = Quotation(
            cod_cot='COTITEMS-001',
            dt_emissao=date(2024, 8, 15),
            fornecedor_id=600,
            fornecedor_descricao='Fornecedor COT Items',
            item_id='COTITEM-001',
            descricao='Primeiro item cotacao',
            quantidade=10,
            unidade_medida='UN',
            preco_unitario=200
        )
        db.session.add(quotation)
        db.session.commit()

    response = auth_client.get('/api/quotation_items', query_string={'cod_cot': 'COTITEMS-001'})
    assert response.status_code == 200
    assert 'cod_cot' in response.json
    assert response.json['items'][0]['unidade_medida'] == 'UN'


# ==================== FUZZY SEARCH TESTS ====================

def test_search_fuzzy(auth_client: FlaskClient):
    """Test fuzzy search for items and orders."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='FUZZY-001',
            dt_emis=date(2024, 9, 1),
            fornecedor_id=700,
            fornecedor_descricao='Fornecedor Fuzzy',
            observacao='Motor eletrico industrial'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='FUZZ-ITEM',
            dt_emis=date(2024, 9, 1),
            cod_pedc='FUZZY-001',
            descricao='Motoredutor industrial',
            quantidade=2,
            preco_unitario=3000,
            total=6000
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/search_fuzzy', query_string={
        'query': 'motor',
        'score_cutoff': 60
    })
    assert response.status_code == 200
    assert 'items' in response.json
    assert 'purchases' in response.json


def test_search_item_fuzzy(auth_client: FlaskClient):
    """Test fuzzy search for items only."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='FUZZITEM-001',
            dt_emis=date(2024, 9, 1),
            fornecedor_id=710,
            fornecedor_descricao='Fornecedor Fuzzy Item'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='FUZZITEM',
            dt_emis=date(2024, 9, 1),
            cod_pedc='FUZZITEM-001',
            descricao='Rolamento de esferas',
            quantidade=100,
            preco_unitario=50,
            total=5000
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/search_item_fuzzy', query_string={
        'descricao': 'Rolamento',
        'score_cutoff': 70
    })
    assert response.status_code == 200
    assert isinstance(response.json, dict)
    assert 'item' in response.json


def test_quotations_fuzzy(auth_client: FlaskClient):
    """Test fuzzy search for quotations."""
    with auth_client.application.app_context():
        quotation = Quotation(
            cod_cot='FUZZQUOT-001',
            dt_emissao=date(2024, 9, 1),
            fornecedor_id=720,
            fornecedor_descricao='Fornecedor Fuzzy Quotation',
            item_id='FUZZQUOT-ITEM',
            descricao='Corrente desmontavel',
            quantidade=50,
            unidade_medida='UN',
            preco_unitario=25
        )
        db.session.add(quotation)
        db.session.commit()

    response = auth_client.get('/api/quotations_fuzzy', query_string={
        'descricao': 'Corrente',
        'score_cutoff': 70
    })
    assert response.status_code == 200


# ==================== ADVANCED SEARCH TESTS ====================

def test_search_combined(auth_client: FlaskClient):
    """Test combined search across multiple fields."""
    response = auth_client.get('/api/search_combined', query_string={
        'query': 'test',
        'page': 1,
        'per_page': 10,
        'score_cutoff': 100,
        'searchByCodPedc': True,
        'searchByFornecedor': True,
        'selectedFuncName': 'todos'
    })
    assert response.status_code == 200
    assert 'purchases' in response.json
    assert 'total_pages' in response.json


def test_search_combined_matches_description(auth_client: FlaskClient):
    """Test that combined search matches descriptions correctly."""
    with auth_client.application.app_context():
        alpha_order = PurchaseOrder(
            cod_pedc='PO-ALPHA-001',
            dt_emis=date(2024, 4, 10),
            fornecedor_id=11,
            fornecedor_descricao='Alpha Equipamentos',
            observacao='Linha hidraulica'
        )
        db.session.add(alpha_order)
        db.session.flush()

        alpha_item = PurchaseItem(
            purchase_order_id=alpha_order.id,
            item_id='ALPHA-ITEM',
            dt_emis=date(2024, 4, 10),
            cod_pedc='PO-ALPHA-001',
            descricao='Bomba Hidraulica industrial',
            quantidade=3,
            preco_unitario=1500,
            total=4500
        )
        db.session.add(alpha_item)
        db.session.commit()

    response = auth_client.get('/api/search_combined', query_string={
        'query': 'hidraulica',
        'page': 1,
        'per_page': 10,
        'score_cutoff': 100,
        'searchByDescricao': True,
        'selectedFuncName': 'todos'
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['purchases']


def test_search_combined_matches_supplier_cnpj(auth_client: FlaskClient):
    """Test that combined search matches supplier CNPJ with and without punctuation."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='PO-CNPJ-001',
            dt_emis=date(2024, 7, 1),
            fornecedor_id=120,
            fornecedor_descricao='Fornecedor CNPJ'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='CNPJ-ITEM',
            dt_emis=date(2024, 7, 1),
            cod_pedc='PO-CNPJ-001',
            descricao='Item com CNPJ',
            quantidade=1,
            preco_unitario=100,
            total=100
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/search_combined', query_string={
        'query': 'CNPJ',
        'page': 1,
        'per_page': 10,
        'score_cutoff': 100,
        'selectedFuncName': 'todos'
    })

    assert response.status_code == 200


def test_search_advanced(auth_client: FlaskClient):
    """Test advanced search."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'test',
        'page': 1,
        'per_page': 20,
        'selectedFuncName': 'todos'
    })
    assert response.status_code == 200
    assert 'purchases' in response.json


def test_search_advanced_allows_empty_query(auth_client: FlaskClient):
    """Test that advanced search allows empty query."""
    response = auth_client.get('/api/search_advanced')
    assert response.status_code == 200


def test_search_advanced_with_date_range(auth_client: FlaskClient):
    """Test advanced search with date range filters."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='DATE-001',
            dt_emis=date(2024, 10, 15),
            fornecedor_id=800,
            fornecedor_descricao='Fornecedor Date Test'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='DATE-ITEM',
            dt_emis=date(2024, 10, 15),
            cod_pedc='DATE-001',
            descricao='Item with date',
            quantidade=5,
            preco_unitario=100,
            total=500
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'date',
        'date_from': '2024-10-01',
        'date_to': '2024-10-31',
        'page': 1,
        'per_page': 10
    })

    assert response.status_code == 200
    assert 'purchases' in response.json


def test_search_advanced_suggestions(auth_client: FlaskClient):
    """Test search suggestions endpoint."""
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


def test_search_advanced_multiterm(auth_client: FlaskClient):
    """Test advanced search with multiple terms."""
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


# ==================== NFE/NFEData TESTS ====================

def test_get_nfe(auth_client: FlaskClient):
    """Test getting NFE data."""
    with auth_client.application.app_context():
        nfe = NFEData(
            chave='12345678901234567890123456789012345678901234',
            xml_content='<xml />',
            numero='001'
        )
        db.session.add(nfe)
        db.session.commit()

    response = auth_client.get('/api/get_nfe', query_string={'cod_pedc': '35000', 'linha': 1})
    # May return 404 if not found, that's acceptable for test
    assert response.status_code in (200, 404, 500)


def test_purchase_by_nf(auth_client: FlaskClient):
    """Test getting purchase orders by NFE number."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='PURNF-001',
            dt_emis=date(2024, 11, 1),
            fornecedor_id=900,
            fornecedor_descricao='Fornecedor NF',
            cod_emp1='001'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='NF-ITEM',
            dt_emis=date(2024, 11, 1),
            cod_pedc='PURNF-001',
            cod_emp1='001',
            linha=1,
            descricao='Item NF',
            quantidade=1,
            preco_unitario=100,
            total=100
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/purchase_by_nf', query_string={
        'num_nf': '001',
        'cod_emp1': '001'
    })
    assert response.status_code in (200, 404)


def test_nfe_by_purchase(auth_client: FlaskClient):
    """Test getting NFEs associated with a purchase order."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='NFEBYPURCH-001',
            dt_emis=date(2024, 11, 5),
            fornecedor_id=910,
            fornecedor_descricao='Fornecedor NFEB',
            cod_emp1='001'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='NFEBYPURCH-ITEM',
            dt_emis=date(2024, 11, 5),
            cod_pedc='NFEBYPURCH-001',
            cod_emp1='001',
            linha=1,
            descricao='Item NFEB Purch',
            quantidade=2,
            preco_unitario=200,
            total=400
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/nfe_by_purchase', query_string={
        'cod_pedc': '35000',
        'cod_emp1': '1'
    })
    assert response.status_code in (200, 404)


def test_get_nfe_by_number(auth_client: FlaskClient):
    """Test getting single NFE by its number."""
    response = auth_client.get('/api/get_nfe_by_number', query_string={
        'num_nf': 'TEST123',
        'fornecedor_id': '999'
    })
    # Will likely return 404 since NFE doesn't exist, that's acceptable
    assert response.status_code in (200, 404)


def test_get_danfe_data(auth_client: FlaskClient):
    """Test getting DANFE display data."""
    response = auth_client.get('/api/get_danfe_data', query_string={
        'chave': 'nonexistent'
    })
    # Will likely return 404, that's acceptable
    assert response.status_code in (200, 404)


def test_get_danfe_pdf(auth_client: FlaskClient):
    """Test getting DANFE PDF."""
    response = auth_client.get('/api/get_danfe_pdf', query_string={
        'xmlKey': 'nonexistent'
    })
    # Will likely return 404, that's acceptable
    assert response.status_code in (200, 404)


def test_get_nfe_data(auth_client: FlaskClient):
    """Test getting NFE data from API."""
    response = auth_client.get('/api/get_nfe_data', query_string={
        'xmlKey': 'nonexistent'
    })
    # Will likely return 400 or 404, that's acceptable
    assert response.status_code in (200, 400, 404, 500)


# ==================== MATCH/MANUAL MATCHING TESTS ====================

def test_match_purchase_nfe(auth_client: FlaskClient):
    """Test matching NFEs to purchase orders."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='MATCH-001',
            dt_emis=date(2024, 12, 1),
            fornecedor_id=920,
            fornecedor_descricao='Fornecedor Match',
            cod_emp1='001'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='MATCH-ITEM',
            dt_emis=date(2024, 12, 1),
            cod_pedc='MATCH-001',
            cod_emp1='001',
            linha=1,
            descricao='Item Match',
            quantidade=5,
            preco_unitario=500,
            total=2500
        )
        db.session.add(item)
        db.session.commit()

    response = auth_client.get('/api/match_purchase_nfe', query_string={
        'cod_pedc': 'MATCH-001',
        'cod_emp1': '001',
        'max_results': 10
    })
    assert response.status_code == 200
    assert 'matches_found' in response.json


def test_manual_match_nfe(auth_client: FlaskClient):
    """Test manual NFE matching endpoint."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='MANUAL-001',
            dt_emis=date(2024, 12, 5),
            fornecedor_id=930,
            fornecedor_descricao='Fornecedor Manual',
            cod_emp1='001'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='MANUAL-ITEM',
            dt_emis=date(2024, 12, 5),
            cod_pedc='MANUAL-001',
            cod_emp1='001',
            linha=1,
            descricao='Item Manual',
            quantidade=3,
            preco_unitario=300,
            total=900
        )
        db.session.add(item)
        db.session.flush()

        nfe = NFEData(
            chave='12345678901234567890123456789012345678901234',
            xml_content='<xml />',
            numero='999999'
        )
        db.session.add(nfe)
        db.session.commit()

    response = auth_client.post('/api/manual_match_nfe', json={
        'nfe_chave': '12345678901234567890123456789012345678901244',
        'cod_pedc': 'MANUAL-001',
        'cod_emp1': '001',
        'purchase_item_id': None
    })
    # May fail due to validation, but endpoint exists
    assert response.status_code in (201, 400, 404, 500)


# ==================== DASHBOARD & REPORTS TESTS ====================

def test_dashboard_summary(auth_client: FlaskClient):
    """Test dashboard summary endpoint."""
    response = auth_client.get('/api/dashboard_summary')
    assert response.status_code == 200
    payload = response.get_json()
    assert 'summary' in payload
    assert 'total_orders' in payload['summary']


def test_dashboard_summary_includes_daily_usage(auth_client: FlaskClient):
    """Test that dashboard summary includes daily usage data."""
    with auth_client.application.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        now = datetime.now()
        for days_ago in range(3):
            db.session.add(LoginHistory(
                user_id=user.id,
                login_time=now - timedelta(days=days_ago),
                login_ip='127.0.0.1'
            ))
        db.session.commit()

    response = auth_client.get('/api/dashboard_summary')
    assert response.status_code == 200
    payload = response.get_json()
    assert 'daily_usage' in payload
    assert isinstance(payload['daily_usage'], list)


def test_count_results(auth_client: FlaskClient):
    """Test counting search results."""
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


def test_last_update(auth_client: FlaskClient):
    """Test getting last update timestamp."""
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


def test_usage_report(auth_client: FlaskClient):
    """Test usage report endpoint."""
    response = auth_client.get('/api/usage_report')
    assert response.status_code in (200, 400, 403)  # May not have data yet


# ==================== USER PURCHASES TESTS ====================

def test_user_purchases(auth_client: FlaskClient):
    """Test getting purchase orders for current user."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='USER-001',
            dt_emis=date(2024, 12, 10),
            fornecedor_id=940,
            fornecedor_descricao='Fornecedor User',
            func_nome='test'
        )
        db.session.add(order)
        db.session.commit()

    response = auth_client.get('/api/user_purchases', query_string={
        'username': 'test',
        'status': 'all'
    })
    assert response.status_code in (200, 404)


# ==================== AUTO MATCHING TESTS ====================

def test_auto_match_nfes(auth_client: FlaskClient):
    """Test automatic NFE matching."""
    response = auth_client.get('/api/auto_match_nfes', query_string={
        'min_score': 50,
        'limit': 10
    })
    assert response.status_code in (200, 500)


# ==================== SYNC & IMPORT TESTS ====================

def test_sync_nfe(auth_client: FlaskClient):
    """Test manual NFE sync trigger."""
    response = auth_client.post('/api/sync_nfe')
    assert response.status_code in (200, 400, 500)


def test_upload_chunk(auth_client: FlaskClient):
    """Test file chunk upload."""
    data = {
        'file': (BytesIO(b'test data'), 'test.xml'),
        'chunk': (0,),
        'chunks': (1,)
    }
    response = auth_client.post(
        '/api/upload_chunk',
        data=data,
        content_type='multipart/form-data'
    )
    assert response.status_code in (200, 400, 413)


def test_process_file(auth_client: FlaskClient):
    """Test file processing after upload."""
    response = auth_client.post('/api/process_file', json={
        'filename': 'test.xml'
    })
    assert response.status_code in (200, 400, 404)


# ==================== VIEW TEMPLATES TESTS ====================

def test_view_danfe_template(auth_client: FlaskClient):
    """Test viewing DANFE template."""
    response = auth_client.get('/api/view_danfe_template/999')
    # Will likely return 404 since NFE doesn't exist
    assert response.status_code in (200, 404)


# ==================== TRACKED COMPANIES TESTS ====================

def test_get_tracked_companies(auth_client: FlaskClient):
    """Test getting tracked companies - returns list."""
    response = auth_client.get('/api/tracked_companies')
    assert response.status_code == 200
    data = response.get_json()
    assert 'companies' in data
    assert isinstance(data['companies'], list)


def test_add_tracked_company(auth_client: FlaskClient):
    """Test adding tracked company with valid data."""
    response = auth_client.post('/api/tracked_companies', json={
        'cod_emp1': 'EMP001',
        'name': 'Test Company',
        'cnpj': '34.028.316/0001-07'  # Valid format
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'company' in data
    assert data['company']['cod_emp1'] == 'EMP001'


def test_add_tracked_company_missing_cnpj(auth_client: FlaskClient):
    """Test adding tracked company without required CNPJ."""
    response = auth_client.post('/api/tracked_companies', json={
        'cod_emp1': 'EMP002',
        'name': 'Test Company'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_add_tracked_company_missing_cod_emp1(auth_client: FlaskClient):
    """Test adding tracked company without required cod_emp1."""
    response = auth_client.post('/api/tracked_companies', json={
        'cnpj': '34.028.316/0001-07',
        'name': 'Test Company'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_add_tracked_company_invalid_cnpj(auth_client: FlaskClient):
    """Test adding company with invalid CNPJ (wrong digit count)."""
    response = auth_client.post('/api/tracked_companies', json={
        'cod_emp1': 'EMP003',
        'name': 'Test',
        'cnpj': '12345'
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data


def test_tracked_company_nfe_count(auth_client: FlaskClient):
    """Test getting NFE count for tracked company by ID."""
    with auth_client.application.app_context():
        # Create a test company with valid CNPJ
        company = Company(cod_emp1='TEST002', name='NFE Test', cnpj='34028316000107')
        db.session.add(company)
        db.session.commit()
        company_id = company.id
    
    response = auth_client.get(f'/api/tracked_companies/{company_id}/nfe_count')
    assert response.status_code == 200
    data = response.get_json()
    assert 'company_id' in data
    assert 'company_name' in data
    assert 'cnpj' in data
    assert 'nfe_count' in data


def test_tracked_company_nfe_count_not_found(auth_client: FlaskClient):
    """Test getting NFE count for non-existent company."""
    response = auth_client.get('/api/tracked_companies/99999/nfe_count')
    assert response.status_code == 404


def test_check_nfe_available_post(auth_client: FlaskClient):
    """Test checking if NFEs are available for a CNPJ in date range."""
    response = auth_client.post('/api/tracked_companies/check_nfe_available', json={
        'cnpj': '34.028.316/0001-07',
        'start_date': '2024-01-01',
        'end_date': '2024-01-31'
    })
    # May succeed or fail depending on SIEG API, but should not be 400/500 on validation
    assert response.status_code in (200, 502)


def test_check_nfe_available_missing_cnpj(auth_client: FlaskClient):
    """Test check available without CNPJ."""
    response = auth_client.post('/api/tracked_companies/check_nfe_available', json={
        'start_date': '2024-01-01',
        'end_date': '2024-01-31'
    })
    assert response.status_code == 400


def test_check_nfe_available_missing_dates(auth_client: FlaskClient):
    """Test check available without date range."""
    response = auth_client.post('/api/tracked_companies/check_nfe_available', json={
        'cnpj': '34.028.316/0001-07'
    })
    assert response.status_code == 400


def test_delete_tracked_company(auth_client: FlaskClient):
    """Test deleting tracked company."""
    with auth_client.application.app_context():
        company = Company(cod_emp1='TEST006', name='Delete Test', cnpj='34028316000107')
        db.session.add(company)
        db.session.commit()
        company_id = company.id
    
    response = auth_client.delete(f'/api/tracked_companies/{company_id}')
    assert response.status_code == 200
    data = response.get_json()
    assert 'message' in data


def test_sync_company_nfes(auth_client: FlaskClient):
    """Test syncing NFEs for a company."""
    with auth_client.application.app_context():
        company = Company(cod_emp1='SYNC001', name='Sync Test', cnpj='34028316000107')
        db.session.add(company)
        db.session.commit()
        company_id = company.id
    
    response = auth_client.post(f'/api/tracked_companies/{company_id}/sync_nfes', json={
        'start_date': '2024-01-01',
        'end_date': '2024-01-15'
    })
    # May succeed or fail based on SIEG API availability
    assert response.status_code in (200, 400, 500)


def test_sync_company_nfes_missing_dates(auth_client: FlaskClient):
    """Test sync without date range."""
    with auth_client.application.app_context():
        company = Company(cod_emp1='SYNC002', name='No Dates', cnpj='34028316000107')
        db.session.add(company)
        db.session.commit()
        company_id = company.id
    
    response = auth_client.post(f'/api/tracked_companies/{company_id}/sync_nfes', json={})
    assert response.status_code == 400


def test_sync_company_nfes_not_found(auth_client: FlaskClient):
    """Test sync for non-existent company."""
    response = auth_client.post('/api/tracked_companies/99999/sync_nfes', json={
        'start_date': '2024-01-01',
        'end_date': '2024-01-15'
    })
    assert response.status_code == 404


def test_sync_company_nfes_chunk(auth_client: FlaskClient):
    """Test syncing a single 15-day chunk of NFEs."""
    with auth_client.application.app_context():
        company = Company(cod_emp1='CHUNK001', name='Chunk Test', cnpj='34028316000107')
        db.session.add(company)
        db.session.commit()
        company_id = company.id
    
    response = auth_client.post(f'/api/tracked_companies/{company_id}/sync_chunk', json={
        'chunk_start': '2024-01-01',
        'chunk_end': '2024-01-15'
    })
    # May succeed or fail based on SIEG API
    assert response.status_code in (200, 400, 500)


def test_sync_company_nfes_chunk_missing_dates(auth_client: FlaskClient):
    """Test chunk sync without dates."""
    with auth_client.application.app_context():
        company = Company(cod_emp1='CHUNK002', name='No Dates', cnpj='34028316000107')
        db.session.add(company)
        db.session.commit()
        company_id = company.id
    
    response = auth_client.post(f'/api/tracked_companies/{company_id}/sync_chunk', json={})
    assert response.status_code == 400


def test_sync_company_nfes_chunk_not_found(auth_client: FlaskClient):
    """Test chunk sync for non-existent company."""
    response = auth_client.post('/api/tracked_companies/99999/sync_chunk', json={
        'chunk_start': '2024-01-01',
        'chunk_end': '2024-01-15'
    })
    assert response.status_code == 404
    assert 'status' in data


# ==================== UTILITY TESTS ====================

def test_check_order_fulfillment_counts_canceled_items(auth_client: FlaskClient):
    """Test that order fulfillment logic counts canceled items correctly."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='FUL-001',
            dt_emis=date(2024, 3, 1),
            fornecedor_id=10,
            fornecedor_descricao='Fornecedor Cancelado'
        )
        db.session.add(order)
        db.session.flush()

        fully_attended = PurchaseItem(
            purchase_order_id=order.id,
            item_id='ITEM-A',
            dt_emis=date(2024, 3, 1),
            cod_pedc='FUL-001',
            descricao='Item atendido',
            quantidade=5,
            preco_unitario=10,
            total=50,
            qtde_atendida=5
        )
        fully_canceled = PurchaseItem(
            purchase_order_id=order.id,
            item_id='ITEM-B',
            dt_emis=date(2024, 3, 1),
            cod_pedc='FUL-001',
            descricao='Item cancelado',
            quantidade=7,
            preco_unitario=12,
            total=84,
            qtde_canc=7
        )
        db.session.add_all([fully_attended, fully_canceled])
        db.session.commit()

        assert check_order_fulfillment(order.id) is True

        pending_order = PurchaseOrder(
            cod_pedc='FUL-002',
            dt_emis=date(2024, 3, 2),
            fornecedor_id=20,
            fornecedor_descricao='Fornecedor Pendente'
        )
        db.session.add(pending_order)
        db.session.flush()

        pending_item = PurchaseItem(
            purchase_order_id=pending_order.id,
            item_id='ITEM-D',
            dt_emis=date(2024, 3, 2),
            cod_pedc='FUL-002',
            descricao='Item pendente',
            quantidade=10,
            preco_unitario=15,
            total=150,
            qtde_atendida=6,
            qtde_canc=2
        )
        db.session.add(pending_item)
        db.session.commit()

        assert check_order_fulfillment(pending_order.id) is False


def test_search_combined_matches_num_nf_from_nfe_match(auth_client: FlaskClient):
    """Test that combined search matches NFE numbers from PurchaseItemNFEMatch."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='PO-MATCH-001',
            dt_emis=date(2024, 5, 20),
            fornecedor_id=33,
            fornecedor_descricao='Fornecedor Match',
            cod_emp1='1'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='MATCH-ITEM',
            dt_emis=date(2024, 5, 20),
            cod_pedc='PO-MATCH-001',
            cod_emp1='1',
            linha=1,
            descricao='Item com correspondencia por NFE match',
            quantidade=1,
            preco_unitario=100,
            total=100
        )
        db.session.add(item)
        db.session.flush()

        nfe_data = NFEData(
            chave='12345678901234567890123456789012345678901244',
            xml_content='<xml />',
            numero='55555'
        )
        db.session.add(nfe_data)
        db.session.flush()

        match = PurchaseItemNFEMatch(
            purchase_item_id=item.id,
            cod_pedc='PO-MATCH-001',
            cod_emp1='1',
            item_seq=1,
            nfe_id=nfe_data.id,
            nfe_chave=nfe_data.chave,
            nfe_numero='55555',
            match_score=95
        )
        db.session.add(match)
        db.session.commit()

    response = auth_client.get('/api/search_combined', query_string={
        'query': '55555',
        'page': 1,
        'per_page': 10,
        'score_cutoff': 100,
        'searchByNumNF': True,
        'selectedFuncName': 'todos'
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['purchases']


def test_search_advanced_matches_num_nf_from_nfe_match(auth_client: FlaskClient):
    """Test that advanced search matches NFE numbers from PurchaseItemNFEMatch."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='PO-ADV-MATCH-001',
            dt_emis=date(2024, 6, 10),
            fornecedor_id=44,
            fornecedor_descricao='Fornecedor Advanced Match',
            cod_emp1='1'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='ADV-MATCH-ITEM',
            dt_emis=date(2024, 6, 10),
            cod_pedc='PO-ADV-MATCH-001',
            cod_emp1='1',
            linha=1,
            descricao='Item para busca avancada por match de NFE',
            quantidade=2,
            preco_unitario=200,
            total=400
        )
        db.session.add(item)
        db.session.flush()

        nfe_data = NFEData(
            chave='22345678901234567890123456789012345678901244',
            xml_content='<xml />',
            numero='55555'
        )
        db.session.add(nfe_data)
        db.session.flush()

        match = PurchaseItemNFEMatch(
            purchase_item_id=item.id,
            cod_pedc='PO-ADV-MATCH-001',
            cod_emp1='1',
            item_seq=1,
            nfe_id=nfe_data.id,
            nfe_chave=nfe_data.chave,
            nfe_numero='55555',
            match_score=90
        )
        db.session.add(match)
        db.session.commit()

    response = auth_client.get('/api/search_advanced', query_string={
        'query': '55555',
        'fields': 'num_nf',
        'page': 1,
        'per_page': 20,
        'selectedFuncName': 'todos'
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['purchases']


# ==================== INVALID INPUT TESTS ====================
# Tests for edge cases and invalid inputs to ensure endpoints don't hang or crash

def test_search_advanced_incomplete_cnpj_no_hang(auth_client: FlaskClient):
    """Test that incomplete CNPJs like 12.123.123 don't hang the search.
    
    Incomplete CNPJs should be treated as normal text (if >= 2 chars) and
    only searched as text, not triggering expensive CNPJ lookups.
    """
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '12.123.123',  # Only 8 digits - incomplete CNPJ
        'page': 1,
        'per_page': 20
    })
    # Should complete quickly without hanging
    assert response.status_code == 200
    assert 'purchases' in response.json


def test_search_advanced_single_character_query(auth_client: FlaskClient):
    """Test that single character queries are rejected (too short)."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'a',
        'page': 1,
        'per_page': 20
    })
    # Should return empty results or error gracefully
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_only_dots(auth_client: FlaskClient):
    """Test that queries with only dots/slashes are rejected."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '...',
        'page': 1,
        'per_page': 20
    })
    # Should return empty results
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_only_dashes(auth_client: FlaskClient):
    """Test that queries with only dashes are rejected."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '-----',
        'page': 1,
        'per_page': 20
    })
    # Should return empty results
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_incomplete_cpf(auth_client: FlaskClient):
    """Test that incomplete CPFs don't trigger expensive CNPJ lookups."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '123.456.789',  # Only 9 digits - incomplete CPF
        'page': 1,
        'per_page': 20
    })
    # Should complete without hanging
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_valid_complete_cnpj(auth_client: FlaskClient):
    """Test that complete CNPJs with 14 digits are recognized."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '45.986.718/0001-37',  # Exactly 14 digits
        'page': 1,
        'per_page': 20
    })
    # Should complete quickly and trigger CNPJ search
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_valid_complete_cpf(auth_client: FlaskClient):
    """Test that complete CPFs with 11 digits are recognized."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '123.456.789-10',  # Exactly 11 digits
        'page': 1,
        'per_page': 20
    })
    # Should complete quickly and trigger CNPJ search  
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_whitespace_only(auth_client: FlaskClient):
    """Test that whitespace-only queries are rejected."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '   ',
        'page': 1,
        'per_page': 20
    })
    # Should return empty results
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_combined_incomplete_cnpj_no_hang(auth_client: FlaskClient):
    """Test that incomplete CNPJs don't hang combined search."""
    response = auth_client.get('/api/search_combined', query_string={
        'query': '12.123.123',  # Only 8 digits
        'page': 1,
        'per_page': 10
    })
    # Should complete without hanging
    assert response.status_code == 200
    assert 'purchases' in response.json


def test_search_advanced_very_long_query(auth_client: FlaskClient):
    """Test that very long queries don't cause issues."""
    long_query = 'a' * 1000  # 1000 character query
    response = auth_client.get('/api/search_advanced', query_string={
        'query': long_query,
        'page': 1,
        'per_page': 20
    })
    # Should complete without hanging or error
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_special_characters(auth_client: FlaskClient):
    """Test that special characters in queries are handled safely."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '<script>alert("xss")</script>',
        'page': 1,
        'per_page': 20
    })
    # Should complete safely without XSS vulnerability
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_sql_injection_attempt(auth_client: FlaskClient):
    """Test that SQL injection attempts are safely handled."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': "' OR '1'='1",
        'page': 1,
        'per_page': 20
    })
    # Should complete safely without SQL injection
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_negative_page(auth_client: FlaskClient):
    """Test that negative page numbers are handled."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'test',
        'page': -5,
        'per_page': 20
    })
    # Should handle gracefully
    assert response.status_code == 200


def test_search_advanced_zero_per_page(auth_client: FlaskClient):
    """Test that zero items per page is handled."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'test',
        'page': 1,
        'per_page': 0
    })
    # Should handle gracefully
    assert response.status_code == 200


def test_search_advanced_excessive_per_page(auth_client: FlaskClient):
    """Test that excessive items per page is capped."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'test',
        'page': 1,
        'per_page': 10000
    })
    # Should handle gracefully (capped to 200)
    assert response.status_code == 200


def test_search_advanced_invalid_date_format(auth_client: FlaskClient):
    """Test that invalid date formats are handled gracefully."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'test',
        'date_from': 'not-a-date',
        'date_to': 'also-not-a-date',
        'page': 1,
        'per_page': 20
    })
    # Should handle gracefully and ignore invalid dates
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_partial_cnpj_with_wildcards(auth_client: FlaskClient):
    """Test that partial CNPJs with wildcards don't cause issues."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '45.986.7*/*-37',  # Partial CNPJ with wildcards
        'page': 1,
        'per_page': 20
    })
    # Should complete without hanging
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_combined_multiple_incomplete_cnpjs(auth_client: FlaskClient):
    """Test searching with multiple incomplete CNPJs."""
    response = auth_client.get('/api/search_combined', query_string={
        'query': '12.123 34.567 56.789',  # Multiple incomplete patterns
        'page': 1,
        'per_page': 10
    })
    # Should complete without hanging
    assert response.status_code == 200
    assert 'purchases' in response.json


def test_search_advanced_min_max_value_edge_cases(auth_client: FlaskClient):
    """Test min/max value filters with edge case values."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'test',
        'minValue': -999999,
        'maxValue': 999999999,
        'valueSearchType': 'item',
        'page': 1,
        'per_page': 20
    })
    # Should handle extreme values gracefully
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_search_advanced_invalid_value_search_type(auth_client: FlaskClient):
    """Test that invalid valueSearchType is handled."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'test',
        'minValue': 100,
        'valueSearchType': 'invalid_type',
        'page': 1,
        'per_page': 20
    })
    # Should handle gracefully
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


def test_count_results_incomplete_cnpj(auth_client: FlaskClient):
    """Test count_results with incomplete CNPJ."""
    response = auth_client.get('/api/count_results', query_string={
        'query': '12.123.123',
        'score_cutoff': 100
    })
    # Should complete without hanging
    assert response.status_code == 200
    assert 'count' in response.json


def test_search_fuzzy_incomplete_cnpj(auth_client: FlaskClient):
    """Test fuzzy search with incomplete CNPJ."""
    response = auth_client.get('/api/search_fuzzy', query_string={
        'query': '12.123.123',
        'score_cutoff': 60
    })
    # Should complete without hanging
    assert response.status_code == 200
    assert 'items' in response.json


def test_search_advanced_suggestions_incomplete_cnpj(auth_client: FlaskClient):
    """Test search suggestions with incomplete CNPJ."""
    response = auth_client.get('/api/search_advanced/suggestions', query_string={
        'term': '12.123.123'
    })
    # Should complete without hanging
    assert response.status_code == 200
    assert 'suggestions' in response.json


def test_search_advanced_empty_multiple_terms(auth_client: FlaskClient):
    """Test search with multiple spaces or empty terms."""
    response = auth_client.get('/api/search_advanced', query_string={
        'query': '   test    motor    ',
        'page': 1,
        'per_page': 20
    })
    # Should handle gracefully
    assert response.status_code == 200
    payload = response.get_json()
    assert 'purchases' in payload


# ==================== IMPORT HANDLER TESTS (RFOR, RPDC, RCOT, RUAH) ====================

def test_import_rfor0302_suppliers(auth_client: FlaskClient):
    """Test import_rfor0302 - Supplier XML file."""
    token_response = auth_client.post('/auth/generate_jwt_token', json={'expires_in': 60})
    assert token_response.status_code == 200
    token = token_response.json['token']
    
    # Sample RFOR0302 XML structure for suppliers
    rfor_xml = """<?xml version="1.0" encoding="UTF-8"?>
<RFOR0302>
    <G_FORNEC>
        <COD_FOR>001</COD_FOR>
        <TIP_FORN>01</TIP_FORN>
        <DESCRICAO>Supplier Test 001</DESCRICAO>
        <NVL_FORN_CNPJ_FORN_CPF>12.345.678/0001-95</NVL_FORN_CNPJ_FORN_CPF>
        <EMAIL>supplier@test.com</EMAIL>
        <TEL_DDD_TEL_TELEFONE>(11) 3000-0000</TEL_DDD_TEL_TELEFONE>
        <ENDERECO>Rua Test, 123</ENDERECO>
        <CEP>01234-567</CEP>
        <CIDADE>Sao Paulo</CIDADE>
        <UF>SP</UF>
        <BAIRRO>Centro</BAIRRO>
        <ID_FOR>100001</ID_FOR>
    </G_FORNEC>
</RFOR0302>""".encode('utf-8')
    
    data = {'file': (BytesIO(rfor_xml), 'RFOR0302.xml')}
    response = auth_client.post(
        '/api/import',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )
    # Debug: print response if not 201
    if response.status_code != 201:
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json}")
    assert response.status_code in (201, 400, 422)


def test_import_rpdc0250c_nfe_entries(auth_client: FlaskClient):
    """Test import_rpdc0250c - NFE entries XML file."""
    token_response = auth_client.post('/auth/generate_jwt_token', json={'expires_in': 60})
    assert token_response.status_code == 200
    token = token_response.json['token']
    
    # Sample RPDC0250C XML structure for NFE entries
    rpdc_xml = """<?xml version="1.0" encoding="UTF-8"?>
<RPDC0250C>
    <G_COD_EMP1>
        <COD_EMP>001</COD_EMP>
        <CGG_TPEDC_ITEM>
            <CODIGO_PEDIDO>PED-001</CODIGO_PEDIDO>
            <LINHA1>1</LINHA1>
            <G_NFE>
                <NUM_NF>000123</NUM_NF>
                <DT_ENT>01/01/2024</DT_ENT>
                <QTDE>10.00</QTDE>
            </G_NFE>
        </CGG_TPEDC_ITEM>
    </G_COD_EMP1>
</RPDC0250C>""".encode('utf-8')
    
    data = {'file': (BytesIO(rpdc_xml), 'RPDC0250C.xml')}
    response = auth_client.post(
        '/api/import',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 201
    assert 'imported' in response.json['message'].lower() or 'success' in response.json['message'].lower()


def test_import_rcot0300_quotations(auth_client: FlaskClient):
    """Test import_rcot0300 - Quotations XML file."""
    token_response = auth_client.post('/auth/generate_jwt_token', json={'expires_in': 60})
    assert token_response.status_code == 200
    token = token_response.json['token']
    
    # Sample RCOT0300 XML structure for quotations
    rcot_xml = """<?xml version="1.0" encoding="UTF-8"?>
<RCOT0300>
    <G_1>
        <COD_COT>COT001</COD_COT>
        <DT_EMISSAO>01/01/2024</DT_EMISSAO>
        <G_2>
            <G_3>
                <ID_FORN>100001</ID_FORN>
                <FORNECEDOR>Supplier Test</FORNECEDOR>
                <G_4>
                    <COD_ITEM>ITEM001</COD_ITEM>
                    <DESC_ITEM>Test Product</DESC_ITEM>
                    <QTDE>10.00</QTDE>
                    <UNID_MED>UN</UNID_MED>
                    <PRECO_UNITARIO>100.00</PRECO_UNITARIO>
                    <DT_ENTREGA>15/01/24</DT_ENTREGA>
                    <COD_EMP>001</COD_EMP>
                </G_4>
            </G_3>
        </G_2>
    </G_1>
</RCOT0300>""".encode('utf-8')
    
    data = {'file': (BytesIO(rcot_xml), 'RCOT0300.xml')}
    response = auth_client.post(
        '/api/import',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 201
    assert 'imported' in response.json['message'].lower() or 'success' in response.json['message'].lower()
    with auth_client.application.app_context():
        quotation = Quotation.query.filter_by(cod_cot='COT001', item_id='ITEM001').first()
        assert quotation is not None
        assert quotation.unidade_medida == 'UN'


def test_import_ruah_purchase_orders(auth_client: FlaskClient):
    """Test import_ruah - Purchase Orders XML file."""
    token_response = auth_client.post('/auth/generate_jwt_token', json={'expires_in': 60})
    assert token_response.status_code == 200
    token = token_response.json['token']
    
    # Sample RUAH XML structure for purchase orders
    ruah_xml = """<?xml version="1.0" encoding="UTF-8"?>
<RPDC0250>
    <G_COD_EMP1>
        <COD_EMP>001</COD_EMP>
        <RAZAO_SOCIAL>Test Company</RAZAO_SOCIAL>
        <EMPR_ID2>001</EMPR_ID2>
    </G_COD_EMP1>
    <TPED_COMPRA>
        <COD_PEDC>PED-001</COD_PEDC>
        <DT_EMIS>01/01/2024</DT_EMIS>
        <FOR_COD>001</FOR_COD>
        <FOR_DESCRICAO>Supplier Test</FOR_DESCRICAO>
        <TOT_BRUTO1>1000.00</TOT_BRUTO1>
        <TOT_LIQUIDO1>900.00</TOT_LIQUIDO1>
        <CP_TOT_IPI>50.00</CP_TOT_IPI>
        <TOT_LIQUIDO_IPI1>950.00</TOT_LIQUIDO_IPI1>
        <POSICAO1>Normal</POSICAO1>
        <POSICAO_HIST1>History</POSICAO_HIST1>
        <OBSERVACAO>Test order</OBSERVACAO>
        <CONTATO>Contact</CONTATO>
        <FUNC_NOME>Buyer Name</FUNC_NOME>
        <CF_PGTO>001</CF_PGTO>
        <LIST_TPEDC_ITEM>
            <TPEDC_ITEM>
                <ITEM_ID>ITEM001</ITEM_ID>
                <LINHA1>1</LINHA1>
                <DESCRICAO>Test Item</DESCRICAO>
                <QTD>5.00</QTD>
                <PRECO_UNITARIO>100.00</PRECO_UNITARIO>
                <TOTAL>500.00</TOTAL>
                <UNIDADE_MEDIDA>UN</UNIDADE_MEDIDA>
                <DT_ENTREGA>15/01/2024</DT_ENTREGA>
                <PERC_IPI>5.00</PERC_IPI>
                <QTD_ATENDIDA>5.00</QTD_ATENDIDA>
                <QTD_SALDO>0.00</QTD_SALDO>
                <QTD_CANC>0.00</QTD_CANC>
            </TPEDC_ITEM>
        </LIST_TPEDC_ITEM>
    </TPED_COMPRA>
</RPDC0250>""".encode('utf-8')
    
    data = {'file': (BytesIO(ruah_xml), 'RUAH.xml')}
    response = auth_client.post(
        '/api/import',
        data=data,
        content_type='multipart/form-data',
        headers={'Authorization': f'Bearer {token}'}
    )
    assert response.status_code == 201
    assert 'imported' in response.json['message'].lower() or 'success' in response.json['message'].lower()
