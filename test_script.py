from app import create_app, db
from app.models import PurchaseItem, PurchaseOrder

app = create_app()
with app.app_context():
    q = PurchaseItem.query.join(PurchaseOrder).filter(PurchaseItem.descricao.ilike('%VELA%'))
    print("COUNT VELA:", q.count())
