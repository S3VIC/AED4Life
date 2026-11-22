import csv,json,sys,datetime
src,out=sys.argv[1],sys.argv[2]
today=datetime.date(2026,11,21)
H=['id_aed','nazwa_obiektu','lat','lon','miejscowosc','kod_pocztowy','cecha_adresu','ulica','numer_budynku','umiejscowienie','poziom_pietro','opis_dojscia','kategoria_dostepu','calodobowo','godziny_dostepu','sposob_otwarcia','status_sprawnosci','data_weryfikacji','sposob_weryfikacji','zrodlo','id_zrodla','wskaznik_jakosci','dysponent_nazwa','dysponent_typ','status_rekordu','etykieta','sposob_geokodowania','data_aktualizacji']
D=[];ver=0
for r in csv.DictReader(open(src,encoding='utf-8-sig')):
    if not r['lat'] or r['status_rekordu']=='usuniety':continue
    dv=r['data_weryfikacji']
    ok=False
    if dv:
        try:ok=(today-datetime.date.fromisoformat(dv)).days<=365
        except ValueError:pass
    r['status_rekordu']='zweryfikowany' if ok and r['status_sprawnosci']!='niesprawny' else 'zgloszony'
    ver+=r['status_rekordu']=='zweryfikowany'
    if not r['nazwa_obiektu'].strip():
        adr=' '.join(x for x in [r['ulica'],r['numer_budynku']] if x).strip()
        op=r['dysponent_nazwa'].strip();od=r['opis_dojscia'].strip()
        r['nazwa_obiektu']=op or (f"AED, {adr}" if adr else (f"AED: {od[0].upper()+od[1:]}" if od else 'AED'))
    row=[]
    for k in H:
        v=r.get(k,'')
        if k in('lat','lon'):v=round(float(v),6)
        elif k=='wskaznik_jakosci':v=int(v or 0)
        row.append(v)
    D.append(row)
json.dump({'h':H,'d':D,'zrodlo':'OpenStreetMap (ODbL-1.0), przetworzone aedkit','data':today.isoformat()},open(out,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
print(len(D),'rekordow,',ver,'potwierdzonych')
