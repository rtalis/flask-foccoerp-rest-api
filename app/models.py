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
    total_pedido_com_ipi = db.Column(db.Float, nullable=True)
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
    role = db.Column(db.String(50), nullable=False, default='viewer')  # 'admin' | 'viewer' | 'purchaser'
    purchaser_name = db.Column(db.String(150), nullable=True)          # Links user to PurchaseOrder.func_nome
    initial_screen = db.Column(db.String(100), nullable=False, default='/dashboard')
    allowed_screens = db.Column(db.JSON, nullable=False, default=list)


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


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    id_for = db.Column(db.Integer)
    cod_for = db.Column(db.String(20))
    tip_forn = db.Column(db.String(100))
    conta_itens = db.Column(db.String(50))
    insc_est = db.Column(db.String(50))
    insc_mun = db.Column(db.String(50))
    email = db.Column(db.String(150))
    tel_ddd_tel_telefone = db.Column(db.String(50))
    endereco = db.Column(db.String(200))
    cep = db.Column(db.String(20))
    cidade = db.Column(db.String(100))
    uf = db.Column(db.String(10))
    nvl_forn_cnpj_forn_cpf = db.Column(db.String(30))
    descricao = db.Column(db.String(200))
    bairro = db.Column(db.String(100))
    cf_fax = db.Column(db.String(50))

class PurchaseAdjustment(db.Model):
    __tablename__ = 'purchase_adjustments'
    
    id = db.Column(db.Integer, primary_key=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id'), nullable=False)
    tp_apl = db.Column(db.String(50), nullable=True)
    tp_dctacr1 = db.Column(db.String(50), nullable=True)
    tp_vlr1 = db.Column(db.String(50), nullable=True)
    vlr1 = db.Column(db.Float, nullable=True)
    order_index = db.Column(db.Integer, nullable=True)
    cod_emp1 = db.Column(db.String(50), nullable=True)
    cod_pedc = db.Column(db.String(50), nullable=True)
    
    purchase_order = db.relationship('PurchaseOrder', backref=db.backref('adjustments', lazy=True))


# Add these new models to your existing models.py file

class NFEData(db.Model):
    __tablename__ = 'nfe_data'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Main NFE identification
    chave = db.Column(db.String(44), unique=True, nullable=False, index=True)
    xml_content = db.Column(db.Text, nullable=False)  # Full XML content for exact reconstruction
    
    # NFE Document Info
    versao = db.Column(db.String(10))
    modelo = db.Column(db.String(2))  # 55 for NFe, 65 for NFCe, etc.
    
    # Basic NFE data
    numero = db.Column(db.String(20))
    serie = db.Column(db.String(10))
    data_emissao = db.Column(db.DateTime)
    data_saida = db.Column(db.DateTime)
    
    # Nature of operation
    natureza_operacao = db.Column(db.String(255))
    tipo_operacao = db.Column(db.String(2))  # 0-entrada, 1-saída
    finalidade = db.Column(db.String(2))  # 1-normal, 2-complementar, etc.
    
    # Status info
    status_code = db.Column(db.String(10))  # cStat from protocol
    status_motivo = db.Column(db.String(255))  # xMotivo from protocol
    protocolo = db.Column(db.String(20))
    data_autorizacao = db.Column(db.DateTime)
    ambiente = db.Column(db.String(2))  # 1-production, 2-test
    
    # UF and city codes
    uf_emitente = db.Column(db.String(2))
    codigo_uf = db.Column(db.String(2))
    codigo_municipio = db.Column(db.String(10))
    
    # Values
    valor_total = db.Column(db.Float)
    valor_produtos = db.Column(db.Float)
    valor_frete = db.Column(db.Float)
    valor_seguro = db.Column(db.Float)
    valor_desconto = db.Column(db.Float)
    valor_imposto = db.Column(db.Float)
    valor_icms = db.Column(db.Float)
    valor_icms_st = db.Column(db.Float)
    valor_ipi = db.Column(db.Float)
    valor_pis = db.Column(db.Float)
    valor_cofins = db.Column(db.Float)
    valor_outros = db.Column(db.Float)
    
    # Additional info
    informacoes_adicionais = db.Column(db.Text)
    informacoes_fisco = db.Column(db.Text)
    
    # Payment info
    forma_pagamento = db.Column(db.String(10))
    valor_pagamento = db.Column(db.Float)
    
    # Transport
    modalidade_frete = db.Column(db.String(2))
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    emitente = db.relationship('NFEEmitente', backref='nfe', uselist=False, cascade="all, delete-orphan")
    destinatario = db.relationship('NFEDestinatario', backref='nfe', uselist=False, cascade="all, delete-orphan")
    itens = db.relationship('NFEItem', backref='nfe', cascade="all, delete-orphan")
    transportadora = db.relationship('NFETransportadora', backref='nfe', uselist=False, cascade="all, delete-orphan")
    volumes = db.relationship('NFEVolume', backref='nfe', cascade="all, delete-orphan")
    pagamentos = db.relationship('NFEPagamento', backref='nfe', cascade="all, delete-orphan")
    duplicatas = db.relationship('NFEDuplicata', backref='nfe', cascade="all, delete-orphan")

class NFEEmitente(db.Model):
    __tablename__ = 'nfe_emitentes'
    
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe_data.id'), nullable=False)
    
    cpf = db.Column(db.String(11))
    cnpj = db.Column(db.String(14))
    nome = db.Column(db.String(255), nullable=False)
    nome_fantasia = db.Column(db.String(255))
    inscricao_estadual = db.Column(db.String(50))
    inscricao_municipal = db.Column(db.String(50))
    codigo_regime_tributario = db.Column(db.String(2))  # CRT
    
    # Address fields
    logradouro = db.Column(db.String(255))
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(255))
    bairro = db.Column(db.String(100))
    codigo_municipio = db.Column(db.String(10))
    municipio = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    pais = db.Column(db.String(100))
    codigo_pais = db.Column(db.String(10))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(255))

class NFEDestinatario(db.Model):
    __tablename__ = 'nfe_destinatarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe_data.id'), nullable=False)
    
    cpf = db.Column(db.String(11))
    cnpj = db.Column(db.String(14))
    id_estrangeiro = db.Column(db.String(50))
    nome = db.Column(db.String(255), nullable=False)
    indicador_ie = db.Column(db.String(2))  # indIEDest
    inscricao_estadual = db.Column(db.String(50))
    inscricao_suframa = db.Column(db.String(50))
    
    # Address fields
    logradouro = db.Column(db.String(255))
    numero = db.Column(db.String(20))
    complemento = db.Column(db.String(255))
    bairro = db.Column(db.String(100))
    codigo_municipio = db.Column(db.String(10))
    municipio = db.Column(db.String(100))
    uf = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    pais = db.Column(db.String(100))
    codigo_pais = db.Column(db.String(10))
    telefone = db.Column(db.String(20))
    email = db.Column(db.String(255))

class NFEItem(db.Model):
    __tablename__ = 'nfe_itens'
    
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe_data.id'), nullable=False)
    
    numero_item = db.Column(db.Integer, nullable=False)
    codigo = db.Column(db.String(60))
    codigo_ean = db.Column(db.String(20))  # cEAN
    codigo_ean_tributario = db.Column(db.String(20))  # cEANTrib
    descricao = db.Column(db.String(255))
    ncm = db.Column(db.String(10))
    cest = db.Column(db.String(10))
    cfop = db.Column(db.String(5))
    unidade_comercial = db.Column(db.String(10))
    quantidade_comercial = db.Column(db.Float)
    valor_unitario_comercial = db.Column(db.Float)
    valor_total_bruto = db.Column(db.Float)
    unidade_tributavel = db.Column(db.String(10))
    quantidade_tributavel = db.Column(db.Float)
    valor_unitario_tributavel = db.Column(db.Float)
    ind_total = db.Column(db.String(2))
    
    # ANP data for fuels and lubricants
    codigo_prod_anp = db.Column(db.String(20))
    descricao_anp = db.Column(db.String(255))
    uf_consumo = db.Column(db.String(2))
    
    # Tax data
    valor_total_tributos = db.Column(db.Float)
    
    # ICMS data
    icms_origem = db.Column(db.String(2))
    icms_cst = db.Column(db.String(3))
    icms_modbc = db.Column(db.String(2))
    icms_vbc = db.Column(db.Float)
    icms_picms = db.Column(db.Float)
    icms_vicms = db.Column(db.Float)
    
    # IPI data
    ipi_cenq = db.Column(db.String(5))
    ipi_cst = db.Column(db.String(3))
    
    # PIS data
    pis_cst = db.Column(db.String(3))
    pis_vbc = db.Column(db.Float)
    pis_ppis = db.Column(db.Float)
    pis_vpis = db.Column(db.Float)
    
    # COFINS data
    cofins_cst = db.Column(db.String(3))
    cofins_vbc = db.Column(db.Float)
    cofins_pcofins = db.Column(db.Float)
    cofins_vcofins = db.Column(db.Float)
    
    # Additional product info
    inf_ad_prod = db.Column(db.Text)

class NFETransportadora(db.Model):
    __tablename__ = 'nfe_transportadoras'
    
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe_data.id'), nullable=False)
    
    cpf = db.Column(db.String(11))
    cnpj = db.Column(db.String(14))
    nome = db.Column(db.String(255))
    inscricao_estadual = db.Column(db.String(50))
    endereco = db.Column(db.String(255))
    municipio = db.Column(db.String(100))
    uf = db.Column(db.String(2))

    placa = db.Column(db.String(10))
    uf_veiculo = db.Column(db.String(2))
    rntc = db.Column(db.String(50))

class NFEVolume(db.Model):
    __tablename__ = 'nfe_volumes'
    
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe_data.id'), nullable=False)
    
    quantidade = db.Column(db.Integer)
    especie = db.Column(db.String(100))
    marca = db.Column(db.String(100))
    numeracao = db.Column(db.String(100))
    peso_liquido = db.Column(db.Float)
    peso_bruto = db.Column(db.Float)

class NFEPagamento(db.Model):
    __tablename__ = 'nfe_pagamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe_data.id'), nullable=False)
    
    indicador = db.Column(db.String(2))  # indPag
    tipo = db.Column(db.String(3))  # tPag
    valor = db.Column(db.Float)  # vPag

class NFEDuplicata(db.Model):
    __tablename__ = 'nfe_duplicatas'
    
    id = db.Column(db.Integer, primary_key=True)
    nfe_id = db.Column(db.Integer, db.ForeignKey('nfe_data.id'), nullable=False)
    
    numero = db.Column(db.String(50))  # nDup
    data_vencimento = db.Column(db.Date)  # dVenc
    valor = db.Column(db.Float)  # vDup