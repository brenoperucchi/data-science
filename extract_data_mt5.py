from datetime import datetime
import MetaTrader5 as mt5
import sqlite3
import schedule
import time
import pandas as pd
import argparse
import pdb
import pytz
from datetime import timedelta


# Configuração inicial
SYMBOLS = ["WINJ25"]  # Ativos B3
DB_NAME = "b3_ticks.db"
TIME_SLEEP = 2

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Tabela para ticks
    c.execute('''CREATE TABLE IF NOT EXISTS ticks
                 (symbol TEXT, time DATETIME, bid REAL, ask REAL, last REAL, volume INTEGER)''')
                 
    # Tabela para OHLC
    c.execute('''CREATE TABLE IF NOT EXISTS ohlc
                 (symbol TEXT, timeframe TEXT, time DATETIME,
                  open REAL, high REAL, low REAL, close REAL, volume INTEGER)''')
    
    conn.commit()
    return conn

def login_mt5():
    # display data on the MetaTrader 5 package
    print("MetaTrader5 package author: ",mt5.__author__)
    print("MetaTrader5 package version: ",mt5.__version__)
    
    # establish connection to the MetaTrader 5 terminal
    if not mt5.initialize():
        print("initialize() failed, error code =",mt5.last_error())
        quit()
    
    # display data on MetaTrader 5 version
    print(mt5.version())
    # connect to the trade account without specifying a password and a server
    mt5_account = 52033102
    mt5_pass = "c3f4SWC@"
    authorized=mt5.login(mt5_account, password=mt5_pass, server="XPMT5-DEMO")  # the terminal database password is applied if connection data is set to be remembered
    # authorized=mt5.login(account, password="gqrtz0lbdm")
    # authorized=mt5.login(mt5_account, password=mt5_pass)
    if authorized:
        # display trading account data 'as is'
        print(mt5.account_info())
        # display trading account data in the form of a list
        print("Show account_info()._asdict():")
        account_info_dict = mt5.account_info()._asdict()
        for prop in account_info_dict:
            print("  {}={}".format(prop, account_info_dict[prop]))
    else:
        print("failed to connect at account #{}, error code: {}".format(mt5_account, mt5.last_error()))

    print(mt5.version())
    
    if(DEBUG):
        # display info on the terminal settings and status
        terminal_info=mt5.terminal_info()
        if terminal_info!=None:
            # display the terminal data 'as is'
            print(terminal_info)
            # display data in the form of a list
            print("Show terminal_info()._asdict():")
            terminal_info_dict = mt5.terminal_info()._asdict()
            for prop in terminal_info_dict:
                print("  {}={}".format(prop, terminal_info_dict[prop]))
            print()
            # convert the dictionary into DataFrame and print
            df=pd.DataFrame(list(terminal_info_dict.items()),columns=['property','value'])
            print("terminal_info() as dataframe:")
            print(df)       
    return mt5        

def collect_ticks(conn, mt5):
    try:                  
        for symbol in SYMBOLS:
            if(DEBUG):
              print(f"Coletando tick atual para {symbol}...")
            # Usa symbol_info_tick para obter o tick do mercado
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                print(f"Nenhum tick disponível para {symbol}")
                continue
                
            print(f"Tick recebido: {tick}")
            
            c = conn.cursor()
            try:
                c.execute('''INSERT INTO ticks VALUES 
                          (?,?,?,?,?,?)''',
                          (symbol, datetime.fromtimestamp(tick.time),
                           tick.bid, tick.ask, tick.last, tick.volume))
                conn.commit()
                if(DEBUG):
                  print(f"Tick inserido para {symbol} no banco de dados")
            except sqlite3.Error as e:
                if(DEBUG):
                  print(f"Erro ao inserir tick: {e}")
                  print(f"Dados do tick: {tick}")
            
            # Verificar os dados inseridos
            c.execute('''SELECT COUNT(*) FROM ticks WHERE symbol = ?''', (symbol,))
            total = c.fetchone()[0]
            print(f"Total de registros para {symbol} no banco: {total}")
            
    except Exception as e:
        print(f"Erro: {e}")
        raise
    finally:
        conn.commit()
        # Mantém a conexão com MT5 ativa para próximas coletas

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='B3 Stream Data Collector')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    
    global DEBUG
    DEBUG = args.debug
    
    print("Iniciando coleta de dados...")
    
    # Inicializa conexões
    mt5_instance = None
    try:
        mt5_instance = login_mt5()
        if not mt5_instance:
            raise Exception("Falha ao conectar ao MT5")
            
        while True:
            try:
                conn = setup_database()
                collect_ticks(conn, mt5_instance)
            except Exception as e:
                print(f"Erro no loop principal: {e}")
                # Tenta reconectar ao MT5 apenas se houver erro
                if not mt5.terminal_info():
                    print("Reconectando ao MT5...")
                    mt5.shutdown()
                    mt5_instance = login_mt5()
            finally:
                conn.close()
            if(DEBUG):
              print(f"Aguardando {TIME_SLEEP} segundos para próxima coleta...")
            time.sleep(TIME_SLEEP)
            
    except KeyboardInterrupt:
        print("\nEncerrando o programa...")
    finally:
        if mt5_instance:
            mt5.shutdown()
        print("Programa encerrado")