# DIARIO DE DESENVOLVIMENTO
## Rotas, login e segurança:
Diferente do problem set "finance" como o projeto contempla diferentes tipos de usuários com diferentes áreas de acesso e escopo. Utilizei a recomendação do framework FLASK de estruturar as páginas e acessos com **blueprints**.  

Dessa maneira foi possivel garantir que usuários logados em um determinado tipo de cota não acessassem as páginas de outro tipo de conta.

- Para ter um controle interno de cada blueprint sobre áreas com login obrigatorio ou não, mantive o recurso do decorador **@login_required** dentro do blueprint.

- Para a diferenciação de contas foi construido no banco de dados user_type
e na aplicação uma variável global de lista que armazena os tipos de conta, podendo ser expansivo caso necessário.

- Assim como no "finance" utilizei querys para buscar validar os registros e logins das contas, com proteção evitando entradas maliciosas e equivocadas nos formulários da página.

## HTTP Errors:
Para lidar com erros HTTP, entradas inválidas de usuário e páginas inexistentes adaptei o código **appology** do curso para um que utiliza um **SVG** inserido com **JINJA** permitindo estilização com CSS, que foi montaod no helpers.py

### Helpers:
```py
def apology(message, code=400):
    """Render message as an apology to user."""
    return render_template("apology.html", message=message, code=code), code
```
### Template:
```html
{% extends "layout.html" %}

{% block title %}
Apology
{% endblock %}

{% block body %}

<div class="text-center">
    <h2 class="mb-3">{{ code }}</h2>
    <h2 class="mb-3">{{ message }}</h2>

<div class="apology-icon mt-3">
    {% include "svg/apology.svg" %}
</div>

</div>
{% endblock %}
```

## CSS
O estilo visual do site é construido com **Bootstrap**, com padrão de cores baseados no tema **catppuccin** do VScode.