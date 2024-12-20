from app import db
from app.models import PurchaseOrder, PurchaseItem
import pytest

@pytest.fixture
def new_purchase_order():
    order = PurchaseOrder(cod_pedc='33951', dt_emis='11/11/24', for_cod='544', for_descricao='JOSÉ LEORNE RIOS E CIA LTDA')
    db.session.add(order)
    db.session.commit()
    return order

@pytest.fixture
def new_purchase_item(new_purchase_order):
    item = PurchaseItem(purchase_order_id=new_purchase_order.id, item_id='1677174', item_desc_tecnica='ÓCULOS DE PROTEÇÃO INCOLOR DE SOBREPOSIÇÃO', qtde=5, preco_unitario=4)
    db.session.add(item)
    db.session.commit()
    return item

def test_purchase_order_creation(new_purchase_order):
    assert new_purchase_order.cod_pedc == '33951'
    assert new_purchase_order.dt_emis == '11/11/24'
    assert new_purchase_order.for_cod == '544'
    assert new_purchase_order.for_descricao == 'JOSÉ LEORNE RIOS E CIA LTDA'

def test_purchase_item_creation(new_purchase_item):
    assert new_purchase_item.item_id == '1677174'
    assert new_purchase_item.item_desc_tecnica == 'ÓCULOS DE PROTEÇÃO INCOLOR DE SOBREPOSIÇÃO'
    assert new_purchase_item.qtde == 5
    assert new_purchase_item.preco_unitario == 4

def test_relationship(new_purchase_order, new_purchase_item):
    assert new_purchase_item.purchase_order_id == new_purchase_order.id
    assert new_purchase_order.purchase_items.count() == 1
    assert new_purchase_order.purchase_items[0].item_id == new_purchase_item.item_id