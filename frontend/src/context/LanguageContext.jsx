import { createContext, useContext, useState, useEffect } from "react";
import { translations } from "@/lib/i18n";

const LanguageContext = createContext();

const STORAGE_KEY = "cardiocoach_lang";

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(STORAGE_KEY) || "en";
    }
    return "en";
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, lang);
  }, [lang]);

  const t = (path) => {
    const keys = path.split(".");
    let result = translations[lang];
    for (const key of keys) {
      if (result && result[key] !== undefined) {
        result = result[key];
      } else {
        // Fallback to English
        result = translations.en;
        for (const k of keys) {
          if (result && result[k] !== undefined) {
            result = result[k];
          } else {
            return path;
          }
        }
        break;
      }
    }
    return result;
  };

  const toggleLanguage = () => {
    setLang((prev) => (prev === "en" ? "fr" : "en"));
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t, toggleLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within LanguageProvider");
  }
  return context;
};
