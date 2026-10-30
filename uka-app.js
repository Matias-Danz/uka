
  'use strict';
  const icon=(id,cls='')=>`<svg class="icon ${cls}" aria-hidden="true"><use href="#i-${id}"/></svg>`;
  const CATS=[['','Všechny'],['koncert','Koncerty'],['rave','Ravy'],['festival','Festivaly'],['opera','Opera'],['klub','Kluby'],['divadlo','Divadlo'],['jiné','Jiné']];
  const CAT_LABELS={koncert:'Koncert',rave:'Rave',festival:'Festival',opera:'Opera',klub:'Klub',divadlo:'Divadlo',jiné:'Jiné'};
  const CITIES={Praha:[50.0871,14.4211],Brno:[49.1951,16.6068],Ostrava:[49.8209,18.2625],Plzeň:[49.7475,13.3776],Olomouc:[49.5938,17.2509],Liberec:[50.769,15.0588],Pardubice:[50.0343,15.7812],České_Budějovice:[48.9757,14.4800]};
  const daysFromNow=n=>{const d=new Date();d.setDate(d.getDate()+n);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`};
  const REAL_EVENTS=[{"id":"uka-ost-dymytry-1016","title":"Dymytry & Arakain: Best Rock Tour 2026","artist":"Dymytry, Arakain, April Art","category":"koncert","venue":"Tatran","city":"Ostrava","address":"Cingrova 1627/10","date":"2026-10-16","time":"18:30","price":990,"price_max":null,"lat":49.8335502,"lng":18.2807156,"ticket_url":"https://goout.net/cs/dymytry-and-arakain-best-rock-tour-2026/szwcrdy/","source":"GoOut","verified_at":"2026-10-15","description":"Rockový večer se skupinami Dymytry a Arakain; čas odpovídá začátku programu."},{"id":"uka-pce-loudz-1016","title":"LOUDZ1 – Contemporary Tour","artist":"LOUDZ1","category":"koncert","venue":"Žlutý pes","city":"Pardubice","address":"Ke Koupališti 62","date":"2026-10-16","time":"21:00","price":350,"price_max":1000,"lat":50.0497294,"lng":15.7752025,"ticket_url":"https://www.eventlook.cz/udalosti/loudz-1-contemporary-tour-pardubice-rorlth/","source":"Eventlook","verified_at":"2026-10-15","description":"Koncertní zastávka v pardubickém klubu Žlutý pes.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/event-lookpardubice-xwjaqv.png","image_credit":"Eventlook / pořadatel"},{"id":"uka-brn-sergei-1016","title":"Sergei Barracuda – Album Tour 2026","artist":"Sergei Barracuda","category":"koncert","venue":"Two Faces","city":"Brno","address":"Biskupská 283","date":"2026-10-16","time":"21:00","price":449,"price_max":890,"lat":49.1921237,"lng":16.6059503,"ticket_url":"https://www.eventlook.cz/udalosti/sergei-barracuda-1610-brno-ohnidv/","source":"Eventlook","verified_at":"2026-10-15","description":"Brněnská zastávka nového album tour.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/3-15-xjsdut.jpg","image_credit":"Eventlook / pořadatel"},{"id":"uka-plz-white-1016","title":"White Girl Music – Plzeň","artist":"DJ line-up","category":"klub","venue":"Fénix Club","city":"Plzeň","address":"Prokopova 2796","date":"2026-10-16","time":"21:00","price":159,"price_max":179,"lat":49.7419057,"lng":13.3790509,"ticket_url":"https://www.eventlook.cz/udalosti/white-girl-music-zsrwuh/","source":"Eventlook","verified_at":"2026-10-15","description":"Tematická taneční párty s hity posledních let.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/white-girl-pc-uvczfh.png","image_credit":"Eventlook / pořadatel"},{"id":"uka-pra-oskar-1017","title":"IAM Oskar – Road to Hell","artist":"IAM Oskar, Teshime","category":"koncert","venue":"Rock Café","city":"Praha","address":"Národní 116","date":"2026-10-17","time":"19:30","price":290,"price_max":950,"lat":50.082011,"lng":14.418418,"ticket_url":"https://www.eventlook.cz/udalosti/iam-oskar-praha-rock-cafe-xowtbf/","source":"Eventlook","verified_at":"2026-10-15","description":"Klubová show s rapem a rockovými prvky. Začátek podle pořadatele 19:30.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/poset-road-to-hell-eventlook-ozfapv.png","image_credit":"Eventlook / pořadatel"},{"id":"o2-mejdan","title":"Český mejdan s Impulsem 2026","artist":"Mirai, Chinaski, Olympic, Mig 21, Lucie Vondráčková","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-10-17","time":"18:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/cesky-mejdan-s-impulsem-2026/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/06/imp-1322x623-o2.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-pra-caravan-1022","title":"Caravan Palace – Prague","artist":"Caravan Palace","category":"koncert","venue":"SaSaZu","city":"Praha","address":"Bubenské nábřeží 306/13","date":"2026-10-22","time":"19:00","price":890,"price_max":1890,"lat":50.0992604,"lng":14.4440222,"ticket_url":"https://www.eventlook.cz/udalosti/caravan-palace-prague-vraasa/","source":"Eventlook","verified_at":"2026-10-15","description":"Francouzská skupina propojující electro-swing, jazz a elektroniku.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/1920-x-1080-ryeybu.jpg","image_credit":"Eventlook / pořadatel"},{"id":"uka-plz-loudz-1023","title":"LOUDZ1 – Contemporary Tour","artist":"LOUDZ1","category":"koncert","venue":"WATT Music Club","city":"Plzeň","address":"Americká 14","date":"2026-10-23","time":"21:00","price":350,"price_max":1000,"lat":49.743523,"lng":13.3742604,"ticket_url":"https://www.eventlook.cz/udalosti/loudz-1-contemporary-tour-plzen-gsgeyf/","source":"Eventlook","verified_at":"2026-10-15","description":"Plzeňský koncert na Contemporary Tour.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/event-lookplzen-dgwzxq.png","image_credit":"Eventlook / pořadatel"},{"id":"uka-pra-golpe-1024","title":"Church Rave – Golpe All Night Long","artist":"Golpe / Broken Robot","category":"rave","venue":"Sacre Coeur","city":"Praha","address":"Holečkova 31","date":"2026-10-24","time":"22:00","price":690,"price_max":1590,"lat":50.0755,"lng":14.398,"ticket_url":"https://goout.net/cs/church-rave-golpe-all-night-long/szdcljy/","source":"GoOut","verified_at":"2026-10-15","description":"Noční hard-techno set v historickém prostoru Sacre Coeur."},{"id":"uka-brn-loudz-1024","title":"LOUDZ1 – Contemporary Tour","artist":"LOUDZ1","category":"koncert","venue":"Fléda","city":"Brno","address":"Štefánikova 266/24","date":"2026-10-24","time":"21:00","price":350,"price_max":1000,"lat":49.2098586,"lng":16.6033107,"ticket_url":"https://www.eventlook.cz/udalosti/loudz-1-contemporary-tour-brno-knfnur/","source":"Eventlook","verified_at":"2026-10-15","description":"Brněnská zastávka koncertního turné.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/event-lookbrno-ismdez.png","image_credit":"Eventlook / pořadatel"},{"id":"o2-hans26","title":"The World of Hans Zimmer – A New Dimension","artist":"The World of Hans Zimmer","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-10-25","time":"19:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/the-world-of-hans-zimmer-a-new-dimension/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2025/03/wohz-o2-1322x623-1-1322x621.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-pra-nemzzz-1027","title":"Nemzzz – Locked In Tour","artist":"Nemzzz","category":"koncert","venue":"Roxy","city":"Praha","address":"Dlouhá 33","date":"2026-10-27","time":"18:00","price":990,"price_max":1690,"lat":50.090689,"lng":14.425874,"ticket_url":"https://www.eventlook.cz/udalosti/nemzzz-locked-in-tour-xoalav/","source":"Eventlook","verified_at":"2026-10-15","description":"Britský rapper představí svou Locked In éru v pražském klubu Roxy.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/nemzzz-16-x-9-prague-whngzz.jpg","image_credit":"Eventlook / pořadatel"},{"id":"uka-plz-halloween-1027","title":"Studentský Halloween – Plzeň","artist":"DJ line-up","category":"klub","venue":"Bílej medvěd","city":"Plzeň","address":"Prokopova 336/30","date":"2026-10-27","time":"21:00","price":159,"price_max":179,"lat":49.7416584,"lng":13.3792319,"ticket_url":"https://www.eventlook.cz/udalosti/studentsky-halloween-plzen-ezbbqz/","source":"Eventlook","verified_at":"2026-10-15","description":"Kostýmová studentská párty se speciálními efekty.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/halloween-pc-plz-jwciqo.png","image_credit":"Eventlook / pořadatel"},{"id":"o2-don","title":"Don Toliver – Nitrous Tour","artist":"Don Toliver","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-10-30","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/don-toliver-nitrous-octane-world-tour-leg/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/06/1322x623-dontoliver.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-pra-komiks-1030","title":"Komiks Warehouse: Halloween Rave with Adiel","artist":"Adiel a hosté","category":"rave","venue":"Chuchle Arena Praha","city":"Praha","address":"Radotínská 69/34","date":"2026-10-30","time":"18:00","price":350,"price_max":490,"lat":50.00677,"lng":14.39122,"ticket_url":"https://goout.net/cs/komiks-warehouse-halloween-rave-with-adiel/szxewmy/","source":"GoOut","verified_at":"2026-10-15","description":"Halloweenská elektronická noc na několika pódiích."},{"id":"uka-pra-hunger-1031","title":"Hunger Games Rave","artist":"Litterbin, Anabanana, ŠatySVlečkou, Sarah Raw","category":"rave","venue":"ARCHA+","city":"Praha","address":"Na Poříčí 1047/26","date":"2026-10-31","time":"21:00","price":350,"price_max":700,"lat":50.0898,"lng":14.4344,"ticket_url":"https://goout.net/cs/hunger-games-rave/szmcumy/","source":"GoOut","verified_at":"2026-10-15","description":"Halloweenská tematická rave party s elektronickým line-upem."},{"id":"uka-pra-students-1031","title":"Největší studentský Halloween – Roxy","artist":"DJ line-up","category":"klub","venue":"Roxy","city":"Praha","address":"Dlouhá 33","date":"2026-10-31","time":"21:00","price":250,"price_max":650,"lat":50.090689,"lng":14.425874,"ticket_url":"https://www.eventlook.cz/udalosti/studentsky-halloween-roxy-wfrncy/","source":"Eventlook","verified_at":"2026-10-15","description":"Studentský Halloween s taneční hudbou a kostýmy.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/halloween-pc-sasa-unbsqp.png","image_credit":"Eventlook / pořadatel"},{"id":"uka-brn-reznik-1031","title":"Řezník × Haades – křest CD","artist":"Řezník, Haades, Strýc Nory, DJ Flux","category":"koncert","venue":"Artbar","city":"Brno","address":"Štefánikova 836/1","date":"2026-10-31","time":"20:00","price":400,"price_max":null,"lat":49.2078207,"lng":16.6037757,"ticket_url":"https://www.eventlook.cz/udalosti/reznik-x-haades-drogstars-brno-pdjzvy/","source":"Eventlook","verified_at":"2026-10-15","description":"Společná brněnská show a křest nové desky.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/dsfb-header-event-new-sytrmb.jpg","image_credit":"Eventlook / pořadatel"},{"id":"uka-brn-mig21-1104","title":"Mig 21","artist":"Mig 21","category":"koncert","venue":"Fléda","city":"Brno","address":"Štefánikova 266/24","date":"2026-11-04","time":"20:00","price":650,"price_max":null,"lat":49.2098586,"lng":16.6033107,"ticket_url":"https://goout.net/cs/mig-21/szsthjy/","source":"GoOut","verified_at":"2026-10-15","description":"První ze dvou listopadových koncertů Mig 21 na Flédě."},{"id":"uka-brn-mig21-1105","title":"Mig 21","artist":"Mig 21","category":"koncert","venue":"Fléda","city":"Brno","address":"Štefánikova 266/24","date":"2026-11-05","time":"20:00","price":650,"price_max":null,"lat":49.2098586,"lng":16.6033107,"ticket_url":"https://goout.net/cs/mig-21/szrthjy/","source":"GoOut","verified_at":"2026-10-15","description":"Druhý listopadový koncert Mig 21 v Brně."},{"id":"uka-pra-opera-1105","title":"Opera & Vivaldi – Four Seasons","artist":"Dvořák Symphony Orchestra Prague, Vanda Šípová a hosté","category":"opera","venue":"Obecní dům","city":"Praha","address":"Náměstí Republiky 1090/5","date":"2026-11-05","time":"20:00","price":900,"price_max":1450,"lat":50.0877,"lng":14.42772,"ticket_url":"https://goout.net/cs/opera-and-vivaldi-four-seasons/szelwmy/","source":"GoOut","verified_at":"2026-10-15","description":"Operní árie a Čtvero ročních dob A. Vivaldiho v historickém Obecním domě."},{"id":"uka-plz-rico-1106","title":"Hard Rico – Focus Tour","artist":"Hard Rico","category":"koncert","venue":"Bílej medvěd","city":"Plzeň","address":"Prokopova 336/30","date":"2026-11-06","time":"21:00","price":490,"price_max":1490,"lat":49.7416584,"lng":13.3792319,"ticket_url":"https://www.eventlook.cz/udalosti/hard-rico-focus-tour-plzen-uqusvw/","source":"Eventlook","verified_at":"2026-10-15","description":"Plzeňská zastávka rapového Focus Tour.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/hard-rico-focus-tour-fb-bilej-medved-etgdjh.jpeg","image_credit":"Eventlook / pořadatel"},{"id":"uka-lib-pondel-1106","title":"Pondělníci + Záviš","artist":"Pondělníci, Záviš","category":"koncert","venue":"Bunkr Music Club","city":"Liberec","address":"Tržní náměstí 876/11","date":"2026-11-06","time":"19:30","price":400,"price_max":null,"lat":50.774402,"lng":15.061395,"ticket_url":"https://goout.net/cs/pondelnici%2Bzavis/szvjkiy/","source":"GoOut","verified_at":"2026-10-15","description":"Koncertní večer v libereckém Bunkru."},{"id":"uka-pra-steve-1106","title":"Steve Sniff – OG Show (Přežil jsem)","artist":"Steve Sniff, Maštizmrd, DJ Kersh","category":"koncert","venue":"OX Club Prague","city":"Praha","address":"Francouzská 75/4","date":"2026-11-06","time":"19:00","price":369,"price_max":1799,"lat":50.0744873,"lng":14.4352169,"ticket_url":"https://www.eventlook.cz/udalosti/steve-sniff-og-show-prezil-jsem-clvqmr/","source":"Eventlook","verified_at":"2026-10-15","description":"Koncert a doprovodný program. V 19:00 začíná Meet & Greet; běžný vstup je později.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/img-3282-png-ssrpdj.png","image_credit":"Eventlook / pořadatel"},{"id":"uka-olm-fixa-1106","title":"Vypsaná fixa – Ideál Tour 2026","artist":"Vypsaná fixa","category":"koncert","venue":"Sklub","city":"Olomouc","address":"Třída 17. listopadu 43","date":"2026-11-06","time":"20:00","price":554,"price_max":null,"lat":49.594036,"lng":17.2623013,"ticket_url":"https://goout.net/cs/vypsana-fixa-ideal-tour-2026/szjirhy/","source":"GoOut","verified_at":"2026-10-15","description":"Vypsaná fixa představí album Ideál i starší oblíbené skladby."},{"id":"o2-kabat10","title":"Kabát – Turné 2026","artist":"Kabát","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-10","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/kabat-turne-2026/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2025/11/kabat-o2-1322x623-3.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-kabat11","title":"Kabát – Turné 2026","artist":"Kabát","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-11","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/kabat-turne-2026/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2025/11/kabat-o2-1322x623-3.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-pra-danz-1113","title":"Danz Hun – křest alba Víc","artist":"Danz Hun","category":"koncert","venue":"SaSaZu","city":"Praha","address":"Bubenské nábřeží 306/13","date":"2026-11-13","time":"20:00","price":490,"price_max":1390,"lat":50.0992604,"lng":14.4440222,"ticket_url":"https://www.eventlook.cz/udalosti/danz-hun-krest-alba-vic-zfzlnx/","source":"Eventlook","verified_at":"2026-10-15","description":"Koncert spojený se křtem deváté desky Danz Hun.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/sasazu-13-eventlook-swsens.png","image_credit":"Eventlook / pořadatel"},{"id":"o2-sima","title":"Sima v O2 areně","artist":"Sima","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-13","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/sima-v-o2-arene/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2025/11/x-sima-o2-1322x623-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-korn","title":"KoRn + Architects + Pixel Grip","artist":"KoRn, Architects, Pixel Grip","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-16","time":"19:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/korn/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/03/korn-1322x623-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-ost-jamaron-1120","title":"Jamaron – Něco zůstane Tour","artist":"Jamaron","category":"koncert","venue":"Barrák","city":"Ostrava","address":"Fügnerova 595/1","date":"2026-11-20","time":"20:00","price":450,"price_max":null,"lat":49.8538177,"lng":18.275662,"ticket_url":"https://goout.net/cs/jamaron-neco-zustane-tour-2026/szxgoiy/","source":"GoOut","verified_at":"2026-10-15","description":"Rockový koncert k novému albu Něco zůstane."},{"id":"o2-martina","title":"Martina Pártlová","artist":"Martina Pártlová","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-20","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/martina-partlova/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2025/11/1322x623.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-radio","title":"Radio Kiss Millennium Explosion","artist":"Radio Kiss a hosté","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-21","time":"19:00","price":1490,"price_max":2290,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/radio-kiss-millennium-explosion-live-show-2026/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/1080x1080-3-735ec86fd8df.jpg","image_credit":"O2 arena / pořadatel"},{"id":"o2-pitbull","title":"Pitbull – I’m Back!","artist":"Pitbull, Lil Jon","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-22","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/pitbull-im-back/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/03/1322x623-pitbull-2026-o2arena.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-prodigy","title":"The Prodigy – European Tour","artist":"The Prodigy","category":"rave","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-23","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/the-prodigy/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/04/prodigy-1322x623-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-brn-colorfactory-1125","title":"Colorfactory","artist":"Colorfactory","category":"koncert","venue":"Fléda","city":"Brno","address":"Štefánikova 266/24","date":"2026-11-25","time":"20:00","price":790,"price_max":null,"lat":49.2098586,"lng":16.6033107,"ticket_url":"https://goout.net/cs/colorfactory/szsqrmy/","source":"GoOut","verified_at":"2026-10-15","description":"Návrat výrazné kapely české alternativní scény 90. let."},{"id":"o2-sarah","title":"Sarah Brightman – A Winter Symphony","artist":"Sarah Brightman","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-26","time":"19:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/sarah-brightman-a-winter-symphony/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/1080x1080-sarah-brightman-2026-praha-o2-d6d856b7fd4c.jpg","image_credit":"O2 arena / pořadatel"},{"id":"uka-pce-dorian-1127","title":"Dorian & Lboy – Pardubice","artist":"Dorian, Lboy, MC Kenny","category":"koncert","venue":"Žlutý pes","city":"Pardubice","address":"Ke Koupališti 62","date":"2026-11-27","time":"21:00","price":399,"price_max":990,"lat":50.0497294,"lng":15.7752025,"ticket_url":"https://www.eventlook.cz/udalosti/dorian-lboy-pardubice-2711-mkzrcw/","source":"Eventlook","verified_at":"2026-10-15","description":"Společná show Dorian & Lboy s hostem MC Kenny.","image_url":"https://eventigo.s3-central.vshosting.cloud/production/event/3-13-tqhgep.jpg","image_credit":"Eventlook / pořadatel"},{"id":"o2-sound","title":"The Sound Chapter – Dimitri Vegas, KSHMR, MORTEN, R3HAB","artist":"Dimitri Vegas, KSHMR, MORTEN, R3HAB","category":"rave","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-27","time":"18:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/the-sound-chapter/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/08/1322-x-623.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-pce-fixa-1127","title":"Vypsaná fixa – Ideál Tour 2026","artist":"Vypsaná fixa","category":"koncert","venue":"ABC Klub","city":"Pardubice","address":"Štolbova 2665","date":"2026-11-27","time":"20:00","price":554,"price_max":null,"lat":50.0327608,"lng":15.7820822,"ticket_url":"https://goout.net/cs/vypsana-fixa-ideal-tour-2026/szyfqhy/","source":"GoOut","verified_at":"2026-10-15","description":"Pardubická zastávka turné k albu Ideál."},{"id":"o2-separ","title":"Separ – 40 Bday Party","artist":"Separ","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-11-28","time":"21:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/separ-40-bday-party/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/separ-o2-1322x623-v-poslednim-zaslani.jpg-22c6d89e1c7c.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-ost-hladik-1201","title":"Pocta Radimu Hladíkovi – Má hra Tour","artist":"Blue Effect, CBC Big Band a hosté","category":"koncert","venue":"Barrák","city":"Ostrava","address":"Fügnerova 595/1","date":"2026-12-01","time":"19:30","price":890,"price_max":null,"lat":49.8538177,"lng":18.275662,"ticket_url":"https://goout.net/cs/pocta-radimu-hladikovi-ma-hra-tour-2026/sztqkey/","source":"GoOut","verified_at":"2026-10-15","description":"Jazzrocková pocta Radimu Hladíkovi s projektem Nová syntéza."},{"id":"o2-calin4","title":"Calin & Viktor Sheen – Arena Tour","artist":"Calin, Viktor Sheen","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-12-04","time":"19:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/calin-viktor-sheen-arena-tour/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/arena-tour-2026-12-05-praha-03-1322x623px-compressed.jpg-0db998e3949a.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-calin5","title":"Calin & Viktor Sheen – Arena Tour","artist":"Calin, Viktor Sheen","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-12-05","time":"19:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/calin-viktor-sheen-arena-tour/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/arena-tour-2026-12-05-praha-03-1322x623px-compressed.jpg-0db998e3949a.webp","image_credit":"O2 arena / pořadatel"},{"id":"uka-lib-paulie-1205","title":"Paulie Garand & Kenny Rough – Addio Tour","artist":"Paulie Garand, Kenny Rough, Under My Pillow","category":"koncert","venue":"Club Warehouse","city":"Liberec","address":"Hanychovská 328/10","date":"2026-12-05","time":"21:00","price":426,"price_max":601,"lat":50.7586389,"lng":15.0439167,"ticket_url":"https://goout.net/cs/paulie-garand-and-kenny-rough%2Bunder-my-pillow-addio-tour-2026/szwpimy/","source":"GoOut","verified_at":"2026-10-15","description":"Klubové turné představí společnou tvorbu a nové album."},{"id":"o2-noname","title":"No Name 30","artist":"No Name","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-12-12","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/no-name-30/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/o2-nn30-2026-1322x623-1-1322x621.jpg-0e906b7986f7.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-bryan","title":"Bryan Adams – Roll With The Punches","artist":"Bryan Adams","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-12-13","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/bryan-adams-roll-with-the-punches/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/02/1322x623-bryanadams.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-drupi","title":"DRUPI","artist":"DRUPI","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-12-27","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/drupi/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Událost uvedená v oficiálním hudebním programu O2 areny. Aktuální cenu a vstupenky najdeš na webu haly.","image_url":"https://cdn.static-assets.cz/20261012-180702/drupi-o2-1080x1080-1.jpg-3522264507e5.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-silvestr","title":"MEGA SILVESTROVSKÉ PECKY","artist":"MEGA SILVESTROVSKÉ PECKY","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2026-12-31","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/filter/concerts/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Událost uvedená v oficiálním hudebním programu O2 areny. Aktuální cenu a vstupenky najdeš na webu haly.","image_url":"","image_credit":""},{"id":"o2-tublatanka","title":"Tublatanka, Alphaville, Argema","artist":"Tublatanka, Alphaville, Argema","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-01-30","time":"19:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/tublatanka-alphaville-argema/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/02/1322-x-623.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-ffdp","title":"Five Finger Death Punch – 20th Anniversary","artist":"Five Finger Death Punch","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-01-31","time":"19:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/five-finger-death-punch-20th-anniversary-world-tour/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/05/ffdp-2027-1322x623-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-slagr","title":"Srdce pro Šlágr – Velký galakoncert","artist":"Srdce pro Šlágr","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-02-14","time":"15:00","price":990,"price_max":9990,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/srdce-pro-slagr-velky-galakoncert-k-15-letum-slagru/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Událost uvedená v oficiálním hudebním programu O2 areny. Aktuální cenu a vstupenky najdeš na webu haly.","image_url":"https://cdn.static-assets.cz/20261012-180702/slagr-o2-01-1080x1080-final.jpg-95277894f954.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-electric","title":"Electric Callboy – Tanzneid World Tour","artist":"Electric Callboy","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-02-24","time":"19:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/electric-callboy-tanzneid-world-tour/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/09/o2a-electriccallboy27-1322x623px.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-queen","title":"Queen Relived Philharmonic","artist":"Queenie, Janáčkova filharmonie","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-02-26","time":"20:00","price":799,"price_max":2999,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/queen-relived-philharmonic-2027/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/05/queen-relived-praha-2027-1080x1080px.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-michael","title":"Michael Lives Forever","artist":"Rodrigo Teaser","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-02-27","time":"19:00","price":699,"price_max":2490,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/michael-lives-forever/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/mj-praha-1080x1080px.jpg-293164adf37d.webp","image_credit":"O2 arena / pořadatel"},{"id":"goout-cult-luna-2027","title":"Cult of Luna + Bruit ≤ + Youth Code","artist":"Cult of Luna, Bruit ≤, Youth Code","category":"koncert","venue":"ARCHA+","city":"Praha","address":"Na Poříčí 1047/26","date":"2027-03-13","time":"19:00","price":960,"lat":50.0898,"lng":14.4344,"ticket_url":"https://goout.net/cs/cult-of-luna%2Bbruit-%2Byouth-code/szifmmy/","source":"GoOut","verified_at":"2026-10-15","description":"Post-metal, post-rock a EBM v ARCHA+."},{"id":"o2-teddy","title":"Teddy Swims – The UGLY Tour","artist":"Teddy Swims","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-03-20","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/teddy-swims-the-ugly-tour/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/07/1322x623-teddyswims.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-hans27","title":"The World of Hans Zimmer – A New Dimension","artist":"The World of Hans Zimmer","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-04-16","time":"19:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/the-world-of-hans-zimmer-a-new-dimension-2027/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/03/wohz-o2-1322x623-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-sabaton","title":"Sabaton – The Legendary Tour Part 2","artist":"Sabaton","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-05-02","time":"19:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/sabaton-the-legendary-tour-part-2-europe-2027/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/06/o2a-sabaton27-1322x623px.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-andre","title":"André Rieu + Johann Strauss Orchestra","artist":"André Rieu","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-05-08","time":"19:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/andre-rieu-in-prague-2027-with-his-johann-strauss-orchestra/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/05/andre-rieu-o2-2027-1322x623-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-nedved14","title":"Nedvědi 27","artist":"Vojtěch Dyk, Jakub Prachař a hosté","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-05-14","time":"20:00","price":990,"price_max":2390,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/nedvedi-27/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/1080x1080-o2.jpg-f5b7ef0d6ca9.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-nedved15","title":"Nedvědi 27","artist":"Vojtěch Dyk, Jakub Prachař a hosté","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-05-15","time":"20:00","price":990,"price_max":2390,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/nedvedi-27/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/1080x1080-o2.jpg-f5b7ef0d6ca9.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-sombr","title":"sombr – You Are The Reason World Tour","artist":"sombr","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-05-19","time":"19:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/sombr/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/09/1322x623-sombr.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-greta","title":"Greta Van Fleet – Into The Beginning","artist":"Greta Van Fleet","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-05-22","time":"19:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/greta-van-fleet-into-the-beginning/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/gretavanfleet-1322x623-1.jpg-e44c90e0d09b.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-richard","title":"Richard Krajčo 50 – Narozeninový koncert","artist":"Richard Krajčo","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-05-29","time":"19:00","price":990,"price_max":4990,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/richard-krajco-50-narozeninovy-koncert/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/1080x1080-1.jpg-967f7fac2f15.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-rod","title":"Rod Stewart","artist":"Rod Stewart","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-06-24","time":"20:00","price":3364,"price_max":4308,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/rod-stewart-2027/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/rodstewart-1080x1080-1.jpg-883c8b043206.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-nickel","title":"Nickelback – Everything Under The Sun Tour","artist":"Nickelback, Don Broco","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-06-26","time":"18:30","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/nickelback-everything-under-the-sun-tour/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/10/nickelback-2027-1322x623-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-ben","title":"Ben Cristovao – Big Bang","artist":"Ben Cristovao","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-10-01","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/ben-cristovao-2027-big-bang/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/04/o2-fb-aplikace-1080x1080px.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-ben2","title":"Ben Cristovao – Big Bang 2","artist":"Ben Cristovao","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-10-02","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/ben-cristovao-2027-big-bang-2/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/10/o2-o2-fb-aplikace-1080x1080px-1.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-ilvolo","title":"Il Volo","artist":"Il Volo","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-10-18","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/il-volo-2027/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://cdn.static-assets.cz/20261012-180702/1080x1080-il-volo-2026-27-praha-o2.jpg-cc98c43471ca.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-horkyze","title":"Horkýže Slíže 35","artist":"Horkýže Slíže","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-11-26","time":"20:00","price":null,"price_max":null,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/horkyze-slize-35-nejvetsi-koncert-v-historii-kapely/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Potvrzený koncert v oficiálním programu O2 areny. Pro aktuální cenu a dostupnost vstupenek otevři zdroj pořadatele.","image_url":"https://www.o2arena.cz/wp-content/webp-express/webp-images/uploads/2026/09/1322x623-o2.jpg.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-tenori","title":"4 TENOŘI – 10 let na scéně","artist":"4 TENOŘI","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2027-12-18","time":"19:00","price":1490,"price_max":3190,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/4-tenori-10-let-na-scene/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Událost uvedená v oficiálním hudebním programu O2 areny. Aktuální cenu a vstupenky najdeš na webu haly.","image_url":"https://cdn.static-assets.cz/20261012-180702/4-tenori-o2-1080x1080-1.jpg-4c1bca543a51.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-maskova","title":"Tereza Mašková – Růžová O2 arena","artist":"Tereza Mašková","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2028-01-22","time":"20:00","price":999,"price_max":3999,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/tereza-maskova-ruzova-o2-arena/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Událost uvedená v oficiálním hudebním programu O2 areny. Aktuální cenu a vstupenky najdeš na webu haly.","image_url":"https://cdn.static-assets.cz/20261012-180702/tm-o2-arena-1080x1080-1.jpg-3798c388caa1.webp","image_credit":"O2 arena / pořadatel"},{"id":"o2-o5","title":"O5 a Radeček + Moravská filharmonie","artist":"O5 a Radeček + Moravská filharmonie","category":"koncert","venue":"O2 arena","city":"Praha","address":"Českomoravská 2345/17a, Praha 9","date":"2028-02-26","time":"19:00","price":1090,"price_max":2990,"lat":50.10475,"lng":14.49362,"ticket_url":"https://www.o2arena.cz/events/o5-a-radecek-moravska-filharmonie-olomouc-hoste/","source":"O2 arena – oficiální program","verified_at":"2026-10-15","description":"Událost uvedená v oficiálním hudebním programu O2 areny. Aktuální cenu a vstupenky najdeš na webu haly.","image_url":"https://cdn.static-assets.cz/20261012-180702/1080x1080-o2-o5ar.jpg-7fbfa493f6f9.webp","image_credit":"O2 arena / pořadatel"}];
  const STORE='uka-events-v1',FAVORITES='uka-favorites-v1'; // vlastní akce uživatele ponecháváme uložené
  function loadJson(key,def){try{const d=JSON.parse(localStorage.getItem(key));return Array.isArray(d)?d:def}catch{return def}}
  let added=loadJson(STORE,[]), favorites=new Set(loadJson(FAVORITES,[]));
  let page='akce',search='',category='',city='',when='all',favoriteOnly=false,mapCategory='',mapCity='',mapQuery='',radius=0,userCoords=null,onlyAvailable=false;
  let availabilityOverrides={};
  let adminOverrides={overrides:{},custom_events:[]};
  let mainMap=null,miniMap=null,mainTiles=null,miniTiles=null,mapMarkers=null,miniMarker=null,chosenCoords=null;
  let toastTimer=null,mapSearchTimer=null,pendingMapFocusId=null,mapReady=false;
  const el=id=>document.getElementById(id);
  const safeHttpUrl=value=>{try{const u=new URL(String(value||""));return u.protocol==="https:"&&u.username===""&&u.password===""?u.href:""}catch{return ""}};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money=p=>p===null||p===undefined||p===''?'Cena neuvedena':Number(p)===0?'Zdarma':`${Number(p).toLocaleString('cs-CZ')} Kč`;
  const priceLabel=e=>e.price==null?money(e.price):Number(e.price)===0?'Zdarma':e.price_note?`${money(e.price)} · ${esc(e.price_note)}`:(e.price_from===true||(e.price_max!=null&&e.price_max>e.price))?`od ${money(e.price)}`:money(e.price);

  // Stav dostupnosti musí mít zdroj a čas kontroly. Neznámý stav není vyprodáno.
  const AV_STATES={
    available:{label:'V prodeji',hint:'Vstupenky byly při poslední kontrole dostupné.'},
    low:{label:'Poslední místa',hint:'Omezenou dostupnost výslovně potvrdil prodejce nebo pořadatel.'},
    temporarily_sold_out:{label:'Aktuálně vyprodáno',hint:'Momentálně nejsou vstupenky k dispozici; další vlna může následovat.'},
    sold_out:{label:'Vyprodáno',hint:'Akce je dle ověřeného zdroje vyprodaná.'},
    unknown:{label:'Dostupnost neověřena',hint:'Dosud nemáme potvrzené informace o dostupnosti vstupenek.'}
  };
  // Bez další živé kontroly údaj časem zastará; zvlášť u „posledních míst“.
  const AV_TTL_MS={available:48*3600000,low:24*3600000,temporarily_sold_out:24*3600000,sold_out:72*3600000};
  function availabilityFor(event){
    const manual=adminOverrides.overrides?.[event.id]?.availability;
    const o=manual&&typeof manual==='object'?manual:availabilityOverrides[event.id];
    const raw=o&&typeof o==='object'?o:{status:event.ticket_status||event.availability_status,verified_at:event.ticket_status_verified_at||event.availability_verified_at,source:event.ticket_status_source||event.availability_source,expires_at:event.ticket_status_expires_at||event.availability_expires_at,note:event.ticket_status_note||event.availability_note};
    const state=typeof raw.status==='string'&&Object.hasOwn(AV_TTL_MS,raw.status)?raw.status:'unknown';
    const checked=Date.parse(raw.verified_at||'');
    const explicitExpiry=raw.expires_at?Date.parse(raw.expires_at):Infinity;
    const source=typeof raw.source==='string'?raw.source.trim():'';
    if(state==='unknown'||!source||!Number.isFinite(checked)||checked>Date.now()+300000)return {status:'unknown'};
    const expires=Math.min(checked+AV_TTL_MS[state],Number.isFinite(explicitExpiry)?explicitExpiry:Infinity);
    if(Date.now()>=expires)return {status:'unknown'};
    return {status:state,source,verified_at:raw.verified_at,note:typeof raw.note==='string'?raw.note.slice(0,200):''};
  }
  // Informace o době prodeje není důkazem dostupných vstupenek.
  function salesPhaseFor(event){
    const at=Date.parse(event.sales_phase_checked_at||'');
    if(!Number.isFinite(at)||at>Date.now()+300000||Date.now()-at>36*3600000)return null;
    const states={on_sale:['Prodej otevřen','Prodej vstupenek byl zahájen. Konkrétní volná místa nejsou potvrzena.'],upcoming:['Prodej zatím nezačal','Prodej podle dostupných údajů začne později.'],closed:['Prodej ukončen','Ukončení prodeje není potvrzením vyprodání.'],paused:['Změna / pozastavení','U prodejce ověř aktuální stav akce.']};
    const value=states[event.sales_phase];
    return value?{label:value[0],hint:value[1],checked:at,source:event.sales_phase_source||'oficiální zdroj'}:null;
  }
  function availabilityBadge(event){
    const info=availabilityFor(event),state=info.status;
    if(state==='unknown'){
      const sale=salesPhaseFor(event);
      if(sale)return `<span class="availability-badge av-phase" title="${esc(sale.hint)}">${esc(sale.label)}</span>`;
    }
    return `<span class="availability-badge av-${state}" title="${esc(AV_STATES[state].hint)}">${esc(AV_STATES[state].label)}</span>`;
  }
  function availabilityMeta(event){
    const a=availabilityFor(event);
    if(a.status==='unknown'){
      const sale=salesPhaseFor(event);
      if(sale)return `${esc(sale.label)} · ${esc(sale.hint)} Zdroj: ${esc(sale.source)} · kontrola ${esc(new Date(sale.checked).toLocaleString('cs-CZ'))}.`;
      return 'Před nákupem ověř stav u prodejce. Cena ani platný odkaz nepotvrzují dostupnost.';
    }
    return `${a.note?esc(a.note)+' · ':''}Zdroj: ${esc(a.source)} · zkontrolováno ${esc(new Date(a.verified_at).toLocaleString('cs-CZ'))}. Stav se může změnit.`;
  }
  function venueAvailability(group){
    const statuses=group.map(ev=>availabilityFor(ev).status);
    if(statuses.every(s=>s==='sold_out'))return 'sold_out';
    if(statuses.every(s=>s==='sold_out'||s==='temporarily_sold_out'))return 'temporarily_sold_out';
    if(statuses.every(s=>s==='available'||s==='low'))return statuses.includes('available')?'available':'low';
    return 'unknown'; // Smíšené a neověřené skupiny nesmí být mylně červené.
  }
  // Dostupnost je nyní součástí events.json a načítá se v refreshEvents().
  const eventSource=e=>e.source||'Vlastní událost';
  function fmtDate(d,mode='long'){const a=String(d).split('-').map(Number); const date=new Date(a[0],a[1]-1,a[2]);return Number.isNaN(date.getTime())?'Datum neuvedeno':date.toLocaleDateString('cs-CZ',mode==='long'?{day:'numeric',month:'long',year:'numeric'}:{day:'numeric',month:'short'});}
  const dateParts=d=>{const p=fmtDate(d,'short').split(' ');return [p[0]?.replace('.','')||'',(p[1]||'').replace('.','').toUpperCase()]};
  let officialEvents=REAL_EVENTS;
  let liveSyncLabel='Předinstalovaný výběr · nové akce se aktualizují po zveřejnění webu';
  // Ruční administrační opravy mají přednost před automaticky obnoveným events.json.
  // Oddělené ukládání zajišťuje, že hodinový import tyto opravy nesmaže.
  function allMergedEvents(){
    const edits=adminOverrides.overrides||{};
    const extra=Array.isArray(adminOverrides.custom_events)?adminOverrides.custom_events:[];
    return [...officialEvents,...added,...extra].map(event=>{
      const change=edits[event.id];
      if(change?.hidden)return null;
      return change?.fields?{...event,...change.fields}:event;
    }).filter(Boolean);
  }
  // Všechny edice KISS OR SLAP jsou klubové party, i když je zdroj mylně zařadí jako koncerty.
  function correctEventCategory(event){
    return /\bkiss (?:or |and )?slap\b/.test(searchNormalize(event.title)) && event.category!=='klub'
      ? {...event,category:'klub'} : event;
  }
  function getEvents(){const today=daysFromNow(0);return allMergedEvents().filter(e=>e.date>=today).map(correctEventCategory).sort((a,b)=>a.date.localeCompare(b.date));}
  // Administrační opravy jsou nyní součástí events.json.
  async function refreshEvents(){
    // On file:// the embedded data are used; a standalone HTML cannot itself run an hourly crawler.
    if(location.protocol==='file:')return;
    try{
      const response=await fetch('./events.json?updated='+Date.now(),{cache:'no-store'});
      if(!response.ok)throw new Error(String(response.status));
      const body=await response.json();
      if(!Array.isArray(body.events))throw new Error('Neplatná data');
      const validated=body.events.filter(e=>e&&typeof e.id==='string'&&typeof e.title==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(e.date)&&typeof e.city==='string'&&typeof e.venue==='string');
      if(!validated.length)throw new Error('Prázdný feed');
      officialEvents=validated;
      const adm=body.admin_overrides||{};
      adminOverrides={overrides:adm.overrides&&typeof adm.overrides==='object'&&!Array.isArray(adm.overrides)?adm.overrides:{},custom_events:Array.isArray(adm.custom_events)?adm.custom_events:[]};
      availabilityOverrides=body.availability_overrides?.overrides||{};
      liveSyncLabel=body.updated_at?'Aktualizováno: '+new Date(body.updated_at).toLocaleString('cs-CZ'):'Synchronizováno';
      if(page==='mapa'){renderMapListAndPins();}
      else if(page==='akce'||page==='oblibene')rerenderList();
      const status=el('syncStatus');if(status)status.textContent=liveSyncLabel;
    }catch(e){console.warn('UKA: live feed není k dispozici; použiji vloženou zálohu',e);}
  }
  // Chytré hledání v3.0 — našeptávač, začátky slov, vyhledávání i s překlepy.
  // Vše probíhá lokálně nad akcemi ve skutečné databázi, bez cizího API.
  const searchNormalize=value=>String(value??'').normalize('NFD')
    .replace(/[\u0300-\u036f]/g,'').toLowerCase()
    .replace(/[^a-z0-9]+/g,' ').trim();
  const searchWords=value=>searchNormalize(value).split(/\s+/).filter(Boolean);
  const searchTokenCache=new Map();
  function indexedWords(event){
    const raw=[event.title,event.artist,event.venue,event.city,event.address];
    const fingerprint=raw.join('\u0001');
    const cached=searchTokenCache.get(event.id);
    if(cached?.fingerprint===fingerprint)return cached.words;
    const words=[];
    const weights=[130,128,104,85,55];
    raw.forEach((value,i)=>{
      const found=String(value??'').match(/[\p{L}\p{N}]+/gu)||[];
      for(const display of found){
        const norm=searchNormalize(display);
        if(norm&&(!words.some(t=>t.norm===norm&&t.weight>=weights[i])))words.push({norm,display,weight:weights[i]});
      }
    });
    if(searchTokenCache.size>1200)searchTokenCache.clear();
    searchTokenCache.set(event.id,{fingerprint,words});
    return words;
  }
  // Omezená Damerau-Levenshteinova vzdálenost (umí i dvě prohozená písmena).
  function searchDistance(a,b,max){
    if(Math.abs(a.length-b.length)>max)return max+1;
    let prev2=null,prev=Array.from({length:b.length+1},(_,i)=>i);
    for(let i=1;i<=a.length;i++){
      const cur=[i];let min=cur[0];
      for(let j=1;j<=b.length;j++){
        let v=Math.min(prev[j]+1,cur[j-1]+1,prev[j-1]+(a[i-1]===b[j-1]?0:1));
        if(prev2&&i>1&&j>1&&a[i-1]===b[j-2]&&a[i-2]===b[j-1])
          v=Math.min(v,prev2[j-2]+1);
        cur[j]=v;min=Math.min(min,v);
      }
      if(min>max)return max+1;
      prev2=prev;prev=cur;
    }
    return prev[b.length];
  }
  function matchSearchWord(q,token,fuzzy){
    const w=token.norm;
    if(w===q)return {score:190+token.weight,corrected:token.display,kind:'exact'};
    if(w.startsWith(q))return {score:148+token.weight-Math.min(24,(w.length-q.length)*2),corrected:token.display,kind:'prefix'};
    if(q.length>=3&&w.includes(q))return {score:72+token.weight,corrected:token.display,kind:'contains'};
    if(!fuzzy||q.length<3)return null;
    const tol=q.length<7?1:q.length<12?2:3;
    if(Math.abs(w.length-q.length)<=tol){
      const distance=searchDistance(q,w,tol);
      if(distance<=tol)return {score:92+token.weight-distance*22,corrected:token.display,kind:'typo'};
    }
    // Neúplné slovo s překlepem: smae -> smack, halowe -> halloween.
    if(w.length>=q.length-1){
      let best=tol+1;
      for(let size=Math.max(1,q.length-tol);size<=Math.min(w.length,q.length+tol);size++){
        best=Math.min(best,searchDistance(q,w.slice(0,size),tol));
      }
      if(best<=tol)return {score:73+token.weight-best*22,corrected:token.display,kind:'typo-prefix'};
    }
    return null;
  }
  function rankSearchEvent(event,queryWords,fuzzy){
    if(!queryWords.length)return {score:0,corrected:[]};
    const tokens=indexedWords(event);let total=0;const corrected=[];
    for(const q of queryWords){
      let best=null;
      for(const token of tokens){
        const match=matchSearchWord(q,token,fuzzy);
        if(match&&(!best||match.score>best.score))best=match;
      }
      if(!best)return null;
      total+=best.score;corrected.push(best.corrected);
    }
    return {score:total,corrected};
  }
  function searchRankedEvents(events,query){
    const terms=searchWords(query);
    if(!terms.length)return events.map(event=>({event,score:0,corrected:[]}));
    const exact=events.map(event=>({event,match:rankSearchEvent(event,terms,false)}))
      .filter(row=>row.match);
    // Fuzzy výsledky pouze pokud nenašla žádná běžná shoda. Nehromadíme nerelevantní podobnosti.
    const matched=exact.length?exact:events.map(event=>({event,match:rankSearchEvent(event,terms,true)})).filter(row=>row.match);
    return matched.map(({event,match})=>({event,score:match.score,corrected:match.corrected}))
      .sort((a,b)=>b.score-a.score||a.event.date.localeCompare(b.event.date));
  }
  function searchSuggestionMarkup(query,events,where){
    const terms=searchWords(query);
    if(!terms.length||searchNormalize(query).length<2)return '';
    const ranked=searchRankedEvents(events,query);
    const options=new Map();
    for(const row of ranked.slice(0,100)){
      const display=row.corrected.join(' ');
      const normalized=searchNormalize(display);
      if(!display||normalized===terms.join(' ')||display.length>58)continue;
      const prev=options.get(normalized);
      if(prev){prev.count++;prev.score=Math.max(prev.score,row.score);}
      else options.set(normalized,{display,count:1,score:row.score});
    }
    const top=[...options.values()].sort((a,b)=>b.count-a.count||b.score-a.score).slice(0,4);
    if(!top.length)return '';
    return `<div class="smart-suggestions" role="group" aria-label="Návrhy vyhledávání">${top.map(option=>{
      const completed=terms.every((term,i)=>searchWords(option.display)[i]?.startsWith(term));
      return `<button type="button" class="smart-suggestion" data-search-correction="${where}" data-corrected="${esc(option.display)}"><span class="smart-suggestion-type">${completed?'Doplnit':'Myslel jsi'}</span><strong>${esc(option.display)}</strong><span class="smart-suggestion-arrow" aria-hidden="true">↗</span></button>`;
    }).join('')}</div>`;
  }
  function filterEvents({favoritesOnly=false,cat='',cityFilter='',query='',period='all',loc=null,maxRadius=0,availableOnly=onlyAvailable}={}){
    const now=daysFromNow(0);const dt=new Date();const end=new Date(dt.getFullYear(),dt.getMonth()+1,0);const monthEnd=`${end.getFullYear()}-${String(end.getMonth()+1).padStart(2,'0')}-${String(end.getDate()).padStart(2,'0')}`;
    const eligible=getEvents().filter(e=>{
      if(e.date<now||(favoritesOnly&&!favorites.has(e.id))||(cat&&e.category!==cat)||(cityFilter&&e.city!==cityFilter))return false;
      if(period==='week'&&e.date>daysFromNow(7))return false;
      if(period==='month'&&e.date>monthEnd)return false;
      if(period==='free'&&(e.price==null||Number(e.price)!==0))return false;
      if(availableOnly){const state=availabilityFor(e).status;if(!['available','low'].includes(state)&&!(state==='unknown'&&e.sales_phase==='on_sale'&&salesPhaseFor(e)))return false;}
      if(loc&&maxRadius>0&&distance(loc,[e.lat,e.lng])>maxRadius)return false;
      return true;
    });
    return searchRankedEvents(eligible,query).map(row=>row.event);
  }
  const datePill=e=>{const [day,month]=dateParts(e.date);return `<div class="poster-date"><strong>${esc(day)}</strong><small>${esc(month)}</small></div>`};
  function eventPoster(e,modal=false){
    const letter=(e.title.match(/[\p{L}]/u)||['U'])[0].toUpperCase();
    const image=safeHttpUrl(e.image_url);
    return `<div class="poster ${image?'has-image':''}" data-theme="${esc(e.category)}">${image?`<img class="poster-photo" src="${esc(image)}" alt="Plakát akce ${esc(e.title)}" loading="lazy" referrerpolicy="no-referrer">`:''}<span class="poster-symbol">${esc(letter)}.</span>${modal?'':datePill(e)}${!modal&&availabilityFor(e).status==='sold_out'?'<span class="poster-sold-ribbon">VYPRODÁNO</span>':''}${modal?'':`<button class="favorite ${favorites.has(e.id)?'active':''}" data-fav="${esc(e.id)}" aria-label="${favorites.has(e.id)?'Odebrat z oblíbených':'Uložit do oblíbených'}" title="Oblíbené">${icon('heart')}</button>`}</div>`;
  }
function compactAvailability(e){
  const info=availabilityFor(e);
  if(info.status==='unknown'&&!salesPhaseFor(e))return '';
  return availabilityBadge(e);
}
function meaningfulDescription(e){
  const d=String(e.description||'').trim();
  if(!d)return '';
  // Generic importer notices aren't part of an artist's event description.
  if(/^(Potvrzený koncert v oficiálním programu|Událost uvedená v oficiálním hudebním programu|Ověřená hudební událost na Eventlooku|Ověřená hudební událost|Vstupenky a aktuální dostupnost|Koncert uvedený v oficiálním programu)/i.test(d))return '';
  return d;
}
function card(e){
  const state=compactAvailability(e);
  return `<article class="event-card av-${availabilityFor(e).status}">
    ${eventPoster(e)}
    <div class="card-body">
      <div class="card-top"><span class="category">${esc(CAT_LABELS[e.category]||'Akce')}</span><span class="card-price">${priceLabel(e)}</span></div>
      <h3>${esc(e.title)}</h3>
      <div class="card-place">${icon('pin','sm')}<span>${esc(e.venue)} · ${esc(e.city)}</span></div>
      ${state?`<div class="availability-row">${state}</div>`:''}
      <div class="card-foot"><span>${e.time?icon('clock','sm')+' '+esc(e.time):fmtDate(e.date,'short')}</span><button type="button" class="text-link" data-detail="${esc(e.id)}" aria-label="Detail akce ${esc(e.title)}">Detail ${icon('arrow','sm')}</button></div>
    </div>
  </article>`;
}
function pageHome(){
  const events=filterEvents({favoritesOnly:favoriteOnly,cat:category,cityFilter:city,query:search,period:when});
  return `
    ${favoriteOnly?'':`<section class="hero"><div class="container hero-wrap"><div class="hero-copy">
      <div class="eyebrow">UKA / HUDBA KOLEM TEBE</div>
      <h1>Kam vyrazíš<br><span>za hudbou?</span></h1>
      <p class="hero-desc">Koncerty, kluby a festivaly. Najdi si svůj další večer.</p>
      <div class="hero-actions"><button class="btn btn-primary" data-jump="events">Prohlédnout akce ${icon('arrow','sm')}</button><button class="btn btn-outline" data-nav="mapa">${icon('pin','sm')} Mapa</button></div>
    </div><div class="hero-visual" aria-hidden="true"><div class="record-art"><span>UKA</span></div></div></div></section>`}
    <section id="events" class="container section">
      <div class="section-head"><div><h2>${favoriteOnly?'Uložené akce':'Objevuj akce'}</h2></div></div>
      <div class="toolbar"><label class="field-wrap">${icon('search')}<input id="searchInput" autocomplete="off" placeholder="Interpret, akce nebo místo" value="${esc(search)}" aria-label="Hledat akci"></label>
        <select id="cityFilter" class="select" aria-label="Město"><option value="">Všechna města</option>${['Praha','Brno','Ostrava','Plzeň','Olomouc','Liberec','Pardubice'].map(c=>`<option value="${c}" ${city===c?'selected':''}>${c}</option>`).join('')}</select>
        <select id="whenFilter" class="select" aria-label="Termín"><option value="all" ${when==='all'?'selected':''}>Kdykoliv</option><option value="week" ${when==='week'?'selected':''}>Do 7 dní</option><option value="month" ${when==='month'?'selected':''}>Tento měsíc</option><option value="free" ${when==='free'?'selected':''}>Zdarma</option></select>
        </div>
      <div id="searchSuggestion" aria-live="polite">${searchSuggestionMarkup(search,filterEvents({favoritesOnly:favoriteOnly,cat:category,cityFilter:city,period:when}),'list')}</div>
      <div class="filter-line"><div class="filter-pills">${CATS.map(([value,label])=>`<button class="pill ${category===value?'active':''}" data-category="${esc(value)}">${label}</button>`).join('')}</div><label class="filter-availability ${onlyAvailable?'is-active':''}" title="Jen akce s otevřeným prodejem nebo potvrzenou dostupností. Volná místa nejsou zaručena."><input id="homeAvailableOnly" type="checkbox" ${onlyAvailable?'checked':''}> V prodeji</label></div>
      <div class="results"><span>${events.length} akcí</span>${search||category||city||when!=='all'||onlyAvailable?'<button type="button" id="clearFilters" class="filter-reset">Vymazat filtry</button>':''}</div>
      <div id="eventCards" class="cards ${events.length?'':'hidden'}">${events.map(card).join('')}</div>
      <div id="searchEmpty" class="empty ${events.length?'hidden':''}"><div class="empty-icon">♫</div><h3>${search?'Nic jsme nenašli':'Zatím tady nic není'}</h3><p>Zkus upravit hledání nebo filtry.</p><button class="btn btn-primary" id="clearFiltersEmpty">Vymazat filtry</button></div>
    </section>`;
}
  function hasVerifiedCoords(e){return e.lat!==null&&e.lng!==null&&e.lat!==undefined&&e.lng!==undefined&&Number.isFinite(Number(e.lat))&&Number.isFinite(Number(e.lng))&&Number(e.lat)>48.3&&Number(e.lat)<51.2&&Number(e.lng)>12&&Number(e.lng)<19.2;}
  function mapEvents(){return filterEvents({cat:mapCategory,cityFilter:mapCity,query:mapQuery,loc:userCoords,maxRadius:radius}).filter(hasVerifiedCoords);}
  function mapPage(){const list=mapEvents();return `<div class="container"><div class="page-top"><div><h1 class="page-title">Mapa akcí</h1></div><button class="btn btn-outline btn-sm" id="locateMe">${icon('locate')} Moje poloha</button></div><div class="map-layout"><div id="mainMap" class="map-box"><div class="map-loading">${icon('pin')} Načítám mapu…</div></div><aside class="map-side"><div class="map-tools"><h3>${list.length} akcí na mapě</h3><div class="map-selects"><select class="select" id="mapCity"><option value="">Všechna města</option>${['Praha','Brno','Ostrava','Plzeň','Olomouc','Liberec','Pardubice'].map(c=>`<option ${mapCity===c?'selected':''}>${c}</option>`).join('')}</select><select class="select" id="mapCat">${CATS.map(([v,l])=>`<option value="${v}" ${mapCategory===v?'selected':''}>${l}</option>`).join('')}</select></div><label class="field-wrap map-search-field" for="mapSearch">${icon('search')}<input id="mapSearch" type="search" autocomplete="off" enterkeyhint="search" placeholder="Hledat koncert, interpreta, místo…" aria-label="Hledat akci na mapě" value="${esc(mapQuery)}"></label><div id="mapSuggestion" aria-live="polite">${searchSuggestionMarkup(mapQuery,filterEvents({cat:mapCategory,cityFilter:mapCity,loc:userCoords,maxRadius:radius}),'map')}</div><div class="map-av-wrap"><label class="filter-availability ${onlyAvailable?'is-active':''}"><input id="mapAvailableOnly" type="checkbox" ${onlyAvailable?'checked':''}> V prodeji</label></div>${userCoords?`<div class="radius-row"><button data-radius="0" class="pill ${radius===0?'active':''}">Vše</button>${[5,10,25,50,100].map(n=>`<button data-radius="${n}" class="pill ${radius===n?'active':''}">${n} km</button>`).join('')}</div>`:''}</div><div class="map-event-list">${list.length?list.map(e=>`<button class="map-event av-${availabilityFor(e).status}" data-focus="${esc(e.id)}"><span class="map-e-top"><span class="category">${esc(CAT_LABELS[e.category]||e.category)}</span><b>${priceLabel(e)}</b></span><strong>${esc(e.title)}</strong><small>${icon('pin','sm')} ${esc(e.city)} · ${fmtDate(e.date,'short')} · ${esc(e.time||'—')}${userCoords?' · '+Math.round(distance(userCoords,[e.lat,e.lng]))+' km':''}</small>${compactAvailability(e)?`<span class="availability-row">${compactAvailability(e)}</span>`:''}</button>`).join(''):'<div class="empty">Žádné akce ve výběru.</div>'}</div></aside></div></div>`;}
  function addPage(){return `<div class="form-shell"><h1>Přidat akci</h1><p class="form-intro">Přidané akce se prozatím ukládají jen do tvého prohlížeče.</p><form id="eventForm">
    <div class="form-card"><h2>Základní údaje</h2><div class="form-grid"><div class="form-group wide"><label for="eTitle">Název akce *</label><input id="eTitle" required maxlength="130" placeholder="Např. Páteční Techno Night"></div><div class="form-group"><label for="eArtist">Interpret / line-up</label><input id="eArtist" maxlength="130" placeholder="Kdo vystupuje"></div><div class="form-group"><label for="eCat">Kategorie</label><select id="eCat">${CATS.filter(([v])=>v).map(([v,l])=>`<option value="${v}">${l}</option>`).join('')}</select></div><div class="form-group wide"><label for="eDesc">Popis akce</label><textarea id="eDesc" maxlength="1200" placeholder="Co návštěvníci zažijí..."></textarea></div></div></div>
    <div class="form-card"><h2>Místo</h2><div class="form-grid"><div class="form-group"><label for="eVenue">Místo konání *</label><input id="eVenue" required maxlength="120" placeholder="Např. klub, hala, park"></div><div class="form-group"><label for="eCity">Město *</label><select required id="eCity">${Object.keys(CITIES).map(c=>`<option value="${c.replaceAll('_',' ')}">${c.replaceAll('_',' ')}</option>`).join('')}</select></div><div class="form-group wide"><label>Poloha na mapě</label><small>Kliknutím na mapu umísti značku. Jinak použijeme centrum města.</small><div id="formMap" class="form-map"></div><div class="form-status" id="coordsText">Vybrána poloha podle města: Praha.</div></div></div></div>
    <div class="form-card"><h2>Termín a vstupenky</h2><div class="form-grid"><div class="form-group"><label for="eDate">Datum *</label><input id="eDate" type="date" min="${daysFromNow(0)}" required value="${daysFromNow(7)}"></div><div class="form-group"><label for="eTime">Začátek</label><input id="eTime" type="time" value="20:00"></div><div class="form-group"><label for="ePrice">Cena od (Kč)</label><input id="ePrice" type="number" min="0" max="1000000" step="1" placeholder="Prázdné = neznámá"></div><div class="form-group"><label for="eTicket">Odkaz na vstupenky</label><input id="eTicket" type="url" placeholder="https://..."></div></div></div>
    <div class="form-actions"><span class="muted tiny">* Povinná pole</span><button class="btn btn-primary" type="submit">${icon('plus')} Uložit a zobrazit akci ${icon('arrow')}</button></div>
  </form></div>`;}
  function theme(){return document.documentElement.dataset.theme==='light'?'light':'dark';}
  function syncThemeButton(){let day=theme()==='light';el('themeIcon').setAttribute('href',day?'#i-moon':'#i-sun');el('themeText').textContent=day?'Denní režim':'Noční režim';el('themeToggle').setAttribute('aria-label',day?'Přepnout na noční režim':'Přepnout na denní režim');document.querySelector('meta[name="theme-color"]').content=day?'#f8f8f6':'#0b0c11';}
  const MAP_STYLES={light:'https://tiles.openfreemap.org/styles/liberty',dark:'https://tiles.openfreemap.org/styles/dark'};
  const mapStyle=()=>MAP_STYLES[theme()];
  // Mapu nikdy neschovávat pod závoj ani uměle nečekat na změnu stylu.
  function refreshMapStyles(){
    const styleURL=mapStyle();
    for(const map of [mainMap,miniMap]){
      if(!map)continue;
      try { map.setStyle(styleURL,{diff:true}); }
      catch(err) { console.warn('UKA: nepodařilo se změnit styl mapy',err); }
    }
  }
  let themeTransitionSerial=0;
  function setTheme(newTheme){
    if(!['light','dark'].includes(newTheme)||newTheme===theme())return;
    const root=document.documentElement;
    const session=++themeTransitionSerial;
    const reduceMotion=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const apply=()=>{
      root.dataset.theme=newTheme;
      try{localStorage.setItem('uka-theme',newTheme)}catch{}
      syncThemeButton();
      refreshMapStyles();
      // Offline náhradní mapa používá proměnné CSS, není nutné ji znovu vytvářet.
    };
    if(reduceMotion){apply();return;}
    if(typeof document.startViewTransition==='function'){
      root.classList.add('uka-theme-atomic');
      try{
        const transition=document.startViewTransition(apply);
        transition.finished.then(
          ()=>{if(session===themeTransitionSerial)root.classList.remove('uka-theme-atomic')},
          ()=>{if(session===themeTransitionSerial)root.classList.remove('uka-theme-atomic')}
        );
      }catch(err){root.classList.remove('uka-theme-atomic');apply();}
    }else{
      root.classList.add('uka-theme-css');
      // Prohlížeč nejprve zaregistruje přechod a až v dalším snímku změní barvy.
      requestAnimationFrame(()=>requestAnimationFrame(()=>{
        apply();setTimeout(()=>root.classList.remove('uka-theme-css'),300);
      }));
    }
  }
  function showToast(msg){const t=el('toast');t.textContent=msg;t.classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.classList.remove('show'),3200);}
  function render(){const current=(location.hash||'#akce').slice(1);page=['akce','mapa','oblibene','pridat'].includes(current)?current:'akce';favoriteOnly=page==='oblibene';closeModal(false);destroyMaps();document.querySelectorAll('[data-nav]').forEach(n=>n.classList.toggle('active',n.dataset.nav===page));el('app').innerHTML=page==='mapa'?mapPage():page==='pridat'?addPage():pageHome();window.scrollTo({top:0,behavior:'instant'});if(page==='mapa')setTimeout(initMainMap,30);if(page==='pridat')setTimeout(initFormMap,30);}
  function go(where){const to=['akce','mapa','oblibene','pridat'].includes(where)?where:'akce';if(location.hash===`#${to}`){render()}else location.hash=to;}
  function rerenderList(){const scroll=window.scrollY;const elem=el('searchInput');const start=elem?.selectionStart,end=elem?.selectionEnd;const focused=document.activeElement===elem;el('app').innerHTML=pageHome();if(focused){const input=el('searchInput');input.focus({preventScroll:true});input.setSelectionRange(Math.min(start??search.length,search.length),Math.min(end??search.length,search.length));}window.scrollTo(0,scroll);}
  function toggleFav(id){if(favorites.has(id))favorites.delete(id);else favorites.add(id);try{localStorage.setItem(FAVORITES,JSON.stringify([...favorites]))}catch{};showToast(favorites.has(id)?'Přidáno do oblíbených':'Odebráno z oblíbených');if(page==='mapa'){renderMapListAndPins()}else if(page!=='pridat')rerenderList();if(el('modalRoot').querySelector('.overlay'))showDetails(id);}
function showDetails(id){
  const e=getEvents().find(x=>x.id===id);if(!e)return;
  const fav=favorites.has(id),price=priceLabel(e),av=compactAvailability(e),desc=meaningfulDescription(e);
  const summary=[e.source?'Zdroj: '+esc(eventSource(e)):'Vlastní záznam',e.verified_at?'Ověřeno '+fmtDate(e.verified_at):''].filter(Boolean).join(' · ');
  el('modalRoot').innerHTML=`<div class="overlay" role="presentation" data-close="true"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="detailTitle">
    <div class="modal-art">${eventPoster(e,true)}<button class="modal-close" data-close="true" aria-label="Zavřít">${icon('cross')}</button></div>
    <div class="modal-main">
      <span class="category">${esc(CAT_LABELS[e.category]||e.category)}</span>
      <h2 id="detailTitle">${esc(e.title)}</h2>
      ${e.artist&&e.artist!==e.title?`<div class="modal-artist">${esc(e.artist)}</div>`:''}
      ${av?`<div class="detail-status">${av}</div>`:''}
      <div class="modal-info">
        <div class="info-item">${icon('calendar')}<div><small>Kdy</small><b>${fmtDate(e.date)}${e.time?' · '+esc(e.time):''}</b></div></div>
        <div class="info-item">${icon('pin')}<div><small>Kde</small><b>${esc(e.venue)} · ${esc(e.city)}</b></div></div>
        <div class="info-item">${icon('ticket')}<div><small>Cena</small><b>${price}${e.price_max!=null&&e.price_max>e.price?' – '+money(e.price_max):''}</b></div></div>
      </div>
      ${desc?`<p class="modal-desc">${esc(desc)}</p>`:''}
      <div class="modal-actions">${safeHttpUrl(e.ticket_url)?`<a class="btn btn-primary" href="${esc(safeHttpUrl(e.ticket_url))}" target="_blank" rel="noopener noreferrer">${icon('ticket')} Vstupenky / info ${icon('arrow','sm')}</a>`:`<button type="button" disabled class="btn btn-outline">Odkaz není k dispozici</button>`}
        <button class="btn btn-outline" data-fav="${esc(e.id)}">${icon('heart')} ${fav?'Uloženo':'Uložit'}</button>
        ${hasVerifiedCoords(e)?`<button class="btn btn-outline" data-map-event="${esc(e.id)}">${icon('pin')} Mapa</button>`:''}
      </div>
      <details class="event-fineprint"><summary>Informace o akci</summary><div class="event-fineprint-content"><p>${summary}</p>${e.address?`<p>Adresa: ${esc(e.address)}</p>`:''}<p>${availabilityMeta(e)}</p><p>Údaje se mohou změnit. Aktuální stav ověř u pořadatele.</p></div></details>
    </div>
  </div></div>`;
  document.body.style.overflow='hidden';
}
  function closeModal(clear=true){if(clear){el('modalRoot').innerHTML='';document.body.style.overflow='';}else{el('modalRoot').innerHTML='';document.body.style.overflow='';}}
  function distance(a,b){let toR=x=>x*Math.PI/180,dl=toR(b[0]-a[0]),dn=toR(b[1]-a[1]);let v=Math.sin(dl/2)**2+Math.cos(toR(a[0]))*Math.cos(toR(b[0]))*Math.sin(dn/2)**2;return 6371*2*Math.atan2(Math.sqrt(v),Math.sqrt(1-v));}
  function pinNode(user=false,status='unknown'){
    const node=document.createElement('div');node.className='uka-marker';
    node.innerHTML=`<div class="pin-bubble ${user?'user':'av-'+status}"><i></i></div>`;
    return node;
  }
  let mainMapTimer=null,miniMapTimer=null,offlineZoom=1;
  function destroyMaps(){
    clearTimeout(mainMapTimer);clearTimeout(miniMapTimer);clearTimeout(mapSearchTimer);
    if(mainMap){mainMap.remove();mainMap=null;}
    if(miniMap){miniMap.remove();miniMap=null;}
    mapMarkers=[];miniMarker=null;chosenCoords=null;mapReady=false;
  }
  // Pokud CDN nebo připojení selže, karta ukáže schematickou ČR a klikatelné akce.
  // Není to náhrada detailních mapových podkladů: uživatel je o omezení informován.
  function showFallbackMap(id,form=false){
    const target=el(id);if(!target)return;
    const positions={Praha:[50.0871,14.4211],Brno:[49.1951,16.6068],Ostrava:[49.8209,18.2625],Plzeň:[49.7475,13.3776],Olomouc:[49.5938,17.2509],Liberec:[50.769,15.0588],Pardubice:[50.0343,15.7812]};
    const project=(lat,lng)=>[Math.round((lng-12.05)/(18.93-12.05)*820+35),Math.round((51.1-lat)/(51.1-48.45)*400+64)];
    const cities=Object.entries(positions).map(([label,[la,lo]])=>{const [x,y]=project(la,lo);return `<g><circle cx="${x}" cy="${y}" r="5" fill="var(--muted)"/><text x="${x+12}" y="${y-8}" font-size="16" font-weight="700" fill="var(--text)">${esc(label)}</text></g>`}).join('');
    const source=form?[]:mapEvents();
    const dots=source.map(ev=>{
      if(!Number.isFinite(Number(ev.lat))||!Number.isFinite(Number(ev.lng)))return '';
      const [x,y]=project(Number(ev.lat),Number(ev.lng));
      return `<g class="fallback-dot" data-detail="${esc(ev.id)}" tabindex="0" role="button" aria-label="Detail: ${esc(ev.title)}"><circle class="fallback-disc" cx="${x}" cy="${y}" r="10" stroke="var(--bg)" stroke-width="3" fill="${({available:'#24be74',low:'#eea23a',temporarily_sold_out:'#ed8541',sold_out:'#ec334e',unknown:'var(--gold)'})[availabilityFor(ev).status]}"/><circle cx="${x}" cy="${y}" r="2.5" fill="var(--bg)"/></g>`;
    }).join('');
    target.innerHTML=`<div class="fallback-map"><p>Detailní mapu se nepodařilo načíst. Zobrazuji orientační mapu ČR s akcemi. Pro ulice a přesné přiblížení je potřeba přístup k mapovým podkladům.</p><svg class="schematic" viewBox="0 0 900 540" role="img" aria-label="Orientační mapa České republiky s hudebními akcemi"><defs><pattern id="geo-grid-${id}" width="36" height="36" patternUnits="userSpaceOnUse"><path d="M 36 0 L 0 0 0 36" fill="none" stroke="var(--stroke)" stroke-width="1"/></pattern></defs><rect width="900" height="540" fill="var(--tile-placeholder)"/><rect width="900" height="540" fill="url(#geo-grid-${id})"/><path d="M70 135 L177 88 L283 92 L362 46 L485 95 L550 53 L676 113 L790 111 L855 188 L825 285 L776 338 L808 422 L698 459 L595 439 L506 485 L383 445 L296 465 L182 411 L87 370 L46 270 Z" fill="var(--surface2)" stroke="var(--stroke)" stroke-width="5" stroke-linejoin="round"/><path d="M120 280 Q280 220 406 278 T789 256 M186 380 Q380 330 527 362 T728 350 M300 112 Q380 250 470 320 T607 435" fill="none" stroke="var(--muted)" stroke-width="5" opacity=".34" stroke-linecap="round"/>${cities}${dots}</svg><div class="fallback-actions"><button type="button" data-offline-zoom="1" title="Oddálit">−</button><button type="button" data-offline-zoom="-1" title="Přiblížit">+</button></div><span class="fallback-badge">Orientační náhled · nejedná se o podrobnou mapu</span></div>`;
    offlineZoom=1;
  }
  function initMainMap(){
    const target=el('mainMap');if(!target)return;
    if(typeof maplibregl==='undefined'){showFallbackMap('mainMap');if(pendingMapFocusId){const id=pendingMapFocusId;pendingMapFocusId=null;showDetails(id);}return;}
    target.innerHTML='';
    try{
      mainMap=new maplibregl.Map({container:target,style:mapStyle(),center:userCoords?[userCoords[1],userCoords[0]]:[15.45,49.9],zoom:userCoords?11:7,maxZoom:22,minZoom:4,attributionControl:false,interactive:true,dragPan:true,scrollZoom:true,doubleClickZoom:true,touchZoomRotate:true});
      mainMap.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
      mainMap.addControl(new maplibregl.AttributionControl({compact:false}),'bottom-right');
      mainMap.on('load',()=>{
         mapReady=true;
         clearTimeout(mainMapTimer);
         renderMapListAndPins(false);
         if(pendingMapFocusId){const id=pendingMapFocusId;pendingMapFocusId=null;focusMapEvent(id);}
       });
       // Při ručním přetažení přerušit automatický přelet; kolečko myši musí zůstat pod kontrolou MapLibre.
       target.addEventListener('pointerdown',()=>mainMap?.stop(),{passive:true});
      mainMap.on('error',e=>{if(e.error)console.warn('Mapový podklad:',e.error.message||e.error)});
      mainMapTimer=setTimeout(()=>{if(mainMap&& !mainMap.loaded()){mainMap.remove();mainMap=null;mapMarkers=[];showFallbackMap('mainMap');}},12000);
      renderMapListAndPins(false);
    }catch(err){console.warn('UKA mapa:',err);if(mainMap){mainMap.remove();mainMap=null;}showFallbackMap('mainMap');}
  }
  function renderMapListAndPins(updateHtml=true){
    if(page!=='mapa')return;
    const visible=mapEvents();
    if(updateHtml){
      const temp=document.createElement('div');temp.innerHTML=mapPage();
      const newSide=temp.querySelector('.map-side'),oldSide=document.querySelector('.map-side');
      if(newSide&&oldSide){
         if(updateHtml==='results'){
           const newList=newSide.querySelector('.map-event-list');
           const oldList=oldSide.querySelector('.map-event-list');
           if(newList&&oldList){oldList.replaceWith(newList);}
           const mapHint=oldSide.querySelector('#mapSuggestion');const freshHint=newSide.querySelector('#mapSuggestion');
           if(mapHint&&freshHint)mapHint.innerHTML=freshHint.innerHTML;
           const count=oldSide.querySelector('.map-tools h3');
           if(count)count.textContent=`${visible.length} akcí na mapě`;
         }else oldSide.replaceWith(newSide);
       }
    }
    if(!mainMap){if(el('mainMap')?.querySelector('.fallback-map'))showFallbackMap('mainMap');return;}
    (mapMarkers||[]).forEach(m=>m.remove());mapMarkers=[];
    // Jedna značka pro stejné místo. Kliknutí nabídne všechny koncerty v daném klubu.
    const byVenue=new Map();
    for(const ev of visible){
      if(!Number.isFinite(Number(ev.lat))||!Number.isFinite(Number(ev.lng)))continue;
      const key=[Number(ev.lat).toFixed(5),Number(ev.lng).toFixed(5)].join(',');
      if(!byVenue.has(key))byVenue.set(key,[]);
      byVenue.get(key).push(ev);
    }
    byVenue.forEach(group=>{
      const ev=group[0];
      const markerEl=pinNode(false,venueAvailability(group));
      if(group.length>1){
        markerEl.classList.add('uka-cluster');
        const count=document.createElement('span');count.className='uka-pin-count';count.textContent=String(group.length);markerEl.append(count);
      }
      const items=group.map(item=>`<button type="button" class="uka-popup-event av-${availabilityFor(item).status}" data-detail="${esc(item.id)}"><b>${esc(item.title)}</b><small>${fmtDate(item.date,'short')} · ${esc(item.time||'—')} · ${priceLabel(item)}</small>${availabilityBadge(item)}</button>`).join('');
      const popup=`<div class="uka-popup"><strong>${esc(ev.venue)} · ${esc(ev.city)}</strong><div class="muted tiny">${group.length} ${group.length===1?'akce':'akcí'} na tomto místě</div>${items}</div>`;
      const marker=new maplibregl.Marker({element:markerEl}).setLngLat([Number(ev.lng),Number(ev.lat)]).setPopup(new maplibregl.Popup({offset:23,maxWidth:'300px'}).setHTML(popup)).addTo(mainMap);
      marker.ukaEventIds=group.map(item=>item.id);
      mapMarkers.push(marker);
    });
    if(userCoords){mapMarkers.push(new maplibregl.Marker({element:pinNode(true)}).setLngLat([userCoords[1],userCoords[0]]).setPopup(new maplibregl.Popup().setText('Tvoje poloha')).addTo(mainMap));}
  }
  function focusMapEvent(id){
    const ev=getEvents().find(x=>x.id===id);if(!ev)return;
    // If the map is still loading, focus only when the tiles and markers are ready.
    if(!mainMap){
      if(el('mainMap')?.querySelector('.fallback-map')){pendingMapFocusId=null;showDetails(id);return;}
      pendingMapFocusId=id;return;
    }
    if(!mapReady){pendingMapFocusId=id;return;}
    const lat=Number(ev.lat),lng=Number(ev.lng);
    if(!hasVerifiedCoords(ev)){showDetails(id);return;}
    // Enable all gestures: navigating from Objevovat must never lock the map.
    mainMap.dragPan.enable();
    mainMap.scrollZoom.enable();
    mainMap.doubleClickZoom.enable();
    mainMap.touchZoomRotate.enable();
    const marker=(mapMarkers||[]).find(m=>m.ukaEventIds?.includes(id));
    mainMap.stop(); // cancel any previous automatic navigation
    mainMap.easeTo({center:[lng,lat],zoom:16,duration:650,essential:true});
    if(marker){
      mainMap.once('moveend',()=>{
        if(!mainMap||!marker.getPopup())return;
        const popup=marker.getPopup();
        if(!popup.isOpen())marker.togglePopup();
        const root=popup.getElement();
        root?.querySelectorAll('.uka-popup-event').forEach(b=>b.classList.toggle('is-target',b.dataset.detail===id));
        const selected=root?.querySelector('.uka-popup-event.is-target');
        if(selected){const scrollArea=selected.closest('.uka-popup');if(scrollArea){scrollArea.scrollTop=selected.offsetTop-scrollArea.offsetTop;}}
      });
    }
  }
  function locate(){
    if(!navigator.geolocation){showToast('Polohu prohlížeč nepodporuje.');return;}
    showToast('Zjišťuji polohu…');
    navigator.geolocation.getCurrentPosition(pos=>{
      userCoords=[pos.coords.latitude,pos.coords.longitude];radius=25;
      renderMapListAndPins(true);if(mainMap)mainMap.flyTo({center:[userCoords[1],userCoords[0]],zoom:11});
      showToast('Poloha nalezena. Zobrazujeme akce do 25 km.');
    },()=>showToast('Polohu se nepodařilo získat. Povol přístup, případně použij filtr města.'),{enableHighAccuracy:false,timeout:12000});
  }
  function initFormMap(){
    const target=el('formMap');if(!target)return;
    chosenCoords=[...CITIES.Praha];
    if(typeof maplibregl==='undefined'){showFallbackMap('formMap',true);return;}
    target.innerHTML='';
    try{
      miniMap=new maplibregl.Map({container:target,style:mapStyle(),center:[chosenCoords[1],chosenCoords[0]],zoom:12,maxZoom:22,attributionControl:false});
      miniMap.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
      miniMap.addControl(new maplibregl.AttributionControl({compact:true}),'bottom-right');
      miniMapTimer=setTimeout(()=>{if(miniMap&&!miniMap.loaded()){miniMap.remove();miniMap=null;showFallbackMap('formMap',true);}},12000);
      miniMap.on('load',()=>clearTimeout(miniMapTimer));
      miniMarker=new maplibregl.Marker({element:pinNode(),draggable:true}).setLngLat([chosenCoords[1],chosenCoords[0]]).addTo(miniMap);
      miniMap.on('click',e=>{chosenCoords=[e.lngLat.lat,e.lngLat.lng];miniMarker.setLngLat(e.lngLat);updateCoordsLabel();});
      miniMarker.on('dragend',()=>{const p=miniMarker.getLngLat();chosenCoords=[p.lat,p.lng];updateCoordsLabel();});
    }catch(err){console.warn('UKA výběr polohy:',err);if(miniMap){miniMap.remove();miniMap=null;}showFallbackMap('formMap',true);}
  }
  function updateCoordsLabel(){if(!el('coordsText')||!chosenCoords)return;el('coordsText').textContent=`Vybraná poloha: ${chosenCoords[0].toFixed(5)}, ${chosenCoords[1].toFixed(5)}. (Bod můžeš na mapě přetáhnout.)`;}
  function updateFormCity(){
    const c=el('eCity').value.replaceAll(' ','_');chosenCoords=[...(CITIES[c]||CITIES.Praha)];
    if(miniMap){miniMap.flyTo({center:[chosenCoords[1],chosenCoords[0]],zoom:12});miniMarker.setLngLat([chosenCoords[1],chosenCoords[0]]);}
    el('coordsText').textContent=`Vybrána poloha podle města: ${el('eCity').value}. Klikni na mapu pro přesnější místo.`;
  }
  function submitEvent(){const f=id=>el(id)?.value?.trim()||'';const title=f('eTitle'),venue=f('eVenue'),cityInput=f('eCity'),date=f('eDate');if(!title||!venue||!cityInput||!date||date<daysFromNow(0)){showToast('Vyplň název, místo, město a budoucí datum.');return;}let url=f('eTicket');if(url){try{const u=new URL(url);if(!safeHttpUrl(url))throw Error();}catch{showToast('Odkaz na vstupenky musí začínat https://');return;}}const key=cityInput.replaceAll(' ','_');const pos=chosenCoords||CITIES[key]||CITIES.Praha;const priceVal=f('ePrice');const e={id:'local-'+Date.now()+'-'+Math.random().toString(36).slice(2,8),title,artist:f('eArtist'),category:f('eCat'),venue,city:cityInput,date,time:f('eTime'),price:priceVal===''?null:Number(priceVal),ticket_url:url,description:f('eDesc'),lat:pos[0],lng:pos[1]};added.push(e);try{localStorage.setItem(STORE,JSON.stringify(added))}catch{showToast('Prohlížeč nepovoluje lokální úložiště; akce bude jen dočasná.')}category='';city='';when='all';search='';showToast('Akce přidána! Najdeš ji v přehledu i na mapě.');go('akce');}
  document.addEventListener('click',e=>{
    const oz=e.target.closest('[data-offline-zoom]');if(oz){offlineZoom=Math.max(1,Math.min(5,offlineZoom-Number(oz.dataset.offlineZoom)*.45));const svg=oz.closest('.fallback-map')?.querySelector('.schematic');if(svg)svg.style.transform=`scale(${offlineZoom})`;return;}
    const n=e.target.closest('[data-nav]');if(n){e.preventDefault();if(n.classList.contains('brand')){search='';city='';when='all';category='';}go(n.dataset.nav);return;}
    const suggestion=e.target.closest('[data-search-correction]');
    if(suggestion){
      if(suggestion.dataset.searchCorrection==='map'){
        mapQuery=suggestion.dataset.corrected;const input=el('mapSearch');if(input)input.value=mapQuery;
        renderMapListAndPins('results');
      }else{search=suggestion.dataset.corrected;rerenderList();}
      return;
    }
    const c=e.target.closest('[data-category]');if(c){category=c.dataset.category;rerenderList();return;}
    const f=e.target.closest('[data-fav]');if(f){e.preventDefault();e.stopPropagation();toggleFav(f.dataset.fav);return;}
    const d=e.target.closest('[data-detail]');if(d){showDetails(d.dataset.detail);return;}
    const close=e.target.closest('[data-close]');if(close&&(e.target===close||e.target.closest('button[data-close]'))){closeModal();return;}
    const jump=e.target.closest('[data-jump]');if(jump){el(jump.dataset.jump)?.scrollIntoView({behavior:'smooth'});return;}
    if(e.target.closest('#clearFilters, #clearFiltersEmpty')){search='';city='';when='all';category='';onlyAvailable=false;rerenderList();return;}
    if(e.target.closest('#locateMe')){locate();return;}
    const r=e.target.closest('[data-radius]');if(r){radius=Number(r.dataset.radius);renderMapListAndPins();return;}
    const focus=e.target.closest('[data-focus]');if(focus){focusMapEvent(focus.dataset.focus);return;}
    const mapEvent=e.target.closest('[data-map-event]');if(mapEvent){const id=mapEvent.dataset.mapEvent;closeModal();mapCategory='';mapCity='';mapQuery='';radius=0;pendingMapFocusId=id;go('mapa');return;}
  });
  document.addEventListener('input',e=>{
     if(e.target.id==='mapSearch'){
       mapQuery=e.target.value;
       clearTimeout(mapSearchTimer);
       mapSearchTimer=setTimeout(()=>{if(page==='mapa')renderMapListAndPins('results');},100);
       return;
     }
     if(e.target.id==='searchInput'){
       search=e.target.value;
       const list=filterEvents({favoritesOnly:favoriteOnly,cat:category,cityFilter:city,query:search,period:when});
       const cards=el('eventCards');
       if(cards){cards.innerHTML=list.map(card).join('');cards.style.display=list.length?'grid':'none';}
       const empty=el('searchEmpty');
       if(empty){empty.style.display=list.length?'none':'block';const heading=empty.querySelector('h3');if(heading)heading.textContent=search?'Nic jsme nenašli':'Zatím tady nic není';}
       const counter=document.querySelector('.results span');
       if(counter)counter.textContent=`${list.length} akcí`;
       const resultsRow=document.querySelector('.results');
       if(resultsRow){
         const active=!!(search||category||city||when!=='all'||onlyAvailable);
         const reset=resultsRow.querySelector('#clearFilters');
         if(active&&!reset)resultsRow.insertAdjacentHTML('beforeend','<button type="button" id="clearFilters" class="filter-reset">Vymazat filtry</button>');
         if(!active&&reset)reset.remove();
       }
       const hint=el('searchSuggestion');
       if(hint)hint.innerHTML=searchSuggestionMarkup(search,filterEvents({favoritesOnly:favoriteOnly,cat:category,cityFilter:city,period:when}),'list');
     }
  });
  document.addEventListener('change',e=>{if(e.target.id==='homeAvailableOnly'||e.target.id==='mapAvailableOnly'){onlyAvailable=!!e.target.checked;if(page==='mapa')renderMapListAndPins();else rerenderList();return;}if(e.target.id==='cityFilter'){city=e.target.value;rerenderList()}if(e.target.id==='whenFilter'){when=e.target.value;rerenderList()}if(e.target.id==='mapCity'){mapCity=e.target.value;renderMapListAndPins()}if(e.target.id==='mapCat'){mapCategory=e.target.value;renderMapListAndPins()}if(e.target.id==='eCity')updateFormCity();});
  document.addEventListener('submit',e=>{if(e.target.id==='eventForm'){e.preventDefault();submitEvent();}});
  document.addEventListener('keydown',e=>{
     if(e.target.id==='mapSearch'&&e.key==='Enter'){
       e.preventDefault();
       clearTimeout(mapSearchTimer);
       renderMapListAndPins('results');
       const first=mapEvents()[0];if(first)focusMapEvent(first.id);
       return;
     }
     if(e.key==='Escape')closeModal();if((e.key==='Enter'||e.key===' ')&&e.target.matches('.fallback-dot[data-detail]')){e.preventDefault();showDetails(e.target.dataset.detail);}});
  el('themeToggle').addEventListener('click',()=>setTheme(theme()==='dark'?'light':'dark'));
  window.addEventListener('hashchange',render);
  syncThemeButton();render();refreshEvents();
  // Refresh the published JSON while tab stays open, independently of background crawler.
  setInterval(refreshEvents,15*60*1000);
  
  document.addEventListener('error',event=>{const img=event.target;if(!(img instanceof HTMLImageElement)||!img.classList.contains('poster-photo'))return;const parent=img.parentElement;parent?.querySelector('.photo-credit')?.remove();img.remove();parent?.classList.remove('has-image');},true);

