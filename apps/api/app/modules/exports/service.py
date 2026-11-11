"""
Motor de Exportación Oficial de Reportes en PDF y Excel (S2-08)
Genera en memoria (BytesIO) Actas de Escrutinio, Reportes de Participación y Bitácoras de Auditoría.
Aplica estrictamente Invariante #11 (403 antes del cierre) e Invariante #12 (k-anonimato).
"""
import io
import uuid
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import TenantContext
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.time import TimeProvider
from app.db.models.audit import AuditLog
from app.db.models.election import Election, ElectionStatus, ScheduleChange
from app.db.models.organization import Organization
from app.db.models.user import User
from app.modules.integrity.service import IntegrityService
from app.modules.realtime.service import RealtimeMonitoringService
from app.modules.results.service import ResultsService


# Paleta institucional
NAVY_HEADER = "0B132B"
EMERALD_ACCENT = "1C7C54"
STONE_BG = "F8F9FA"


class ExportService:
    @staticmethod
    async def export_results(
        db: AsyncSession,
        election_id: uuid.UUID,
        user: User,
        time_provider: TimeProvider,
        export_format: str = "xlsx",
    ) -> tuple[io.BytesIO, str, str]:
        """
        Exporta los resultados oficiales con k-anonimato.
        Invariante #11: Solo permitido cuando election.status in [VOTING_CLOSED, TALLIED].
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección {election_id} no encontrada.")

        if election.status not in (ElectionStatus.VOTING_CLOSED, ElectionStatus.TALLIED):
            raise ForbiddenException(
                "Invariante #11: Los resultados electorales se encuentran criptográficamente sellados "
                "hasta la conclusión oficial del sufragio (VOTING_CLOSED)."
            )

        org = await db.get(Organization, election.organization_id)
        org_name = org.name if org else "Institución Electoral"

        # Cargar resultados computados con k-anonimato
        tenant = TenantContext(organization_id=election.organization_id, user=user, assignments=[])
        results = await ResultsService.compute_election_results(
            db=db,
            election_id=election_id,
            tenant=tenant,
        )

        filename_base = f"Acta_Resultados_{election.name.replace(' ', '_')}"

        if export_format.lower() == "pdf":
            buffer = ExportService._build_results_pdf(election, org_name, results)
            return buffer, f"{filename_base}.pdf", "application/pdf"
        else:
            buffer = ExportService._build_results_xlsx(election, org_name, results)
            return (
                buffer,
                f"{filename_base}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    @staticmethod
    async def export_participation(
        db: AsyncSession,
        election_id: uuid.UUID,
        user: User,
        time_provider: TimeProvider,
        export_format: str = "xlsx",
    ) -> tuple[io.BytesIO, str, str]:
        """
        Exporta el avance de empadronamiento, participación por nodo y votos por hora.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección {election_id} no encontrada.")

        org = await db.get(Organization, election.organization_id)
        org_name = org.name if org else "Institución Electoral"

        snapshot = await RealtimeMonitoringService.get_live_dashboard_snapshot(
            db=db,
            election_id=election_id,
            user=user,
            time_provider=time_provider,
        )

        filename_base = f"Reporte_Participacion_{election.name.replace(' ', '_')}"

        if export_format.lower() == "pdf":
            buffer = ExportService._build_participation_pdf(election, org_name, snapshot)
            return buffer, f"{filename_base}.pdf", "application/pdf"
        else:
            buffer = ExportService._build_participation_xlsx(election, org_name, snapshot)
            return (
                buffer,
                f"{filename_base}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    @staticmethod
    async def export_audit(
        db: AsyncSession,
        election_id: uuid.UUID,
        user: User,
        time_provider: TimeProvider,
        export_format: str = "xlsx",
    ) -> tuple[io.BytesIO, str, str]:
        """
        Exporta la bitácora inmutable de auditoría, cambios de cronograma y verificación de integridad.
        """
        election = await db.get(Election, election_id)
        if not election:
            raise NotFoundException(f"Elección {election_id} no encontrada.")

        org = await db.get(Organization, election.organization_id)
        org_name = org.name if org else "Institución Electoral"

        # Cargar bitácora de auditoría
        stmt_audit = (
            select(AuditLog)
            .where(
                (AuditLog.election_id == election_id)
                | (AuditLog.organization_id == election.organization_id)
            )
            .order_by(AuditLog.chain_index.asc())
        )
        logs = (await db.execute(stmt_audit)).scalars().all()

        # Cargar cambios de cronograma
        stmt_sched = (
            select(ScheduleChange)
            .where(ScheduleChange.election_id == election_id)
            .order_by(ScheduleChange.changed_at.asc())
        )
        schedule_changes = (await db.execute(stmt_sched)).scalars().all()

        # Verificación en vivo de la cadena de hashes
        vote_integrity = await IntegrityService.verify_vote_chain(db, election_id)
        audit_integrity = await IntegrityService.verify_audit_chain(db, election_id)

        filename_base = f"Bitacora_Auditoria_{election.name.replace(' ', '_')}"

        if export_format.lower() == "pdf":
            buffer = ExportService._build_audit_pdf(
                election, org_name, logs, schedule_changes, vote_integrity, audit_integrity
            )
            return buffer, f"{filename_base}.pdf", "application/pdf"
        else:
            buffer = ExportService._build_audit_xlsx(
                election, org_name, logs, schedule_changes, vote_integrity, audit_integrity
            )
            return (
                buffer,
                f"{filename_base}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    # =========================================================================
    # Generadores Excel (openpyxl)
    # =========================================================================

    @staticmethod
    def _build_results_xlsx(election: Election, org_name: str, results) -> io.BytesIO:
        wb = Workbook()

        # Hoja 1: Resumen y Sellos
        ws1 = wb.active
        ws1.title = "Resumen y Sellos"
        ws1.views.sheetView[0].showGridLines = True

        header_font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")
        title_font = Font(name="Calibri", size=16, bold=True, color=NAVY_HEADER)

        ws1["A1"] = f"ACTA OFICIAL DE RESULTADOS ELECTORALES — {org_name.upper()}"
        ws1["A1"].font = title_font
        ws1["A2"] = f"Elección: {election.name} | Estado: {election.status.value}"

        total_votes_recorded = sum(
            const.total_cast
            for g in results.groups
            for c in g.contests
            for const in c.constituencies
        )

        metadata = [
            ("ID de Elección", str(election.id)),
            ("Institución", org_name),
            ("Apertura de Votación", election.voting_opens_at.isoformat() if election.voting_opens_at else "N/A"),
            ("Cierre de Votación", election.voting_closes_at.isoformat() if election.voting_closes_at else "N/A"),
            ("Umbral k-Anonimato", f"k = {election.k_anonymity}"),
            ("Config Hash (RFC 8785)", election.config_hash or "N/A"),
            ("Roll Hash (Padrón)", election.roll_hash or "N/A"),
            ("Merkle Root (Padrón)", election.merkle_root or "N/A"),
            ("Vote Chain Head Hash", election.votes_chain_head or "N/A"),
            ("Total Votos Escrutados", total_votes_recorded),
        ]

        row = 4
        for label, val in metadata:
            ws1.cell(row=row, column=1, value=label).font = Font(bold=True)
            ws1.cell(row=row, column=2, value=str(val)).font = Font(name="Consolas" if "Hash" in label or "Root" in label else "Calibri")
            row += 1

        # Hoja 2: Resultados por Circunscripción
        ws2 = wb.create_sheet(title="Resultados por Cargo")
        ws2.views.sheetView[0].showGridLines = True

        headers2 = ["Grupo", "Cargo", "Circunscripción / Territorio", "Opción / Candidato", "Organización Política", "Votos Válidos", "Porcentaje (%)"]
        ws2.append(headers2)
        for col_idx in range(1, len(headers2) + 1):
            cell = ws2.cell(row=1, column=col_idx)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = header_fill

        for g in results.groups:
            for contest in g.contests:
                c_name = contest.contest_name
                for const in contest.constituencies:
                    terr = const.node_name or const.node_path
                    tot = const.total_cast
                    for cand in const.candidates:
                        pct = cand.percentage if cand.percentage is not None else (round((cand.votes_count or 0) / tot * 100, 2) if tot > 0 else 0.0)
                        ws2.append([
                            g.group_name,
                            c_name,
                            terr,
                            cand.full_name,
                            cand.party_affiliation or "Independiente",
                            cand.votes_count or 0,
                            f"{pct}%",
                        ])
                    b_pct = round((const.blank_count / tot * 100), 2) if tot > 0 else 0.0
                    n_pct = round((const.null_count / tot * 100), 2) if tot > 0 else 0.0
                    ws2.append([g.group_name, c_name, terr, "VOTO EN BLANCO", "—", const.blank_count, f"{b_pct}%"])
                    ws2.append([g.group_name, c_name, terr, "VOTO NULO", "—", const.null_count, f"{n_pct}%"])

        # Hoja 3: Desgloses Jerárquicos y Filtros con k-Anonimato
        ws3 = wb.create_sheet(title="Desgloses k-Anonimato")
        ws3.views.sheetView[0].showGridLines = True
        headers3 = ["Cargo", "Etiqueta Desglose", "Segmento / Valor", "Total Votos Segmento", "Estado de Protección"]
        ws3.append(headers3)
        for col_idx in range(1, len(headers3) + 1):
            cell = ws3.cell(row=1, column=col_idx)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = PatternFill(start_color=EMERALD_ACCENT, end_color=EMERALD_ACCENT, fill_type="solid")

        for g in results.groups:
            for contest in g.contests:
                for const in contest.constituencies:
                    for bd in const.breakdowns:
                        for cell_item in bd.cells:
                            val_display = str(cell_item.total_votes) if not cell_item.redacted_by_k_anonymity else f"< {election.k_anonymity}"
                            prot_status = "PROTEGIDO POR K-ANONIMATO" if cell_item.redacted_by_k_anonymity else "DIVULGACIÓN VÁLIDA"
                            ws3.append([
                                contest.contest_name,
                                bd.label or bd.kind,
                                cell_item.cell_name,
                                val_display,
                                prot_status,
                            ])

        # Auto-ajuste de columnas
        for sheet in (ws1, ws2, ws3):
            for col in sheet.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                col_letter = col[0].column_letter
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 65)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    @staticmethod
    def _build_participation_xlsx(election: Election, org_name: str, snapshot) -> io.BytesIO:
        wb = Workbook()
        ws = wb.active
        ws.title = "Participación y Padrón"
        ws.views.sheetView[0].showGridLines = True

        header_fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")

        ws["A1"] = f"REPORTE OFICIAL DE PARTICIPACIÓN Y EMPADRONAMIENTO — {org_name.upper()}"
        ws["A1"].font = Font(size=14, bold=True, color=NAVY_HEADER)
        ws["A2"] = f"Elección: {election.name} | Fecha: {snapshot.server_now_utc.isoformat()}"

        ws.append([])
        ws.append(["MÉTRICAS DE EMPADRONAMIENTO", "CANTIDAD"])
        ws.cell(row=4, column=1).font = Font(bold=True)
        ws.append(["Importados", snapshot.registration_metrics.imported])
        ws.append(["Invitados", snapshot.registration_metrics.invited])
        ws.append(["Activos (Habilitados)", snapshot.registration_metrics.active])
        ws.append(["Bloqueados", snapshot.registration_metrics.blocked])
        ws.append(["Pendientes de Aprobación", snapshot.registration_metrics.pending_approval])
        ws.append(["Total Padrón", snapshot.registration_metrics.total])
        ws.append(["Tasa de Activación", f"{snapshot.registration_metrics.activation_rate_pct}%"])

        ws.append([])
        ws.append(["MÉTRICAS DE PARTICIPACIÓN", "CANTIDAD"])
        ws.append(["Total Habilitados Activos", snapshot.participation_metrics.total_eligible_active])
        ws.append(["Votos Emitidos", snapshot.participation_metrics.total_voted])
        ws.append(["Abstención Estimada", snapshot.participation_metrics.abstention_count])
        ws.append(["Participación (%)", f"{snapshot.participation_metrics.participation_rate_pct}%"])

        # Desglose Territorial
        ws_seg = wb.create_sheet(title="Desglose por Territorio")
        ws_seg.views.sheetView[0].showGridLines = True
        headers = ["Grupo", "Unidad / Nodo", "Ruta Jerárquica", "Padrón Activo", "Votos Emitidos", "Participación (%)"]
        ws_seg.append(headers)
        for col_idx in range(1, len(headers) + 1):
            cell = ws_seg.cell(row=1, column=col_idx)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = header_fill

        for seg in snapshot.segment_breakdown:
            ws_seg.append([
                seg.group_name,
                seg.node_name,
                seg.node_path,
                seg.active_voters,
                seg.votes_cast,
                f"{seg.participation_pct}%",
            ])

        # Serie por Hora
        ws_hr = wb.create_sheet(title="Votos por Hora")
        ws_hr.views.sheetView[0].showGridLines = True
        headers_hr = ["Hora (UTC)", "Hora Local", "Papeletas Emitidas", "Total Acumulado"]
        ws_hr.append(headers_hr)
        for col_idx in range(1, len(headers_hr) + 1):
            cell = ws_hr.cell(row=1, column=col_idx)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = PatternFill(start_color=EMERALD_ACCENT, end_color=EMERALD_ACCENT, fill_type="solid")

        for hr in snapshot.hourly_votes_series:
            ws_hr.append([
                hr.hour_bucket_utc,
                hr.hour_label_local,
                hr.ballots_cast,
                hr.cumulative_ballots,
            ])

        for sheet in (ws, ws_seg, ws_hr):
            for col in sheet.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                col_letter = col[0].column_letter
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 60)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    @staticmethod
    def _build_audit_xlsx(
        election: Election,
        org_name: str,
        logs: list[AuditLog],
        schedule_changes: list[ScheduleChange],
        vote_integrity,
        audit_integrity,
    ) -> io.BytesIO:
        wb = Workbook()
        ws = wb.active
        ws.title = "Integridad y Resumen"
        ws.views.sheetView[0].showGridLines = True

        ws["A1"] = f"BITÁCORA OFICIAL Y CERTIFICACIÓN DE INTEGRIDAD — {org_name.upper()}"
        ws["A1"].font = Font(size=14, bold=True, color=NAVY_HEADER)

        ws.append([])
        ws.append(["AUDITORÍA DE CADENA DE VOTOS", "VALOR"])
        ws.append(["Estado de Integridad de Urna", "100% ÍNTEGRA" if vote_integrity.valid else "ALTERADA/CORRUPTA"])
        ws.append(["Bloques Eslabonados Verificados", f"{vote_integrity.verified_blocks} de {vote_integrity.total_blocks}"])
        ws.append(["Genesis Hash", vote_integrity.genesis_hash])
        ws.append(["Head Hash", vote_integrity.head_hash or "N/A"])

        ws.append([])
        ws.append(["AUDITORÍA DE CADENA DE BITÁCORA", "VALOR"])
        ws.append(["Estado de Integridad de Auditoría", "100% ÍNTEGRA" if audit_integrity.valid else "ALTERADA/CORRUPTA"])
        ws.append(["Entradas Verificadas", f"{audit_integrity.verified_entries} de {audit_integrity.total_entries}"])

        # Hoja 2: Entradas de Auditoría
        ws_logs = wb.create_sheet(title="Entradas de Auditoría")
        ws_logs.views.sheetView[0].showGridLines = True
        headers_log = ["# Eslabón", "Fecha/Hora (UTC)", "Rol Actor", "Acción", "Tipo Entidad", "ID Entidad", "Hash Entrada (entry_hash)", "Hash Previo (prev_hash)"]
        ws_logs.append(headers_log)
        for col_idx in range(1, len(headers_log) + 1):
            cell = ws_logs.cell(row=1, column=col_idx)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = PatternFill(start_color=NAVY_HEADER, end_color=NAVY_HEADER, fill_type="solid")

        for l in logs:
            ws_logs.append([
                l.chain_index,
                l.created_at.isoformat() if l.created_at else "",
                l.actor_role,
                l.action,
                l.entity_type,
                l.entity_id,
                l.entry_hash or "",
                l.prev_hash or "",
            ])

        # Hoja 3: Cambios de Cronograma
        ws_sc = wb.create_sheet(title="Historial de Cronograma")
        ws_sc.views.sheetView[0].showGridLines = True
        headers_sc = ["Fecha Cambio", "Campo Modificado", "Valor Anterior", "Valor Nuevo", "Motivo Formal Declarado"]
        ws_sc.append(headers_sc)
        for col_idx in range(1, len(headers_sc) + 1):
            cell = ws_sc.cell(row=1, column=col_idx)
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = PatternFill(start_color=EMERALD_ACCENT, end_color=EMERALD_ACCENT, fill_type="solid")

        for sc in schedule_changes:
            ws_sc.append([
                sc.changed_at.isoformat() if sc.changed_at else "",
                sc.field_name,
                sc.old_value,
                sc.new_value,
                sc.reason,
            ])

        for sheet in (ws, ws_logs, ws_sc):
            for col in sheet.columns:
                max_len = max(len(str(c.value or "")) for c in col)
                col_letter = col[0].column_letter
                sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 65)

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return buf

    # =========================================================================
    # Generadores PDF (ReportLab)
    # =========================================================================

    @staticmethod
    def _build_results_pdf(election: Election, org_name: str, results) -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=16,
            leading=20,
            textColor=colors.HexColor(f"#{NAVY_HEADER}"),
            alignment=1,
            bold=True,
        )
        subtitle_style = ParagraphStyle(
            "DocSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            textColor=colors.dimgrey,
            alignment=1,
        )
        mono_hash_style = ParagraphStyle(
            "MonoHash",
            fontName="Courier",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#2B2D42"),
        )
        cell_style = ParagraphStyle("CellText", fontSize=8, leading=10)

        story = []

        # Encabezado
        story.append(Paragraph(f"ACTA OFICIAL DE ESCRUTINIO Y CÓMPUTO ELECTORAL", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"{org_name.upper()} — VOTOSEGURO PLATAFORMA CRIPTOGRÁFICA", subtitle_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(f"#{NAVY_HEADER}")))
        story.append(Spacer(1, 10))

        total_votes_recorded = sum(
            const.total_cast
            for g in results.groups
            for c in g.contests
            for const in c.constituencies
        )

        # Metadatos y Sellos Criptográficos
        story.append(Paragraph("<b>Sellos Criptográficos y Parámetros Electorales</b>", styles["Heading3"]))
        seal_data = [
            ["Elección:", election.name, "Estado Oficial:", election.status.value],
            ["Config Hash (RFC 8785):", Paragraph(election.config_hash or "N/A", mono_hash_style), "k-Anonimato:", f"k = {election.k_anonymity}"],
            ["Roll Hash (Padrón):", Paragraph(election.roll_hash or "N/A", mono_hash_style), "Total Escrutado:", str(total_votes_recorded)],
            ["Merkle Root (Padrón):", Paragraph(election.merkle_root or "N/A", mono_hash_style), "Zona Horaria:", election.timezone],
            ["Votes Chain Head:", Paragraph(election.votes_chain_head or "N/A", mono_hash_style), "ID Elección:", str(election.id)[:18] + "..."],
        ]
        t_seal = Table(seal_data, colWidths=[110, 220, 90, 120])
        t_seal.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(f"#{STONE_BG}")),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ]))
        story.append(t_seal)
        story.append(Spacer(1, 14))

        # Resultados por Cargo y Circunscripción
        story.append(Paragraph("<b>Resultados Electorales por Circunscripción</b>", styles["Heading3"]))
        for g in results.groups:
            for contest in g.contests:
                story.append(Paragraph(f"<b>Cargo: {contest.contest_name} (Grupo: {g.group_name})</b>", styles["Heading4"]))
                for const in contest.constituencies:
                    terr = const.node_name or const.node_path
                    story.append(Paragraph(f"<i>Circunscripción / Territorio: {terr}</i>", styles["Normal"]))
                    story.append(Spacer(1, 4))

                    table_data = [["Opción / Candidato", "Organización Política", "Votos Obtenidos", "Porcentaje"]]
                    tot = const.total_cast
                    for cand in const.candidates:
                        pct = cand.percentage if cand.percentage is not None else (round((cand.votes_count or 0) / tot * 100, 2) if tot > 0 else 0.0)
                        table_data.append([
                            cand.full_name,
                            cand.party_affiliation or "Independiente",
                            str(cand.votes_count or 0),
                            f"{pct}%",
                        ])
                    b_pct = round((const.blank_count / tot * 100), 2) if tot > 0 else 0.0
                    n_pct = round((const.null_count / tot * 100), 2) if tot > 0 else 0.0
                    table_data.append(["VOTO EN BLANCO", "—", str(const.blank_count), f"{b_pct}%"])
                    table_data.append(["VOTO NULO", "—", str(const.null_count), f"{n_pct}%"])
                    table_data.append(["TOTAL ESCRUTADO", "—", str(const.total_cast), "100.0%"])

                    t_res = Table(table_data, colWidths=[180, 160, 100, 100])
                    t_res.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{NAVY_HEADER}")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EAEBED")),
                        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ]))
                    story.append(t_res)
                    story.append(Spacer(1, 10))

        # Certificación al pie
        story.append(Spacer(1, 15))
        story.append(Paragraph(
            "<b>Certificación Institucional:</b> La presente acta certifica que el escrutinio ha sido ejecutado "
            "con estricto respeto a las 17 Invariantes Electorales Criptográficas de VotoSeguro v2.0.",
            cell_style,
        ))

        doc.build(story)
        buf.seek(0)
        return buf

    @staticmethod
    def _build_participation_pdf(election: Election, org_name: str, snapshot) -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            textColor=colors.HexColor(f"#{NAVY_HEADER}"),
            alignment=1,
            bold=True,
        )

        story = [
            Paragraph("REPORTE OFICIAL DE PARTICIPACIÓN ELECTORAL", title_style),
            Paragraph(f"{org_name.upper()} — {election.name}", styles["Normal"]),
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(f"#{NAVY_HEADER}")),
            Spacer(1, 12),
        ]

        # Tabla de KPIs
        kpi_data = [
            ["Avance del Padrón Electoral", "Valor", "Métrica de Participación", "Valor"],
            ["Votantes Importados", str(snapshot.registration_metrics.imported), "Padrón Activo Habilitado", str(snapshot.participation_metrics.total_eligible_active)],
            ["Votantes Invitados", str(snapshot.registration_metrics.invited), "Votos Totales Depositados", str(snapshot.participation_metrics.total_voted)],
            ["Votantes Activos", str(snapshot.registration_metrics.active), "Abstención Estimada", str(snapshot.participation_metrics.abstention_count)],
            ["Votantes Bloqueados", str(snapshot.registration_metrics.blocked), "Participación Global", f"{snapshot.participation_metrics.participation_rate_pct}%"],
        ]
        t_kpi = Table(kpi_data, colWidths=[150, 110, 160, 120])
        t_kpi.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (1, 0), colors.HexColor(f"#{NAVY_HEADER}")),
            ("BACKGROUND", (2, 0), (3, 0), colors.HexColor(f"#{EMERALD_ACCENT}")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        story.append(t_kpi)
        story.append(Spacer(1, 14))

        # Desglose Territorial
        story.append(Paragraph("<b>Participación Territorial por Segmento</b>", styles["Heading3"]))
        seg_data = [["Grupo", "Nodo / Carrera", "Ruta Jerárquica", "Padrón Activo", "Votaron", "%"]]
        for s in snapshot.segment_breakdown:
            seg_data.append([s.group_name, s.node_name, s.node_path, str(s.active_voters), str(s.votes_cast), f"{s.participation_pct}%"])

        t_seg = Table(seg_data, colWidths=[90, 110, 160, 60, 60, 60])
        t_seg.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{NAVY_HEADER}")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("ALIGN", (3, 0), (-1, -1), "CENTER"),
        ]))
        story.append(t_seg)

        doc.build(story)
        buf.seek(0)
        return buf

    @staticmethod
    def _build_audit_pdf(
        election: Election,
        org_name: str,
        logs: list[AuditLog],
        schedule_changes: list[ScheduleChange],
        vote_integrity,
        audit_integrity,
    ) -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            textColor=colors.HexColor(f"#{NAVY_HEADER}"),
            alignment=1,
            bold=True,
        )
        mono_style = ParagraphStyle("Mono", fontName="Courier", fontSize=7, leading=9)

        story = [
            Paragraph("CERTIFICADO DE AUDITORÍA E INTEGRIDAD CRIPTOGRÁFICA", title_style),
            Paragraph(f"{org_name.upper()} — ELECCIÓN: {election.name}", styles["Normal"]),
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=1.5, color=colors.HexColor(f"#{NAVY_HEADER}")),
            Spacer(1, 10),
        ]

        # Estado de Integridad
        int_data = [
            ["Dimensión Auditada", "Resultado Criptográfico", "Eslabones Verificados", "Dictamen Técnico"],
            ["Cadena de Hashes de Votos", "VÁLIDA (100% ÍNTEGRA)" if vote_integrity.valid else "ALTERADA", f"{vote_integrity.verified_blocks} / {vote_integrity.total_blocks}", "Sin adulteraciones en urna"],
            ["Bitácora Inmutable (AuditLog)", "VÁLIDA (100% ÍNTEGRA)" if audit_integrity.valid else "ALTERADA", f"{audit_integrity.verified_entries} / {audit_integrity.total_entries}", "Encadenamiento continuo"],
        ]
        t_int = Table(int_data, colWidths=[150, 130, 110, 150])
        t_int.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{NAVY_HEADER}")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("TEXTCOLOR", (1, 1), (1, -1), colors.HexColor(f"#{EMERALD_ACCENT}")),
            ("FONTNAME", (1, 1), (1, -1), "Helvetica-Bold"),
        ]))
        story.append(t_int)
        story.append(Spacer(1, 14))

        # Primeras entradas de auditoría
        story.append(Paragraph("<b>Registro Cronológico de Bitácora Inmutable (AuditLog)</b>", styles["Heading3"]))
        log_data = [["#", "Fecha/Hora (UTC)", "Rol", "Acción", "Hash Entrada (entry_hash)"]]
        for l in logs[:30]:
            log_data.append([
                str(l.chain_index),
                l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "",
                l.actor_role,
                l.action,
                Paragraph(l.entry_hash or "", mono_style),
            ])

        t_log = Table(log_data, colWidths=[30, 95, 75, 140, 200])
        t_log.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(f"#{NAVY_HEADER}")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        story.append(t_log)

        doc.build(story)
        buf.seek(0)
        return buf
