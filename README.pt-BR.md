<p align="center">
  <img src="templates/svg/agendei_logo-full.svg" alt="Agendei Logo" width="300">
</p>

# Agendei

### Video Demo: https://www.youtube.com/watch?v=yOo3XS8nt2Q&t=29s

*Leia isto em outros idiomas: [English](README.md)*

## 1. Visão Geral

O **Agendei** é uma aplicação web para descoberta e agendamento de serviços. Ela conecta clientes a estabelecimentos e prestadores, permitindo que cada atendimento tenha serviço, duração, data, horário e profissional responsável.

O projeto foi desenvolvido como trabalho final do curso **CS50** de Harvard, com foco em Python, Flask, SQL, autenticação, HTML, CSS e JavaScript.

Existem dois tipos principais de usuário:

- **Cliente:** Pesquisa estabelecimentos, escolhe serviço e profissional, consulta horários livres, cria agendamentos, visualiza seus agendamentos e cancela atendimentos futuros.
- **Parceiro (Owner/Provider):** Cadastra estabelecimentos, cria serviços, define durações, gerencia prestadores e acompanha a própria agenda.

A aplicação também oferece uma página de perfil compartilhada entre clientes e parceiros, com edição de dados pessoais, telefone e troca de senha mediante confirmação da senha atual.

---

## 2. Principais Fluxos

<details>
  <summary><b>Fluxo do Cliente</b> (Clique para expandir)</summary>

1. Acessa a página inicial.
2. Filtra estabelecimentos por estado, cidade, bairro e categoria.
3. Seleciona um estabelecimento e um serviço.
4. Escolhe um prestador específico ou qualquer profissional disponível.
5. Seleciona uma data no calendário interativo.
6. Escolhe um horário livre, respeitando a duração do serviço e o horário atual.
7. Confirma o agendamento.
8. Consulta ou cancela o atendimento em **Meus Agendamentos**.
</details>

<details>
  <summary><b>Fluxo do Parceiro</b> (Clique para expandir)</summary>

1. Cria uma conta de parceiro.
2. Cadastra um estabelecimento com contato e endereço.
3. Cria serviços com preço e duração em minutos.
4. Participa da equipe do estabelecimento como *owner* ou *provider*.
5. Vincula os serviços que atende.
6. Acompanha os agendamentos na agenda do prestador.
7. Gerencia equipe, serviços e dados da conta.
</details>

---

## 3. Tecnologias Utilizadas

<details>
  <summary><b>Backend</b> (Clique para expandir)</summary>

- **Python:** Linguagem principal.
- **Flask:** Servidor web, rotas, templates e tratamento de requisições.
- **Flask-Session:** Armazenamento das sessões em arquivos locais.
- **Werkzeug:** Hash e verificação de senhas por meio de `generate_password_hash` e `check_password_hash`.
- **SQLite:** Banco de dados relacional local.

*As dependências Python usadas diretamente pela aplicação estão em `requirements.txt`. O SQLite faz parte da biblioteca padrão do Python, enquanto Werkzeug e Jinja2 são instalados automaticamente como dependências do Flask.*
</details>

<details>
  <summary><b>Frontend</b> (Clique para expandir)</summary>

- **HTML com Jinja:** Templates dinâmicos renderizados pelo Flask.
- **Bootstrap 5:** Grid responsivo, navbar, cards, formulários, tabelas, badges, alertas, modais e componentes `collapse`.
- **Bootstrap Icons:** Ícones usados nos botões e informações da interface.
- **JavaScript:** Chamadas `fetch` para prestadores e disponibilidade, filtros dependentes e interações de perfil.
- **Flatpickr:** Calendário interativo usado na escolha da data do agendamento.
- **SCSS:** Definição do tema visual e compilação dos estilos do projeto.
</details>

---

## 4. Arquitetura da Aplicação

O Flask é iniciado em `app.py`. As rotas são separadas em dois **Blueprints**:

- `client_bp`: Área pública e área dos clientes.
- `business_bp`: Área de parceiros, estabelecimentos e prestadores.

O `layout.html` é o template base. Ele concentra a navbar, o carregamento do CSS/Bootstrap, mensagens *flash*, rodapé e os blocos que os demais templates reutilizam.

O acesso é controlado pela sessão:
- `user_type = 1`: Parceiro (*provider* ou *owner*).
- `user_type = 2`: Cliente.

---

## 5. Decisões de Design

### Separação por Blueprint e limites de acesso

A aplicação é dividida entre `client_bp` e `business_bp` para que cada área tenha um limite de responsabilidade claro. Essa separação não é apenas organizacional: cada Blueprint possui proteções por requisição que verificam o tipo de usuário na sessão antes de liberar rotas protegidas. Assim, clientes e parceiros têm fluxos, rotas e painéis realmente separados, enquanto o perfil compartilhado permanece disponível de forma intencional para os dois tipos de usuário.

### Modelo unificado de conta Business

A área Business foi projetada com uma única conta de parceiro, em vez de contas separadas para proprietário e prestador. Qualquer usuário Business pode criar um novo estabelecimento ou solicitar participação em uma equipe existente. O tipo geral da conta identifica apenas que se trata de um parceiro; o papel efetivo é definido por estabelecimento, através da relação entre `business.owner_id` e `business_providers`, que registra papel, status, vínculo de prestador e solicitações pendentes.

Esse modelo mantém a conta flexível sem perder o controle explícito de autorização. Um usuário pode ser proprietário de um estabelecimento e prestador em outro, sem precisar de contas duplicadas ou de uma migração manual de papel. O fluxo de solicitação é necessário porque entrar em uma equipe não deve conceder permissão imediatamente: o prestador envia a solicitação, o proprietário analisa e somente a aprovação, com vínculo ativo, libera os recursos da equipe e a associação aos serviços.

Essa distinção também orienta a interface. O menu inicial Business oferece tanto a criação de um estabelecimento quanto a opção de procurar e solicitar entrada em uma equipe. Os cards dos estabelecimentos identificam se o usuário atual é proprietário ou prestador ativo e exibem as ações correspondentes. Proprietários acessam um dashboard de gestão com serviços, equipe, solicitações pendentes e agendamentos; prestadores recebem um dashboard focado nos serviços atribuídos e na própria agenda. Assim, uma única conta permanece simples de usar, sem esconder as responsabilidades diferentes existentes dentro de cada estabelecimento.

### Linguagem visual centralizada com SCSS

O SCSS concentra a maior parte das regras visuais próprias do projeto em um único lugar, evitando espalhar valores do tema pelos templates. Isso facilita manter de forma consistente a paleta Catppuccin, as sobrescritas do Bootstrap, espaçamentos, superfícies e comportamento responsivo. Os templates ficam concentrados em estrutura e conteúdo, enquanto o CSS compilado carrega o sistema visual.

### Registro progressivo de agendamentos com JavaScript

A página de agendamento utiliza JavaScript e requisições assíncronas com `fetch` para carregar progressivamente os prestadores e os horários disponíveis depois que o cliente escolhe serviço, profissional e data. Isso torna a interação mais fluida e evita criar um HTML separado para cada estado intermediário. O servidor continua recalculando a disponibilidade e validando o agendamento final, portanto a interação no cliente não substitui a validação no backend.

### Funções helper pequenas e focadas

Os comportamentos compartilhados ficam em `helpers.py`, por meio de funções específicas como `login_required` para controle de acesso, `apology` para erros padronizados, `get_db` e `close_db` para o ciclo de vida do banco, `normalize_phone` e `normalize_street` para normalização de entradas e helpers de formatação de moeda, telefone e slug de categoria. Manter essas responsabilidades em funções pequenas reduz duplicação nas rotas e oferece um único lugar para evoluir cada comportamento repetido.

### Filtros hierárquicos de localização em vez de coordenadas

Os estabelecimentos armazenam campos estruturados como estado, cidade, bairro e logradouro. A página inicial utiliza queries SQL e filtros dependentes para restringir os resultados seguindo essa hierarquia. Essa foi uma decisão deliberada de escopo: uma busca baseada em coordenadas exigiria geocodificação, dados cartográficos e APIs externas, aumentando a complexidade operacional e dificultando a divulgação aberta do projeto. Para um projeto desse tamanho, filtros SQL são suficientes para demonstrar claramente a descoberta de estabelecimentos sem adicionar uma infraestrutura que não é essencial ao problema central de agendamento.

---

## 6. Estrutura do Projeto

<details>
  <summary><b>Visualizar Árvore de Arquivos e Detalhes</b> (Clique para expandir)</summary>

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

### Arquivos Python Principais

- **`app.py`**: Ponto de entrada da aplicação. Cria a instância Flask, registra os Blueprints, configura o Flask-Session, registra filtros Jinja (moeda e telefone), disponibiliza a rota `/profile` e encerra conexões do banco ao final da requisição.
- **`helpers.py`**: Reúne funções compartilhadas, como decorador de autenticação (`login_required`), renderizador de erros (`apology`), conexões com banco (`get_db`, `close_db`), normalização de dados (telefone/logradouro) e migração leve do banco.
- **`blueprints/client.py`**: Concentra a lógica de clientes (filtros, agendamento, API de disponibilidade e cancelamentos).
- **`blueprints/business.py`**: Concentra a lógica de parceiros (gestão de estabelecimentos, equipes, criação de serviços e agenda dos prestadores).
</details>

---

## 7. Banco de Dados e Migrações

<details>
  <summary><b>Estrutura e Lógica de Disponibilidade</b> (Clique para expandir)</summary>

O banco de desenvolvimento é o arquivo local `agendei.db` (ignorado pelo Git).

### Tabelas Principais
- `users`: Usuários, nome, sobrenome, username, hash da senha, telefone e tipo de acesso.
- `business`: Estabelecimentos, owner, telefone, categoria e endereço.
- `services`: Serviços oferecidos, preço e duração em minutos.
- `business_providers`: Vínculo entre estabelecimento e provider/owner, com papel e status.
- `provider_services`: Vínculo entre prestador e serviços que ele atende.
- `appointment`: Cliente, prestador, serviço, data, horário, duração e status.

### Relacionamentos

```text
users 1----N appointment N----1 services N----1 business
    |                                      |
    `----N business_providers N------------`
                            |
                            `----N provider_services ---- services
```

### Disponibilidade Dinâmica
A API `/api/availability` calcula os horários livres considerando:
- A duração configurada no serviço.
- Os horários de funcionamento da grade (08:00 às 18:00).
- Agendamentos existentes do prestador.
- Conflitos de intervalo entre início e fim.
- Horário atual (bloqueando horários passados no mesmo dia).

A validação é feita no frontend e repetida estritamente no backend antes da inserção no banco de dados.
</details>

---

## 8. Como Instalar e Executar

### Pré-requisitos

- Python 3.10 ou superior
- SQLite 3
- Gerenciador de pacotes `pip`

### Passo a Passo

1. **Clone o repositório e crie um ambiente virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # No Windows: venv\Scripts\Activate.ps1
   ```

2. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Inicialize o banco de dados:**
   ```bash
   sqlite3 agendei.db < schema.sql
   ```

4. **Inicie a aplicação:**
   ```bash
   python app.py
   # Ou utilizando a CLI do Flask:
   # flask --app app run --debug
   ```
   Acesse `http://127.0.0.1:5000` no navegador.

---

## 9. Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.