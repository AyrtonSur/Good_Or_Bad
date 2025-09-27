import streamlit as st
import pandas as pd
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Optional authentication library
try:
    import streamlit_authenticator as stauth
except ImportError:
    stauth = None

# IDs dos Google Sheets (extraídos das URLs)
SHEETS_GOOD_ID = '1Iimtpui2WJlzrIGbJma6ucGrefuKWsGjshG9LCBEyHE'
SHEETS_BAD_ID = '1ZJFoD_y8uNXXEWhB-iYTI-xkfQ8XxmDvInNx3PQkgUI'

JSON_FILE_AYRTON = 'esg_full_splited_set_test_shuffled_part1.json'
JSON_FILE_PEDRO = 'esg_full_splited_set_test_shuffled_part2.json'
CREDENTIALS_FILE = 'credentials.json'

# Campos extras do CSV/Sheets
EXTRA_FIELDS = ['isAlign', 'isEnv', 'isSocial', 'isGovernance', 'isGeneral']

@st.cache_resource
def authenticate_google_sheets():
    """Autentica e retorna o cliente do Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        # Try to get credentials from secrets first
        creds_text = None
        try:
            if hasattr(st, 'secrets') and st.secrets:
                creds_text = st.secrets.get('GSPREAD_CREDENTIALS_JSON')
        except Exception:
            pass
        
        if creds_text:
            # Use credentials from secrets (for deployment)
            import json
            creds_dict = json.loads(creds_text)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        elif os.path.exists(CREDENTIALS_FILE):
            # Fallback to local file only if it exists (for development)
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        else:
            # No credentials available
            raise FileNotFoundError("Nenhuma credencial encontrada. Configure GSPREAD_CREDENTIALS_JSON em st.secrets ou adicione credentials.json localmente.")
        
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


def load_json_from_secrets_or_file(key_name='JSON_PAYLOAD', fallback_file=None):
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
    if fallback_file:
        return read_json(fallback_file)
    else:
        return read_json(JSON_FILE_AYRTON)  # Default fallback

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

def get_used_questions(sheets_data, user):
    """Retorna set de perguntas já utilizadas por um usuário específico"""
    used_questions = set()
    
    for sheet_type in ['Good', 'Bad']:
        df = sheets_data[sheet_type][user]
        if not df.empty and 'Pergunta' in df.columns:
            used_questions.update(df['Pergunta'].tolist())
    
    return used_questions

def get_available_questions(json_data, used_questions):
    """Retorna lista de perguntas disponíveis (não utilizadas) do JSON, filtrando apenas gen_run = 2"""
    available = []
    
    for i, item in enumerate(json_data):
        question = item.get('question', '')
        gen_run = item.get('gen_run', 0)  # Pega o gen_run do item
        
        # Filtra apenas perguntas com gen_run = 2 e que não foram utilizadas
        if question and question not in used_questions and gen_run == 2:
            available.append((i, item))
    
    return available

def select_random_question(json_data, sheets_data, user):
    """Seleciona uma pergunta aleatória que ainda não foi utilizada"""
    import random
    
    # Pega perguntas já utilizadas
    used_questions = get_used_questions(sheets_data, user)
    
    # Pega perguntas disponíveis
    available_questions = get_available_questions(json_data, used_questions)
    
    if not available_questions:
        return None, None  # Não há mais perguntas disponíveis
    
    # Seleciona uma pergunta aleatória
    random_index, random_question = random.choice(available_questions)
    
    return random_index, random_question

def main():
    # Configuração da página
    st.set_page_config(
        page_title="Good or Bad Sheets Adder", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
        # Initialize session state variables
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'sheets_client' not in st.session_state:
        st.session_state.sheets_client = None
    if 'sheets_data' not in st.session_state:
        st.session_state.sheets_data = None
    if 'json_data_ayrton' not in st.session_state:
        st.session_state.json_data_ayrton = None
    if 'json_data_pedro' not in st.session_state:
        st.session_state.json_data_pedro = None
    if 'current_question_ayrton' not in st.session_state:
        st.session_state.current_question_ayrton = None
    if 'current_question_pedro' not in st.session_state:
        st.session_state.current_question_pedro = None
    if 'force_new_question' not in st.session_state:
        st.session_state.force_new_question = False
    if 'saving_in_progress' not in st.session_state:
        st.session_state.saving_in_progress = False
    
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
        
        # Botão para recarregar dados
        if st.button("🔄 Recarregar dados", help="Recarrega dados do Google Sheets"):
            st.session_state.sheets_data = None
            st.session_state.json_data_ayrton = None
            st.session_state.json_data_pedro = None
            st.rerun()
        
        # Estatísticas de progresso (só mostrar se os dados estão carregados)
        if (st.session_state.sheets_data is not None and 
            st.session_state.json_data_ayrton is not None and 
            st.session_state.json_data_pedro is not None):
            
            st.markdown("---")
            st.markdown("📈 **Progresso:**")
            
            for user in ['Ayrton', 'Pedro']:
                json_data = st.session_state.json_data_ayrton if user == 'Ayrton' else st.session_state.json_data_pedro
                used_questions = get_used_questions(st.session_state.sheets_data, user)
                total = len(json_data)  # Total de todas as perguntas
                used = len(used_questions)
                available = total - used
                
                st.markdown(f"**{user}:** {used}/{total} ({available} restantes)")
                if total > 0:
                    progress = used / total
                    st.progress(progress)
    
    # Título principal
    st.title('🔍 Good or Bad Sheets Adder')
    st.markdown('---')

    # Authentication: use streamlit-authenticator if available and configured
    if not st.session_state.authenticated and stauth is not None and st.secrets.get('auth'):
        try:
            auth_conf = st.secrets['auth']
            
            # Handle different possible structures
            if 'users' in auth_conf:
                users_data = auth_conf['users']
                
                # If users is a list of dicts
                if isinstance(users_data, list):
                    names = [u['name'] for u in users_data]
                    usernames = [u['username'] for u in users_data]
                    passwords = [u['password'] for u in users_data]
                # If users is a dict with numeric keys (TOML array parsed differently)
                elif isinstance(users_data, dict):
                    # Try to get values from numbered keys (0, 1, 2, etc.)
                    user_list = []
                    for key in sorted(users_data.keys()):
                        if isinstance(key, (int, str)) and str(key).isdigit():
                            user_list.append(users_data[key])
                    
                    if user_list:
                        names = [u['name'] for u in user_list]
                        usernames = [u['username'] for u in user_list]
                        passwords = [u['password'] for u in user_list]
                    else:
                        raise ValueError("Could not parse users structure")
                else:
                    raise ValueError(f"Unexpected users data type: {type(users_data)}")
            else:
                raise ValueError("No 'users' key found in auth config")
            
            # Hash passwords using updated API (no arguments to constructor)
            hasher = stauth.Hasher()
            hashed_passwords = [hasher.hash(pwd) for pwd in passwords]
            
            # Create credentials in the format expected by streamlit-authenticator
            credentials = {
                'usernames': {}
            }
            
            for i, username in enumerate(usernames):
                credentials['usernames'][username] = {
                    'name': names[i],
                    'password': hashed_passwords[i]
                }
            
            authenticator = stauth.Authenticate(
                credentials,
                auth_conf.get('cookie_name', 'app_cookie'),
                auth_conf.get('signature_key', 'secret_signature'),
                auth_conf.get('cookie_expiry_days', 30)
            )
            
            # Try different login method signatures based on version
            try:
                # Try newer API first
                login_result = authenticator.login()
                if login_result is not None:
                    name, authentication_status, username = login_result
                else:
                    # If login returns None, try alternative approach
                    name = st.session_state.get('name')
                    authentication_status = st.session_state.get('authentication_status')
                    username = st.session_state.get('username')
            except Exception as login_error:
                st.error(f'Erro no método login: {login_error}')
                # Try older API
                try:
                    name, authentication_status, username = authenticator.login(location='main')
                except:
                    # Last resort - try without parameters
                    result = authenticator.login()
                    if result:
                        name, authentication_status, username = result
                    else:
                        name, authentication_status, username = None, None, None
            
            if authentication_status is False:
                st.error('Usuário ou senha inválidos')
                st.stop()
            if authentication_status is None:
                st.warning('Por favor, faça login')
                st.stop()
            
            # Store authentication status
            st.session_state.authenticated = True
            st.session_state.auth_user = name
            
        except Exception as e:
            st.error('Erro na autenticação: ' + str(e))
            # continue without auth if config is invalid
            st.session_state.authenticated = True  # Skip auth if there's an error
    elif not st.session_state.authenticated:
        # If stauth not installed or no auth config, skip authentication
        if stauth is None:
            st.info('streamlit-authenticator não instalado — sem autenticação.')
        elif not st.secrets.get('auth'):
            st.info('Nenhuma configuração de autenticação encontrada em st.secrets["auth"]')
        st.session_state.authenticated = True

    # Only authenticate and load data once
    if st.session_state.sheets_client is None:
        st.session_state.sheets_client = authenticate_google_sheets()
        if not st.session_state.sheets_client:
            st.stop()

    # Load data only once
    if (st.session_state.json_data_ayrton is None or 
        st.session_state.json_data_pedro is None or 
        st.session_state.sheets_data is None):
        with st.spinner('Carregando dados iniciais...'):
            # Load JSON files for both users
            st.session_state.json_data_ayrton = load_json_from_secrets_or_file('JSON_PAYLOAD', JSON_FILE_AYRTON)
            st.session_state.json_data_pedro = load_json_from_secrets_or_file('JSON_PAYLOAD_PEDRO', JSON_FILE_PEDRO)

            # Carrega dados das planilhas para determinar a próxima pergunta
            # Use cached reads to avoid network calls on every widget interaction
            st.session_state.sheets_data = {
                'Good': {
                    'Ayrton': read_sheet_cached(st.session_state.sheets_client, SHEETS_GOOD_ID, 'Ayrton'),
                    'Pedro': read_sheet_cached(st.session_state.sheets_client, SHEETS_GOOD_ID, 'Pedro')
                },
                'Bad': {
                    'Ayrton': read_sheet_cached(st.session_state.sheets_client, SHEETS_BAD_ID, 'Ayrton'),
                    'Pedro': read_sheet_cached(st.session_state.sheets_client, SHEETS_BAD_ID, 'Pedro')
                }
            }

    # Layout em duas colunas
    col1, col2 = st.columns([2, 1])
    
    # Primeiro, vamos criar os controles na coluna 2 para definir a página
    with col2:
        # Sidebar para controles
        st.subheader('⚙️ Configurações')
        
        # Escolha da página primeiro (determina qual JSON usar)
        st.markdown('**Usuário:**')
        page = st.radio(
            'Página:', 
            ['Ayrton', 'Pedro'],
            help="Escolha para qual usuário adicionar a pergunta"
        )
        
        st.markdown('---')
        
        # Botão para pegar nova pergunta
        if st.button("🔄 Nova Pergunta", help="Clique para carregar uma nova pergunta aleatória"):
            st.session_state.force_new_question = True
            st.rerun()
        
        st.markdown('---')

    # Determina pergunta aleatória baseada na página selecionada
    # Só seleciona nova pergunta se não houver uma atual ou se foi forçado
    if page == 'Ayrton':
        current_json = st.session_state.json_data_ayrton
        
        # Verifica se precisa de uma nova pergunta
        if (st.session_state.current_question_ayrton is None or 
            st.session_state.force_new_question):
            
            next_index, next_data = select_random_question(
                st.session_state.json_data_ayrton, 
                st.session_state.sheets_data, 
                'Ayrton'
            )
            st.session_state.current_question_ayrton = (next_index, next_data)
            st.session_state.force_new_question = False
        else:
            # Usa a pergunta já armazenada
            next_index, next_data = st.session_state.current_question_ayrton
            
    else:  # Pedro
        current_json = st.session_state.json_data_pedro
        
        # Verifica se precisa de uma nova pergunta
        if (st.session_state.current_question_pedro is None or 
            st.session_state.force_new_question):
            
            next_index, next_data = select_random_question(
                st.session_state.json_data_pedro, 
                st.session_state.sheets_data, 
                'Pedro'
            )
            st.session_state.current_question_pedro = (next_index, next_data)
            st.session_state.force_new_question = False
        else:
            # Usa a pergunta já armazenada
            next_index, next_data = st.session_state.current_question_pedro

    if not next_data:
        st.info(f'✅ Não há mais perguntas disponíveis no JSON para {page}.')
        st.balloons()
        st.stop()

    # Mostrar estatísticas
    used_questions = get_used_questions(st.session_state.sheets_data, page)
    available_questions = get_available_questions(current_json, used_questions)
    total_questions = len(current_json)  # Total de todas as perguntas
    used_questions_count = len(used_questions)
    
    st.info(f"📊 Estatísticas para {page}: {used_questions_count}/{total_questions} perguntas utilizadas | {len(available_questions)} restantes (apenas Gen 2)")

    # Verifica se a pergunta atual já foi utilizada
    pergunta_atual = next_data.get('question', '') if next_data else ''
    pergunta_ja_usada = pergunta_atual in used_questions
    
    # Proteção adicional: desabilita se está salvando ou se já foi usada
    botao_desabilitado = pergunta_ja_usada or st.session_state.saving_in_progress

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
        # Campos extras
        st.markdown('**Campos extras:**')
        extra_values = {}
        for field in EXTRA_FIELDS:
            if field == 'isAlign':
                # isAlign será puxado do deberta_answer do JSON, não da interface
                deberta_value = next_data.get('deberta_answer', 0)
                st.markdown(f"*{field}: {deberta_value} (do JSON - deberta_answer)*")
                continue
            extra_values[field] = st.checkbox(
                field, 
                value=bool(next_data.get(field, 0)),
                help=f"Marque se a pergunta se enquadra em {field}"
            )

        st.markdown('---')
        
        # Botão para pular pergunta (nova pergunta aleatória)
        if st.button("🎲 Nova pergunta aleatória", help="Seleciona uma nova pergunta aleatória"):
            st.rerun()

        st.markdown('---')

        # Escolha da planilha
        st.markdown('**Destino:**')
        sheet_type = st.radio(
            'Planilha:', 
            ['Good', 'Bad'],
            help="Escolha se a pergunta é boa ou ruim"
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
        
        # Mostra status se pergunta já foi usada
        if pergunta_ja_usada:
            st.warning("⚠️ Esta pergunta já foi salva anteriormente")
        elif st.session_state.saving_in_progress:
            st.info("💾 Salvamento em andamento...")
            
        if st.button(
            '💾 Salvar no Google Sheets', 
            type="primary",
            use_container_width=True,
            disabled=botao_desabilitado
        ):
            # Marca que o salvamento está em andamento
            st.session_state.saving_in_progress = True
            
            # Dupla verificação: verifica novamente se a pergunta já foi salva
            current_used_questions = get_used_questions(st.session_state.sheets_data, page)
            if pergunta_atual in current_used_questions:
                st.error("❌ Esta pergunta já foi salva! Não é possível salvar novamente.")
                st.session_state.saving_in_progress = False
                st.stop()
            
            with st.spinner('Salvando...'):
                row = {
                    'Contexto': next_data.get('context', ''),
                    'Pergunta': next_data.get('question', ''),
                    'Resposta': next_data.get('answer', ''),
                    'source_file': next_data.get('source_file', ''),
                    'stringFilter': next_data.get('stringFilter', 'none'),
                    'isAlign': next_data.get('deberta_answer', 0),  # Pega deberta_answer do JSON e envia como isAlign
                    'isEnv': int(extra_values.get('isEnv', 0)),
                    'isSocial': int(extra_values.get('isSocial', 0)),
                    'isGovernance': int(extra_values.get('isGovernance', 0)),
                    'isGeneral': int(extra_values.get('isGeneral', 0)),
                    'Comentários': comentario.strip(),
                }

                # Determina a planilha de destino
                sheet_id = SHEETS_GOOD_ID if sheet_type == 'Good' else SHEETS_BAD_ID

                # Adiciona ao Google Sheets
                if append_to_sheet(st.session_state.sheets_client, sheet_id, page, row):
                    # Clear cached sheet reads so UI shows updated data next render
                    try:
                        st.cache_data.clear()
                    except Exception:
                        # Older Streamlit may not have clear(); ignore if fails
                        pass
                    
                    # Update sheets data in session state
                    st.session_state.sheets_data = {
                        'Good': {
                            'Ayrton': read_sheet_cached(st.session_state.sheets_client, SHEETS_GOOD_ID, 'Ayrton'),
                            'Pedro': read_sheet_cached(st.session_state.sheets_client, SHEETS_GOOD_ID, 'Pedro')
                        },
                        'Bad': {
                            'Ayrton': read_sheet_cached(st.session_state.sheets_client, SHEETS_BAD_ID, 'Ayrton'),
                            'Pedro': read_sheet_cached(st.session_state.sheets_client, SHEETS_BAD_ID, 'Pedro')
                        }
                    }
                    
                    st.success(f'✅ Adicionado ao {sheet_type} - Página {page}!')
                    st.balloons()
                    
                    # Força uma nova pergunta após salvar
                    st.session_state.force_new_question = True
                    if page == 'Ayrton':
                        st.session_state.current_question_ayrton = None
                    else:
                        st.session_state.current_question_pedro = None
                    
                    # Reset do flag de salvamento
                    st.session_state.saving_in_progress = False
                    
                    # Recarrega a página para mostrar a próxima pergunta
                    st.rerun()
                else:
                    # Se falhou ao salvar, reseta o flag
                    st.session_state.saving_in_progress = False

    # Informações adicionais no rodapé
    st.markdown('---')
    
    # Calcula estatísticas de perguntas (conjunto completo)
    used_questions = get_used_questions(st.session_state.sheets_data, page)
    total_questions = len(current_json)  # Total de todas as perguntas
    used_count = len(used_questions)
    available_gen2 = len(get_available_questions(current_json, used_questions))  # Disponíveis Gen 2
    
    st.caption(f'📊 {page}: {used_count}/{total_questions} usadas | {available_gen2} disponíveis Gen 2 | {total_questions} total | 🔗 Conectado ao Google Sheets')
    
    if available_gen2 > 0:
        progress = used_count / total_questions
        st.progress(progress, text=f"Progresso: {progress:.1%}")
    else:
        st.success("🎉 Todas as perguntas da Gen 2 foram processadas!")

if __name__ == '__main__':
    main()
