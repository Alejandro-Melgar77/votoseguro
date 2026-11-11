import React, { useState } from 'react';
import { UnitNode, HierarchyLevel, NodeImportResult } from '@votoseguro/api-client';
import { api } from '@/lib/api';

interface HierarchyTreeExplorerProps {
  groupId: string;
  levels: HierarchyLevel[];
  nodes: UnitNode[];
  isDraft: boolean;
  onRefresh: () => void;
}

export const HierarchyTreeExplorer: React.FC<HierarchyTreeExplorerProps> = ({
  groupId,
  levels,
  nodes,
  isDraft,
  onRefresh,
}) => {
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [selectedParentId, setSelectedParentId] = useState<string | null>(null);
  const [selectedLevelId, setSelectedLevelId] = useState<string>('');
  const [nodeName, setNodeName] = useState('');
  const [nodeCode, setNodeCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Estado para modal CSV
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState<NodeImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  const openAddChildModal = (parentNode?: UnitNode) => {
    setFormError(null);
    setNodeName('');
    setNodeCode('');
    if (parentNode) {
      setSelectedParentId(parentNode.id);
      const nextLevel = levels.find((l) => l.depth === parentNode.depth + 1);
      setSelectedLevelId(nextLevel ? nextLevel.id : '');
    } else {
      setSelectedParentId(null);
      const rootLevel = levels.find((l) => l.depth === 1);
      setSelectedLevelId(rootLevel ? rootLevel.id : '');
    }
    setShowAddModal(true);
  };

  const handleCreateNode = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    if (!nodeName.trim() || !nodeCode.trim() || !selectedLevelId) {
      setFormError('Por favor complete todos los campos obligatorios.');
      return;
    }

    try {
      setSubmitting(true);
      await api.post(`/groups/${groupId}/nodes`, {
        level_id: selectedLevelId,
        parent_id: selectedParentId || null,
        name: nodeName.trim(),
        code: nodeCode.trim().toUpperCase(),
      });
      setShowAddModal(false);
      onRefresh();
    } catch (err: any) {
      setFormError(err.message || 'Error al crear el nodo.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteNode = async (nodeId: string, nodeName: string) => {
    if (!window.confirm(`¿Está seguro de eliminar el nodo '${nodeName}'? Esta acción no se puede deshacer.`)) {
      return;
    }
    try {
      await api.delete(`/nodes/${nodeId}`);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'No se pudo eliminar el nodo.');
    }
  };

  const handleImportCsv = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!csvFile) return;
    setImportError(null);
    setImportResult(null);

    const formData = new FormData();
    formData.append('file', csvFile);

    try {
      setImporting(true);
      const res = await api.post<NodeImportResult>(`/groups/${groupId}/nodes/import`, formData);
      setImportResult(res);
      onRefresh();
    } catch (err: any) {
      setImportError(err.message || 'Error al procesar el archivo CSV.');
    } finally {
      setImporting(false);
    }
  };

  const downloadSampleCsv = () => {
    const csvContent =
      'code,name,level_depth,parent_code\n' +
      'UNIV,Universidad Autonoma,1,\n' +
      'FICCT,Facultad de Tecnologia,2,UNIV\n' +
      'FCE,Facultad de Economicas,2,UNIV\n' +
      'INF,Ingenieria Informatica,3,FICCT\n' +
      'SIS,Ingenieria de Sistemas,3,FICCT\n' +
      'ECO,Licenciatura en Economia,3,FCE\n';
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'plantilla_nodos_jerarquicos.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Renderizar árbol recursivo o plano indentado
  const renderNodeRows = (nodesList: UnitNode[], parentId: string | null = null, depth = 0): React.ReactNode => {
    const currentNodes = nodesList.filter((n) => n.parent_id === parentId);
    if (currentNodes.length === 0) return null;

    return currentNodes.map((node) => {
      const level = levels.find((l) => l.id === node.level_id);
      const canHaveChildren = depth + 1 < levels.length;

      return (
        <React.Fragment key={node.id}>
          <tr className="hover:bg-slate-50/80 transition-colors border-b border-slate-100">
            <td className="py-3 px-4">
              <div className="flex items-center space-x-2" style={{ paddingLeft: `${depth * 28}px` }}>
                <span className="text-slate-400 font-mono text-xs select-none">
                  {depth === 0 ? '🏛️' : depth === 1 ? '🏢' : '🎓'}
                </span>
                <span className="font-semibold text-slate-900 text-sm">{node.name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-slate-200 text-slate-700 font-mono font-bold">
                  {node.code}
                </span>
              </div>
            </td>
            <td className="py-3 px-4">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-civic-navy/10 text-civic-navy border border-civic-navy/20">
                Nivel {node.depth}: {level ? level.name : `Profundidad ${node.depth}`}
              </span>
            </td>
            <td className="py-3 px-4 font-mono text-xs text-slate-600">
              <span className="bg-slate-100 px-2 py-1 rounded border border-slate-200 select-all">
                {node.path}
              </span>
            </td>
            <td className="py-3 px-4 text-right space-x-2 whitespace-nowrap">
              {isDraft && canHaveChildren && (
                <button
                  type="button"
                  onClick={() => openAddChildModal(node)}
                  className="inline-flex items-center text-xs font-semibold px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
                >
                  + Sub-nodo
                </button>
              )}
              {isDraft && (
                <button
                  type="button"
                  onClick={() => handleDeleteNode(node.id, node.name)}
                  className="inline-flex items-center text-xs font-semibold px-2 py-1 rounded hover:bg-red-50 text-red-600 transition"
                  title="Eliminar nodo"
                >
                  🗑️
                </button>
              )}
            </td>
          </tr>
          {renderNodeRows(nodesList, node.id, depth + 1)}
        </React.Fragment>
      );
    });
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Cabecera de la sección */}
      <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-serif text-lg font-bold text-civic-navy flex items-center space-x-2">
            <span>Árbol Territorial y Organizacional</span>
            <span className="text-xs bg-civic-navy/10 text-civic-navy font-sans px-2.5 py-0.5 rounded-full font-semibold">
              {nodes.length} Nodos
            </span>
          </h3>
          <p className="text-xs text-slate-600 mt-0.5">
            Estructura jerárquica con rutas materializadas deterministas para cálculo de padrón y circunscripciones.
          </p>
        </div>

        {isDraft && (
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={downloadSampleCsv}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm transition flex items-center space-x-1"
            >
              <span>📥 Plantilla CSV</span>
            </button>
            <button
              type="button"
              onClick={() => {
                setCsvFile(null);
                setImportResult(null);
                setImportError(null);
                setShowImportModal(true);
              }}
              className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm transition flex items-center space-x-1"
            >
              <span>📂 Importar CSV</span>
            </button>
            <button
              type="button"
              onClick={() => openAddChildModal()}
              className="px-3 py-1.5 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800 shadow-sm transition flex items-center space-x-1"
            >
              <span>+ Nuevo Nodo Raíz</span>
            </button>
          </div>
        )}
      </div>

      {/* Tabla del Árbol */}
      {nodes.length === 0 ? (
        <div className="p-12 text-center">
          <div className="text-4xl mb-3">🌳</div>
          <h4 className="font-serif text-slate-800 font-bold mb-1">Árbol de Nodos Vacío</h4>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-4">
            Comience agregando el nodo de mayor jerarquía (Nivel 1) o importe la estructura completa mediante un archivo CSV.
          </p>
          {isDraft && (
            <div className="space-x-3">
              <button
                type="button"
                onClick={() => openAddChildModal()}
                className="px-4 py-2 text-sm font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800 transition"
              >
                + Crear Nodo Raíz (Nivel 1)
              </button>
              <button
                type="button"
                onClick={() => setShowImportModal(true)}
                className="px-4 py-2 text-sm font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition"
              >
                Importar CSV
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-100/60 text-xs font-bold text-slate-600 uppercase tracking-wider border-b border-slate-200">
                <th className="py-2.5 px-4">Nodo / Unidad</th>
                <th className="py-2.5 px-4">Nivel Jerárquico</th>
                <th className="py-2.5 px-4">Ruta Materializada (Path)</th>
                <th className="py-2.5 px-4 text-right">Acciones</th>
              </tr>
            </thead>
            <tbody>{renderNodeRows(nodes, null, 0)}</tbody>
          </table>
        </div>
      )}

      {/* Modal para Crear / Añadir Nodo */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-md overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
              <h4 className="font-serif font-bold text-civic-navy text-base">
                {selectedParentId ? 'Agregar Sub-nodo Hijo' : 'Crear Nodo Raíz'}
              </h4>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleCreateNode} className="p-6 space-y-4">
              {formError && (
                <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                  {formError}
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Nivel Jerárquico</label>
                <select
                  value={selectedLevelId}
                  onChange={(e) => setSelectedLevelId(e.target.value)}
                  disabled={!!selectedParentId}
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 bg-slate-50 disabled:bg-slate-100"
                >
                  <option value="">Seleccione el nivel...</option>
                  {levels.map((lvl) => (
                    <option key={lvl.id} value={lvl.id}>
                      Nivel {lvl.depth}: {lvl.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Nombre Completo del Nodo</label>
                <input
                  type="text"
                  value={nodeName}
                  onChange={(e) => setNodeName(e.target.value)}
                  placeholder="Ej. Facultad de Tecnología"
                  required
                  className="w-full text-sm border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-civic-navy/20 focus:border-civic-navy"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Código Corto (Identificador en Ruta)
                </label>
                <input
                  type="text"
                  value={nodeCode}
                  onChange={(e) => setNodeCode(e.target.value.toUpperCase())}
                  placeholder="Ej. FICCT"
                  required
                  className="w-full text-sm font-mono uppercase border border-slate-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-civic-navy/20 focus:border-civic-navy"
                />
                <p className="text-2xs text-slate-500 mt-1">
                  Se utilizará para componer la ruta materializada única (ej. <code className="bg-slate-100 px-1">/FICCT/</code>).
                </p>
              </div>

              <div className="pt-2 flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800 disabled:opacity-50 transition"
                >
                  {submitting ? 'Guardando...' : 'Crear Nodo'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal para Importación CSV */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            <div className="px-6 py-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center">
              <h4 className="font-serif font-bold text-civic-navy text-base">
                Importación Masiva de Nodos Jerárquicos
              </h4>
              <button
                type="button"
                onClick={() => setShowImportModal(false)}
                className="text-slate-400 hover:text-slate-600 text-lg font-bold"
              >
                &times;
              </button>
            </div>
            <form onSubmit={handleImportCsv} className="p-6 space-y-4">
              <p className="text-xs text-slate-600 leading-relaxed">
                El archivo CSV debe incluir las columnas <code className="bg-slate-100 font-mono px-1">code</code>,{' '}
                <code className="bg-slate-100 font-mono px-1">name</code>,{' '}
                <code className="bg-slate-100 font-mono px-1">level_depth</code> y{' '}
                <code className="bg-slate-100 font-mono px-1">parent_code</code>. El sistema procesa las filas en orden
                topológico construyendo automáticamente la jerarquía.
              </p>

              {importError && (
                <div className="p-3 text-xs bg-red-50 text-red-700 border border-red-200 rounded-lg">
                  {importError}
                </div>
              )}

              {importResult && (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg space-y-2">
                  <div className="text-xs font-bold text-emerald-800 flex items-center space-x-1">
                    <span>✅ Procesamiento completado:</span>
                    <span>{importResult.created_nodes} nodos creados de {importResult.total_rows} filas.</span>
                  </div>
                  {importResult.errors.length > 0 && (
                    <div className="mt-2 text-xs text-amber-900">
                      <div className="font-bold mb-1">Advertencias / Errores en filas:</div>
                      <div className="max-h-36 overflow-y-auto space-y-1 bg-white p-2 rounded border border-amber-200 font-mono text-2xs">
                        {importResult.errors.map((err, i) => (
                          <div key={i} className="text-red-700">
                            Fila {err.row} [{err.code}]: {err.message}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">Seleccionar archivo CSV</label>
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setCsvFile(e.target.files ? e.target.files[0] : null)}
                  required
                  className="w-full text-xs text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-civic-navy file:text-white hover:file:bg-slate-800 border border-slate-200 rounded-lg p-1"
                />
              </div>

              <div className="pt-2 flex justify-between items-center">
                <button
                  type="button"
                  onClick={downloadSampleCsv}
                  className="text-xs text-civic-navy hover:underline font-semibold"
                >
                  📥 Descargar Plantilla CSV
                </button>
                <div className="space-x-2">
                  <button
                    type="button"
                    onClick={() => setShowImportModal(false)}
                    className="px-4 py-2 text-xs font-semibold text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition"
                  >
                    Cerrar
                  </button>
                  <button
                    type="submit"
                    disabled={importing || !csvFile}
                    className="px-4 py-2 text-xs font-semibold text-white bg-civic-navy rounded-lg hover:bg-slate-800 disabled:opacity-50 transition"
                  >
                    {importing ? 'Procesando...' : 'Iniciar Importación'}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
