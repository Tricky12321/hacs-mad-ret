# 🍽️ Mad Planner — Home Assistant Custom Component

Et simpelt og stilfuldt plugin til Home Assistant, der hjælper dig med at holde styr på dine madretter.

## ✨ Features

- **Opret madretter** med navn, beskrivelse, ingredienser og kategorier
- **Søg og filtrer** — angiv ingredienser og/eller kategorier du har til rådighed
- **Smart sortering** — retter med flest matches vises øverst
- **Rediger og slet** retter nemt fra UI'et
- Gemmer data lokalt på din Home Assistant server

---

## 📦 Installation via HACS

1. Åbn HACS i Home Assistant
2. Gå til **Integrations** → klik de tre prikker → **Custom repositories**
3. Tilføj URL til dette repository og vælg kategori: `Integration`
4. Klik **Install**
5. Genstart Home Assistant

### Manuel installation

1. Kopier mappen `custom_components/mad_planner/` til din HA's `config/custom_components/`
2. Genstart Home Assistant

---

## ⚙️ Opsætning

1. Gå til **Indstillinger → Enheder & tjenester**
2. Klik **Tilføj integration**
3. Søg efter **Mad Planner**
4. Klik **Installer**

Et nyt punkt **Mad Planner** 🍽️ vises i din sidebjælke.

---

## 🔍 Søgefunktion

- Tilsæt ingredienser og/eller kategorier i søgefeltet
- Tryk **Søg** — retter der matcher vises øverst
- Det er ikke nødvendigt at alle ingredienser/kategorier matcher — selv ét match er nok til at retten vises
- Jo flere matches, jo højere op på listen

---

## 📁 Data

Data gemmes i `config/mad_planner_data.json`. Du kan frit tage backup af denne fil.

---

## 🛠 Krav

- Home Assistant 2023.1.0 eller nyere
