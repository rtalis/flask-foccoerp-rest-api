"""
Test for the PurchaseItemNFEMatch re-linking functionality.

This test verifies that when PurchaseItems are deleted and recreated,
the PurchaseItemNFEMatch records are properly re-linked using business keys.
"""
import pytest
from datetime import date, datetime
from app import create_app, db
from app.models import (
    PurchaseOrder, PurchaseItem, NFEData, NFEItem, 
    PurchaseItemNFEMatch, NFEEmitente
)
from app.utils import relink_purchase_item_nfe_matches


@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


def test_relink_purchase_item_nfe_matches(app):
    """
    Test that PurchaseItemNFEMatch records are properly re-linked
    after PurchaseItems are deleted and recreated.
    """
    with app.app_context():
        # === STEP 1: Create initial data ===
        
        # Create a purchase order
        purchase_order = PurchaseOrder(
            cod_pedc='12345',
            cod_emp1='001',
            dt_emis=date(2025, 1, 1),
            fornecedor_id=100,
            fornecedor_descricao='Test Supplier'
        )
        db.session.add(purchase_order)
        db.session.flush()
        
        # Create purchase items
        item1 = PurchaseItem(
            purchase_order_id=purchase_order.id,
            cod_pedc='12345',
            cod_emp1='001',
            item_id='ITEM001',
            linha=1,
            dt_emis=date(2025, 1, 1),
            descricao='Test Item 1',
            quantidade=10.0,
            preco_unitario=100.0,
            total=1000.0
        )
        item2 = PurchaseItem(
            purchase_order_id=purchase_order.id,
            cod_pedc='12345',
            cod_emp1='001',
            item_id='ITEM002',
            linha=2,
            dt_emis=date(2025, 1, 1),
            descricao='Test Item 2',
            quantidade=5.0,
            preco_unitario=200.0,
            total=1000.0
        )
        db.session.add_all([item1, item2])
        db.session.flush()
        
        original_item1_id = item1.id
        original_item2_id = item2.id
        
        # Create NFE data
        nfe = NFEData(
            chave='12345678901234567890123456789012345678901234',
            xml_content='<test>xml</test>',
            numero='123',
            data_emissao=datetime(2025, 1, 15)
        )
        db.session.add(nfe)
        db.session.flush()
        
        # Create NFE items
        nfe_item1 = NFEItem(
            nfe_id=nfe.id,
            numero_item=1,
            descricao='Test NFE Item 1',
            quantidade_comercial=10.0,
            valor_unitario_comercial=100.0
        )
        nfe_item2 = NFEItem(
            nfe_id=nfe.id,
            numero_item=2,
            descricao='Test NFE Item 2',
            quantidade_comercial=5.0,
            valor_unitario_comercial=200.0
        )
        db.session.add_all([nfe_item1, nfe_item2])
        db.session.flush()
        
        # Create PurchaseItemNFEMatch records
        match1 = PurchaseItemNFEMatch(
            purchase_item_id=item1.id,
            cod_pedc='12345',
            cod_emp1='001',
            item_seq=1,  # Matches linha
            nfe_id=nfe.id,
            nfe_item_id=nfe_item1.id,
            nfe_chave=nfe.chave,
            nfe_numero=nfe.numero,
            match_score=85.0,
            po_item_descricao='Test Item 1',
            po_item_quantidade=10.0,
            po_item_preco=100.0,
            nfe_item_descricao='Test NFE Item 1',
            nfe_item_quantidade=10.0,
            nfe_item_preco=100.0
        )
        match2 = PurchaseItemNFEMatch(
            purchase_item_id=item2.id,
            cod_pedc='12345',
            cod_emp1='001',
            item_seq=2,  # Matches linha
            nfe_id=nfe.id,
            nfe_item_id=nfe_item2.id,
            nfe_chave=nfe.chave,
            nfe_numero=nfe.numero,
            match_score=80.0,
            po_item_descricao='Test Item 2',
            po_item_quantidade=5.0,
            po_item_preco=200.0,
            nfe_item_descricao='Test NFE Item 2',
            nfe_item_quantidade=5.0,
            nfe_item_preco=200.0
        )
        db.session.add_all([match1, match2])
        db.session.commit()
        
        # Verify initial state
        assert match1.purchase_item_id == original_item1_id
        assert match2.purchase_item_id == original_item2_id
        
        print(f"Initial state:")
        print(f"  Item1 ID: {original_item1_id}, Match1 purchase_item_id: {match1.purchase_item_id}")
        print(f"  Item2 ID: {original_item2_id}, Match2 purchase_item_id: {match2.purchase_item_id}")
        
        # === STEP 2: Simulate deletion (like import_ruah does) ===
        
        # Delete purchase items - this should SET NULL on the matches
        PurchaseItem.query.filter_by(purchase_order_id=purchase_order.id).delete()
        db.session.commit()
        
        # Refresh the match objects
        db.session.refresh(match1)
        db.session.refresh(match2)
        
        # Verify matches now have NULL purchase_item_id
        assert match1.purchase_item_id is None, f"Expected NULL, got {match1.purchase_item_id}"
        assert match2.purchase_item_id is None, f"Expected NULL, got {match2.purchase_item_id}"
        
        print(f"\nAfter deletion:")
        print(f"  Match1 purchase_item_id: {match1.purchase_item_id}")
        print(f"  Match2 purchase_item_id: {match2.purchase_item_id}")
        
        # === STEP 3: Recreate purchase items (like import_ruah does) ===
        
        new_item1 = PurchaseItem(
            purchase_order_id=purchase_order.id,
            cod_pedc='12345',
            cod_emp1='001',
            item_id='ITEM001',
            linha=1,
            dt_emis=date(2025, 1, 1),
            descricao='Test Item 1 - Updated',
            quantidade=10.0,
            preco_unitario=100.0,
            total=1000.0
        )
        new_item2 = PurchaseItem(
            purchase_order_id=purchase_order.id,
            cod_pedc='12345',
            cod_emp1='001',
            item_id='ITEM002',
            linha=2,
            dt_emis=date(2025, 1, 1),
            descricao='Test Item 2 - Updated',
            quantidade=5.0,
            preco_unitario=200.0,
            total=1000.0
        )
        db.session.add_all([new_item1, new_item2])
        db.session.commit()
        
        new_item1_id = new_item1.id
        new_item2_id = new_item2.id
        
        print(f"\nAfter recreation:")
        print(f"  New Item1 ID: {new_item1_id}")
        print(f"  New Item2 ID: {new_item2_id}")
        
        # === STEP 4: Re-link the matches ===
        
        relinked_count = relink_purchase_item_nfe_matches()
        
        print(f"\nRe-linked count: {relinked_count}")
        
        # === STEP 5: Verify the matches are now linked to new items ===
        
        # Refresh the match objects
        db.session.refresh(match1)
        db.session.refresh(match2)
        
        print(f"\nAfter re-linking:")
        print(f"  Match1 purchase_item_id: {match1.purchase_item_id} (expected: {new_item1_id})")
        print(f"  Match2 purchase_item_id: {match2.purchase_item_id} (expected: {new_item2_id})")
        
        assert relinked_count == 2, f"Expected 2 re-linked, got {relinked_count}"
        assert match1.purchase_item_id == new_item1_id, f"Expected {new_item1_id}, got {match1.purchase_item_id}"
        assert match2.purchase_item_id == new_item2_id, f"Expected {new_item2_id}, got {match2.purchase_item_id}"
        
        # Verify the business keys are still intact
        assert match1.cod_pedc == '12345'
        assert match1.cod_emp1 == '001'
        assert match1.item_seq == 1
        assert match2.cod_pedc == '12345'
        assert match2.cod_emp1 == '001'
        assert match2.item_seq == 2
        
        print("\n✅ All assertions passed! Re-linking works correctly.")


def test_relink_no_orphans(app):
    """Test that relink returns 0 when there are no orphaned matches."""
    with app.app_context():
        # No matches exist
        relinked_count = relink_purchase_item_nfe_matches()
        assert relinked_count == 0
        print("✅ No orphans test passed!")


def test_relink_partial_matches(app):
    """Test that relink handles partial matches (some items don't exist)."""
    with app.app_context():
        # Create NFE data
        nfe = NFEData(
            chave='99999999999999999999999999999999999999999999',
            xml_content='<test>xml</test>',
            numero='999',
            data_emissao=datetime(2025, 1, 15)
        )
        db.session.add(nfe)
        db.session.flush()
        
        nfe_item = NFEItem(
            nfe_id=nfe.id,
            numero_item=1,
            descricao='Test NFE Item',
            quantidade_comercial=10.0
        )
        db.session.add(nfe_item)
        db.session.flush()
        
        # Create orphaned match (no corresponding PurchaseItem exists)
        orphan_match = PurchaseItemNFEMatch(
            purchase_item_id=None,  # Already orphaned
            cod_pedc='99999',  # This order doesn't exist
            cod_emp1='999',
            item_seq=1,
            nfe_id=nfe.id,
            nfe_item_id=nfe_item.id,
            nfe_chave=nfe.chave,
            match_score=70.0
        )
        db.session.add(orphan_match)
        db.session.commit()
        
        # Try to relink - should return 0 since no matching PurchaseItem exists
        relinked_count = relink_purchase_item_nfe_matches()
        
        assert relinked_count == 0, f"Expected 0, got {relinked_count}"
        
        # Verify match is still orphaned
        db.session.refresh(orphan_match)
        assert orphan_match.purchase_item_id is None
        
        print("✅ Partial matches test passed!")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
