import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# URLs dos Google Sheets
SHEETS_GOOD_URL = 'https://docs.google.com/spreadsheets/d/1Iimtpui2WJlzrIGbJma6ucGrefuKWsGjshG9LCBEyHE'
SHEETS_BAD_URL = 'https://docs.google.com/spreadsheets/d/1ZJFoD_y8uNXXEWhB-iYTI-xkfQ8XxmDvInNx3PQkgUI'

# IDs dos Google Sheets (extraídos das URLs)
SHEETS_GOOD_ID = '1Iimtpui2WJlzrIGbJma6ucGrefuKWsGjshG9LCBEyHE'
SHEETS_BAD_ID = '1ZJFoD_y8uNXXEWhB-iYTI-xkfQ8XxmDvInNx3PQkgUI'

JSON_FILE = 'combined_jsons_without_context_clean_shuffled_part2.json'
CREDENTIALS_FILE = 'credentials.json'  # Arquivo de credenciais do Google

# Campos extras do CSV/Sheets
EXTRA_FIELDS = ['isAlign', 'isEnv', 'isSocial', 'isGovernance', 'isGeneral']

def authenticate_google_sheets():
    """Autentica e retorna o cliente do Google Sheets"""
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        messagebox.showerror('Erro de Autenticação', f'Erro ao autenticar Google Sheets: {str(e)}')
        return None

def read_sheet_data(client, sheet_id, worksheet_name):
    """Lê dados de uma planilha Google Sheets"""
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f'Erro ao ler planilha {worksheet_name}: {str(e)}')
        return pd.DataFrame()

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
        messagebox.showerror('Erro', f'Erro ao adicionar linha: {str(e)}')
        return False

def read_json(filename):
    with open(filename, encoding='utf-8') as f:
        return json.load(f)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Good or Bad Sheets Adder')
        # Ajusta o tamanho da janela para 70% da tela
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = int(screen_w * 0.7)
        height = int(screen_h * 0.7)
        self.geometry(f'{width}x{height}')

        # Autentica Google Sheets
        self.client = authenticate_google_sheets()
        if not self.client:
            self.destroy()
            return

        self.json_data = read_json(JSON_FILE)
        
        # Carrega dados das planilhas para determinar a próxima pergunta
        self.load_sheets_data()
        self.determine_next_question()
        self.create_widgets()

    def load_sheets_data(self):
        """Carrega dados das planilhas Good e Bad para ambas as páginas"""
        self.sheets_data = {
            'Good': {
                'Ayrton': read_sheet_data(self.client, SHEETS_GOOD_ID, 'Ayrton'),
                'Pedro': read_sheet_data(self.client, SHEETS_GOOD_ID, 'Pedro')
            },
            'Bad': {
                'Ayrton': read_sheet_data(self.client, SHEETS_BAD_ID, 'Ayrton'),
                'Pedro': read_sheet_data(self.client, SHEETS_BAD_ID, 'Pedro')
            }
        }

    def find_json_index(self, question):
        """Encontra o índice de uma pergunta no JSON"""
        for i, item in enumerate(self.json_data):
            if item.get('question') == question:
                return i
        return None

    def determine_next_question(self):
        """Determina qual é a próxima pergunta baseada nos dados das planilhas"""
        max_index = -1
        
        # Verifica todas as planilhas e páginas para encontrar o maior índice
        for sheet_type in ['Good', 'Bad']:
            for page in ['Ayrton', 'Pedro']:
                df = self.sheets_data[sheet_type][page]
                if not df.empty and 'Pergunta' in df.columns:
                    last_question = df['Pergunta'].iloc[-1] if len(df) > 0 else ''
                    if last_question:
                        index = self.find_json_index(last_question)
                        if index is not None and index > max_index:
                            max_index = index

        self.next_index = max_index + 1
        self.update_next_data()

    def update_next_data(self):
        self.next_data = self.json_data[self.next_index] if self.next_index < len(self.json_data) else None

    def update_info_frame(self):
        """Atualiza o frame de informações com os dados da pergunta atual"""
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        
        if self.next_data:
            for key, value in self.next_data.items():
                ttk.Label(self.info_frame, text=f'{key}: {value}', wraplength=1200, justify='left').pack(anchor='w', padx=5, pady=2)
        else:
            ttk.Label(self.info_frame, text='Nenhuma informação disponível').pack(anchor='w', padx=5, pady=2)

    def create_widgets(self):
        # Informações completas da pergunta atual
        self.info_frame = ttk.LabelFrame(self, text='Informações da pergunta atual')
        self.info_frame.pack(fill='both', expand=True, padx=10, pady=10)
        self.update_info_frame()

        # Pergunta atual
        ttk.Label(self, text='Pergunta atual do JSON:').pack(anchor='w', padx=10, pady=5)
        self.next_question_var = tk.StringVar(value=self.next_data['question'] if self.next_data else '')
        self.next_question_label = ttk.Label(self, textvariable=self.next_question_var, wraplength=1200, foreground='green')
        self.next_question_label.pack(anchor='w', padx=10)

        # Resposta
        ttk.Label(self, text='Resposta:').pack(anchor='w', padx=10, pady=5)
        self.answer_var = tk.StringVar(value=self.next_data['answer'] if self.next_data else '')
        self.answer_label = ttk.Label(self, textvariable=self.answer_var, wraplength=1200)
        self.answer_label.pack(anchor='w', padx=10)

        # Campos extras
        self.extra_vars = {}
        self.frame_extras = ttk.LabelFrame(self, text='Campos extras (0 ou 1)')
        self.frame_extras.pack(fill='both', expand=True, padx=10, pady=10)
        for field in EXTRA_FIELDS:
            if field == 'isAlign':
                # isAlign será puxado do JSON, não da interface
                continue
            var = tk.IntVar(value=self.next_data.get(field, 0) if self.next_data else 0)
            self.extra_vars[field] = var
            ttk.Checkbutton(self.frame_extras, text=field, variable=var).pack(side='left', padx=5)

        # Comentário
        comment_frame = ttk.Frame(self)
        comment_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(comment_frame, text='Comentário (opcional):').pack(side='left', padx=5)
        self.comment_text = tk.Text(comment_frame, height=4, width=100)
        self.comment_text.pack(side='left', padx=5)
        def clear_comment():
            self.comment_text.delete('1.0', tk.END)
        ttk.Button(comment_frame, text='Limpar comentário', command=clear_comment).pack(side='left', padx=5)

        # Escolha da planilha e página
        choice_frame = ttk.LabelFrame(self, text='Destino')
        choice_frame.pack(fill='x', padx=10, pady=10)
        
        # Escolha do tipo (Good/Bad)
        ttk.Label(choice_frame, text='Planilha:').pack(side='left', padx=5)
        self.sheet_choice = tk.StringVar(value='Good')
        ttk.Radiobutton(choice_frame, text='Good', variable=self.sheet_choice, value='Good').pack(side='left', padx=5)
        ttk.Radiobutton(choice_frame, text='Bad', variable=self.sheet_choice, value='Bad').pack(side='left', padx=5)
        
        # Escolha da página
        ttk.Label(choice_frame, text='Página:').pack(side='left', padx=10)
        self.page_choice = tk.StringVar(value='Ayrton')
        ttk.Radiobutton(choice_frame, text='Ayrton', variable=self.page_choice, value='Ayrton').pack(side='left', padx=5)
        ttk.Radiobutton(choice_frame, text='Pedro', variable=self.page_choice, value='Pedro').pack(side='left', padx=5)

        # Botão de salvar
        self.save_button = ttk.Button(self, text='Salvar no Google Sheets', command=self.save_entry)
        self.save_button.pack(pady=20)

    def save_entry(self):
        if not self.next_data:
            messagebox.showerror('Erro', 'Não há próxima pergunta disponível.')
            return

        row = {
            'Contexto': self.next_data.get('context', ''),
            'Pergunta': self.next_data.get('question', ''),
            'Resposta': self.next_data.get('answer', ''),
            'source_file': self.next_data.get('source_file', ''),
            'stringFilter': self.next_data.get('stringFilter', 'none'),
            'isAlign': self.next_data.get('isAlign', 0),
            'isEnv': self.extra_vars['isEnv'].get(),
            'isSocial': self.extra_vars['isSocial'].get(),
            'isGovernance': self.extra_vars['isGovernance'].get(),
            'isGeneral': self.extra_vars['isGeneral'].get(),
            'Comentários': self.comment_text.get('1.0', tk.END).strip(),
        }

        # Determina a planilha de destino
        sheet_type = self.sheet_choice.get()
        page = self.page_choice.get()
        sheet_id = SHEETS_GOOD_ID if sheet_type == 'Good' else SHEETS_BAD_ID

        # Adiciona ao Google Sheets
        if append_to_sheet(self.client, sheet_id, page, row):
            messagebox.showinfo('Sucesso', f'Adicionado ao {sheet_type} - Página {page}!')
            
            # Avança para a próxima questão
            self.next_index += 1
            self.update_next_data()
            
            if not self.next_data:
                messagebox.showinfo('Fim', 'Não há mais perguntas disponíveis no JSON.')
                self.save_button.config(state='disabled')
                self.next_question_var.set('')
                self.answer_var.set('')
                for var in self.extra_vars.values():
                    var.set(0)
                self.comment_text.delete('1.0', tk.END)
                return
            
            # Atualiza interface para próxima questão
            self.update_info_frame()
            self.next_question_var.set(self.next_data['question'])
            self.answer_var.set(self.next_data['answer'])
            for field in EXTRA_FIELDS:
                if field == 'isAlign':
                    continue
                self.extra_vars[field].set(self.next_data.get(field, 0))
            self.comment_text.delete('1.0', tk.END)

if __name__ == '__main__':
    app = App()
    app.mainloop()
