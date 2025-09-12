import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import json
import os

CSV_GOOD = 'Good-Ayrton.csv'
CSV_BAD = 'Bad-Ayrton.csv'
JSON_FILE = 'combined_jsons_without_context_clean_shuffled_part2.json'

# Campos extras do CSV
EXTRA_FIELDS = ['isAlign', 'isEnv', 'isSocial', 'isGovernance', 'isGeneral']

def read_csv(filename):
    if os.path.isfile(filename):
        return pd.read_csv(filename)
    else:
        return pd.DataFrame(columns=[
            'Contexto','Pergunta','Resposta','source_file','stringFilter',
            'isAlign','isEnv','isSocial','isGovernance','isGeneral','Comentários'])

def read_json(filename):
    with open(filename, encoding='utf-8') as f:
        return json.load(f)

def append_csv(filename, row, fieldnames):
    df = read_csv(filename)
    df = pd.concat([df, pd.DataFrame([row], columns=fieldnames)], ignore_index=True)
    df.to_csv(filename, index=False)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Good or Bad CSV Adder')
        # Ajusta o tamanho da janela para 70% da tela
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        width = int(screen_w * 0.7)
        height = int(screen_h * 0.7)
        self.geometry(f'{width}x{height}')

        self.csv_good = read_csv(CSV_GOOD)
        self.csv_bad = read_csv(CSV_BAD)
        self.json_data = read_json(JSON_FILE)
        self.csv_fields = list(self.csv_good.columns) if not self.csv_good.empty else [
            'Contexto','Pergunta','Resposta','source_file','stringFilter',
            'isAlign','isEnv','isSocial','isGovernance','isGeneral','Comentários']

        # Pega a última pergunta do Good e do Bad
        last_question_good = self.csv_good['Pergunta'].iloc[-1] if not self.csv_good.empty else ''
        last_question_bad = self.csv_bad['Pergunta'].iloc[-1] if not self.csv_bad.empty else ''
        last_index_good = self.find_json_index(last_question_good)
        last_index_bad = self.find_json_index(last_question_bad)
        # Começa pelo maior índice
        self.next_index = max(
            last_index_good if last_index_good is not None else -1,
            last_index_bad if last_index_bad is not None else -1
        ) + 1
        self.update_next_data()
        self.create_widgets()

    def update_next_data(self):
        self.next_data = self.json_data[self.next_index] if self.next_index < len(self.json_data) else None

    def update_info_frame(self):
        # Limpa o frame de informações
        for widget in self.info_frame.winfo_children():
            widget.destroy()
        # Adiciona as informações atualizadas
        if self.next_data:
            for key, value in self.next_data.items():
                ttk.Label(self.info_frame, text=f'{key}: {value}', wraplength=1200, justify='left').pack(anchor='w', padx=5, pady=2)
        else:
            ttk.Label(self.info_frame, text='Nenhuma informação disponível').pack(anchor='w', padx=5, pady=2)

    def find_json_index(self, question):
        for i, item in enumerate(self.json_data):
            if item.get('question') == question:
                return i
        return None

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

        # Escolha do CSV
        self.csv_choice = tk.StringVar(value='Good')
        ttk.Radiobutton(self, text='Adicionar ao Good', variable=self.csv_choice, value='Good').pack(anchor='w', padx=10, pady=2)
        ttk.Radiobutton(self, text='Adicionar ao Bad', variable=self.csv_choice, value='Bad').pack(anchor='w', padx=10, pady=2)

        # Botão de salvar
        self.save_button = ttk.Button(self, text='Salvar', command=self.save_entry)
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
        target_csv = CSV_GOOD if self.csv_choice.get() == 'Good' else CSV_BAD
        append_csv(target_csv, row, self.csv_fields)
        messagebox.showinfo('Sucesso', f'Adicionado ao {target_csv}!')
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
