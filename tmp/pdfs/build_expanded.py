from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from pypdf import PdfReader
import pypdfium2 as pdfium

out=Path('output/pdf/Aaron_Grossman_Resume_Expanded_Preview.pdf')
pdfmetrics.registerFont(TTFont('Arial',r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('ArialBold',r'C:\Windows\Fonts\arialbd.ttf'))
pdfmetrics.registerFontFamily('Arial',normal='Arial',bold='ArialBold')
styles={
'name':ParagraphStyle('name',fontName='ArialBold',fontSize=21,leading=25,spaceAfter=4),
'contact':ParagraphStyle('contact',fontName='Arial',fontSize=10,leading=13,spaceAfter=8),
'section':ParagraphStyle('section',fontName='ArialBold',fontSize=11,leading=14,spaceBefore=7,spaceAfter=4,keepWithNext=True),
'employer':ParagraphStyle('employer',fontName='ArialBold',fontSize=11,leading=13,spaceBefore=4,spaceAfter=1,keepWithNext=True),
'role':ParagraphStyle('role',fontName='Arial',fontSize=10.5,leading=13,spaceAfter=3,keepWithNext=True),
'body':ParagraphStyle('body',fontName='Arial',fontSize=10.5,leading=13,spaceAfter=2),
'bullet':ParagraphStyle('bullet',fontName='Arial',fontSize=10.5,leading=13,leftIndent=11,firstLineIndent=0,bulletIndent=0,spaceAfter=1),
}
story=[]
plain=[]
def p(t,style='body'):
    story.append(Paragraph(t,styles[style])); plain.append(t)
def b(t):
    story.append(Paragraph(t,styles['bullet'],bulletText='\u2022')); plain.append('- '+t)
p('Aaron Grossman','name')
p('ahgrossman96@gmail.com | (631) 617-3523 | New York, NY | Open to remote','contact')
p('SKILLS','section')
p('SQL, Python, BigQuery, Tableau, Looker, Looker Studio, Sigma, Git, Excel, A/B Testing, Data Visualization, Stakeholder Communication, AI-Assisted Analytics')
p('PROFESSIONAL EXPERIENCE','section')
p('DraftKings','employer')
p('Manager, Cross Product Analytics | July 2025 - April 2026','role')
b('Managed and mentored two analysts through coaching, annual performance reviews, and structured improvement planning.')
b('Developed team roadmaps across referral, cross-play, and cross-sell initiatives to align analytics with product and business priorities.')
b('Owned cross-sell analytics and weekly executive reporting, translating performance drivers and risks into recommendations.')
b('Built a Refer a Friend analytics framework and funnel monitoring system to identify conversion drivers, surface attribution gaps, and inform strategy.')
b('Built a cross-sell attribution dashboard identifying last-touch interactions driving product adoption and informing optimization.')
b('Led cross-play personalization testing, generating approximately $40K in annualized theoretical gross gaming revenue by tailoring content to user behavior.')
b('Improved experimentation procedures by adding bonus redemption validation checks to reduce the risk of misconfigured test/control exposure.')
b('Refined Sigma automated alerting logic to improve internal analytics workflows.')
p('Alchemy Worx','employer')
p('Manager of Analytics Team | July 2022 - July 2025','role')
b('Managed three junior analysts, overseeing projects, balancing workloads, and aligning stakeholder expectations.')
b('Continued hands-on client analytics alongside team management, delivering performance reporting, customer lifecycle analyses, and actionable recommendations across email and SMS.')
b('Led department-wide analyst meetings and cross-team collaboration sessions to share knowledge and resolve project roadblocks.')
b('Identified and addressed issues in automated messaging, contributing to revenue increases of up to 512% on those messages.')
p('Alchemy Worx','employer')
p('Jr. Data Analyst | November 2019 - June 2022','role')
b('Owned email/SMS analytics across 30+ client accounts, delivering performance insights, lifecycle analyses, business reviews, and trigger audits.')
b('Created the framework for migrating client reporting from Excel to Looker Studio and built dashboards in Looker.')
b('Created and taught six-month courses in SQL and Looker Studio; recordings became reusable analyst training materials.')
p('PROJECTS','section')
p('MLB Game Outcome Prediction and Automation','employer')
p('Independent Project | Fall 2023 - October 2026','role')
b('Built a Python and BigQuery pipeline connecting MLB matchups, published lineups, rolling player statistics, and game-level win probabilities.')
b('Implemented a 31-feature logistic regression model using 7,594 historical games, with saved preprocessing, lineup weighting, and checks for missing or stale inputs.')
b('Developed scheduled prediction checks and email delivery with per-recipient tracking to suppress repeat sends, plus logging and automated tests.')
p('EDUCATION','section')
p('<b>Binghamton University</b> | MBA, Business Analytics &amp; Supply Chain Management | 2019')
p('<b>Binghamton University</b> | B.A., Mathematical Sciences; Minor in Economics | 2018')
project_start = next(i for i, item in enumerate(story) if getattr(item, 'text', '') == 'PROJECTS')
education_start = next(i for i, item in enumerate(story) if getattr(item, 'text', '') == 'EDUCATION')
story[project_start:education_start] = [KeepTogether(story[project_start:education_start])]
SimpleDocTemplate(str(out),pagesize=(612,792),rightMargin=36,leftMargin=36,topMargin=30,bottomMargin=30,title='Aaron Grossman Resume',author='Aaron Grossman').build(story)
d=PdfReader(str(out)); print('PAGES',len(d.pages)); print('\n'.join(x.extract_text() for x in d.pages))
render=pdfium.PdfDocument(str(out))
for i in range(len(render)):
    render[i].render(scale=1.8).to_pil().save(f'tmp/pdfs/expanded_page_{i+1}.png')


