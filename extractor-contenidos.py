import streamlit as st
import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.style import WD_STYLE_TYPE
from io import BytesIO

# --- Funciones de conversión HTML a DOCX (sin cambios, las mismas que antes) ---
def add_styled_run(paragraph_or_heading, bs_node):
    if isinstance(bs_node, NavigableString):
        text = str(bs_node)
        if text.strip():
            paragraph_or_heading.add_run(text)
    elif isinstance(bs_node, Tag):
        text = bs_node.get_text(strip=True)
        if not text and bs_node.name != 'br':
            return

        if bs_node.name in ['strong', 'b']:
            run = paragraph_or_heading.add_run(text)
            run.bold = True
        elif bs_node.name in ['em', 'i']:
            run = paragraph_or_heading.add_run(text)
            run.italic = True
        elif bs_node.name == 'a':
            href = bs_node.get('href')
            if href:
                try:
                    paragraph_or_heading.add_hyperlink(text, href, is_external=True)
                except Exception as e:
                    st.warning(f"Advertencia: No se pudo crear el hipervínculo para '{text}': {e}")
                    run = paragraph_or_heading.add_run(text + f" [{href}]")
                    run.font.color.rgb = RGBColor(0x05, 0x63, 0xC1)
                    run.font.underline = True
            else:
                paragraph_or_heading.add_run(text)
        elif bs_node.name == 'br':
            paragraph_or_heading.add_run().add_break()
        else:
            if bs_node.contents:
                for child in bs_node.contents:
                    add_styled_run(paragraph_or_heading, child)
            elif text:
                 paragraph_or_heading.add_run(text)

def html_to_docx_elements(bs_element, document_or_container):
    if isinstance(bs_element, NavigableString):
        text = str(bs_element).strip()
        if text:
            p = document_or_container.add_paragraph()
            p.add_run(text)
        return

    if not isinstance(bs_element, Tag):
        return

    tag_name = bs_element.name.lower()

    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        level = int(tag_name[1])
        heading = document_or_container.add_heading(level=level)
        for content_node in bs_element.contents:
            add_styled_run(heading, content_node)
    elif tag_name == 'p':
        p = document_or_container.add_paragraph()
        for content_node in bs_element.contents:
            add_styled_run(p, content_node)
    elif tag_name == 'ul':
        for li in bs_element.find_all('li', recursive=False):
            item_p = document_or_container.add_paragraph(style='ListBullet')
            for content_node in li.contents:
                add_styled_run(item_p, content_node)
    elif tag_name == 'ol':
        for li in bs_element.find_all('li', recursive=False):
            item_p = document_or_container.add_paragraph(style='ListNumber')
            for content_node in li.contents:
                add_styled_run(item_p, content_node)
    elif tag_name == 'br':
        if document_or_container.paragraphs:
            document_or_container.paragraphs[-1].add_run().add_break()
        else:
            document_or_container.add_paragraph().add_run().add_break()
    elif tag_name == 'div':
        for child in bs_element.children:
            html_to_docx_elements(child, document_or_container)
    elif tag_name == 'style':
        pass
    else:
        for child in bs_element.children:
            html_to_docx_elements(child, document_or_container)

# --- Aplicación Streamlit ---
st.set_page_config(page_title="HTML a Word", layout="wide") # layout="centered" o "wide"
st.title("📄 Extractor de Contenido HTML a Documento Word")
st.markdown("""
Esta aplicación te permite extraer el contenido de un elemento HTML específico (identificado por su ID)
de una página web y guardarlo como un documento de Word (.docx), conservando parte de la estructura
(encabezados, párrafos, listas, negritas, cursivas y enlaces).
""")

st.markdown("---") # Separador visual

# Sección de Configuración en el área central usando st.form
st.subheader("⚙️ Configuración de Extracción")
with st.form(key="extraction_form"):
    url = st.text_input("🔗 URL de la página:", "https://www.unir.net/educacion/master-secundaria/")
    div_id = st.text_input("🆔 ID del div a extraer:", "main-description")
    
    # Botón de envío para el formulario
    submitted = st.form_submit_button("🚀 Extraer y Convertir")

# La lógica de procesamiento ahora se activa solo cuando el formulario es enviado
if submitted:
    if not url:
        st.error("Por favor, introduce una URL.")
    elif not div_id:
        st.error("Por favor, introduce el ID del div.")
    else:
        try:
            with st.spinner(f"Descargando contenido de {url}..."):
                response = requests.get(url, timeout=15)
                response.raise_for_status()
            st.success(f"Página descargada exitosamente de {url}")

            with st.spinner("Parseando HTML..."):
                soup = BeautifulSoup(response.text, 'html.parser')
                main_content_div = soup.find('div', id=div_id)

            if main_content_div:
                st.success(f"Div con id='{div_id}' encontrado.")

                with st.spinner("Convirtiendo HTML a DOCX..."):
                    document = Document()
                    document.core_properties.title = f"Contenido de {div_id} de {url}"
                    document.core_properties.author = "Extractor HTML Streamlit App"
                    
                    # Ya no se añade la portada
                    # document.add_heading('Contenido Extraído de la Web', level=0)
                    # ... (código de portada eliminado) ...

                    for element in main_content_div.children:
                        html_to_docx_elements(element, document)

                doc_io = BytesIO()
                document.save(doc_io)
                doc_io.seek(0)

                st.success("¡Conversión a Word completada!")

                clean_url_for_filename = url.split('//')[-1].split('/')[0].replace('.', '_')
                output_filename = f"contenido_{clean_url_for_filename}_{div_id}.docx"

                st.download_button(
                    label="📥 Descargar Documento Word (.docx)",
                    data=doc_io,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            else:
                st.error(f"No se encontró el div con id='{div_id}' en la página.")
                st.info("Verifica la URL y el ID. Puedes inspeccionar el código fuente de la página (Ctrl+U o Cmd+Opt+U) para encontrar el ID correcto.")

        except requests.exceptions.RequestException as e:
            st.error(f"Error de red al intentar acceder a la URL: {e}")
        except Exception as e:
            st.error(f"Ocurrió un error inesperado: {e}")
            st.exception(e)

# Información en la sidebar (opcional, puedes moverla o eliminarla)
st.sidebar.markdown("---")
st.sidebar.info("Creado con Streamlit y python-docx.")
