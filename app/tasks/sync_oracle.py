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
        oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient_23_4")
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

def sync_purchase_adjustments(oracle_conn, start_date):
    """Step 3.5: Sync Purchase Adjustments (Traduzindo siglas para o cálculo)"""
    logger.info("Syncing Purchase Adjustments...")
    
    query = """
        SELECT 
            adj.ID AS id,
            adj.TPEDC_ID AS purchase_order_id,
            
            CASE adj.TP_APLICACAO 
                WHEN 'P' THEN 'Pedido' 
                WHEN 'I' THEN 'Itens' 
                ELSE adj.TP_APLICACAO 
            END AS tp_apl,
            
            CASE adj.TP_DCTACR 
                WHEN 'D' THEN 'Desconto' 
                WHEN 'A' THEN 'Acréscimo' 
                ELSE adj.TP_DCTACR 
            END AS tp_dctacr1,
            
            CASE adj.TP_VLR 
                WHEN 'P' THEN 'Percentual' 
                WHEN 'V' THEN 'Valor' 
                ELSE adj.TP_VLR 
            END AS tp_vlr1,
            
            adj.VLR AS vlr1,
            TO_CHAR(pdc.EMPR_ID) AS cod_emp1,
            TO_CHAR(pdc.COD_PEDC) AS cod_pedc
            
        FROM FOCCO3I.TPEDC_DCTACR adj
        JOIN FOCCO3I.TPED_COMPRA pdc ON adj.TPEDC_ID = pdc.ID
        WHERE pdc.DT_EMIS >= :start_date
    """
    data = fetch_oracle_data(oracle_conn, query, start_date)
    if not data: 
        logger.info("No new purchase adjustments found.")
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
            WHERE emp.CNPJ != '00000000000'
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
            uf.UF AS uf,  -- CORREÇÃO 1: A coluna correta é UF (e não SIGLA)
            COALESCE(forn.CNPJ, forn.CPF) AS nvl_forn_cnpj_forn_cpf,
            REGEXP_REPLACE(COALESCE(forn.CNPJ, forn.CPF), '[^0-9]', '') AS cnpj_cpf_normalized,
            forn.DESCRICAO AS descricao,
            forn.BAIRRO AS bairro,
            
            -- Mantendo nulos por enquanto para garantir a execução
            NULL as email,
            NULL as cf_fax,
            
            -- DICA: No Focco, os telefones ficam na TTEL_FOR. 
            -- Se quiser testar depois, descomente a linha abaixo e remova o NULL acima:
            -- (SELECT MAX(DDD || TELEFONE) FROM FOCCO3I.TTEL_FOR WHERE FORN_ID = forn.ID) AS tel_ddd_tel_telefone,
            NULL as tel_ddd_tel_telefone,
            
            TO_CHAR(forn.FORN_ID) AS conta_itens 
        FROM FOCCO3I.TFORNECEDORES forn
        LEFT JOIN FOCCO3I.TCIDADES cid ON forn.CID_ID = cid.ID
        LEFT JOIN FOCCO3I.TUFS uf ON cid.UF_ID = uf.ID  -- CORREÇÃO 2: A tabela é TUFS (plural)
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
            uf.UF AS for_uf,               -- CORREÇÃO 1: Nome correto da coluna de UF
            func.NOME AS func_nome,
            pdc.POSICAO AS posicao,
            pdc.POSICAO AS posicao_hist,
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
            TO_CHAR(pdc.TP_PGTO) AS cf_pgto, -- CORREÇÃO 2: Puxando direto do pedido (a tabela TCOND_PGTO não tem vínculo direto aqui)
            moe.SIGLA AS moeped
            
        FROM FOCCO3I.TPED_COMPRA pdc
        JOIN FOCCO3I.TEMPRESAS emp ON pdc.EMPR_ID = emp.ID
        LEFT JOIN FOCCO3I.TFORNECEDORES forn ON pdc.TFOR_ID = forn.ID
        LEFT JOIN FOCCO3I.TCIDADES cid ON forn.CID_ID = cid.ID
        LEFT JOIN FOCCO3I.TUFS uf ON cid.UF_ID = uf.ID     -- CORREÇÃO 1: Tabela no plural (TUFS)
        LEFT JOIN FOCCO3I.TFUNCIONARIOS func ON pdc.FUNC_ID = func.ID
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
            pdc.DT_EMIS AS dt_emis,
            itpdc.TPEDC_ID AS purchase_order_id,
            pdc.COD_PEDC AS cod_pedc,
            TO_CHAR(emp.ID) AS cod_emp1,
            TO_CHAR(itpdc.ID) AS linha,
            NVL(item.COD_ITEM, 'N/A') AS item_id,
            itpdc.DESCRICAO_ITEM AS descricao,
            itpdc.OBS AS observacao,              -- CORREÇÃO: No item a coluna é OBS
            um.COD_UNID_MED AS unidade_medida,    -- CORREÇÃO: Tabela TUNID_MED e coluna COD_UNID_MED
            itpdc.DT_ENTREGA AS dt_entrega,
            
            -- Quantidades
            itpdc.QTDE AS quantidade,
            NVL(itpdc.QTDE_ATENDIDA, 0) AS qtde_atendida,  -- CORREÇÃO: Coluna nativa é QTDE_ATENDIDA
            NVL(itpdc.QTDE_CANC, 0) AS qtde_canc,
            NVL(itpdc.QTDE_SALDO, 0) AS qtde_saldo,        -- CORREÇÃO: Puxando o saldo já calculado pelo Focco
            NVL(itpdc.QTDE_CANC_TOLER, 0) AS qtde_canc_toler,
            NVL(itpdc.PERC_TOLER, 0) AS perc_toler,
            
            -- Valores e Impostos
            itpdc.PRECO_UNITARIO AS preco_unitario,
            itpdc.TOT_BRUTO AS total,                      -- CORREÇÃO: O Focco já grava o TOT_BRUTO (Qtd * Preço)
            NVL(itpdc.PERC_IPI, 0) AS perc_ipi,
            itpdc.TOT_LIQUIDO_IPI AS tot_liquido_ipi,      -- CORREÇÃO: Valor nativo já calculado pelo ERP
            NVL(itpdc.TOT_DESCONTOS, 0) AS tot_descontos,  -- CORREÇÃO: Nome correto da coluna
            NVL(itpdc.TOT_ACRESCIMOS, 0) AS tot_acrescimos -- CORREÇÃO: Nome correto da coluna
            
        FROM FOCCO3I.TPEDC_ITEM itpdc
        JOIN FOCCO3I.TPED_COMPRA pdc ON itpdc.TPEDC_ID = pdc.ID
        JOIN FOCCO3I.TEMPRESAS emp ON pdc.EMPR_ID = emp.ID
        LEFT JOIN FOCCO3I.TITENS_SUPRIMENTOS itsup ON itpdc.ITEM_ID = itsup.ID
        LEFT JOIN FOCCO3I.TITENS_EMPR itempr ON itsup.ITEMPR_ID = itempr.ID
        LEFT JOIN FOCCO3I.TITENS item ON itempr.ITEM_ID = item.ID
        LEFT JOIN FOCCO3I.TUNID_MED um ON itpdc.UNID_MED_ID = um.ID  -- CORREÇÃO: Tabela correta e Join correto
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
    """Step 3.6: Sync Purchase Payment Installments (Condições de Pagamento)"""
    logger.info("Syncing Purchase Installments...")
    
    query = """
        SELECT 
            pgto.ID AS id,
            pgto.TPEDC_ID AS purchase_order_id,
            TO_CHAR(pdc.COD_PEDC) AS cod_pedc,
            TO_CHAR(pdc.EMPR_ID) AS cod_emp1,
            pgto.NUM_DIAS AS num_dias,      
            pgto.DT_VCTO AS dt_vcto,
            pgto.PERC_PGTO AS perc_pgto
        FROM FOCCO3I.TPEDC_PGTO pgto
        JOIN FOCCO3I.TPED_COMPRA pdc ON pgto.TPEDC_ID = pdc.ID
        WHERE pdc.DT_EMIS >= :start_date
    """
    data = fetch_oracle_data(oracle_conn, query, start_date)
    if not data: 
        logger.info("No new installments found.")
        return

    for chunk in chunk_data(data, chunk_size=2000):
        stmt = insert(PurchasePaymentInstallment).values(chunk)
        
        on_conflict = stmt.on_conflict_do_update(
            index_elements=['id'],
            set_={
                'num_dias': stmt.excluded.num_dias,
                'dt_vcto': stmt.excluded.dt_vcto,
                'perc_pgto': stmt.excluded.perc_pgto
            }
        )
        db.session.execute(on_conflict)
        
    db.session.commit()
    logger.info(f"Successfully synced {len(data)} installments.")
    
    
    
def sync_nf_entries(oracle_conn, start_date):
    """Step 4: Sync Invoices garantindo a substituição de dados provisórios do XML"""
    logger.info("Syncing NF Entries from db...")
    
    query_entries = """
        SELECT 
            TO_CHAR(itnfe.ID) AS itnfe_id,      
            'FOCCO' AS origem,
            TO_CHAR(emp.ID) AS cod_emp1,
            TO_CHAR(pdc.COD_PEDC) AS cod_pedc,
            TO_CHAR(itpdc.LINHA) AS linha,
            TO_CHAR(nfe.NUM_NF) AS num_nf,
            nfe.DT_ENT AS dt_ent,
            nfe.OBS_CONF AS obs_conf,
            nfe.CHAVE_ACESSO_NFEL AS chave_acesso_nfel,
            TO_CHAR(itnfe.QTDE) AS qtde
        FROM FOCCO3I.TNFS_ENTRADA nfe
        JOIN FOCCO3I.TEMPRESAS emp ON nfe.EMPR_ID = emp.ID
        JOIN FOCCO3I.TITENS_NFE itnfe ON itnfe.NFE_ID = nfe.ID
        JOIN FOCCO3I.TPEDC_ITEM itpdc ON itnfe.PEDCITEM_ID = itpdc.ID
        JOIN FOCCO3I.TPED_COMPRA pdc ON itpdc.TPEDC_ID = pdc.ID
        WHERE nfe.DT_ENT >= :start_date
    """
    entries = fetch_oracle_data(oracle_conn, query_entries, start_date)
    if not entries: 
        logger.info("No NF Entries found in this window.")
        return

    notas_coletadas = list(set([row['num_nf'] for row in entries]))
    if notas_coletadas:
        db.session.query(NFEntry).filter(
            NFEntry.num_nf.in_(notas_coletadas),
            NFEntry.origem == 'XML'
        ).delete(synchronize_session=False)
        db.session.commit()
        
    chunk_count = 0
    for chunk in chunk_data(entries, chunk_size=2000):
        stmt_e = insert(NFEntry).values(chunk)
        
        on_conflict_e = stmt_e.on_conflict_do_update(
            index_elements=['itnfe_id'],  
            set_={
                'dt_ent': stmt_e.excluded.dt_ent,
                'qtde': stmt_e.excluded.qtde,
                'obs_conf': stmt_e.excluded.obs_conf,
                'chave_acesso_nfel': stmt_e.excluded.chave_acesso_nfel,
                'origem': stmt_e.excluded.origem
            }
        )
        db.session.execute(on_conflict_e)
        chunk_count += 1
        
    db.session.commit()
    logger.info(f"Successfully synced {len(entries)} precise NF entries from Oracle.")
    

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