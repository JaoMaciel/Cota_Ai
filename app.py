import streamlit as st
import sqlite3
import pandas as pd
import urllib.parse
import os

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title="Cota AI", page_icon="🔍", layout="wide")

# --- INTERFACE VISUAL (MODO DARK + ESTILOS) ---
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
        max-width: 850px !important;
        padding-top: 5rem !important;
    }
    
    /* BARRA DE PESQUISA */
    div[data-baseweb="input"] {
        background-color: #1E2330 !important;
        border: 1px solid #2A3347 !important;
        border-radius: 28px !important;
        padding: 4px 20px !important;
        box-shadow: 0 0 25px rgba(30, 144, 255, 0.15) !important;
    }
    
    div[data-baseweb="base-input"] {
        background-color: transparent !important;
    }
    
    div[data-baseweb="input"]:focus-within {
        border-color: #1E90FF !important;
        box-shadow: 0 0 35px rgba(30, 144, 255, 0.4) !important;
    }
    
    input {
        color: #F8FAFC !important;
        font-size: 16px !important;
        background-color: transparent !important;
    }
    
    input::placeholder {
        color: #64748B !important;
    }
    
    /* BOTÃO COTA AÍ (PRINCIPAL) */
    div.stButton > button {
        background-color: #1E90FF !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 15px !important;
        border-radius: 24px !important;
        border: none !important;
        padding: 12px 28px !important;
        width: 100% !important;
        box-shadow: 0 4px 14px rgba(30, 144, 255, 0.4);
        transition: all 0.3s ease;
    }
    
    div.stButton > button:hover {
        background-color: #58C4FF !important;
        color: #0A3D91 !important;
        box-shadow: 0 6px 20px rgba(88, 196, 255, 0.5);
    }
    
    /* Abas */
    button[data-baseweb="tab"] {
        color: #64748B !important;
        font-size: 15px !important;
        font-weight: 600 !important;
        background-color: transparent !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #58C4FF !important;
        border-bottom: 2px solid #58C4FF !important;
    }
    
    h3, p, label, .stMarkdown {
        color: #E2E8F0 !important;
    }
    
    div[data-testid="stForm"] {
        border: 1px solid #2A3347 !important;
        background-color: #131926 !important;
        border-radius: 12px !important;
        padding: 20px !important;
    }

    /* --- ESTILO DO BOTÃO ADM EM HTML (FIXO À DIREITA, COR DO FUNDO, BORDA AZUL) --- */
    .botao-adm-html {
        position: fixed;
        top: 30px;
        right: 40px;
        background-color: #0B0F19 !important; /* Mesma cor do fundo */
        color: #1E90FF !important; /* Texto Azul */
        border: 1px solid #1E90FF !important; /* Borda Fina Azul */
        padding: 6px 16px;
        font-size: 13px;
        font-weight: 600;
        border-radius: 10px;
        text-decoration: none;
        z-index: 999999;
        transition: all 0.2s ease;
    }
    .botao-adm-html:hover {
        background-color: rgba(30, 144, 255, 0.1) !important;
        color: #58C4FF !important;
        border-color: #58C4FF !important;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. BANCO DE DADOS
def inicializar_banco():
    conn = sqlite3.connect('cota_ai.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material TEXT,
            fornecedor TEXT,
            contato TEXT,
            whatsapp TEXT,
            ultimo_preco REAL,
            data_compra TEXT,
            localidade TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE historico ADD COLUMN localidade TEXT")
    except sqlite3.OperationalError:
        pass
        
    conn.commit()
    conn.close()

inicializar_banco()

# --- CONTROLE DOS ESTADOS DA TELA ---
if "mostrar_painel_admin" not in st.session_state:
    st.session_state["mostrar_painel_admin"] = False
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

# Captura cliques vindos do botão HTML através dos parâmetros da URL
query_params = st.query_params
if "action" in query_params:
    if query_params["action"] == "adm":
        st.session_state["mostrar_painel_admin"] = True
    elif query_params["action"] == "voltar":
        st.session_state["mostrar_painel_admin"] = False
    # Limpa os parâmetros da URL para evitar loops
    st.query_params.clear()
    st.rerun()

# 3. RENDERIZAÇÃO DO BOTÃO HTML (Garante cor do fundo e canto superior direito)
if st.session_state["mostrar_painel_admin"]:
    st.markdown('<a href="/?action=voltar" target="_self" class="botao-adm-html">Voltar</a>', unsafe_allow_html=True)
else:
    st.markdown('<a href="/?action=adm" target="_self" class="botao-adm-html">ADM</a>', unsafe_allow_html=True)

# 4. LOGO CENTRALIZADA E EM TAMANHO MÉDIO EQUILIBRADO
col_logo_esq, col_logo_cen, col_logo_dir = st.columns([0.8, 1.4, 0.8])
with col_logo_cen:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center; color: #1E90FF;'>COTA AI</h1>", unsafe_allow_html=True)


# --- RENDERIZAÇÃO CONDICIONAL DE TELAS ---

if st.session_state["mostrar_painel_admin"]:
    st.write("")
    st.markdown("## 🔒 Autenticação do Administrador")
    
    if not st.session_state["autenticado"]:
        with st.form("form_login_admin"):
            col_u, col_p = st.columns(2)
            with col_u:
                usuario = st.text_input("Usuário")
            with col_p:
                senha = st.text_input("Senha", type="password")
            
            botao_entrar = st.form_submit_button("Entrar no Painel")
            if botao_entrar:
                if usuario == "admin" and senha == "1234":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Usuário ou Senha incorretos.")
    else:
        st.success("Autenticado como Administrador!")
        if st.button("🔴 Fazer Logout"):
            st.session_state["autenticado"] = False
            st.session_state["mostrar_painel_admin"] = False
            st.rerun()
            
        st.write("---")
        
        sub_aba_editar, sub_aba_importar = st.tabs(["📝 Editar/Excluir Registros", "📥 Importar por Lote (Excel/CSV)"])
        
        with sub_aba_editar:
            st.markdown("### 📊 Base de Dados Completa")
            
            conn = sqlite3.connect('cota_ai.db')
            df_admin = pd.read_sql_query("SELECT * FROM historico", conn)
            conn.close()
            
            if not df_admin.empty:
                df_admin.insert(0, "Deletar", False)
                
                df_admin_editado = st.data_editor(
                    df_admin,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["id"]
                )
                
                if st.button("💾 Aplicar Alterações / Exclusões"):
                    conn = sqlite3.connect('cota_ai.db')
                    cursor = conn.cursor()
                    
                    deletar_ids = df_admin_editado[df_admin_editado["Deletar"] == True]["id"].tolist()
                    if deletar_ids:
                        cursor.execute(f"DELETE FROM historico WHERE id IN ({','.join(map(str, deletar_ids))})")
                    
                    salvar_linhas = df_admin_editado[df_admin_editado["Deletar"] == False]
                    for _, row in salvar_linhas.iterrows():
                        cursor.execute('''
                            UPDATE historico 
                            SET material=?, fornecedor=?, localidade=?, contato=?, whatsapp=?, ultimo_preco=?, data_compra=?
                            WHERE id=?
                        ''', (row['material'], row['fornecedor'], row['localidade'], row['contato'], row['whatsapp'], row['ultimo_preco'], row['data_compra'], row['id']))
                    
                    conn.commit()
                    conn.close()
                    st.success("Banco de dados sincronizado!")
                    st.rerun()
            else:
                st.info("O banco de dados está vazio.")
                
        with sub_aba_importar:
            st.markdown("### 📥 Upload de Planilhas por Lote")
            st.write("A sua planilha deve conter exatamente as seguintes colunas de cabeçalho:")
            st.code("material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra")
            
            arquivo_enviado = st.file_uploader("Selecione um arquivo Excel (.xlsx) ou CSV", type=["xlsx", "csv"])
            
            if arquivo_enviado is not None:
                try:
                    # Detecção inteligente de formato e separador
                    if arquivo_enviado.name.endswith('.csv'):
                        # Lê os primeiros caracteres para descobrir o separador correto
                        conteudo_inicio = arquivo_enviado.read(1024).decode('utf-8', errors='ignore')
                        arquivo_enviado.seek(0) # Reseta o ponteiro de leitura
                        separador = ';' if ';' in conteudo_inicio else ','
                        df_importado = pd.read_csv(arquivo_enviado, sep=separador)
                    else:
                        df_importado = pd.read_excel(arquivo_enviado)
                    
                    # Remove espaços em branco extras dos nomes das colunas (evita erros de digitação)
                    df_importado.columns = [str(c).strip().lower() for c in df_importado.columns]
                        
                    st.markdown("### 👀 Pré-visualização dos dados importados:")
                    st.dataframe(df_importado.head(5), use_container_width=True)
                    
                    colunas_necessarias = ["material", "fornecedor", "localidade", "contato", "whatsapp", "ultimo_preco", "data_compra"]
                    colunas_validas = all(col in df_importado.columns for col in colunas_necessarias)
                    
                    if colunas_validas:
                        if st.button("🚀 Confirmar e Salvar Tudo no Banco"):
                            conn = sqlite3.connect('cota_ai.db')
                            df_importado['ultimo_preco'] = pd.to_numeric(df_importado['ultimo_preco']).fillna(0.0)
                            df_importado['whatsapp'] = df_importado['whatsapp'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                            df_importado[colunas_necessarias].to_sql('historico', conn, if_exists='append', index=False)
                            conn.close()
                            st.success(f"Sucesso! {len(df_importado)} novos registros foram adicionados.")
                    else:
                        st.error("Erro nos cabeçalhos da planilha. Verifique se os nomes das colunas estão exatamente iguais aos exigidos acima.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo: {e}")

else:
    aba_busca, aba_cadastro = st.tabs(["🔍 Painel de Cotação", "➕ Novo Fornecedor"])

    with aba_busca:
        st.write("")
        col_input, col_btn = st.columns([4, 1])
        
        with col_input:
            termo_busca = st.text_input("", placeholder="O que você precisa comprar hoje?", label_visibility="collapsed")
            
        with col_btn:
            clicou_buscar = st.button("Cota Aí")

        if (clicou_buscar or termo_busca) and termo_busca:
            if "termo_atual" not in st.session_state or st.session_state["termo_atual"] != termo_busca:
                conn = sqlite3.connect('cota_ai.db')
                query = f"SELECT material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra FROM historico WHERE material LIKE '%{termo_busca}%'"
                df_resultado = pd.read_sql_query(query, conn)
                conn.close()
                
                if not df_resultado.empty:
                    df_resultado.insert(0, "Selecionar", False)
                    st.session_state["dados_busca"] = df_resultado
                    st.session_state["termo_atual"] = termo_busca
                else:
                    st.session_state["dados_busca"] = None
                    st.warning("Nenhum histórico encontrado para este material.")

        if "dados_busca" in st.session_state and st.session_state["dados_busca"] is not None:
            st.markdown("### ✨ Selecione os itens que deseja cotar:")
            
            df_editado = st.data_editor(
                st.session_state["dados_busca"],
                use_container_width=True,
                hide_index=True,
                disabled=["material", "fornecedor", "localidade", "contato", "whatsapp", "ultimo_preco", "data_compra"]
            )
            
            itens_selecionados = df_editado[df_editado["Selecionar"] == True]
            
            if not itens_selecionados.empty:
                st.write("---")
                st.markdown("### 📱 Envio de Mensagens Combinadas")
                
                agrupado = itens_selecionados.groupby("whatsapp")
                
                for whatsapp, group in agrupado:
                    fornecedor = group["fornecedor"].iloc[0]
                    contato = group["contato"].iloc[0]
                    
                    lista_materiais = ""
                    for m in group["material"].tolist():
                        lista_materiais += f"\n- *{m.strip()}*"
                    
                    texto_msg = f"Olá {contato} ({fornecedor}), tudo bem? Poderia cotar o(s) seguinte(s) item(ns) para mim?{lista_materiais}"
                    
                    chave_dinamica = f"msg_{whatsapp}_{len(group)}"
                    
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        msg_customizada = st.text_area(f"Mensagem para {fornecedor}:", value=texto_msg, height=140, key=chave_dinamica)
                    with c2:
                        texto_url = urllib.parse.quote(msg_customizada)
                        link_wp = f"https://web.whatsapp.com/send?phone={whatsapp}&text={texto_url}"
                        st.markdown(f"<br><a href='{link_wp}' target='_blank'><button style='background-color:#25D366; color:white; border:none; padding:12px 15px; border-radius:24px; font-weight:bold; cursor:pointer; width:100%;'>Zap</button></a>", unsafe_allow_html=True)

    with aba_cadastro:
        st.markdown("### 📝 Alimentar Banco de Dados")
        with st.form("form_cadastro", clear_on_submit=True):
            novo_material = st.text_input("Nome do Material/Equipamento")
            novo_fornecedor = st.text_input("Fornecedor")
            novo_localidade = st.text_input("Localidade (Cidade/UF)")
            novo_contato = st.text_input("Nome do Vendedor")
            novo_whats = st.text_input("WhatsApp (Ex: 5511999999999)")
            novo_preco = st.number_input("Último valor pago (R$)", min_value=0.0, step=0.01)
            nova_data = st.text_input("Data da compra")
            
            st.write("")
            bot_salvar = st.form_submit_button("💾 Salvar Registro")
            
            if bot_salvar:
                if novo_material and novo_fornecedor:
                    conn = sqlite3.connect('cota_ai.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO historico (material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (novo_material, novo_fornecedor, novo_localidade, novo_contato, novo_whats, novo_preco, nova_data))
                    conn.commit()
                    conn.close()
                    st.success("Dados salvos com sucesso!")
                else:
                    st.error("Preencha os campos obrigatórios (Material e Fornecedor).")