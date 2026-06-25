import streamlit as st
import sqlite3
import pandas as pd
import urllib.parse
import os
import unicodedata

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Cota AI", page_icon="🔍", layout="wide")

# --- INTERFACE VISUAL (MODO DARK + ESTILOS PREMIUM) ---
st.markdown("""
    <style>
    /* Fundo Dark Geral */
    .stApp {
        background-color: #0B0F19 !important;
    }
    
    /* Remove elementos nativos */
    #MainMenu, header, footer { visibility: hidden; }
    
    /* Centralizar container principal */
    .block-container {
        max-width: 950px !important;
        padding-top: 3rem !important;
    }
    
    /* BARRA DE PESQUISA ESTILIZADA */
    div[data-baseweb="input"] {
        background-color: #1E2330 !important;
        border: 1px solid #2A3347 !important;
        border-radius: 28px !important;
        padding: 4px 20px !important;
        box-shadow: 0 0 20px rgba(30, 144, 255, 0.1) !important;
    }
    
    div[data-baseweb="base-input"] {
        background-color: transparent !important;
    }
    
    div[data-baseweb="input"]:focus-within {
        border-color: #1E90FF !important;
        box-shadow: 0 0 30px rgba(30, 144, 255, 0.3) !important;
    }
    
    input {
        color: #F8FAFC !important;
        font-size: 16px !important;
    }

    /* BOTÕES AZUIS */
    div.stButton > button {
        background-color: #1E90FF !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        border-radius: 24px !important;
        border: none !important;
        padding: 10px 25px !important;
        box-shadow: 0 4px 14px rgba(30, 144, 255, 0.3);
        transition: all 0.3s ease;
        width: 100%;
    }
    
    div.stButton > button:hover {
        background-color: #58C4FF !important;
        transform: translateY(-2px);
    }

    /* Estilo das Abas */
    button[data-baseweb="tab"] {
        color: #64748B !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #58C4FF !important;
        border-bottom: 2px solid #58C4FF !important;
    }

    h1, h2, h3, p, label, .stMarkdown {
        color: #E2E8F0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. FUNÇÕES DE APOIO (INTELIGÊNCIA E BANCO)
def inicializar_banco():
    conn = sqlite3.connect('cota_ai.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material TEXT, fornecedor TEXT, localidade TEXT, 
            contato TEXT, whatsapp TEXT, ultimo_preco REAL, data_compra TEXT
        )
    ''')
    conn.commit()
    conn.close()

def remover_acentos(texto):
    if not isinstance(texto, str): return ""
    # Transforma Á -> A, Ç -> C e remove variações de acentos
    texto_limpo = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto_limpo.lower().strip()

inicializar_banco()

# Estados da sessão
if "dados_busca" not in st.session_state: st.session_state["dados_busca"] = None
if "termo_atual" not in st.session_state: st.session_state["termo_atual"] = ""
if "autenticado" not in st.session_state: st.session_state["autenticado"] = False

# 3. LAYOUT DO TOPO (LOGO CENTRALIZADA)
col_l1, col_l2, col_l3 = st.columns([1, 1.8, 1])
with col_l2:
    # Tenta carregar os nomes possíveis da sua logo
    logo_path = "logo.png" if os.path.exists("logo.png") else "image_40eed9.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center; color: #1E90FF; margin-bottom:0;'>COTA AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-style: italic; margin-top:0;'>A inteligência por trás das suas compras.</p>", unsafe_allow_html=True)

st.write("---")

# 4. NAVEGAÇÃO POR ABAS
aba_busca, aba_cadastro, aba_admin = st.tabs(["🔍 Painel de Cotação", "➕ Novo Fornecedor", "🔒 Administrador"])

# ==========================================
# ABA DE BUSCA (A LÓGICA INTELIGENTE)
# ==========================================
with aba_busca:
    st.write("")
    col_in, col_bt = st.columns([4, 1])
    
    with col_in:
        termo_busca = st.text_input("", placeholder="O que você precisa comprar hoje? (Ex: aco, valvula, plastico)", label_visibility="collapsed")
    with col_bt:
        clicou = st.button("Cota Aí")

    if (clicou or termo_busca) and termo_busca:
        termo_limpo = remover_acentos(termo_busca)
        
        if st.session_state["termo_atual"] != termo_limpo:
            conn = sqlite3.connect('cota_ai.db')
            df_completo = pd.read_sql_query("SELECT * FROM historico", conn)
            conn.close()
            
            if not df_completo.empty:
                # Filtro Inteligente: Limpa o banco temporariamente para comparar com o termo limpo
                mask = df_completo['material'].apply(remover_acentos).str.contains(termo_limpo, na=False)
                df_resultado = df_completo[mask].copy()
                
                if not df_resultado.empty:
                    df_resultado.insert(0, "Selecionar", False)
                    st.session_state["dados_busca"] = df_resultado
                    st.session_state["termo_atual"] = termo_limpo
                else:
                    st.session_state["dados_busca"] = None
                    st.warning("Nenhum histórico encontrado para este termo.")
            else:
                st.info("O banco de dados está vazio.")

    if st.session_state["dados_busca"] is not None:
        st.markdown("### ✨ Itens encontrados no histórico:")
        df_editado = st.data_editor(
            st.session_state["dados_busca"],
            use_container_width=True,
            hide_index=True,
            column_config={
                "id": None, # Esconde o ID
                "ultimo_preco": st.column_config.NumberColumn("Último Preço", format="R$ %,.2f"),
                "Selecionar": st.column_config.CheckboxColumn("Cotar?", default=False)
            },
            disabled=["material", "fornecedor", "localidade", "contato", "whatsapp", "ultimo_preco", "data_compra"]
        )
        
        # Lógica de agrupamento para WhatsApp (Opcional: você pode adicionar o botão de Zap aqui se desejar)
        selecionados = df_editado[df_editado["Selecionar"] == True]
        if not selecionados.empty:
             if st.button("📱 Abrir WhatsApp com Selecionados"):
                st.info("Funcionalidade de link de WhatsApp pode ser integrada aqui.")

# ==========================================
# ABA DE CADASTRO
# ==========================================
with aba_cadastro:
    st.markdown("### 📝 Cadastrar Compra Manual")
    with st.form("form_cad", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            m = st.text_input("Material *")
            f = st.text_input("Fornecedor *")
            l = st.text_input("Localidade")
        with c2:
            w = st.text_input("WhatsApp (DDD+Número)")
            p = st.number_input("Preço (R$)", min_value=0.0, format="%.2f")
            d = st.text_input("Data (DD/MM/AA)")
        
        if st.form_submit_button("Salvar Registro"):
            if m and f:
                conn = sqlite3.connect('cota_ai.db')
                conn.execute("INSERT INTO historico (material, fornecedor, localidade, whatsapp, ultimo_preco, data_compra) VALUES (?,?,?,?,?,?)", 
                             (m.upper(), f.upper(), l.upper(), w, p, d))
                conn.commit()
                conn.close()
                st.success("Salvo com sucesso!")
                st.session_state["termo_atual"] = "" # Limpa busca para atualizar
            else:
                st.error("Preencha Material e Fornecedor.")

# ==========================================
# ABA ADMINISTRADOR
# ==========================================
with aba_admin:
    if not st.session_state["autenticado"]:
        senha = st.text_input("Senha de Acesso", type="password")
        if st.button("Entrar"):
            if senha == "admin123": # Altere sua senha aqui
                st.session_state["autenticado"] = True
                st.rerun()
            else: st.error("Senha incorreta.")
    else:
        st.subheader("⚙️ Gestão de Dados")
        conn = sqlite3.connect('cota_ai.db')
        df_adm = pd.read_sql_query("SELECT * FROM historico", conn)
        conn.close()
        
        st.data_editor(df_adm, use_container_width=True, hide_index=True, 
                       column_config={"ultimo_preco": st.column_config.NumberColumn(format="R$ %,.2f")})
        
        if st.button("Sair do Painel ADM"):
            st.session_state["autenticado"] = False
            st.rerun()