# Agendei

## 1. Visao geral

Agendei e uma aplicacao web para descoberta e agendamento de servicos. Ela conecta clientes a estabelecimentos e prestadores, permitindo que cada atendimento tenha servico, duracao, data, horario e profissional responsavel.

O projeto foi desenvolvido como trabalho final do curso CS50, com foco em Python, Flask, SQL, autenticacao, HTML, CSS e JavaScript.

Existem dois tipos principais de usuario:

- **Cliente:** pesquisa estabelecimentos, escolhe servico e profissional, consulta horarios livres, cria agendamentos, visualiza seus agendamentos e cancela atendimentos futuros.
- **Parceiro:** e o usuario do tipo provider/owner. Pode cadastrar estabelecimentos, criar servicos, definir duracoes, gerenciar prestadores e acompanhar a propria agenda.

A aplicacao tambem oferece uma pagina de perfil compartilhada entre clientes e parceiros, com edicao de dados pessoais, telefone e troca de senha mediante confirmacao da senha atual.

## 2. Principais fluxos

### Fluxo do cliente

1. Acessa a pagina inicial.
2. Filtra estabelecimentos por estado, cidade, bairro e categoria.
3. Seleciona um estabelecimento e um servico.
4. Escolhe um prestador especifico ou qualquer profissional disponivel.
5. Seleciona uma data no calendario interativo.
6. Escolhe um horario livre, respeitando a duracao do servico e o horario atual.
7. Confirma o agendamento.
8. Consulta ou cancela o atendimento em **Meus Agendamentos**.

### Fluxo do parceiro

1. Cria uma conta de parceiro.
2. Cadastra um estabelecimento com contato e endereco.
3. Cria servicos com preco e duracao em minutos.
4. Participa da equipe do estabelecimento como owner ou provider.
5. Vincula os servicos que atende.
6. Acompanha os agendamentos na agenda do prestador.
7. Gerencia equipe, servicos e dados da conta.

## 3. Tecnologias utilizadas

### Backend

- **Python:** linguagem principal.
- **Flask:** servidor web, rotas, templates e tratamento de requisicoes.
- **Flask-Session:** armazenamento das sessoes em arquivos locais.
- **Werkzeug:** hash e verificacao de senhas por meio de `generate_password_hash` e `check_password_hash`.
- **SQLite:** banco de dados relacional local.

As dependencias Python usadas diretamente pela aplicacao estao em `requirements.txt`. SQLite faz parte da biblioteca padrao do Python, e Werkzeug e Jinja2 sao instalados automaticamente como dependencias do Flask.

### Frontend

- **HTML com Jinja:** templates dinamicos renderizados pelo Flask.
- **Bootstrap 5:** grid responsivo, navbar, cards, formularios, tabelas, badges, alertas, modais e componentes `collapse`.
- **Bootstrap Icons:** icones usados nos botoes e informacoes da interface.
- **JavaScript:** chamadas `fetch` para prestadores e disponibilidade, filtros dependentes e interacoes de perfil.
- **Flatpickr:** calendario interativo usado na escolha da data do agendamento.
- **SCSS:** definicao do tema visual e compilacao dos estilos do projeto.

## 4. Arquitetura da aplicacao

O Flask e iniciado em `app.py`. As rotas sao separadas em dois Blueprints:

- `client_bp`: area publica e area dos clientes.
- `business_bp`: area de parceiros, estabelecimentos e prestadores.

O `layout.html` e o template base. Ele concentra a navbar, o carregamento do CSS/Bootstrap, mensagens flash, rodape e os blocos que os demais templates reutilizam.

O acesso e controlado pela sessao:

- `user_type = 1`: parceiro, provider ou owner.
- `user_type = 2`: cliente.

As rotas de cada Blueprint verificam o tipo de usuario antes de permitir o acesso a sua area.

## 5. Estrutura do projeto

```text
project/
|-- app.py
|-- helpers.py
|-- schema.sql
|-- requirements.txt
|-- blueprints/
|   |-- __init__.py
|   |-- client.py
|   `-- business.py
|-- templates/
|   |-- layout.html
|   |-- index.html
|   |-- login.html
|   |-- register.html
|   |-- profile.html
|   |-- client-appointments.html
|   |-- appointment_new.html
|   |-- business.html
|   |-- business-login.html
|   |-- business-register.html
|   |-- business-home.html
|   |-- business-addbusiness.html
|   |-- business-manage.html
|   |-- business-provider-view.html
|   |-- business-join.html
|   |-- provider-services.html
|   |-- service-create.html
|   `-- apology.html
|-- static/
|   |-- css/
|   |   `-- main.css
|   |-- scss/
|   |   `-- main.scss
|   |-- js/
|   `-- images/
|-- acompanhamento.md
|-- hello.py
`-- LICENSE
```

### Arquivos Python

#### `app.py`

E o ponto de entrada da aplicacao. Suas responsabilidades sao:

- criar a instancia Flask;
- registrar os Blueprints;
- configurar o Flask-Session;
- registrar filtros Jinja, como moeda e telefone;
- disponibilizar a rota `/profile`;
- configurar mensagens flash e tratamento de erro 404;
- fechar a conexao do banco ao final da requisicao.

#### `helpers.py`

Reune funcoes compartilhadas:

- `login_required`: exige usuario autenticado;
- `apology`: renderiza a pagina padrao de erro;
- `get_db` e `close_db`: abrem e fecham a conexao SQLite;
- `normalize_phone` e `format_phone`: validam e exibem telefones brasileiros;
- `normalize_street`: padroniza nomes de logradouros;
- `category_slug`: cria identificadores usados na estilizacao das categorias;
- `_ensure_booking_columns` e `_ensure_contact_columns`: fazem a migracao leve do banco existente.

#### `blueprints/client.py`

Concentra as funcionalidades dos clientes:

- pagina inicial e filtros de localizacao;
- login, cadastro e logout;
- criacao de agendamento;
- API de prestadores por servico;
- API de disponibilidade;
- pagina de meus agendamentos;
- cancelamento de agendamento pelo proprio cliente.

#### `blueprints/business.py`

Concentra a area de parceiros:

- login e cadastro de providers/owners;
- cadastro e listagem de estabelecimentos;
- entrada em equipes;
- aprovacao e remocao de prestadores;
- ativacao do owner como provider;
- criacao e exclusao de servicos;
- configuracao dos servicos atendidos por cada provider;
- agenda individual do prestador.

## 6. Frontend, Bootstrap e SCSS

O template `layout.html` carrega o CSS compilado em `static/css/main.css` e o JavaScript do Bootstrap 5 por CDN. Os templates utilizam classes Bootstrap para manter o layout responsivo sem criar componentes visuais do zero.

Os principais componentes utilizados sao:

- `navbar`: navegacao entre Home, perfil, agendamentos e logout;
- `card`: estabelecimentos, servicos, perfil e agendamentos;
- `row`, `col-*` e utilitarios flex: responsividade;
- `form-control`, `form-select` e `input-group`: formularios;
- `badge`: categorias e estados de agendamento;
- `table`: agendas de providers;
- `collapse`: detalhes expandidos dos agendamentos do cliente;
- `alert`: mensagens de sucesso e erro;
- `modal`: aviso de login necessario para agendar.

O arquivo `static/scss/main.scss` configura o Bootstrap antes da compilacao. Ele define a paleta Catppuccin Mocha, cores do tema, fundo do body, cards, formularios, navbar, tabelas, dropdowns e badges de categoria. O resultado compilado fica em `static/css/main.css`.

O calendario de agendamento e o Flatpickr. Ele e carregado por CDN em `appointment_new.html`, inicializado como calendario inline e estilizado com as variaveis CSS do Bootstrap para acompanhar o tema do SCSS.

## 7. Banco de dados

O banco de desenvolvimento e o arquivo local `agendei.db`. Ele nao deve ser versionado. O arquivo `.gitignore` tambem exclui sessoes Flask, ambiente virtual e caches.

### Tabelas principais

- `users`: usuarios, nome, sobrenome, username, hash da senha, telefone e tipo de acesso.
- `business`: estabelecimentos, owner, telefone, categoria e endereco.
- `services`: servicos oferecidos, preco e duracao em minutos.
- `business_providers`: vinculo entre estabelecimento e provider/owner, com papel e status.
- `provider_services`: vinculo entre prestador e servicos que ele atende.
- `appointment`: cliente, prestador, servico, data, horario, duracao e status.

### Relacionamentos

```text
users 1----N appointment N----1 services N----1 business
	|                                      |
	`----N business_providers N------------`
							|
							`----N provider_services ---- services
```

Um cliente cria um `appointment` para um `service`. O servico pertence a um `business`. O prestador escolhido vem dos vinculos de `business_providers` e `provider_services`.

### Disponibilidade

A API `/api/availability` considera:

- a duracao configurada no servico;
- os horarios de funcionamento da grade atual, das 08:00 as 18:00;
- agendamentos existentes do prestador;
- conflitos de intervalo entre inicio e fim;
- horario atual, impedindo slots que ja passaram no dia atual.

O backend repete a validacao no momento da criacao do agendamento. Portanto, esconder um horario no frontend nao e a unica protecao.

### Schema e migracao

`schema.sql` documenta a estrutura base do banco. Como o projeto evoluiu durante o desenvolvimento, `helpers.py` verifica o banco ao abrir a conexao e adiciona colunas novas quando necessario, incluindo:

- `services.duration_minutes`;
- `appointment.appointment_time`;
- `appointment.duration_minutes`;
- `users.phone`;
- `business.phone`.

Os registros antigos recebem numeros ficticios unicos para preencher os telefones. Tambem sao criados indices unicos para impedir telefones repetidos entre usuarios e entre estabelecimentos.

Para criar uma base inicial manualmente:

```bash
sqlite3 agendei.db < schema.sql
```

Ao iniciar a aplicacao, a migracao leve de `helpers.py` completa as colunas necessarias para a versao atual.

## 8. Como instalar e executar

### Requisitos

- Python 3.10 ou superior;
- SQLite 3;
- `pip`;
- opcionalmente, Sass/Live Sass Compiler se for recompilar o SCSS.

### Ambiente virtual

No Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

No Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Banco

Se ainda nao existir um banco local:

```bash
sqlite3 agendei.db < schema.sql
```

Se o banco ja existir, nao e necessario apagar os dados. A aplicacao executa as migracoes leves ao abrir a conexao.

### Iniciar o servidor

Com o ambiente virtual ativado:

```bash
python app.py
```

Depois acesse `http://127.0.0.1:5000` no navegador.

Tambem e possivel iniciar usando a CLI do Flask:

```bash
flask --app app run --debug
```

## 9. Como usar

### Como cliente

1. Acesse `/register` e crie uma conta com nome, username, telefone e senha.
2. Entre pela pagina `/login`.
3. Na Home, selecione estado, cidade, bairro ou categoria para filtrar estabelecimentos.
4. Clique em **Agendar Atendimento**.
5. Escolha o servico, o profissional, a data e um horario disponivel.
6. Confirme o atendimento.
7. Use **Meus Agendamentos** para consultar detalhes, telefone e endereco do estabelecimento.
8. Cancele um atendimento futuro pelo botao **Cancelar**.
9. Use **Meu Perfil** para editar dados ou trocar a senha. A troca exige a senha atual.

### Como parceiro, provider ou owner

1. Acesse `/business/register` para criar uma conta de parceiro.
2. Entre pela area `/business/login`.
3. Cadastre um estabelecimento em **Cadastrar Local**.
4. Informe telefone, endereco, categoria e descricao do estabelecimento.
5. Abra o gerenciamento do local e crie os servicos oferecidos.
6. Defina o preco e a duracao de cada servico.
7. Ative-se como provider ou aprove prestadores da equipe.
8. Configure quais servicos cada provider atende.
9. Acesse **Ver Minha Agenda** ou **Ver Agenda de Atendimentos** para consultar os atendimentos.
10. Use **Meu Perfil** para atualizar seus dados e senha.

## 10. Desenvolvimento e arquivos locais

- `agendei.db`: banco local, ignorado pelo Git.
- `flask_session/`: arquivos de sessao, ignorados pelo Git.
- `venv/`: ambiente virtual Python, ignorado pelo Git.
- `__pycache__/`: arquivos temporarios do Python.
- `LICENSE`: licenca do projeto.

Antes de enviar alteracoes, e recomendavel verificar a sintaxe:

```bash
python -m py_compile app.py helpers.py blueprints/client.py blueprints/business.py
```
