import streamlit as st
import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# IDs dos Google Sheets (extraídos das URLs)
SHEETS_GOOD_ID = '1Iimtpui2WJlzrIGbJma6ucGrefuKWsGjshG9LCBEyHE'
SHEETS_BAD_ID = '1ZJFoD_y8uNXXEWhB-iYTI-xkfQ8XxmDvInNx3PQkgUI'

JSON_FILE = 'combined_jsons_without_context_clean_shuffled_part2.json'
CREDENTIALS_FILE = 'credentials.json'

# Campos extras do CSV/Sheets
EXTRA_FIELDS = ['isAlign', 'isEnv', 'isSocial', 'isGovernance', 'isGeneral']

@st.cache_resource
def authenticate_google_sheets():
    """Autentica e retorna o cliente do Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f'Erro ao autenticar Google Sheets: {str(e)}')
        return None

@st.cache_data
def read_json(filename):
    """Lê o arquivo JSON"""
    with open(filename, encoding='utf-8') as f:
        return json.load(f)


def load_json_from_secrets_or_file(key_name='JSON_PAYLOAD'):
    """Try to load JSON from Streamlit secrets (as a string) or fall back to a local file.

    Expected secret key: st.secrets['JSON_PAYLOAD'] containing the full JSON text.
    """
    # First prefer st.secrets if available
    try:
        if hasattr(st, 'secrets') and st.secrets:
            payload = st.secrets.get(key_name)
            if payload:
                try:
                    return json.loads(payload)
                except Exception:
                    # If payload is a path inside secrets dict, try loading that path
                    pass
    except Exception:
        # Accessing st.secrets can fail in some contexts, ignore and fallback
        pass

    # Fallback to reading the local file
    return read_json(JSON_FILE)


def write_credentials_from_secrets(key_name='GSPREAD_CREDENTIALS_JSON'):
    """If service account JSON is provided in secrets, write it to `credentials.json`.

    Expects st.secrets['GSPREAD_CREDENTIALS_JSON'] to be the full JSON text.
    """
    try:
        creds_text = None
        if hasattr(st, 'secrets') and st.secrets:
            creds_text = st.secrets.get(key_name)

        if creds_text:
            with open(CREDENTIALS_FILE, 'w', encoding='utf-8') as f:
                f.write(creds_text)
            return True
    except Exception:
        pass
    return False

def read_sheet_data(client, sheet_id, worksheet_name):
    """Lê dados de uma planilha Google Sheets"""
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f'Erro ao ler planilha {worksheet_name}: {str(e)}')
        return pd.DataFrame()


@st.cache_data
def read_sheet_cached(_client, sheet_id, worksheet_name):
    """Cached wrapper around read_sheet_data to avoid re-fetching on every interaction.
    Prefix _client to avoid Streamlit hashing/unhashable errors for client objects.
    """
    return read_sheet_data(_client, sheet_id, worksheet_name)

def append_to_sheet(client, sheet_id, worksheet_name, row_data):
    """Adiciona uma linha à planilha Google Sheets"""
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)
        # Converte os dados da linha para uma lista na ordem correta
        row_values = [
            row_data.get('Contexto', ''),
            row_data.get('Pergunta', ''),
            row_data.get('Resposta', ''),
            row_data.get('source_file', ''),
            row_data.get('stringFilter', 'none'),
            row_data.get('isAlign', 0),
            row_data.get('isEnv', 0),
            row_data.get('isSocial', 0),
            row_data.get('isGovernance', 0),
            row_data.get('isGeneral', 0),
            row_data.get('Comentários', '')
        ]
        worksheet.append_row(row_values)
        return True
    except Exception as e:
        st.error(f'Erro ao adicionar linha: {str(e)}')
        return False

def find_json_index(json_data, question):
    """Encontra o índice de uma pergunta no JSON"""
    for i, item in enumerate(json_data):
        if item.get('question') == question:
            return i
    return None

def determine_next_question(json_data, sheets_data):
    """Determina qual é a próxima pergunta baseada nos dados das planilhas"""
    max_index = -1
    
    # Verifica todas as planilhas e páginas para encontrar o maior índice
    for sheet_type in ['Good', 'Bad']:
        for page in ['Ayrton', 'Pedro']:
            df = sheets_data[sheet_type][page]
            if not df.empty and 'Pergunta' in df.columns:
                last_question = df['Pergunta'].iloc[-1] if len(df) > 0 else ''
                if last_question:
                    index = find_json_index(json_data, last_question)
                    if index is not None and index > max_index:
                        max_index = index

    return max_index + 1

def main():
    # Configuração da página
    st.set_page_config(
        page_title="Good or Bad Sheets Adder", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Sidebar para configurações globais
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        # Seletor de tema
        theme = st.selectbox(
            "🎨 Tema:",
            ["Auto", "Light", "Dark"],
            help="Escolha o tema da interface"
        )
        
        # Aplicar tema via CSS
        if theme == "Dark":
            st.markdown("""
            <style>
            /* Fundo principal e corpo */
            .stApp {
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%) !important;
                color: #ffffff !important;
            }
            
            /* Header principal - forçar fundo escuro */
            header[data-testid="stHeader"] {
                background-color: #0f1419 !important;
                color: #ffffff !important;
            }
            
            /* Container principal */
            .main .block-container {
                background-color: transparent !important;
                color: #ffffff !important;
            }
            
            /* Sidebar completa - todos os seletores possíveis */
            .css-1d391kg, .css-1cypcdb, .css-17lntkn, 
            section[data-testid="stSidebar"], 
            .css-1cypcdb *, .css-1d391kg *,
            .sidebar .sidebar-content {
                background-color: #0f1419 !important;
                color: #ffffff !important;
            }
            
            /* Forçar texto branco na sidebar */
            section[data-testid="stSidebar"] * {
                color: #ffffff !important;
            }
            
            /* Headers da sidebar */
            section[data-testid="stSidebar"] h1,
            section[data-testid="stSidebar"] h2,
            section[data-testid="stSidebar"] h3 {
                color: #4f9eff !important;
            }
            
            /* Todos os inputs */
            .stSelectbox > div > div, 
            .stTextInput > div > div > input,
            .stTextArea > div > div > textarea {
                background-color: #2a2d3a !important;
                color: #ffffff !important;
                border: 1px solid #404552 !important;
                border-radius: 8px !important;
            }
            
            /* Dropdown options e selectbox na sidebar */
            .stSelectbox div[data-baseweb="select"] > div,
            section[data-testid="stSidebar"] .stSelectbox > div > div,
            section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div,
            .css-1d391kg .stSelectbox > div > div {
                background-color: #2a2d3a !important;
                color: #ffffff !important;
                border: 1px solid #404552 !important;
            }
            
            /* Menu dropdown quando aberto */
            div[data-baseweb="popover"] ul,
            div[data-baseweb="popover"] li {
                background-color: #2a2d3a !important;
                color: #ffffff !important;
            }
            
            /* Hover no dropdown */
            div[data-baseweb="popover"] li:hover {
                background-color: #404552 !important;
                color: #ffffff !important;
            }
            
            /* Radio buttons: use aria-checked to reliably set selected/unselected states */
            .stRadio > div, div[role="radiogroup"] {
                background-color: transparent !important;
            }

            /* Default label color */
            .stRadio > div > label, div[role="radio"] {
                color: #ffffff !important;
            }

            /* Unselected radio (outer circle) */
            .stRadio label[aria-checked="false"] > div:first-child,
            div[role="radio"][aria-checked="false"] > div:first-child {
                background-color: #2a2d3a !important; /* blends with dark background */
                border: 2px solid #404552 !important;
            }

            /* Selected radio (outer circle border highlighted) */
            .stRadio label[aria-checked="true"] > div:first-child,
            div[role="radio"][aria-checked="true"] > div:first-child {
                background-color: #2a2d3a !important;
                border: 2px solid #4f9eff !important; /* ring for selected */
            }

            /* Selected radio dot (center) */
            .stRadio label[aria-checked="true"] > div:first-child > div,
            div[role="radio"][aria-checked="true"] > div:first-child > div {
                background-color: #4f9eff !important; /* filled dot */
            }

            /* Hover removed: no hover styling for radio buttons to avoid visual jumps */
            .stRadio > div > label:hover > div:first-child,
            div[role="radio"]:hover > div:first-child {
                /* intentionally empty to disable hover */
            }
            
            /* Checkboxes */
            .stCheckbox > label {
                color: #ffffff !important;
            }
            .stCheckbox > label > div:first-child {
                background-color: #2a2d3a !important;
                border: 2px solid #404552 !important;
            }
            .stCheckbox > label > div:first-child > div {
                background-color: #4f9eff !important;
            }
            
            /* Botões */
            .stButton > button {
                background: linear-gradient(45deg, #4f9eff 0%, #7b68ee 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 10px !important;
                font-weight: 600 !important;
                transition: all 0.3s ease !important;
            }
            .stButton > button:hover {
                transform: translateY(-2px) !important;
                box-shadow: 0 8px 16px rgba(79, 158, 255, 0.3) !important;
            }
            
            /* Todo texto, markdown e parágrafos */
            .stMarkdown, .stText, p, span, div {
                color: #ffffff !important;
            }
            
            /* Headers - mais claros e visíveis */
            h1, h2, h3, h4, h5, h6 {
                color: #ffffff !important;
                text-shadow: 0 0 10px rgba(79, 158, 255, 0.3) !important;
            }
            
            /* Success/Info/Error boxes com fundo escuro */
            .stSuccess {
                background-color: rgba(34, 197, 94, 0.2) !important;
                border: 1px solid #22c55e !important;
                color: #ffffff !important;
            }
            .stInfo {
                background-color: rgba(79, 158, 255, 0.2) !important;
                border: 1px solid #4f9eff !important;
                color: #ffffff !important;
            }
            .stError {
                background-color: rgba(239, 68, 68, 0.2) !important;
                border: 1px solid #ef4444 !important;
                color: #ffffff !important;
            }
            
            /* Expander com fundo escuro completo */
            .streamlit-expanderHeader, 
            div[data-testid="expander"] summary,
            div[data-testid="expander"] > div > div:first-child,
            div[data-testid="expander"] [data-testid="stExpander"] summary {
                background-color: #2a2d3a !important;
                color: #ffffff !important;
                border-radius: 8px !important;
                border: 1px solid #404552 !important;
            }
            
            .streamlit-expanderContent,
            div[data-testid="expander"] div:not(:first-child),
            div[data-testid="expander"] > div > div:last-child,
            div[data-testid="expander"] [data-testid="stExpander"] > div:last-child {
                background-color: #2a2d3a !important;
                border: 1px solid #404552 !important;
                border-radius: 0 0 8px 8px !important;
                color: #ffffff !important;
            }
            
            /* Container principal do expander */
            div[data-testid="expander"],
            div[data-testid="stExpander"] {
                background-color: #2a2d3a !important;
                border: 1px solid #404552 !important;
                border-radius: 8px !important;
            }
            
            /* Todos os elementos filhos do expander */
            div[data-testid="expander"] *,
            div[data-testid="stExpander"] *,
            .streamlit-expanderContent *,
            .streamlit-expanderContent {
                color: #ffffff !important;
                background-color: transparent !important;
            }
            
            /* Forçar fundo escuro em divs internas */
            div[data-testid="expander"] > div,
            div[data-testid="expander"] > div > div,
            div[data-testid="stExpander"] > div,
            div[data-testid="stExpander"] > div > div {
                background-color: #2a2d3a !important;
            }
            
            /* Markdown dentro do expander */
            div[data-testid="expander"] .stMarkdown,
            div[data-testid="stExpander"] .stMarkdown {
                background-color: transparent !important;
                color: #ffffff !important;
            }
            
            /* Spinner */
            .stSpinner > div {
                border-top-color: #4f9eff !important;
            }
            
            /* Captions */
            .caption, small {
                color: #b0b0b0 !important;
            }
            
            /* Subheaders na coluna direita */
            .stApp .main .block-container h3 {
                color: #4f9eff !important;
            }
            
            /* Labels dos campos */
            .stMarkdown label, .css-1cpxqw2 {
                color: #ffffff !important;
            }
            
            /* Forçar cores escuras em todos os containers */
            .element-container, .stColumn > div {
                background-color: transparent !important;
            }
            </style>
            """, unsafe_allow_html=True)
        elif theme == "Light":
            st.markdown("""
            <style>
            /* Fundo principal */
            .stApp {
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
                color: #1e293b;
            }
            
            /* Sidebar */
            .css-1d391kg {
                background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
            }
            
            /* Selectbox e inputs */
            .stSelectbox > div > div,
            .stTextInput > div > div > input, 
            .stTextArea > div > div > textarea {
                background-color: #ffffff !important;
                color: #1e293b !important;
                border: 1px solid #cbd5e1 !important;
                border-radius: 8px !important;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            
            /* Radio buttons (light theme): use aria-checked for correct logic */
            .stRadio > div, div[role="radiogroup"] {
                background-color: transparent;
            }

            /* Unselected (outer circle) - light background */
            .stRadio label[aria-checked="false"] > div:first-child,
            div[role="radio"][aria-checked="false"] > div:first-child {
                background-color: #ffffff;
                border: 2px solid #e2e8f0;
            }

            /* Selected (dot) - dark center for contrast */
            .stRadio label[aria-checked="true"] > div:first-child > div,
            div[role="radio"][aria-checked="true"] > div:first-child > div {
                background-color: #1e293b;
            }

            /* Selected outer border highlight */
            .stRadio label[aria-checked="true"] > div:first-child,
            div[role="radio"][aria-checked="true"] > div:first-child {
                border: 2px solid #94a3b8;
            }

            /* Hover removed: no hover styling for radio buttons in light theme */
            .stRadio > div > label:hover > div:first-child,
            div[role="radio"]:hover > div:first-child {
                /* intentionally empty to disable hover */
            }
            
            /* Checkboxes */
            .stCheckbox > label {
                color: #1e293b !important;
            }
            .stCheckbox > label > div:first-child {
                background-color: #ffffff;
                border: 2px solid #cbd5e1;
            }
            .stCheckbox > label > div:first-child > div {
                background-color: #3b82f6;
            }
            
            /* Botões */
            .stButton > button {
                background: linear-gradient(45deg, #3b82f6 0%, #6366f1 100%);
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                transition: all 0.3s ease;
                box-shadow: 0 4px 6px rgba(59, 130, 246, 0.2);
            }
            .stButton > button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 16px rgba(59, 130, 246, 0.3);
            }
            
            /* Texto e markdown */
            .stMarkdown, .stText {
                color: #1e293b !important;
            }
            
            /* Headers */
            h1, h2, h3, h4, h5, h6 {
                color: #3b82f6 !important;
            }
            
            /* Success/Info/Error boxes */
            .stSuccess {
                background-color: rgba(34, 197, 94, 0.1);
                border: 1px solid #22c55e;
            }
            .stInfo {
                background-color: rgba(59, 130, 246, 0.1);
                border: 1px solid #3b82f6;
            }
            .stError {
                background-color: rgba(239, 68, 68, 0.1);
                border: 1px solid #ef4444;
            }
            
            /* Expander */
            .streamlit-expanderHeader {
                background-color: #ffffff;
                color: #1e293b;
                border-radius: 8px;
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            }
            .streamlit-expanderContent {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 0 0 8px 8px;
            }
            
            /* Captions */
            .caption {
                color: #64748b !important;
            }
            </style>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Título principal
    st.title('🔍 Good or Bad Sheets Adder')
    st.markdown('---')

    # Autenticação
    client = authenticate_google_sheets()
    if not client:
        st.stop()

    # Carregamento dos dados
    with st.spinner('Carregando dados...'):
        # If secrets contain credentials, write them to local file for gspread
        write_credentials_from_secrets()

        # Load JSON either from secrets or local file
        json_data = load_json_from_secrets_or_file()

        # Carrega dados das planilhas para determinar a próxima pergunta
        # Use cached reads to avoid network calls on every widget interaction
        sheets_data = {
            'Good': {
                'Ayrton': read_sheet_cached(client, SHEETS_GOOD_ID, 'Ayrton'),
                'Pedro': read_sheet_cached(client, SHEETS_GOOD_ID, 'Pedro')
            },
            'Bad': {
                'Ayrton': read_sheet_cached(client, SHEETS_BAD_ID, 'Ayrton'),
                'Pedro': read_sheet_cached(client, SHEETS_BAD_ID, 'Pedro')
            }
        }

    # Determina próxima questão
    next_index = determine_next_question(json_data, sheets_data)
    next_data = json_data[next_index] if next_index < len(json_data) else None

    if not next_data:
        st.info('✅ Não há mais perguntas disponíveis no JSON.')
        st.balloons()
        st.stop()

    # Layout em duas colunas
    col1, col2 = st.columns([2, 1])

    with col1:
        # Informações completas da pergunta atual
        st.subheader('📋 Informações da pergunta atual')
        
        with st.expander("Ver todas as informações", expanded=True):
            for key, value in next_data.items():
                if key in ['question', 'answer', 'context']:
                    # Destaque para campos principais
                    st.markdown(f"**{key.upper()}:** {value}")
                else:
                    st.markdown(f"**{key}:** {value}")

        st.markdown('---')

        # Pergunta e resposta destacadas
        st.subheader('❓ Pergunta atual')
        st.success(next_data['question'])
        
        st.subheader('💡 Resposta')
        st.info(next_data['answer'])

    with col2:
        # Sidebar para controles
        st.subheader('⚙️ Configurações')
        
        # Campos extras
        st.markdown('**Campos extras:**')
        extra_values = {}
        for field in EXTRA_FIELDS:
            if field == 'isAlign':
                # isAlign será puxado do JSON, não da interface
                st.markdown(f"*{field}: {next_data.get(field, 0)} (do JSON)*")
                continue
            extra_values[field] = st.checkbox(
                field, 
                value=bool(next_data.get(field, 0)),
                help=f"Marque se a pergunta se enquadra em {field}"
            )

        st.markdown('---')

        # Escolha da planilha e página
        st.markdown('**Destino:**')
        sheet_type = st.radio(
            'Planilha:', 
            ['Good', 'Bad'],
            help="Escolha se a pergunta é boa ou ruim"
        )
        
        page = st.radio(
            'Página:', 
            ['Ayrton', 'Pedro'],
            help="Escolha em qual página adicionar"
        )

        # Comentário
        st.markdown('**Comentário (opcional):**')
        comentario = st.text_area(
            'Adicione observações sobre a pergunta:', 
            value='', 
            height=150,
            placeholder="Digite aqui qualquer comentário adicional..."
        )

        # Botão de salvar
        st.markdown('---')
        if st.button(
            '💾 Salvar no Google Sheets', 
            type="primary",
            use_container_width=True
        ):
            with st.spinner('Salvando...'):
                row = {
                    'Contexto': next_data.get('context', ''),
                    'Pergunta': next_data.get('question', ''),
                    'Resposta': next_data.get('answer', ''),
                    'source_file': next_data.get('source_file', ''),
                    'stringFilter': next_data.get('stringFilter', 'none'),
                    'isAlign': next_data.get('isAlign', 0),
                    'isEnv': int(extra_values.get('isEnv', 0)),
                    'isSocial': int(extra_values.get('isSocial', 0)),
                    'isGovernance': int(extra_values.get('isGovernance', 0)),
                    'isGeneral': int(extra_values.get('isGeneral', 0)),
                    'Comentários': comentario.strip(),
                }

                # Determina a planilha de destino
                sheet_id = SHEETS_GOOD_ID if sheet_type == 'Good' else SHEETS_BAD_ID

                # Adiciona ao Google Sheets
                if append_to_sheet(client, sheet_id, page, row):
                    # Clear cached sheet reads so UI shows updated data next render
                    try:
                        st.cache_data.clear()
                    except Exception:
                        # Older Streamlit may not have clear(); ignore if fails
                        pass
                    st.success(f'✅ Adicionado ao {sheet_type} - Página {page}!')
                    st.balloons()
                    # Recarrega a página para mostrar a próxima pergunta
                    st.rerun()

    # Informações adicionais no rodapé
    st.markdown('---')
    st.caption(f'📊 Pergunta {next_index + 1} de {len(json_data)} | 🔗 Conectado ao Google Sheets')

if __name__ == '__main__':
    main()
