from pathlib import Path
s=Path('tmp/pdfs/build_resume.py').read_text(encoding='utf-8-sig')
s=s.replace('output/pdf/Aaron_Grossman_Resume_Mock.pdf','tmp/pdfs/four_bullet_check.pdf').replace('resume_mock_page_','four_bullet_page_')
s=s.replace("b('Managed three junior analysts, overseeing projects, balancing workloads, and aligning stakeholder expectations; led department-wide meetings and cross-team collaboration.')", """b('Managed three junior analysts, overseeing projects, balancing workloads, and aligning stakeholder expectations.')
b('Continued hands-on client analytics alongside team management, delivering performance reporting, customer lifecycle analyses, and actionable recommendations across email and SMS.')
b('Led department-wide analyst meetings and cross-team collaboration sessions to share knowledge and resolve project roadblocks.')""")
s=s.replace('Identified roadblocks and solutions for automated messages, resulting in revenue increases of up to 512% on those messages.','Identified and addressed issues in automated messaging, contributing to revenue increases of up to 512% on those messages.')
exec(compile(s,'layout_check','exec'))
