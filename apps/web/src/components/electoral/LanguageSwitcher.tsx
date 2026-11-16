import React, { useState, useRef, useEffect } from 'react';
import { useI18n, SUPPORTED_LANGUAGES, LanguageCode } from '@/i18n';

interface LanguageSwitcherProps {
  className?: string;
  variant?: 'compact' | 'full';
}

export const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({
  className = '',
  variant = 'compact',
}) => {
  const { language, setLanguage, currentLanguageOption, isNativeReviewed, reviewDisclaimer } = useI18n();
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className={`relative inline-block text-left ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-slate-700 bg-slate-800/90 hover:bg-slate-700/80 text-xs font-medium text-slate-200 transition-colors shadow-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
        title="Cambiar idioma (Español, Quechua, Aymara, Guaraní)"
        aria-label="Selector de idioma"
      >
        <span className="text-sm">{currentLanguageOption.flag}</span>
        <span className="font-semibold tracking-wide">
          {variant === 'full' ? currentLanguageOption.native : currentLanguageOption.code.toUpperCase()}
        </span>
        <svg
          className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-1.5 w-56 rounded-xl bg-slate-900 border border-slate-700 shadow-2xl py-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
          <div className="px-3 py-1.5 border-b border-slate-800">
            <p className="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
              Lenguas Originarias y Oficiales
            </p>
          </div>

          <div className="py-1">
            {SUPPORTED_LANGUAGES.map((opt) => {
              const isSelected = opt.code === language;
              return (
                <button
                  key={opt.code}
                  type="button"
                  onClick={() => {
                    setLanguage(opt.code);
                    setIsOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2 flex items-center justify-between text-xs transition-colors ${
                    isSelected
                      ? 'bg-emerald-500/15 text-emerald-300 font-semibold'
                      : 'text-slate-300 hover:bg-slate-800/70'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-base">{opt.flag}</span>
                    <div>
                      <p className="font-medium">{opt.label}</p>
                      <p className="text-[10px] text-slate-400">{opt.native}</p>
                    </div>
                  </div>
                  {isSelected && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  )}
                </button>
              );
            })}
          </div>

          {!isNativeReviewed && reviewDisclaimer && (
            <div className="px-3 py-2 mt-1 border-t border-slate-800/80 bg-slate-950/60">
              <p className="text-[10px] leading-tight text-amber-400/90 flex items-start gap-1">
                <span>⚠️</span>
                <span>{reviewDisclaimer}</span>
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
