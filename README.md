# Guia de Uso do Projeto

## Arquivos Disponíveis

- `interface.py` - Versão que trabalha com arquivos CSV locais
- `interface_sheets.py` - Versão que trabalha com Google Sheets
- `SETUP_GOOGLE_SHEETS.md` - Instruções para configurar Google Sheets

## Requisitos
- Python 3
- pip
- venv
- Tkinter (interface gráfica)

## Passos para rodar o projeto (Linux/Ubuntu)

1. **Instale o Python 3 e ferramentas necessárias**
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-venv python3-pip
   ```

2. **Instale o Tkinter**
   ```bash
   sudo apt-get install python3-tk
   ```

3. **Crie e ative o ambiente virtual**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Instale as dependências do projeto**
   ```bash
   pip install -r requirements.txt
   ```

5. **Execute o script**
   
   Para versão CSV local:
   ```bash
   python interface.py
   ```
   
   Para versão Google Sheets (requer configuração adicional):
   ```bash
   python interface_sheets.py
   ```

## Passos para rodar o projeto (Windows)

1. **Instale o Python 3**
   - Baixe e instale o Python pelo site oficial: https://www.python.org/downloads/
   - Certifique-se de marcar a opção "Add Python to PATH" durante a instalação.

2. **Instale o Tkinter**
   - Tkinter já vem incluído na instalação padrão do Python para Windows.

3. **Crie e ative o ambiente virtual**
   Abra o Prompt de Comando (cmd) na pasta do projeto e execute:
   ```cmd
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Instale as dependências do projeto**
   ```cmd
   pip install -r requirements.txt
   ```

5. **Execute o script**
   
   Para versão CSV local:
   ```cmd
   python interface.py
   ```
   
   Para versão Google Sheets (requer configuração adicional):
   ```cmd
   python interface_sheets.py
   ```

## Configuração do Google Sheets

Para usar a versão Google Sheets, siga as instruções detalhadas no arquivo `SETUP_GOOGLE_SHEETS.md`.

---
Esses passos funcionam em qualquer distribuição Linux baseada em Debian/Ubuntu e em Windows 10/11. Se estiver usando outra distribuição ou versão do Windows, adapte os comandos conforme necessário. Se tiver problemas com Tkinter, verifique se o Python foi instalado corretamente e se está usando o ambiente virtual ativado.
