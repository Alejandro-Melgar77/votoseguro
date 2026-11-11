import React, { useState } from 'react';
import { Fingerprint, Copy, Check, ShieldCheck } from 'lucide-react';

interface CryptographicHashBadgeProps {
  label: string;
  hash: string | null;
  type?: 'config' | 'roll';
}

export const CryptographicHashBadge: React.FC<CryptographicHashBadgeProps> = ({
  label,
  hash,
  type = 'config',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const truncated = hash ? `${hash.slice(0, 10)}...${hash.slice(-8)}` : null;

  return (
    <div className="bg-ballot-ivory-50 border border-stone-300 rounded-lg p-3.5 flex items-center justify-between shadow-sm">
      <div className="flex items-center space-x-3">
        <div
          className={`w-9 h-9 rounded-md flex items-center justify-center ${
            hash
              ? 'bg-seal-emerald/10 text-seal-emerald border border-seal-emerald/30'
              : 'bg-stone-100 text-stone-400 border border-stone-200'
          }`}
        >
          {hash ? <ShieldCheck className="w-5 h-5" /> : <Fingerprint className="w-5 h-5" />}
        </div>
        <div>
          <span className="text-[10px] font-mono uppercase tracking-wider text-stone-500 font-semibold block">
            {label}
          </span>
          {hash ? (
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-bold text-civic-navy-900 tracking-wider">
                sha256:{truncated}
              </span>
              <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-semibold bg-emerald-100 text-seal-emerald">
                Inmutable
              </span>
            </div>
          ) : (
            <span className="font-mono text-xs text-stone-400 italic">
              No calculado (Pendiente de congelamiento)
            </span>
          )}
        </div>
      </div>

      {hash && (
        <button
          onClick={handleCopy}
          className="p-1.5 rounded-md hover:bg-stone-200/60 text-stone-600 transition-colors"
          title="Copiar hash completo al portapapeles"
        >
          {copied ? (
            <Check className="w-4 h-4 text-seal-emerald" />
          ) : (
            <Copy className="w-4 h-4 text-stone-500" />
          )}
        </button>
      )}
    </div>
  );
};
