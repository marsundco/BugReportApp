/* Karta niezgodności — logika formularza.
   Vanilla JS (bez HTMX/CDN): PWA ma działać z własnego app-shellu, więc nie
   wieszamy startu aplikacji na zewnętrznym skrypcie. */

const form = document.getElementById("report-form");
const submitBtn = document.getElementById("submit-btn");
const toastEl = document.getElementById("toast");

const photoInput = document.getElementById("photo");
const gallery = document.getElementById("gallery");
const photoCount = document.getElementById("photo-count");

const MAX_PHOTOS = 10;

/* Własna lista zdjęć zamiast polegania na photoInput.files.
   To sedno poprawki: input.files jest ZASTĘPOWANE przy każdym wyborze, więc
   drugie zdjęcie kasowało pierwsze. Trzymamy stan po swojej stronie i po
   każdym wyborze czyścimy input (dzięki temu da się też dodać dwa razy ten
   sam plik, np. dwa ujęcia tej samej wady).

   Każdy wpis: { id, file, url, link, state: "upload" | "ok" | "err" } */
let photos = [];
let nextPhotoId = 1;

let toastTimer;
function toast(message, kind = "ok", ms = 5000) {
  clearTimeout(toastTimer);
  toastEl.textContent = message;
  toastEl.className = `toast ${kind}`;
  toastEl.hidden = false;
  // Wymuszenie reflow, żeby przejście odpaliło także przy kolejnych toastach.
  void toastEl.offsetWidth;
  toastEl.classList.add("show");
  toastTimer = setTimeout(() => {
    toastEl.classList.remove("show");
    setTimeout(() => { toastEl.hidden = true; }, 200);
  }, ms);
}

/* ---------- Zdjęcie ---------- */

if (photoInput) {
  photoInput.addEventListener("change", () => {
    const chosen = Array.from(photoInput.files || []);
    // Wyczyść od razu, żeby kolejny wybór zawsze odpalił "change" — także gdy
    // użytkownik wskaże ten sam plik ponownie.
    photoInput.value = "";
    if (!chosen.length) return;

    const room = MAX_PHOTOS - photos.length;
    if (room <= 0) {
      toast(`Można dodać maksymalnie ${MAX_PHOTOS} zdjęć.`, "err");
      return;
    }
    if (chosen.length > room) {
      toast(`Dodano ${room} z ${chosen.length} zdjęć (limit ${MAX_PHOTOS}).`, "err");
    }

    for (const file of chosen.slice(0, room)) {
      const entry = {
        id: nextPhotoId++,
        file,
        url: URL.createObjectURL(file),
        link: "",
        state: "upload",
      };
      photos.push(entry);
      renderGallery();
      uploadPhoto(entry);   // każde zdjęcie leci osobno i niezależnie
    }
  });

  gallery.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-remove]");
    if (btn) removePhoto(Number(btn.dataset.remove));
  });
}

async function uploadPhoto(entry) {
  const body = new FormData();
  body.append("photo", entry.file);
  try {
    const resp = await fetch("/upload", { method: "POST", body });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) throw new Error(data.error || "Nie udało się wysłać zdjęcia.");
    entry.link = data.link;
    entry.state = "ok";
  } catch (err) {
    entry.state = "err";
    // Nie kasujemy kafelka — użytkownik ma widzieć, KTÓRE zdjęcie padło,
    // i móc je usunąć albo dodać ponownie.
    toast(err.message || "Nie udało się wysłać zdjęcia.", "err");
  } finally {
    renderGallery();
  }
}

function removePhoto(id) {
  const entry = photos.find((p) => p.id === id);
  if (entry) URL.revokeObjectURL(entry.url);
  photos = photos.filter((p) => p.id !== id);
  renderGallery();
}

function clearPhotos() {
  for (const entry of photos) URL.revokeObjectURL(entry.url);
  photos = [];
  if (photoInput) photoInput.value = "";
  renderGallery();
}

function renderGallery() {
  if (!gallery) return;

  gallery.replaceChildren();
  gallery.hidden = photos.length === 0;
  photoCount.textContent = photos.length ? `(${photos.length}/${MAX_PHOTOS})` : "";

  for (const entry of photos) {
    const li = document.createElement("li");
    li.className = `thumb ${entry.state}`;

    const img = document.createElement("img");
    img.src = entry.url;
    img.alt = entry.file.name || "Zdjęcie";
    li.appendChild(img);

    const badge = document.createElement("span");
    badge.className = "thumb-badge";
    badge.textContent = entry.state === "upload" ? "…" : entry.state === "ok" ? "✓" : "!";
    badge.title = entry.state === "upload" ? "Wysyłanie…"
      : entry.state === "ok" ? "Wysłane" : "Błąd wysyłania";
    li.appendChild(badge);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "thumb-remove";
    remove.dataset.remove = String(entry.id);
    remove.setAttribute("aria-label", `Usuń ${entry.file.name || "zdjęcie"}`);
    remove.textContent = "×";
    li.appendChild(remove);

    gallery.appendChild(li);
  }
}

/* ---------- Walidacja ---------- */

function setInvalid(field, message) {
  const wrap = field.closest(".field");
  wrap.classList.add("invalid");
  if (!wrap.querySelector(".field-error")) {
    const p = document.createElement("div");
    p.className = "field-error";
    p.textContent = message;
    wrap.appendChild(p);
  }
}

function clearInvalid(field) {
  const wrap = field.closest(".field");
  wrap.classList.remove("invalid");
  const err = wrap.querySelector(".field-error");
  if (err) err.remove();
}

const shortDesc = document.getElementById("shortDesc");
shortDesc.addEventListener("input", () => {
  if (shortDesc.value.trim()) clearInvalid(shortDesc);
});

/* ---------- Wysyłka ---------- */

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!shortDesc.value.trim()) {
    setInvalid(shortDesc, "To pole jest wymagane.");
    shortDesc.focus();
    return;
  }

  // Któreś zdjęcie wciąż leci na serwer — poczekaj, zamiast zgubić link.
  if (photos.some((p) => p.state === "upload")) {
    toast("Czekam na wysłanie zdjęć…", "ok", 2500);
    while (photos.some((p) => p.state === "upload")) {
      await new Promise((resolve) => setTimeout(resolve, 150));
    }
  }

  // Zdjęcia, których nie udało się wysłać, nie blokują zgłoszenia — ale
  // użytkownik musi wiedzieć, że karta pójdzie bez nich.
  const failed = photos.filter((p) => p.state === "err").length;
  if (failed && !confirm(
    `${failed} zdjęcie/zdjęcia nie zostały wysłane i nie trafią do zgłoszenia.\n\nWysłać kartę mimo to?`
  )) {
    return;
  }

  submitBtn.disabled = true;
  submitBtn.classList.add("busy");

  const body = new FormData(form);
  // Pliki idą osobnym endpointem — do /report wysyłamy tylko gotowe linki,
  // po jednym w linii (backend rozdziela je po znaku nowej linii).
  body.delete("photo");
  body.set("imageLink", photos.filter((p) => p.link).map((p) => p.link).join("\n"));

  try {
    const resp = await fetch("/report", { method: "POST", body });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) throw new Error(data.error || "Nie udało się wysłać zgłoszenia.");

    const nr = data.shortId ? ` (nr ${data.shortId})` : "";
    toast(`Zgłoszenie wysłane${nr}. Dziękujemy!`, "ok");

    form.reset();
    clearPhotos();
    clearInvalid(shortDesc);
    // Klawiatura ekranowa na tablecie chowa się dopiero po zdjęciu fokusu.
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    window.scrollTo({ top: 0, behavior: "smooth" });
  } catch (err) {
    toast(err.message || "Nie udało się wysłać zgłoszenia.", "err", 7000);
  } finally {
    submitBtn.disabled = false;
    submitBtn.classList.remove("busy");
  }
});

/* ---------- PWA ---------- */

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* Brak SW = aplikacja nadal działa, tylko nie jest instalowalna. */
    });
  });
}
