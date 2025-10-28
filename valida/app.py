# app.py
import streamlit as st
from PIL import Image
import pytesseract
import io
import re

# --- Funções de Extração e Validação (sem alterações) ---

def classify_document(text):
    """Classifica o documento como laudo, exame ou desconhecido."""
    lower_text = text.lower()
    exam_keywords = ['exame', 'resultado de', 'hemograma', 'ressonância magnética', 'raio-x', 'tomografia']
    report_keywords = ['laudo', 'atestado', 'relatório médico', 'declaração']

    if any(word in lower_text for word in exam_keywords):
        if any(word in lower_text for word in report_keywords):
            return 'Laudo com Exame'
        return 'Exame'
    if any(word in lower_text for word in report_keywords):
        return 'Laudo'
    return 'Desconhecido'

def extract_cid(text):
    """Extrai o código CID do texto."""
    match = re.search(r'cid[-\s]?10?\s*[:\-\s]?\s*([a-zA-Z]\d{1,2}(\.\d{1,2})?)', text, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None

def extract_registry(text):
    """Extrai registros profissionais e simula a validação de status."""
    pattern = re.compile(r'\b(CRM|CRP|CREFITO|CRO|COREN)\b[\s/]*([A-Z]{2})?[\s/]*(\d+)', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        registry_type, state, number = match.groups()
        registry_str = f"{registry_type.upper()}/{state.upper() if state else ''} {number}"
        status = "Ativo" # Status simulado
        return registry_str, status
    return None, None

def check_afastamento(text):
    """Verifica se há indicação de afastamento no texto."""
    keywords = ['afastamento', 'repouso', 'suspensão de suas atividades', 'impossibilitado de comparecer', 'afastar-se']
    return any(re.search(r'\b' + keyword + r'\b', text, re.IGNORECASE) for keyword in keywords)

def check_signature(text):
    """Verifica a presença de uma assinatura."""
    return bool(re.search(r'ass\w*:', text, re.IGNORECASE))

# --- Estrutura principal da Aplicação ---

def main():
    st.set_page_config(page_title="ValidaEJA", layout="centered")

    # 1. INICIALIZAÇÃO DO ESTADO DA SESSÃO
    # Garante que as variáveis de estado existam desde o início.
    if "analysis_complete" not in st.session_state:
        st.session_state.analysis_complete = False
        st.session_state.results = None
        st.session_state.error_message = None

    # Layout do Cabeçalho
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("Logo-Ejabrasil-sem-fundo.png.jpg", use_column_width=True)

    st.title("Validador de Laudos Médicos")

    # 2. LÓGICA DE EXIBIÇÃO CONDICIONAL
    # Mostra a tela de upload OU a tela de resultados, nunca as duas ao mesmo tempo.
    if st.session_state.analysis_complete:
        display_results()
    else:
        display_uploader()

def display_uploader():
    """Função para exibir a interface de upload."""
    st.markdown("Faça o upload do documento (.jpg, .png, .jpeg) para análise automática.")
    
    uploaded_file = st.file_uploader(
        "Selecione o arquivo",
        type=['jpg', 'jpeg', 'png'],
        key="uploader"
    )

    if uploaded_file is not None:
        with st.spinner('Analisando o documento...'):
            try:
                # Processamento do arquivo
                image = Image.open(uploaded_file)
                text = pytesseract.image_to_string(image, lang='por')

                # Coleta todos os resultados em um dicionário
                results = {
                    'doc_type': classify_document(text),
                    'cid': extract_cid(text),
                    'registry_info': extract_registry(text),
                    'afastamento': check_afastamento(text),
                    'signature': check_signature(text),
                    'raw_text': text
                }

                # Atualiza o estado da aplicação de uma só vez
                st.session_state.results = results
                st.session_state.analysis_complete = True
                st.session_state.error_message = None

            except Exception as e:
                st.session_state.error_message = f"Ocorreu um erro ao processar o arquivo: {e}"
        
        # Força a re-execução do script para refletir o novo estado
        st.rerun()

    # Exibe mensagem de erro se houver
    if st.session_state.error_message:
        st.error(st.session_state.error_message)


def display_results():
    """Função para exibir os resultados da análise."""
    res = st.session_state.results
    
    st.markdown("---")
    st.subheader("Resultado da Análise")

    # Regras de aprovação
    registry, registry_status = res['registry_info']
    is_valid_type = res['doc_type'] in ['Laudo', 'Laudo com Exame']
    is_active_registry = registry_status == "Ativo"
    is_approved = all([is_valid_type, res['cid'], is_active_registry, res['afastamento'], res['signature']])

    if is_approved:
        st.success("**APROVADO:** O trancamento pode seguir.")
    else:
        st.error("**REPROVADO:** O documento possui pendências.")

    # Checklist
    st.markdown(f"""
    - { '✅' if is_valid_type else '❌'} **Tipo de Documento:** {res['doc_type']}
    - { '✅' if res['cid'] else '❌'} **Diagnóstico (CID):** {res['cid'] or "Não encontrado"}
    - { '✅' if is_active_registry else '❌'} **Registro Profissional:** {f"{registry} (Status: {registry_status})" if registry else "Não encontrado"}
    - { '✅' if res['afastamento'] else '❌'} **Indicação de Afastamento:** {'Encontrada' if res['afastamento'] else 'Não encontrada'}
    - { '✅' if res['signature'] else '❌'} **Assinatura do Responsável:** {'Encontrada' if res['signature'] else 'Não encontrada'}
    """)

    with st.expander("Ver texto extraído do documento"):
        st.text_area("", res['raw_text'], height=300)

    # Botão para resetar o estado e permitir nova análise
    if st.button("Analisar Novo Documento"):
        st.session_state.analysis_complete = False
        st.session_state.results = None
        st.session_state.error_message = None
        st.rerun()

# Ponto de entrada da aplicação
if __name__ == '__main__':
    main()
