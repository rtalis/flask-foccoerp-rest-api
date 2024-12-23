import pytest
from flask import Flask
from flask.testing import FlaskClient
from app import create_app, db
from app.models import PurchaseOrder, PurchaseItem

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()

def test_import_xml(client: FlaskClient):
    data = {
        'file': (open('tests/test_data.xml', 'rb'), 'test_data.xml')
    }
    response = client.post('/api/import', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    assert b'Data imported successfully' in response.data

def test_get_purchases(client: FlaskClient):
    response = client.get('/api/search_purchases')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_search_item(client: FlaskClient):
    response = client.get('/api/search_item', query_string={'descricao': 'example'})
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_search_item_fuzzy(client: FlaskClient):
    response = client.get('/api/search_item_fuzzy', query_string={'descricao': 'exmple'})
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_search_item_id(client: FlaskClient):
    response = client.get('/api/search_item_id', query_string={'item_id': '123'})
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_search_cod_pedc(client: FlaskClient):
    response = client.get('/api/search_cod_pedc', query_string={'cod_pedc': '456'})
    assert response.status_code == 200
    assert isinstance(response.json, list)