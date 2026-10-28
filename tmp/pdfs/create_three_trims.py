from pathlib import Path
s=Path('tmp/pdfs/build_corrected.py').read_text(encoding='utf-8-sig')
changes={
'Managed three junior analysts, overseeing projects, balancing workloads, and aligning stakeholder expectations.':'Managed three junior analysts, overseeing projects, workloads, and stakeholder expectations.',
'Led department-wide analyst meetings and cross-team collaboration sessions to share knowledge and resolve project roadblocks.':'Led department-wide analyst meetings and cross-team sessions to share knowledge and resolve roadblocks.',
'Created the framework for migrating client reporting from Excel to Looker Studio and built dashboards in Looker.':'Built the framework for migrating client reporting from Excel to Looker Studio; created Looker dashboards.'
}
for old,new in changes.items():
    assert s.count(old)==1
    s=s.replace(old,new)
s=s.replace('Aaron_Grossman_Resume_Corrected_Preview.pdf','Aaron_Grossman_Resume_Three_Trims.pdf').replace('corrected_page_','three_trims_page_')
Path('tmp/pdfs/build_three_trims.py').write_text(s,encoding='utf-8')
exec(compile(s,'three_trims','exec'))
