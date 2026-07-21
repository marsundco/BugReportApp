# WUWER — reguły projektowe aplikacji wewnętrznych

Zasady wyglądu i zachowania interfejsu, wspólne dla wszystkich naszych
aplikacji webowych. Cel: kolejna aplikacja ma wyglądać jak poprzednie.

Pakiet to dwa pliki — ten opis i `tokens.css`. Nie zakłada żadnego konkretnego
języka backendu, narzędzi ani sposobu przechowywania projektu.

> **Dla instancji Claude:** przeczytaj całość **zanim** napiszesz pierwszą
> linijkę CSS. Skopiuj `tokens.css` do projektu i buduj na nim. Jeśli musisz
> złamać którąś regułę — napisz w komentarzu dlaczego.

---

## 1. Założenia techniczne

Tylko dwa, bo oba wpływają wprost na wygląd i działanie:

- **Zwykły CSS i JS, bez frameworka frontendowego.** Nasze aplikacje to
  formularze i tabele.
- **Żadnych zasobów z CDN** (czcionki, ikony, biblioteki). Aplikacje działają
  w sieci lokalnej, czasem bez internetu. Wszystko serwuj z własnego katalogu
  statycznego.

Reszta — backend, testy, sposób wdrożenia — jest dowolna.

---

## 2. Tokeny

Skopiuj `tokens.css`. **Nie wpisuj kolorów wprost w regułach CSS.** Jeśli
czegoś brakuje, dodaj token, nie wartość na miejscu.

### Powierzchnie

| Token | Wartość | Zastosowanie |
|---|---|---|
| `--bg` | `#0b1220` | tło strony |
| `--bg-elev` | `#131c2e` | karta, pasek nagłówka |
| `--bg-input` | `#0e1729` | wnętrze pola |

Warstwy buduje **kolor**, nie cień. Żadnych `box-shadow` do budowania głębi
(wyjątek: komunikat unoszący się nad treścią).

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

Zabronione: logo · nagłówki · ozdobniki · ikony bez funkcji.

Kiedy żółty jest wszędzie, przestaje cokolwiek znaczyć — a to jedyny kolor,
który na naszym ciemnym tle naprawdę przyciąga wzrok.

Na żółtym tle zawsze `--accent-ink`, nigdy biały.

---

## 3. Układ

### Jedna kolumna treści

Pasek nagłówka i karta z treścią dzielą tę samą szerokość (`--max-w`) i ten
sam margines boczny (`--gutter`). **Lewe krawędzie muszą pokrywać się co do
piksela.**

To jedyny powód, dla którego układ wygląda na zaprojektowany, a nie
przypadkowy. Sprawdzaj pomiarem, nie na oko:

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
  **podpisem** („czyja to aplikacja"), nie tytułem.
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

**Nigdy stałych szerokości pól.**

---

## 4. Komponenty

### Pola formularza

```css
input[type="text"], textarea {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border-field);
  border-radius: var(--radius-sm);
  padding: 12px 13px;
  font-size: 16px;
  font-family: inherit;
}
input:focus, textarea:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(255, 217, 102, 0.16);
}
```

**`font-size: 16px` w polach jest nienegocjowalny.** Poniżej tej wartości iOS
Safari przybliża widok przy wejściu w pole i użytkownik ląduje w przewiniętym,
rozjechanym formularzu.

Etykiety **nad** polem. Nigdy placeholder zamiast etykiety — znika w chwili,
gdy zaczyna być potrzebny.

### Grupy pól

Więcej niż cztery pola z rzędu czytają się jak lista bez znaczenia. Podziel na
nazwane sekcje: nagłówek `--text-muted`, wersaliki, 11 px,
`letter-spacing: 0.9px`, sekcje oddzielone `border-top`.

### Przyciski

- Minimum **48 px wysokości** — cel dotykowy dla operatora w rękawicach.
- Główny: tło `--accent`, tekst `--accent-ink`, pełna szerokość.
- Drugorzędny: przezroczysty, obramowanie `--border-strong`.
- Stan zajętości: dwie etykiety w HTML, przełączane klasą — nie podmieniaj
  `textContent`.

### Komunikaty

Jeden element `role="status" aria-live="polite"`, `position: fixed`, na dole,
`max-width: 480px`. Warianty `.ok` / `.err`. Nie używaj `alert()`.

### Listy plików i miniatury

Trzymaj **własny stan listy w JS**. `input.files` jest *zastępowane* przy
każdym wyborze, więc opieranie się na nim gubi wcześniejsze pliki. Czyść
`input.value` po każdym wyborze — dzięki temu da się wybrać ponownie ten sam
plik.

Każdy element ma widoczny stan: wysyłanie / OK / błąd. **Element z błędem
zostaje na liście** (na czerwono), żeby było wiadomo *który* zawiódł.

---

## 5. Logo i ikona

### Wordmark — technika maski

Nie utrzymujemy osobnych plików logo w różnych kolorach. Kształt bierzemy z
kanału alfa pliku PNG, a kolor z tokenu:

```css
.logo {
  height: clamp(19px, 5.2vw, 24px);
  aspect-ratio: 2868 / 1386;   /* Z PROPORCJI PLIKU */
  background-color: var(--text-muted);
  -webkit-mask: url(logo-white.png) left center / contain no-repeat;
          mask: url(logo-white.png) left center / contain no-repeat;
}
```

⚠️ **Szerokość musi wynikać z proporcji pliku.** Jeśli ustawisz wysokość i
szerokość niezależnie, `contain` wpisze wordmark w za duże pudełko i zostanie
martwy odstęp, wyglądający jak przypadkowa dziura w nagłówku.

### Ikona aplikacji ≠ logo firmy

**Ikona na ekranie głównym musi być znakiem TEJ aplikacji, nie logiem WUWER.**
Przy kilku aplikacjach identyczne kafle nie odróżniają niczego. Logo firmy
zostaje w pasku nagłówka, gdzie kontekst jest jednoznaczny.

Znak na tle `--bg`, w rozmiarach 192, 512 i „maskable" 512. W wariancie
maskable znak zajmuje ok. 52 % kafla — Android przycina go do koła.

---

## 6. Aplikacja instalowalna (PWA)

Jeśli aplikacja ma dać się zainstalować na tablecie:

- `manifest.webmanifest` i `sw.js` serwowane **z katalogu głównego** — plik
  `sw.js` z podkatalogu nie obejmie zakresem całej aplikacji.
- `background_color` i `theme-color` równe `--bg`.
- Service worker cache'uje **tylko powłokę aplikacji**. Nie kolejkuj żądań
  offline bez twardego wymagania: ciche wysyłanie po godzinach daje duplikaty
  i zgłoszenia „znikające" na pół dnia. Lepszy jawny błąd.
- Żądania `POST` **nigdy** nie przechodzą przez cache.

**Instalacja wymaga HTTPS** (poza `http://localhost`) — to reguła
przeglądarki, nie kwestia kodu. Aparat przez `<input type="file" capture>`
działa **bez** HTTPS; to nie jest `getUserMedia`.

---

## 7. Dostępność — zmierzone, nie deklarowane

| Para | Kontrast | |
|---|---|---|
| `--text` na `--bg` | 15.85 | AAA |
| `--text-dim` na `--bg-elev` | 8.62 | AAA |
| `--text-muted` na `--bg-elev` | 5.54 | AA |
| `--accent` na `--bg` | 13.70 | AAA |
| `--accent-ink` na `--accent` | 13.43 | AAA |
| `--ok` / `--danger` na `--bg-elev` | 6.70 / 5.08 | AA |
| `--border-field` na `--bg-elev` | 3.42 | AA (element UI) |

- Nie przyciemniaj `--border-field` — 3:1 to wymóg WCAG 1.4.11 dla granic
  elementów interaktywnych. (Zwykłe `--border` daje tu 1.29 — pole staje się
  praktycznie niewidoczne, dopóki się go nie dotknie.)
- Nie usuwaj `:focus-visible` bez zamiennika.
- Ikona powtarzająca sąsiedni tekst dostaje `alt=""` — czytnik ekranu ma
  przeczytać treść raz.
- Stan nigdy nie może być sygnalizowany **wyłącznie** kolorem: dokładaj znak
  (`✓`, `!`) albo tekst.

---

## 8. Język i teksty

- Interfejs **po polsku**, z polskimi znakami — w tym etykiety przycisków.
- **Nie poprawiaj samodzielnie etykiet odziedziczonych** po starszej wersji
  aplikacji, nawet jeśli mają literówki. Operatorzy znają je z pamięci.
  Zmieniaj tylko na wyraźne życzenie.
- Komunikaty błędów mówią, **co zrobić**, nie jaki kod HTTP wystąpił.
- Komentarze w kodzie po polsku — tłumaczą **dlaczego**, nie co robi linijka.

---

## 9. Antywzorce

| Nie rób | Dlaczego |
|---|---|
| Żółty na logo, nagłówkach, ozdobnikach | akcent przestaje znaczyć „akcja" |
| Kolory wpisane wprost w CSS | rozjazd między aplikacjami |
| Stałe szerokości pól | ucinają się na telefonie |
| `font-size < 16px` w polach | iOS przybliża widok przy fokusie |
| Cienie do budowania głębi | warstwy buduje kolor powierzchni |
| Zasoby z CDN | psują pracę bez internetu |
| Placeholder zamiast etykiety | znika, gdy staje się potrzebny |
| Więcej niż jeden breakpoint | układ nie do utrzymania |
| Ikona aplikacji = logo firmy | kafle nie do odróżnienia |

---

## 10. Checklista przed oddaniem

- [ ] Lewe krawędzie paska i karty pokrywają się (zmierzone w przeglądarce)
- [ ] Brak przewijania w poziomie przy 320, 375 i 1280 px
- [ ] Pola mają `font-size: 16px`, przyciski min. 48 px
- [ ] Żółty występuje **wyłącznie** przy akcjach i fokusie
- [ ] Wszystkie teksty interfejsu po polsku
- [ ] Ikona aplikacji to jej własny znak, nie logo firmy
- [ ] Fokus klawiatury jest widoczny na każdej kontrolce
