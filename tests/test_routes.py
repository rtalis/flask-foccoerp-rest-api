from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
import pytest
from app import create_app, db
from app.models import PurchaseOrder, PurchaseItem

@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_import_xml(client):
    with open('tests/test_data.xml', 'rb') as xml_file:
        response = client.post('/import', data={'file': xml_file})
    assert response.status_code == 200
    assert b'Importaaoo realizada com sucesso' in response.data

def test_get_purchase_orders(client):
    response = client.get('/purchase_orders')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_get_purchase_items(client):
    response = client.get('/purchase_items')
    assert response.status_code == 200
    assert isinstance(response.json, list)