from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta

"""
project_web.py

Aplicação Flask para gerenciamento de reservas de carros:
- Conexão com SQLite para persistência de usuários, carros, reservas e pagamentos.
- Rotas para login, cadastro, listagem de carros, CRUD de reservas e processamento de pagamento.
- Uso de sessões para controle de autenticação e totais de pagamento.
"""


#criar base de dados no sqlite (primeiro passo)
app = Flask(__name__)
app.secret_key= 'chave_super_secreta_444'   #Usada para criptografar cookies da sessão
app.config["DEBUG"] = True              #Modo Debug habilitado

#filtro para converter string de data para objeto date
@app.template_filter('todate')
def todate_filter(value, format="%Y-%m-%d"):
    """
    Converte string no formato YYYY-MM-DD para objeto date do Python.
    Uso em Jinja: {{ '2025-05-01'|todate }} retorna datetime.date(2025, 5, 1).
    """
    try:
        return datetime.strptime(value,format).date()
    except:
        return value

#conectar base de dados ao projeto
def conectar_bd():
    conn = sqlite3.connect("database/banco_de_dados.db")
    conn.row_factory = sqlite3.Row
    return conn

#criação das tabelas da base de dados
def criar_tabelas():
     #Cria as tabelas no banco SQLite caso não existam:
     #- usuarios (login e senha)
     #- carros (modelo, categoria, preço etc.)
     #- reservas (relaciona usuário, carro e datas)
     #- pagamentos (dados de cartão vinculados à reserva)
     
    conn= conectar_bd()
    cursor= conn.cursor()
    cursor.executescript('''
                        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            marca TEXT NOT NULL,
            modelo TEXT NOT NULL,
            categoria TEXT NOT NULL,
            transmissao TEXT NOT NULL,
            tipo TEXT NOT NULL,
            capacidade INTEGER NOT NULL,
            imagem TEXT NOT NULL,
            valor_diaria REAL NOT NULL,
            ultima_revisao DATE NOT NULL,
            proxima_revisao DATE NOT NULL,
            ultima_inspecao DATE NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS reservas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            veiculo_id INTEGER NOT NULL,
            data_inicio DATE NOT NULL,
            data_fim DATE NOT NULL,
            valor_total REAL NOT NULL,
            status TEXT DEFAULT 'Ativa',
            FOREIGN KEY (cliente_id) REFERENCES clientes(id),
            FOREIGN KEY (veiculo_id) REFERENCES veiculos(id)
        );
        
        CREATE TABLE IF NOT EXISTS pagamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reserva_id INTEGER NOT NULL,
            numero_cartao TEXT NOT NULL,
            nome_cartao TEXT NOT NULL,
            validade TEXT NOT NULL,
            codigo_seg INTEGER NOT NULL,
            FOREIGN KEY (reserva_id) REFERENCES reservas(id)
        );
    ''')
    conn.commit()
    conn.close()

#Vamos agora criar uma função para verificar se existe o usuário
def verificar_usuario(usuario, senha):
 #Valida credenciais de login.
    
#Args:
    #usuario (str): nome de usuário.
    #senha (str): senha em texto plano.
    
#Returns:
    #dict | None: dados do usuário (id, nome) se válido, ou None caso contrário.

    conn= conectar_bd()
    cursor=conn.cursor()
    cursor.execute("SELECT * FROM clientes WHERE usuario = ? AND senha = ?", (usuario,senha))
    usuario_encontrado= cursor.fetchone()
    conn.close()
    return usuario_encontrado

#função para registar um novo utilizador
def registar_usuario(nome, usuario, senha):
    conn= conectar_bd()
    cursor= conn.cursor()
    cursor.execute("INSERT INTO clientes (nome, usuario, senha) VALUES (?, ?, ?)", (nome, usuario, senha))
    conn.commit()
    conn.close()

#página inicial (login/registo)
@app.route('/', methods=  ['GET','POST'])
def home ():
    mensagem = None #mensagem de erro se existir
    #Na página de login/registo vamos verificar se todos os requisitos são preenchidos
    if request.method == "POST":    
        if 'nome' in request.form and 'senha_confirmacao' in request.form:
            nome= request.form['nome']
            usuario = request.form ['usuario']
            senha =request.form ['senha']
            senha_confirmacao=request.form['senha_confirmacao']

            if senha != senha_confirmacao:
                mensagem= "As senhas não coincidem."

            else: 
                try:
                    conn =conectar_bd()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO clientes (nome, usuario, senha) VALUES (?,?,?)", (nome,usuario, senha))
                    conn.commit()
                    conn.close()
                    mensagem= "Registo efetuado com sucesso! Agora podes realizar o login."
                except sqlite3.IntegrityError:
                    mensagem= "Este nome do usuário ja se encontra registado."
    if 'usuario' in request.form and 'senha' in request.form:
        usuario= request.form['usuario']
        senha= request.form['senha']

        usuario_encontrado= verificar_usuario(usuario,senha)
        if usuario_encontrado:
            session['usuario'] = usuario_encontrado[2] #guarda o nome do usuário na sessão
            return redirect(url_for('listar_carros')) #Redireciona para a página listar_carros após executar login
            
        else:
            mensagem = "Credenciais inválidas, tente novamente."
            
    return render_template('index.html', mensagem=mensagem)


#Página com todos os carros
@app.route('/carros', methods=['GET']) #define a rota da página
def listar_carros():
    #Verificar se o utilizador está autenticado
    if 'usuario' not in session:
        return redirect(url_for('home'))
    #obtem a data de hoje
    hoje = date.today().isoformat()
    #calcula a data daqui a 1 ano para o filtro de inspeção obrigatório
    um_ano = (date.today() + relativedelta(years=1)).isoformat()
    
    #conectar á base de dados
    conn= conectar_bd()
    cursor = conn.cursor()

    # Monta a query principal com filtros de inspeção e revisão e exclusão de veículos reservados
    sql_base = '''
    SELECT v.*
    FROM veiculos v
    WHERE v.id NOT IN (
    SELECT r.veiculo_id
    FROM reservas r
    WHERE date(r.data_fim) >= DATE('now')
        AND r.status = 'Ativa'
        )
    '''
    parametros = []


    #Recolher os filtros enviados por GET (pesquisa e filtros laterais)
    pesquisa= request.args.get('pesquisa', "")
    #parametros = [um_ano, hoje, hoje,hoje]

    if pesquisa:
         # Adiciona filtro de pesquisa por marca, modelo ou categoria
        sql_base += """
            AND (v.marca LIKE ?
              OR v.modelo LIKE ?
              OR v.categoria LIKE ?)
        """
        pesquisa_like = f'%{pesquisa}%'
        parametros.extend([pesquisa_like, pesquisa_like, pesquisa_like])

    # Executa a query final com placeholders para evitar SQL injection
    cursor.execute(sql_base, tuple(parametros))
    carros = cursor.fetchall()
    conn.close()

    # Renderiza template passando lista filtrada de carros e termo de pesquisa
    return render_template('carros.html', carros=carros, pesquisa=pesquisa)
#Função vou inserir os carros para o utilizador ter acesso
def inserir_carros():
    conn = conectar_bd()
    cursor = conn.cursor()

    #Verificar se já existem carros, para não correr o risco de ficarem duplicados
    cursor.execute("SELECT COUNT (*) FROM veiculos")
    total= cursor.fetchone()[0]

    if total > 0:
        conn.close()
        return #já existem carros

    carros = [
         # marca, modelo, categoria, transmissao, tipo, capacidade, imagem, valor_diaria, ultima_revisao, proxima_revisao, ultima_inspecao
        ("Toyota", "Yaris", "Pequeno", "Manual", "Carro", 4, "yaris.jpg", 30.0, "2024-01-10", "2025-01-10", "2024-02-10"),
        ("Honda", "Civic", "Médio", "Automática", "Carro", 5, "civic.jpg", 45.0, "2024-01-05", "2025-01-05", "2024-02-01"),
        ("BMW", "X5", "SUV", "Automática", "Carro", 5, "bmw_x5.jpg", 120.0, "2023-08-01", "2024-08-01", "2023-09-01"),
        ("Audi", "A8", "Luxo", "Automática", "Carro", 5, "audi_a8.jpg", 160.0, "2024-01-15", "2025-01-15", "2024-01-20"),
        ("Fiat", "500", "Pequeno", "Manual", "Carro", 4, "fiat_500.jpg", 28.0, "2024-02-01", "2025-02-01", "2024-02-10"),
        ("Kawasaki", "Ninja 400", "Médio", "Manual", "Mota", 2, "ninja_400.jpg", 40.0, "2024-03-01", "2025-03-01", "2024-03-10"),
        ("Yamaha", "TMAX", "Grande", "Automática", "Mota", 2, "tmax.jpg", 50.0, "2024-01-20", "2025-01-20", "2024-02-01")
    ]

    cursor.executemany('''
        INSERT INTO veiculos (
            marca, modelo, categoria, transmissao, tipo, capacidade, imagem, valor_diaria,
            ultima_revisao, proxima_revisao, ultima_inspecao
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', carros)

    conn.commit()
    conn.close()



@app.route("/reservar/<int:carro_id>", methods=["GET", "POST"])
def reservar_carro(carro_id):

#Rota para mostrar o formulário de reserva (GET) e processar a reserva (POST).
#Em GET: busca sempre o carro pelo ID e exibe o template.
#Em POST: valida datas, obtém cliente, calcula total, cria reserva e redireciona ao pagamento.
     
    if 'usuario' not in session:
        return redirect(url_for('home'))
    
    conn = conectar_bd()
    cursor = conn.cursor()

# Busca o carro no GET para preencher template e no POST para cálculo
    cursor.execute("SELECT * FROM veiculos WHERE id = ?", (carro_id,))
    carro = cursor.fetchone()
    if not carro:
        conn.close()
        return "Carro não encontrado", 404
    
    if request.method == "POST":
        data_inicio_str = request.form['data_inicio']
        data_fim_str = request.form['data_fim']
        usuario = session['usuario']

        # Converte para datetime.date
        data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        data_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()

        # Validação: fim não pode ser antes de início
        if data_fim < data_inicio:
            conn.close()
            return "A data de fim não pode ser anterior à data de início.", 400

        # Busca ID do cliente
        cursor.execute("SELECT id FROM clientes WHERE usuario = ?", (usuario,))
        cliente = cursor.fetchone()
        if not cliente:
            conn.close()
            return f"Cliente não encontrado para o usuário {usuario}.", 404
        cliente_id = cliente['id']

        # Calcula dias e total
        dias = (datetime.strptime(data_fim, "%Y-%m-%d") - datetime.strptime(data_inicio, "%Y-%m-%d")).days + 1
        valor_diaria = carro['valor_diaria']
        total = dias * valor_diaria

        # Insere reserva
        cursor.execute("""
            INSERT INTO reservas 
                (cliente_id, veiculo_id, data_inicio, data_fim, valor_total, status)
            VALUES (?, ?, ?, ?, ?, 'Ativa')
        """, (cliente_id, carro_id, data_inicio_str, data_fim_str, total))
        conn.commit()
        reserva_id = cursor.lastrowid

        # Armazena o total a pagar na sessão para exibir no pagamento
        session['total_a_pagar'] = total
        #'total_a_pagar': valor calculado da reserva que será exibido na página de pagamento.
        # Certifica-se de remover qualquer diferença pré-existente
        session.pop('diferenca_pagamento', None)

        conn.close()
        # Redireciona para a tela de pagamento
        return redirect(url_for('pagamento', reserva_id=reserva_id))

    conn.close()
    return render_template("reserva.html", carro=carro)

#Rota de pagamento após uma reserva
@app.route('/pagamento/<int:reserva_id>', methods=['GET', 'POST'])
def pagamento(reserva_id):

    """
    Rota para exibir valores e processar o pagamento:
    - Usa session['total_a_pagar'] e, se existir >0, session['diferenca_pagamento'].
    - Ao concluir (POST), insere em pagamentos e limpa ambas as chaves na sessão.
    """

    if 'usuario' not in session:
        return redirect(url_for('home'))
    
    conn = conectar_bd()
    cursor = conn.cursor()

    # Recupera apenas o mínimo de dados da reserva (pode ser usado para validação extra)
    cursor.execute("SELECT id FROM reservas WHERE id = ?", (reserva_id,))
    if not cursor.fetchone():
        conn.close()
        return "Reserva não encontrada.", 404

    # Carrega valores da sessão
    valor_total = session.get('total_a_pagar', 0)
    diferenca = session.get('diferenca_pagamento', 0)
    mostrar_alteracao = (diferenca > 0)

    #Verifica se o formulário foi submetido
    if request.method == 'POST':
        #Recolhe os dados do formulário
        numero_cartao = request.form['numero_cartao']
        nome_cartao = request.form['nome_cartao']
        validade= request.form['validade']
        codigo_seg = request.form['codigo_seg']


        #insere os dados do pagamento
        cursor.execute("""
            INSERT INTO pagamentos (reserva_id, numero_cartao, nome_cartao, validade, codigo_seg)
            VALUES (?, ?, ?, ?, ?)
        """, (reserva_id, numero_cartao, nome_cartao, validade, codigo_seg))
        conn.commit()

        #limpar a diferença da sessão após o pagamento
        session.pop('diferenca_pagamento', None)
        session.pop('total_a_pagar', None)

        conn.close()
        #mostra a mensagem e redireciona o utilizador para a página "minhas_reservas"
        flash ('Pagamento realizado com sucesso!', 'sucess')
        #Mensagem de confirmação de reserva, categoria 'success' para estilização no template.
        return redirect(url_for('minhas_reservas'))

    conn.close()
    #Se for pedido GET, mostra o formulário de pagamento
    return render_template('pagamento.html', reserva_id=reserva_id, valor_total= valor_total, mostrar_alteracao=mostrar_alteracao, valor_alteracao=diferenca)

@app.route("/minhas_reservas")
def minhas_reservas():
    if 'usuario' not in session:
        return redirect(url_for('home')) #se não estiver logado
    
    usuario = session['usuario']
    conn= conectar_bd()
    cursor = conn.cursor()

    #Obter ID do cliente com base no nome do utilizador da sessão
    cursor.execute("SELECT id FROM clientes WHERE usuario = ?", (usuario,))
    cliente= cursor.fetchone()

    if cliente:
        cliente_id = cliente[0]

        #Obter todas as reservas feitas por este cliente
        cursor.execute("""
            SELECT reservas.id, veiculos.marca, veiculos.modelo, reservas.data_inicio, reservas.data_fim, veiculos.valor_diaria, reservas.status
            FROM reservas
            JOIN veiculos ON reservas.veiculo_id = veiculos.id
            WHERE reservas.cliente_id = ?
        """, (cliente_id,))
        reservas = []
        for row in cursor.fetchall():
            id, marca, modelo, data_inicio, data_fim, valor_diaria, status = row
            dias = (datetime.strptime(data_fim, "%Y-%m-%d") - datetime.strptime(data_inicio, "%Y-%m-%d")).days + 1
            total = dias * valor_diaria
            reservas.append({
                "id": id,
                "marca": marca,
                "modelo": modelo,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "valor_diaria": valor_diaria,
                "total": total,
                "status": status
            })
        conn.close()

        return render_template("minhas_reservas.html", reservas=reservas)
    
    conn.close()
    return redirect(url_for('home'))

#esta rota trata  do pedido de POST no botão "limpar_reservas"
@app.route('/limpar_reservas', methods=['POST'])
def limpar_reservas():
    #garantir que o usuario está iniciado
    if 'usuario' not in session:
        return redirect(url_for('home'))

    #obter o id do utilizador autenticado
    usuario= session['usuario']

    conn = conectar_bd()
    cursor = conn.cursor()
    #Buscar Id do cliente
    cursor.execute("SELECT id FROM clientes WHERE usuario = ?", (usuario,))
    cliente = cursor.fetchone()

    #o importante é apagar as reservas que não estão ativas
    if cliente:
        cliente_id = cliente[0]
        cursor.execute("DELETE FROM reservas WHERE cliente_id = ? AND status != 'Ativa'", (cliente_id,))
        conn.commit()
    
    
    conn.close()

    #enviar uma mensagem de sucesso temporária 
    flash("Reservas inativas foram removidas com sucesso com sucesso")
    return redirect(url_for('minhas_reservas'))

#rota para cancelar uma reserva especifica
@app.route("/cancelar_reserva/<int:reserva_id>")
def cancelar_reserva(reserva_id):
    if 'usuario' not in session:
        return redirect(url_for('home'))
    
    conn = conectar_bd()
    cursor = conn.cursor()

    #Atualizar o status da reserva para 'Cancelada'
    cursor.execute("UPDATE reservas SET status = 'Cancelada' WHERE id = ?", (reserva_id,))
    conn.commit()
    conn.close()

    return redirect(url_for("minhas_reservas"))

#Rota para alterar as datas da reservas
@app.route("/alterar_reserva/<int:reserva_id>", methods= ["GET", "POST"])
def alterar_reserva(reserva_id):

    """
    Rota para exibir o form de alteração (GET) e processar mudança de datas (POST).
    - Recalcula total e diferença.
    - Armazena temporariamente em sessão: 'total_a_pagar' e, se >0, 'diferenca_pagamento'.
    - Redireciona sempre para /pagamento.
    """

    if 'usuario' not in session:
        return redirect(url_for('home'))
    
    conn = conectar_bd()
    cursor = conn.cursor()

    if request.method == "POST":
        #obter novas datas do formulário
        nova_inicio= request.form['data_inicio']
        nova_fim= request.form ['data_fim']

        #Validar ordem das datas
        data_inicio= datetime.strptime(nova_inicio, "%Y-%m-%d").date()
        data_fim= datetime.strptime(nova_fim, "%Y-%m-%d").date()

        #Verifica se a data do fim é anterior á de inicio
        if data_fim < data_inicio:
            conn.close()
            return "A data de fim não pode ser anterior á data de início!"

        # Obter dados da reserva original (veiculo e valor anterior)
        cursor.execute("SELECT veiculo_id, valor_total FROM reservas WHERE id = ?", (reserva_id,))
        dados_reserva = cursor.fetchone()

        if not dados_reserva:
            conn.close()
            return "Reserva não encontrada."
        
        veiculo_id, valor_anterior = dados_reserva['veiculo_id'], dados_reserva['valor_total']

        #Obter o valor da diária do veículo
        cursor.execute("SELECT valor_diaria FROM veiculos WHERE id = ?", (veiculo_id,))
        valor = cursor.fetchone()

        if not valor:
            conn.close()
            return "Veículo não encontrado."
        
        diaria = valor['valor_diaria']

        #calcular o novo total com base nas novas datas
        dias = (datetime.strptime(data_fim, "%Y-%m-%d") - datetime.strptime(data_inicio, "%Y-%m-%d")).days + 1
        novo_total = diaria * dias

        #calcular a diferença entre o novo total e o valor pago anteriormente
        diferenca = novo_total - valor_anterior

        #Atualizar as datas e o novo valor na reserva
        cursor.execute("""
            UPDATE reservas
            SET data_inicio = ?, data_fim = ?, valor_total = ?
            WHERE id = ?
        """, (nova_inicio, nova_fim, novo_total, reserva_id))

        conn.commit()
        # Armazena na sessão apenas o que for relevante
        session['total_a_pagar'] = novo_total
        if diferenca > 0:
            session['diferenca_pagamento'] = diferenca
        else:
            session.pop('diferenca_pagamento', None)
        
        conn.close()

        #se houver valor adicional a pagar, redireciona para a página de pagamento
        return redirect(url_for('pagamento', reserva_id=reserva_id))

    #se for um pedido GET , busca dados atuais para mostrar no formulário
    cursor.execute("""
        SELECT data_inicio, data_fim 
        FROM reservas WHERE id = ?
    """, (reserva_id,))
    reserva = cursor.fetchone()
    conn.close()

    #enviar os dados para o template
    return render_template("alterar_reserva.html", reserva = reserva, reserva_id= reserva_id)

#route de logout, redireciona para a página "home", para o registo     
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__=='__main__':
    #Inicializa o esquema e dados padrão de carros
    criar_tabelas()
    inserir_carros()
    app.run(debug=True)