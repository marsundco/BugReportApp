/* Karta niezgodności — logika formularza.
   Vanilla JS (bez HTMX/CDN): PWA ma działać z własnego app-shellu, więc nie
   wieszamy startu aplikacji na zewnętrznym skrypcie. */

const form = document.getElementById("report-form");
const submitBtn = document.getElementById("submit-btn");
const toastEl = document.getElementById("toast");

const photoInput = document.getElementById("photo");
const preview = document.getElementById("preview");
const previewImg = document.getElementById("preview-img");
const previewRemove = document.getElementById("preview-remove");

// Link zwrócony przez /upload. Zdjęcie wysyłamy od razu po wyborze, żeby
// „Zgłoś kartę" nie czekało na transfer — na hali liczy się szybkość.
let uploadedLink = "";
let uploadInFlight = null;

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
  photoInput.addEventListener("change", async () => {
    const file = photoInput.files && photoInput.files[0];
    if (!file) return;

    const objectUrl = URL.createObjectURL(file);
    previewImg.src = objectUrl;
    preview.hidden = false;
    preview.classList.add("uploading");

    const body = new FormData();
    body.append("photo", file);

    uploadInFlight = (async () => {
      try {
        const resp = await fetch("/upload", { method: "POST", body });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok || !data.ok) throw new Error(data.error || "Nie udało się wysłać zdjęcia.");
        uploadedLink = data.link;
      } catch (err) {
        uploadedLink = "";
        clearPhoto();
        toast(err.message || "Nie udało się wysłać zdjęcia.", "err");
      } finally {
        preview.classList.remove("uploading");
        uploadInFlight = null;
      }
    })();

    await uploadInFlight;
  });

  previewRemove.addEventListener("click", () => {
    clearPhoto();
  });
}

function clearPhoto() {
  uploadedLink = "";
  if (!photoInput) return;
  photoInput.value = "";
  preview.hidden = true;
  preview.classList.remove("uploading");
  if (previewImg.src.startsWith("blob:")) URL.revokeObjectURL(previewImg.src);
  previewImg.removeAttribute("src");
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

  // Jeśli zdjęcie wciąż leci na serwer — poczekaj, zamiast zgubić link.
  if (uploadInFlight) {
    toast("Czekam na wysłanie zdjęcia…", "ok", 2500);
    await uploadInFlight;
  }

  submitBtn.disabled = true;
  submitBtn.classList.add("busy");

  const body = new FormData(form);
  // Plik idzie osobnym endpointem — do /report wysyłamy tylko gotowy link.
  body.delete("photo");
  body.set("imageLink", uploadedLink);

  try {
    const resp = await fetch("/report", { method: "POST", body });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok || !data.ok) throw new Error(data.error || "Nie udało się wysłać zgłoszenia.");

    const nr = data.shortId ? ` (nr ${data.shortId})` : "";
    toast(`Zgłoszenie wysłane${nr}. Dziękujemy!`, "ok");

    form.reset();
    clearPhoto();
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
