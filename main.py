
import os
import csv
import re
import unicodedata
import logging
import mysql.connector
from mysql.connector import Error
import pandas as pd

# Configuração do log
logging.basicConfig(filename='sistema_gestao.log', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Configurações do banco de dados
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "user"),
    "password": os.environ.get("DB_PASSWORD", "password"),
    "database": os.environ.get("DB_NAME", "database_name")
}

def process_csv(input_file, output_file):
    """
    Processa um arquivo CSV, remove tags HTML, normaliza texto (acentuação, 'ç' para 'c') 
    e ajusta delimitadores (de ponto e vírgula para o delimitador desejado).
    """
    def remove_html_tags(text):
        """Remove tags HTML de uma string."""
        return re.sub(r'<[^>]*>', '', text)

    def normalize_text(text):
        """Remove acentuações e substitui 'ç' por 'c'."""
        if not text:
            return None
        normalized = unicodedata.normalize('NFD', text)
        without_accents = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
        return without_accents.replace('ç', 'c').replace('Ç', 'C')

    def converter_para_utf8(nome_arquivo):
        """Converte um arquivo CSV para UTF-8."""
        arquivo_normalizado = os.path.join(os.getcwd(), "normalized_" + nome_arquivo)

        try:
            dados = pd.read_csv(nome_arquivo, sep=";", encoding="latin1")
            # Normalizar colunas
            dados.columns = dados.columns.str.strip().str.replace(r'\s+', ' ', regex=True)
            dados.to_csv(arquivo_normalizado, index=False, encoding="utf-8")
            logging.info(f"Arquivo '{nome_arquivo}' convertido para UTF-8 com sucesso.")
            return arquivo_normalizado
        except Exception as e:
            logging.error(f"Erro ao converter arquivo: {e}")
            raise

    # Converter o arquivo original para UTF-8
    converter_para_utf8(input_file)

    # Processar e salvar o arquivo normalizado
    with open(input_file, mode='r', encoding='latin-1') as infile, \
         open(output_file, mode='w', encoding='utf-8', newline='') as outfile:
        
        reader = csv.reader(infile, delimiter=';')  # Ajuste para ponto e vírgula no CSV original
        writer = csv.writer(outfile, delimiter=';')  # Preserva o delimitador na saída
        
        # Processar linha por linha
        for row in reader:
            # Normalizar o conteúdo de cada célula
            cleaned_row = [normalize_text(remove_html_tags(cell)) for cell in row]
            writer.writerow(cleaned_row)

    logging.info(f"Arquivo '{input_file}' processado e salvo como '{output_file}'.")

# Função para limpar as tabelas excluindo suas linhas
def limpar_tabelas():
    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                # Desabilitar checagem de chave estrangeira temporariamente
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                
                # Obter as tabelas do banco de dados
                cursor.execute("SHOW TABLES;")
                tabelas = cursor.fetchall()
             
                tabelas = [t for t in tabelas if not t[0].startswith('vw')]


                if tabelas:
                    for tabela in tabelas:
                        print()
                        tabela_nome = tabela[0]
                        print(f"Limpando dados da tabela: {tabela_nome}")
                        
                        # Verificar a quantidade de registros antes da exclusão
                        cursor.execute(f"SELECT COUNT(*) FROM {tabela_nome};")
                        count_before = cursor.fetchone()[0]
                        print(f"Quantidade de registros antes da exclusão: {count_before}")

                        # Limpar os dados da tabela (usando TRUNCATE para maior eficiência)
                        cursor.execute(f"TRUNCATE TABLE {tabela_nome};")

                        # Verificar a quantidade de registros depois da exclusão
                        cursor.execute(f"SELECT COUNT(*) FROM {tabela_nome};")
                        count_after = cursor.fetchone()[0]
                        print(f"Quantidade de registros depois da exclusão: {count_after}")

                    # Comitar as mudanças
                    conn.commit()
                else:
                    print("Nenhuma tabela encontrada no banco de dados.")
                
                # Reabilitar a checagem de chave estrangeira
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
                print()
                print("Limpeza concluída com sucesso.")
    
    except Error as err:
        logging.error(f"Erro ao limpar tabelas: {err}")
        print(f"Erro ao limpar tabelas: {err}")


# Função para conectar ao banco de dados
def conectar():
    print()
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as err:
        logging.error(f"Erro ao conectar ao banco de dados: {err}")
        raise


# Criação de tabelas no banco
def criar_tabelas():
    queries = [
        """
        CREATE TABLE IF NOT EXISTS Pessoa (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sexo VARCHAR(10),
            forca VARCHAR(5),
            posto_graduacao VARCHAR(50)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Localizacao (
            id INT AUTO_INCREMENT PRIMARY KEY,
            estado VARCHAR(30),
            cidade VARCHAR(50)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS Esporte (
            id INT AUTO_INCREMENT PRIMARY KEY,
            modalidade VARCHAR(50),
            possui_medalha VARCHAR(5),
            possui_bolsa VARCHAR(5),
            paar VARCHAR(5)
        )
        """
    ]

    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                for query in queries:
                    cursor.execute(query)
            conn.commit()
            logging.info("Tabelas criadas com sucesso.")
            print("Tabelas criadas com sucesso.")
    except Error as err:
        logging.error(f"Erro ao criar tabelas: {err}")
        print(f"Erro ao criar tabelas: {err}")


# Carrega o CSV para o banco de dados
def carregar_csv_para_banco(nome_arquivo):
    arquivo_normalizado = "normalized_" + nome_arquivo
    process_csv(nome_arquivo, arquivo_normalizado)  # Normalizar o arquivo

    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                with open(arquivo_normalizado, mode='r', encoding='utf-8') as arquivo:
                    leitor = csv.DictReader(arquivo, delimiter=';')  # Ajuste para ponto e vírgula no CSV
        

                    # Verificar se as chaves estão corretas
                    print("Cabeçalhos do CSV:", leitor.fieldnames)  # Verificar se os cabeçalhos estão corretos
                    for linha in leitor:
                        
                        if linha.get('Sexo') and linha.get('Modalidade'):
                            sexo = linha.get('Sexo', '').strip()
                            estado = linha.get('Estado', '').strip()
                            cidade = linha.get('Cidade', '').strip()
                            forca = linha.get('Forca', '').strip()
                            posto_graduacao = linha.get('Posto Graduacao', '').strip()
                            possui_medalha = linha.get('Possui Medalha de  Merito Desportivo Militar', 'Nao').strip() == 'Sim'
                            modalidade = linha.get('Modalidade', '').strip()
                            possui_bolsa = linha.get('Possui Bolsa Atleta', 'Nao').strip() == 'Sim'
                            paar = linha.get('PAAR', 'Nao').strip() == 'Sim'
                            
                            if (estado == ""):
                                estado = "N/A"
                            
                            if (cidade == ""):
                                cidade = "N/A"

                            if (possui_bolsa):
                                possui_bolsa = "Sim"
                            else:
                                possui_bolsa = "Não"

                            if (possui_medalha):
                                possui_medalha = "Sim"
                            else:  
                                possui_medalha = "Não"

                            if (paar):
                                paar = "Sim"
                            else:
                                paar = "Não"

                            lista_elementos = [sexo, forca, posto_graduacao, estado, cidade, modalidade, possui_medalha, possui_bolsa, paar]
                            novo_elemento(lista_elementos)

                    conn.commit()
                    print()
                    print("Dados carregados com sucesso.")
    except Error as err:
        print()
        logging.error(f"Erro ao carregar CSV: {err}")
        print(f"Erro ao carregar CSV: {err}")


def consultar_tabela(nome_tabela):
    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {nome_tabela}")
                resultados = cursor.fetchall()

                if(resultados == []):
                    print("Tabela vazia.")

                for linha in resultados:
                    print(linha)
    except Error as err:
        logging.error(f"Erro ao consultar tabela {nome_tabela}: {err}")
        print(f"Erro ao consultar tabela {nome_tabela}: {err}")


def listar_tabelas():
    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES;")
                tabelas = cursor.fetchall()

                tabelas = [t for t in tabelas if not t[0].startswith('vw')]
                
                if tabelas:
                    print("Tabelas disponíveis no banco de dados:")
                    for tabela in tabelas:
                        print(f"- {tabela[0]}")
                else:
                    print("Nenhuma tabela encontrada no banco de dados.")
    except Error as err:
        logging.error(f"Erro ao listar tabelas: {err}")
        print(f"Erro ao listar tabelas: {err}")


def consultar_elemento():
    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                # Entrada do ID com tratamento de erro
                id = input("Digite o ID do elemento que deseja consultar: ").strip()

                if not id.isdigit():  # Verificar se o ID é numérico
                    print("ID inválido. Por favor, insira um ID numérico.")
                    return
                
                # Consulta ajustada para evitar repetição do ID
                cursor.execute("""
                    SELECT 
                        Pessoa.sexo, 
                        Pessoa.forca, 
                        Pessoa.posto_graduacao, 
                        Localizacao.estado, 
                        Localizacao.cidade, 
                        Esporte.modalidade, 
                        Esporte.possui_medalha, 
                        Esporte.possui_bolsa, 
                        Esporte.paar
                    FROM 
                        Pessoa
                    LEFT JOIN 
                        Esporte ON Pessoa.id = Esporte.id
                    LEFT JOIN 
                        Localizacao ON Pessoa.id = Localizacao.id
                    WHERE 
                        Pessoa.id = %s
                """, (id,))
                
                resultado = cursor.fetchone()

                if resultado:
                    print("Resultado encontrado:")
                    # A ordem de exibição será a mesma do SELECT
                    print(resultado)

                else:
                    print("Nenhum resultado encontrado para o ID fornecido.")
                    
    except Error as err:
        logging.error(f"Erro ao consultar elementos: {err}")
        print(f"Erro ao consultar elementos: {err}")


def fazer_crud():
    print()
    escolha = input("Escolha uma opção: \n1. Incluir\n2. Alterar\n3. Consultar\n4. Excluir\n5. Sair\n")
    match escolha:
        case "1":
            incluir_elemento()
        case "2":
            alterar_elemento()
        case "3":
            consultar_elemento()
        case "4":
            excluir_elemento()
        case _:
            print("Opção Inválida")

def excluir_tabelas():
    try:
        with conectar() as conn:
            with conn.cursor() as cursor:

                listar_tabelas()

                tabela = input("Digite o nome da tabela que deseja excluir: ").strip()

                cursor.execute("SHOW TABLES;")
                tabelas = cursor.fetchall()

                tabelas = [t[0] for t in tabelas if not t[0].startswith('vw')]

                print (tabela, tabelas)

                if tabela not in tabelas:
                    print()
                    print("Tabela não encontrada.")
                    return

                confirmar = input(f"Tem certeza de que deseja excluir a tabela '{tabela}'? (Sim/Não): ").strip().lower()

                if confirmar in ["sim", "s"]:
                    cursor.execute(f"DROP TABLE IF EXISTS {tabela}")
                    conn.commit()
                    print(f"Tabela '{tabela}' excluída com sucesso.")
                else:
                    print("Operação cancelada.")     
                     
    except Error as err:
        logging.error(f"Erro ao excluir tabelas: {err}")
        print(f"Erro ao excluir tabelas: {err}")


def menu():
    while True:
        print("\n--- Sistema de Gestão ---")
        print("1. Criar tabelas")
        print("2. Carregar CSV")
        print("3. Consultar tabela")
        print("4. Listar tabelas disponíveis")
        print("5. Limpar tabelas")
        print("6. Excluir tabelas")
        print("7. Fazer CRUD")
        print("8. Sair")

        escolha = input("Escolha uma opção: ")
    
        try:
            match escolha:
                case "1":
                    criar_tabelas()
                case "2":
                    nome_arquivo = input("Digite o nome do arquivo CSV: ")
                    carregar_csv_para_banco(nome_arquivo)
                case "3":
                    tabela = input("Digite o nome da tabela para consultar: ")
                    consultar_tabela(tabela)
                case "4":
                    listar_tabelas()
                case "5":
                    limpar_tabelas()
                case "6":
                    excluir_tabelas()
                case "7":
                    fazer_crud()
                case "8":
                    print("Saindo...")
                    break
                case _:
                    print("Opção inválida!")
                
        except Exception as e:
            print()
            logging.error(f"Erro inesperado no menu: {e}")
            print(f"Erro inesperado: {e}")



def novo_elemento(lista_elementos):

    sexo, forca, posto_graduacao, estado, cidade, modalidade, possui_medalha, possui_bolsa, paar = lista_elementos

    try:
        with conectar() as conn:
            with conn.cursor() as cursor:

                # if table vazio, then id = 1

                # Inserir em Pessoa
                cursor.execute("""
                    INSERT INTO Pessoa (sexo, forca, posto_graduacao)
                    VALUES (%s, %s, %s)
                """, (sexo, forca, posto_graduacao))

                # Inserir em Localizacao
                cursor.execute("""
                    INSERT INTO Localizacao (estado, cidade)
                    VALUES (%s, %s)
                """, (estado, cidade))

                # Inserir em Esporte
                cursor.execute("""
                    INSERT INTO Esporte (modalidade, possui_medalha, possui_bolsa, paar)
                    VALUES (%s, %s, %s, %s)
                """, (modalidade, possui_medalha, possui_bolsa, paar))

                conn.commit()

    except Error as err:
        print()
        logging.error(f"Erro ao tentar incluir novo elemento: {err}")
        print(f"Erro ao tentar incluir novo elemento: {err}")

def remover_acentos(texto):
    """
    Remove acentos de uma string.
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )

def incluir_elemento():
   
    print("Forneça os dados para inclusão:")
    while (True):
        sexo = input("Sexo: ")
        if (sexo in ["masculino", "Masculino", "M", "m"]):
            sexo = "Masculino"
            break
        elif (sexo in ["feminino", "Feminino", "F", "f"]):
            sexo = "Feminino"
            break
        else:
            print("Sexo inválido. Digite novamente.")
    
    forcas = ["MB", "FAB", "EB"]
    while(True):
        forca = input("Força: ").upper()
        forca = remover_acentos(forca)
        if forca in forcas:
            break
        else:
            print("Força inválida. Digite novamente.")

    postos_de_graduacao = ["soldado", "cabo", "sargento", "primeiro sargento", "primeiro tenente", "primeiro sargente",
                            "segundo sargento", "capitao de mar e guerra", 
                           "subtenente", "tenente", "suboficial", "suboficial r/1", "tenete-coronel r/1",
                           "capitao", "terceiro sargento", "terceiro sargento r/1", "tenente-coronel", "coronel"]
    while(True):
        posto_graduacao = input("Posto/Graduação: ").lower()
        posto_graduacao = remover_acentos(posto_graduacao)
        if posto_graduacao in postos_de_graduacao:
            break
        else:
            print("Posto/Graduação inválido. Digite novamente.")
    
    estado = input("Estado: ")
    if not estado:
        estado = "N/A"

    cidade = input("Cidade: ")
    if not cidade:
        cidade = "N/A"
    
    lista_modalidades = ["apneia", "atletismo", "basquete", "boxe", "canoagem slalom", 
                             "canoagem velocidade", "ciclismo mtb", "escalada esportiva", "esgrima", 
                             "futebol", "ginastica artistica", "golfe", "judo", "levantamento de peso", 
                             "lifesaving", "lutas associadas (wrestling)", "maratona", "maratonas aquaticas",
                             "nado sincronizado", "natacao", "orientacao", "paraquedismo", "pentatlo militar", 
                             "pentatlo moderno", "pentatlo naval", "pesca submarina", "taekwondo", "tiro", "tiro com arco",
                             "triatlo", "vela", "voleibol", "volei de praia"]

    while(True):
        modalidade = input("Digite uma modalidade: ").strip().lower()
        modalidade = remover_acentos(modalidade)

        if modalidade in [m.lower() for m in lista_modalidades]:
            break 
        else:
            print("Modalidade inválida. Digite novamente.")


    while(True):
        possui_medalha = input("Possui medalha de mérito desportivo militar (Sim/Não): ")
        if (possui_medalha in ["Sim", "sim", "S", "s"]):
            possui_medalha = "Sim"
            break
        elif (possui_medalha in ["Não", "não", "N", "n"]):   
            possui_medalha = "Não"
            break
        else:
            print("Opção inválida. Digite novamente.")
    
    while(True):
        possui_bolsa = input("Possui bolsa atleta (Sim/Não): ")
        if (possui_bolsa in ["Sim", "sim", "S", "s"]):
            possui_bolsa = "Sim"
            break
        elif (possui_bolsa in ["Não", "não", "N", "n"]):   
            possui_bolsa = "Não"
            break
        else:
            print("Opção inválida. Digite novamente.")
    
    while(True):
        paar = input("PAAR (Sim/Não): ")
        if (paar in ["Sim", "sim", "S", "s"]):
            paar = "Sim"
            break
        elif (paar in ["Não", "não", "N", "n"]):   
            paar = "Não"
            break
        else:
            print("Opção inválida. Digite novamente.")



    lista_elementos = [sexo, forca, posto_graduacao, estado, cidade, modalidade, possui_medalha, possui_bolsa, paar]
    
    novo_elemento(lista_elementos)


def tratar_input(lista_elementos):

    sexo, forca, posto_graduacao, estado, cidade, modalidade, possui_medalha, possui_bolsa, paar = lista_elementos


    if (forca == ""):
        forca = "N/A"
    
    if (posto_graduacao == ""):
        posto_graduacao = "N/A"
    
    if (estado == ""):
        estado = "N/A"
    
    if (cidade == ""):
        cidade = "N/A"
    
    if (modalidade == ""):
        modalidade = "N/A"
    
    if (possui_medalha == ""):
        possui_medalha = "N/A"
    
    if (possui_bolsa == ""):
        possui_bolsa = "N/A"
    
    if (paar == ""):
        paar = "N/A"

    lista_elementos = [sexo, forca, posto_graduacao, estado, cidade, modalidade, possui_medalha, possui_bolsa, paar]

    return lista_elementos


           
           


def alterar_elemento():
    id = input("Digite o ID do elemento que deseja alterar: ")

    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                # Verificar se o ID existe nas tabelas
                cursor.execute("SELECT * FROM Pessoa WHERE id = %s", (id,))
                pessoa = cursor.fetchone()
                
                if not pessoa:
                    print("Registro não encontrado.")
                    return

                # Coletar dados existentes
                cursor.execute("SELECT * FROM Localizacao WHERE id = %s", (id,))
                localizacao = cursor.fetchone()

                cursor.execute("SELECT * FROM Esporte WHERE id = %s", (id,))
                esporte = cursor.fetchone()

                if not localizacao:
                    localizacao = ["", "N/A", "N/A"] 


                print("\nDigite os novos valores ou pressione Enter para manter os atuais.")

                # Coletar e validar as entradas para os campos
                while True:
                    sexo = input(f"Sexo [{pessoa[1]}]: ").strip() or pessoa[1]
                    if sexo in ["masculino", "Masculino", "M", "m"]:
                        sexo = "Masculino"
                        break
                    elif sexo in ["feminino", "Feminino", "F", "f"]:
                        sexo = "Feminino"
                        break
                    elif sexo == pessoa[1]:  # Caso o usuário queira manter o valor
                        break
                    else:
                        print("Sexo inválido. Digite novamente.")

                forcas = ["MB", "FAB", "EB"]
                while True:
                    forca = input(f"Força [{pessoa[2]}]: ").upper().strip() or pessoa[2]
                    forca = remover_acentos(forca)
                    if forca in forcas:
                        break
                    elif forca == pessoa[2]:  # Caso o usuário queira manter o valor
                        break
                    else:
                        print("Força inválida. Digite novamente.")

                postos_de_graduacao = ["soldado", "cabo", "sargento", "primeiro sargento", "primeiro tenente", "primeiro sargente",
                                       "segundo sargento", "capitao de mar e guerra", "subtenente", "tenente", "suboficial", 
                                       "suboficial r/1", "tenete-coronel r/1", "capitao", "terceiro sargento", 
                                       "terceiro sargento r/1", "tenente-coronel", "coronel"]
                while True:
                    posto_graduacao = input(f"Posto/Graduação [{pessoa[3]}]: ").lower().strip() or pessoa[3]
                    posto_graduacao = remover_acentos(posto_graduacao)
                    if posto_graduacao in postos_de_graduacao:
                        break
                    elif posto_graduacao == pessoa[3]:  # Caso o usuário queira manter o valor
                        break
                    else:
                        print("Posto/Graduação inválido. Digite novamente.")

                estado = input(f"Estado [{localizacao[1]}]: ").strip() or (localizacao[1] if localizacao[1] else "N/A")
                cidade = input(f"Cidade [{localizacao[2]}]: ").strip() or (localizacao[2] if localizacao[2] else "N/A")
                
                lista_modalidades = ["apneia", "atletismo", "basquete", "boxe", "canoagem slalom", "canoagem velocidade", 
                                     "ciclismo mtb", "escalada esportiva", "esgrima", "futebol", "ginastica artistica", 
                                     "golfe", "judo", "levantamento de peso", "lifesaving", "lutas associadas (wrestling)", 
                                     "maratona", "maratonas aquaticas", "nado sincronizado", "natacao", "orientacao", 
                                     "paraquedismo", "pentatlo militar", "pentatlo moderno", "pentatlo naval", 
                                     "pesca submarina", "taekwondo", "tiro", "tiro com arco", "triatlo", "vela", 
                                     "voleibol", "volei de praia"]

                while True:
                    modalidade = input(f"Modalidade [{esporte[1]}]: ").strip().lower() or esporte[1]
                    modalidade = remover_acentos(modalidade)
                    if modalidade in [m.lower() for m in lista_modalidades] or modalidade == esporte[1]:
                        break
                    else:
                        print("Modalidade inválida. Digite novamente.")

                while True:
                    possui_medalha = input(f"Possui medalha de mérito desportivo militar (Sim/Não) [{esporte[2]}]: ").strip() or esporte[2]
                    if possui_medalha in ["Sim", "sim", "S", "s"]:
                        possui_medalha = "Sim"
                        break
                    elif possui_medalha in ["Não", "não", "N", "n"]:
                        possui_medalha = "Não"
                        break
                    elif possui_medalha == esporte[2]:  # Caso o usuário queira manter o valor
                        break
                    else:
                        print("Opção inválida. Digite novamente.")

                while True:
                    possui_bolsa = input(f"Possui bolsa atleta (Sim/Não) [{esporte[3]}]: ").strip() or esporte[3]
                    if possui_bolsa in ["Sim", "sim", "S", "s"]:
                        possui_bolsa = "Sim"
                        break
                    elif possui_bolsa in ["Não", "não", "N", "n"]:
                        possui_bolsa = "Não"
                        break
                    elif possui_bolsa == esporte[3]:  # Caso o usuário queira manter o valor
                        break
                    else:
                        print("Opção inválida. Digite novamente.")

                while True:
                    paar = input(f"PAAR (Sim/Não) [{esporte[4]}]: ").strip() or esporte[4]
                    if paar in ["Sim", "sim", "S", "s"]:
                        paar = "Sim"
                        break
                    elif paar in ["Não", "não", "N", "n"]:
                        paar = "Não"
                        break
                    elif paar == esporte[4]:  # Caso o usuário queira manter o valor
                        break
                    else:
                        print("Opção inválida. Digite novamente.")

                # Atualizar os valores no banco
                cursor.execute("""
                    UPDATE Pessoa
                    SET sexo = %s, forca = %s, posto_graduacao = %s
                    WHERE id = %s
                """, (sexo, forca, posto_graduacao, id))

                print(estado, cidade)
         
                cursor.execute("""
                    UPDATE Localizacao
                    SET estado = %s, cidade = %s
                    WHERE id = %s       
                """, (estado, cidade, id))

                cursor.execute("""
                    UPDATE Esporte
                    SET modalidade = %s, possui_medalha = %s, possui_bolsa = %s, paar = %s
                    WHERE id = %s
                """, (modalidade, possui_medalha, possui_bolsa, paar, id))

                conn.commit()
                print()
                print("Registro atualizado com sucesso.")
    
    except Error as err:
        logging.error(f"Erro ao alterar registro: {err}")
        print(f"Erro ao alterar registro: {err}")


def excluir_elemento():
    id = input("ID do registro a ser excluído: ")

    try:
        with conectar() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM Pessoa WHERE id = %s", (id,))
                cursor.execute("DELETE FROM Localizacao WHERE id = %s", (id,))
                cursor.execute("DELETE FROM Esporte WHERE id = %s", (id,))

                # Atualiza os IDs das tabelas relacionadas
                cursor.execute("UPDATE Pessoa SET id = id - 1 WHERE id > %s", (id,))
                cursor.execute("UPDATE Localizacao SET id = id - 1 WHERE id > %s", (id,))
                cursor.execute("UPDATE Esporte SET id = id - 1 WHERE id > %s", (id,))

                conn.commit()
                print("Registro excluído com sucesso.")
    except Error as err:
        print()
        logging.error(f"Erro ao excluir registro: {err}")
        print(f"Erro ao excluir registro: {err}")




if __name__ == "__main__":
    menu()
