from marshmallow import Schema, fields, post_load

from app.models import PurchaseItem, PurchaseOrder

class PurchaseItemSchema(Schema):
    id = fields.Int(dump_only=True)
    item_id = fields.Int(required=True)
    item_description = fields.Str(required=True)
    quantity = fields.Int(required=True)
    unit_price = fields.Float(required=True)
    total_price = fields.Float(required=True)

    @post_load
    def create_purchase_item(self, data, **kwargs):
        return PurchaseItem(**data)

class PurchaseOrderSchema(Schema):
    id = fields.Int(dump_only=True)
    order_code = fields.Str(required=True)
    supplier = fields.Str(required=True)
    order_date = fields.Date(required=True)
    items = fields.List(fields.Nested(PurchaseItemSchema), required=True)

    @post_load
    def create_purchase_order(self, data, **kwargs):
        return PurchaseOrder(**data)