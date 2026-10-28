from pathlib import Path
s=Path('tmp/pdfs/build_three_trims.py').read_text(encoding='utf-8-sig')
old='Identified and addressed issues in automated messaging, contributing to revenue increases of up to 512% on those messages.'
assert s.count(old)==1
s=s.replace(old,'Optimized automated messaging, increasing revenue by up to 512% on individual messages.')
s=s.replace('Aaron_Grossman_Resume_Three_Trims.pdf','Aaron_Grossman_Resume_Updated.pdf').replace('three_trims_page_','updated_page_')
Path('tmp/pdfs/build_updated.py').write_text(s,encoding='utf-8')
exec(compile(s,'updated_resume','exec'))
