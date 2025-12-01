"""
Script to match unfulfilled purchase orders with NFEs from the database.
Uses the existing score_purchase_nfe_match logic to find best matches.
When a match score is high enough (default: 80%), stores the NFE number
for unfulfilled items to display in the search screen with an AI icon.

Results are stored in the PurchaseItemNFEMatch auxiliary table.
"""
import os
import sys
import logging
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from app.models import PurchaseOrder, PurchaseItem, NFEData, NFEItem, PurchaseItemNFEMatch
from app.utils import score_purchase_nfe_match

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Try to add file handler if log directory exists
try:
    os.makedirs("/var/log/foccoerp", exist_ok=True)
    file_handler = logging.FileHandler("/var/log/foccoerp/purchase_nfe_match.log")
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
except Exception:
    pass

logger = logging.getLogger('purchase_nfe_match')


def get_unfulfilled_orders(days=60):
    """
    Get all unfulfilled purchase orders from the last N days.
    Returns orders where is_fulfilled is False or has items with remaining qty.
    """
    cutoff_date = datetime.now().date() - timedelta(days=days)
    
    # Get orders from the last N days that are not fulfilled
    orders = PurchaseOrder.query.filter(
        PurchaseOrder.dt_emis >= cutoff_date,
        PurchaseOrder.is_fulfilled == False
    ).all()
    
    return orders


def get_unfulfilled_items_for_order(order):
    """
    Get all items for an order that are not fully fulfilled.
    Returns items where quantity remaining > 0.
    """
    items = PurchaseItem.query.filter_by(purchase_order_id=order.id).all()
    
    unfulfilled = []
    for item in items:
        qty = float(item.quantidade or 0)
        atendida = float(item.qtde_atendida or 0)
        canceled = float(item.qtde_canc or 0)
        
        effective_qty = qty - canceled
        remaining = effective_qty - atendida
        
        if remaining > 0:
            unfulfilled.append({
                'item': item,
                'remaining_qty': remaining,
                'effective_qty': effective_qty
            })
    
    return unfulfilled


def clean_fulfilled_items():
    """
    Remove entries from PurchaseItemNFEMatch for items that are now fulfilled.
    """
    # Get all unique purchase_item_ids from the match table
    matches = db.session.query(PurchaseItemNFEMatch.purchase_item_id).distinct().all()
    
    deleted_count = 0
    
    for (item_id,) in matches:
        # Check if the purchase item is now fulfilled
        item = db.session.get(PurchaseItem, item_id)
        
        if item is None:
            # Item was deleted, remove matches
            PurchaseItemNFEMatch.query.filter_by(purchase_item_id=item_id).delete()
            deleted_count += 1
            continue
        
        qty = float(item.quantidade or 0)
        atendida = float(item.qtde_atendida or 0)
        canceled = float(item.qtde_canc or 0)
        
        effective_qty = qty - canceled
        remaining = effective_qty - atendida
        
        if remaining <= 0:
            # Item is fulfilled, delete matches
            PurchaseItemNFEMatch.query.filter_by(purchase_item_id=item_id).delete()
            deleted_count += 1
            logger.info(f"Cleaned matches for fulfilled item {item_id}")
    
    if deleted_count > 0:
        db.session.commit()
        logger.info(f"Cleaned {deleted_count} fulfilled items from match table")
    
    return deleted_count


def store_item_matches(order, nfe_match, unfulfilled_items, min_score=80):
    """
    Store item-level matches from a high-scoring NFE match.
    
    Args:
        order: The PurchaseOrder
        nfe_match: The NFE match result from score_purchase_nfe_match
        unfulfilled_items: List of unfulfilled items for this order
        min_score: Minimum overall match score to store (default: 80)
    
    Returns:
        Number of items stored
    """
    score = nfe_match.get('score', 0)
    
    # Only store if overall match score is high enough
    if score < min_score:
        return 0
    
    nfe_id = nfe_match.get('nfe_id')
    nfe_chave = nfe_match.get('nfe_chave')
    nfe_numero = nfe_match.get('nfe_number')
    nfe_supplier = nfe_match.get('nfe_supplier', '')
    
    # Handle combined NFEs - use first NFE's info
    is_combined = nfe_match.get('is_combined', False)
    if is_combined:
        # For combined NFEs, we'll store the combination info but use first NFE
        combined_nfes = nfe_match.get('combined_nfes', [])
        if combined_nfes:
            first_nfe = NFEData.query.filter(NFEData.numero == combined_nfes[0]).first()
            if first_nfe:
                nfe_id = first_nfe.id
                nfe_chave = first_nfe.chave
            else:
                return 0
        else:
            return 0
    else:
        # Get the NFE from database
        if isinstance(nfe_id, int):
            nfe = db.session.get(NFEData, nfe_id)
            if nfe:
                nfe_chave = nfe.chave
        elif nfe_chave:
            nfe = NFEData.query.filter_by(chave=nfe_chave).first()
            if nfe:
                nfe_id = nfe.id
        
        if not nfe_id or not nfe_chave:
            return 0
    
    # Get full NFE object for data_emissao
    nfe = db.session.get(NFEData, nfe_id) if isinstance(nfe_id, int) else None
    
    # Get item matches from the NFE match result
    item_matches = nfe_match.get('item_matches', [])
    
    # Build a map of PO item ID to match details
    po_item_match_map = {}
    for match in item_matches:
        po_item_id = match.get('po_item_id')
        if po_item_id:
            po_item_match_map[po_item_id] = match
    
    stored_count = 0
    
    # Store matches for unfulfilled items that have a corresponding item match
    for item_data in unfulfilled_items:
        item = item_data['item']
        
        # Check if this item has a match
        item_match = po_item_match_map.get(item.id)
        
        if not item_match:
            # No item-level match, but if overall score is very high (>=90),
            # still associate this NFE with unfulfilled items
            if score >= 90:
                item_match = {
                    'combined_score': score * 0.8,  # Slightly lower since no direct item match
                    'desc_score': 0,
                    'nfe_item_id': None,
                    'nfe_item_desc': None,
                    'nfe_qty': None,
                    'nfe_price': None
                }
            else:
                continue
        
        item_id = item.id
        
        try:
            # Get NFE item if available
            nfe_item_id = item_match.get('nfe_item_id')
            nfe_item = None
            if nfe_item_id:
                nfe_item = db.session.get(NFEItem, nfe_item_id)
            
            # Check if entry already exists
            existing = PurchaseItemNFEMatch.query.filter_by(
                purchase_item_id=item.id,
                nfe_id=nfe_id
            ).first()
            
            item_score = item_match.get('combined_score', score * 0.8)
            desc_similarity = item_match.get('desc_score', 0)
            qty_match = item_match.get('qty_score', 0) >= 80 if item_match.get('qty_score') else False
            price_diff = 0
            if item_match.get('po_price') and item_match.get('nfe_price'):
                if item_match['po_price'] > 0:
                    price_diff = abs(item_match['nfe_price'] - item_match['po_price']) / item_match['po_price'] * 100
            
            if existing:
                # Update if new score is better
                if item_score > existing.match_score:
                    existing.match_score = item_score
                    existing.description_similarity = desc_similarity
                    existing.quantity_match = qty_match
                    existing.price_diff_pct = price_diff
                    existing.nfe_item_id = nfe_item_id
                    existing.nfe_item_descricao = item_match.get('nfe_item_desc', '')
                    existing.nfe_item_quantidade = item_match.get('nfe_qty')
                    existing.nfe_item_preco = item_match.get('nfe_price')
                    existing.nfe_fornecedor = nfe_supplier
                    existing.nfe_data_emissao = nfe.data_emissao if nfe else None
                    existing.updated_at = datetime.now()
                    stored_count += 1
            else:
                # Create new entry
                new_match = PurchaseItemNFEMatch(
                    purchase_item_id=item.id,
                    cod_pedc=order.cod_pedc,
                    cod_emp1=order.cod_emp1,
                    item_seq=item.linha,
                    nfe_id=nfe_id,
                    nfe_item_id=nfe_item_id,
                    nfe_chave=nfe_chave,
                    nfe_numero=nfe_numero,
                    match_score=item_score,
                    description_similarity=desc_similarity,
                    quantity_match=qty_match,
                    price_diff_pct=price_diff,
                    po_item_descricao=item.descricao,
                    po_item_quantidade=float(item.quantidade or 0),
                    po_item_preco=float(item.preco_unitario or 0),
                    nfe_item_descricao=item_match.get('nfe_item_desc', ''),
                    nfe_item_quantidade=item_match.get('nfe_qty'),
                    nfe_item_preco=item_match.get('nfe_price'),
                    nfe_fornecedor=nfe_supplier,
                    nfe_data_emissao=nfe.data_emissao if nfe else None
                )
                db.session.add(new_match)
                stored_count += 1
                
        except Exception as e:
            logger.error(f"Error storing match for item {item_id}: {str(e)}")
            db.session.rollback()  # Rollback to recover from error
            continue
    
    return stored_count


def match_purchases_with_nfes(days=60, min_score=80):
    """
    Main function to match unfulfilled purchases with NFEs.
    Uses the existing score_purchase_nfe_match logic.
    
    Args:
        days: Number of days to look back for purchases (default: 60)
        min_score: Minimum score to store a match (default: 80)
    
    Returns:
        Dictionary with statistics about the matching process
    """
    app = create_app()
    
    with app.app_context():
        logger.info(f"Starting purchase-NFE matching for last {days} days (min_score={min_score})")
        
        stats = {
            'orders_processed': 0,
            'orders_with_matches': 0,
            'items_matched': 0,
            'items_cleaned': 0,
            'errors': 0
        }
        
        # First, clean up fulfilled items from the match table
        stats['items_cleaned'] = clean_fulfilled_items()
        
        # Get unfulfilled orders
        unfulfilled_orders = get_unfulfilled_orders(days)
        logger.info(f"Found {len(unfulfilled_orders)} unfulfilled orders to process")
        
        for order in unfulfilled_orders:
            # Store order info before any DB operations that might expire the object
            order_cod_pedc = order.cod_pedc
            order_cod_emp1 = order.cod_emp1
            
            try:
                # Get unfulfilled items for this order
                unfulfilled_items = get_unfulfilled_items_for_order(order)
                
                if not unfulfilled_items:
                    stats['orders_processed'] += 1
                    continue
                
                # Check if we already have matches for this order's unfulfilled items
                # Skip if all unfulfilled items already have a match
                unfulfilled_item_ids = [item_data['item'].id for item_data in unfulfilled_items]
                existing_matches = PurchaseItemNFEMatch.query.filter(
                    PurchaseItemNFEMatch.purchase_item_id.in_(unfulfilled_item_ids)
                ).count()
                
                if existing_matches >= len(unfulfilled_items):
                    # All items already have matches, skip
                    stats['orders_processed'] += 1
                    continue
                
                logger.info(f"Processing order {order_cod_pedc}/{order_cod_emp1} with {len(unfulfilled_items)} unfulfilled items")
                
                # Call the existing scoring function
                match_results = score_purchase_nfe_match(order_cod_pedc, order_cod_emp1)
                
                if isinstance(match_results, dict) and 'error' in match_results:
                    logger.warning(f"Error matching order {order.cod_pedc}: {match_results['error']}")
                    stats['errors'] += 1
                    continue
                
                # Get matches from result
                matches = match_results.get('matches', [])
                
                if not matches:
                    continue
                
                # Store matches for the best matching NFE(s)
                # Only process top matches that meet the score threshold
                order_items_matched = 0
                for nfe_match in matches:
                    if nfe_match.get('score', 0) >= min_score:
                        stored = store_item_matches(order, nfe_match, unfulfilled_items, min_score)
                        order_items_matched += stored
                        
                        # Only store the best match per order to avoid duplicates
                        if stored > 0:
                            break
                
                if order_items_matched > 0:
                    stats['orders_with_matches'] += 1
                    stats['items_matched'] += order_items_matched
                    logger.info(f"Stored {order_items_matched} item matches for order {order_cod_pedc}")
                
                stats['orders_processed'] += 1
                
                # Commit periodically to avoid large transactions
                if stats['orders_processed'] % 50 == 0:
                    db.session.commit()
                    logger.info(f"Processed {stats['orders_processed']} orders so far...")
                
            except Exception as e:
                logger.error(f"Error processing order {order_cod_pedc}: {str(e)}")
                stats['errors'] += 1
                db.session.rollback()
                continue
        
        # Final commit
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error committing final batch: {str(e)}")
            db.session.rollback()
        
        logger.info(f"Purchase-NFE matching completed. Stats: {stats}")
        
        return stats


def get_estimated_nfe_for_item(purchase_item_id):
    """
    Retrieve the estimated NFE match for a specific purchase item.
    Returns the best match (highest score) for display in the search screen.
    """
    match = PurchaseItemNFEMatch.query.filter_by(
        purchase_item_id=purchase_item_id
    ).order_by(PurchaseItemNFEMatch.match_score.desc()).first()
    
    if not match:
        return None
    
    return {
        'nfe_chave': match.nfe_chave,
        'nfe_numero': match.nfe_numero,
        'match_score': match.match_score,
        'nfe_fornecedor': match.nfe_fornecedor,
        'nfe_data_emissao': match.nfe_data_emissao.isoformat() if match.nfe_data_emissao else None,
        'is_estimated': True
    }


def get_estimated_nfes_for_order(cod_pedc, cod_emp1):
    """
    Retrieve all estimated NFE matches for a purchase order.
    Returns a dict mapping item_seq to estimated NFE info for the search screen.
    """
    matches = PurchaseItemNFEMatch.query.filter_by(
        cod_pedc=cod_pedc,
        cod_emp1=cod_emp1
    ).order_by(
        PurchaseItemNFEMatch.item_seq,
        PurchaseItemNFEMatch.match_score.desc()
    ).all()
    
    # Group by item_seq, keep only best match per item
    result = {}
    for m in matches:
        seq = m.item_seq or 0
        if seq not in result:
            result[seq] = {
                'purchase_item_id': m.purchase_item_id,
                'nfe_chave': m.nfe_chave,
                'nfe_numero': m.nfe_numero,
                'match_score': m.match_score,
                'nfe_fornecedor': m.nfe_fornecedor,
                'nfe_data_emissao': m.nfe_data_emissao.isoformat() if m.nfe_data_emissao else None,
                'is_estimated': True
            }
    
    return result


def get_estimated_nfe_numbers_for_order(cod_pedc, cod_emp1):
    """
    Get unique AI-estimated NFE numbers for a purchase order.
    Used to populate the NFEs column in the search screen.
    """
    matches = PurchaseItemNFEMatch.query.filter_by(
        cod_pedc=cod_pedc,
        cod_emp1=cod_emp1
    ).order_by(PurchaseItemNFEMatch.match_score.desc()).all()
    
    # Get unique NFE numbers with their best score
    nfe_map = {}
    for m in matches:
        if m.nfe_numero and m.nfe_numero not in nfe_map:
            nfe_map[m.nfe_numero] = {
                'nfe_numero': m.nfe_numero,
                'nfe_chave': m.nfe_chave,
                'match_score': m.match_score,
                'nfe_fornecedor': m.nfe_fornecedor,
                'is_estimated': True
            }
    
    return list(nfe_map.values())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Match unfulfilled purchases with NFEs')
    parser.add_argument('--days', type=int, default=60, help='Number of days to look back (default: 60)')
    parser.add_argument('--min-score', type=int, default=80, help='Minimum score to store match (default: 80)')
    parser.add_argument('--clean-only', action='store_true', help='Only clean fulfilled items, do not match')
    
    args = parser.parse_args()
    
    if args.clean_only:
        app = create_app()
        with app.app_context():
            cleaned = clean_fulfilled_items()
            print(f"Cleaned {cleaned} fulfilled items from match table")
    else:
        stats = match_purchases_with_nfes(
            days=args.days,
            min_score=args.min_score
        )
        print(f"Matching completed: {stats}")
