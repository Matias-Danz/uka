import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import tm_browser_prices as tm

class TestTicketmaster(unittest.TestCase):
    SAMPLE = '''Artemas - LOVERCORE / GETTING UP TO NO GOOD Tour
    ne 22. 11. 2026 20:00 – SaSaZu, Praha
    Uplatňuje se transakční poplatek ve výši 30 Kč
    Všechny ceny
    Plocha 890,00 Kč za kus 0
    Balkon 1 190,00 Kč za kus 0
    VIP Package 2 309,00 Kč za kus 0
    Vstupenek v košíku: 0×0
    Jiný koncert 99,00 Kč za kus'''
    def test_realistic_page(self): self.assertEqual(tm.visible_ticket_prices(self.SAMPLE), (890,2309))
    def test_foreign_event_ignored(self): self.assertEqual(tm.visible_ticket_prices('jiný koncert 490,00 Kč za kus'), (None,None))
    def test_without_prices(self): self.assertEqual(tm.visible_ticket_prices('Všechny ceny Vstupenek v košíku: 0×0'), (None,None))
    def test_fee_not_price(self): self.assertEqual(tm.visible_ticket_prices('30 Kč poplatek Všechny ceny Vstupenek v košíku'), (None,None))
    def test_price_formats(self):
        for s,expected in [('890,00',890),('1 190,00',1190),('2 309,00',2309),('1.190,00',1190),('890.00',890)]:
            self.assertEqual(tm.to_czk(s),expected)
    def test_names(self):
        self.assertTrue(tm.belongs_to_event('Artemas - LOVERCORE / GETTING UP TO NO GOOD Tour', 'Artemas - LOVERCORE / GETTING UP TO NO GOOD Tour'))
        self.assertFalse(tm.belongs_to_event('Taylor Swift Tour', 'Artemas LOVERCORE Tour'))
    def test_safe_url(self):
        self.assertTrue(tm.sane_url('https://www.ticketmaster.cz/event/artemas-lovercore-getting-up-to-no-good-tour-vstupenky/463801089'))
        self.assertFalse(tm.sane_url('https://ticketmaster.cz.bad.example/event/foo'))
        self.assertFalse(tm.sane_url('http://www.ticketmaster.cz/event/foo'))
    def test_select(self):
        from datetime import datetime,timezone
        items=[{'id':'ticketmaster-ok', 'date':'2026-11-22', 'title':'Artemas', 'ticket_url':'https://www.ticketmaster.cz/event/a/123','price':None},
               {'id':'other-one','date':'2026-11-22','ticket_url':'https://www.ticketmaster.cz/event/a/123','price':None},
               {'id':'ticketmaster-manual','date':'2026-11-22','ticket_url':'https://www.ticketmaster.cz/event/a/456','price':690,'price_source':'Ruční cena'}]
        result=tm.select_events(items,datetime(2026,10,25,tzinfo=timezone.utc),5)
        self.assertEqual([r['id'] for r in result], ['ticketmaster-ok'])

if __name__=='__main__':unittest.main(verbosity=2)
