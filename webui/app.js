/* VentoyThemer web UI. Vanilla JS, no build step. */
"use strict";

const $ = (id) => document.getElementById(id);
let api = null;
const getApi = () => (window.pywebview && window.pywebview.api) || null;

const S = {
  drive: null,          // root path of the selected drive
  state: null,          // get_state() result
  files: [],            // scanned image paths (rel)
  base: {},             // rel -> effective class from saved rules
  overrides: {},        // rel -> class | "" (cleared)
  available: [],        // classes the active theme can draw
  themeIcons: {},       // class -> dataURL (active theme)
  themes: [],           // registered theme file paths
  selectedTheme: null,  // theme rel path shown in the preview
  sources: [],          // archives/folders picked for install
  busy: false,
  lastClickedIndex: -1,
  previewData: null,   // cached get_preview() payload for selectedTheme
  languages: [],       // available language names
  wallpapers: [],      // "/ventoy/wallpapers/x.png" list
  themeBackgrounds: {},// theme key -> {original, wallpaper}
  iconSource: "",      // "theme:<Name>" or "pack:<Folder>"
};

/* ---------------- i18n ---------------- */
let MESSAGES = {};

function t(key, fallback) {
  return (MESSAGES && MESSAGES[key]) || fallback || key;
}

function applyI18n(i18n) {
  MESSAGES = i18n.messages || {};
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n, el.textContent);
  });
  if (i18n.resolutions) {
    const gfx = $("gfxmodeSelect");
    gfx.innerHTML = "";
    for (const res of i18n.resolutions) {
      gfx.add(new Option(res, res));
    }
  }
  const langSelect = $("langSelect");
  if (i18n.languages) {
    langSelect.innerHTML = "";
    for (const name of i18n.languages) langSelect.add(new Option(name, name));
    if (i18n.lang) langSelect.value = i18n.lang;
  }
}

/* Styled replacement for window.confirm (native script dialogs look
   alien inside the app window). */
function askChoices(text, options, checkboxLabel) {
  return new Promise((resolve) => {
    $("modalText").textContent = text;
    const buttons = $("modalButtons");
    buttons.innerHTML = "";
    const overlay = $("modalOverlay");
    overlay.hidden = false;
    const checkRow = $("modalCheckRow");
    const checkbox = $("modalCheckbox");
    checkbox.checked = false;
    checkRow.hidden = !checkboxLabel;
    if (checkboxLabel) $("modalCheckText").textContent = checkboxLabel;
    for (const opt of options) {
      const btn = document.createElement("button");
      if (opt.kind) btn.className = opt.kind;
      btn.textContent = opt.label;
      btn.onclick = () => {
        overlay.hidden = true;
        resolve({ value: opt.value, applyToAll: checkbox.checked });
      };
      buttons.append(btn);
    }
  });
}

async function askConfirm(text) {
  const result = await askChoices(text, [
    { value: true, label: t("dialog_confirm_delete_theme_title", "Confirm"), kind: "primary" },
    { value: false, label: t("option_skip", "Skip") },
  ]);
  return result.value;
}

function toast(message, kind) {
  const box = document.createElement("div");
  box.className = "toast" + (kind ? ` ${kind}` : "");
  box.textContent = message;
  $("toasts").append(box);
  setTimeout(() => box.remove(), 5000);
}

function toastError(error) {
  toast(error && error.message ? error.message : String(error), "error");
}

function toastOperationFailure(detail) {
  // detail is usually a technical backend message; the wrapper text is
  // localized, the detail stays as-is for debuggability.
  const suffix = detail ? ": " + detail : "";
  toast(t("toast_operation_failed", "Operation failed") + suffix, "error");
}

/* ---------------- helpers ---------------- */
function setStatus(message, busy) {
  const pill = $("statusPill");
  pill.textContent = message;
  pill.classList.toggle("busy", !!busy);
}

function setProgress(percent) {
  $("progressBar").style.width = `${Math.max(0, Math.min(100, percent || 0))}%`;
}

function backendEvent(payload) {
  if (payload.message) setStatus(payload.message, payload.stage !== "done" && payload.stage !== "error");
  if (payload.percent !== null && payload.percent !== undefined) setProgress(payload.percent);
  if (payload.stage === "done" || payload.stage === "error") {
    setTimeout(() => setProgress(0), 1500);
    if (payload.stage === "done") refreshAll();
  }
}

async function refreshAll() {
  await loadDriveState();
}

/* ---------------- drives ---------------- */
async function refreshDrives(keep) {
  const drives = await api.list_drives();
  const select = $("driveSelect");
  select.innerHTML = "";
  for (const d of drives) select.add(new Option(d.display, d.root));
  const ventoy = drives.find((d) => d.ventoy);
  const wanted = keep && drives.some((d) => d.root === keep)
    ? keep
    : (ventoy && ventoy.root) || (drives[0] && drives[0].root) || "";
  select.value = wanted;
  S.drive = wanted || null;
  await loadDriveState();
}

async function loadDriveState() {
  if (!S.drive) {
    $("themeList").innerHTML = "";
    $("fileList").innerHTML = "";
    renderPreview(null);
    return;
  }
  S.state = await api.get_state(S.drive);
  S.themes = S.state.theme_files || [];
  S.wallpapers = S.state.wallpapers || [];
  S.themeBackgrounds = S.state.theme_backgrounds || {};
  renderThemeList();
  $("defaultThemeSelect").innerHTML = "";
  $("defaultThemeSelect").add(new Option(t("option_random_theme", "Random Theme"), ""));
  for (const name of S.state.theme_names) $("defaultThemeSelect").add(new Option(name, name));
  $("defaultThemeSelect").value = S.state.default_theme || "";
  $("gfxmodeSelect").value = S.state.gfxmode || "max";
  renderIconSourceSelect();
  renderWallpaperSelect();
  await scanImages();
}

function renderIconSourceSelect() {
  const select = $("iconSourceSelect");
  select.innerHTML = "";
  for (const name of S.state.theme_names) select.add(new Option(name, "theme:" + name));
  for (const pack of S.state.icon_packs || []) select.add(new Option("\u{1F4E6} " + pack, "pack:" + pack));
  const sources = S.state.theme_icon_sources || {};
  // The previewed theme's own stored source, else the theme itself.
  // S.selectedTheme may be null during the initial load - fall back to
  // the default theme, then to the first registered one.
  const rel = S.selectedTheme
    || S.themes.find((r) => decodeURIComponent(r.split("/").slice(-2)[0]) === S.state.default_theme)
    || S.themes[0] || null;
  S.iconSource = (rel && sources[themeKey(rel)]) ||
    (rel ? "theme:" + (S.state.theme_names[S.themes.indexOf(rel)] || "") : "");
  const wanted = [...select.options].some((o) => o.value === S.iconSource);
  if (!wanted && select.options.length) S.iconSource = select.options[0].value;
  select.value = S.iconSource;
}

function themeKey(rel) {
  // "/ventoy/theme/<Folder>/..." -> "/ventoy/theme/<Folder>"
  return "/" + rel.replace(/^\/+/, "").split("/").slice(0, 3).join("/");
}

function renderWallpaperSelect() {
  const select = $("wallpaperSelect");
  select.innerHTML = "";
  select.add(new Option(t("wallpaper_theme_option", "Theme background"), ""));
  for (const rel of S.wallpapers) {
    select.add(new Option(rel.split("/").pop(), rel));
  }
  const info = S.selectedTheme ? S.themeBackgrounds[themeKey(S.selectedTheme)] : null;
  select.value = (info && info.wallpaper) || "";
}

async function changeWallpaper(value) {
  if (!S.selectedTheme) {
    toast(t("warning_no_theme_selected_to_delete_message", "No theme selected"), "error");
    return;
  }
  const result = await api.apply_background(S.drive, S.selectedTheme, value);
  if (result.ok) {
    delete S.previewData;
    await renderPreview(S.selectedTheme);
  } else {
    toastOperationFailure(result.error);
  }
}

async function addWallpapers(paths) {
  let added = 0;
  for (const p of paths) {
    const result = await api.add_wallpaper(S.drive, p);
    if (result.ok) { added++; }
  }
  if (added) {
    S.state.wallpapers = await api.list_wallpapers(S.drive);
    S.wallpapers = S.state.wallpapers;
    renderWallpaperSelect();
    toast(t("status_added_dropped_items_total", "Added {} item(s).").replace("{}", added), "success");
  }
}

/* ---------------- theme list ---------------- */
function renderThemeList() {
  const list = $("themeList");
  list.innerHTML = "";
  S.themes.forEach((rel, index) => {
    const name = (S.state.theme_names || [])[index] ||
                 decodeURIComponent(rel.split("/").slice(-2)[0]) || rel;
    const li = document.createElement("li");
    li.dataset.rel = rel;
    const label = document.createElement("span");
    label.textContent = name;
    label.style.flex = "1";
    label.style.overflow = "hidden";
    label.style.textOverflow = "ellipsis";
    li.append(label);

    const isDefault = name === S.state.default_theme;
    const star = document.createElement("button");
    star.textContent = isDefault ? "★" : "☆";
    star.title = t("select_default_theme_label", "Select Default Theme");
    star.onclick = (e) => { e.stopPropagation(); setDefaultTheme(name); };
    li.append(star);

    const trash = document.createElement("button");
    trash.textContent = "✕";
    trash.title = t("remove_selected_button", "Remove Selected Theme");
    trash.onclick = async (e) => {
      e.stopPropagation();
      const ok = await askConfirm(
        t("dialog_confirm_delete_theme_message", "Delete this theme?"));
      if (!ok) return;
      const result = await api.remove_theme(S.drive, name);
      if (result.ok) {
        toast(t("print_theme_folder_deleted", "Theme folder deleted: {}")
          .replace("{}", name), "success");
      } else {
        toastOperationFailure(result.error);
      }
      await refreshAll();
    };
    li.append(trash);

    li.onclick = () => {
      list.querySelectorAll("li").forEach((x) => x.classList.remove("selected"));
      li.classList.add("selected");
      S.selectedTheme = rel;
      // The icon combo follows the theme: its own stored source, else
      // the theme itself (nothing is persisted until the user acts).
      S.iconSource = (S.state.theme_icon_sources || {})[themeKey(rel)] || "theme:" + name;
      $("iconSourceSelect").value = S.iconSource;
      renderPreview(rel);
    };
    if (rel === S.selectedTheme) li.classList.add("selected");
    list.append(li);
  });
}

async function setDefaultTheme(name) {
  await api.set_default_theme(S.drive, name);
  await loadDriveState();
}

/* ---------------- install ---------------- */
async function browseSources() {
  const picked = await api.pick_sources();
  if (picked && picked.length) {
    for (const p of picked) if (!S.sources.includes(p)) S.sources.push(p);
    renderSources();
  }
}

function renderSources() {
  const list = $("sourcesList");
  list.innerHTML = "";
  for (const s of S.sources) {
    const li = document.createElement("li");
    li.textContent = s.split(/[\\/]/).pop();
    list.append(li);
  }
  // No queued sources -> one quiet line; queued -> share the card 50/50.
  list.classList.toggle("has-items", S.sources.length > 0);
}

function installName(source) {
  const base = source.split(/[\\/]/).pop();
  return base.includes(".") ? base.replace(/\.[^.]+$/, "") : base;
}

async function installSources() {
  if (S.busy) return;
  if (!S.drive) { setStatus(t("warning_select_drive_message", "Please select a drive first."), false); return; }
  if (!S.sources.length) { setStatus(t("warning_no_theme_archive_selected_message", "No theme archive selected"), false); return; }
  S.busy = true;
  const decisions = {};
  let applyToAll = false;
  let sharedDecision = null;
  for (const source of S.sources) {
    const name = installName(source);
    if (!S.state.theme_folders.includes(name)) continue;
    if (applyToAll) {
      decisions[source] = sharedDecision;
      continue;
    }
    const answer = await askChoices(
      t("dialog_overwrite_question", "Theme '{}' already exists. Choose an action.").replace("{}", name),
      [
        { value: "overwrite", label: t("option_overwrite", "Overwrite"), kind: "primary" },
        { value: "skip", label: t("option_skip", "Skip") },
        { value: "copy", label: t("option_copy", "Install a copy") },
      ],
      t("option_apply_to_all", "Apply to subsequent conflicts"),
    );
    decisions[source] = answer.value;
    if (answer.applyToAll) {
      applyToAll = true;
      sharedDecision = answer.value;
    }
  }
  const sources = S.sources.slice();
  const result = await api.install_themes(S.drive, sources, decisions);
  S.busy = false;
  if (result.ok) {
    S.sources = S.sources.filter((src) => !result.installed.includes(installName(src)));
    if (result.skipped.length) {
      toast(t("status_skipped_existing_theme", "Skipped existing theme: {}")
        .replace("{}", result.skipped.join(", ")));
    }
  }
  renderSources();
  await refreshAll();
}

/* ---------------- menu classes ---------------- */
async function scanImages(iconSourceOverride) {
  if (!S.drive) return;
  const data = await api.scan_images(S.drive, iconSourceOverride || null);
  S.files = data.files;
  S.base = data.base;
  S.overrides = {};
  S.available = data.available;
  const classList = $("classList");
  classList.innerHTML = "";
  for (const cls of data.available) {
    const opt = document.createElement("option");
    opt.value = cls;
    classList.append(opt);
  }

  if (!S.selectedTheme || !S.themes.includes(S.selectedTheme)) {
    S.selectedTheme = null;
    if (S.state.default_theme) {
      S.selectedTheme = S.themes.find(
        (rel) => decodeURIComponent(rel.split("/").slice(-2)[0]) === S.state.default_theme) || null;
    }
    S.selectedTheme = S.selectedTheme || S.themes[0] || null;
  }
  renderFileList();
  renderThemeList();
  await renderPreview(S.selectedTheme);
}

function displayClass(path) {
  const override = S.overrides[path];
  if (override === undefined) return S.base[path] || "vtoyiso";
  if (override === "") return "vtoyiso";
  return override;
}

function iconFor(cls) {
  return S.themeIcons[cls] || null;
}

function renderFileList() {
  const list = $("fileList");
  const cursor = list.querySelectorAll("li.selected");
  list.innerHTML = "";
  S.files.forEach((path, index) => {
    const cls = displayClass(path);
    const li = document.createElement("li");
    li.dataset.path = path;
    const icon = iconFor(cls);
    if (icon) {
      const img = document.createElement("img");
      img.src = icon;
      li.append(img);
    }
    const name = document.createElement("span");
    name.className = "fname";
    name.textContent = path;
    const tag = document.createElement("span");
    tag.className = "fcls";
    tag.textContent = cls;
    li.append(name, tag);
    li.onclick = (e) => {
      const items = [...list.children];
      if (e.shiftKey && S.lastClickedIndex >= 0) {
        items.forEach((x) => x.classList.remove("selected"));
        const [a, b] = [S.lastClickedIndex, index].sort((x, y) => x - y);
        for (let i = a; i <= b; i++) items[i].classList.add("selected");
      } else if (e.ctrlKey || e.metaKey) {
        li.classList.toggle("selected");
        S.lastClickedIndex = index;
      } else {
        items.forEach((x) => x.classList.remove("selected"));
        li.classList.add("selected");
        S.lastClickedIndex = index;
      }
    };
    list.append(li);
  });
}

function selectedPaths() {
  return [...$("fileList").querySelectorAll("li.selected")].map((li) => li.dataset.path);
}

async function setClass(value) {
  const paths = selectedPaths();
  const cls = (value !== undefined ? value : $("classInput").value).trim();
  if (!paths.length || !cls) return;
  for (const p of paths) S.overrides[p] = cls;
  renderFileList();
  renderEntries();
}

async function clearClass() {
  const paths = selectedPaths();
  if (!paths.length) return;
  for (const p of paths) S.overrides[p] = "";
  renderFileList();
  renderEntries();
}

async function autoSuggest() {
  const suggestions = await api.suggest_classes(S.files, S.available);
  for (const [path, cls] of Object.entries(suggestions)) {
    if (S.overrides[path] === undefined) S.overrides[path] = cls;
  }
  renderFileList();
  renderEntries();
}

async function applyClasses() {
  if (S.busy || !S.drive) return;
  S.busy = true;
  const result = await api.save_menu_class(S.drive, S.files, S.overrides, S.state.menu_class);
  S.busy = false;
  if (result.ok) {
    setStatus(t("menuclass_status_applied", "menu_class saved: {} rule(s).").replace("{}", result.count), false);
    await loadDriveState();
  }
}

/* ---------------- preview ---------------- */
function previewGfxmode() {
  const mode = (S.state && S.state.gfxmode) || "1024x768";
  return mode === "max" ? "1280x720" : mode;
}

function geomPx(geom, base) {
  if (!geom) return 0;
  return geom[0] === "%" ? (geom[1] / 100) * base : geom[1];
}

const sliceCache = {};

async function composeNineSlice(slices, width, height) {
  if (!slices || !Object.keys(slices).length) return null;
  const key = JSON.stringify([slices, width | 0, height | 0]);
  if (sliceCache[key]) return sliceCache[key];
  const load = (src) => new Promise((res) => { const im = new Image(); im.onload = () => res(im); im.src = src; });
  const imgs = {};
  for (const [suffix, src] of Object.entries(slices)) imgs[suffix] = await load(src);

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(width));
  canvas.height = Math.max(1, Math.round(height));
  const ctx = canvas.getContext("2d");
  const ew = imgs.e ? imgs.e.width : 0;
  const w2 = imgs.w ? imgs.w.width : ew;
  const nh = imgs.n ? imgs.n.height : 0;
  const sh = imgs.s ? imgs.s.height : 0;
  const cx = Math.max(1, canvas.width - ew - w2);
  const cy = Math.max(1, canvas.height - nh - sh);
  const draw = (im, x, y, w, h) => { if (im && w > 0 && h > 0) ctx.drawImage(im, x, y, w, h); };
  draw(imgs.c, w2, nh, cx, cy);
  draw(imgs.n, w2, 0, cx, nh);
  draw(imgs.s, w2, canvas.height - sh, cx, sh);
  draw(imgs.w, 0, nh, w2, cy);
  draw(imgs.e, canvas.width - ew, nh, ew, cy);
  draw(imgs.nw, 0, 0, w2, nh);
  draw(imgs.ne, canvas.width - ew, 0, ew, nh);
  draw(imgs.sw, 0, canvas.height - sh, w2, sh);
  draw(imgs.se, canvas.width - ew, canvas.height - sh, ew, sh);
  const url = canvas.toDataURL("image/png");
  sliceCache[key] = url;
  return url;
}

let previewSeq = 0;

function renderEntries() {
  const data = S.previewData;
  if (!data) { renderPreview(S.selectedTheme); return; }
  const scale = Math.max(0.1, Math.min(
    ($("previewStage").getBoundingClientRect().width - 24) / data.width,
    ($("previewStage").getBoundingClientRect().height - 24) / data.height));
  const menu = data.model.menu;
  const W = Math.round(data.width * scale), H = Math.round(data.height * scale);
  const mx = geomPx(menu.left, W), my = geomPx(menu.top, H);
  const mw = geomPx(menu.width, W), mh = geomPx(menu.height, H);
  const box = $("previewBox");
  box.style.width = `${W}px`;
  box.style.height = `${H}px`;
  const menuBox = $("previewMenuBox");
  Object.assign(menuBox.style, { left: `${mx}px`, top: `${my}px`, width: `${mw}px`, height: `${mh}px` });
  composeNineSlice(menu.menu_slices || {}, mw, mh).then((url) => {
    menuBox.style.backgroundImage = url ? `url("${url}")` : "none";
    menuBox.style.backgroundSize = "100% 100%";
  });

  const entriesBox = $("previewEntries");
  Object.assign(entriesBox.style, { left: `${mx}px`, top: `${my}px`, width: `${mw}px`, height: `${mh}px` });
  entriesBox.innerHTML = "";

  const fam = menu.font.family === "monospace"
    ? '"Cascadia Mono", Consolas, "Courier New", monospace'
    : '"Segoe UI", system-ui, sans-serif';
  const fontSize = Math.max(8, Math.round(menu.font.size * scale));
  const iconW = Math.round(menu.icon_width * scale);
  const iconH = Math.round(menu.icon_height * scale);
  const gap = Math.round(menu.item_icon_space * scale);
  const pad = Math.round(menu.item_padding * scale);
  const rowH = Math.max(iconH, Math.round(menu.item_height * scale));
  const rowGap = Math.max(0, Math.round(menu.item_spacing * scale));

  const label = data.model.label;
  const labelBox = $("previewLabel");
  if (label) {
    Object.assign(labelBox.style, {
      left: `${geomPx(label.left, W)}px`,
      top: `${geomPx(label.top, H)}px`,
      width: label.width ? `${geomPx(label.width, W)}px` : "auto",
      textAlign: label.align || "left",
      color: label.color,
      fontSize: `${Math.max(8, Math.round(label.font.size * scale))}px`,
      fontFamily: fam,
      display: "",
    });
    labelBox.textContent = (label.text || "").replace("%d", "10");
  } else {
    labelBox.style.display = "none";
  }

  S.files.slice(0, 12).forEach((path, index) => {
    const cls = displayClass(path);
    const row = document.createElement("div");
    row.className = "pentry" + (index === 0 ? " selected" : "");
    row.style.height = `${rowH}px`;
    row.style.marginBottom = `${rowGap}px`;
    row.style.paddingLeft = `${pad}px`;
    if (index === 0) {
      row.style.color = menu.selected_item_color;
      composeNineSlice(menu.select_slices || {}, mw, rowH).then((url) => {
        if (index === 0) {
          row.style.backgroundImage = url ? `url("${url}")` : "none";
          row.style.backgroundSize = "100% 100%";
        }
      });
    } else {
      row.style.color = menu.item_color;
    }
    const icon = S.themeIcons[cls];
    if (icon) {
      const img = document.createElement("img");
      img.src = icon;
      img.style.width = `${iconW}px`;
      img.style.height = `${iconH}px`;
      img.style.marginRight = `${gap}px`;
      row.append(img);
    }
    const text = document.createElement("span");
    text.textContent = path.split("/").pop();
    text.style.fontSize = `${fontSize}px`;
    text.style.fontFamily = fam;
    row.append(text);
    entriesBox.append(row);
  });
}

async function renderPreview(themeRel) {
  const seq = ++previewSeq;
  const stage = $("previewStage");
  const empty = $("previewEmpty");
  if (!themeRel || !S.drive) {
    $("previewBox").style.display = "none";
    empty.style.display = "";
    return;
  }
  empty.style.display = "none";
  const data = await api.get_preview(S.drive, themeRel, previewGfxmode());
  if (seq !== previewSeq) return;
  if (!data.ok) {
    $("previewBox").style.display = "none";
    empty.style.display = "";
    return;
  }
  S.previewData = data;
  S.themeIcons = data.icons || {};

  const stageBox = stage.getBoundingClientRect();
  const scale = Math.max(0.1, Math.min((stageBox.width - 24) / data.width, (stageBox.height - 24) / data.height));
  const box = $("previewBox");
  const W = Math.round(data.width * scale);
  const H = Math.round(data.height * scale);
  box.style.display = "";
  box.style.width = `${W}px`;
  box.style.height = `${H}px`;

  const bg = $("previewBg");
  bg.style.backgroundImage = data.background ? `url("${data.background}")` : "none";
  bg.style.backgroundColor = data.model.desktop_color || "#000";

  const menu = data.model.menu;
  const fam = menu.font.family === 'monospace'
    ? '"Cascadia Mono", Consolas, "Courier New", monospace'
    : '"Segoe UI", system-ui, sans-serif';
  const menuBox = $("previewMenuBox");
  const mx = geomPx(menu.left, W), my = geomPx(menu.top, H);
  const mw = geomPx(menu.width, W), mh = geomPx(menu.height, H);
  Object.assign(menuBox.style, {
    left: `${mx}px`, top: `${my}px`, width: `${mw}px`, height: `${mh}px`,
    backgroundImage: menu.menu_slices && Object.keys(menu.menu_slices).length
      ? `url("${await composeNineSlice(menu.menu_slices, mw, mh)}")` : "none",
    backgroundSize: "100% 100%",
  });

  renderEntries();
}

/* ---------------- wiring ---------------- */
function wire() {
  $("driveSelect").onchange = async () => {
    S.drive = $("driveSelect").value || null;
    S.selectedTheme = null;
    await loadDriveState();
  };
  $("makeDefaultBtn").onclick = installSources;
  $("browseBtn").onclick = browseSources;
  $("clearSourcesBtn").onclick = () => { S.sources = []; renderSources(); };
  $("rescanBtn").onclick = scanImages;
  $("suggestBtn").onclick = autoSuggest;
  $("setClassBtn").onclick = () => setClass();
  $("clearClassBtn").onclick = clearClass;
  $("applyClassesBtn").onclick = applyClasses;
  $("defaultThemeSelect").onchange = (e) => setDefaultTheme(e.target.value);
  $("gfxmodeSelect").onchange = async (e) => {
    await api.set_gfxmode(S.drive, e.target.value);
    S.state.gfxmode = e.target.value;
    renderPreview(S.selectedTheme);
  };
  $("classInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter") setClass();
  });
  $("iconSourceSelect").onchange = async (e) => {
    if (!S.selectedTheme) {
      toast(t("warning_no_theme_selected_to_delete_message", "No theme selected"), "error");
      return;
    }
    S.busy = true;
    setStatus(t("status_ready", "Status - READY"), true);
    const key = themeKey(S.selectedTheme);
    const result = await api.apply_icon_set(S.drive, key, e.target.value);
    S.busy = false;
    if (result.ok) {
      S.state = await api.get_state(S.drive);
      S.iconSource = e.target.value;
      delete S.previewData;
      renderFileList();
      await renderPreview(S.selectedTheme);
      setStatus(t("menuclass_status_applied", "menu_class saved: {} rule(s).").replace("{}", result.rules), false);
    } else {
      toastOperationFailure(result.error);
    }
  };
  $("addIconPackBtn").onclick = async () => {
    if (!S.drive) { setStatus(t("warning_select_drive_message", "Please select a drive first."), false); return; }
    const folder = await api.pick_folder();
    if (!folder) return;
    const result = await api.add_icon_pack(S.drive, folder);
    if (result.ok) {
      S.state = await api.get_state(S.drive);
      renderIconSourceSelect();
      S.iconSource = "pack:" + result.name;
      $("iconSourceSelect").value = S.iconSource;
      await scanImages(S.iconSource);
      toast(t("status_added_dropped_items_total", "Added {} item(s).").replace("{}", 1), "success");
    } else {
      toastOperationFailure(result.error);
    }
  };
  $("wallpaperSelect").onchange = (e) => changeWallpaper(e.target.value);
  $("addWallpaperBtn").onclick = async () => {
    const path = await api.pick_image();
    if (path) await addWallpapers([path]);
  };
  $("removeWallpaperBtn").onclick = async () => {
    const value = $("wallpaperSelect").value;
    if (!value) {
      toast(t("wallpaper_none_selected", "No wallpaper selected"), "error");
      return;
    }
    const result = await api.remove_wallpaper(S.drive, value);
    if (result.ok) {
      S.state.wallpapers = await api.list_wallpapers(S.drive);
      S.wallpapers = S.state.wallpapers;
      renderWallpaperSelect();
      if (S.selectedTheme) {
        delete S.previewData;
        await renderPreview(S.selectedTheme);
      }
      toast(t("status_ready", "Status - READY"));
    } else {
      toastOperationFailure(result.error);
    }
  };
  $("langSelect").onchange = async (e) => {
    const result = await api.set_language(e.target.value);
    if (result.ok) {
      applyI18n(result);
      // re-render everything whose text was generated with t()
      if (S.state) {
        $("defaultThemeSelect").innerHTML = "";
        $("defaultThemeSelect").add(new Option(t("option_random_theme", "Random Theme"), ""));
        for (const name of S.state.theme_names) {
          $("defaultThemeSelect").add(new Option(name, name));
        }
        $("defaultThemeSelect").value = S.state.default_theme || "";
      }
      renderThemeList();
      renderWallpaperSelect();
      setStatus(t("status_ready", "Status - READY"), false);
    }
  };
  $("fullscreenBtn").onclick = () => {
    const stage = $("previewStage");
    if (document.fullscreenElement) document.exitFullscreen();
    else if (stage.requestFullscreen) stage.requestFullscreen().catch(toastError);
  };
  document.addEventListener("fullscreenchange", () => renderEntries());

  // Drag & drop: paths arrive through the python-side DOM hook
  // (register_dom_hooks → window.addDroppedSources). The listeners here
  // only stop the browser from navigating to the dropped file.
  document.addEventListener("dragover", (e) => e.preventDefault());
  document.addEventListener("drop", (e) => e.preventDefault());

  window.addEventListener("resize", () => renderEntries());
  new ResizeObserver(() => renderEntries()).observe($("previewStage"));
  document.querySelectorAll("#footer a").forEach((a) => {
    a.onclick = (e) => { e.preventDefault(); api.open_link(a.dataset.link); };
  });
}

async function refreshDrivesAndState() {
  await refreshDrives(S.drive);
}

async function boot() {
  // The pywebview bridge is injected asynchronously; poll briefly.
  for (let i = 0; !api && i < 100; i++) {
    api = getApi();
    if (!api) await new Promise((resolve) => setTimeout(resolve, 100));
  }
  if (!api) {
    document.body.innerHTML = "<p style='padding:20px'>pywebview API is unavailable.</p>";
    return;
  }
  wire();
  const i18n = await api.get_i18n();
  i18n.languages = await api.get_languages();
  applyI18n(i18n);
  await refreshDrives();
  setStatus(t("status_ready", "Status - READY"), false);
}

window.addDroppedWallpapers = function (paths) {
  if (paths && paths.length) addWallpapers(paths);
};

window.addDroppedSources = function (paths) {
  if (paths && paths.length) {
    let added = 0;
    for (const p of paths) {
      if (!S.sources.includes(p)) { S.sources.push(p); added++; }
    }
    renderSources();
    toast(t("status_added_dropped_items_total", "Added {} item(s).").replace("{}", added), "success");
  } else {
    toast(t("print_skipping_unsupported_dropped_item", "Unsupported dropped item").replace("{}", ""), "error");
  }
};

window.backendEvent = backendEvent;
window.addEventListener("pywebviewready", boot);
boot();
