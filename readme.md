# Agendei

Agendei e uma aplicacao web de agendamento desenvolvida com Flask e SQLite. O projeto permite o cadastro e o acesso de usuarios, alem de oferecer uma area dedicada a parceiros comerciais.

Este repositorio faz parte do projeto final do curso CS50, da Harvard University. Ele reune a implementacao desenvolvida para demonstrar os conceitos de Python, Flask, SQL, HTML, CSS e autenticacao estudados durante o curso.

## Tecnologias

- Python
- Flask
- Flask-Session
- SQLite
- HTML e CSS

## Estrutura do projeto

- `app.py`: ponto de entrada da aplicacao. Cria o Flask, configura sessoes, registra os Blueprints, o filtro de moeda, o tratamento de erros e o fechamento da conexao com o banco.
- `helpers.py`: funcoes compartilhadas para exigir login, renderizar erros, formatar valores em reais e abrir/fechar a conexao SQLite.
- `blueprints/client.py`: rotas da area de clientes: pagina inicial, login, cadastro e logout. Tambem impede que parceiros acessem essa area.
- `blueprints/business.py`: rotas da area de parceiros em `/business`: pagina institucional, login, cadastro e pagina inicial. Controla o acesso de parceiros e administradores.
- `blueprints/__init__.py`: inicializacao do pacote de Blueprints.
- `schema.sql`: schema reproduzivel do SQLite, com as tabelas `users`, `business`, `services` e `appointment`.
- `requirements.txt`: dependencias Python necessarias para executar a aplicacao.
- `static/css/styles.css`: estilos visuais compartilhados pelas paginas.
- `static/images/`: icones e imagens usadas pela interface, incluindo o favicon e a imagem de erro.
- `templates/layout.html`: template base compartilhado pelas demais paginas.
- `templates/index.html`: pagina inicial para clientes.
- `templates/login.html`: formulario de login de clientes.
- `templates/register.html`: formulario de cadastro de clientes.
- `templates/business.html`: pagina inicial da area de parceiros.
- `templates/business-login.html`: formulario de login de parceiros.
- `templates/business-register.html`: formulario de cadastro de parceiros.
- `templates/business-home.html`: pagina inicial autenticada do parceiro.
- `templates/apology.html`: pagina exibida para mensagens de erro.
- `templates/svg/apology.svg`: recurso SVG usado na pagina de erro.
- `hello.py`: pequeno programa independente usado nos estudos iniciais de Python.
- `acompanhamento.md`: registro de acompanhamento do desenvolvimento do projeto.
- `Usos de IA no projeto.txt`: registro do uso de ferramentas de IA durante o desenvolvimento.
- `LICENSE`: licenca MIT do projeto.
- `.gitignore`: impede o versionamento de bancos locais, sessoes, ambiente virtual, caches e configuracoes pessoais.

## Banco de dados

O arquivo `agendei.db` e local e fica fora do Git. Para criar uma base vazia a partir do schema:

```bash
sqlite3 agendei.db < schema.sql
```

As senhas sao armazenadas como hash na tabela `users`. O campo `user_type` identifica o tipo de acesso: `1` para parceiro e `2` para cliente.

## Execucao local

Instale as dependencias listadas em `requirements.txt` e execute:

```bash
flask run
```

O banco de dados local e os dados de sessao nao fazem parte do versionamento.
