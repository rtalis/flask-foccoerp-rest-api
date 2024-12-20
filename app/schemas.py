from marshmallow import Schema, fields, post_load

from app.models import PurchaseItem, PurchaseOrder

class PurchaseItemSchema(Schema):
    id = fields.Int(dump_only=True)
    item_id = fields.Int(required=True)
    descricao = fields.Str(required=True)
    quantidade = fields.Float(required=True)  # Alterado para Float
    preco_unitario = fields.Float(required=True)

    @post_load
    def create_purchase_item(self, data, **kwargs):
        return PurchaseItem(**data)

class PurchaseOrderSchema(Schema):
    id = fields.Int(dump_only=True)
    cod_pedc = fields.Str(required=True)
    fornecedor_id = fields.Int(required=True)
    dt_emis = fields.Date(required=True)
    items = fields.List(fields.Nested(PurchaseItemSchema), required=False)

    @post_load
    def create_purchase_order(self, data, **kwargs):
        return PurchaseOrder(**data)