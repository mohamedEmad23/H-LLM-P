import fitz
import os

def convert_pdfs_to_markdown():
    """Convert all PDF files in current directory to markdown."""
    pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
    
    if not pdf_files:
        print("No PDF files detected in current directory")
        return
    
    for pdf_file in pdf_files:
        try:
            doc = fitz.open(pdf_file)
            md_file = pdf_file.replace('.pdf', '.md')

            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(f'# {pdf_file}\n\n')

                for page_num, page in enumerate(doc, 1):
                    f.write(f'## Page {page_num}\n\n')
                    f.write(page.get_text())
                    f.write('\n\n')
            
            print(f'Converted {pdf_file} -> {md_file}')
        except Exception as e:
            print(f'x Error converting {pdf_file}: {e}')


if __name__ == '__main__':
    convert_pdfs_to_markdown()
