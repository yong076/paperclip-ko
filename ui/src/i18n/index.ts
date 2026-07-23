import i18n, { type InitOptions, type TOptions } from "i18next";
import { initReactI18next, useTranslation as useReactI18nextTranslation } from "react-i18next";

import { DEFAULT_LOCALE, i18nextResources, supportedLocales } from "./locales";
import { syncKoreanRuntimeTranslation } from "./runtime-ko";

const LOCALE_STORAGE_KEY = "paperclip-language";
const FORK_DEFAULT_LOCALE = supportedLocales.includes("ko") ? "ko" : DEFAULT_LOCALE;

function normalizeSupportedLocale(value: string | null) {
  if (!value) return null;
  const trimmed = value.trim();
  return supportedLocales.includes(trimmed) ? trimmed : null;
}

function detectInitialLocale() {
  if (typeof window === "undefined") return FORK_DEFAULT_LOCALE;

  const params = new URLSearchParams(window.location.search);
  const queryLocale = normalizeSupportedLocale(params.get("lng") ?? params.get("language"));
  if (queryLocale) {
    try {
      window.localStorage.setItem(LOCALE_STORAGE_KEY, queryLocale);
    } catch {
      // Ignore storage failures; querystring selection still applies.
    }
    return queryLocale;
  }

  try {
    return normalizeSupportedLocale(window.localStorage.getItem(LOCALE_STORAGE_KEY)) ?? FORK_DEFAULT_LOCALE;
  } catch {
    return FORK_DEFAULT_LOCALE;
  }
}

const i18nextOptions: InitOptions = {
  resources: i18nextResources,
  lng: detectInitialLocale(),
  fallbackLng: DEFAULT_LOCALE,
  supportedLngs: supportedLocales,
  defaultNS: "translation",
  interpolation: { escapeValue: false },
  returnObjects: false,
  initAsync: false,
};

void i18n
  .use(initReactI18next)
  .init(i18nextOptions)
  .then(() => {
    syncKoreanRuntimeTranslation(i18n.language);
    i18n.on("languageChanged", syncKoreanRuntimeTranslation);
  })
  .catch((error: unknown) => {
    console.error("Failed to initialize i18next", error);
  });

export function t(key: string, options: TOptions = {}) {
  return i18n.t(key, options);
}

export const useTranslation = useReactI18nextTranslation;
export { i18n };
