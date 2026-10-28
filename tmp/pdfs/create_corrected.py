from pathlib import Path
prep=Path('tmp/pdfs/check_trimmed.py').read_text(encoding='utf-8-sig').replace("exec(compile(s,'trimmed_check','exec'))",'')
exec(prep)
s=s.replace('tmp/pdfs/four_bullet_trimmed_check.pdf','output/pdf/Aaron_Grossman_Resume_Corrected_Preview.pdf').replace('trimmed_page_','corrected_page_')
s=s.replace("b('Strengthened experiment validation with bonus redemption checks to reduce misconfigured test/control exposure; refined Sigma alerting logic.')", """b('Improved experimentation procedures by adding bonus redemption validation checks to reduce the risk of misconfigured test/control exposure.')
b('Refined Sigma automated alerting logic to improve internal analytics workflows.')""")
s=s.replace("spaceBefore=7,spaceAfter=4)","spaceBefore=7,spaceAfter=4,keepWithNext=True)")
Path('tmp/pdfs/build_corrected.py').write_text(s,encoding='utf-8')
exec(compile(s,'corrected_preview','exec'))
