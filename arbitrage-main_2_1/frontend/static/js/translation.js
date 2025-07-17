import { translations } from "./i18n.js"

const DEFAULT_LANG = "en"


export function applyTranslation() {
    const params = new URLSearchParams(window.location.search)
    const lang = params.get("lang") || DEFAULT_LANG
    const dict = translations[lang] || translations[DEFAULT_LANG]
    document.querySelectorAll("[data-i18n]").forEach(elem => {
        const key = elem.getAttribute("data-i18n")
        if (dict[key]) elem.innerText = dict[key]
    })
}