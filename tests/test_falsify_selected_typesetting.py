import unittest
from types import SimpleNamespace
import pymupdf
from babeldoc.format.pdf.document_il import Box, PdfStyle, PdfParagraph, PdfCharacter, PdfParagraphComposition
from babeldoc.format.pdf.document_il.midend.typesetting import Typesetting, TypesettingUnit

class StrictSelectionTests(unittest.TestCase):
    def setUp(self):
        self.font = pymupdf.Font('helv')
        self.style = PdfStyle(font_id='base', font_size=10)
        self.ts = Typesetting.__new__(Typesetting)
        self.ts.is_cjk = False
        self.ts.font_mapper = SimpleNamespace(base_font=self.font)
        self.old = PdfParagraphComposition(pdf_character=PdfCharacter(char_unicode='old'))
        self.para = PdfParagraph(box=Box(x=10,y=50,x2=110,y2=90), pdf_paragraph_composition=[self.old])
        self.page = SimpleNamespace(cropbox=SimpleNamespace(box=Box(x=0,y=0,x2=120,y2=120)), pdf_paragraph=[self.para], pdf_character=[], pdf_figure=[], pdf_curve=[], pdf_form=[])
    def units(self, text):
        return [TypesettingUnit(unicode=c, font=self.font, font_size=10, style=self.style, xobj_id=-1) for c in text]
    def test_real_multiline_layout_at_original_size(self):
        result = self.ts.render_selected_paragraph_strict(self.para,self.page,self.units('alpha beta gamma delta epsilon zeta'))
        self.assertEqual(result['status'],'fitted')
        chars = [c.pdf_character for c in self.para.pdf_paragraph_composition]
        self.assertGreater(len({round(c.box.y, 2) for c in chars}),1)
        self.assertEqual({c.pdf_style.font_size for c in chars},{10})
        self.assertEqual(''.join(c.char_unicode for c in chars).replace(' ',''),'alphabetagammadeltaepsilonzeta')
    def test_dropped_leading_space_is_rejected(self):
        result = self.ts.render_selected_paragraph_strict(self.para, self.page, self.units(' leading'))
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(result['reason'], 'layout-dropped-units')
        self.assertEqual(self.para.pdf_paragraph_composition, [self.old])

    def test_expansion_requires_all_ink_check(self):
        self.para.box = Box(x=10, y=70, x2=110, y2=90)
        original = self.para.box
        result = self.ts.render_selected_paragraph_strict(
            self.para, self.page, self.units('One two three four five six seven eight nine ten'))
        self.assertEqual(result['reason'], 'expansion-unverified')
        self.assertIs(self.para.box, original)
        self.assertEqual(self.para.pdf_paragraph_composition, [self.old])

    def test_overflow_does_not_mutate_selection(self):
        original_box = self.para.box
        result = self.ts.render_selected_paragraph_strict(self.para,self.page,self.units('long text ' * 150))
        self.assertEqual(result['status'],'overflow')
        self.assertEqual(self.para.pdf_paragraph_composition,[self.old])
        self.assertIs(self.para.box,original_box)
        self.assertEqual(self.page.pdf_curve,[])
        self.assertEqual(self.page.pdf_form,[])
        self.assertEqual(result['scale'],1.0)

if __name__ == '__main__': unittest.main()
