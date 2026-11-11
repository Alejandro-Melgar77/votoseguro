import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Shield, Send, CheckCircle2, AlertCircle, Building, Calendar, Mail, User, Phone, FileText } from 'lucide-react';
import { api } from '@/lib/api';
import type { ElectionRequestCreate, OrganizationType } from '@votoseguro/api-client';

export const PublicLandingRequestPage: React.FC = () => {
  const [formData, setFormData] = useState<ElectionRequestCreate>({
    organization_name: '',
    org_type: 'UNIVERSITY',
    requester_name: '',
    contact_email: '',
    contact_phone: '',
    desired_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0] as any,
    description: '',
  });

  const [isLoading, setIsLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      await api.post('/public/election-requests', {
        ...formData,
        desired_date: new Date(formData.desired_date).toISOString(),
      });
      setSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'Error al enviar la solicitud.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ballot-ivory-100 flex flex-col font-sans">
      {/* Barra de cabecera */}
      <header className="bg-civic-navy-950 border-b border-civic-navy-800 text-white px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded bg-seal-emerald/20 border border-seal-emerald/40 flex items-center justify-center text-seal-emerald font-bold">
            VS
          </div>
          <div>
            <h1 className="font-title text-base font-bold tracking-wide">VotoSeguro</h1>
            <p className="text-[10px] text-stone-400 font-mono">Infraestructura Electoral SaaS</p>
          </div>
        </div>

        <Link
          to="/login"
          className="px-4 py-2 bg-civic-navy-800 hover:bg-civic-navy-700 text-xs font-semibold rounded-lg text-white transition-colors border border-civic-navy-700 shadow-sm"
        >
          Acceso Institucional
        </Link>
      </header>

      {/* Contenido Hero + Formulario */}
      <main className="flex-1 max-w-4xl mx-auto w-full p-6 sm:p-10 space-y-10">
        <div className="text-center space-y-3">
          <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-100 border border-emerald-300 text-seal-emerald text-xs font-semibold">
            <Shield className="w-3.5 h-3.5" />
            <span>Soberanía Cívica y Criptografía Transparente</span>
          </div>
          <h2 className="font-title text-3xl sm:text-4xl font-bold text-civic-navy-900">
            Solicite su Proceso Electoral Institucional
          </h2>
          <p className="text-stone-600 text-sm max-w-2xl mx-auto leading-relaxed">
            Universidades, colegios profesionales, municipios y organizaciones pueden gestionar sus elecciones con padrón auditable, papeletas dinámicas y secreto de voto respaldado matemáticamente.
          </p>
        </div>

        {submitted ? (
          <div className="bg-white border border-stone-300 rounded-2xl p-8 sm:p-10 text-center space-y-4 shadow-electoral max-w-xl mx-auto">
            <div className="w-14 h-14 bg-emerald-100 text-seal-emerald rounded-full flex items-center justify-center mx-auto">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h3 className="font-title text-xl font-bold text-civic-navy-900">
              Solicitud Registrada Exitosamente
            </h3>
            <p className="text-xs text-stone-600 leading-relaxed">
              Hemos recibido la postulación de su institución. El Operador Central revisará los antecedentes y se pondrá en contacto a través de <span className="font-mono font-semibold text-civic-navy-900">{formData.contact_email}</span> para proveer las credenciales de Administrador General.
            </p>
            <div className="pt-4">
              <button
                onClick={() => setSubmitted(false)}
                className="text-xs font-semibold text-seal-emerald hover:underline"
              >
                Enviar otra solicitud institucional
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-white border border-stone-300 rounded-2xl p-6 sm:p-10 shadow-electoral">
            <div className="border-b border-stone-200 pb-4 mb-6">
              <h3 className="font-title text-lg font-bold text-civic-navy-900">
                Formulario de Solicitud de Elección (RF-04 / S1-12)
              </h3>
              <p className="text-xs text-stone-500">
                Complete los datos de la institución interesada para habilitar un espacio tenant aislado.
              </p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-seal-crimson-light border border-seal-crimson text-seal-crimson-dark text-xs rounded-xl flex items-start space-x-2.5">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                <div>
                  <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                    Nombre Oficial de la Institución
                  </label>
                  <div className="relative">
                    <Building className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                    <input
                      type="text"
                      placeholder="Ej. Universidad EL GRAN ESTUDIO"
                      value={formData.organization_name}
                      onChange={(e) =>
                        setFormData({ ...formData, organization_name: e.target.value })
                      }
                      className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                    Tipo de Organización
                  </label>
                  <select
                    value={formData.org_type}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        org_type: e.target.value as OrganizationType,
                      })
                    }
                    className="w-full text-xs rounded-lg border border-stone-300 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                  >
                    <option value="UNIVERSITY">Universidad / Centro Académico</option>
                    <option value="MUNICIPALITY">Municipio / Gobierno Local</option>
                    <option value="NATIONAL">Elección Nacional / Regional</option>
                    <option value="CORPORATE">Colegio Profesional / Empresa</option>
                    <option value="COOPERATIVE">Cooperativa / Asociación</option>
                    <option value="OTHER">Otra Entidad</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                    Nombre del Representante o Solicitante
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                    <input
                      type="text"
                      placeholder="Ej. Dr. Mario Aguilera"
                      value={formData.requester_name}
                      onChange={(e) =>
                        setFormData({ ...formData, requester_name: e.target.value })
                      }
                      className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                    Correo Electrónico Institucional
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                    <input
                      type="email"
                      placeholder="contacto@institucion.edu"
                      value={formData.contact_email}
                      onChange={(e) =>
                        setFormData({ ...formData, contact_email: e.target.value })
                      }
                      className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                    Teléfono de Contacto (Opcional)
                  </label>
                  <div className="relative">
                    <Phone className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                    <input
                      type="tel"
                      placeholder="+591 70000000"
                      value={formData.contact_phone || ''}
                      onChange={(e) =>
                        setFormData({ ...formData, contact_phone: e.target.value })
                      }
                      className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                    Fecha Estimada de la Elección
                  </label>
                  <div className="relative">
                    <Calendar className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                    <input
                      type="date"
                      value={formData.desired_date as any}
                      onChange={(e) =>
                        setFormData({ ...formData, desired_date: e.target.value as any })
                      }
                      className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                      required
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-civic-navy-900 mb-1.5">
                  Descripción del Proceso Electoral o Cargos a Elegir
                </label>
                <div className="relative">
                  <FileText className="w-4 h-4 text-stone-400 absolute left-3 top-3" />
                  <textarea
                    rows={3}
                    placeholder="Ej. Elección de Rectorado, Decanaturas y Direcciones de Carrera para el periodo 2026-2030..."
                    value={formData.description || ''}
                    onChange={(e) =>
                      setFormData({ ...formData, description: e.target.value })
                    }
                    className="w-full text-xs rounded-lg border border-stone-300 pl-9 p-2.5 focus:ring-2 focus:ring-civic-navy-800"
                  />
                </div>
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3 bg-civic-navy-900 hover:bg-civic-navy-800 text-white font-semibold text-xs rounded-xl shadow-md transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  <span>{isLoading ? 'Registrando...' : 'Enviar Solicitud de Elección'}</span>
                </button>
              </div>
            </form>
          </div>
        )}
      </main>

      <footer className="bg-civic-navy-950 text-stone-400 text-xs py-6 text-center border-t border-civic-navy-800">
        <p>© 2026 VotoSeguro — Plataforma de Votación Electrónica. INF 422 SB (UAGRM).</p>
      </footer>
    </div>
  );
};
