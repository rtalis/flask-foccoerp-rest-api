from app import create_app, db
from app.models import PurchaseOrder, Supplier
from sqlalchemy import cast, func
import re

app = create_app()
with app.app_context():
    def normalize_cnpj_expr(column):
        normalized = func.coalesce(cast(column, db.String), '')
        for char in ('.', '/', '-', ' '):
            normalized = func.replace(normalized, char, '')
        return normalized

    suppliers = Supplier.query.filter(normalize_cnpj_expr(Supplier.nvl_forn_cnpj_forn_cpf).ilike('%90815150%')).all()
    print("Found suppliers:", [(s.id_for, s.cod_for, s.nvl_forn_cnpj_forn_cpf) for s in suppliers])
    for s in suppliers:
        if s.id_for:
            # check orders by id_for
            orders2 = PurchaseOrder.query.filter(PurchaseOrder.fornecedor_id == s.id_for).count()
            print(f"Orders for ID_FOR ({s.id_for}): {orders2}")

        if s.cod_for:
            # check orders by cod_for
            orders1 = PurchaseOrder.query.filter(PurchaseOrder.fornecedor_id == int(s.cod_for)).count()
            print(f"Orders for COD_FOR ({s.cod_for}): {orders1}")
 
