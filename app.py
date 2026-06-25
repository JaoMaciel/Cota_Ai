import streamlit as st
import pandas as pd
import sqlite3
import unicodedata

# Configuração da página do Streamlit
st.set_page_config(page_title="Cota AI", page_icon="🛍️", layout="wide")

# Inicialização do Banco de Dados SQLite
def criar_banco():
    conn = sqlite3.connect('cota_ai.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material TEXT NOT NULL,
            fornecedor TEXT NOT NULL,
            localidade TEXT,
            contato TEXT,
            whatsapp TEXT,
            ultimo_preco REAL,
            data_compra TEXT
        )
    ''')
    conn.commit()
    conn.close()

criar_banco()

# Função auxiliar para remover acentos e caracteres especiais (Ç -> C)
def remover_acentos(texto):
    if not isinstance(texto, str):
        return ""
    # Separa os acentos das letras e remove os diacríticos
    texto_sem_acento = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return texto_sem_acento.lower().strip()

# Inicialização das variáveis de estado (Session State)
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "dados_busca" not in st.session_state:
    st.session_state["dados_busca"] = None
if "termo_atual" not in st.session_state:
    st.session_state["termo_atual"] = ""

# Cabeçalho Principal da Aplicação
st.markdown("<h1 style='text-align: center; color: #1E88E5;'>COTA AI ↪</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-style: italic;'>A inteligência por trás das suas compras.</p>", unsafe_allow_html=True)
st.write("---")

# Definição das Abas de Navegação
aba_busca, aba_cadastro, aba_admin = st.tabs([
    "🔍 Painel de Cotação", 
    "➕ Novo Fornecedor", 
    "🔒 Área do Administrador"
])

# ==========================================
# ABA 1: PAINEL DE COTAÇÃO (BUSCA INTELIGENTE)
# ==========================================
with aba_busca:
    st.write("")
    col_input, col_btn = st.columns([4, 1])
    
    with col_input:
        termo_busca = st.text_input("", placeholder="O que você precisa comprar hoje?", label_visibility="collapsed")
        
    with col_btn:
        clicou_buscar = st.button("Cota Aí")

    if (clicou_buscar or termo_busca) and termo_busca:
        # Prepara o termo digitado (ex: "aco" ou "valvula")
        termo_ajustado = remover_acentos(termo_busca)
        
        if st.session_state["termo_atual"] != termo_ajustado:
            conn = sqlite3.connect('cota_ai.db')
            query = "SELECT material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra FROM historico"
            df_completo = pd.read_sql_query(query, conn)
            conn.close()
            
            if not df_completo.empty:
                # Aplica a limpeza de acentos na coluna de materiais para comparação rápida
                material_limpo = df_completo['material'].apply(remover_acentos)
                
                # Filtra os dados usando a lista limpa
                df_resultado = df_completo[material_limpo.str.contains(termo_ajustado, na=False, regex=False)].copy()
                
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

    # Exibição dos resultados encontrados
    if st.session_state["dados_busca"] is not None:
        st.write("")
        st.markdown("### ✨ Selecione os itens que deseja cotar:")
        
        # Configuração e exibição do editor de dados com formatação de moeda brasileira
        df_editavel = st.data_editor(
            st.session_state["dados_busca"],
            hide_index=True,
            column_config={
                "Selecionar": st.column_config.CheckboxColumn(help="Marque para incluir na cotação"),
                "material": "material",
                "fornecedor": "fornecedor",
                "localidade": "localidade",
                "contato": "contato",
                "whatsapp": "whatsapp",
                "ultimo_preco": st.column_config.NumberColumn("Último Preço", format="R$ %.2f"),
                "data_compra": "data_compra"
            },
            disabled=["material", "fornecedor", "localidade", "contato", "whatsapp", "ultimo_preco", "data_compra"],
            use_container_width=True
        )
        
        # Ação para disparar as mensagens dos itens marcados
        itens_selecionados = df_editavel[df_editavel["Selecionar"] == True]
        if st.button("Gerar Cotação para Selecionados") and not itens_selecionados.empty:
            st.success(f"Cotação iniciada para {len(itens_selecionados)} fornecedor(es)!")
            # Aqui você pode plugar a sua lógica de envio de mensagens do WhatsApp futuramente

# ==========================================
# ABA 2: CADASTRO MANUAL DE FORNECEDORES
# ==========================================
with aba_cadastro:
    st.subheader("📝 Cadastrar Novo Registro de Compra")
    
    with st.form("form_cadastro", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            mat = st.text_input("Nome do Material *")
            forn = st.text_input("Nome do Fornecedor *")
            loc = st.text_input("Localidade / Cidade")
            cont = st.text_input("Nome do Contato")
        with col2:
            zap = st.text_input("WhatsApp (com DDD)")
            preco = st.number_input("Último Preço Pago (R$)", min_value=0.0, step=0.01, format="%.2f")
            data = st.text_input("Data da Compra (DD/MM/AAAA)")
            
        enviar = st.form_submit_button("Salvar Registro")
        
        if enviar:
            if not mat or not forn:
                st.error("Por favor, preencha os campos obrigatórios (*).")
            else:
                conn = sqlite3.connect('cota_ai.db')
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO historico (material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (mat.strip(), forn.strip(), loc.strip(), cont.strip(), zap.strip(), preco, data.strip()))
                conn.commit()
                conn.close()
                st.success(f"Registro de '{mat}' cadastrado com sucesso!")
                # Força a limpeza do cache de buscas anteriores
                st.session_state["termo_atual"] = ""

# ==========================================
# ABA 3: ÁREA DO ADMINISTRADOR (GESTÃO & LOTES)
# ==========================================
with aba_admin:
    st.subheader("🔐 Autenticação do Administrador")
    
    if not st.session_state["autenticado"]:
        senha = st.text_input("Digite a senha master:", type="password")
        if st.button("Acessar Painel"):
            if senha == "admin123":  # Substitua pela sua senha de preferência
                st.session_state["autenticado"] = True
                st.rerun()
            else:
                st.error("Senha incorreta!")
    else:
        st.sidebar.success("Autenticado como Administrador!")
        if st.sidebar.button("Fazer Logout"):
            st.session_state["autenticado"] = False
            st.rerun()
            
        sub_aba_gerenciar, sub_aba_lote = st.tabs(["📝 Editar/Excluir Registros", "📥 Importar por Lote (Excel/CSV)"])
        
        # SUB-ABA: Gerenciar Banco Existente
        with sub_aba_gerenciar:
            conn = sqlite3.connect('cota_ai.db')
            df_admin = pd.read_sql_query("SELECT * FROM historico", conn)
            conn.close()
            
            if df_admin.empty:
                st.info("Nenhum dado cadastrado no sistema ainda.")
            else:
                df_admin.insert(0, "Deletar", False)
                
                df_admin_editado = st.data_editor(
                    df_admin,
                    hide_index=True,
                    column_config={
                        "Deletar": st.column_config.CheckboxColumn(),
                        "id": st.column_config.NumberColumn("ID", disabled=True),
                        "ultimo_preco": st.column_config.NumberColumn("Último Preço", format="R$ %.2f")
                    },
                    use_container_width=True
                )
                
                col_btn_salvar, col_btn_deletar = st.columns(2)
                
                with col_btn_salvar:
                    if st.button("Salvar Alterações da Tabela"):
                        conn = sqlite3.connect('cota_ai.db')
                        cursor = conn.cursor()
                        for _, row in df_admin_editado.iterrows():
                            cursor.execute('''
                                UPDATE historico 
                                SET material=?, fornecedor=?, localidade=?, contato=?, whatsapp=?, ultimo_preco=?, data_compra=?
                                WHERE id=?
                            ''', (row['material'], row['fornecedor'], row['localidade'], row['contato'], row['whatsapp'], row['ultimo_preco'], row['data_compra'], row['id']))
                        conn.commit()
                        conn.close()
                        st.success("Alterações salvas com sucesso!")
                        st.session_state["termo_atual"] = ""
                        st.rerun()
                        
                with col_btn_deletar:
                    ids_para_deletar = df_admin_editado[df_admin_editado["Deletar"] == True]["id"].tolist()
                    if ids_para_deletar and st.button("Excluir Itens Selecionados", type="primary"):
                        conn = sqlite3.connect('cota_ai.db')
                        cursor = conn.cursor()
                        for id_del in ids_para_deletar:
                            cursor.execute("DELETE FROM historico WHERE id=?", (id_del,))
                        conn.commit()
                        conn.close()
                        st.success(f"{len(ids_para_deletar)} item(ns) removido(s) com sucesso!")
                        st.session_state["termo_atual"] = ""
                        st.rerun()

        # SUB-ABA: Importação por Lote via Arquivo
        with sub_aba_lote:
            st.markdown("### 📥 Upload de Planilhas por Lote")
            st.write("A sua planilha deve conter exatamente as seguintes colunas de cabeçalho:")
            st.code("material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra")
            
            arquivo_enviado = st.file_uploader("Selecione um arquivo Excel (.xlsx) ou CSV", type=["xlsx", "csv"])
            
            if arquivo_enviado is not None:
                try:
                    if arquivo_enviado.name.endswith('.csv'):
                        df_lote = pd.read_csv(arquivo_enviado)
                    else:
                        df_lote = pd.read_excel(arquivo_enviado)
                        
                    colunas_obrigatorias = ["material", "fornecedor", "localidade", "contato", "whatsapp", "ultimo_preco", "data_compra"]
                    
                    if all(col in df_lote.columns for col in colunas_obrigatorias):
                        df_lote = df_lote[colunas_obrigatorias].copy()
                        
                        st.markdown("### 👀 Pré-visualização dos dados importados:")
                        st.dataframe(df_lote, use_container_width=True)
                        
                        if st.button("🚀 Confirmar e Salvar Tudo no Banco"):
                            conn = sqlite3.connect('cota_ai.db')
                            cursor = conn.cursor()
                            
                            for _, linha in df_lote.iterrows():
                                # Tratamento para valores nulos/vazios numéricos
                                preco_linha = 0.0 if pd.isna(linha['ultimo_preco']) else float(linha['ultimo_preco'])
                                
                                cursor.execute('''
                                    INSERT INTO historico (material, fornecedor, localidade, contato, whatsapp, ultimo_preco, data_compra)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                ''', (
                                    str(linha['material']).strip(),
                                    str(linha['fornecedor']).strip(),
                                    "" if pd.isna(linha['localidade']) else str(linha['localidade']).strip(),
                                    "" if pd.isna(linha['contato']) else str(linha['contato']).strip(),
                                    "" if pd.isna(linha['whatsapp']) else str(linha['whatsapp']).strip(),
                                    preco_linha,
                                    "" if pd.isna(linha['data_compra']) else str(linha['data_compra']).strip()
                                ))
                                
                            conn.commit()
                            conn.close()
                            st.success(f"Sucesso! {len(df_lote)} novos registros inseridos.")
                            st.session_state["termo_atual"] = ""
                    else:
                        st.error("Erro nos cabeçalhos da planilha. Certifique-se de que as colunas combinam exatamente com o exemplo apresentado.")
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo: {e}")