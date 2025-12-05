import requests

# URL BASE simplificada (a que falhou com /search, mas deve funcionar com /book)
BASE_URL = "https://openscriptureapi.org/api/v1" 

def obter_capitulo_completo(book_id, chapter_number, language='por'):
    """
    Obtém um capítulo específico (com todos os versículos) e detalhes em Português.
    Exemplo: book_id='1nephi', chapter_number=3
    """
    
    # 1. Endpoint: Usando o formato /book/[book_id]/[chapter_number]
    endpoint = f"{BASE_URL}/book/{book_id}/{chapter_number}"
    
    # 2. Parâmetros de Consulta: Incluindo idioma e informações extras
    params = {
        'lang': language, # Define o idioma do texto/sumário
        'includeExtras.volumeInfo': 'true',
        'includeExtras.bookInfo': 'true',
        'includeExtras.footnotes': 'true' 
        # API Keys não são necessárias, mas se fossem, iriam aqui: 'api-key': 'SUA_CHAVE'
    }
    
    try:
        print(f"Buscando capítulo: {book_id.upper()} {chapter_number} em {language.upper()}...")
        response = requests.get(endpoint, params=params)
        response.raise_for_status() # Lança erro 404 se o recurso não for encontrado
        
        data = response.json()
        
        # 3. Processar e Exibir
        capitulo = data.get('chapter', {})
        livro = data.get('book', {})
        
        print("\n" + "=" * 50)
        print(f"📖 {livro.get('title', book_id.upper())}, {capitulo.get('delineation', 'Capítulo')} {capitulo.get('number', chapter_number)}")
        print(f"SUMÁRIO: {capitulo.get('summary', 'N/A')}")
        print("=" * 50)
        
        for verse in capitulo.get('verses', []):
            # Assumimos que o índice + 1 é o número do versículo
            v_num = capitulo['verses'].index(verse) + 1
            print(f"V.{v_num} - {verse.get('text', '')}")
            if verse.get('footNotes'):
                print(f"   (Notas: {verse['footNotes']})")
        
        return data
        
    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao buscar capítulo: {http_err}")
        print(f"URL Falhada: {response.url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão: {e}")
        return None

# --- EXECUÇÃO ---
# Se você quiser rodar este teste, chame a função principal
# obter_capitulo_completo('1nephi', 3, 'por')