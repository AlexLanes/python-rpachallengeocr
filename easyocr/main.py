# std
import os as OS
import csv as Csv
import time as Time
from datetime import datetime as DateTime, date as Date
# externo
from easyocr import Reader
from selenium.webdriver.common.by import By
from selenium.webdriver import Edge, EdgeOptions
from selenium.webdriver.edge.service import Service
import selenium.webdriver.support.expected_conditions as Expect
from selenium.webdriver.support.wait import WebDriverWait as Wait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# current working directory
CWD = "\\".join( __file__.split("\\")[0:-1] )

DRIVER = EdgeChromiumDriverManager().install()
OPTIONS = EdgeOptions()
OPTIONS.add_argument("--start-maximized")

LeitorImagem = Reader([ "en" ])

class XPaths:
    TBODY = "/html/body/div/div/div[2]/div/div[1]/div[1]/table/tbody"
    def id( indexTr: int ) -> str: 
        return f"{ XPaths.TBODY }/tr[{ indexTr }]/td[2]"
    def dueDate( indexTr: int ) -> str: 
        return f"{ XPaths.TBODY }/tr[{ indexTr }]/td[3]"
    def url( indexTr: int ) -> str: 
        return f"{ XPaths.TBODY }/tr[{ indexTr }]/td[4]/a"

def extrair_info_imagem( nomeImagem: str, invoice: dict ) -> None:
    """Extrai: InvoiceNo, InvoiceDate, CompanyName e TotalDue da imagem e insere no invoice"""
    # ler o texto da imagem
    texto = LeitorImagem.readtext(f"./arquivos/{ nomeImagem }", detail = 0)

    # o valor total varia de lugar na lista
    # a data está invertida
    if "Aenean LLC".lower() in texto[0].lower():
        invoice["InvoiceNo"] = texto[5].split(" ")[1][1:]
        ano, mes, dia = texto[3][:10].split("-")
        invoice["InvoiceDate"] = f"{dia}-{mes}-{ano}"
        invoice["CompanyName"] = texto[0][:10]
        indexTotal = texto.index("Total")
        invoice["TotalDue"] = texto[indexTotal + 1]
    
    # o nome varia de lugar na lista
    # a data pode vir quebrada sem o dia => 1
    # o valor total deve ignorar o primeiro caracter
    # os "Sit Amet Corp" aparentam estar na regra "dueDate > Date.today()"
    elif "Sit Amet Corp".lower() in texto[5].lower() or "Sit Amet Corp".lower() in texto[6].lower():
        pass
    else: return

def conversor_data( data: str ) -> Date | None:
    """Faz o parse para Date(). Se houver erro retorna None"""
    try:
        return DateTime.strptime(data, r"%d-%m-%Y").date()
    except:
        return None

def main() -> None:
    navegador = Edge( OPTIONS, Service(DRIVER) )
    navegador.implicitly_wait(10)
    navegador.get("https://rpachallengeocr.azurewebsites.net/")

    # clicar em "Start" e esperar o refresh da página
    idAntesRefresh = navegador.find_element( By.XPATH, XPaths.id(1) ).text
    navegador.find_element(By.ID, "start").click()
    condicaoAntiga = Expect.text_to_be_present_in_element( (By.XPATH, XPaths.id(1)), idAntesRefresh ) 
    Wait(navegador, 2).until_not(condicaoAntiga)

    invoices: list[dict] = []
    # percorrer todas as páginas
    while True:

        # percorrer todos os Invoices da página
        start = 1
        end = len( navegador.find_elements(By.XPATH, f"{XPaths.TBODY}/tr") ) + 1 
        for index in range(start, end):
            # garantir que o DueDate é menor ou igual a hoje
            dueDate = conversor_data( navegador.find_element(By.XPATH, XPaths.dueDate(index)).text )
            if dueDate is None or dueDate > Date.today(): continue
            # salvar atributos do Invoice
            urlImagem = navegador.find_element( By.XPATH, XPaths.url(index) ).get_attribute("href")
            nomeImagem = urlImagem.split("/")[-1]
            invoices.append({
                "ID": navegador.find_element( By.XPATH, XPaths.id(index) ).text,
                "DueDate": navegador.find_element( By.XPATH, XPaths.dueDate(index) ).text,
                "imagem": {
                    "nome": nomeImagem,
                    "url": urlImagem
                }
            })

        # próxima página ?
        botaoNext = navegador.find_element(By.ID, "tableSandbox_next")
        if "disabled" not in botaoNext.get_attribute("class"):
            botaoNext.click()
        else: break

    # baixar e Ler os Invoices
    for invoice in invoices:
        nomeImagem, urlImagem = invoice["imagem"]["nome"], invoice["imagem"]["url"]
        del invoice["imagem"]
        # abrir o link e alterar a aba do navegador
        navegador.switch_to.new_window("tab")
        navegador.get(urlImagem)
        # baixar e salvar a imagem
        pathImagem = f"arquivos/{ nomeImagem }"
        with open( pathImagem, "wb" ) as file:
            file.write( navegador.find_element(By.TAG_NAME, "img").screenshot_as_png )
        # inserir os dados da imagem no invoice
        extrair_info_imagem(nomeImagem, invoice)
        # fechar a aba aberta e trocar o navegador para a aba principal
        navegador.close()
        navegador.switch_to.window( navegador.window_handles[0] )
    
    # criar o .csv
    nomeCsv = "output.csv"
    with open( f"./arquivos/{ nomeCsv }", "w", newline = "" ) as file:
        w = Csv.DictWriter( file, fieldnames = list(invoices[0].keys()) )
        w.writeheader()
        w.writerows( invoices )
    
    # enviar o .csv para concluir o desafio
    navegador.find_element( By.NAME, "csv" )\
             .send_keys( rf"{OS.getcwd()}\arquivos\{nomeCsv}" )

    # finalizar
    Time.sleep(5)
    navegador.quit()

"""
Desafio RPA: https://rpachallengeocr.azurewebsites.net/

Dados necessários dos INVOICEs:
    - ID: TABELA
    - DueDate: TABELA DD-MM-YYYY
    - InvoiceNo: IMAGEM
    - InvoiceDate: IMAGEM
    - CompanyName: IMAGEM
    - TotalDue: IMAGEM

Procurar apenas pelos INVOICEs onde:
    - DueDate <= Date.Now

São 2 formatos de INVOICES
Ambos os formatos precisam de uma interpretação única
    - Sit Amet Corp.
    - Aenean LLC
"""
if __name__ == "__main__":
    # altera o cwd para a pasta desse arquivo
    OS.chdir(CWD)
    # limpa a pasta dos arquivos
    [ OS.remove(f"./arquivos/{imagem}") for imagem in OS.listdir("./arquivos") ]
    
    main()
    exit(0)