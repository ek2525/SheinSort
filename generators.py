# generators.py
import csv
from datetime import datetime
from reportlab.lib.styles    import getSampleStyleSheet
from reportlab.platypus      import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
from reportlab.lib.pagesizes import landscape, LETTER
from reportlab.lib import colors
from reportlab.lib.units     import inch

def make_pdf(items, customer, path, oos_count):
    total = sum(int(i['quantity']) for i in items)
    total_amount = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in items)
    doc = SimpleDocTemplate(
        path, pagesize=landscape(LETTER),
        leftMargin=0.5*inch, rightMargin=0.5*inch,
        topMargin=0.5*inch, bottomMargin=0.5*inch
    )
    styles = getSampleStyleSheet()
    body = styles['BodyText']
    body.fontName = 'Helvetica'
    body.fontSize = 10
    body.leading = 12

    story = [
        Paragraph(f"{customer}'s Order (Total items: {total})", styles['Title']),
        Spacer(1, 0.2*inch)
    ]
    data = [['#', 'SKU', 'Qty', 'Item Name', 'Price']]

    for idx, it in enumerate(items, 1):
        pfx, sfx = it['goods_sn'][:-4], it['goods_sn'][-4:]
        price = it.get('price', '')
        data.append([
            str(idx),
            Paragraph(f"{pfx}<b>{sfx}</b>", body),
            it['quantity'],
            ' '.join(it['name'].split()[:10]),
            price
        ])

    # Add totals row
    data.append([
        '',  # Row number
        Paragraph('<b>Total</b>', body),
        str(total),
        '',  # Item Name
        f"${total_amount:.2f}"
    ])

    table = Table(data, colWidths=[0.5*inch, 2*inch, 0.5*inch, 6*inch, 1*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, -1), (-1, -1), colors.beige),  # Totals row color
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold')
    ]))
    story.extend([
        table,
        Spacer(1, 0.2*inch),
        Paragraph(f"Items to recheck (out of stock): {oos_count}", body)
    ])
    doc.build(story)


def make_merged_pdf(m_items, order, path):
    total = sum(int(i['quantity']) for i in m_items)
    doc = SimpleDocTemplate(
      path, pagesize=landscape(LETTER),
      leftMargin=0.5*inch, rightMargin=0.5*inch,
      topMargin=0.5*inch, bottomMargin=0.5*inch
    )
    styles = getSampleStyleSheet()
    story  = [
      Paragraph(f"Order {order} (Total items: {total})", styles['Title']),
      Spacer(1,0.2*inch)
    ]
    data = [['#','SKU','Qty','Customer']]
    for idx,i in enumerate(m_items,1):
        data.append([
          str(idx),
          Paragraph(i['goods_sn'], styles['BodyText']),
          i['quantity'],
          i['customer']
        ])
    tbl = Table(data, colWidths=[0.5*inch,2*inch,0.5*inch,4*inch])
    tbl.setStyle(TableStyle([
      ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),
      ('GRID',(0,0),(-1,-1),0.5,colors.grey)
    ]))
    story.append(tbl)
    doc.build(story)

def write_csv(items, customer, path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['sku','customer','quantity'])
        w.writerows([[it['goods_sn'], customer, it['quantity']] for it in items])

def write_merged_csv(m_items, path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['sku','customer','quantity'])
        w.writerows([[i['goods_sn'], i['customer'], i['quantity']] for i in m_items])
