import streamlit as st
import pandas as pd
import urllib.parse
import os
import time
import base64
import hashlib
import unicodedata
from datetime import datetime
from sqlalchemy import create_engine, text, bindparam

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

    /* --- ESTILO DO BOTÃO ADM EM HTML --- */
    .botao-adm-html {
        position: fixed;
        top: 30px;
        right: 40px;
        background-color: #0B0F19 !important;
        color: #1E90FF !important;
        border: 1px solid #1E90FF !important;
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

    /* --- SPLASH DE CARREGAMENTO --- */
    .splash-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        height: 75vh;
    }
    .splash-logo {
        opacity: 0;
        transform: scale(0.85);
        animation: fadeInScale 1.6s ease forwards;
        max-width: 340px;
        width: 100%;
    }
    @keyframes fadeInScale {
        0%   { opacity: 0;   transform: scale(0.85); }
        60%  { opacity: 1;   transform: scale(1.03); }
        100% { opacity: 1;   transform: scale(1); }
    }

    /* --- CARD DE LOGIN / CADASTRO --- */
    .login-card-wrapper {
        display: flex;
        justify-content: center;
        margin-top: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. BANCO DE DADOS (Postgres via Supabase)

@st.cache_resource
def get_engine():
    """Cria (uma única vez por sessão do servidor) a conexão com o Postgres do Supabase.
    A string de conexão vem dos Secrets do Streamlit — nunca fica exposta no código/GitHub."""
    if "SUPABASE_URL" not in st.secrets:
        st.error(
            "Não encontrei a variável SUPABASE_URL nos Secrets. "
            "Configure em Settings > Secrets (Streamlit Cloud) ou no arquivo "
            ".streamlit/secrets.toml (ao rodar localmente)."
        )
        st.stop()
    try:
        return create_engine(st.secrets["SUPABASE_URL"], pool_pre_ping=True)
    except Exception as e:
        st.error(f"Erro ao conectar no banco de dados: {e}")
        st.stop()


def inicializar_banco():
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS historico (
                id SERIAL PRIMARY KEY,
                material TEXT,
                fornecedor TEXT,
                contato TEXT,
                whatsapp TEXT,
                ultimo_preco REAL,
                data_compra TEXT,
                localidade TEXT
            )
        '''))

        # Tabela de usuários comuns (login/cadastro)
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                nome_completo TEXT,
                empresa TEXT,
                funcao TEXT,
                avatar TEXT,
                email TEXT,
                senha_hash TEXT,
                data_criacao TEXT
            )
        '''))

        # Tabela que guarda automaticamente o que cada usuário pediu para cotar
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS solicitacoes (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER,
                termo_buscado TEXT,
                data_hora TEXT
            )
        '''))

inicializar_banco()

# --- FUNÇÕES AUXILIARES ---
def normalizar_texto(texto):
    if not isinstance(texto, str):
        return ""
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII').strip().lower()

def hash_senha(senha):
    """Nunca salvamos a senha em texto puro — apenas o hash dela."""
    return hashlib.sha256(senha.encode()).hexdigest()

def carregar_logo_base64():
    if os.path.exists("logo.png"):
        with open("logo.png", "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

AVATARES = ["🧑‍💼", "👩‍💼", "🧑‍🔧", "👷", "🧑‍💻", "👩‍🔧", "🧑‍🏭", "👨‍💼"]

# --- CONTROLE DOS ESTADOS DA TELA ---
if "mostrar_painel_admin" not in st.session_state:
    st.session_state["mostrar_painel_admin"] = False
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "splash_mostrado" not in st.session_state:
    st.session_state["splash_mostrado"] = False
if "usuario_logado" not in st.session_state:
    st.session_state["usuario_logado"] = None
if "tela_auth" not in st.session_state:
    st.session_state["tela_auth"] = "login"

# Captura cliques vindos do botão HTML através dos parâmetros da URL
query_params = st.query_params
if "action" in query_params:
    if query_params["action"] == "adm":
        st.session_state["mostrar_painel_admin"] = True
    elif query_params["action"] == "voltar":
        st.session_state["mostrar_painel_admin"] = False
    st.query_params.clear()
    st.rerun()

# 3. SPLASH DE CARREGAMENTO (aparece uma única vez por sessão)
if not st.session_state["splash_mostrado"]:
    logo_b64 = carregar_logo_base64()
    if logo_b64:
        conteudo_logo = f'<img class="splash-logo" src="data:image/png;base64,{logo_b64}">'
    else:
        conteudo_logo = '<h1 class="splash-logo" style="color:#1E90FF; font-size:52px; text-align:center;">COTA AI</h1>'

    st.markdown(f"""
        <div class="splash-container">
            {conteudo_logo}
        </div>
    """, unsafe_allow_html=True)

    time.sleep(1.8)
    st.session_state["splash_mostrado"] = True
    st.rerun()

# 4. RENDERIZAÇÃO DO BOTÃO HTML (ADM continua acessível de qualquer tela)
if st.session_state["mostrar_painel_admin"]:
    st.markdown('<a href="/?action=voltar" target="_self" class="botao-adm-html">Voltar</a>', unsafe_allow_html=True)
else:
    st.markdown('<a href="/?action=adm" target="_self" class="botao-adm-html">ADM</a>', unsafe_allow_html=True)

# 5. LOGO CENTRALIZADA
col_logo_esq, col_logo_cen, col_logo_dir = st.columns([0.8, 1.4, 0.8])
with col_logo_cen:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center; color: #1E90FF;'>COTA AI</h1>", unsafe_allow_html=True)


# --- TELAS DE LOGIN E CADASTRO DE USUÁRIO ---
def tela_login():
    col_a, col_b, col_c = st.columns([1, 1.3, 1])
    with col_b:
        st.markdown("<h3 style='text-align:center;'>Entrar</h3>", unsafe_allow_html=True)
        with st.form("form_login_usuario"):
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            entrar = st.form_submit_button("Entrar")

            if entrar:
                engine = get_engine()
                with engine.begin() as conn:
                    resultado = conn.execute(
                        text("SELECT id, nome_completo, avatar FROM usuarios WHERE email = :email AND senha_hash = :senha"),
                        {"email": email.strip().lower(), "senha": hash_senha(senha)}
                    ).fetchone()

                if resultado:
                    st.session_state["usuario_logado"] = {
                        "id": resultado[0],
                        "nome": resultado[1],
                        "avatar": resultado[2] or "🧑‍💼"
                    }
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

        st.markdown("<p style='text-align:center;'>Não tem conta?</p>", unsafe_allow_html=True)
        if st.button("Criar cadastro", use_container_width=True, key="btn_ir_cadastro"):
            st.session_state["tela_auth"] = "cadastro"
            st.rerun()


def tela_cadastro():
    col_a, col_b, col_c = st.columns([1, 1.3, 1])
    with col_b:
        st.markdown("<h3 style='text-align:center;'>Criar cadastro</h3>", unsafe_allow_html=True)
        with st.form("form_cadastro_usuario"):
            avatar = st.selectbox("Escolha um avatar", AVATARES, index=0)
            nome_completo = st.text_input("Nome completo")
            nome_empresa = st.text_input("Nome da empresa")
            funcao = st.text_input("Função na empresa")
            email = st.text_input("E-mail")
            senha = st.text_input("Senha", type="password")
            confirmar_senha = st.text_input("Confirmar senha", type="password")

            criar = st.form_submit_button("Continuar para login")

            if criar:
                if not nome_completo or not email or not senha:
                    st.error("Preencha ao menos nome, e-mail e senha.")
                elif senha != confirmar_senha:
                    st.error("As senhas não coincidem.")
                else:
                    engine = get_engine()
                    email_normalizado = email.strip().lower()

                    with engine.begin() as conn:
                        existe = conn.execute(
                            text("SELECT id FROM usuarios WHERE email = :email"),
                            {"email": email_normalizado}
                        ).fetchone()

                        if existe:
                            st.error("Este e-mail já está cadastrado.")
                        else:
                            conn.execute(text('''
                                INSERT INTO usuarios (nome_completo, empresa, funcao, avatar, email, senha_hash, data_criacao)
                                VALUES (:nome, :empresa, :funcao, :avatar, :email, :senha, :data)
                            '''), {
                                "nome": nome_completo.strip(),
                                "empresa": nome_empresa.strip(),
                                "funcao": funcao.strip(),
                                "avatar": avatar,
                                "email": email_normalizado,
                                "senha": hash_senha(senha),
                                "data": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.success("Cadastro criado com sucesso! Faça login para continuar.")
                            st.session_state["tela_auth"] = "login"

        st.markdown("<p style='text-align:center;'>Já tem conta?</p>", unsafe_allow_html=True)
        if st.button("Entrar", use_container_width=True, key="btn_ir_login"):
            st.session_state["tela_auth"] = "login"
            st.rerun()


# --- GATE: só passa daqui se estiver no painel admin OU já estiver logado ---
if not st.session_state["mostrar_painel_admin"] and st.session_state["usuario_logado"] is None:
    if st.session_state["tela_auth"] == "login":
        tela_login()
    else:
        tela_cadastro()
    st.stop()


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
            engine = get_engine()
            df_admin = pd.read_sql_query("SELECT * FROM historico", engine)
            
            if not df_admin.empty:
                df_admin.insert(0, "Deletar", False)
                df_admin_editado = st.data_editor(
                    df_admin,
                    use_container_width=True,
                    hide_index=True,
                    disabled=["id"],
                    column_config={
                        "ultimo_preco": st.column_config.NumberColumn(
                            "Último Preço",
                            format="R$ %,.2f"
                        )
                    }
                )
                
                if st.button("💾 Aplicar Alterações / Exclusões"):
                    with engine.begin() as conn:
                        deletar_ids = [int(i) for i in df_admin_editado[df_admin_editado["Deletar"] == True]["id"].tolist()]
                        if deletar_ids:
                            stmt_delete = text("DELETE FROM historico WHERE id IN :ids").bindparams(
                                bindparam("ids", expanding=True)
                            )
                            conn.execute(stmt_delete, {"ids": deletar_ids})

                        salvar_linhas = df_admin_editado[df_admin_editado["Deletar"] == False]
                        for _, row in salvar_linhas.iterrows():
                            conn.execute(text('''
                                UPDATE historico
                                SET material=:material, fornecedor=:fornecedor, localidade=:localidade,
                                    contato=:contato, whatsapp=:whatsapp, ultimo_preco=:preco, data_compra=:data
                                WHERE id=:id
                            '''), {
                                "material": row['material'],
                                "fornecedor": row['fornecedor'],
                                "localidade": row['localidade'],
                                "contato": row['contato'],
                                "whatsapp": row['whatsapp'],
                                "preco": row['ultimo_preco'],
                                "data": row['data_compra'],
                                "id": int(row['id'])
                            })
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
                    if arquivo_enviado.name.endswith('.csv'):
                        conteudo_inicio = arquivo_enviado.read(1024).decode('utf-8', errors='ignore')
                        arquivo_enviado.seek(0)
                        separador = ';' if ';' in conteudo_inicio else ','
                        df_importado = pd.read_csv(arquivo_enviado, sep=separador)
                    else:
                        df_importado = pd.read_excel(arquivo_enviado)
                    
                    colunas_necessarias = ["material", "fornecedor", "localidade", "contato", "whatsapp", "ultimo_preco", "data_compra"]
                    
                    if len(df_importado.columns) == 1:
                        col_unica = df_importado.columns[0]
                        linhas_brutas = [str(col_unica)] + df_importado[col_unica].dropna().astype(str).tolist()
                        dados_processados = []
                        for linha in linhas_brutas:
                            partes = [p.strip() for p in linha.split(',')]
                            while len(partes) < len(colunas_necessarias):
                                partes.append("")
                            dados_processados.append(partes[:len(colunas_necessarias)])
                        df_importado = pd.DataFrame(dados_processados, columns=colunas_necessarias)
                    
                    df_importado.columns = [str(c).strip().lower() for c in df_importado.columns]
                    
                    for col in df_importado.columns:
                        if col != 'ultimo_preco':
                            df_importado[col] = df_importado[col].astype(str).replace(['None', 'nan', '<NA>'], '')
                    
                    st.markdown("### 👀 Pré-visualização dos dados importados:")
                    st.dataframe(df_importado.head(5), use_container_width=True)
                    
                    colunas_validas = all(col in df_importado.columns for col in colunas_necessarias)
                    
                    if colunas_validas:
                        if st.button("🚀 Confirmar e Salvar Tudo no Banco"):
                            engine = get_engine()
                            df_importado['ultimo_preco'] = df_importado['ultimo_preco'].astype(str).str.replace('R$', '', regex=False).str.strip()
                            df_importado['ultimo_preco'] = pd.to_numeric(df_importado['ultimo_preco'], errors='coerce').fillna(0.0)
                            df_importado['whatsapp'] = df_importado['whatsapp'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                            
                            for c in colunas_necessarias:
                                if c != 'ultimo_preco':
                                    df_importado[c] = df_importado[c].fillna('').astype(str)
                            
                            df_importado[colunas_necessarias].to_sql('historico', engine, if_exists='append', index=False)
                            st.success(f"Sucesso! {len(df_importado)} novos registros foram adicionados.")
                    else:
                        st.error("Erro nos cabeçalhos da planilha. Verifique se os nomes das colunas estão corretos.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo: {e}")

else:
    # --- BARRA DO USUÁRIO LOGADO ---
    usuario_atual = st.session_state["usuario_logado"]
    col_user_info, col_user_logout = st.columns([5, 1])
    with col_user_info:
        st.markdown(
            f"<p style='font-size:16px;'>{usuario_atual['avatar']} Olá, <b>{usuario_atual['nome']}</b></p>",
            unsafe_allow_html=True
        )
    with col_user_logout:
        if st.button("Sair"):
            st.session_state["usuario_logado"] = None
            st.rerun()

    aba_busca, aba_cadastro, aba_minhas = st.tabs(["🔍 Painel de Cotação", "➕ Novo Fornecedor", "📋 Minhas Solicitações"])

    with aba_busca:
        st.write("")
        col_input, col_btn = st.columns([4, 1])
        
        with col_input:
            termo_busca = st.text_input("", placeholder="O que você precisa comprar hoje?", label_visibility="collapsed")
            
        with col_btn:
            clicou_buscar = st.button("Cota Aí")

        # Dispara a busca se houver alteração ou clique no botão
        if clicou_buscar or (termo_busca and ("termo_atual" not in st.session_state or st.session_state["termo_atual"] != normalizar_texto(termo_busca))):
            termo_ajustado = normalizar_texto(termo_busca)
            
            if termo_ajustado:
                engine = get_engine()

                # Registra automaticamente essa busca na "lista de compras" do usuário
                with engine.begin() as conn:
                    conn.execute(text('''
                        INSERT INTO solicitacoes (usuario_id, termo_buscado, data_hora)
                        VALUES (:usuario_id, :termo, :data)
                    '''), {
                        "usuario_id": usuario_atual["id"],
                        "termo": termo_busca.strip(),
                        "data": datetime.now().strftime("%d/%m/%Y %H:%M")
                    })

                query = "SELECT material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra FROM historico"
                df_completo = pd.read_sql_query(query, engine)
                
                if not df_completo.empty:
                    # Cria uma lista com as palavras que o usuário digitou
                    palavras_busca = termo_ajustado.split()
                    
                    # Função interna para checar se as palavras batem de forma flexível
                    def checar_compatibilidade(material_banco):
                        material_norm = normalizar_texto(material_banco)
                        # Retorna True se qualquer palavra digitada estiver no material do banco
                        # OU se o material do banco estiver contido no que foi digitado
                        return any(p in material_norm for p in palavras_busca) or material_norm in termo_ajustado

                    # Aplica o filtro flexível
                    mascara = df_completo['material'].apply(checar_compatibilidade)
                    df_resultado = df_completo[mascara].copy()
                    
                    if not df_resultado.empty:
                        df_resultado.insert(0, "Selecionar", False)
                        st.session_state["dados_busca"] = df_resultado
                        st.session_state["termo_atual"] = termo_ajustado
                    else:
                        st.session_state["dados_busca"] = None
                        st.warning("Nenhum histórico encontrado para este material.")
                else:
                    st.session_state["dados_busca"] = None
                    st.warning("O banco de dados está completamente vazio.")

        if "dados_busca" in st.session_state and st.session_state["dados_busca"] is not None:
            st.markdown("### ✨ Selecione os itens que deseja cotar:")
            
            df_editado = st.data_editor(
                st.session_state["dados_busca"],
                use_container_width=True,
                hide_index=True,
                disabled=["material", "fornecedor", "localidade", "contato", "whatsapp", "ultimo_preco", "data_compra"],
                column_config={
                    "ultimo_preco": st.column_config.NumberColumn(
                        "Último Preço",
                        format="R$ %,.2f"
                    )
                }
            )
            
            itens_selecionados = df_editado[df_editado["Selecionar"] == True]
            
            if not itens_selecionados.empty:
                st.write("---")
                st.markdown("### 📱 Envio de Mensagens Combinadas")
                
                agrupado = itens_selecionados.groupby("whatsapp")
                
                for whatsapp, group in agrupado:
                    contato = group["contato"].iloc[0]
                    fornecedor = group["fornecedor"].iloc[0]
                    
                    # Usa o termo exato que o usuário digitou na barra de pesquisa como descrição
                    descricao_produto = termo_busca.strip() if termo_busca else group["material"].iloc[0]
                    
                    # Monta a mensagem usando apenas o nome do vendedor e a descrição digitada
                    texto_msg = f"Olá {contato}, tudo bem? Poderia cotar o(s) seguinte(s) item(ns) para mim?\n- *{descricao_produto}*"
                    chave_dinamica = f"msg_{whatsapp}_{len(group)}"
                    
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        # Exibe o título da caixa com o nome do fornecedor apenas para identificação visual no app
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
                    engine = get_engine()
                    with engine.begin() as conn:
                        conn.execute(text('''
                            INSERT INTO historico (material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra)
                            VALUES (:material, :fornecedor, :localidade, :contato, :whatsapp, :preco, :data)
                        '''), {
                            "material": novo_material,
                            "fornecedor": novo_fornecedor,
                            "localidade": novo_localidade,
                            "contato": novo_contato,
                            "whatsapp": novo_whats,
                            "preco": novo_preco,
                            "data": nova_data
                        })
                    st.success("Dados salvos com sucesso!")
                else:
                    st.error("Preencha os campos obrigatórios (Material e Fornecedor).")

    with aba_minhas:
        st.markdown("### 📋 Minhas Solicitações de Cotação")
        st.caption("Todo item que você pesquisou no Painel de Cotação aparece aqui automaticamente.")

        engine = get_engine()
        df_minhas = pd.read_sql_query(
            text('SELECT termo_buscado AS "Item Solicitado", data_hora AS "Data/Hora" FROM solicitacoes WHERE usuario_id = :uid ORDER BY id DESC'),
            engine,
            params={"uid": usuario_atual["id"]}
        )

        if not df_minhas.empty:
            st.dataframe(df_minhas, use_container_width=True, hide_index=True)
        else:
            st.info("Você ainda não fez nenhuma solicitação de cotação.")