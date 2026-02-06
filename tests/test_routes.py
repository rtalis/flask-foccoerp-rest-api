import pytest
from io import BytesIO
from datetime import date, datetime, timedelta
from flask import Flask
from flask.testing import FlaskClient
from app import create_app, db
from app.models import PurchaseOrder, PurchaseItem, User, LoginHistory, NFEntry, Quotation
from app.utils import check_order_fulfillment
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
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

def test_import_requires_file_with_token(auth_client: FlaskClient):
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

def test_search_combined_matches_description(auth_client: FlaskClient):
    with auth_client.application.app_context():
        alpha_order = PurchaseOrder(
            cod_pedc='PO-ALPHA-001',
            dt_emis=date(2024, 4, 10),
            fornecedor_id=11,
            fornecedor_descricao='Alpha Equipamentos',
            observacao='Linha hidraulica'
        )
        beta_order = PurchaseOrder(
            cod_pedc='PO-BETA-001',
            dt_emis=date(2024, 4, 11),
            fornecedor_id=22,
            fornecedor_descricao='Beta Ferramentas',
            observacao='Linha filtros'
        )
        db.session.add_all([alpha_order, beta_order])
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
        beta_item = PurchaseItem(
            purchase_order_id=beta_order.id,
            item_id='BETA-ITEM',
            dt_emis=date(2024, 4, 11),
            cod_pedc='PO-BETA-001',
            descricao='Filtro de ar',
            quantidade=5,
            preco_unitario=200,
            total=1000
        )
        db.session.add_all([alpha_item, beta_item])
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
    assert len(payload['purchases']) == 1
    assert payload['purchases'][0]['order']['cod_pedc'] == 'PO-ALPHA-001'
    assert payload['purchases'][0]['items'][0]['descricao'] == 'Bomba Hidraulica industrial'

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

    with auth_client.application.app_context():
        user = User.query.filter_by(email='test@example.com').first()
        history = LoginHistory.query.filter_by(user_id=user.id).order_by(LoginHistory.login_time.desc()).first()
        assert history is not None
        assert history.logout_time is not None
        assert history.logout_ip == '127.0.0.1'


def test_dashboard_summary_includes_daily_usage(auth_client: FlaskClient):
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


def test_search_advanced_allows_empty_query(auth_client: FlaskClient):
    response = auth_client.get('/api/search_advanced')
    assert response.status_code == 200


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

    def test_search_advanced_respects_min_value(auth_client: FlaskClient):
        with auth_client.application.app_context():
            low_order = PurchaseOrder(
                cod_pedc='PO-LOW',
                dt_emis=date(2024, 5, 1),
                fornecedor_id=55,
                fornecedor_descricao='Fornecedor Basico'
            )
            high_order = PurchaseOrder(
                cod_pedc='PO-HIGH',
                dt_emis=date(2024, 5, 2),
                fornecedor_id=56,
                fornecedor_descricao='Fornecedor Premium'
            )
            db.session.add_all([low_order, high_order])
            db.session.flush()

            low_item = PurchaseItem(
                purchase_order_id=low_order.id,
                item_id='VALV-100',
                dt_emis=date(2024, 5, 1),
                cod_pedc='PO-LOW',
                descricao='Valvula compacta',
                quantidade=2,
                preco_unitario=500,
                total=1000
            )
            high_item = PurchaseItem(
                purchase_order_id=high_order.id,
                item_id='VALV-900',
                dt_emis=date(2024, 5, 2),
                cod_pedc='PO-HIGH',
                descricao='Valvula industrial premium',
                quantidade=4,
                preco_unitario=4000,
                total=16000
            )
            db.session.add_all([low_item, high_item])
            db.session.commit()

        response = auth_client.get('/api/search_advanced', query_string={
            'query': 'valvula',
            'fields': 'descricao',
            'per_page': 10,
            'minValue': 2000,
            'valueSearchType': 'item'
        })

        assert response.status_code == 200
        payload = response.get_json()
        assert payload['purchases']
        assert len(payload['purchases']) == 1
        assert payload['purchases'][0]['order']['cod_pedc'] == 'PO-HIGH'
        assert payload['purchases'][0]['items'][0]['preco_unitario'] == 4000

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


def test_check_order_fulfillment_counts_canceled_items(auth_client: FlaskClient):
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
        split_attended = PurchaseItem(
            purchase_order_id=order.id,
            item_id='ITEM-C',
            dt_emis=date(2024, 3, 1),
            cod_pedc='FUL-001',
            descricao='Item parcial atendido/cancelado',
            quantidade=9,
            preco_unitario=8,
            total=72,
            qtde_atendida=4,
            qtde_canc=5
        )
        db.session.add_all([fully_attended, fully_canceled, split_attended])
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


# ==================== NEW ENDPOINT TESTS ====================

def test_get_companies(auth_client: FlaskClient):
    """Test getting distinct company codes from purchase orders."""
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

    # Search by item_id
    response = auth_client.get('/api/search_items', query_string={'item_id': 'VALVE-001'})
    assert response.status_code == 200
    assert len(response.json) >= 1
    assert response.json[0]['item_id'] == 'VALVE-001'


def test_search_purchases(auth_client: FlaskClient):
    """Test searching purchase orders by cod_pedc, fornecedor, and observacao."""
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

    # Search by cod_pedc
    response = auth_client.get('/api/search_purchases', query_string={'cod_pedc': 'SRCPO'})
    assert response.status_code == 200

    # Search by fornecedor
    response = auth_client.get('/api/search_purchases', query_string={'fornecedor_descricao': 'Especial'})
    assert response.status_code == 200

    # Search by observacao
    response = auth_client.get('/api/search_purchases', query_string={'observacao': 'Urgente'})
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

    # Missing item_id should return error
    response = auth_client.get('/api/search_item_id')
    assert response.status_code == 400

    # Search with valid item_id
    response = auth_client.get('/api/search_item_id', query_string={'item_id': 'EXACT-ITEM-123'})
    assert response.status_code == 200
    assert isinstance(response.json, list)


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

    # Missing cod_pedc should return error
    response = auth_client.get('/api/get_purchase')
    assert response.status_code == 400

    # Get with valid cod_pedc
    response = auth_client.get('/api/get_purchase', query_string={'cod_pedc': 'GETPO-001'})
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) >= 1
    assert response.json[0]['cod_pedc'] == 'GETPO-001'


def test_quotations(auth_client: FlaskClient):
    """Test getting quotations by item_id."""
    from app.models import Quotation
    
    with auth_client.application.app_context():
        quotation = Quotation(
            cod_cot='COT-001',
            dt_emissao=date(2024, 8, 1),
            fornecedor_id=500,
            fornecedor_descricao='Fornecedor Cotacao',
            item_id='QUOT-ITEM-001',
            descricao='Item para cotacao',
            quantidade=20,
            preco_unitario=150
        )
        db.session.add(quotation)
        db.session.commit()

    # Missing item_id should return error
    response = auth_client.get('/api/quotations')
    assert response.status_code == 400

    # Get with valid item_id
    response = auth_client.get('/api/quotations', query_string={'item_id': 'QUOT-ITEM-001'})
    assert response.status_code == 200
    assert isinstance(response.json, list)


def test_quotation_items(auth_client: FlaskClient):
    """Test getting quotation items by cod_cot."""
    from app.models import Quotation
    
    with auth_client.application.app_context():
        quotation = Quotation(
            cod_cot='COTITEMS-001',
            dt_emissao=date(2024, 8, 15),
            fornecedor_id=600,
            fornecedor_descricao='Fornecedor COT Items',
            item_id='COTITEM-001',
            descricao='Primeiro item cotacao',
            quantidade=10,
            preco_unitario=200
        )
        db.session.add(quotation)
        db.session.commit()

    # Missing cod_cot should return error
    response = auth_client.get('/api/quotation_items')
    assert response.status_code == 400

    # Get with valid cod_cot
    response = auth_client.get('/api/quotation_items', query_string={'cod_cot': 'COTITEMS-001'})
    assert response.status_code == 200
    assert 'cod_cot' in response.json
    assert 'items' in response.json


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

    # Missing query should return error
    response = auth_client.get('/api/search_fuzzy')
    assert response.status_code == 400

    # Fuzzy search
    response = auth_client.get('/api/search_fuzzy', query_string={
        'query': 'motor',
        'score_cutoff': 60
    })
    assert response.status_code == 200
    assert 'items' in response.json
    assert 'purchases' in response.json


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


def test_auth_register_requires_admin(auth_client: FlaskClient):
    """Test that registration requires admin role."""
    # Default test user is not admin, should be forbidden
    response = auth_client.post('/auth/register', json={
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'newpass123'
    })
    assert response.status_code == 403


def test_auth_users_requires_admin(auth_client: FlaskClient):
    """Test that getting users list requires admin role."""
    response = auth_client.get('/auth/users')
    assert response.status_code == 403


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
        'fields': 'cod_pedc,descricao'
    })
    assert response.status_code == 200
    assert 'purchases' in response.json


def test_search_advanced_with_value_filters(auth_client: FlaskClient):
    """Test advanced search with min/max value filters."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='VALUE-001',
            dt_emis=date(2024, 11, 1),
            fornecedor_id=900,
            fornecedor_descricao='Fornecedor Value',
            total_pedido_com_ipi=50000
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='EXPENSIVE-ITEM',
            dt_emis=date(2024, 11, 1),
            cod_pedc='VALUE-001',
            descricao='Expensive industrial equipment',
            quantidade=1,
            preco_unitario=50000,
            total=50000
        )
        db.session.add(item)
        db.session.commit()

    # Search with minimum value
    response = auth_client.get('/api/search_advanced', query_string={
        'minValue': 10000,
        'valueSearchType': 'item',
        'fields': 'descricao'
    })
    assert response.status_code == 200


def test_search_advanced_hide_cancelled(auth_client: FlaskClient):
    """Test advanced search with hide cancelled filter."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='CANC-001',
            dt_emis=date(2024, 11, 15),
            fornecedor_id=950,
            fornecedor_descricao='Fornecedor Cancelados'
        )
        db.session.add(order)
        db.session.flush()

        active_item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='ACTIVE-ITEM',
            dt_emis=date(2024, 11, 15),
            cod_pedc='CANC-001',
            descricao='Active item filter test',
            quantidade=10,
            preco_unitario=100,
            total=1000,
            qtde_canc=0
        )
        cancelled_item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='CANCELLED-ITEM',
            dt_emis=date(2024, 11, 15),
            cod_pedc='CANC-001',
            descricao='Cancelled item filter test',
            quantidade=5,
            preco_unitario=200,
            total=1000,
            qtde_canc=5
        )
        db.session.add_all([active_item, cancelled_item])
        db.session.commit()

    response = auth_client.get('/api/search_advanced', query_string={
        'query': 'filter test',
        'hideCancelled': 'true',
        'fields': 'descricao'
    })
    assert response.status_code == 200


def test_dashboard_summary_with_buyer_filter(auth_client: FlaskClient):
    """Test dashboard summary with buyer filter."""
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='DASH-001',
            dt_emis=date(2024, 12, 1),
            fornecedor_id=1000,
            fornecedor_descricao='Fornecedor Dashboard',
            func_nome='Comprador Teste',
            total_pedido_com_ipi=15000
        )
        db.session.add(order)
        db.session.commit()

    response = auth_client.get('/api/dashboard_summary', query_string={
        'months': 3,
        'buyer': 'Comprador Teste'
    })
    assert response.status_code == 200
    assert 'summary' in response.json
    assert 'monthly_data' in response.json
    assert 'buyer_data' in response.json


def test_dashboard_summary_with_date_range(auth_client: FlaskClient):
    """Test dashboard summary with custom date range."""
    response = auth_client.get('/api/dashboard_summary', query_string={
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    })
    assert response.status_code == 200
    assert 'summary' in response.json


def test_purchase_by_nf(auth_client: FlaskClient):
    """Test getting purchase order by NF number."""
    from app.models import NFEntry
    
    with auth_client.application.app_context():
        order = PurchaseOrder(
            cod_pedc='NFTEST-001',
            dt_emis=date(2024, 12, 15),
            fornecedor_id=1100,
            fornecedor_descricao='Fornecedor NF Test',
            cod_emp1='001'
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            purchase_order_id=order.id,
            item_id='NF-ITEM',
            dt_emis=date(2024, 12, 15),
            cod_pedc='NFTEST-001',
            cod_emp1='001',
            linha='1',
            descricao='Item com NF',
            quantidade=3,
            preco_unitario=1000,
            total=3000
        )
        db.session.add(item)
        db.session.flush()

        nf_entry = NFEntry(
            cod_emp1='001',
            cod_pedc='NFTEST-001',
            linha='1',
            num_nf='123456'
        )
        db.session.add(nf_entry)
        db.session.commit()

    # Missing num_nf should return error
    response = auth_client.get('/api/purchase_by_nf')
    assert response.status_code == 400

    # Get with valid num_nf
    response = auth_client.get('/api/purchase_by_nf', query_string={'num_nf': '123456'})
    assert response.status_code == 200
    assert response.json['cod_pedc'] == 'NFTEST-001'


def test_search_nfe_requires_params(auth_client: FlaskClient):
    """Test that search_nfe requires query or date range."""
    response = auth_client.get('/api/search_nfe')
    assert response.status_code == 400
    assert 'error' in response.json


def test_search_nfe_with_date_range(auth_client: FlaskClient):
    """Test NFE search with date range only."""
    response = auth_client.get('/api/search_nfe', query_string={
        'start_date': '2024-01-01',
        'end_date': '2024-12-31'
    })
    assert response.status_code == 200
    assert 'nfes' in response.json
    assert 'purchase_orders' in response.json


def test_tracked_companies(auth_client: FlaskClient):
    """Test getting tracked companies."""
    response = auth_client.get('/api/tracked_companies')
    assert response.status_code == 200
    assert 'companies' in response.json
    assert isinstance(response.json['companies'], list)


def test_tracked_companies_add_requires_cnpj(auth_client: FlaskClient):
    """Test that adding tracked company requires CNPJ."""
    response = auth_client.post('/api/tracked_companies', json={
        'name': 'Test Company'
    })
    assert response.status_code == 400
    assert 'CNPJ' in response.json['error']


def test_tracked_companies_add_requires_cod_emp1(auth_client: FlaskClient):
    """Test that adding tracked company requires cod_emp1."""
    response = auth_client.post('/api/tracked_companies', json={
        'cnpj': '12345678901234',
        'name': 'Test Company'
    })
    assert response.status_code == 400
    assert 'cod_emp1' in response.json['error']