import React from 'react';
import { ShieldCheck, ShieldAlert, Award } from 'lucide-react';
import type { ElectionStatus } from '@votoseguro/api-client';

interface SealStatusStampProps {
  status: ElectionStatus;
}

export const SealStatusStamp: React.FC<SealStatusStampProps> = ({ status }) => {
  const getStampConfig = () => {
    switch (status) {
      case 'DRAFT':
        return {
          title: 'ESTRUCTURA EN BORRADOR',
          desc: 'Configuración de jerarquías y candidatos editable',
          border: 'border-stone-400',
          bg: 'bg-stone-50',
          text: 'text-stone-700',
          icon: <Award className="w-5 h-5 text-stone-600" />,
        };
      case 'SCHEDULED':
        return {
          title: 'ELECCIÓN PROGRAMADA',
          desc: 'Estructura congelada bajo sello criptográfico',
          border: 'border-amber-500',
          bg: 'bg-amber-50/50',
          text: 'text-amber-800',
          icon: <ShieldCheck className="w-5 h-5 text-seal-amber" />,
        };
      case 'REGISTRATION_OPEN':
        return {
          title: 'REGISTRO DE ELECTORES ACTIVO',
          desc: 'Ventana de empadronamiento habilitada',
          border: 'border-seal-emerald',
          bg: 'bg-emerald-50/60',
          text: 'text-seal-emerald',
          icon: <ShieldCheck className="w-5 h-5 text-seal-emerald" />,
        };
      case 'REGISTRATION_CLOSED':
        return {
          title: 'PADRÓN ELECTORAL CONGELADO',
          desc: 'Padrón inmutable con hash de verificación emitido',
          border: 'border-civic-navy-800',
          bg: 'bg-civic-navy-950 text-white',
          text: 'text-stone-200',
          icon: <ShieldCheck className="w-5 h-5 text-seal-emerald" />,
        };
      case 'VOTING_OPEN':
        return {
          title: 'CABINA ELECTORAL ABIERTA',
          desc: 'Emisión atómica de sufragios en curso',
          border: 'border-seal-emerald',
          bg: 'bg-emerald-50/60',
          text: 'text-seal-emerald',
          icon: <ShieldCheck className="w-5 h-5 text-seal-emerald" />,
        };
      case 'VOTING_CLOSED':
      case 'TALLIED':
        return {
          title: 'VOTACIÓN FINALIZADA',
          desc: 'Recepción bloqueada · Escrutinio habilitado',
          border: 'border-civic-navy-900',
          bg: 'bg-stone-100',
          text: 'text-civic-navy-900',
          icon: <ShieldCheck className="w-5 h-5 text-civic-navy-900" />,
        };
      case 'CANCELLED':
      default:
        return {
          title: 'PROCESO ANULADO',
          desc: 'Fase cancelada administrativamente',
          border: 'border-seal-crimson',
          bg: 'bg-red-50',
          text: 'text-seal-crimson',
          icon: <ShieldAlert className="w-5 h-5 text-seal-crimson" />,
        };
    }
  };

  const config = getStampConfig();

  return (
    <div
      className={`border-2 border-dashed ${config.border} ${config.bg} rounded-xl p-4 flex items-center space-x-3.5 shadow-seal`}
    >
      <div className="shrink-0">{config.icon}</div>
      <div>
        <h4 className={`text-xs font-bold tracking-wider font-mono uppercase ${config.text}`}>
          {config.title}
        </h4>
        <p className="text-[11px] text-stone-500 font-sans mt-0.5">{config.desc}</p>
      </div>
    </div>
  );
};
