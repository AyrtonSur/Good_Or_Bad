# Configuração do Google Sheets

## Passo 1: Criar Projeto no Google Cloud Console

1. Acesse https://console.cloud.google.com/
2. Crie um novo projeto ou selecione um existente
3. Ative as APIs necessárias:
   - Google Sheets API
   - Google Drive API

## Passo 2: Criar Credenciais de Serviço

1. Vá em "APIs & Services" > "Credentials"
2. Clique em "Create Credentials" > "Service Account"
3. Preencha os dados do service account
4. Baixe o arquivo JSON de credenciais
5. Renomeie o arquivo para `credentials.json`
6. Coloque o arquivo na pasta do projeto

## Passo 3: Compartilhar as Planilhas

1. Abra cada planilha no Google Sheets
2. Clique em "Share" (Compartilhar)
3. Adicione o email do service account (encontrado no arquivo credentials.json)
4. Dê permissão de "Editor"

## Passo 4: Instalar Dependências

```bash
pip install -r requirements.txt
```

## Passo 5: Executar o Script

```bash
python interface_sheets.py
```

## Estrutura das Planilhas

Certifique-se de que ambas as planilhas (Good e Bad) tenham:
- Página "Ayrton" 
- Página "Pedro"
- Colunas: Contexto, Pergunta, Resposta, source_file, stringFilter, isAlign, isEnv, isSocial, isGovernance, isGeneral, Comentários

## Troubleshooting

- Se der erro de autenticação, verifique se o arquivo credentials.json está correto
- Se der erro de permissão, verifique se o service account foi adicionado às planilhas
- Se der erro de planilha não encontrada, verifique se os nomes das páginas estão corretos
