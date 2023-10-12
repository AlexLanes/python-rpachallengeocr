# std
import re as Regex
from json import dump
from time import sleep
from os import getcwd, system as abrirArquivo
from datetime import datetime as DateTime, date as Date
# externo
from selenium.webdriver.common.by import By
from selenium.webdriver import Edge, EdgeOptions
from selenium.webdriver.edge.service import Service
import selenium.webdriver.support.expected_conditions as Expect
from selenium.webdriver.support.wait import WebDriverWait as Wait
from webdriver_manager.microsoft import EdgeChromiumDriverManager

class XPaths:
    TBODY = "/html/body/div/div/div[2]/div/div[1]/div[1]/table/tbody"
    BR = '//*[@id="result-sec"]/div[1]/br'
    TEXTO = '//*[@id="result-sec"]/div[1]'
    STATUS = "/html/body/div/div/div[2]/div/div[2]/h1/span"
    MENSAGEM = "/html/body/div/div/div[2]/div/div[2]/strong"

    def id( indexTr: int ) -> str: 
        return f"{ XPaths.TBODY }/tr[{ indexTr }]/td[2]"
    def due_date( indexTr: int ) -> str: 
        return f"{ XPaths.TBODY }/tr[{ indexTr }]/td[3]"
    def url( indexTr: int ) -> str: 
        return f"{ XPaths.TBODY }/tr[{ indexTr }]/td[4]/a"

class Navegador:
    navegador: Edge
    def __init__(self, url: str) -> None:
        """iniciar o navegador com as opções e no url informado"""
        driver = EdgeChromiumDriverManager().install()
        options = EdgeOptions()
        options.add_argument("--start-maximized")

        self.navegador = Edge( options, Service(driver) )
        self.navegador.implicitly_wait(10)
        self.navegador.get(url)
    
    def iniciar_desafio(self) -> None:
        """clicar em "Start" e esperar o refresh da página"""
        idAntesRefresh = self.navegador.find_element( By.XPATH, XPaths.id(1) ).text
        self.navegador.find_element(By.ID, "start").click()
        condicao = Expect.text_to_be_present_in_element( (By.XPATH, XPaths.id(1)), idAntesRefresh ) 
        Wait(self.navegador, 2).until_not(condicao)
    
    def obter_invoices(self) -> list[dict]:
        """obter invoices com o dueDate <= hoje"""
        invoices: list[dict] = []
        def conversorData(data: str) -> Date:
            """faz o parse para Date()"""
            return DateTime.strptime(data, r"%d-%m-%Y").date()

        # Percorrer todas as páginas
        while True:
            inicio = 1
            fim = len( self.navegador.find_elements(By.XPATH, f"{XPaths.TBODY}/tr") ) + 1
            
            # Percorrer todos os Invoices da página
            for index in range(inicio, fim):
                # Garantir que o DueDate é menor ou igual a hoje
                dueDate = self.navegador.find_element( By.XPATH, XPaths.due_date(index) ).text
                if conversorData(dueDate) > Date.today(): continue
                # Salvar atributos do Invoice
                urlImagem = self.navegador.find_element( By.XPATH, XPaths.url(index) )\
                                          .get_attribute("href")
                nomeImagem = urlImagem.split("/")[-1]
                invoices.append({
                    "ID": self.navegador.find_element( By.XPATH, XPaths.id(index) ).text,
                    "DueDate": dueDate,
                    "contexto": {
                        "nome": nomeImagem,
                        "url": urlImagem
                    }
                })
            
            # Próxima página ?
            botaoNext = self.navegador.find_element(By.ID, "tableSandbox_next")
            if "disabled" not in botaoNext.get_attribute("class"):
                botaoNext.click()
            else: break
        
        return invoices

    def baixar_imagem(self, invoice: dict) -> None:
        """abrir imagem, salvar localmente e retornar a aba original"""
        abaOriginal = self.navegador.current_window_handle
        
        # abrir nova aba e trocar o navegador para ela
        self.navegador.switch_to.new_window("tab")
        self.navegador.get( invoice["contexto"]["url"] )
        
        # baixar imagem
        self.navegador.find_element(By.TAG_NAME, "img")\
                      .screenshot(f"./arquivos/{ invoice['contexto']['nome'] }")
        
        # retornar à aba original
        self.navegador.close()
        self.navegador.switch_to.window(abaOriginal)

    def iniciar_processamento(self, invoice: dict) -> None:
        """abrir site de processamento ocr, realizar o upload da imagem e iniciar o processamento"""
        # abrir nova aba, trocar o navegador para ela e guardar o handle da aba no invoice
        self.navegador.switch_to.new_window("tab")
        self.navegador.get("https://www.imagetotext.info/")
        invoice["contexto"]["aba"] = self.navegador.current_window_handle

        # realizar o upload, esperar carregar e clicar em submit
        self.navegador.find_element(By.ID, "file")\
                      .send_keys(rf"{ getcwd() }\arquivos\{ invoice['contexto']['nome'] }")
        condicao = Expect.text_to_be_present_in_element( (By.CLASS_NAME, "img-size"), "File Size" )
        Wait(self.navegador, 5).until_not(condicao)
        self.navegador.find_element(By.ID, "jsShadowRoot")\
                      .click()
    
    def capturar_informacoes(self, invoice: dict) -> None:
        """capturar informações do invoice na aba do processamento da imagem e fechar aba"""
        # abri a aba do processamento da imagem
        self.navegador.switch_to.window( invoice["contexto"]["aba"] )

        # esperar o processamento finalizar
        # => quando o <br> aparece no elemento do TEXTO
        condicao = Expect.presence_of_element_located(( By.XPATH, XPaths.BR ))
        Wait(self.navegador, 30).until(condicao)

        # obter texto e quebrar em linhas
        linhas = self.navegador.find_element(By.XPATH, XPaths.TEXTO)\
                               .text.split("\n")
        
        # capturar informações
        numero, data, nome, total = None, None, linhas[0], None
        for linha in linhas:
            # data
            if data is None:
                search = Regex.search(r"\d{4}-\d{2}-\d{2}", linha)
                if search is not None:
                    data = search.group().split("-")
                    data.reverse()
                    data = "-".join(data)
            # número
            if numero is None:
                search = Regex.search(r"(?<=#)\d+", linha)
                numero = search.group() if search is not None else numero
            # total
            search = Regex.search(r"\d+\.\d+", linha)
            if search is not None:
                total = search.group()

        # inserir informações no invoice
        invoice["InvoiceNo"] = numero
        invoice["InvoiceDate"] = data
        invoice["CompanyName"] = nome
        invoice["TotalDue"] = total

        # fechar a aba
        self.navegador.close()

    def finalizar_desafio(self, nomeCsv: str, aguardar: int = 0) -> None:
        """realizar o submit do csv e fechar o navegador"""
        # alterar para a aba do desafio
        aba =  self.navegador.window_handles
        self.navegador.switch_to.window( aba[0] )

        # enviar o .csv para concluir o desafio
        self.navegador.find_element(By.NAME, "csv")\
                      .send_keys(rf"{ getcwd() }\arquivos\{ nomeCsv }")

        # criar status
        sleep(1)
        status = {
            "status": self.navegador.find_element(By.XPATH, XPaths.STATUS).text,
            "mensagem": self.navegador.find_element(By.XPATH, XPaths.MENSAGEM).text
        }
        with open(r"arquivos\status.json", "w") as file:
            dump(status, file, indent = 4)

        # fechar navegador e mostrar o status
        sleep(aguardar)
        self.navegador.quit()
        abrirArquivo(r"arquivos\status.json")