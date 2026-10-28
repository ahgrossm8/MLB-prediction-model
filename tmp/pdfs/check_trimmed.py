from pathlib import Path
s=Path('tmp/pdfs/check_four.py').read_text(encoding='utf-8-sig').split("exec(compile(s,")[0]
exec(s)
changes={
'Designed a cross-sell merchandising attribution dashboard to identify last-touch interactions driving product adoption and inform optimization recommendations.':'Built a cross-sell attribution dashboard identifying last-touch interactions driving product adoption and informing optimization.',
'Owned cross-sell analytics and weekly executive reporting, translating performance drivers and risks into actionable recommendations for stakeholders.':'Owned cross-sell analytics and weekly executive reporting, translating performance drivers and risks into recommendations.',
'Owned analytics across 30+ client accounts, delivering email/SMS performance insights, customer lifecycle analyses, annual business reviews, and trigger audits.':'Owned email/SMS analytics across 30+ client accounts, delivering performance insights, lifecycle analyses, business reviews, and trigger audits.',
'Created and led six-month weekly courses in SQL and Looker Studio, with recordings reused as analyst training materials.':'Created and taught six-month courses in SQL and Looker Studio; recordings became reusable analyst training materials.'
}
for old,new in changes.items():
    assert old in s
    s=s.replace(old,new)
s=s.replace('four_bullet_check.pdf','four_bullet_trimmed_check.pdf').replace('four_bullet_page_','trimmed_page_')
exec(compile(s,'trimmed_check','exec'))
