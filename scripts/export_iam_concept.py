"""Render the versioned IAM concept as a readable FLOWDOC PDF."""
from pathlib import Path
import re
from html import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Preformatted

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/architecture/iam-security-concept.md'
TARGET = ROOT / 'output/pdf/SEC-IAM-001_IAM-Sicherheitskonzept_v1.0.pdf'

def inline(s):
    s = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'\1', s)
    s = escape(s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    return re.sub(r'`([^`]+)`', r'<font name="Courier">\1</font>', s)

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Text', fontName='Helvetica', fontSize=9, leading=13, spaceAfter=6))
styles.add(ParagraphStyle(name='Cell', fontName='Helvetica', fontSize=7.4, leading=10))
styles['Title'].fontSize = 20
story=[]
lines=SOURCE.read_text().splitlines(); i=0
while i<len(lines):
    line=lines[i].strip()
    if not line:
        i+=1; continue
    if line.startswith('```'):
        lang=line[3:]; code=[]; i+=1
        while i<len(lines) and not lines[i].startswith('```'):
            code.append(lines[i]); i+=1
        if lang=='mermaid':
            story.append(Paragraph('Vertrauensweg: AD liefert Identitäten und Gruppen an Keycloak. Portal und KI-Host erhalten dienstgebundene Tokens. MCP prüft Werkzeugrechte; DMS-/ERP-API prüft die konkreten Objektberechtigungen.',styles['Text']))
        else:
            for row in code:
                story.append(Paragraph(escape(row).replace(' ','&#160;'),styles['Cell']))
        story.append(Spacer(1,8)); i+=1; continue
    if line.startswith('|'):
        rows=[]
        while i<len(lines) and lines[i].strip().startswith('|'):
            row=lines[i].strip().strip('|').split('|')
            if not all(re.fullmatch(r'\s*:?-+:?\s*',v) for v in row):
                rows.append([Paragraph(inline(v.strip()),styles['Cell']) for v in row])
            i+=1
        cols=len(rows[0]); width=A4[0]-80
        table=Table(rows,colWidths=[width/cols]*cols,repeatRows=1,hAlign='LEFT')
        table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#d9ecea')),('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#b4c8c6')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story += [table,Spacer(1,10)]; continue
    if line.startswith('#'):
        level=len(line)-len(line.lstrip('#'))
        story.append(Paragraph(inline(line.lstrip('# ')),styles['Title' if level==1 else 'Heading'+str(min(level-1,3))])); i+=1; continue
    paragraph=[line]; i+=1
    while i<len(lines) and lines[i].strip() and not lines[i].lstrip().startswith(('#','|','```','- ')):
        paragraph.append(lines[i].strip()); i+=1
    text=' '.join(paragraph).removeprefix('> ').removeprefix('- ')
    story.append(Paragraph(inline(text),styles['Text']))

def footer(canvas,doc):
    canvas.setFont('Helvetica',8); canvas.setFillColor(colors.HexColor('#526866'))
    canvas.drawString(40,25,'SEC-IAM-001 | v1.0 | 17.11.2026 | ENTWURF - intern')
    canvas.drawRightString(A4[0]-40,25,str(doc.page))

TARGET.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(TARGET),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=40,bottomMargin=45,title='SEC-IAM-001 - IAM-Sicherheitskonzept - Entwurf',author='Business Applications').build(story,onFirstPage=footer,onLaterPages=footer)
print(TARGET)
