from flask import Flask, flash, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime, timedelta
#criar base de dados no sqlite (primeiro passo)
app = Flask(__name__)
app.secret_key= 'chave_super_secreta_444'
app.config["DEBUG"] = True

#filtro para converter string de data para objeto date
@app.template_filter('todate')
def todate_filter(value, format="%Y-%m-%d"):
    try:
        return datetime.strptime(value,format).date()
    except:
        return value


def conectar_bd():
    return sqlite3.connect("database/banco_de_dados.db")

#criação das tabelas da base de dados
def criar_tabelas():
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
            session['usuario'] = usuario_encontrado[1] #guarda o nome do usuário na sessão
                #print para analisar se deu
                #print(f"Usuário autenticado: {session['usuario']}") #Debugging
                #print("Redirencionando para a página de carros")
            return redirect(url_for('listar_carros')) #Redireciona para a página do dashboard após executar login
            
        else:
            mensagem = "Credenciais inválidas, tente novamente."
        
        """elif 'nome' in request.form and 'usuario' in request.form and 'senha' in request.form and 'senha_confirmacao' in request.form:
            nome = request.form['nome']
            usuario = request.form['usuario']
            senha = request.form['senha']
            senha_confirmacao= request.form['senha_confirmacao']

            if senha == senha_confirmacao:
                registar_usuario(nome, usuario, senha)
                print(f"Usuário {usuario} registado com sucesso") #Debugging
                #Registo de utilizador bem sucedido
                return redirect(url_for('home', registo="sucesso")) #após registar volta para a página inicial e entra
            
            else:
                mensagem= "As senhas não coincidem, tente novamente."""
            
    return render_template('index.html', mensagem=mensagem)

#Página dashboard (após login)
@app.route('/dashboard')
def dashboard():
    if 'usuario' not in session:
        return redirect(url_for('home')) #se o utilizador não logado, redireciona para o login
    return "Login executado com sucesso"

#Página com todos os carros
@app.route('/carros', methods=['GET']) #define a rota da página
#se o utilizador não tiver logado será redirecionado
def listar_carros():
    #Verificar se o utilizador está autenticado
    if 'usuario' not in session:
        print("Usuário não logado, redirecionando para o login...") #Debugging
        return redirect(url_for('home'))
    
    #conectar á base de dados
    conn= conectar_bd()
    cursor = conn.cursor()


     #Recolher os filtros enviados por GET (pesquisa e filtros laterais)
    pesquisa= request.args.get('pesquisa', "")

    if pesquisa:
        cursor.execute("SELECT * FROM veiculos WHERE marca LIKE ? or modelo LIKE ? or categoria LIKE ?",
                       ('%' + pesquisa + '%', '%' + pesquisa + '%', '%' + pesquisa + '%'))
    
    else:
        cursor.execute("SELECT * FROM veiculos")

    
    carros = cursor.fetchall()
    conn.close()

    return render_template('carros.html', carros=carros, pesquisa=pesquisa)

#Neste momento vou inserir os carros para o utilizador ter acesso
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

@app.route('/carro/<int:carro_id>', methods=['GET'])
def ver_carro(carro_id):
    if 'usuario' not in session:
        return redirect(url_for('home'))
    
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM veiculos WHERE id = ?", (carro_id,))
    carro = cursor.fetchone()
    conn.close()

    if not carro:
        return "Carro não encontrado", 404
    
    return render_template('detalhes_carro.html', carro=carro)



@app.route("/reservar/<int:carro_id>", methods= ["GET", "POST"])
def reservar_carro(carro_id):
    if 'usuario' not in session:
        return redirect(url_for('home'))
    
    conn = conectar_bd()
    cursor= conn.cursor()

    #Obter detalhes do carro
    cursor.execute("SELECT * FROM veiculos WHERE id = ?", (carro_id,))
    carro =cursor.fetchone()

    #caso nao seja encontrado
    if not carro:
        conn.close()
        return "Carro não encontrado", 404
    
    if request.method == "POST":
        data_inicio= request.form ['data_inicio']
        data_fim = request.form ['data_fim']
        usuario = session ['usuario']

        #Obter ID do cliente com base no nome do utilizador
        cursor.execute("SELECT id FROM clientes WHERE usuario = ?", (usuario,))
        cliente = cursor.fetchone()

        if cliente:
            cliente_id= cliente[0]

            #verificar se existe alguma reserva igual
            cursor.execute("""
                SELECT * FROM reservas
                WHERE cliente_id = ? AND veiculo_id = ? AND data_inicio  = ? AND data_fim = ? AND status = 'Ativa'
            """, (cliente_id, carro_id, data_inicio, data_fim))
            reserva_existente= cursor.fetchone()

            if reserva_existente:
                conn.close()
                return "Já existe uma reserva ativa com os mesmos dados."

            #calcular total 
            data1= datetime.strptime(data_inicio, "%Y-%m-%d")
            data2= datetime.strptime(data_fim, "%Y-%m-%d")
            dias= (data2 - data1).days + 1
            total = dias * carro[8] #carro[8] valor diaria

            cursor.execute("""
                INSERT INTO reservas (cliente_id, veiculo_id, data_inicio, data_fim, valor_total, status)
                VALUES (?, ?, ?, ?, ?, 'Ativa')
                """, (cliente_id, carro_id, data_inicio, data_fim, total)) 
            
            conn.commit()
            conn.close()

            return redirect(url_for("minhas_reservas"))
        
    conn.close()
    return render_template("reserva.html", carro=carro)

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
        reservas= cursor.fetchall()
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

        if data_fim < data_inicio:
            return "A data de fim não pode ser anterior á data de início!"

        #Buscar veiculo_id e diária da reserva original
        cursor.execute("SELECT veiculo_id FROM reservas WHERE id = ?", (reserva_id,))
        veiculo = cursor.fetchone()

        if veiculo:
            veiculo_id = veiculo[0]

            cursor.execute("SELECT valor_diaria FROM veiculos WHERE id = ?", (veiculo_id,))
            valor = cursor.fetchone()
            if valor:
                diaria = valor[0]
                dias = (data_fim - data_inicio).days + 1
                total = diaria * dias

            #Atualizar os dados das datas da reserva
            cursor.execute("""
                UPDATE reservas SET data_inicio = ?, data_fim = ?
                WHERE id = ?
            """, (nova_inicio, nova_fim, reserva_id))

            conn.commit()
            conn.close()
            return redirect(url_for("minhas_reservas"))
    
    #Obter dados da reserva para preencher o formulário
    cursor.execute("SELECT data_inicio, data_fim FROM reservas WHERE id = ?", (reserva_id,))
    reserva= cursor.fetchone()
    conn.close()

    return render_template("alterar_reserva.html", reserva=reserva, reserva_id=reserva_id)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


if __name__=='__main__':
    criar_tabelas()
    inserir_carros()
    app.run(debug=True)