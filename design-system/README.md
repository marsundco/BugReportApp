# WUWER — reguły projektowe aplikacji wewnętrznych

Pakiet startowy dla **każdej kolejnej aplikacji webowej WUWER**. Zawiera stack,
tokeny, układ, komponenty i uzasadnienia decyzji — czyli wszystko, czego
potrzeba, żeby nowa aplikacja wyglądała i działała jak poprzednie.

**Aplikacje referencyjne:** Lean Daily Management Board · Karta niezgodności
(`web/` w tym repo — patrz jej `style.css` i `form.html` jako żywy przykład).

> **Dla instancji Claude:** przeczytaj ten plik w całości **zanim** napiszesz
> pierwszą linijkę CSS lub HTML. Skopiuj `tokens.css` i buduj na nim. Jeśli
> musisz złamać którąś regułę — napisz w komentarzu dlaczego.

---

## 1. Stack — obowiązkowy

| Warstwa | Wybór |
|---|---|
| Backend | Python 3.11 · FastAPI |
| Szablony | Jinja2 |
| Frontend | vanilla JS (moduły ES) + zwykły CSS |
| HTTP | `requests` |
| Konfiguracja | `python-dotenv` + `config.py` |
| Testy | `pytest` |
| Serwer | `uvicorn` pod `systemd` |
| Baza danych | **brak**, dopóki nie jest naprawdę potrzebna |

**Czego nie używamy i dlaczego:**

- **Żadnego npm ani kroku build.** Wdrożenie to `git pull` + restart usługi.
  Build znaczy: node_modules na serwerze, wersje, „u mnie działa".
- **Żadnych zasobów z CDN.** Aplikacja ma działać w sieci lokalnej bez
  internetu, a PWA nie może zależeć od zewnętrznego skryptu przy starcie.
  Wszystko serwujemy z `/static`.
- **Żadnego frameworka frontendowego.** Nasze aplikacje to formularze i
  tabele. React nie rozwiązuje tu żadnego istniejącego problemu.

HTMX jest dopuszczalny (używa go LDMB), ale **hostuj go lokalnie**, nie z CDN.

---

## 2. Struktura projektu

```
app/
  main.py         FastAPI: trasy, montowanie /static, /healthz
  <domena>.py     klient zewnętrznego API (jeden plik na integrację)
  templates/      szablony Jinja2
  static/         style.css, app.js, sw.js, manifest, logo, ikony
config.py         konfiguracja z .env (nic wpisanego na sztywno)
tests/            pytest
tools/            skrypty pomocnicze (np. make_icons.py)
deploy/           jednostka systemd + instrukcja
.env.example      wszystkie klucze, wartości puste
requirements.txt
```

---

## 3. Tokeny

Skopiuj `tokens.css`. **Nie wpisuj kolorów wprost w regułach CSS** — jeśli
czegoś brakuje, dodaj token, nie wartość na miejscu.

### Powierzchnie

| Token | Wartość | Zastosowanie |
|---|---|---|
| `--bg` | `#0b1220` | tło strony |
| `--bg-elev` | `#131c2e` | karta, pasek nagłówka |
| `--bg-input` | `#0e1729` | wnętrze pola |

Warstwy buduje **kolor**, nie cień. Żadnych `box-shadow` do budowania
głębi (wyjątek: toast, który unosi się nad treścią).

### Tekst

| Token | Zastosowanie |
|---|---|
| `--text` | treść, etykiety pól |
| `--text-dim` | teksty drugorzędne |
| `--text-muted` | podpisy, nagłówki grup, logo |

Trzy poziomy wystarczają. Czwarty oznacza, że hierarchia jest do poprawy.

### Akcent — najważniejsza reguła koloru

**Żółty `--accent` oznacza wyłącznie: „to coś robi albo wymaga uwagi".**

Dozwolone: przycisk główny · obwódka fokusu · gwiazdka pola wymaganego ·
aktywny stan kontrolki.

Zabronione: logo · nagłówki · ozdobniki · ikony bez funkcji · ramki „dla
ładności". Kiedy żółty jest wszędzie, przestaje cokolwiek znaczyć — a to
jedyny kolor, który na naszym ciemnym tle naprawdę przyciąga wzrok.

Na żółtym tle zawsze `--accent-ink` (13.4:1), nigdy biały.

---

## 4. Układ

### Jedna kolumna treści

Wszystko — pasek nagłówka, tytuł, karta — dzieli tę samą szerokość
(`--max-w`) i ten sam margines boczny (`--gutter`). **Lewe krawędzie muszą
się pokrywać co do piksela.**

To jest jedyny powód, dla którego układ wygląda na zaprojektowany, a nie
przypadkowy. Sprawdzaj to pomiarem, nie na oko:

```js
document.querySelector('.appbar-inner').getBoundingClientRect().left
  === document.querySelector('.card').getBoundingClientRect().left
```

### Pasek nagłówka

```
[ znak aplikacji  Nazwa aplikacji ] ................. [ logo WUWER ]
```

- **Po lewej tożsamość aplikacji** (ikona + nazwa) — to główna informacja
  i to ona trzyma wspólną krawędź z treścią.
- **Po prawej logo firmy**, przygaszone do `--text-muted`. Logo jest
  **podpisem** („czyja to aplikacja"), nie tytułem. Nie może przeciągać
  wzroku z nazwy.
- Cały pasek to **jeden wiersz**, ok. 47 px. Na tablecie każdy piksel nad
  treścią to piksel mniej na treść.

Nie dodawaj zdań objaśniających pod tytułem — użytkownik czyta je raz, a
zajmują miejsce przy każdym otwarciu.

### Responsywność

Mobile-first. **Jeden breakpoint: 560 px.** Poniżej — jedna kolumna, pełna
szerokość. Powyżej — pola mogą stanąć parami.

Do siatek używaj `auto-fill` + `minmax()` zamiast kolejnych breakpointów:

```css
grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
```

**Nigdy stałych szerokości pól.** (Aplikacja androidowa miała `400dp` i
ucinała się na telefonie — to był jeden z powodów całego przepisania.)

---

## 5. Komponenty

### Pola formularza

```css
input[type="text"], textarea {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border-field);
  border-radius: var(--radius-sm);
  padding: 12px 13px;
  font-size: 16px;       /* NIE mniej — patrz niżej */
  font-family: inherit;
}
input:focus, textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(255, 217, 102, 0.16);
}
```

**`font-size: 16px` w polach jest nienegocjowalny.** Poniżej tej wartości
iOS Safari przybliża widok przy wejściu w pole i użytkownik ląduje w
przewiniętym, rozjechanym formularzu.

Etykiety **nad** polem, nigdy placeholdery zamiast etykiet — placeholder
znika w chwili, gdy zaczyna być potrzebny.

### Grupy pól

Więcej niż cztery pola z rzędu czytają się jak lista bez znaczenia. Podziel
je na nazwane sekcje (`<section class="group">` + nagłówek `--text-muted`,
wersaliki, 11 px, `letter-spacing: 0.9px`), oddzielone `border-top`.

### Przyciski

- Minimum **48 px wysokości** — cel dotykowy dla operatora w rękawicach.
- Główny: tło `--accent`, tekst `--accent-ink`, pełna szerokość.
- Drugorzędny: przezroczysty, obramowanie `--border-strong`.
- Stan zajętości: dwie etykiety w środku, przełączane klasą (`.busy`),
  nie podmiana `textContent` — tekst „Wysyłam…" ma być w HTML.

### Komunikaty (toast)

Jeden element `role="status" aria-live="polite"`, `position: fixed`, na dole,
`max-width: 480px`. Warianty `.ok` / `.err`. Nie używaj `alert()`.

### Miniatury i listy plików

Trzymaj **własny stan listy w JS**. `input.files` jest *zastępowane* przy
każdym wyborze, więc opieranie się na nim gubi wcześniejsze pliki.
Czyść `input.value` po każdym wyborze — dzięki temu da się też wybrać
ponownie ten sam plik.

Każdy element ma widoczny stan: wysyłanie / OK / błąd. **Element z błędem
zostaje na liście** (na czerwono), żeby było wiadomo *który* zawiódł.

---

## 6. Logo i ikony

### Wordmark — technika maski

Nie utrzymujemy osobnych plików logo w różnych kolorach. Kształt bierzemy z
kanału alfa PNG, a kolor z tokenu:

```css
.logo {
  height: clamp(19px, 5.2vw, 24px);
  aspect-ratio: 2868 / 1386;   /* Z PROPORCJI PLIKU */
  background-color: var(--text-muted);
  -webkit-mask: url(/static/logo-white.png) left center / contain no-repeat;
          mask: url(/static/logo-white.png) left center / contain no-repeat;
}
```

⚠️ **Szerokość musi wynikać z proporcji pliku.** Jeśli ustawisz wysokość i
szerokość niezależnie, `contain` wpisze wordmark w za duże pudełko i zostanie
martwy odstęp, który wygląda jak przypadkowa dziura w nagłówku.

### Ikona aplikacji ≠ logo firmy

**Ikona PWA musi być znakiem TEJ aplikacji, nie logiem WUWER.** Przy kilku
aplikacjach na ekranie głównym identyczne kafle nie odróżniają niczego.
Logo firmy zostaje w pasku nagłówka, gdzie kontekst jest jednoznaczny.

Znak na tle `--bg`, generowany skryptem (`tools/make_icons.py`) w rozmiarach
192, 512 i maskable 512. W wariancie `maskable` znak zajmuje ok. 52 %
kafla — Android przycina go do koła.

---

## 7. PWA

Wymagane: `manifest.webmanifest` (serwowany **z roota**), `sw.js`
(też **z roota** — inaczej nie obejmie zakresem całej aplikacji), ikony,
`theme-color`, `apple-mobile-web-app-capable`.

**Service worker cache'uje wyłącznie app-shell.** Nie kolejkuj żądań offline,
dopóki nie ma na to twardego wymagania: ciche wysyłanie po godzinach daje
duplikaty i zgłoszenia „znikające" na pół dnia. Lepszy jawny błąd.

- Dokument: **network-first** (po wdrożeniu ma przyjść świeża wersja).
- Statyki: cache-first + `?v=<mtime>` w adresie.
- Żądania `POST` **nigdy** nie przechodzą przez cache.

**Instalacja wymaga HTTPS** (poza `http://localhost`) — to reguła
przeglądarki, nie kwestia kodu. Aparat przez `<input type="file" capture>`
działa **bez** HTTPS; to nie jest `getUserMedia`.

---

## 8. Dostępność — zmierzone, nie deklarowane

Kontrasty tej palety (WCAG):

| Para | Kontrast | |
|---|---|---|
| `--text` na `--bg` | 15.85 | AAA |
| `--text-dim` na `--bg-elev` | 8.62 | AAA |
| `--text-muted` na `--bg-elev` | 5.54 | AA |
| `--accent` na `--bg` | 13.70 | AAA |
| `--accent-ink` na `--accent` | 13.43 | AAA |
| `--ok` / `--danger` na `--bg-elev` | 6.70 / 5.08 | AA |
| `--border-field` na `--bg-elev` | 3.42 | AA (element UI) |

Zasady:

- Nie przyciemniaj `--border-field` — 3:1 to wymóg WCAG 1.4.11 dla granic
  elementów interaktywnych.
- Nie usuwaj `:focus-visible` bez zamiennika.
- Ikona powtarzająca sąsiedni tekst dostaje `alt=""` — czytnik ekranu ma
  przeczytać treść raz.
- Stan nigdy nie może być sygnalizowany **wyłącznie** kolorem: dokładaj
  znak (`✓`, `!`) albo tekst.
- Respektuj `prefers-reduced-motion` (jest w `tokens.css`).

---

## 9. Język i teksty

- Interfejs **po polsku**, z polskimi znakami.
- **Nie poprawiaj etykiet odziedziczonych** po starszej wersji aplikacji,
  nawet jeśli mają literówki. Operatorzy znają je z pamięci; zgodność jest
  ważniejsza niż poprawność. (W Karcie niezgodności celowo zostało
  „Jaka niezgodnośc postąpiła?".)
- Komunikaty błędów mówią, **co zrobić**, nie jaki kod HTTP wystąpił.
- Komentarze w kodzie po polsku — tłumaczą **dlaczego**, nie co robi linijka.

---

## 10. Backend — konwencje

- **Żaden sekret nie trafia do przeglądarki.** Klucze API żyją w `.env`,
  aplikacja rozmawia z zewnętrznym API przez własny endpoint-proxy.
- `.env` jest w `.gitignore`; `.env.example` zawiera wszystkie klucze z
  pustymi wartościami i komentarzem, skąd je wziąć.
- **W testach używaj wartości atrap**, nigdy prawdziwych kluczy — testy
  trafiają do repo.
- Każda aplikacja wystawia **`/healthz`**, który pokazuje stan konfiguracji
  (`true`/`false`), ale **nigdy samych wartości**.
- Kroki poboczne (np. ustawienie statusu po utworzeniu rekordu) mają być
  **nieblokujące**: jeśli główna operacja się powiodła, użytkownik widzi
  sukces, a szczegóły idą do logu. Błąd zachęciłby do ponownej wysyłki i
  zdublował dane.

### Konwencje wdrożenia

| | |
|---|---|
| Katalog | `/srv/wuwer/<app>/` |
| Usługa | `wuwer-<app>.service` |
| Porty | od 8000 w górę, jeden na aplikację |
| Przegląd | `systemctl list-units 'wuwer-*'` |

---

## 11. Antywzorce — czego nie robić

| Nie rób | Dlaczego |
|---|---|
| Żółty na logo, nagłówkach, ozdobnikach | akcent przestaje znaczyć „akcja" |
| Kolory wpisane wprost w CSS | rozjazd między aplikacjami |
| Stałe szerokości pól | ucinają się na telefonie |
| `font-size < 16px` w polach | iOS przybliża widok przy fokusie |
| Cienie do budowania głębi | warstwy buduje kolor powierzchni |
| Zasoby z CDN | psują PWA i pracę bez internetu |
| Placeholder zamiast etykiety | znika, gdy staje się potrzebny |
| Kolejka offline „na wszelki wypadek" | duplikaty i znikające zgłoszenia |
| Więcej niż jeden breakpoint | układ robi się nie do utrzymania |
| Sekret w kodzie klienta | rotacja wymaga przebudowy aplikacji |

---

## 12. Checklista przed wdrożeniem

- [ ] Lewe krawędzie paska i karty pokrywają się (zmierzone w przeglądarce)
- [ ] Brak przewijania w poziomie przy 320, 375 i 1280 px
- [ ] Pola mają `font-size: 16px`, przyciski min. 48 px
- [ ] Żółty występuje **wyłącznie** przy akcjach i fokusie
- [ ] Ikona PWA to znak aplikacji, nie logo firmy
- [ ] `manifest` i `sw.js` serwowane z roota
- [ ] `/healthz` odpowiada i nie ujawnia wartości sekretów
- [ ] Żaden sekret nie występuje w HTML ani w plikach `/static` (test!)
- [ ] `.env` w `.gitignore`, `.env.example` uzupełniony
- [ ] Testy przechodzą
