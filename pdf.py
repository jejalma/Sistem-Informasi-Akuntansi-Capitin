from fpdf import FPDF

import config

TEAL = (15, 76, 92)


def _safe(value) -> str:
    return str(value).replace('\u2003', '  ').replace('\u00b7', '-').replace('\u2014', '-').replace('\u2013', '-').encode('latin-1', 'replace').decode('latin-1')


class _ReportPDF(FPDF):
    def __init__(self, title: str, subtitle: str, orientation: str):
        super().__init__(orientation=orientation, unit='mm', format='A4')
        self.report_title, self.report_subtitle = title, subtitle
        self.set_auto_page_break(True, 15)
        self.add_page()

    def header(self):
        self.set_font('Helvetica', 'B', 13)
        self.set_text_color(*TEAL)
        self.cell(0, 7, _safe(f'{config.APP_NAME} - {config.COMPANY_NAME}'), new_x='LMARGIN', new_y='NEXT')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(110)
        self.cell(0, 4, _safe(config.COMPANY_ADDRESS), new_x='LMARGIN', new_y='NEXT')
        self.set_draw_color(*TEAL)
        self.line(self.l_margin, self.get_y() + 2, self.w - self.r_margin, self.get_y() + 2)
        self.ln(5)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(25)
        self.cell(0, 6, _safe(self.report_title), new_x='LMARGIN', new_y='NEXT')
        self.set_font('Helvetica', '', 9)
        self.cell(0, 5, _safe(self.report_subtitle), new_x='LMARGIN', new_y='NEXT')
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(130)
        self.cell(0, 5, _safe(f'Halaman {self.page_no()} - dicetak dari Sistem Informasi Akuntansi {config.APP_NAME}'),
                  align='C')

    def fit(self, text: str, width: float) -> str:
        text = _safe(text)
        while text and self.get_string_width(text) > width - 2:
            text = text[:-2] + '.'
        return text


def table_pdf(title: str, subtitle: str, headers: list[str], rows: list[tuple[list, str]],
              widths: list[float], aligns: str, orientation: str = 'P') -> bytes:
    """rows: (cells, style) dengan style '' | 'bold' | 'section'. widths: proporsi kolom."""
    pdf = _ReportPDF(title, subtitle, orientation)
    col_w = [w / sum(widths) * pdf.epw for w in widths]

    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_fill_color(*TEAL)
    pdf.set_text_color(255)
    for h, w, a in zip(headers, col_w, aligns):
        pdf.cell(w, 7, pdf.fit(h, w), border=0, align=a, fill=True)
    pdf.ln()

    pdf.set_draw_color(225, 220, 210)
    for cells, style in rows:
        pdf.set_text_color(25)
        pdf.set_font('Helvetica', 'B' if style in ('bold', 'section') else '', 8)
        fill = style in ('bold', 'section')
        pdf.set_fill_color(240, 236, 226) if style == 'bold' else pdf.set_fill_color(226, 238, 238)
        for value, w, a in zip(cells, col_w, aligns):
            pdf.cell(w, 6, pdf.fit(value, w), border='B', align=a, fill=fill)
        pdf.ln()
    return bytes(pdf.output())
