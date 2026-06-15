import os
import logging
import sys
import oracledb
from datetime import datetime
from dateutil.relativedelta import relativedelta
from sqlalchemy.dialects.postgresql import insert
from pathlib import Path
from dotenv import load_dotenv

# --- 1. PATH FIX FOR SCRIPT EXECUTION ---
current_file = Path(__file__).resolve()
repo_root = current_file.parents[2]
sys.path.insert(0, str(repo_root))

# --- 2. NOW IMPORT FLASK APP AND MODELS ---
# Added Supplier to the imports
from app import create_app, db
from app.models import (
    Company, PurchaseAdjustment, PurchasePaymentInstallment, PurchasePaymentInstallment, Supplier, PurchaseOrder, PurchaseItem, 
    NFEntry
)

# --- 3. CONFIGURATION & ENV VARIABLES ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

dotenv_path = repo_root / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path)
    logger.info(f"Loaded environment from {dotenv_path}")
else:
    load_dotenv()
    logger.info("Loaded default environment variables")
    
ORACLE_USER = os.getenv('ORACLE_USER', 'your_oracle_user')
ORACLE_PASSWORD = os.getenv('ORACLE_PASSWORD', 'your_oracle_password')
ORACLE_DSN = os.getenv('ORACLE_DSN', 'your_oracle_host:1521/your_service_name')

# --- 4. HELPER FUNCTIONS ---
def get_oracle_connection():
    """Establish connection to Oracle DB."""
    try:
        oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_19_21")
    except Exception as e:
        logger.warning(f"Thick mode init warning (safe to ignore if already init): {e}")

    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=ORACLE_DSN)

def fetch_oracle_data(connection, query, start_date=None):
    """Executes a query and returns a list of dictionaries matching the columns."""
    cursor = connection.cursor()
    if start_date:
        cursor.execute(query, start_date=start_date)
    else:
        cursor.execute(query)
    columns = [col[0].lower() for col in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    cursor.close()
    return data

def chunk_data(data_list, chunk_size=2000):
    """Yield successive chunks from a list to avoid DB parameter limits."""
    for i in range(0, len(data_list), chunk_size):
        yield data_list[i:i + chunk_size]

# --- 5. SYNC FUNCTIONS ---
def sync_purchase_adjustments(oracle_conn, start_date):
    """Step 3.5: Sync Purchase Adjustments (Discounts/Additions)"""
    logger.info("Syncing Purchase Adjustments...")
    
    # We join TPED_COMPRA to get the cod_emp1 (EMPR_ID) and cod_pedc
    query = """
        SELECT 
            adj.ID AS id,
            adj.TPEDC_ID AS purchase_order_id,
            adj.TP_APLICACAO AS tp_apl,
            adj.TP_DCTACR AS tp_dctacr1,
            adj.TP_VLR AS tp_vlr1,
            adj.VLR AS vlr1,
            TO_CHAR(pdc.EMPR_ID) AS cod_emp1,
            TO_CHAR(pdc.COD_PEDC) AS cod_pedc
        FROM FOCCO3I.TPEDC_DCTACR adj
        JOIN FOCCO3I.TPED_COMPRA pdc ON adj.TPEDC_ID = pdc.ID
        WHERE pdc.DT_EMIS >= :start_date
    """
    data = fetch_oracle_data(oracle_conn, query, start_date)
    if not data: 
        return

    chunk_count = 0
    for chunk in chunk_data(data, chunk_size=2000):
        stmt = insert(PurchaseAdjustment).values(chunk)
        
        on_conflict = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                'tp_apl': stmt.excluded.tp_apl,
                'tp_dctacr1': stmt.excluded.tp_dctacr1,
                'tp_vlr1': stmt.excluded.tp_vlr1,
                'vlr1': stmt.excluded.vlr1
            }
        )
        db.session.execute(on_conflict)
        chunk_count += 1
        
    db.session.commit()
    logger.info(f"Successfully synced {len(data)} purchase adjustments across {chunk_count} batches.")

def sync_companies(oracle_conn):    
    """Step 1: Sync Companies (Warehouses) based strictly on TEMPRESAS DDL"""
    logger.info("Syncing Companies...")
    query = """
            SELECT 
                TO_CHAR(emp.ID) AS cod_emp1, 
                emp.RAZAO_SOCIAL AS name,
                emp.CNPJ AS cnpj,
                emp.NOME_FAN AS fantasy_name,
                emp.ENDERECO AS address,
                emp.BAIRRO AS neighborhood,
                cid.CIDADE AS city,         
                TO_CHAR(emp.CEP) AS zip_code,
                emp.INSEST AS inscricao_estadual
            FROM FOCCO3I.TEMPRESAS emp
            LEFT JOIN FOCCO3I.TCIDADES cid ON emp.CID_ID = cid.ID
        """
        
    data = fetch_oracle_data(oracle_conn, query)
    if not data: return

    stmt = insert(Company).values(data)
    on_conflict = stmt.on_conflict_do_update(
        index_elements=['cod_emp1'],
        set_={
            'name': stmt.excluded.name,
            'cnpj': stmt.excluded.cnpj,
            'fantasy_name': stmt.excluded.fantasy_name,
            'address': stmt.excluded.address,
            'neighborhood': stmt.excluded.neighborhood,
            'zip_code': stmt.excluded.zip_code,
            'inscricao_estadual': stmt.excluded.inscricao_estadual,
            'updated_at': datetime.now()
        }
    )
    db.session.execute(on_conflict)
    db.session.commit()
    logger.info(f"Successfully synced {len(data)} companies.")

def sync_suppliers(oracle_conn):
    """Step 1.5: Sync Suppliers com todos os campos de contato e UF"""
    logger.info("Syncing Suppliers...")
    query = """
        SELECT 
            forn.ID AS id_for,
            TO_CHAR(forn.COD_FOR) AS cod_for,
            TO_CHAR(forn.TIPO) AS tip_forn,
            forn.INSC_EST AS insc_est,
            forn.INSC_MUN AS insc_mun,
            forn.ENDERECO AS endereco,
            TO_CHAR(forn.CEP) AS cep,
            cid.CIDADE AS cidade,
            uf.SIGLA AS uf,
            COALESCE(forn.CNPJ, forn.CPF) AS nvl_forn_cnpj_forn_cpf,
            REGEXP_REPLACE(COALESCE(forn.CNPJ, forn.CPF), '[^0-9]', '') AS cnpj_cpf_normalized,
            forn.DESCRICAO AS descricao,
            forn.BAIRRO AS bairro,
            -- Buscando contatos genéricos da TCONTATOS
            (SELECT MAX(EMAIL) FROM FOCCO3I.TCONTATOS WHERE FORN_ID = forn.ID) AS email,
            (SELECT MAX(FONE) FROM FOCCO3I.TCONTATOS WHERE FORN_ID = forn.ID) AS tel_ddd_tel_telefone,
            (SELECT MAX(FAX) FROM FOCCO3I.TCONTATOS WHERE FORN_ID = forn.ID) AS cf_fax,
            -- O Focco usa conta_ctb_id ou similar. Se não houver correspondência exata, mantemos nulo
            TO_CHAR(forn.FORN_ID) AS conta_itens 
        FROM FOCCO3I.TFORNECEDORES forn
        LEFT JOIN FOCCO3I.TCIDADES cid ON forn.CID_ID = cid.ID
        LEFT JOIN FOCCO3I.TUF uf ON cid.UF_ID = uf.ID
    """
    data = fetch_oracle_data(oracle_conn, query)
    if not data: return

    for chunk in chunk_data(data, chunk_size=2000):
        stmt = insert(Supplier).values(chunk)
        on_conflict = stmt.on_conflict_do_update(
            index_elements=['id_for'],
            set_={
                'descricao': stmt.excluded.descricao,
                'cnpj_cpf_normalized': stmt.excluded.cnpj_cpf_normalized,
                'uf': stmt.excluded.uf,
                'email': stmt.excluded.email,
                'tel_ddd_tel_telefone': stmt.excluded.tel_ddd_tel_telefone,
                'cf_fax': stmt.excluded.cf_fax,
                'conta_itens': stmt.excluded.conta_itens,
                'endereco': stmt.excluded.endereco,
                'bairro': stmt.excluded.bairro,
                'cep': stmt.excluded.cep,
                'cidade': stmt.excluded.cidade
            }
        )
        db.session.execute(on_conflict)
    db.session.commit()
    logger.info(f"Successfully synced {len(data)} suppliers.")
    



def sync_purchase_orders(oracle_conn, start_date):
    """Step 2: Sync Purchase Orders com totais, transportadora e pgto"""
    logger.info(f"Syncing Purchase Orders since {start_date.strftime('%Y-%m-%d')}...")
    query = """
        SELECT 
            pdc.ID AS id,
            pdc.COD_PEDC AS cod_pedc,
            pdc.DT_EMIS AS dt_emis,
            TO_CHAR(emp.ID) AS cod_emp1, 
            NVL(forn.ID, 0) AS fornecedor_id,
            forn.DESCRICAO AS fornecedor_descricao,
            uf.SIGLA AS for_uf,
            func.NOME AS func_nome,
            pdc.POSICAO AS posicao,
            pdc.POSICAO AS posicao_hist, -- Usando a atual como histórico inicial
            pdc.OBSERVACAO AS observacao,
            pdc.CONTATO AS contato,
            TO_CHAR(pdc.NUM_TALAO) AS num_talao,
            
            -- Totais e Impostos
            pdc.VLR_TOTAL AS total_pedido_com_ipi,
            pdc.TOT_BRUTO AS total_bruto,
            pdc.TOT_LIQUIDO AS total_liquido,
            pdc.TOT_LIQUIDO_IPI AS total_liquido_ipi,
            pdc.VLR_ICMS_ST AS vlr_icms_st,
            
            -- Transportadora e Redespacho
            pdc.VLR_FRETE_TRA AS vlr_frete_tra,
            pdc.TP_FRETE_TRA AS tp_frete_tra,
            pdc.TP_VLR_FRETE_TRA AS tp_vlr_frete_tra,
            pdc.VLR_FRETE_RED AS vlr_frete_red,
            pdc.TP_FRETE_RED AS tp_frete_red,
            pdc.TP_VLR_FRETE_RED AS tp_vlr_frete_red,
            
            -- Condição Pagamento e Moeda
            cond.DESCRICAO AS cf_pgto,
            moe.SIGLA AS moeped
            
        FROM FOCCO3I.TPED_COMPRA pdc
        JOIN FOCCO3I.TEMPRESAS emp ON pdc.EMPR_ID = emp.ID
        LEFT JOIN FOCCO3I.TFORNECEDORES forn ON pdc.TFOR_ID = forn.ID
        LEFT JOIN FOCCO3I.TCIDADES cid ON forn.CID_ID = cid.ID
        LEFT JOIN FOCCO3I.TUF uf ON cid.UF_ID = uf.ID
        LEFT JOIN FOCCO3I.TFUNCIONARIOS func ON pdc.FUNC_ID = func.ID
        LEFT JOIN FOCCO3I.TCOND_PGTO cond ON pdc.TCONDPGTO_ID = cond.ID
        LEFT JOIN FOCCO3I.TMOEDAS moe ON pdc.MOE_ID = moe.ID
        WHERE pdc.DT_EMIS >= :start_date
    """
    data = fetch_oracle_data(oracle_conn, query, start_date)
    if not data: return

    for chunk in chunk_data(data, chunk_size=2000):
        stmt = insert(PurchaseOrder).values(chunk)
        on_conflict = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                'posicao': stmt.excluded.posicao,
                'observacao': stmt.excluded.observacao,
                'total_pedido_com_ipi': stmt.excluded.total_pedido_com_ipi,
                'total_bruto': stmt.excluded.total_bruto,
                'total_liquido': stmt.excluded.total_liquido,
                'total_liquido_ipi': stmt.excluded.total_liquido_ipi,
                'contato': stmt.excluded.contato,
                'cf_pgto': stmt.excluded.cf_pgto,
                'vlr_icms_st': stmt.excluded.vlr_icms_st,
                'vlr_frete_tra': stmt.excluded.vlr_frete_tra,
                'tp_frete_tra': stmt.excluded.tp_frete_tra,
                'vlr_frete_red': stmt.excluded.vlr_frete_red,
                'posicao_hist': stmt.excluded.posicao_hist
            }
        )
        db.session.execute(on_conflict)
    db.session.commit()
    logger.info(f"Successfully synced {len(data)} purchase orders.")
    
    
def sync_purchase_items(oracle_conn, start_date):
    """Step 3: Sync Purchase Items com Unidades, Prazos e Impostos"""
    logger.info("Syncing Purchase Items...")
    query = """
        SELECT 
            itpdc.ID AS id,
            itpdc.TPEDC_ID AS purchase_order_id,
            pdc.COD_PEDC AS cod_pedc,
            TO_CHAR(emp.ID) AS cod_emp1,
            TO_CHAR(itpdc.ID) AS linha,
            NVL(item.COD_ITEM, 'N/A') AS item_id,
            itpdc.DESCRICAO_ITEM AS descricao,
            itpdc.OBSERVACAO AS observacao,
            um.SIGLA AS unidade_medida,
            itpdc.DT_ENTREGA AS dt_entrega,
            
            -- Quantidades
            itpdc.QTDE AS quantidade,
            NVL(itpdc.QTDE_REC, 0) AS qtde_atendida,
            NVL(itpdc.QTDE_CANC, 0) AS qtde_canc,
            (itpdc.QTDE - NVL(itpdc.QTDE_REC, 0) - NVL(itpdc.QTDE_CANC, 0)) AS qtde_saldo,
            itpdc.QTDE_CANC_TOLER AS qtde_canc_toler,
            itpdc.PERC_TOLER AS perc_toler,
            
            -- Valores e Impostos
            itpdc.PRECO_UNITARIO AS preco_unitario,
            (itpdc.QTDE * itpdc.PRECO_UNITARIO) AS total,
            itpdc.PERC_IPI AS perc_ipi,
            -- Cálculo seguro para Total Líquido IPI caso não haja coluna nativa
            ((itpdc.QTDE * itpdc.PRECO_UNITARIO) * (1 + NVL(itpdc.PERC_IPI,0)/100)) AS tot_liquido_ipi,
            NVL(itpdc.VLR_DESC, 0) AS tot_descontos,
            NVL(itpdc.VLR_ACRESC, 0) AS tot_acrescimos
            
        FROM FOCCO3I.TPEDC_ITEM itpdc
        JOIN FOCCO3I.TPED_COMPRA pdc ON itpdc.TPEDC_ID = pdc.ID
        JOIN FOCCO3I.TEMPRESAS emp ON pdc.EMPR_ID = emp.ID
        LEFT JOIN FOCCO3I.TITENS_SUPRIMENTOS itsup ON itpdc.ITEM_ID = itsup.ID
        LEFT JOIN FOCCO3I.TITENS_EMPR itempr ON itsup.ITEMPR_ID = itempr.ID
        LEFT JOIN FOCCO3I.TITENS item ON itempr.ITEM_ID = item.ID
        LEFT JOIN FOCCO3I.TUM um ON itpdc.UM_ID = um.ID
        WHERE pdc.DT_EMIS >= :start_date
    """
    data = fetch_oracle_data(oracle_conn, query, start_date)
    if not data: return

    for chunk in chunk_data(data, chunk_size=2000):
        stmt = insert(PurchaseItem).values(chunk)
        on_conflict = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                'quantidade': stmt.excluded.quantidade,
                'preco_unitario': stmt.excluded.preco_unitario,
                'total': stmt.excluded.total,
                'dt_entrega': stmt.excluded.dt_entrega,
                'qtde_atendida': stmt.excluded.qtde_atendida,
                'qtde_canc': stmt.excluded.qtde_canc,
                'qtde_saldo': stmt.excluded.qtde_saldo,
                'perc_ipi': stmt.excluded.perc_ipi,
                'tot_liquido_ipi': stmt.excluded.tot_liquido_ipi,
                'tot_descontos': stmt.excluded.tot_descontos,
                'tot_acrescimos': stmt.excluded.tot_acrescimos,
                'observacao': stmt.excluded.observacao
            }
        )
        db.session.execute(on_conflict)
    db.session.commit()
    logger.info(f"Successfully synced {len(data)} purchase items.")
    
    


def sync_purchase_installments(oracle_conn, start_date):
    """Step 3.6: Sync Purchase Payment Installments (Parcelas)"""
    logger.info("Syncing Purchase Installments...")
    query = """
        SELECT 
            venc.ID AS id,
            venc.TPEDC_ID AS purchase_order_id,
            TO_CHAR(pdc.COD_PEDC) AS cod_pedc,
            TO_CHAR(pdc.EMPR_ID) AS cod_emp1,
            venc.PARCELA AS nr_parc,       -- Ou o nome do seu campo no modelo (ex: installment_number)
            venc.DT_VCTO AS dt_vcto,
            venc.VLR_PARC AS vlr_parc,
            venc.PERC_PARC AS perc_parc
        FROM FOCCO3I.TPEDC_VENC venc
        JOIN FOCCO3I.TPED_COMPRA pdc ON venc.TPEDC_ID = pdc.ID
        WHERE pdc.DT_EMIS >= :start_date
    """
    data = fetch_oracle_data(oracle_conn, query, start_date)
    if not data: return

    for chunk in chunk_data(data, chunk_size=2000):
        stmt = insert(PurchasePaymentInstallment).values(chunk)
        
        # O ID na tabela TPEDC_VENC é a primary key ideal
        on_conflict = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                'dt_vcto': stmt.excluded.dt_vcto,
                'vlr_parc': stmt.excluded.vlr_parc,
                'perc_parc': stmt.excluded.perc_parc
            }
        )
        db.session.execute(on_conflict)
    db.session.commit()
    logger.info(f"Successfully synced {len(data)} installments.")
    
    
    
def sync_nf_entries(oracle_conn, start_date):
    """Step 4: Sync Invoices directly into NFEntry"""
    logger.info("Syncing NF Entries...")
    
    # Focco uses CHAVE_NFE instead of CHAVE_ACESSO_NFEL in the base header table usually
    # If your specific installation uses CHAVE_ACESSO_NFEL, swap nfe.CHAVE_NFE below.
    query_entries = """
        SELECT 
            TO_CHAR(emp.ID) AS cod_emp1,
            pdc.COD_PEDC AS cod_pedc,
            TO_CHAR(itpdc.ID) AS linha,
            nfe.NUM_NF AS num_nf,
            nfe.DT_ENT AS dt_ent,
            TO_CHAR(itnfe.QTDE) AS qtde,
            nfe.OBS_CONF AS obs_conf,
            nfe.CHAVE_ACESSO_NFEL AS chave_acesso_nfel
        FROM FOCCO3I.TITENS_NFE itnfe
        JOIN FOCCO3I.TNFS_ENTRADA nfe ON itnfe.NFE_ID = nfe.ID
        JOIN FOCCO3I.TPEDC_ITEM itpdc ON itnfe.PEDCITEM_ID = itpdc.ID
        JOIN FOCCO3I.TPED_COMPRA pdc ON itpdc.TPEDC_ID = pdc.ID
        JOIN FOCCO3I.TEMPRESAS emp ON pdc.EMPR_ID = emp.ID
        WHERE nfe.DT_ENT >= :start_date
    """
    entries = fetch_oracle_data(oracle_conn, query_entries, start_date)
    if not entries: return

    chunk_count = 0
    for chunk in chunk_data(entries, chunk_size=2000):
        stmt_e = insert(NFEntry).values(chunk)
        
        on_conflict_e = stmt_e.on_conflict_do_update(
            constraint='uq_nf_entry',
            set_={
                'dt_ent': stmt_e.excluded.dt_ent,
                'qtde': stmt_e.excluded.qtde,
                'obs_conf': stmt_e.excluded.obs_conf,
                'chave_acesso_nfel': stmt_e.excluded.chave_acesso_nfel
            }
        )
        db.session.execute(on_conflict_e)
        chunk_count += 1
        
    db.session.commit()
    logger.info(f"Successfully synced {len(entries)} NF Entries across {chunk_count} batches.")

def run_sync():
    """Main execution function."""
    app = create_app()
    with app.app_context():
        try:
            logger.info("Starting Oracle to Postgres Sync...")
            oracle_conn = get_oracle_connection()
            
            # Calculate the window (last 1 month)
            start_date = datetime.now() - relativedelta(months=1)
            
            sync_companies(oracle_conn)
            sync_suppliers(oracle_conn)
            sync_purchase_orders(oracle_conn, start_date)
            sync_purchase_items(oracle_conn, start_date)
            sync_nf_entries(oracle_conn, start_date)
            sync_purchase_adjustments(oracle_conn, start_date)
            sync_purchase_installments(oracle_conn, start_date)
            
            oracle_conn.close()
            logger.info("Sync completed successfully.")
            
        except Exception as e:
            logger.error(f"Error during synchronization: {str(e)}")
            db.session.rollback()

if __name__ == '__main__':
    run_sync()