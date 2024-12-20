from marshmallow import Schema, fields, post_load

from app.models import PurchaseItem, PurchaseOrder

class PurchaseItemSchema(Schema):
    id = fields.Int(dump_only=True)
    item_id = fields.Int(required=True)
    cod_pedc = fields.Str(required=True)
    linha = fields.Int(required=False)
    descricao = fields.Str(required=True)
    quantidade = fields.Float(required=True)
    preco_unitario = fields.Float(required=True)
    total = fields.Float(required=True)
    unidade_medida = fields.Str(required=False)
    dt_entrega = fields.Date(required=False)
    perc_ipi = fields.Float(required=False)
    tot_liquido_ipi = fields.Float(required=False)
    tot_descontos = fields.Float(required=False)
    tot_acrescimos = fields.Float(required=False)
    qtde_canc = fields.Float(required=False)
    qtde_canc_toler = fields.Float(required=False)
    perc_toler = fields.Float(required=False)

    @post_load
    def create_purchase_item(self, data, **kwargs):
        return PurchaseItem(**data)

class PurchaseOrderSchema(Schema):
    id = fields.Int(dump_only=True)
    cod_pedc = fields.Str(required=True)
    fornecedor_id = fields.Int(required=True)
    dt_emis = fields.Date(required=True)
    fornecedor_descricao = fields.Str(required=False)
    total_bruto = fields.Float(required=False)
    total_liquido = fields.Float(required=False)
    total_liquido_ipi = fields.Float(required=False)
    posicao = fields.Str(required=False)
    posicao_hist = fields.Str(required=False)
    observacao = fields.Str(required=False)
    items = fields.List(fields.Nested(PurchaseItemSchema), required=False)

    @post_load
    def create_purchase_order(self, data, **kwargs):
        return PurchaseOrder(**data)