import React from 'react';
import { Candidate } from '@votoseguro/api-client';

interface OfficialBallotPreviewCardProps {
  electionName: string;
  contestName: string;
  constituencyName: string;
  allowBlank: boolean;
  allowNull: boolean;
  candidates: Candidate[];
}

export const OfficialBallotPreviewCard: React.FC<OfficialBallotPreviewCardProps> = ({
  electionName,
  contestName,
  constituencyName,
  allowBlank,
  allowNull,
  candidates,
}) => {
  return (
    <div className="bg-[#FAF8F5] border-2 border-slate-300 rounded-xl shadow-md p-6 max-w-md mx-auto text-slate-800 relative overflow-hidden select-none">
      {/* Marca de agua de fondo */}
      <div className="absolute inset-0 flex items-center justify-center opacity-[0.03] pointer-events-none">
        <span className="font-serif text-8xl font-black rotate-[-25deg] uppercase">VotoSeguro</span>
      </div>

      {/* Encabezado Oficial de Papeleta */}
      <div className="text-center pb-4 border-b-2 border-slate-400/50 mb-5 relative">
        <div className="inline-block px-3 py-0.5 rounded-full bg-civic-navy/10 text-civic-navy font-mono text-2xs font-bold uppercase tracking-widest mb-1">
          Papeleta Oficial de Sufragio
        </div>
        <h3 className="font-serif font-black text-lg text-civic-navy tracking-tight leading-tight">
          {electionName}
        </h3>
        <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mt-0.5">
          {contestName}
        </p>
        <div className="text-2xs text-slate-500 font-mono mt-1">
          Circunscripción: <span className="font-bold text-slate-700">{constituencyName}</span>
        </div>
      </div>

      {/* Instrucciones al votante */}
      <div className="text-2xs text-slate-500 text-center italic mb-4">
        Marque con una sola cruz o tilde en la casilla correspondiente a su preferencia electoral.
      </div>

      {/* Lista de Candidatos */}
      <div className="space-y-3 mb-5">
        {candidates.length === 0 ? (
          <div className="p-6 text-center border-2 border-dashed border-slate-300 rounded-lg text-slate-400 text-xs">
            Sin candidatos registrados en esta circunscripción.
          </div>
        ) : (
          candidates
            .sort((a, b) => a.ballot_order - b.ballot_order)
            .map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between p-3 bg-white rounded-lg border border-slate-300/80 shadow-xs hover:border-civic-navy/50 transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div className="w-11 h-11 rounded-full bg-slate-100 border border-slate-200 overflow-hidden flex items-center justify-center shrink-0">
                    {c.photo_url ? (
                      <img src={c.photo_url} alt={c.name} className="w-full h-full object-cover" />
                    ) : (
                      <span className="text-slate-400 text-base font-bold">👤</span>
                    )}
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="w-5 h-5 rounded-full bg-slate-100 border border-slate-300 text-slate-700 font-mono text-xs font-bold flex items-center justify-center">
                        {c.ballot_order}
                      </span>
                      <span className="font-serif font-bold text-sm text-slate-900 leading-snug">
                        {c.name}
                      </span>
                    </div>
                    {c.party_or_front && (
                      <div className="text-2xs font-semibold text-slate-500 uppercase mt-0.5">
                        {c.party_or_front}
                      </div>
                    )}
                  </div>
                </div>

                {/* Casilla de marcación */}
                <div className="w-8 h-8 rounded border-2 border-slate-400 flex items-center justify-center bg-[#FAF8F5] shrink-0">
                  <div className="w-2 h-2 rounded-xs bg-slate-300/40"></div>
                </div>
              </div>
            ))
        )}

        {/* Casillas Institucionales: Voto en Blanco y Voto Nulo */}
        {allowBlank && (
          <div className="flex items-center justify-between p-3 bg-white/70 rounded-lg border border-slate-300/60 shadow-xs">
            <div className="flex items-center space-x-3">
              <span className="w-11 h-11 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 font-mono text-xs">
                ⚪
              </span>
              <div>
                <span className="font-serif font-bold text-sm text-slate-700">Voto en Blanco</span>
                <p className="text-2xs text-slate-500">Dejar sin preferencia este cargo</p>
              </div>
            </div>
            <div className="w-8 h-8 rounded border-2 border-slate-300 flex items-center justify-center bg-[#FAF8F5] shrink-0"></div>
          </div>
        )}

        {allowNull && (
          <div className="flex items-center justify-between p-3 bg-white/70 rounded-lg border border-slate-300/60 shadow-xs">
            <div className="flex items-center space-x-3">
              <span className="w-11 h-11 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 font-mono text-xs">
                ✖️
              </span>
              <div>
                <span className="font-serif font-bold text-sm text-slate-700">Voto Nulo</span>
                <p className="text-2xs text-slate-500">Anular deliberadamente la papeleta</p>
              </div>
            </div>
            <div className="w-8 h-8 rounded border-2 border-slate-300 flex items-center justify-center bg-[#FAF8F5] shrink-0"></div>
          </div>
        )}
      </div>

      {/* Pie de seguridad criptográfica */}
      <div className="pt-3 border-t border-slate-300/60 flex items-center justify-between text-2xs text-slate-400 font-mono">
        <span>SERIE: SEC-2026-VS</span>
        <span>AUDITORÍA: NULLIFIER-ACTIVE</span>
      </div>
    </div>
  );
};
