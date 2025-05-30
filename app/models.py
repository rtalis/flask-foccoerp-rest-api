from datetime import datetime
from app import db
from flask_login import UserMixin

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'

    id = db.Column(db.Integer, primary_key=True)
    cod_pedc = db.Column(db.String, nullable=False)
    dt_emis = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, nullable=False)
    fornecedor_descricao = db.Column(db.String, nullable=True)
    total_bruto = db.Column(db.Float, nullable=True)
    total_liquido = db.Column(db.Float, nullable=True)
    total_liquido_ipi = db.Column(db.Float, nullable=True)
    posicao = db.Column(db.String, nullable=True)
    posicao_hist = db.Column(db.String, nullable=True)
    observacao = db.Column(db.String, nullable=True)
    contato = db.Column(db.String, nullable=True)
    func_nome = db.Column(db.String, nullable=True)
    cf_pgto = db.Column(db.String, nullable=True)
    cod_emp1 = db.Column(db.String, nullable=True)
    items = db.relationship('PurchaseItem', backref='purchase_order', lazy=True)

class PurchaseItem(db.Model):
    __tablename__ = 'purchase_items'

    id = db.Column(db.Integer, primary_key=True)
    dt_emis = db.Column(db.Date, nullable=False)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    item_id = db.Column(db.String, nullable=False)
    cod_pedc = db.Column(db.String, nullable=False)
    linha = db.Column(db.Integer, nullable=True)
    descricao = db.Column(db.String, nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    unidade_medida = db.Column(db.String, nullable=True)
    dt_entrega = db.Column(db.Date, nullable=True)
    perc_ipi = db.Column(db.Float, nullable=True)
    tot_liquido_ipi = db.Column(db.Float, nullable=True)
    tot_descontos = db.Column(db.Float, nullable=True)
    tot_acrescimos = db.Column(db.Float, nullable=True)
    qtde_canc = db.Column(db.Float, nullable=True)
    qtde_canc_toler = db.Column(db.Float, nullable=True)
    perc_toler = db.Column(db.Float, nullable=True)
    qtde_atendida = db.Column(db.Float, nullable=True)
    qtde_saldo = db.Column(db.Float, nullable=True)
    cod_emp1 = db.Column(db.String, nullable=True)
    
class NFEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cod_emp1 = db.Column(db.String(50), nullable=False)
    cod_pedc = db.Column(db.String(50), nullable=False)
    linha = db.Column(db.Integer, nullable=True)
    num_nf = db.Column(db.String(50), nullable=False)
    dt_ent = db.Column(db.Date, nullable=True)    #purchase_item_id = db.Column(db.Integer, db.ForeignKey('purchase_item.id'), nullable=False)

    #purchase_item = db.relationship('PurchaseItem', backref=db.backref('nf_entries', lazy=True))
    

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    login_history = db.relationship('LoginHistory', backref='user', lazy=True)

class LoginHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, default=datetime.now)
    logout_time = db.Column(db.DateTime, nullable=True)
    
class Quotation(db.Model):
    __tablename__ = 'quotations'
    id = db.Column(db.Integer, primary_key=True)
    cod_cot = db.Column(db.String, nullable=False)
    dt_emissao = db.Column(db.Date, nullable=False)
    fornecedor_id = db.Column(db.Integer, nullable=False)
    fornecedor_descricao = db.Column(db.String, nullable=False)
    item_id = db.Column(db.String, nullable=False)
    descricao = db.Column(db.String, nullable=False)
    quantidade = db.Column(db.Float, nullable=False)
    preco_unitario = db.Column(db.Float, nullable=True)
    dt_entrega = db.Column(db.Date, nullable=True)
    cod_emp1 = db.Column(db.String, nullable=True)